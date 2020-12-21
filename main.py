import sys
import json


from data_generator import DataGenerator


def main():
    if len(sys.argv) > 3:
        raise Exception('Too many args')

    config_path = sys.argv[1] if len(sys.argv) > 1 else 'model.json'
    row_count = int(sys.argv[2]) if len(sys.argv) > 1 else 1

    with open(config_path) as config_file:
        config = json.load(config_file)

    generator = DataGenerator(config)
    for i in range(row_count):
        print(json.dumps(next(generator), indent=4), '\n')


if __name__ == '__main__':
    main()
