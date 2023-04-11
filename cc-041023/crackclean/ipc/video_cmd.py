# coding=utf-8

from enum import Enum, unique

from .op_obj import OpObj


class VideoCmd(OpObj):

    @unique
    class Token(Enum):
        TERMINATE      = 0
        IS_READY       = 1
        GET_LATEST_IMG = 2

    def __init__(self, token, params):
        super().__init__(token, params)

