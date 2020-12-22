import sys
import json
import yaml


from data_generator import DataGenerator


def main():
    if len(sys.argv) > 4:
        raise Exception('Too many args')

    config_path = sys.argv[1] if len(sys.argv) > 1 else 'model.json'
    row_count = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    output_format = sys.argv[3] if len(sys.argv) > 3 else 'yaml'

    with open(config_path) as config_file:
        config = json.load(config_file)

    generator = DataGenerator(config)

    dump = {
        'yaml': yaml.dump,
        'json': json.dumps
    }[output_format]

    for i in range(row_count):
        print(dump(next(generator), indent=4, sort_keys=False), end='')


if __name__ == '__main__':
    main()
