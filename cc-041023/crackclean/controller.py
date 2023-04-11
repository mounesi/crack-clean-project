# coding=utf-8

from abc import ABC, abstractmethod

from .exceptions import ContractViolation


class Controller(ABC):

    @abstractmethod
    def __init__(self, endpoint, params):
        self._endpoint = endpoint
        self._params = params

    @property
    def endpoint(self):
        return self._endpoint

    @property
    def params(self):
        return self._params

    @abstractmethod
    def init(self):
        raise ContractViolation('abstract method invoked')

    @abstractmethod
    def start(self):
        raise ContractViolation('abstract method invoked')

    @abstractmethod
    def deinit(self):
        raise ContractViolation('abstract method invoked')

