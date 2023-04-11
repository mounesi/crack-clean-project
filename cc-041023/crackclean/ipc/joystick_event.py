# coding=utf-8

from enum import Enum, unique

from .op_obj import OpObj


class JoystickEvent(OpObj):

    @unique
    class Token(Enum):
        BUTTON_DOWN = 0
        POSITION = 1

    def __init__(self, token, params):
        super().__init__(token, params)

