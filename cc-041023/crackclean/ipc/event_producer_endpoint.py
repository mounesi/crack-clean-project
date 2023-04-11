# coding=utf-8

import queue
import time

from .comm_obj import CommObj
from ..const import Const
from .endpoint import Endpoint


class EventProducerEndpoint(Endpoint):

    def __init__(self, txq):
        super().__init__(txq, None)
        self.next_op_id = 0

    def send_event(self, op_obj):
        if op_obj is None:
            raise ContractViolation('invalid argument: op_obj')
        op_id = self.reserve_op_id()
        comm_obj = CommObj(op_id, op_obj)
        try:
            self.txq.put(block=True, timeout=Const.QUEUE_TIMEOUT_S, obj=comm_obj)
        except queue.Full:
            return False
        return True

    def reserve_op_id(self):
        op_id = self.next_op_id
        self.next_op_id += 1
        return op_id

