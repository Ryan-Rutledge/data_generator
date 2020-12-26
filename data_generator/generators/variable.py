from data_generator.generators.primitive import *
import random
from typing import Any, Union


class StringGenerator(BaseGenerator):
    """Arbitrary string concatenation"""

    def __init__(self, string: [str, BaseGenerator], *generators: Union[str, BaseGenerator]):
        super().__init__()
        self.string(string, *generators)

    def string(self, string: [str, BaseGenerator], *generators: [str, BaseGenerator]):
        self._string = to_generator(string)
        self._generators = [to_generator(g) for g in generators]

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
            field = StringGenerator(field)

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
        self._min_size = ValueGenerator(min_size)
        self._max_size = ValueGenerator(max_size)

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

    _DEFAULT_WEIGHT = ValueGenerator(1)

    def __init__(self, generators: [BaseGenerator] = None, weights: [int, BaseGenerator] = None):
        super().__init__()
        self.choices(generators, weights)

    def choices(self, generators: [BaseGenerator] = None, weights: [int, BaseGenerator] = None) -> None:
        """Set list of items to choose items from"""

        self._generators = generators
        if weights:
            self._weights = [ValueGenerator(w) for w in weights]
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
