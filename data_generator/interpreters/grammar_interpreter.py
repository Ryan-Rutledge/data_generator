from dataclasses import dataclass
from functools import reduce
import os

from arpeggio.cleanpeg import ParserPEG
from arpeggio import PTNodeVisitor, visit_parse_tree

from data_generator.randomizers import *
from data_generator.interpreters.interpeter_interface import InterpreterInterface


@dataclass
class RandomizerWrapper(Randomizer):
    """Passes method calls to a Randomizer instance and records output on a stack"""

    randomizer: Randomizer

    def __post_init__(self):
        self.stack = []

    def next(self, data=None):
        value = self.randomizer.next(data)
        self.stack.append(value)
        return value
    
    def has_stack(self):
        return len(self.stack) == 0

    def info(self):
        return self.randomizer.info()

@dataclass
class RandomizerPointer(Randomizer):
    """Simulates running a Randomizer by accessing a RadomizerWrapper stack"""

    wrapper: RandomizerWrapper

    def next(self, data=None):
        self._get_next_if_missing_stack()
        return self.wrapper.stack[-1]

    def _get_next_if_missing_stack(self, data):
        if not self.wrapper.has_stack():
            self.wrapper.next(data)
    
    def info(self):
        return {
            'type': 'Pointer',
            'target': self.wrapper.info()
        }

@dataclass
class ParseString:
    """Stores info about a string matched by the grammar"""

    format_string: str
    pointers: list[RandomizerWrapper]

    @classmethod
    def extract_format_string(cls, children):
        format_list = (
            "{}" if cls._is_randomizer(child) else child for child in children
        )
        return "".join(format_list)

    @staticmethod
    def _is_randomizer(x):
        return isinstance(x, Randomizer)

    @classmethod
    def extract_pointers(cls, children):
        return list(filter(cls._is_randomizer, children))


class ParserVisitor(PTNodeVisitor):
    _OUTPUT_KEY = "__OUTPUT__"

    def __init__(self):
        super().__init__()

        self.randomizers = dict()

    def visit_WS(self, node, children):
        return None

    def visit_NL(self, node, children):
        return None

    def visit_NWS(self, node, children):
        return None

    def visit_SOL(self, node, children):
        return None

    def visit_EOL(self, node, children):
        return None
    
    def visit_caller(self, node, children):
        randomizer_name = children[0]
        return self._get_existing_randomizer(randomizer_name)

    def visit_pointer(self, node, children):
        randomizer_name = children[0]
        randomizer = self._get_existing_randomizer(randomizer_name)
        return RandomizerPointer(randomizer)
    
    def _get_existing_randomizer(self, name):
        return self.randomizers[name]

    def visit_short_string(self, node, children):
        format_string = ParseString.extract_format_string(children)
        pointers = ParseString.extract_pointers(children)
        return ParseString(format_string, pointers)

    def visit_long_string_segment(self, node, children):
        return children[0]

    def visit_long_string(self, node, children):
        format_string = self._join_short_strings(children)
        pointers = self._join_short_string_pointers(children)
        return ParseString(format_string, pointers)

    def _join_short_strings(self, children):
        format_strings = [child.format_string for child in children]
        return "\n".join(format_strings)

    def _join_short_string_pointers(self, children):
        return reduce(lambda c1, c2: c1 + c2.pointers, children, [])

    def visit_string(self, node, children):
        return self._make_string_randomizer(children)
    
    def _make_string_randomizer(self, children):
        string_data = children[0]
        return StringRandomizer(string_data.format_string, *string_data.pointers)

    def visit_string_argument(self, node, children):
        return self._make_string_randomizer(children)

    def visit_list(self, node, children):
        return ChoiceRandomizer(children)
    
    def visit_repeater(self, node, children):
        reps, content = children
        repeater = RepeatRandomizer(content, reps)
        return FunctionRandomizer(''.join, repeater)
    
    def visit_integer(self, node, children):
        return int(node.value)
    
    def visit_randomizer_name(self, node, children):
        return node.value

    def visit_randomizer(self, node, children):
        return children[0]

    def visit_randomizer_declaration(self, node, children):
        randomizer_name, randomizer = children
        self.randomizers[randomizer_name] = RandomizerWrapper(randomizer)
        return randomizer_name, randomizer

    def visit_root_node(self, node, children):
        return self._get_output_randomizer()

    def _get_output_randomizer(self):
        return self.randomizers.get(self._OUTPUT_KEY)


class GrammarInterpreter(InterpreterInterface):
    GRAMMAR_FILE = "grammar.peg"
    GRAMMAR_ROOT = "root_node"

    def __init__(self, source):
        super().__init__(source)

        self._grammar_text = self._fetch_grammar_text()
        self._parser = self._fetch_parser()
        self._parse_tree = self._fetch_parse_tree()
        self._randomizer = self._parse_source()

    def _fetch_grammar_text(self):
        current_dir = os.path.dirname(__file__)
        filename = os.path.join(current_dir, self.GRAMMAR_FILE)

        with open(filename) as file:
            grammar_text = file.read()

        return grammar_text

    def _fetch_parser(self):
        return ParserPEG(self._grammar_text, self.GRAMMAR_ROOT, ws="")

    def _fetch_parse_tree(self):
        return self._parser.parse(self.source)

    def _parse_source(self):
        return visit_parse_tree(self._parse_tree, ParserVisitor())

    def interpret(self):
        return self._randomizer
