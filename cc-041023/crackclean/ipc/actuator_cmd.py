# coding=utf-8

from enum import Enum, unique

from .op_obj import OpObj


class ActuatorCmd(OpObj):

    @unique
    class Token(Enum):
        TERMINATE     = 0
        IS_READY      = 1
        GET_TARGET_MM = 2
        SET_TARGET_MM = 3
        STOP_MOTOR    = 4

    def __init__(self, token, params):
        super().__init__(token, params)

