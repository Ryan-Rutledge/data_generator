import random
from abc import ABCMeta, abstractmethod
from majormode.utils.namegen import NameGeneratorFactory
from typing import Callable, Any


class BaseGenerator(metaclass=ABCMeta):
    """Abstract node for holding arbitrary data"""

    def __init__(self,
                 reps: [int, (int, int)] = 1,
                 conditions: list[Callable[[dict], bool], ...] = None):

        self.conditions = conditions or []
        self.min_reps, self.max_reps = (reps, reps) if isinstance(reps, int) else reps

    def __iter__(self):
        while True:
            yield next(self)

    def __next__(self):
        return self.generate({})

    def meets_conditions(self, data: dict = None) -> bool:
        """Returns true if all conditions are met, false otherwise"""

        if data is None:
            data = {}

        for condition in self.conditions:
            if not condition(data):
                return False
        return True

    def generate(self, data: dict = None) -> Any:
        """Generates an arbitrary number of arbitrary instances of data if conditions are met"""

        data = data or {}
        if self.meets_conditions(data):
            reps = random.randint(self.min_reps, self.max_reps)

            fake_data = []
            for _ in range(reps):
                fake_data.append(self._generate(data))

            return fake_data[0] if self.min_reps == 1 and self.max_reps == 1 else fake_data

    @abstractmethod
    def _generate(self, data: dict = None) -> Any:
        """Generates a single instance of arbitrary data"""

        pass


class NoneGenerator(BaseGenerator):
    """None handler generator"""

    def _generate(self, data: dict = None) -> None:
        return None


class RepeaterGenerator(BaseGenerator, metaclass=ABCMeta):
    """Abstract node for custom repetition features"""

    def generate(self, data: dict = None) -> [Any, None]:
        data = data or {}
        if self.meets_conditions(data):
            return self._generate(data)

    @abstractmethod
    def _generate(self, data: dict = None) -> Any:
        pass


class IntegerGenerator(BaseGenerator, metaclass=ABCMeta):
    """Generates integers"""

    def __init__(self, start: int, stop: int, step: int = 1,
                 reps: [int, (int, int)] = 1,
                 conditions: list[Callable[[dict], bool]] = None):

        super().__init__(reps, conditions)
        self.start, self.stop, self.step = start, stop, step

    def _generate(self, data: dict = None):
        return random.randrange(self.start, self.stop, self.step)


class FloatGenerator(BaseGenerator, metaclass=ABCMeta):
    """Generates floating point numbers"""

    def __init__(self, start: float, stop: float, decimals: int = 1,
                 reps: [int, (int, int)] = 1,
                 conditions: list[Callable[[dict], bool]] = None):

        super().__init__(reps, conditions)
        self.start, self.stop, self.decimals = start, stop, decimals

    def _generate_float(self):
        return round(random.uniform(self.start, self.stop), self.decimals)


class NameGenerator(RepeaterGenerator):
    """Generates a name string"""

    _name_generators = dict(zip(
        [str(language) for language in NameGeneratorFactory.Language],
        NameGeneratorFactory.Language
    ))

    def __init__(self,
                 language: str = 'Hebrew',
                 reps: [int, (int, int)] = (1, 4),
                 conditions: list[Callable[[dict], bool]] = None):

        super().__init__(reps, conditions)
        self.generator = NameGeneratorFactory.get_instance(self._name_generators[language])
        self.generator.min_syl, self.generator.max_syl = self.min_reps, self.max_reps

    def _generate(self, data: dict = None) -> str:
        return self.generator.generate_name(True)


class StringGenerator(BaseGenerator):
    """Arbitrary string concatenation"""

    def __init__(self,
                 string: str,
                 generators: list[BaseGenerator, ...] = None,
                 reps: [int, (int, int)] = 1,
                 conditions: list[Callable[[dict], bool]] = None):

        super().__init__(reps, conditions)

        self.string = string
        self.generators = generators or []

    def _generate(self, data=None) -> str:
        random_substrings = [g.generate(data) for g in self.generators]
        return self.string.format(*random_substrings)


class SampleGenerator(BaseGenerator):
    """Random list selection node"""

    def __init__(self,
                 generators: list[BaseGenerator, ...],
                 size: [int, (int, int)] = 1,
                 reps: [int, (int, int)] = 1,
                 conditions: list[Callable[[dict], bool]] = None):

        super().__init__(reps, conditions)
        self.generators = generators
        self.min_size, self.max_size = (size, size) if isinstance(size, int) else size

    def _generate(self, data: dict = None) -> Any:
        count = random.randint(self.min_size, self.max_size)
        fake_data = list([d.generate(data) for d in random.sample(self.generators, k=count)])
        return self._list_or_element(fake_data)

    def _list_or_element(self, items: list) -> [Any, list[Any, ...]]:
        return items[0] if self.min_size == 1 and self.max_size == 1 else items


class ChoiceGenerator(RepeaterGenerator):
    """Random elements chooser"""

    def __init__(self,
                 generators: [BaseGenerator, ...] = None,
                 weights: [int, ...] = None,
                 reps: [int, (int, int)] = 1,
                 conditions: [Callable[[dict], bool]] = None):

        super().__init__(reps, conditions)
        self.weights = weights or [1] * len(self.generators)  # Default all weights to 1
        self.generators = generators

    def _generate(self, data: dict = None) -> Any:
        reps = random.randint(self.min_reps, self.max_reps)
        generators = random.choices(self.generators, weights=self.weights, k=reps)
        output = [choice.generate(data) for choice in generators]

        return output[0] if self.min_reps == 1 and self.max_reps == 1 else output


class DictGenerator(BaseGenerator):
    """"Generates each value in a dictionary if the generator conditions are met"""

    def __init__(self,
                 generators: dict[str, BaseGenerator] = None,
                 reps: [int, (int, int)] = 1,
                 conditions: list[Callable[[dict], bool]] = None):

        super().__init__(reps, conditions)
        self.generators = generators or dict()

    def _generate(self, data: dict = None) -> dict:
        fake_data = {}
        for field, generator in self.generators.items():
            generated_data = generator.generate(fake_data)

            if generated_data is not None:
                fake_data[field] = generated_data

        return fake_data
