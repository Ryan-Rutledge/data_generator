import random
from abc import ABCMeta, abstractmethod
from typing import Any, Callable, Union


class Generator(metaclass=ABCMeta):
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


class PassThrough(Generator):
    """Generates a single arbitrary value"""

    def __init__(self, value: Any = None):
        self.value(value)

    def value(self, value: Any = None) -> None:
        """Set generated value"""

        self._value = value

    def generate(self, data: dict = None) -> Any:
        return self._value

    def info(self) -> Any:
        return self._value.__name__ + '()' if callable(self._value) else self._value


class Integer(Generator):
    """Generates integers"""

    def __init__(self,
                 start: Union[int, Generator],
                 stop: Union[int, Generator],
                 step: Union[int, Generator] = 1):

        super().__init__()
        self.range(start, stop, step)

    def range(self,
              start: Union[int, Generator],
              stop: Union[int, Generator],
              step: Union[int, Generator] = 1) -> None:

        self._start = generates(start)
        self._stop = generates(stop)
        self._step = generates(step)

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


class Float(Generator):
    """Generates floating point numbers"""

    def __init__(self, start: float, stop: float, precision: int = 1):
        super().__init__()
        self.range(start, stop, precision)

    def range(self,
              start: Union[float, Generator],
              stop: Union[float, Generator],
              precision: Union[float, Generator] = 1) -> None:

        self._start = generates(start)
        self._stop = generates(stop)
        self._precision = generates(precision)

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


class Call(Generator):
    """Generates output of an arbitrary function"""

    def __int__(self,
                function: Union[Callable, Generator],
                parameters: list = None):

        self.function(function, parameters)

    def function(self,
                 function: Union[Callable, Generator],
                 parameters: list = None) -> None:

        self._function = generates(function)
        self._parameters = [generates(p) for p in parameters]

    def generate(self, data: dict = None) -> Any:
        function = self._function.generate(data)
        parameters = [p.generate(data) for p in self._parameters]
        return function(*parameters)

    def info(self) -> Any:
        return {
            'type': 'CallGenerator',
            'function': self._function.info(),
            'parameters': [p.info for p in self._parameters]
        }


class String(Generator):
    """Arbitrary string concatenation"""

    def __init__(self, string: Union[str, Generator], *generators: Union[str, Generator]):
        super().__init__()
        self.string(string, *generators)

    def string(self, string: Union[str, Generator], *generators: Union[str, Generator]):
        self._string = generates(string)
        self._generators = [generates(g) for g in generators]

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


def generates(value: Any) -> Generator:
    """Convert a value into a generator if it isn't one already"""

    return value if isinstance(value, Generator) else PassThrough(value)
