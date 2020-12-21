import faker
import itertools
import json
import random
import re
import sys
from majormode.utils.namegen import NameGeneratorFactory


class DataGenerator:
    """Arbitrary data generator"""

    _field_regex = re.compile(r'\[(?P<field>\w+?)]')
    _faker_regex = re.compile(r'{{2}faker:(?P<function>\w+?)}{2}')
    _namegen_regex = re.compile(r'{{2}namegen:(?P<language>\w+?)}{2}')

    _conditional_regex = re.compile(r'(?P<not>!)?\[(?P<field>.*)](?:=(?P<condition>.*))?')

    def __init__(self, model):
        self.data_model = model

        self.fake = faker.Faker()

        # Dict of language names and their corresponding generators
        self.namegen = dict(zip(
            [str(language) for language in NameGeneratorFactory.Language],
            [NameGeneratorFactory.get_instance(language) for language in NameGeneratorFactory.Language]
        ))

        for generator in self.namegen.values():
            generator.min_syl = 3
            generator.max_syl = 8

    def __iter__(self):
        while True:
            yield next(self)

    def __next__(self):
        return self.generate()

    def generate(self):
        data = {}
        for key, val in self.data_model.items():
            self._generate_from(key, val, data)

        for key in data.keys():
            if isinstance(data[key], str):
                # Generate faker strings
                data[key] = self._faker_regex.sub(
                    lambda m: str(getattr(self.fake, m.groups()[0])()), data[key])

                # Generate names
                data[key] = self._namegen_regex.sub(
                    lambda m: self.namegen.get(m.groups()[0]).generate_name(), data[key])

                # Replace field references
                data[key] = self._field_regex.sub(
                    lambda m: data.get(m.groups()[0]), data[key])

        return data

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

        self._generate_from(key, random_value, data)

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
                    self._generate_from(inner_key, inner_val, data)


def main():
    if len(sys.argv) != 3:
        raise Exception('Wrong number of args')

    config_path, row_count = sys.argv[1], int(sys.argv[2])

    with open(config_path) as config_file:
        config = json.load(config_file)

    generator = DataGenerator(config)
    for i in range(row_count):
        print(json.dumps(next(generator), indent=4), '\n')


if __name__ == '__main__':
    main()
