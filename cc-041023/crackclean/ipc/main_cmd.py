# coding=utf-8

from enum import Enum, unique

from .op_obj import OpObj


class MainCmd(OpObj):

    @unique
    class Token(Enum):
        TERMINATE              = 0
        IS_READY               = 1
        START                  = 2
        GET_STATUS             = 3
        SET_MODE               = 4
        TOGGLE_MODE            = 5
        SET_DETECT_THRESH      = 6
        SET_SIMPFILTER_THRESH  = 7
        SET_ADAPTFILTER_RADIUS = 8
        SET_ADAPTFILTER_THRESH = 9
        SET_FILTER_MODE        = 10

    def __init__(self, token, params):
        super().__init__(token, params)

