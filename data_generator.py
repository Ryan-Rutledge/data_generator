import faker
import itertools
import random
import re
from majormode.utils.namegen import NameGeneratorFactory


class StringGenerator:
    """Replaces placeholder text in strings with generated data"""

    _field_regex = re.compile(r'\[(?P<field>\w+?)]')
    _faker_regex = re.compile(r'{{2}faker:(?P<function>\w+?)}{2}')
    _namegen_regex = re.compile(r'{{2}namegen:(?P<language>\w+?)(?::(?P<min>\d+):(?P<max>\d+))?}{2}')

    def __init__(self):
        self.fake = faker.Faker()

        # Dict of language names and their corresponding generators
        self.namegen = dict(zip(
            [str(language) for language in NameGeneratorFactory.Language],
            [NameGeneratorFactory.get_instance(language) for language in NameGeneratorFactory.Language]
        ))

    def sub(self, key, data):
        """Replace placeholder text in data dict"""

        # Generate faker strings
        data[key] = self._faker_regex.sub(self._sub_faker, data[key])

        # Generate names
        data[key] = self._namegen_regex.sub(self._sub_namegen, data[key])

        # Replace field references
        data[key] = self._field_regex.sub(lambda m: data.get(m.groups()[0]), data[key])

    def _sub_faker(self, match):
        func_name = match.groupdict()['function']
        func = getattr(self.fake, func_name)
        return str(func())

    def _sub_namegen(self, match):
        groups = match.groupdict()
        language = groups['language']
        generator = self.namegen.get(language)

        if generator is not None:
            # Change minimum and maximum syllables if they are provided
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

    _conditional_regex = re.compile(r'^(?P<not>!)?\[(?P<field>.*)](?:=(?P<condition>.*))?$')
    _count_regex = re.compile(r'^(?P<field>.+)\*(?:(?P<count>\d+)|(?P<min>\d)+-(?P<max>\d+))$')
    _hidden_regex = re.compile(r'^_.+$')

    def __init__(self, model):
        self.data_model = model
        self.string_generator = StringGenerator()

    def __iter__(self):
        while True:
            yield next(self)

    def __next__(self):
        return self.generate()

    def generate(self, model=None):
        data = {}
        data_model = self.data_model if model is None else model

        for key, val in data_model.items():
            self._generate(key, val, data)

        hidden_fields = []
        for key in data.keys():
            if isinstance(data[key], str):
                self.string_generator.sub(key, data)

            # Remove fields that are denoted as hidden
            if self._hidden_regex.match(key):
                hidden_fields.append(key)

        for hidden_field in hidden_fields:
            del data[hidden_field]

        return data

    def _generate(self, key, model, data):
        # Check if generator should generate an array
        count_match = self._count_regex.match(key)
        if count_match:
            match_groups = count_match.groupdict()
            field = match_groups['field']
            count = match_groups['count']

            if count is None:
                min_count = int(match_groups['min'])
                max_count = int(match_groups['max'])
                count = random.randint(min_count, max_count)

            data[field] = []
            for i in range(int(count)):
                sub_data = self.generate(model)
                data[field].append(sub_data)
        else:
            self._generate_from(key, model, data)

    def _generate_from(self, key, model, data):
        if isinstance(model, list):
            self._generate_from_list(key, model, data)
        elif isinstance(model, dict):
            self._generate_from_dict(key, model, data)
        elif model is not None:
            data[key] = model

    def _generate_from_list(self, key, model, data):
        is_weighted = len(model) > 1 and\
                      model[0] is not None and\
                      len(model[0]) == 2 and\
                      isinstance(model[0][1], (int, float))

        if is_weighted:
            population, weights = itertools.zip_longest(*model, fillvalue=1)
            random_value = random.choices(population, weights, k=1)
        else:
            random_value = random.choice(model)

        self._generate(key, random_value, data)

    def _generate_from_dict(self, key, model, data):
        conditional_field_match = self._conditional_regex.match(key)
        if conditional_field_match is not None:
            groups = conditional_field_match.groupdict()
            reverse_condition = groups.get('not')
            field = data.get(groups.get('field'))
            condition = groups.get('condition')
            condition_met = field is not None and (condition is None or condition == field)

            if reverse_condition:
                condition_met = not condition_met

            if condition_met:
                for inner_key, inner_val in model.items():
                    self._generate(inner_key, inner_val, data)
