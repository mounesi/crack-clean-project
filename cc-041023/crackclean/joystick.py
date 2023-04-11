# coding=utf-8

import errno
import os
import time

from .const import Const
from .exceptions import ContractViolation
from .exceptions import JoystickException


class Joystick(object):

    #from enum import Enum, unique
    #@unique
    #class EventType(Enum):
    #    BUTTON = 0
    #    AXIS   = 1

    JS_EVENT_BUTTON = (1 << 0)
    JS_EVENT_AXIS   = (1 << 1)
    JS_EVENT_INIT   = (1 << 7)

    VAL_BUTTON_RELEASE = 0x00
    VAL_BUTTON_PRESS   = 0x01

    VAL_AXIS_MAXABS = 32767

    PACKET_SIZE = 8

    class AxisEvent(object):
        def __init__(self, time_val, axis_num, val_norm):
            self.time_val = time_val
            self.axis_num = axis_num
            self.val_norm = val_norm

    class ButtonEvent(object):
        def __init__(self, time_val, btn_num, press):
            self.time_val = time_val
            self.btn_num = btn_num
            self.press = press

    def __init__(self):
        self.axes = None
        self.btns = None
        self.fd   = None

    def init(self):
        self.btns = set()
        self.axes = set()

        self.fd = Joystick.__opendev(Const.JOYSTICK_COOKED_DEV, Const.JOYSTICK_MAX_OPEN_ATTEMPTS, Const.JOYSTICK_OPEN_FAIL_SLEEP_S)
        if self.fd is None:
            raise JoystickException('failed to open joystick device')

    def deinit(self):
        if self.fd is not None:
            Joystick.__closedev(self.fd)
        del self.fd
        del self.btns
        del self.axes

    def check_for_event(self):
        buf = self.__check_for_packet()
        if buf is not None:
            return self.process_cooked(buf)		# TEMP
        return None

    @staticmethod
    def __closedev(fd):
        try:
            os.close(fd)
        except OSError as e:
            raise JoystickException('failed to close joystick device: %s' % e)

    @staticmethod
    def __opendev(dev, max_attempts, fail_sleep_s):
        fd = None
        attempts = 0
        while (attempts < max_attempts):
            try:
                fd = os.open(dev, (os.O_RDONLY | os.O_NONBLOCK))
                print('joystick device opened successfully')
                return fd
            except OSError:
                attempts += 1
                time.sleep(fail_sleep_s)
        print('failed to open joystick device after ' + str(max_attempts) + ' attempts')
        return None

    # returns None or packet
    def __check_for_packet(self):
        try:
            data = os.read(self.fd, Joystick.PACKET_SIZE)
        except OSError as e:
            if not ((e.errno == errno.EAGAIN) or (e.errno == errno.EWOULDBLOCK)):
                raise JoystickException('OSError: %s' % e)
            return None
        num = len(data)
        if (num != Joystick.PACKET_SIZE):
            raise JoystickException('read incomplete packet')
        return data

    # FIXME: still want this to be a separate func?
    # returns AxisEvent or ButtonEvent
    def process_cooked(self, data):
        if (len(data) != Joystick.PACKET_SIZE):
            raise ContractViolation('invalid argument: data')
        ev_time = int.from_bytes(data[0:4], byteorder='little')
        ev_val = int.from_bytes(data[4:6], byteorder='little', signed=True)
        ev_typeval = data[6]
        ev_num = data[7]
        is_init = ((ev_typeval & Joystick.JS_EVENT_INIT) != 0x00)
        ev_type = ev_typeval & ~(Joystick.JS_EVENT_INIT)
        if (ev_type == Joystick.JS_EVENT_BUTTON):
            if is_init:
                self.btns.add(ev_num)
            else:
                if ev_num not in self.btns:
                    raise JoystickException('received event for unknown button')
                if (ev_val == Joystick.VAL_BUTTON_RELEASE):
                    return Joystick.ButtonEvent(ev_time, ev_num, False)
                    #print(str(ev_time) + '    button ' + str(ev_num) + ' up')
                elif (ev_val == Joystick.VAL_BUTTON_PRESS):
                    return Joystick.ButtonEvent(ev_time, ev_num, True)
                    #print(str(ev_time) + '    button ' + str(ev_num) + ' down')
                else:
                    raise JoystickException('received unexpected event value')
        elif (ev_type == Joystick.JS_EVENT_AXIS):
            if is_init:
                self.axes.add(ev_num)
            else:
                if ev_num not in self.axes:
                    raise JoystickException('received event for unknown axis')
                if (abs(ev_val) > Joystick.VAL_AXIS_MAXABS):
                    raise JoystickException('received unexpected event value')
                return Joystick.AxisEvent(ev_time, ev_num, (ev_val / Joystick.VAL_AXIS_MAXABS))
                #print('axis ' + str(ev_num) + ': ' + str(ev_val))
        else:
            raise JoystickException('received event of unknown type')

