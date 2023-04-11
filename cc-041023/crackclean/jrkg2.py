# coding=utf-8

from enum import Enum, unique
import serial

from .const import Const
from .exceptions import ContractViolation
from .exceptions import JrkG2Exception


class JrkG2(object):

    CRC7_POLY = 0x91

    DUMMY_USB_BAUD = 9600

    TARGET_MINVAL = 0x0000
    TARGET_MAXVAL = 0x0FFF

    CMDBYTE_GET_AND_CLEAR_ERROR_FLAGS_HALTING  = 0xB3
    CMDBYTE_GET_AND_CLEAR_ERROR_FLAGS_OCCURRED = 0xB5
    CMDBYTE_SET_TARGET_HIRES                   = 0xC0
    CMDBYTE_GET_VARIABLES                      = 0xE5
    CMDBYTE_STOP_MOTOR                         = 0xFF

    VAR_OFFSET_TARGET               = 0x02
    VAR_LENGTH_TARGET               = 2
    VAR_OFFSET_FEEDBACK             = 0x04
    VAR_LENGTH_FEEDBACK             = 2
    VAR_OFFSET_ERROR_FLAGS_HALTING  = 0x12
    VAR_LENGTH_ERROR_FLAGS_HALTING  = 2
    VAR_OFFSET_ERROR_FLAGS_OCCURRED = 0x14
    VAR_LENGTH_ERROR_FLAGS_OCCURRED = 2

    @unique
    class ErrorFlag(Enum):
        AWAITING_COMMAND      = (0b0000000000000001, 'awaiting command')
        NO_POWER              = (0b0000000000000010, 'no power')
        MOTOR_DRIVER_ERROR    = (0b0000000000000100, 'motor driver error')
        INPUT_INVALID         = (0b0000000000001000, 'input invalid ')
        INPUT_DISCONNECT      = (0b0000000000010000, 'input disconnect')
        FEEDBACK_DISCONNECT   = (0b0000000000100000, 'feedback disconnect')
        SOFT_OVERCURRENT      = (0b0000000001000000, 'soft overcurrent')
        SERIAL_SIGNAL_ERROR   = (0b0000000010000000, 'serial signal error')
        SERIAL_OVERRUN        = (0b0000000100000000, 'serial overrun')
        SERIAL_RX_BUFFER_FULL = (0b0000001000000000, 'serial RX buffer full')
        SERIAL_CRC_ERROR      = (0b0000010000000000, 'serial CRC error')
        SERIAL_PROTOCOL_ERROR = (0b0000100000000000, 'serial protocol error')
        SERIAL_TIMEOUT_ERROR  = (0b0001000000000000, 'serial timeout error')
        HARD_OVERCURRENT      = (0b0010000000000000, 'hard overcurrent')
        def mask(self):
            return self.value[0]
        def desc(self):
            return self.value[1]

    def __init__(self):
        self.crc_xor_table = JrkG2.build_crc_xor_table()
        self.serial_obj = None

    def init(self):
        baud = (Const.JRKG2_BAUD if (Const.JRKG2_BAUD is not None) else JrkG2.DUMMY_USB_BAUD)
        read_timeout_s = (Const.JRKG2_READ_TIMEOUT_MS / 1000)
        write_timeout_s = (Const.JRKG2_WRITE_TIMEOUT_MS / 1000)
        try:
            self.serial_obj = serial.Serial(
                port               = Const.JRKG2_DEV,
                baudrate           = baud,
                bytesize           = serial.EIGHTBITS,
                parity             = serial.PARITY_NONE,
                stopbits           = serial.STOPBITS_ONE,
                timeout            = read_timeout_s,
                xonxoff            = False,
                rtscts             = False,
                write_timeout      = write_timeout_s,
                dsrdtr             = False,
                inter_byte_timeout = None
            )
        except ValueError:
            raise JrkG2Exception('ValueError: %s' % e)
        except serial.SerialException as e:
            raise JrkG2Exception('SerialException: %s' % e)

    def deinit(self):
        try:
            # unclear if this can raise SerialException
            self.serial_obj.close()
        except serial.SerialException as e:
            raise JrkG2Exception('SerialException: %s' % e)
        del self.serial_obj

    def __issue_cmd(self, cmd, resp_length, inhibit_err_check=False):
        if Const.JRKG2_CRC_ENABLED:
            crc = self.calc_crc(cmd)
            self.__send(cmd + crc)
        else:
            self.__send(cmd)
        if (resp_length > 0):
            resp = self.__recv(resp_length)
        else:
            resp = bytes([])
        if ((Const.JRKG2_CHECK_ERRFLAGS_AFTER_CMDS) and (not inhibit_err_check)):
            flags = self.get_and_clear_error_flags_occurred()
            # ignore AWAITING_COMMAND error
            ignore_mask = JrkG2.ErrorFlag.AWAITING_COMMAND.mask()
            errors = JrkG2.derive_error_flags(flags & (~ignore_mask))
            if len(errors) > 0:
                descs = []
                for err in errors:
                    descs.append(err.desc())
                print('Warning: error flags occurred: ' + ','.join(descs))
        return resp

    @staticmethod
    def derive_error_flags(err_var):
        error_flags = []
        for err in JrkG2.ErrorFlag:
            if ((err_var & err.mask()) != 0):
                error_flags.append(err)
        return error_flags

    def __send(self, data):
        try:
            self.serial_obj.write(data)
        except serial.SerialException as e:
            raise JrkG2Exception('SerialException: %s' % e)

    def __recv(self, length):
        try:
            data = self.serial_obj.read(length)
        except serial.SerialException as e:
            raise JrkG2Exception('SerialException: %s' % e)
        if len(data) != length:
            raise JrkG2Exception("read timed out: " + str(data) + ' bytes read, ' + str(length) + ' expected')
        return data

    def calc_crc(self, msg):
        remainder = 0x00
        for i in range(0, len(msg)):
            remainder ^= msg[i]
            remainder = self.crc_xor_table[remainder]
        return bytes([remainder])

    # [TARGET_MINVAL,TARGET_MAXVAL]
    def get_target(self):
        # TODO: implement short form of this?: 0xA3?
        data = self.get_variables(JrkG2.VAR_OFFSET_TARGET, JrkG2.VAR_LENGTH_TARGET)
        value = (data[1] << 8) + data[0]
        return value

    # [TARGET_MINVAL,TARGET_MAXVAL]
    def set_target(self, target):
        if not isinstance(target, int):
            raise ContractViolation('invalid argument: target')
        if ((target < JrkG2.TARGET_MINVAL) or (target > JrkG2.TARGET_MAXVAL)):
            raise ContractViolation('invalid argument: target')
        byte0 = JrkG2.CMDBYTE_SET_TARGET_HIRES + (target & 0x1F)
        byte1 = (target >> 5) & 0x7F
        data = bytes([byte0, byte1])
        self.__issue_cmd(data, 0)

    # [0,1]
    def get_target_norm(self):
        target = self.get_target()
        norm = (target - JrkG2.TARGET_MINVAL) / (JrkG2.TARGET_MAXVAL - JrkG2.TARGET_MINVAL)
        return norm

    # [0,1]
    def set_target_norm(self, norm):
        if ((norm < 0) or (norm > 1)):
            raise ContractViolation('invalid argument: norm')
        target = round(JrkG2.TARGET_MINVAL + (norm * (JrkG2.TARGET_MAXVAL - JrkG2.TARGET_MINVAL)))
        self.set_target(target)

    # [0,stroke_mm]
    def get_target_mm(self):
        mm = self.get_target_norm() * Const.ACTUATOR_STROKE_MM
        return mm

    # [0,stroke_mm]
    # returns True if mm is valid, else False
    def set_target_mm(self, mm):
        if ((mm < 0) or (mm > Const.ACTUATOR_STROKE_MM)):
            return False
        norm = mm / Const.ACTUATOR_STROKE_MM
        self.set_target_norm(norm)
        return True

    def stop_motor(self):
        byte0 = JrkG2.CMDBYTE_STOP_MOTOR
        data = bytes([byte0])
        self.__issue_cmd(data, 0)

    def get_variables(self, offset, length):
        if ((offset < 0) or (offset > 0xFF)):
            raise ContractViolation('invalid argument: offset')
        if ((length < 0) or (length > 0xFF)):
            raise ContractViolation('invalid argument: length')
        data = self.__issue_cmd(bytes([JrkG2.CMDBYTE_GET_VARIABLES, offset, length]), length)
        return bytearray(data)		# switch to immutable bytes? recv should already return bytes

    def get_feedback(self):
        # TODO: implement short form of this?: 0xA5?
        data = self.get_variables(JrkG2.VAR_OFFSET_FEEDBACK, JrkG2.VAR_LENGTH_FEEDBACK)
        value = (data[1] << 8) + data[0]
        return value

    @staticmethod
    def build_crc_xor_table():
        table = {}
        for b in range(0, 0x100):
            v = b
            for i in range(0, 8):
                if ((v & 0x01) != 0x00):
                    v ^= JrkG2.CRC7_POLY
                v >>= 1
            table[b] = v
        return table

    def get_and_clear_error_flags_halting(self):
        data = bytes([JrkG2.CMDBYTE_GET_AND_CLEAR_ERROR_FLAGS_HALTING])
        data = self.__issue_cmd(data, JrkG2.VAR_LENGTH_ERROR_FLAGS_HALTING, inhibit_err_check=True)
        value = (data[1] << 8) + data[0]
        return value

    def get_and_clear_error_flags_occurred(self):
        data = bytes([JrkG2.CMDBYTE_GET_AND_CLEAR_ERROR_FLAGS_OCCURRED])
        data = self.__issue_cmd(data, JrkG2.VAR_LENGTH_ERROR_FLAGS_OCCURRED, inhibit_err_check=True)
        value = (data[1] << 8) + data[0]
        return value

#    def get_error_flags_occurred(self):
#        data = self.get_variables(JrkG2.VAR_OFFSET_ERROR_FLAGS_OCCURRED, JrkG2.VAR_LENGTH_ERROR_FLAGS_OCCURRED)
#        value = (data[1] << 8) + data[0]
#        return value
#
#    def get_error_flags_halting(self):
#        data = self.get_variables(JrkG2.VAR_OFFSET_ERROR_FLAGS_HALTING, JrkG2.VAR_LENGTH_ERROR_FLAGS_HALTING)
#        value = (data[1] << 8) + data[0]
#        return value

