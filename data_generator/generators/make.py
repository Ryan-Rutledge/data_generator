import random
from typing import Any, Union

from majormode.utils.namegen import NameGeneratorFactory, NameGenerator

from data_generator.generators import primitive


class Name(primitive.Generator):
    """Generates a name string"""

    _name_factory_lookup = dict(zip(
        [str(language) for language in NameGeneratorFactory.Language],
        NameGeneratorFactory.Language
    ))

    def __init__(self,
                 language: Union[str, primitive.Generator] = 'Hebrew',
                 min_syl: Union[int, primitive.Generator] = 2,
                 max_syl: Union[int, primitive.Generator] = 4):

        super().__init__()

        # Create  list of generator classes
        self._name_factories = dict(
            [(str(lang), None) for lang in NameGeneratorFactory.Language]
        )

        self.language(language)
        self.syllables(min_syl, max_syl)

    @classmethod
    def _instantiate(cls, language: str):
        return NameGeneratorFactory.get_instance(cls._name_factory_lookup[language])

    def _get_language_generator(self, language: str) -> NameGenerator:
        # Instantiate name generator if one for that language has not been already been instantiated
        generator = self._name_factories.get(language)
        if generator is None:
            generator = self._name_factories[language] = self._instantiate(language)
        return generator

    def language(self, language: Union[str, primitive.Generator]) -> None:
        self._language = primitive.generates(language)

    def syllables(self, min_syl: Union[int, primitive.Generator], max_syl: Union[int, primitive.Generator]) -> None:
        self._min_syl = primitive.generates(min_syl)
        self._max_syl = primitive.generates(max_syl)

    def generate(self, data: dict = None) -> str:
        language = self._language.generate(data)
        generator = self._get_language_generator(language)
        generator.min_syl = self._min_syl.generate(data)
        generator.max_syl = self._max_syl.generate(data)
        return generator.generate_name(True)

    def info(self) -> Any:
        return {
            'type': 'LanguageGenerator',
            'language': self._language.info(),
            'min_syllables': self._min_syl.info(),
            'max_syllables': self._max_syl.info()
        }


class Counter(primitive.Generator):
    """Generates incrementing integers"""

    def __init__(self,
                 start: Union[int, primitive.Generator],
                 stop: Union[int, float, primitive.Generator] = None,
                 step: Union[int, float, primitive.Generator] = 1):

        super().__init__()
        self.range(start, stop, step)

    def range(self,
              start: Union[int, float, primitive.Generator],
              step: Union[int, float, primitive.Generator] = 1,
              stop: Union[int, float, primitive.Generator] = None,
              ) -> None:

        self._previous = None
        self._start = primitive.generates(start)
        self._step = primitive.generates(step)
        self._stop = primitive.generates(stop)

    def generate(self, data: dict = None) -> int:
        if self._previous is None:  # If first time running increment
            value = self._previous = self._start.generate(data)
        else:
            step = self._step.generate(data)
            stop = self._stop.generate(data)
            value = self._previous + step

            # If generator has incremented/decremented past stopping point
            if stop is not None and ((step > 0 and value > stop) or (step < 0 and value < stop)):
                value = self._previous = self._start.generate(data)
            else:
                self._previous = value

        return value

    def info(self) -> Any:
        return {
            'type': 'IncrementGenerator',
            'start': self._start.info(),
            'step': self._step.info(),
            'stop': self._stop.info()
        }


class Dict(primitive.Generator):
    """"Generates each value in a dictionary if return is not None"""

    def __init__(self, key_values: list[tuple[primitive.Generator, Union[primitive.Generator, str, None]]] = None):
        super().__init__()
        self._key_values = []
        if key_values:
            self.fields(*key_values)

    def generate(self, data: dict = None) -> dict:
        fake_data = {}
        for generator, field_generator in self._key_values:
            self._generate(generator, field_generator, fake_data)

        return fake_data

    def fields(self, *key_values: tuple[primitive.Generator, Union[primitive.Generator, str, None]]):
        """Replaces current key value generators"""

        self._key_values.clear()
        for key_val in key_values:
            self.field(*key_val)

    def field(self, generator: primitive.Generator, field: Union[primitive.Generator, str, None] = None):
        """Appends a new key value generator"""

        if isinstance(field, str):
            field = primitive.String(field)

        self._key_values.append((generator, field))

    @staticmethod
    def _generate(generator: primitive.Generator, field: Union[primitive.Generator, None], data: dict) -> None:
        generated_data = generator.generate(data)

        if generated_data is not None:
            if field is None:
                # Raise key values from generated data
                for key, val in generated_data:
                    data[key] = val
            else:
                field_names = field.generate(data)
                # Ensure field_names is a list
                field_names = field_names if isinstance(field_names, list) else [field_names]

                for field_name in field_names:
                    data[field_name] = generated_data

    def info(self) -> Any:
        return {
            'type': 'DictGenerator',
            'items': list([{"key": k.info(), "value": v.info()} for v, k in self._key_values])
        }


class Sample(primitive.Generator):
    """Random list sampler"""

    def __init__(self,
                 generators: list[primitive.Generator],
                 min_size: Union[int, primitive.Generator],
                 max_size: Union[int, primitive.Generator]):
        super().__init__()
        self._generators = generators
        self.size(min_size, max_size)

    def size(self, min_size, max_size):
        self._min_size = primitive.generates(min_size)
        self._max_size = primitive.generates(max_size)

    def generate(self, data: dict = None) -> list:
        min_size = self._min_size.generate(data)
        max_size = self._min_size.generate(data)
        count = random.randint(min_size, max_size)

        return list([d.generate(data) for d in random.sample(self._generators, k=count)])

    def info(self) -> Any:
        return {
            'type': 'SampleGenerator',
            'min': self._min_size.info(),
            'max': self._max_size.info(),
            'data': list([g.info() for g in self._generators])
        }


class Choice(primitive.Generator):
    """Random element selector"""

    _DEFAULT_WEIGHT = primitive.generates(1)

    def __init__(self, generators: [primitive.Generator] = None, weights: [int, primitive.Generator] = None):
        super().__init__()
        self.choices(generators, weights)

    def choices(self, generators: [primitive.Generator] = None, weights: [int, primitive.Generator] = None) -> None:
        """Set list of items to choose items from"""

        self._generators = generators
        if weights:
            self._weights = [primitive.generates(w) for w in weights]
        else:
            self._weights = [self._DEFAULT_WEIGHT] * len(self._generators)  # Default all weights to 1

    def generate(self, data: dict = None) -> Any:
        weights = [w.generate(data) for w in self._weights]
        generator = random.choices(self._generators, weights=weights, k=1)
        return generator[0].generate(data)

    def info(self) -> Any:
        return {
            'type': 'ChoiceGenerator',
            'items': [{"weight": w, "value": k} for w, k in zip(
                [w.info() for w in self._weights],
                [g.info() for g in self._generators],
            )]
        }
