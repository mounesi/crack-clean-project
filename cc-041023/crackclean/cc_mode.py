# coding=utf-8

from enum import Enum, unique


@unique
class CcMode(Enum):
    MANUAL = 0
    AUTO = 1

    def __str__(self):
        return self.name

