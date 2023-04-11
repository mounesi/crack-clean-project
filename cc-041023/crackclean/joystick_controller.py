# coding=utf-8

import time

from .const import Const
from .controller import Controller
from .exceptions import JoystickException
from .joystick import Joystick
from .ipc.endpoint import Endpoint
from .ipc.joystick_cmd import JoystickCmd
from .ipc.joystick_resp import JoystickResp
from .ipc.joystick_event import JoystickEvent


class JoystickController(Controller):

    def __init__(self, endpoint, params):
        super().__init__(endpoint, params)
        self.ep_event_producer = self.params[0]
        self.joystick = None

    def init(self):
        self.joystick = Joystick()
        self.joystick.init()

    def deinit(self):
        self.joystick.deinit()
        # shutdown all queues that we write to
        Endpoint.shutdown_queue(self.endpoint.txq)
        Endpoint.shutdown_queue(self.ep_event_producer.txq)
        # delete refs
        del self.joystick
        del self.ep_event_producer

    def start(self):
        ignore_events = True
        ts_start = time.monotonic()
        while True:
            event = self.joystick.check_for_event()
            if ignore_events:
                # ignore the initial flurry of non-init events that are occasionally emitted
                # after the device is opened
                if ((time.monotonic() - ts_start) >= Const.JOYSTICK_INITIAL_IGNORE_TIME_S):
                    ignore_events = False
            else:
                if event is not None:
                    if (isinstance(event, Joystick.AxisEvent)):
                        if (event.axis_num == Const.JOYSTICK_AXIS_NUM):
                            joystick_event = JoystickEvent(JoystickEvent.Token.POSITION, (event.val_norm,))
                            self.ep_event_producer.send_event(joystick_event)
                    elif (isinstance(event, Joystick.ButtonEvent)):
                        if ((event.btn_num == Const.JOYSTICK_BUTTON_NUM) and (event.press)):
                            joystick_event = JoystickEvent(JoystickEvent.Token.BUTTON_DOWN, ())
                            self.ep_event_producer.send_event(joystick_event)
                    else:
                        raise JoystickException('JoystickController received unexpected event from Joystick')
            # handle any incoming commands
            tup = self.endpoint.get_cmd(False)
            if tup is not None:
                (cmd_op_id, cmd) = tup
                if not isinstance(cmd, JoystickCmd):
                    self.endpoint.send_resp(cmd_op_id, JoystickResp(JoystickResp.Token.ERROR, ()))
                    raise JoystickException('JoystickController received unexpected OpObj')
                if (cmd.token == JoystickCmd.Token.TERMINATE):
                    self.endpoint.send_resp(cmd_op_id, JoystickResp(JoystickResp.Token.OK, ()))
                    break
                elif (cmd.token == JoystickCmd.Token.IS_READY):
                    self.endpoint.send_resp(cmd_op_id, JoystickResp(JoystickResp.Token.TRUE, ()))
                else:
                    self.endpoint.send_resp(cmd_op_id, JoystickResp(JoystickResp.Token.ERROR, ()))
                    raise JoystickException('JoystickController received unexpected JoystickCmd')
            time.sleep(Const.JOYSTICK_CONTROLLER_LOOP_SLEEP_S)

    # for use in a ControllerProcess
    @staticmethod
    def worker(endpoint, params):
        print('initializing JoystickController...')
        controller = JoystickController(endpoint, params)
        controller.init()
        print('starting JoystickController...')
        try:
            controller.start()
        except JoystickException as e:
            print('JoystickException: ' + str(e))
        print('deinitializing JoystickController...')
        controller.deinit()
        print('exiting JoystickController worker...')

