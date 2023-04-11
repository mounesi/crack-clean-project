# coding=utf-8

from .controller import Controller
from .exceptions import ActuatorException
from .exceptions import JrkG2Exception
from .ipc.actuator_cmd import ActuatorCmd
from .ipc.actuator_resp import ActuatorResp
from .ipc.endpoint import Endpoint
from .jrkg2 import JrkG2


class ActuatorController(Controller):

    def __init__(self, endpoint, params):
        super().__init__(endpoint, params)
        self.jrkg2 = None

    def init(self):
        self.jrkg2 = JrkG2()
        try:
            self.jrkg2.init()
            self.jrkg2.get_and_clear_error_flags_halting()
            self.jrkg2.stop_motor()
        except JrkG2Exception as e:
            # TODO: attempt to deinit?  or can this trigger a pyserial exception if not already open?
            raise ActuatorException('JrkG2Exception: %s' % e)

    def deinit(self):
        try:
            self.jrkg2.deinit()
        except JrkG2Exception as e:
            raise ActuatorException('JrkG2Exception: %s' % e)
        # shutdown all queues that we write to
        Endpoint.shutdown_queue(self.endpoint.txq)
        # delete refs
        del self.jrkg2

    # TODO: catch JrkG2Exception in various places below
    def start(self):
        while True:
            tup = self.endpoint.get_cmd(True)
            (cmd_op_id, cmd) = tup
            if not isinstance(cmd, ActuatorCmd):
                self.endpoint.send_resp(cmd_op_id, ActuatorResp(ActuatorResp.Token.ERROR, ()))
                raise ActuatorException('ActuatorController received unexpected OpObj')
            if (cmd.token == ActuatorCmd.Token.TERMINATE):
                self.endpoint.send_resp(cmd_op_id, ActuatorResp(ActuatorResp.Token.OK, ()))
                break
            elif (cmd.token == ActuatorCmd.Token.IS_READY):
                self.endpoint.send_resp(cmd_op_id, ActuatorResp(ActuatorResp.Token.TRUE, ()))
            elif (cmd.token == ActuatorCmd.Token.GET_TARGET_MM):
                target_current = self.jrkg2.get_target_mm()
                self.endpoint.send_resp(cmd_op_id, ActuatorResp(ActuatorResp.Token.TARGET_VALUE, (target_current,)))
            elif (cmd.token == ActuatorCmd.Token.SET_TARGET_MM):
                target_new = cmd.params[0]
                result = self.jrkg2.set_target_mm(target_new)
                if result:
                    self.endpoint.send_resp(cmd_op_id, ActuatorResp(ActuatorResp.Token.OK, ()))
                else:
                    self.endpoint.send_resp(cmd_op_id, ActuatorResp(ActuatorResp.Token.ERROR, ()))
            elif (cmd.token == ActuatorCmd.Token.STOP_MOTOR):
                self.jrkg2.stop_motor()
                self.endpoint.send_resp(cmd_op_id, ActuatorResp(ActuatorResp.Token.OK, ()))
            else:
                self.endpoint.send_resp(cmd_op_id, ActuatorResp(ActuatorResp.Token.ERROR, ()))
                raise ActuatorException('ActuatorController received unexpected command')

    # for use in a ControllerProcess
    @staticmethod
    def worker(endpoint, params):
        print('initializing ActuatorController...')
        controller = ActuatorController(endpoint, params)
        controller.init()
        print('starting ActuatorController...')
        try:
            controller.start()
        except ActuatorException as e:
            print('ActuatorException: ' + str(e))
        print('deinitializing ActuatorController...')
        controller.deinit()
        print('exiting ActuatorController worker...')

