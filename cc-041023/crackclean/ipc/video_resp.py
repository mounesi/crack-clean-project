# coding=utf-8

from enum import Enum, unique

from .op_obj import OpObj


class VideoResp(OpObj):

    @unique
    class Token(Enum):
        OK         = 0
        ERROR      = 1
        TRUE       = 2
        FALSE      = 3
        LATEST_IMG = 4

    def __init__(self, token, params):
        super().__init__(token, params)

