# coding=utf-8

class ActuatorException(Exception):
    def __init__(self, msg):
        super(ActuatorException, self).__init__(msg)
        self.msg = msg

class CcException(Exception):
    def __init__(self, msg):
        super(CcException, self).__init__(msg)
        self.msg = msg

class ContractViolation(Exception):
    def __init__(self, msg):
        super(ContractViolation, self).__init__(msg)
        self.msg = msg

class DetectionException(Exception):
    def __init__(self, msg):
        super(DetectionException, self).__init__(msg)
        self.msg = msg

class JoystickException(Exception):
    def __init__(self, msg):
        super(JoystickException, self).__init__(msg)
        self.msg = msg

class JrkG2Exception(Exception):
    def __init__(self, msg):
        super(JrkG2Exception, self).__init__(msg)
        self.msg = msg

class SpinCamException(Exception):
    def __init__(self, msg):
        super(SpinCamException, self).__init__(msg)
        self.msg = msg

class VideoException(Exception):
    def __init__(self, msg):
        super(VideoException, self).__init__(msg)
        self.msg = msg

