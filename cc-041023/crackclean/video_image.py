# coding=utf-8

from .exceptions import ContractViolation


class VideoImage(object):

    # img and timestamp must both be either non-None or None
    def __init__(self, img, timestamp):
        if ((img is None) != (timestamp is None)):
            raise ContractViolation('invalid argument: img/timestamp')
        self.img = img
        self.timestamp = timestamp

    def is_empty(self):
        return (self.img is None)

