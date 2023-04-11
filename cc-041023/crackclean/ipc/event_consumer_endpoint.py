# coding=utf-8

import queue
import time

from .comm_obj import CommObj
from .endpoint import Endpoint


class EventConsumerEndpoint(Endpoint):

    def __init__(self, rxq):
        super().__init__(None, rxq)

    def check_for_event(self):
        try:
            comm_obj = self.rxq.get(block=False)
            return comm_obj.op_obj
        except queue.Empty:
            pass
        return None

