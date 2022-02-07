import random

from majormode.utils.namegen import NameGeneratorFactory, NameGenerator

from data_generator.randomizers import primitive


class NameRandomizer(primitive.Randomizer):
    """Generates a name string"""

    _NAME_FACTORY_LOOKUP = dict(
        zip(
            [str(language) for language in NameGeneratorFactory.Language],
            NameGeneratorFactory.Language,
        )
    )

    def __init__(self, language="Hebrew", minSyllables=2, maxSyllables=4):

        super().__init__()

        assert (
            minSyllables <= maxSyllables
        ), "minimum syllable count must be less than or equal to maximum syllable count"

        # Create list of name generator classes
        self._nameFactories = dict(
            [(str(lang), None) for lang in NameGeneratorFactory.Language]
        )

        self._language = primitive.randomizable(language)
        self._minSyllables = primitive.randomizable(minSyllables)
        self._maxSyllables = primitive.randomizable(maxSyllables)

    def next(self, data=None):
        language = self._language.next(data)
        name_generator = self._get_language_generator(language)
        name_generator.min_syl = self._minSyllables.next(data)
        name_generator.max_syl = self._maxSyllables.next(data)

        return name_generator.generate_name(True)

    def _get_language_generator(self, language):
        # Instantiate name generator if one for that language has not been already been instantiated
        name_generator = self._nameFactories.get(language)

        if name_generator is None:
            name_generator = self._nameFactories[language] = self._instantiate(
                language
            )

        return name_generator

    @classmethod
    def _instantiate(cls, language):
        return NameGeneratorFactory.get_instance(cls._NAME_FACTORY_LOOKUP[language])

    def info(self):
        return {
            "type": "NameRandomizer",
            "language": self._language.info(),
            "min_syllables": self._minSyllables.info(),
            "max_syllables": self._maxSyllables.info(),
        }


class SequenceRandomizer(primitive.Randomizer):
    """Generates incrementing integers"""

    def __init__(self, start, stop=None, step=1):
        super().__init__()

        self._previous = None
        self._start = primitive.randomizable(start)
        self._step = primitive.randomizable(step)
        self._stop = primitive.randomizable(stop)

    def next(self, data=None):
        if self._previous is None:  # If first time running increment
            return self._next_first(data)
        else:
            return self._next_subsequent(data)

    def _next_first(self, data=None):
        self._previous = self._start.next(data)

        return self._previous

    def _next_subsequent(self, data=None):
        step = self._step.next(data)
        stop = self._stop.next(data)
        value = self._previous + step

        if self._time_to_start_over(value, stop, step):
            return self._next_first(data)
        else:
            return value

    def _time_to_start_over(self, value, stop, step):
        return stop is not None and (
            (step > 0 and value > stop) or (step < 0 and value < stop)
        )

    def info(self):
        return {
            "type": "IncrementGenerator",
            "start": self._start.info(),
            "step": self._step.info(),
            "stop": self._stop.info(),
        }


class DictRandomizerFactory:
    @staticmethod
    def get_dict_randomizer(key_values=None):
        if isinstance(key_values, primitive.Randomizer):
            return DictRandomizer(key_values)
        else:
            return DictFromListRandomizer(key_values)
    

class DictRandomizerInterface(primitive.Randomizer):
    def info(self):
        return {
            "type": "DictRandomizer",
            "items": self._iteminfo(),
        }
    
    def _item_info(self):
        return list(
            [{"key": k.info(), "value": v.info()} for v, k in self._key_values]
        )

class DictRandomizer(DictRandomizerInterface):
    """ "Generates key-value pairs from a list randomizer"""

    def __init__(self, key_value_randomizer: primitive.Randomizer):
        super().__init__()

        self._key_value_randomizer = key_value_randomizer

    def next(self, data=None):
        key_values = self._key_value_randomizer.next(data)
        non_null_key_values = filter(value is not None for _, value in key_values)
        return dict(non_null_key_values)
    
    def _item_info(self):
        return self._key_value_randomizer.info()


class DictFromListRandomizer(DictRandomizerInterface):
    """Generates key-value pairs from a list of tuples"""

    def __init__(self, key_values):
        super().__init__()

        print([(key, value) for key, value in key_values])

        self._key_values = (
            (primitive.randomizable(key), primitive.randomizable(value))
            for key, value in key_values
        )

    def next(self, data=None) -> dict:
        self._next_dict = dict()
        self._setDictEntries(data)
        return self._next_dict
    
    def _setDictEntries(self, data):
        for key_randomizer, value_randomizer in self._key_values:
            self._setDictEntry(key_randomizer, value_randomizer, data)
    
    def _setDictEntry(self, key_randomizer, value_randomizer, data):
        key = key_randomizer.next(data)
        value = value_randomizer.next(data)

        if value is not None:
            self._next_dict[key] = value


class SampleRandomizer(primitive.Randomizer):
    """Random list sampler"""

    def __init__(self, randomizers, min_size, max_size):
        super().__init__()
        self._randomizers = randomizers
        self._min_size = primitive.randomizable(min_size)
        self._max_size = primitive.randomizable(max_size)

    def next(self, data=None):
        min_size = self._min_size.next(data)
        max_size = self._min_size.next(data)
        count = random.randint(min_size, max_size)

        return self._getSampleList(count, data)

    def _getSampleList(self, count, data=None):
        return list(
            [
                randomizer.next(data)
                for randomizer in random.sample(self._randomizers, k=count)
            ]
        )

    def info(self):
        return {
            "type": "SampleRandomizer",
            "min": self._min_size.info(),
            "max": self._max_size.info(),
            "data": list([g.info() for g in self._randomizers]),
        }


class ChoiceRandomizer(primitive.Randomizer):
    """Random element selector"""

    _DEFAULT_WEIGHT = primitive.PassThroughRandomizer(1)

    def __init__(self, randomizers=None, weights=None):
        super().__init__()

        self._randomizers = randomizers
        self._setWeights(weights)
    
    def _setWeights(self, weights=None):
        if weights is None:
            self._setDefaultWeights()
        else:
            self._setProvidedWeights(weights)

    def _setDefaultWeights(self):
        self._weights = [self._DEFAULT_WEIGHT] * len(self._randomizers)
    
    def _setProvidedWeights(self, weights):
        self._weights = [primitive.randomizable(w) for w in weights]

    def next(self, data: dict = None):
        weights = [w.next(data) for w in self._weights]
        randomizer = random.choices(self._randomizers, weights=weights, k=1)
        return randomizer[0].next(data)

    def info(self):
        return {
            "type": "ChoiceGenerator",
            "items": self._getWeightInfo(),
        }

    def _getWeightInfo(self):
        return [
            {"weight": weight, "value": randomizer}
            for weight, randomizer in self._getWeightRandomizerTuples()
        ]

    def _getWeightRandomizerTuples(self):
        return zip(
            [w.info() for w in self._weights],
            [g.info() for g in self._randomizers],
        )
