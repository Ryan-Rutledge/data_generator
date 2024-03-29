import random
from abc import ABCMeta, abstractmethod

from data_generator.randomizers import complex, primitive


class ConditionRandomizer(primitive.Randomizer, metaclass=ABCMeta):
    """Selects which generator to run based on arbitrary conditions"""

    def __init__(
        self,
        on_true=None,
        on_false=None,
        condition_functions=None,
    ):

        self._type = "ConditionRandomizer"
        self._true_randomizer = primitive.randomizer(on_true)
        self._false_randomizer = primitive.randomizer(on_false)
        self._condition_functions = condition_functions or []

    @abstractmethod
    def next(self, data=None):
        pass

    def info(self):
        return {
            "type": self._type,
            "conditions": len(self._conditions),
            "on true": self._true_randomizer.info(),
            "on false": self._false_randomizer.info(),
        }


class AndConditionRandomizer(ConditionRandomizer):
    def __init__(self, on_true, on_false, condition_functions):
        super().__init__(on_true, on_false, condition_functions)
        self._type = "AndConditionRandomizer"

    def next(self, data=None):
        """Runs true generator if all conditions are met, false generator otherwise"""

        randomizer = self._true_randomizer
        for condition in self._condition_functions:
            if not condition(data):
                randomizer = self._false_randomizer
                break

        return randomizer.next(data or {})


class OrConditionRandomizer(ConditionRandomizer):
    def __init__(self, on_true, on_false, condition_functions):
        super().__init__(on_true, on_false, condition_functions)
        self._type = "OrConditionRandomizer"

    def next(self, data=None):
        """Runs true generator if any conditions are met, false generator otherwise"""

        randomizer = self._false_randomizer
        for condition in self._condition_functions:
            if condition(data):
                randomizer = self._true_randomizer
                break

        return randomizer.next(data)


class RepeatRandomizer(primitive.Randomizer):
    """Generates repeating generator output"""

    def __init__(self, randomizer, reps):
        super().__init__()
        self._randomizer = randomizer
        self._total_reps = primitive.randomizable(reps)

    def next(self, data=None):
        """Runs a generator a random number of times"""

        total_reps = self._total_reps.next(data)

        random_data = []
        for _ in range(total_reps):
            random_data.append(self._randomizer.next(data))

        return random_data

    def info(self):
        return {
            "type": "RepeaterRandomizer",
            "reps": self._total_reps.info(),
            "child": self._randomizer.info(),
        }


class RotateRandomizer(primitive.Randomizer):
    """Returns the output of one randomizer at a time, in order"""

    def __init__(self, *randomizers):
        self._randomizers = [primitive.randomizable(r) for r in randomizers]
        self._cur_index = 0

    def next(self, data=None):
        next_value = self._cur_randomizer().next(data)
        self._increment_cur_index()
        return next_value

    def _increment_cur_index(self):
        self._cur_index = self._cur_index + 1

    def _cur_randomizer(self):
        if self._randomizer_exists_at_index():
            return self._randomizers[self._cur_index]
        else:
            return primitive.NoneRandomizer

    def _randomizer_exists_at_index(self):
        return self._cur_index < len(self._randomizers) and self._cur_index >= 0

    def info(self):
        return {"type": "RotateRandomizer", "randomizers": self._randomizers_info()}

    def _randomizers_info(self):
        return (list([r.info() for r in self._randomizers]),)


class InfiniteRotateRandomizer(RotateRandomizer):
    def _increment_cur_index(self):
        self._cur_index = (self._cur_index + 1) % len(self._randomizers)

    def info(self):
        return {
            "type": "InfiniteRotateRandomizer",
            "randomizers": self._randomizers_info(),
        }


class ConsumeRandomizer(primitive.Randomizer):
    """Sequentially run generators until they return None"""

    def __init__(self, randomizers):
        self._cur_index = 0
        self._randomizers = randomizers

    def next(self, data=None):
        if not self._isDone():
            return self._next_randomizer(data)

        return None

    def _isDone(self):
        return self._cur_index >= len(self._randomizers)

    def _next_randomizer(self, data):
        randomizer = self._randomizers[self._cur_index]
        randomizer_data = randomizer.next(data)

        # Rotate to the next randomizer if this one is finished
        if randomizer_data is None:
            return self._consume_next_randomizer(data)

        return randomizer_data

    def _consume_next_randomizer(self, data):
        self._cur_index += 1
        return self.next(data)

    def info(self):
        return {
            "type": "ConsumeRandomizer",
            "generators": list([r.info() for r in self._randomizers]),
        }
