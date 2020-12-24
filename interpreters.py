import re
from abc import ABCMeta, abstractmethod
import data_generators
from itertools import zip_longest
from typing import Callable, Any


class Interpreter(metaclass=ABCMeta):
    @abstractmethod
    def interpret(self, source: Any) -> data_generators.BaseGenerator:
        pass

    @staticmethod
    def _field_exists_logic(field_name: str, reverse: bool = False) -> Callable[[], bool]:
        """Return a method that evaluates to true when the supplied data contains field_name"""

        def condition(data):
            meets_condition = data.get(field_name) is not None
            return meets_condition ^ reverse
        return condition

    @staticmethod
    def _field_matches_logic(field_name: str, value: str, reverse: bool = False) -> Callable[[], bool]:
        """Return a method that evaluates to true when the supplied data field matches value"""

        def condition(data: dict) -> bool:
            field = data.get(field_name)
            meets_condition = field is not None and field == value
            return meets_condition ^ reverse
        return condition


class DictInterpreter(Interpreter):

    _string_generator_regex = re.compile(r'{{2}(?P<generator>\w+)(?P<parameters>(?::\w+)+?)?}{2}')
    _conditional_field_regex = re.compile(r'^(?P<not>!)?\[(?P<field>.*)](?:=(?P<value>.*))?$')
    _repeat_field_regex = re.compile(r'^(?P<field>.+)(?P<operator>[*+])(?:(?P<min>\d+)(?:-(?P<max>\d+))?)?$')
    # _hidden_field_regex = re.compile(r'^_.+$')

    @classmethod
    def interpret(cls, source: dict) -> data_generators.BaseGenerator:
        return cls._make_dict_generator(source, (1, 1), [])

    @classmethod
    def _add_field(cls,
                   field_name: str,
                   source: dict,
                   parent: data_generators.DictGenerator,
                   conditions: list[Callable[[dict], bool], ...] = None) -> None:

        new_conditions = cls._extract_conditions(field_name)
        conditions = (conditions or []) + new_conditions

        if new_conditions:
            for key, val in source.items():
                cls._add_field(key, val, parent, conditions)
        else:
            # Remove conditions from field_name
            field_name = cls._clean_condition(field_name)
            proper_name = cls._clean_repeater(field_name)
            parent.generators[proper_name] = cls._make_generator(field_name, source, conditions)

    @classmethod
    def _make_generator(cls, field_name: str, source: dict, conditions: list = None) -> data_generators.BaseGenerator:
        conditions = conditions or []
        reps = cls._get_counter(field_name, '*') or (1, 1)

        if isinstance(source, list):
            size = cls._get_counter(field_name, '+')

            if size:
                return cls._make_sample_generator(source, size, reps, conditions)
            else:
                return cls._make_choice_generator(source, reps, conditions)
        elif isinstance(source, dict):
            return cls._make_dict_generator(source, reps, conditions)
        elif isinstance(source, str):
            return cls._make_string_generator(source, reps,  conditions)
        else:
            return data_generators.NoneGenerator(reps, conditions)

    @classmethod
    def _make_dict_generator(cls,
                             source: dict,
                             reps: (int, int),
                             conditions: [Callable[[dict], bool], ...]) -> data_generators.DictGenerator:

        generator = data_generators.DictGenerator(reps=reps, conditions=conditions)
        for key, val in source.items():
            cls._add_field(key, val, generator)
        return generator

    @classmethod
    def _generate_from_list(cls, items: [Any, ...]) -> [data_generators.BaseGenerator, ...]:
        generators = []
        for sub_source in items:
            generator = cls._make_generator('', sub_source)
            generators.append(generator)

        return generators

    @classmethod
    def _make_sample_generator(cls,
                               source: list,
                               size: (int, int),
                               reps: (int, int),
                               conditions: [Callable[[dict], bool], ...]) -> data_generators.SampleGenerator:

        generators = cls._generate_from_list(source)
        return data_generators.SampleGenerator(generators, size, reps, conditions)

    @classmethod
    def _make_choice_generator(cls,
                               source: list,
                               reps: (int, int),
                               conditions: [Callable[[dict], bool], ...]) -> data_generators.ChoiceGenerator:

        def is_weighted(item):
            return isinstance(item, list) and len(item) == 2 and isinstance(item[1], (int, float))

        selection = [m if is_weighted(m) else [m, 1] for m in source]
        population, weights = zip_longest(*selection, fillvalue=1)
        generators = cls._generate_from_list(population)

        return data_generators.ChoiceGenerator(generators, weights, reps, conditions=conditions)

    @classmethod
    def _make_string_generator(cls, source, reps: (int, int), conditions: [Callable[[dict], bool], ...]):
        string_template = cls._string_generator_regex.sub('{}', source)

        generators = []
        for generator_type, args in cls._string_generator_regex.findall(source):
            generator_args = args[1:].split(':') if args else []

            if generator_type == 'name':
                generators.append(cls._make_name_generator(*generator_args))

        return data_generators.StringGenerator(string_template, generators, reps, conditions)

    @classmethod
    def _make_name_generator(cls, *args):
        language = args[0] if len(args) > 0 else 'Norse'
        min_syl = int(args[1]) if len(args) > 1 else 2
        max_syl = int(args[2]) if len(args) > 2 else 6

        return data_generators.NameGenerator(language, (min_syl, max_syl))

    @classmethod
    def _extract_conditions(cls, string: str) -> [Callable[[dict], bool], ...]:
        # TODO: Add support for multiple conditions

        conditions = []
        conditional_field_match = cls._conditional_field_regex.match(string)
        if conditional_field_match is not None:
            groups = conditional_field_match.groupdict()
            reverse = bool(groups.get('not'))
            field = groups.get('field')
            value = groups.get('value')

            if value is None:  # Check if field has a value
                condition = cls._field_exists_logic(field, reverse)
            else:
                condition = cls._field_matches_logic(field, value, reverse)

            conditions.append(condition)

        return conditions

    @classmethod
    def _clean_repeater(cls, field: str) -> str:
        proper_field = field
        repeat_match = cls._repeat_field_regex.match(field)
        if repeat_match:
            proper_field = repeat_match.groupdict()['field']

        return proper_field

    @classmethod
    def _clean_condition(cls, field: str) -> str:
        proper_field = field
        condition_match = cls._conditional_field_regex.match(field)
        if condition_match:
            proper_field = condition_match.groupdict()['field']

        return proper_field

    @classmethod
    def _get_counter(cls, string: str, operator: str) -> [(int, int), None]:
        repeating_field_match = cls._repeat_field_regex.match(string)
        if repeating_field_match:
            groups = repeating_field_match.groupdict()
            if groups['operator'] == operator:
                min_reps = int(groups.get('min', 1))
                max_reps = int(groups.get('max') or min_reps)
                return min_reps, max_reps
        return None
