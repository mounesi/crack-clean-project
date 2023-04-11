# coding=utf-8

from enum import Enum, unique

from .op_obj import OpObj


class DetectionResp(OpObj):

    @unique
    class Token(Enum):
        OK               = 0
        ERROR            = 1
        TRUE             = 2
        FALSE            = 3
        DETECTION_RESULT = 4

    def __init__(self, token, params):
        super().__init__(token, params)

