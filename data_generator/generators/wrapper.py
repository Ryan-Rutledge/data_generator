from data_generator.generators.primitive import *
from typing import Any, Callable, Union


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

        self._true_generator = generator or NoneGenerator()

    def false(self, generator: BaseGenerator = None) -> None:
        """Set generator to run if not all conditions are true"""

        self._false_generator = generator or NoneGenerator()

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

    def repeat(self, start: Union[int, BaseGenerator] = 1, stop: Union[int, BaseGenerator] = 1) -> None:
        self._min_reps = ValueGenerator(start)
        self._max_reps = ValueGenerator(stop)

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
