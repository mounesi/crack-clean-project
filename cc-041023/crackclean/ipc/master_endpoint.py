# coding=utf-8

import queue
import time

from ..const import Const
from .comm_obj import CommObj
from .endpoint import Endpoint


class MasterEndpoint(Endpoint):

    def __init__(self, txq, rxq):
        super().__init__(txq, rxq)
        self.resp_cache = {}
        self.next_op_id = 0

    # TODO: refactor
    #def get_resp(self, op_id, block):
    def check_for_resp(self, op_id):
        resp = self.resp_cache.pop(op_id, None)
        if resp is not None:
            return resp
        while True:
            try:
                comm_obj = self.rxq.get(block=False)
                if (comm_obj.op_id == op_id):
                    return comm_obj.op_obj
                self.resp_cache[comm_obj.op_id] = comm_obj.op_obj
            except queue.Empty:
                break
        return None

    def reserve_op_id(self):
        op_id = self.next_op_id
        self.next_op_id += 1
        return op_id

    # TODO: don't block on put; should have short/zero timeout
    def send_cmd_async(self, op_obj):
        if op_obj is None:
            raise ContractViolation('invalid argument: op_obj')
        op_id = self.reserve_op_id()
        comm_obj = CommObj(op_id, op_obj)
        self.txq.put(block=True, timeout=None, obj=comm_obj)
        return op_id

    # TODO: change the send semantics to be similar to the getresp ones
    def send_cmd_sync(self, op_obj, timeout_ms):
        ts = time.monotonic()
        op_id = self.send_cmd_async(op_obj)
        resp = self.__get_resp_timeout(op_id, timeout_ms)
        dur_ms = (time.monotonic() - ts) * 1000
        if ((resp is not None) and (dur_ms > Const.CMD_SYNC_WARN_MS)):
            print('warning: send_cmd_sync resp to ' + str(type(op_obj)) + '.' + str(op_obj.token) + ' took ' + str(dur_ms) + ' ms')
        return resp

    def __get_resp_timeout(self, op_id, timeout_ms):
        resp = self.resp_cache.pop(op_id, None)
        if resp is not None:
            return resp
        while True:
            try:
                comm_obj = self.rxq.get(block=True, timeout=(timeout_ms / 1000))
                if (comm_obj.op_id == op_id):
                    return comm_obj.op_obj
                self.resp_cache[comm_obj.op_id] = comm_obj.op_obj
            except queue.Empty:
                return None

