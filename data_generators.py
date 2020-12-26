import random
from abc import ABCMeta, abstractmethod
from majormode.utils.namegen import NameGeneratorFactory, NameGenerator
from typing import Any, Callable, Union


class BaseGenerator(metaclass=ABCMeta):
    """Abstract node for generating arbitrary data"""

    def __iter__(self):
        while True:
            yield next(self)

    def __next__(self):
        return self.generate({})

    @abstractmethod
    def generate(self, data: dict = None) -> Any:
        """Generates an arbitrary instances of data"""

        pass

    @abstractmethod
    def info(self) -> Any:
        """Traversal visualization object returns information about object"""

        pass


class Primitive:
    """Generators that create their own non-arbitrary types of data"""

    @classmethod
    def value(cls, value: Any):
        """Convert a value into a generator if it isn't one already"""

        return value if isinstance(value, BaseGenerator) else Primitive.ValueGenerator(value)

    class NoneGenerator(BaseGenerator):
        """None handler generator"""

        def generate(self, data: dict = None) -> None:
            return None

        def info(self):
            return None

    class ValueGenerator(BaseGenerator):
        """Generates a single arbitrary value"""

        def __init__(self, value: Any = None):
            self.value(value)

        def value(self, value: Any = None) -> None:
            """Set generated value"""

            self._value = value

        def generate(self, data: dict = None) -> Any:
            return self._value

        def info(self) -> Any:
            return self._value

    class IntegerGenerator(BaseGenerator):
        """Generates integers"""

        def __init__(self,
                     start: Union[int, BaseGenerator],
                     stop: Union[int, BaseGenerator],
                     step: Union[int, BaseGenerator] = 1):

            super().__init__()
            self.range(start, stop, step)

        def range(self,
                  start: Union[int, BaseGenerator],
                  stop: Union[int, BaseGenerator],
                  step: Union[int, BaseGenerator] = 1) -> None:

            self._start = Primitive.value(start)
            self._stop = Primitive.value(stop)
            self._step = Primitive.value(step)

        def generate(self, data: dict = None) -> int:
            start = self._start.generate(data)
            stop = self._stop.generate(data)
            step = self._step.generate(data)

            return random.randrange(start, stop, step)

        def info(self) -> Any:
            return {
                'type': 'IntegerGenerator',
                'start': self._start.info(),
                'stop': self._stop.info(),
                'step': self._step.info()
            }

    class FloatGenerator(BaseGenerator):
        """Generates floating point numbers"""

        def __init__(self, start: float, stop: float, precision: int = 1):
            super().__init__()
            self.range(start, stop, precision)

        def range(self,
                  start: Union[float, BaseGenerator],
                  stop: Union[float, BaseGenerator],
                  precision: Union[float, BaseGenerator] = 1) -> None:

            self._start = Primitive.value(start)
            self._stop = Primitive.value(stop)
            self._precision = Primitive.value(precision)

        def generate(self, data: dict = None) -> float:
            start = self._start.generate(data)
            stop = self._stop.generate(data)
            precision = self._precision.generate(data)

            return round(random.uniform(start, stop), precision)

        def info(self) -> Any:
            return {
                'type': 'FloatGenerator',
                'start': self._start.info(),
                'stop': self._start.info(),
                'precision': self._precision.info()
            }

    class NameGenerator(BaseGenerator):
        """Generates a name string"""

        _name_factory_lookup = dict(zip(
            [str(language) for language in NameGeneratorFactory.Language],
            NameGeneratorFactory.Language
        ))

        def __init__(self,
                     language: Union[str, BaseGenerator] = 'Hebrew',
                     min_syl: Union[int, BaseGenerator] = 2,
                     max_syl: Union[int, BaseGenerator] = 4):

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

        def language(self, language: Union[str, BaseGenerator]) -> None:
            self._language = Primitive.value(language)

        def syllables(self, min_syl: Union[int, BaseGenerator], max_syl: Union[int, BaseGenerator]) -> None:
            self._min_syl = Primitive.value(min_syl)
            self._max_syl = Primitive.value(max_syl)

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


class Variable:
    """Generators with a variable number of child generators"""

    class StringGenerator(BaseGenerator):
        """Arbitrary string concatenation"""

        def __init__(self, string: [str, BaseGenerator], *generators: Union[str, BaseGenerator]):
            super().__init__()
            self.string(string, *generators)

        def string(self,  string: [str, BaseGenerator], *generators: [str, BaseGenerator]):
            self._string = Primitive.value(string)
            self._generators = [Primitive.value(g) for g in generators]

        def generate(self, data: dict = None) -> str:
            string = self._string.generate(data)
            substrings = [g.generate(data) for g in self._generators]
            return string.format(*substrings)

        def info(self) -> Any:
            if len(self._generators) > 0:
                return {
                    'string': self._string.info(),
                    'formatters': list([f.info() for f in self._generators])
                }
            else:
                return self._string.info()

    class DictGenerator(BaseGenerator):
        """"Generates each value in a dictionary if return is not None"""

        def __init__(self, key_values: list[tuple[BaseGenerator, Union[BaseGenerator, str, None]]] = None):
            super().__init__()
            self._key_values = []
            if key_values:
                self.fields(*key_values)

        def generate(self, data: dict = None) -> dict:
            fake_data = {}
            for generator, field_generator in self._key_values:
                self._generate(generator, field_generator, fake_data)

            return fake_data

        def fields(self, *key_values: tuple[BaseGenerator, Union[BaseGenerator, str, None]]):
            """Replaces current key value generators"""

            self._key_values.clear()
            for key_val in key_values:
                self.field(*key_val)

        def field(self, generator: BaseGenerator, field: Union[BaseGenerator, str, None] = None):
            """Appends a new key value generator"""

            if isinstance(field, str):
                field = Variable.StringGenerator(field)

            self._key_values.append((generator, field))

        @staticmethod
        def _generate(generator: BaseGenerator, field: Union[BaseGenerator, None], data: dict) -> None:
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

    class SampleGenerator(BaseGenerator):
        """Random list sampler"""

        def __init__(self,
                     generators: list[BaseGenerator],
                     min_size: Union[int, BaseGenerator],
                     max_size: Union[int, BaseGenerator]):

            super().__init__()
            self._generators = generators
            self.size(min_size, max_size)

        def size(self, min_size, max_size):
            self._min_size = Primitive.ValueGenerator(min_size)
            self._max_size = Primitive.ValueGenerator(max_size)

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

    class ChoiceGenerator(BaseGenerator):
        """Random element selector"""

        _DEFAULT_WEIGHT = Primitive.ValueGenerator(1)

        def __init__(self, generators: [BaseGenerator] = None, weights: [int, BaseGenerator] = None):
            super().__init__()
            self.choices(generators, weights)

        def choices(self, generators: [BaseGenerator] = None, weights: [int, BaseGenerator] = None) -> None:
            """Set list of items to choose items from"""

            self._generators = generators
            if weights:
                self._weights = [Primitive.ValueGenerator(w) for w in weights]
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


class Wrapper:
    """Generators that manipulate the arbitrary output of a child generator"""

    class ConditionalGenerator(BaseGenerator):
        """Selects which generator to run based on arbitrary conditions"""

        def __init__(self,
                     true_generator: BaseGenerator = None,
                     false_generator: BaseGenerator = None,
                     conditions: list[Callable[[dict], bool]] = None):

            self.true(true_generator)
            self.false(false_generator)
            self.conditions(conditions)

        def true(self, generator: BaseGenerator = None) -> None:
            """Set generator to run if all conditions are true"""

            self._true_generator = generator or Primitive.NoneGenerator()

        def false(self, generator: BaseGenerator = None) -> None:
            """Set generator to run if not all conditions are true"""

            self._false_generator = generator or Primitive.NoneGenerator()

        def conditions(self, conditions: list[Callable[[dict], bool]] = None) -> None:
            """Set boolean conditions that check which generator to run"""

            self._conditions = conditions or []

        def generate(self, data: dict = None) -> Any:
            """Runs true generator if all conditions are met, false generator otherwise"""

            generator = self._true_generator
            for condition in self._conditions:
                if not condition(data):
                    generator = self._false_generator
                    break

            return generator.generate(data or {})

        def info(self) -> dict:
            info = {'conditions': len(self._conditions)}
            true_info = self._true_generator.info()
            false_info = self._false_generator.info()

            if true_info is not None:
                info['true'] = true_info
            if false_info is not None:
                info['true'] = false_info

            return info

    class RepeaterGenerator(BaseGenerator):
        """Generates repeating generator output"""

        def __init__(self, generator: BaseGenerator):
            super().__init__()
            self._generator = generator
            self.repeat()

        def repeat(self, start: Union[int, BaseGenerator] = 1, stop: int = Union[int, BaseGenerator]) -> None:
            self._min_reps = Primitive.ValueGenerator(start)
            self._max_reps = Primitive.ValueGenerator(stop)

        def generate(self, data: dict = None) -> Any:
            """Runs a generator a random number of times"""

            min_reps = self._min_reps.generate(data)
            max_reps = self._max_reps.generate(data)
            reps = random.randint(min_reps, max_reps)

            fake_data = []
            for _ in range(reps):
                fake_data.append(self._generator.generate(data))

            return fake_data

        def info(self) -> Any:
            return {
                'type': 'RepeaterGenerator',
                'min': self._min_reps.info(),
                'max': self._max_reps.info(),
                'child': self._generator.info()
            }
