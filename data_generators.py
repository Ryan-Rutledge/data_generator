import random
from abc import ABCMeta, abstractmethod
from majormode.utils.namegen import NameGeneratorFactory
from typing import Any, Callable, Union


class BaseGenerator(metaclass=ABCMeta):
    """Abstract node for holding arbitrary data"""

    def __iter__(self):
        while True:
            yield next(self)

    def __next__(self):
        return self.generate({})

    @abstractmethod
    def generate(self, data: dict = None) -> Any:
        """Generates an arbitrary instances of data"""

        pass


class Primitive:
    """Generators that create their own non-arbitrary types of data"""

    class NoneGenerator(BaseGenerator):
        """None handler generator"""

        def generate(self, data: dict = None) -> None:
            return None

    class IntegerGenerator(BaseGenerator):
        """Generates integers"""

        def __init__(self, start: int, stop: int, step: int = 1):
            super().__init__()
            self.start, self.stop, self.step = start, stop, step

        def generate(self, data: dict = None) -> int:
            return random.randrange(self.start, self.stop, self.step)

    class FloatGenerator(BaseGenerator):
        """Generates floating point numbers"""

        def __init__(self, start: float, stop: float, precision: int = 1):
            super().__init__()
            self.start, self.stop, self.precision = start, stop, precision

        def generate(self, data: dict = None) -> float:
            return round(random.uniform(self.start, self.stop), self.precision)

    class NameGenerator(BaseGenerator):
        """Generates a name string"""

        _name_generators = dict(zip(
            [str(language) for language in NameGeneratorFactory.Language],
            NameGeneratorFactory.Language
        ))

        def __init__(self, language: str = 'Hebrew', min_syl: int = None, max_syl: int = None):
            super().__init__()
            self.generator = NameGeneratorFactory.get_instance(self._name_generators[language])
            self.generator.min_syl = min_syl or 2
            self.generator.max_syl = max_syl or 4

        def generate(self, data: dict = None) -> str:
            return self.generator.generate_name(True)


class Complex:
    """Generators that manipulate primitive generators"""

    class StringGenerator(BaseGenerator):
        """Arbitrary string concatenation"""

        def __init__(self, string: str, generators: list[BaseGenerator] = None):
            super().__init__()
            self.string = string
            self.generators = generators or []

        def generate(self, data: dict = None) -> str:
            random_substrings = [g.generate(data) for g in self.generators]
            return self.string.format(*random_substrings)

    class DictGenerator(BaseGenerator):
        """"Generates each value in a dictionary if return is not None"""

        def __init__(self, generators: list[tuple[str, BaseGenerator]] = None):
            super().__init__()
            self.generators = generators or []

        def generate(self, data: dict = None) -> dict:
            fake_data = {}
            for field, generator in self.generators:
                generated_data = generator.generate(fake_data)

                if generated_data is not None:
                    fake_data[field] = generated_data

            return fake_data

    class SampleGenerator(BaseGenerator):
        """Random list sampler"""

        def __init__(self, generators: list[BaseGenerator], size: Union[int, tuple[int, int]] = 1):

            super().__init__()
            self.generators = generators
            self.min_size, self.max_size = (size, size) if isinstance(size, int) else size

        def generate(self, data: dict = None) -> list:
            count = random.randint(self.min_size, self.max_size)
            fake_data = list([d.generate(data) for d in random.sample(self.generators, k=count)])
            return fake_data

    class ChoiceGenerator(BaseGenerator):
        """Random element selector"""

        def __init__(self, generators: [BaseGenerator] = None, weights: [int] = None):
            super().__init__()
            self.weights = weights or [1] * len(self.generators)  # Default all weights to 1
            self.generators = generators

        def generate(self, data: dict = None) -> Any:
            generator = random.choices(self.generators, weights=self.weights, k=1)
            return generator[0].generate(data)


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
            self._true_generator = generator or Primitive.NoneGenerator

        def false(self, generator: BaseGenerator = None) -> None:
            self._false_generator = generator or Primitive.NoneGenerator

        def conditions(self, conditions: list[Callable[[dict], bool]] = None) -> None:

            self._conditions = conditions or []

        def generate(self, data: dict = None) -> Any:
            """Runs true generator if all conditions are met, false generator otherwise"""

            generator = self._true_generator
            for condition in self._conditions:
                if not condition(data):
                    generator = self._false_generator
                    break

            return generator.generate(data or {})

    class RepeaterGenerator(BaseGenerator):
        """Generates repeating generator output"""

        def __init__(self, generator: BaseGenerator):
            super().__init__()
            self.generator = generator
            self.repeat()

        def generate(self, data: dict = None) -> Any:
            """Runs a generator a random number of times"""
            reps = random.randint(self.min_reps, self.max_reps)

            fake_data = []
            for _ in range(reps):
                fake_data.append(self.generator.generate(data))

            return fake_data

        def repeat(self, start: int = 1, stop: int = 1, step: int = 1) -> None:
            self.min_reps = max(start, 1)
            self.max_reps = min(max(stop, 1), self.min_reps)
            self.rep_step = max(step, 1)
