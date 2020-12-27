import random
from typing import Any, Callable, Union

from data_generator.generators import primitive, make


class Condition(primitive.Generator):
    """Selects which generator to run based on arbitrary conditions"""

    def __init__(self,
                 true_generator: primitive.Generator = None,
                 false_generator: primitive.Generator = None,
                 conditions: list[Callable[[dict], bool]] = None):

        self.true(true_generator)
        self.false(false_generator)
        self.conditions(conditions)

    def true(self, generator: primitive.Generator = None) -> None:
        """Set generator to run if all conditions are true"""

        self._true_generator = generator or primitive.generates(None)

    def false(self, generator: primitive.Generator = None) -> None:
        """Set generator to run if not all conditions are true"""

        self._false_generator = generator or primitive.generates(None)

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


class Repeat(primitive.Generator):
    """Generates repeating generator output"""

    def __init__(self, generator: primitive.Generator):
        super().__init__()
        self._generator = generator
        self.repeat()

    def repeat(self, start: Union[int, primitive.Generator] = 1, stop: Union[int, primitive.Generator] = 1) -> None:
        self._min_reps = primitive.generates(start)
        self._max_reps = primitive.generates(stop)

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


class Rotate(primitive.Generator):
    """Returns the output of one generator in a time, in order"""

    def __init__(self, generators: list[Any]):
        self.generators(generators)

    def generators(self, generators: list[primitive.Generator], incrementer: primitive.Generator = None):
        if incrementer is None:
            incrementer = make.Counter(0, 1, len(generators) - 1)

        self._incrementer = incrementer
        self._generators = [primitive.generates(g) for g in generators]

    def generate(self, data: dict = None) -> Any:
        index = self._incrementer.generate(data)

        if index < len(self._generators):
            generator = self._generators[index]
            return generator.generate(data)
        else:
            return None

    def info(self):
        return {
            'type': 'RotateGenerator',
            'increment': self._incrementer,
            'generators': list([g.info() for g in self._generators])
        }


class Consume(primitive.Generator):
    """Sequentially run generators until they return None"""

    def __init__(self, generators: list[Any]):
        self.generators(generators)

    def generators(self, generators: list[primitive.Generator]):
        """Set new generators to consume"""

        self._index = 0
        self._generators = generators

    def generate(self, data: dict = None) -> Any:
        fake_data = self._generators[self._index].generate(data)

        if fake_data is None:
            self._index += 1  # Increment generator index

        return fake_data

    def info(self) -> Any:
        return {
            'type': 'ConsumeGenerator',
            'generators': list([g.info() for g in self._generators])
        }
