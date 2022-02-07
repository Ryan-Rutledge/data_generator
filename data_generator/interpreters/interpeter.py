import re
from abc import ABCMeta, abstractmethod
from itertools import zip_longest

from data_generator import randomizers


class Interpreter(metaclass=ABCMeta):
    """Abstract generator interpreter for converting arbitrary information into an iterable generator"""

    def __init__(self, source):
        self.source = source

    @abstractmethod
    def interpret(self):
        """Parse source and convert into a generator"""

        pass

    @staticmethod
    def make_boolean_or(conditions):
        """Return a method that evaluates to true if any condition is true"""

        def _condition(data):
            for condition in conditions:
                if condition(data):
                    return True
            return False

        return _condition

    @staticmethod
    def make_boolean_not(condition):
        """Return a method that evaluates to the inverse of a condition"""

        def _condition(data):
            return not condition(data)

        return _condition
