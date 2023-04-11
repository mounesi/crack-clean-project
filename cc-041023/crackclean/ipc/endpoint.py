# coding=utf-8

from abc import ABC, abstractmethod
import queue
import time

from ..const import Const


class Endpoint(ABC):

    @abstractmethod
    def __init__(self, txq, rxq):
        self.txq = txq
        self.rxq = rxq

    @staticmethod
    def shutdown_queue(q):
        time.sleep(Const.ENDPOINT_QUEUE_SHUTDOWN_DELAY_S)
        while True:
            try:
                q.get(block=False)
            except queue.Empty:
                break
        q.close()
        q.join_thread()

