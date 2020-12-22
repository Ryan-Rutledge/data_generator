import itertools
import random
import re
from majormode.utils.namegen import NameGeneratorFactory


class StringGenerator:
    """Dict value manipulator and fake data generator"""

    _field_regex = re.compile(r'\[(?P<field>\w+?)]')
    _name_regex = re.compile(r'{{2}name:(?P<language>\w+?)(?::(?P<min>\d+):(?P<max>\d+))?}{2}')

    def __init__(self):
        # Dict of language names and their corresponding generators
        self.name_generators = dict(zip(
            [str(language) for language in NameGeneratorFactory.Language],
            [NameGeneratorFactory.get_instance(language) for language in NameGeneratorFactory.Language]
        ))

    def sub(self, key, data):
        """Replace placeholder text in data dict"""

        # Generate names
        data[key] = self._name_regex.sub(self._sub_name, data[key])

        # Replace field references
        data[key] = self._field_regex.sub(lambda m: data.get(m.groups()[0]), data[key])

    def _sub_name(self, match):
        """Replace name generator language regex match with random name"""

        groups = match.groupdict()
        language = groups['language']
        generator = self.name_generators.get(language)

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


class DataGenerator:
    """Arbitrary data generator"""

    _conditional_field_regex = re.compile(r'^(?P<not>!)?\[(?P<field>.*)](?:=(?P<value>.*))?$')

    _repeat_field_regex = re.compile(r'^(?P<field>.+)(?P<condition>[*+])(?:(?P<min>\d+)(?:-(?P<max>\d+))?)?$')
    _hidden_field_regex = re.compile(r'^_.+$')

    def __init__(self, model):
        self.data_model = model
        self.string_generator = StringGenerator()

    def __iter__(self):
        while True:
            yield next(self)

    def __next__(self):
        return self._generate_object()

    def _generate_object(self, model=None):
        """Generate a dict of random data"""

        data_model = self.data_model if model is None else model
        data = {}

        # Generate random data for each field
        for field, val in data_model.items():
            self._generate_info(field, val, data)

        self._clean_data(data)

        return data

    def _clean_data(self, data):
        """Replace placeholder text and applies post-generation cleanup"""

        hidden_fields = []
        for key in data.keys():
            # Substitute placeholders
            if isinstance(data[key], str):
                self.string_generator.sub(key, data)

            # Record field to be removed if it's marked as hidden
            if self._hidden_field_regex.match(key):
                hidden_fields.append(key)

        # Remove hidden fields
        for hidden_field in hidden_fields:
            del data[hidden_field]

    def _generate_info(self, key, model, data):
        """Generate model data and adds it to data[key]"""

        repeating_field_match = self._repeat_field_regex.match(key)

        if repeating_field_match:
            # Generate a self-contained list of random data
            groups = repeating_field_match.groupdict()
            field, condition = groups['field'], groups['condition']
            min_reps, max_reps = groups['min'], groups['max']
            reps = random.randint(int(min_reps), int(max_reps or min_reps))

            data[field] = []
            if condition == '+':
                # Generate a non-repeating list (requires list)
                for sub_model in random.sample(model, reps):
                    self._generate_list_item(field, sub_model, data)
            else:
                # Generate a completely random list
                for _ in range(reps):
                    self._generate_list_item(field, model, data)
        else:
            self._generate_from_unknown(key, model, data)

    def _generate_list_item(self, key, model, data):
        """Appends a list item to data"""

        sub_data = {}
        self._generate_from_unknown(key, model, sub_data)
        data[key].append(sub_data[key])

    def _generate_from_unknown(self, key, model, data):
        """Evaluate model and recursively generate data based on attributes"""

        if isinstance(model, list):
            self._generate_from_list(key, model, data)
        elif isinstance(model, dict):
            self._generate_from_dict(key, model, data)
        elif model is not None:
            data[key] = model

    def _generate_from_list(self, key, model, data):
        """Randomly select a list item"""

        is_weighted = len(model) > 1 and\
            model[0] is not None and\
            len(model[0]) == 2 and\
            isinstance(model[0][1], (int, float))

        if is_weighted:
            population, weights = itertools.zip_longest(*model, fillvalue=1)
            random_value = random.choices(population, weights, k=1)
        else:
            random_value = random.choice(model)

        self._generate_info(key, random_value, data)

    def _generate_from_dict(self, key, model, data):
        """Extract fields from dictionary if condition is met"""

        conditional_field_match = self._conditional_field_regex.match(key)
        if conditional_field_match is not None:
            groups = conditional_field_match.groupdict()
            reverse_condition = bool(groups.get('not'))
            reference_field = data.get(groups.get('field'))
            value = groups.get('value')
            condition_met = reference_field is not None and (value is None or value == reference_field)

            if reverse_condition ^ condition_met:
                for inner_key, inner_val in model.items():
                    self._generate_info(inner_key, inner_val, data)
        else:
            data[key] = self._generate_object(model)
