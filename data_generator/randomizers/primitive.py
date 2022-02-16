import random
from abc import ABCMeta, abstractmethod


class Randomizer(metaclass=ABCMeta):
    """Abstract node for generating arbitrary data"""

    def __iter__(self):
        while True:
            yield next(self)

    def __next__(self):
        return self.next({})

    @abstractmethod
    def next(self, data=None):
        """Generates an arbitrary instance of data"""

        pass

    @abstractmethod
    def info(self):
        """Returns recursive randomizer info for visualization"""

        pass


class NoneRandomizer(Randomizer):
    """Generates None"""

    @staticmethod
    def next(data=None):
        return None

    @staticmethod
    def info():
        return None

class PassThroughRandomizer(Randomizer):
    """Generates a single arbitrary value"""

    def __init__(self, value=None):
        self._value = value

    def next(self, data=None):
        return self._value

    def info(self):
        if callable(self._value):
            # It should be made clear when the value is a function
            return self._value.__name__ + "()"
        else:
            return str(self._value)


class IntegerRandomizer(Randomizer):
    """Generates integers"""

    def __init__(self, start, stop, step=1):

        super().__init__()

        self._start = randomizable(start)
        self._stop = randomizable(stop)
        self._step = randomizable(step)

    def next(self, data):
        start = self._start.next(data)
        stop = self._stop.next(data)
        step = self._step.next(data)

        return random.randrange(start, stop, step)

    def info(self):
        return {
            "type": "IntegerRandomizer",
            "start": self._start.info(),
            "stop": self._stop.info(),
            "step": self._step.info(),
        }


class FloatRandomizer(Randomizer):
    """Generates floating point numbers"""

    def __init__(self, start, stop, precision=1):
        super().__init__()

        self._start = randomizable(start)
        self._stop = randomizable(stop)
        self._precision = randomizable(precision)

    def next(self, data=None):
        start = self._start.next(data)
        stop = self._stop.next(data)
        precision = self._precision.next(data)

        return round(random.uniform(start, stop), precision)

    def info(self):
        return {
            "type": "FloatRandomizer",
            "start": self._start.info(),
            "stop": self._start.info(),
            "precision": self._precision.info(),
        }


class FunctionRandomizer(Randomizer):
    """Generates output of an arbitrary function"""

    def __init__(self, function, *parameters):
        super().__init__()

        self._function = randomizable(function)
        self._parameters = [randomizable(p) for p in parameters]

    def next(self, data=None):
        function = self._function.next(data)
        parameters = [p.next(data) for p in self._parameters]
        return function(*parameters)

    def info(self):
        return {
            "type": "FunctionRandomizer",
            "function": self._function.info(),
            "parameters": [p.info for p in self._parameters],
        }


class StringRandomizer(Randomizer):
    """Arbitrary string interpolator"""

    def __init__(self, string, *interpolators):
        super().__init__()

        self._format_string = randomizable(string)
        self._interpolators = [
            randomizable(interpolator) for interpolator in interpolators
        ]

    def next(self, data=None):
        format_string = self._format_string.next(data)
        interpolators = [g.next(data) for g in self._interpolators]
        return format_string.format(*interpolators)

    def info(self):
        return {
            "format_string": self._format_string.info(),
            "interpolators": list([f.info() for f in self._interpolators]),
        }


def randomizable(value):
    """Converts a value into a generator if it isn't one already"""

    return value if isinstance(value, Randomizer) else PassThroughRandomizer(value)
