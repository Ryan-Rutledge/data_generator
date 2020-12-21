import faker
import itertools
import json
import random
import re
import sys
from majormode.utils.namegen import NameGeneratorFactory


class DataGenerator:
    """Arbitrary data generator"""

    _field_regex = re.compile(r'{{2}(?P<field>\w+?)}{2}')
    _faker_regex = re.compile(r'{{2}faker:(?P<function>\w+?)}{2}')
    _namegen_regex = re.compile(r'{{2}namegen:(?P<language>\w+?)}{2}')

    def __init__(self, data):
        self.data = data

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
        rows = {}
        for key, val in self.data.items():
            # Generate fields
            rows[key] = self._generate_from(val)

            # Generate faker strings
            rows[key] = self._faker_regex.sub(lambda m: str(getattr(self.fake, m.groups()[0])()), rows[key])

            # Generate names
            rows[key] = self._namegen_regex.sub(lambda m: self.namegen.get(m.groups()[0]).generate_name(), rows[key])

            # Replace field references
            rows[key] = self._field_regex.sub(lambda m: rows.get(m.groups()[0]), rows[key])

        return rows

    def _generate_from(self, data):
        if isinstance(data, list):
            return self._generate_from_list(data)
        else:
            return data

    def _generate_from_list(self, data):
        is_weighted = len(data) > 1 and len(data[0]) == 2 and isinstance(data[0][1], (int, float))

        if is_weighted:
            population, weights = itertools.zip_longest(*data, fillvalue=1)
            random_value = random.choices(population, weights, k=1)
        else:
            random_value = random.choice(data)

        return self._generate_from(random_value)


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
