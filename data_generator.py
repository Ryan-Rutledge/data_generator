import random
import re
from abc import ABCMeta, abstractmethod
from majormode.utils.namegen import NameGeneratorFactory


class BasicNode(metaclass=ABCMeta):
    """Abstract node for creating traversable generator models"""

    def __init__(self, conditions=None):
        self.conditions = conditions or []

    def __iter__(self):
        while True:
            yield next(self)

    @abstractmethod
    def __next__(self):
        pass

    def meets_conditions(self, data):
        for condition in self.conditions:
            if not condition(data):
                return False
        return True


class WrapperNode(BasicNode):
    """Applies arbitrary functionality to a contained node"""

    def __init__(self, node=None, conditions=None):
        super().__init__(conditions)
        self.node = node

    def __next__(self):
        return next(self.node)


class NamedNode(WrapperNode):
    """Applies a name to a node"""

    def __init__(self, name, node=None, conditions=None):
        super().__init__(node, conditions)
        self.name = name


class RepeaterNode(WrapperNode):
    """Generate data an arbitrary number of times"""

    def __init__(self, node=None, reps=None, conditions=None):
        super().__init__(node, conditions)

        if reps is None:
            reps = (1, 1)
        elif isinstance(reps, int):
            reps = (reps, reps)

        self.min_reps, self.max_reps = reps

    def __next__(self):
        reps = random.randint(self.min_reps, self.max_reps)
        return [next(self.node) for _ in range(reps)]


class StringGenerator(BasicNode):
    """Random string generator"""

    _field_regex = re.compile(r'\[(?P<field>\w+?)]')
    _name_regex = re.compile(r'{{2}name:(?P<language>\w+?)(?::(?P<min>\d+):(?P<max>\d+))?}{2}')

    _name_generators = dict(zip(
        [str(language) for language in NameGeneratorFactory.Language],
        [NameGeneratorFactory.get_instance(language) for language in NameGeneratorFactory.Language]
    ))

    def __init__(self, string, conditions=None):
        super().__init__(conditions)
        self.model_string = string

    def __next__(self):
        data = self.model_string
        data = self._name_regex.sub(self._sub_name, data)
        return data

    @classmethod
    def _sub_name(cls, match):
        """Replace name generator language regex match with random name"""

        groups = match.groupdict()
        language = groups['language']
        generator = cls._name_generators.get(language)

        if generator is not None:
            # Use minimum and maximum syllables if they are provided
            min_syl, max_syl = generator.min_syl, generator.max_syl
            if groups['min'] and groups['max']:
                generator.min_syl = int(groups['min'])
                generator.max_syl = int(groups['max'])

            name = generator.generate_name()

            # Return syllable counts back to defaults
            generator.min_syl, generator.max_syl = min_syl, max_syl

            return name


class SelectionGenerator(BasicNode, metaclass=ABCMeta):
    """Random list selection node"""

    def __init__(self, choices, min_size=1, max_size=1, conditions=None):
        super().__init__(conditions)
        self.min_size, self.max_size = min_size, max_size
        self.choices = choices

    def __next__(self):
        count = random.randint(self.min_size, self.max_size)
        selection = self._selection(count)
        data = list([next(d) for d in selection])
        return self._list_or_element(data)

    @abstractmethod
    def _selection(self, count):
        pass

    def _list_or_element(self, items):
        return items[0] if self.min_size == 1 and self.max_size == 1 else items


class SampleGenerator(SelectionGenerator):
    """Random elements sampler"""

    def _selection(self, count):
        return random.sample(self.choices, k=count)


class ChoiceGenerator(SelectionGenerator):
    """Random elements chooser"""

    def __init__(self, choices, weights=None, min_size=1, max_size=1, conditions=None):
        super().__init__(choices, min_size, max_size, conditions)

        # Default all weights to 1
        self.weights = weights or [1]*len(self.choices)

    def _selection(self, count):
        return random.choices(self.choices, weights=self.weights, k=count)


class DictGenerator(BasicNode):
    """Arbitrary dict generator"""

    def __init__(self, nodes=None, conditions=None):
        super().__init__(conditions)
        self.nodes = nodes or []

    def __next__(self):
        data = {}

        for node in self.nodes:
            if node.meets_conditions(data):
                data[node.name] = next(node)

        return data


class DataGeneratorModel:
    def __init__(self, root_node):
        self.root = root_node

    def __iter__(self):
        while True:
            yield next(self)

    @abstractmethod
    def __next__(self):
        return next(self.root)


class DataGenerator:
    def __init__(self, model):
        self.model = model

    def __iter__(self):
        while True:
            yield next(self)

    @abstractmethod
    def __next__(self):
        return next(self.model)
