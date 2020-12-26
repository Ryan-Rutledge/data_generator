import random
from abc import ABCMeta, abstractmethod
from majormode.utils.namegen import NameGeneratorFactory, NameGenerator
from typing import Any, Union


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

        self._start = to_generator(start)
        self._stop = to_generator(stop)
        self._step = to_generator(step)

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

        self._start = to_generator(start)
        self._stop = to_generator(stop)
        self._precision = to_generator(precision)

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


class NameMaker(BaseGenerator):
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
        self._language = to_generator(language)

    def syllables(self, min_syl: Union[int, BaseGenerator], max_syl: Union[int, BaseGenerator]) -> None:
        self._min_syl = to_generator(min_syl)
        self._max_syl = to_generator(max_syl)

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


class IncrementGenerator(BaseGenerator):
    """Generates incrementing integers"""

    def __init__(self,
                 start: Union[int, BaseGenerator],
                 stop: Union[int, float, BaseGenerator] = None,
                 step: Union[int, float, BaseGenerator] = 1):

        super().__init__()
        self.range(start, stop, step)

    def range(self,
              start: Union[int, float, BaseGenerator],
              step: Union[int, float, BaseGenerator] = 1,
              stop: Union[int, float, BaseGenerator] = None,
              ) -> None:

        self._previous = None
        self._start = to_generator(start)
        self._step = to_generator(step)
        self._stop = to_generator(stop)

    def generate(self, data: dict = None) -> int:
        value = None

        if self._previous is None:  # If first time running increment
            value = self._previous = self._start.generate(data)
        else:
            step = self._step.generate(data)

            if step is not None:  # Step of None indicates generator is done incrementing
                stop = self._stop.generate(data)
                value = self._previous + step

                # If generator has incremented/decremented past stopping point
                if stop is not None and ((step > 0 and value > stop) or (step < 0 and value < stop)):
                    self._step = NoneGenerator  # Stop generating
                    value = None
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


def to_generator(value: Any) -> BaseGenerator:
    """Convert a value into a generator if it isn't one already"""

    return value if isinstance(value, BaseGenerator) else ValueGenerator(value)
