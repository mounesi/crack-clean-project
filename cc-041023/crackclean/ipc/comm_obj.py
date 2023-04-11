# coding=utf-8


class CommObj(object):

    def __init__(self, op_id, op_obj):
        self._op_id = op_id
        self._op_obj = op_obj

    @property
    def op_id(self):
        return self._op_id

    @property
    def op_obj(self):
        return self._op_obj

