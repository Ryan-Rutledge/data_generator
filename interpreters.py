import re
from abc import ABCMeta, abstractmethod
import data_generators
from itertools import zip_longest
from typing import Any, Callable, Optional, Union


class Interpreter(metaclass=ABCMeta):
    """Abstract generator interpreter for converting arbitrary information into an iterable generator"""

    def __init__(self, source: Any):
        self.source = source

    @abstractmethod
    def interpret(self) -> data_generators.BaseGenerator:
        """Parse source and convert into a generator"""

        pass

    @staticmethod
    def _field_exists_logic(field_name: str, reverse: bool = False) -> Callable[[dict], bool]:
        """Return a method that evaluates to true when the supplied data contains field_name"""

        def _condition(data):
            meets_condition = data.get(field_name) is not None
            return meets_condition ^ reverse
        return _condition

    @staticmethod
    def _field_matches_logic(field_name: str, value: str, reverse: bool = False) -> Callable[[dict], bool]:
        """Return a method that evaluates to true when the supplied data field matches value"""

        def _condition(data: dict) -> bool:
            field = data.get(field_name)
            meets_condition = field is not None and field == value
            return meets_condition ^ reverse
        return _condition

    @staticmethod
    def _or_condition_logic(conditions: list[Callable[[dict], bool]]) -> Callable[[dict], bool]:
        """Return a method that evaluates to true if any condition is true"""

        def _condition(data: dict) -> bool:
            for condition in conditions:
                if condition(data):
                    return True
            return False
        return _condition

    @staticmethod
    def _not_condition_logic(condition: Callable[[dict], bool]) -> Callable[[dict], bool]:
        """Return a method that evaluates to the inverse of a condition"""

        def _condition(data: dict) -> bool:
            return not condition(data)
        return _condition

    @staticmethod
    def _field_gt_condition_logic(x_field: str,
                                  y_value: Union[int, float],
                                  reverse: bool = False) -> Callable[[dict], bool]:
        """Return a method that evaluates x_field > y"""

        def _condition(data: dict) -> bool:
            field = data.get(x_field)
            field = int(field) if field.isdigit() else float(field)
            meets_condition = field is not None and field > y_value
            return meets_condition ^ reverse
        return _condition


class DictInterpreter(Interpreter):
    """Abstract interpreter for converting dict objects into a DictGenerator"""

    _string_generator_regex = re.compile(r'{{2}(?P<generator>\w+)(?P<parameters>(?::.+?)+?)?}{2}')
    _conditional_field_regex = re.compile(r'^(?P<not>!)?\[(?P<field>.*)](?:(?P<operator>[=><])(?P<value>.*))?$')
    _repeat_field_regex = re.compile(r'^(?P<field>.+)(?:(?P<operator>[*+])(?:(?P<min>\d+)(?:-(?P<max>\d+))?)?)+$')
    _clean_notation_regex = re.compile(r'^(?P<field>.*?)(?=[*+])')
    # _hidden_field_regex = re.compile(r'^_.+$')

    def interpret(self) -> data_generators.Variable.DictGenerator:
        return self._make_dict_generator(self.source)

    @classmethod
    def _make_dict_generator(cls, source: dict) -> data_generators.Variable.DictGenerator:

        generator = data_generators.Variable.DictGenerator()
        for key, val in source.items():
            cls._add_field(key, val, generator)
        return generator

    @classmethod
    def _add_field(cls,
                   field_name: str,
                   source: Union[dict, list],
                   parent: data_generators.Variable.DictGenerator,
                   conditions: list[Callable[[dict], bool]] = None) -> None:

        conditions = conditions or []
        new_condition = cls._create_condition(field_name)

        if new_condition:
            # Raise fields for when conditions are true
            true_source = source[0] if isinstance(source, list) else source
            for key, val in true_source.items():
                cls._add_field(key, val, parent, conditions + [new_condition])

            # Raise fields for when conditions are false
            false_source = source[1] if isinstance(source, list) and len(source) > 1 else None
            if false_source:
                reverse_condition = cls._not_condition_logic(new_condition)
                for key, val in false_source.items():
                    cls._add_field(key, val, parent, conditions + [reverse_condition])
        else:
            proper_name = cls._make_string_generator(cls._remove_notation(field_name))
            generator = cls._make_generator(field_name, source)

            # Wrap generator in a conditional generator if there are true false
            if conditions:
                generator = data_generators.Wrapper.ConditionalGenerator(generator)
                generator.conditions(conditions)

            parent.field(generator, proper_name)

    @classmethod
    def _make_generator(cls, field_name: str, source: dict) -> data_generators.BaseGenerator:
        """Returns an arbitrary generator object"""

        field_name, min_reps, max_reps = cls._get_counter(field_name, '*')
        if isinstance(source, list):
            field_name, min_size, max_size = cls._get_counter(field_name, '+')  # Sample generator notation

            if min_size:
                generator = cls._make_sample_generator(source, min_size, max_size)
            else:
                generator = cls._make_choice_generator(source)
        elif isinstance(source, dict):
            generator = cls._make_dict_generator(source)
        elif isinstance(source, str):
            generator = cls._make_string_generator(source)
        else:
            generator = data_generators.Primitive.NoneGenerator()

        if min_reps:
            generator = data_generators.Wrapper.RepeaterGenerator(generator)
            generator.repeat(min_reps, max_reps)

        return generator

    @classmethod
    def _generate_each(cls, items: list[Any]) -> list[data_generators.BaseGenerator]:
        generators = []
        for sub_source in items:
            generator = cls._make_generator('', sub_source)
            generators.append(generator)
        return generators

    @classmethod
    def _make_sample_generator(cls,
                               source: list,
                               min_size: int = 1,
                               max_size: int = 1) -> data_generators.Variable.SampleGenerator:

        generators = cls._generate_each(source)
        return data_generators.Variable.SampleGenerator(generators, min_size, max_size)

    @classmethod
    def _make_choice_generator(cls, source: list) -> data_generators.Variable.ChoiceGenerator:
        def is_weighted(item: Any):
            return isinstance(item, list) and len(item) == 2 and isinstance(item[1], (int, float))

        # Default list items to (sub_source, 1) for calculating weights
        selection = [m if is_weighted(m) else (m, 1) for m in source]
        population, weights = zip_longest(*selection, fillvalue=1)

        generators = cls._generate_each(population)
        return data_generators.Variable.ChoiceGenerator(generators, weights)

    @classmethod
    def _make_string_generator(cls, source: str) -> data_generators.Variable.StringGenerator:
        # Add a primitive generator for each instance of string substitution notation
        substring_generators = []
        for generator_type, args in cls._string_generator_regex.findall(source):
            generator_args = args[1:].split(':') if args else []
            primitive_generator = cls._make_primitive_generator(generator_type.lower(), generator_args)
            substring_generators.append(primitive_generator)

        string_template = cls._string_generator_regex.sub('{}', source)
        string_generator = data_generators.Variable.StringGenerator(string_template, *substring_generators)
        return string_generator

    @classmethod
    def _create_condition(cls, string: str) -> Optional[Callable[[dict], bool]]:
        substrings = string.split('|')

        # Extract individual conditions within string
        conditions = []
        for substring in substrings:
            condition = cls._extract_condition(substring)
            if condition:
                conditions.append(condition)

        # If multiple conditions are found, treat them all as an "or" statement
        if len(substrings) > 1:
            return cls._or_condition_logic(conditions)
        else:
            return next(iter(conditions), None)

    @classmethod
    def _extract_condition(cls, string: str) -> Optional[Callable[[dict], bool]]:
        conditional_field_match = cls._conditional_field_regex.match(string)
        condition = None

        if conditional_field_match is not None:
            groups = conditional_field_match.groupdict()
            reverse = bool(groups.get('not'))
            field = groups.get('field')
            value = groups.get('value')
            operator = groups.get('operator')

            if value is None:  # If no match is provided, just check if field exists
                condition = cls._field_exists_logic(field, reverse)
            elif operator == '=':
                condition = cls._field_matches_logic(field, value, reverse)
            elif operator == '>':
                value = int(value) if value.isdigit() else float(value)
                condition = cls._field_gt_condition_logic(field, value, reverse)

        return condition

    @classmethod
    def _remove_notation(cls, string: str) -> str:
        match = cls._clean_notation_regex.match(string)
        return match.groups()[0] if match else string

    @classmethod
    def _get_counter(cls, string: str, operator: str) -> tuple[str, Union[int, None], Union[int, None]]:
        repeating_field_match = cls._repeat_field_regex.match(string)
        if repeating_field_match:
            groups = repeating_field_match.groupdict()
            if groups['operator'] == operator:
                min_reps = int(groups.get('min', 1))
                max_reps = int(groups.get('max') or min_reps)
                return groups['field'], min_reps, max_reps
        return string, None, None

    @classmethod
    def _make_primitive_generator(cls, generator_type: str, args: list[str]):
        if generator_type == 'name':
            return cls._make_name_generator(*args)
        elif generator_type == 'int' or generator_type == 'integer':
            return cls._make_integer_generator(*args)
        elif generator_type == 'float':
            return cls._make_float_generator(*args)
        elif generator_type == 'increment':
            return cls._make_increment_generator(*args)
        else:
            return data_generators.Primitive.NoneGenerator()

    @staticmethod
    def _make_name_generator(*args: str) -> data_generators.Primitive.NameGenerator:
        language = args[0] if len(args) > 0 else 'Norse'
        min_syl = int(args[1]) if len(args) > 1 else 2
        max_syl = int(args[2]) if len(args) > 2 else 6

        generator = data_generators.Primitive.NameGenerator(language, min_syl, max_syl)
        return generator

    @staticmethod
    def _make_integer_generator(*args: str) -> data_generators.Primitive.IntegerGenerator:
        start = int(args[0])
        stop = int(args[1])
        step = int(args[2]) if len(args) > 2 else 1

        return data_generators.Primitive.IntegerGenerator(start, stop, step)

    @staticmethod
    def _make_float_generator(*args: str) -> data_generators.Primitive.FloatGenerator:
        start = float(args[0])
        stop = float(args[1])
        precision = float(args[2]) if len(args) > 2 else 1

        return data_generators.Primitive.FloatGenerator(start, stop, precision)

    @staticmethod
    def _make_increment_generator(*args: str) -> data_generators.Primitive.IncrementGenerator:
        start = args[0] if len(args) > 0 else '1'
        step = args[1] if len(args) > 1 else '1'
        stop = args[2] if len(args) > 2 else None

        start = int(start) if start.isdigit() else float(start)
        step = int(step) if step.isdigit() else float(step)
        stop = None if stop is None else int(stop) if stop.isdigit() else float(stop)

        return data_generators.Primitive.IncrementGenerator(start, step, stop)
