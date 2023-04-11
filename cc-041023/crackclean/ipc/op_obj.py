# coding=utf-8

from abc import ABC, abstractmethod


class OpObj(ABC):

    @abstractmethod
    def __init__(self, token, params):
        self._token = token
        self._params = params

    @property
    #@abstractmethod
    def token(self):
        return self._token

    @property
    #@abstractmethod
    def params(self):
        return self._params

