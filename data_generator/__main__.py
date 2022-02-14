import sys

from data_generator.interpreters.grammar_interpreter import GrammarInterpreter


class DataGenerator:
    DEFAULT_SOURCE = "models/model.txt"

    def __init__(self):
        self._config_path, self._row_count = self._fetch_cmdline_args()
        self._config = self._fetch_randomizer_config()
        self._randomizer = self._fetch_randomizer()

    def _fetch_cmdline_args(self):
        assert len(sys.argv) <= 2, "Too many args"

        config_path = self._fetch_config_path_arg()
        row_count = self._fetch_row_count_arg()

        return config_path, row_count

    def _fetch_config_path_arg(self):
        return sys.argv[1] if len(sys.argv) > 1 else self.DEFAULT_SOURCE

    def _fetch_row_count_arg(self):
        return int(sys.argv[2]) if len(sys.argv) > 2 else 1

    def _fetch_randomizer_config(self):
        with open(self._config_path) as config_file:
            return config_file.read()

    def _fetch_randomizer(self):
        return GrammarInterpreter(self._config).interpret()

    def generate(self):
        for _ in range(self._row_count):
            print(self._generate(), end='')

    def _generate(self):
        return next(self._randomizer)


if __name__ == "__main__":
    DataGenerator().generate()
