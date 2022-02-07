import sys
import json
import yaml
from data_generator.interpreters.interpeter import DictInterpreter


class DataGenerator:
    def __init__(self):
        self._getCommandlineArgs()
        self._setRandomizerConfig()
        self._randomizer = self._getRandomizer()

    def _getCommandlineArgs(self):
        assert len(sys.argv) <= 4, "Too many args"

        self._getConfigPathArg()
        self._getRowCountArg()
        self._getOutputFormatterArg()

    def _getConfigPathArg(self):
        self._config_path = sys.argv[1] if len(sys.argv) > 1 else "models/model.json"

    def _getRowCountArg(self):
        self._row_count = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    def _getOutputFormatterArg(self):
        output_format = sys.argv[3] if len(sys.argv) > 3 else "yaml"
        self._output_formatter = {"yaml": yaml.dump, "json": json.dumps}[output_format]

    def _setRandomizerConfig(self):
        with open(self._config_path) as config_file:
            self._config = json.load(config_file)

    def _getRandomizer(self):
        return DictInterpreter(self._config).interpret()

    def generate(self):
        for i in range(self._row_count):
            self._generate()

    def _generate(self):
        print(self._randomizer)
        random_data = next(self._randomizer)
        format_data = self._output_formatter(random_data, indent=4, sort_keys=False)
        print(format_data, end="")


if __name__ == "__main__":
    DataGenerator().generate()
