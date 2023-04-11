# coding=utf-8

from enum import Enum, unique


@unique
class FilterMode(Enum):
    SIMPLE = 0
    ADAPTIVE = 1

    def __str__(self):
        return self.name

