# coding=utf-8

import queue

from .comm_obj import CommObj
from .endpoint import Endpoint


class SlaveEndpoint(Endpoint):

    def __init__(self, txq, rxq):
        super().__init__(txq, rxq)

    # TODO: don't block on put; should have short/zero timeout
    def send_resp(self, op_id, op_obj):
        if op_obj is None:
            raise ContractViolation('invalid argument: op_obj')
        comm_obj = CommObj(op_id, op_obj)
        self.txq.put(block=True, timeout=None, obj=comm_obj)

    # returns (op_id, op_obj) or None if empty (when block is False)
    def get_cmd(self, block):
        try:
            comm_obj = self.rxq.get(block=block, timeout=None)
            return (comm_obj.op_id, comm_obj.op_obj)
        except queue.Empty:
            return None

