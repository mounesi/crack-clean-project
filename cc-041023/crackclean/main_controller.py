# coding=utf-8

from enum import Enum, unique
import time

from .cc_mode import CcMode
from .cc_status import CcStatus
from .const import Const
from .controller import Controller
from .exceptions import CcException
from .filter_mode import FilterMode
from .ipc.actuator_cmd import ActuatorCmd
from .ipc.actuator_resp import ActuatorResp
from .ipc.endpoint import Endpoint
from .ipc.detection_cmd import DetectionCmd
from .ipc.detection_resp import DetectionResp
from .ipc.joystick_cmd import JoystickCmd
from .ipc.joystick_resp import JoystickResp
from .ipc.joystick_event import JoystickEvent
from .ipc.main_cmd import MainCmd
from .ipc.main_resp import MainResp
from .ipc.video_cmd import VideoCmd
from .ipc.video_resp import VideoResp


class MainController(Controller):

    TARGET_STOP = -1

    @unique
    class FsmState(Enum):
        STARTING         = 0
        READY            = 1
        ACQUIRE_IMAGE    = 2
        AWAIT_IMAGE      = 3
        AWAIT_RESULT     = 4
        AWAIT_ACTUATOR   = 6
        TERMINATE        = 7

    def __init__(self, endpoint, params):
        super().__init__(endpoint, params)
        self.endpoint_actuator = None
        self.endpoint_detection = None
        self.endpoint_joystick = None
        self.endpoint_joystick_event = None
        self.endpoint_video = None
        self.pending_op_id_actuator = None
        self.pending_op_id_detection = None
        self.pending_op_id_joystick = None
        self.pending_op_id_video = None

    def init(self):
        self.endpoint_actuator = self.params[0]
        self.endpoint_detection = self.params[1]
        self.endpoint_joystick = self.params[2]
        self.endpoint_joystick_event = self.params[3]
        self.endpoint_video = self.params[4]

    def deinit(self):
        # shutdown all queues that we write to
        Endpoint.shutdown_queue(self.endpoint.txq)
        Endpoint.shutdown_queue(self.endpoint_actuator.txq)
        Endpoint.shutdown_queue(self.endpoint_detection.txq)
        Endpoint.shutdown_queue(self.endpoint_joystick.txq)
        Endpoint.shutdown_queue(self.endpoint_video.txq)
        # delete refs
        del self.endpoint_actuator
        del self.endpoint_detection
        del self.endpoint_joystick
        del self.endpoint_joystick_event
        del self.endpoint_video

    def start(self):
        cc_mode = CcMode.MANUAL
        filter_mode = FilterMode.ADAPTIVE
        target_cur = None       # TEMP: can also be MainController.TARGET_STOP
        target_req = None       # TEMP: can also be MainController.TARGET_STOP
        fsm_state = MainController.FsmState.STARTING
        num_full_cycles = 0
        detection_result = None
        cc_status = None
        ts_start = None
        actuator_ready = False
        detection_ready = False
        joystick_ready = False
        video_ready = False
        # used for both IS_READY and main functions:
        self.pending_op_id_actuator = None
        self.pending_op_id_detection = None
        self.pending_op_id_joystick = None
        self.pending_op_id_video = None

        ts_last_video_acquire_cmd = None

        cur_detect_thresh = Const.DETECTION_DETECT_THRESH_DEFAULT
        cur_simpfilter_thresh = Const.DETECTION_SIMPFILTER_THRESH_DEFAULT
        cur_adaptfilter_thresh = Const.DETECTION_ADAPTFILTER_THRESH_DEFAULT
        cur_adaptfilter_radius = Const.DETECTION_ADAPTFILTER_RADIUS_DEFAULT

        last_loop = time.monotonic()
        while True:
            #print(str(fsm_state))
            if (fsm_state == MainController.FsmState.STARTING):
                if not actuator_ready:
                    if self.pending_op_id_actuator is None:
                        self.cmd_actuator_is_ready(False)
                    else:
                        resp = self.endpoint_actuator.check_for_resp(self.pending_op_id_actuator)
                        if (resp is not None):
                            MainController.validate_op_obj(resp, ActuatorResp, (ActuatorResp.Token.TRUE, ActuatorResp.Token.FALSE))
                            print('ActuatorController ready: ' + str(resp.token))
                            self.pending_op_id_actuator = None
                            if (resp.token == ActuatorResp.Token.TRUE):
                                actuator_ready = True
                if not detection_ready:
                    if self.pending_op_id_detection is None:
                        self.cmd_detection_is_ready(False)
                    else:
                        resp = self.endpoint_detection.check_for_resp(self.pending_op_id_detection)
                        if (resp is not None):
                            MainController.validate_op_obj(resp, DetectionResp, (DetectionResp.Token.TRUE, DetectionResp.Token.FALSE))
                            print('DetectionController ready: ' + str(resp.token))
                            self.pending_op_id_detection = None
                            if (resp.token == DetectionResp.Token.TRUE):
                                detection_ready = True
                if not joystick_ready:
                    if self.pending_op_id_joystick is None:
                        self.cmd_joystick_is_ready(False)
                    else:
                        resp = self.endpoint_joystick.check_for_resp(self.pending_op_id_joystick)
                        if (resp is not None):
                            MainController.validate_op_obj(resp, JoystickResp, (JoystickResp.Token.TRUE, JoystickResp.Token.FALSE))
                            print('JoystickController ready: ' + str(resp.token))
                            self.pending_op_id_joystick = None
                            if (resp.token == JoystickResp.Token.TRUE):
                                joystick_ready = True
                if not video_ready:
                    if self.pending_op_id_video is None:
                        self.cmd_video_is_ready(False)
                    else:
                        resp = self.endpoint_video.check_for_resp(self.pending_op_id_video)
                        if (resp is not None):
                            MainController.validate_op_obj(resp, VideoResp, (VideoResp.Token.TRUE, VideoResp.Token.FALSE))
                            print('VideoController ready: ' + str(resp.token))
                            self.pending_op_id_video = None
                            if (resp.token == VideoResp.Token.TRUE):
                                video_ready = True
                if (actuator_ready and detection_ready and joystick_ready and video_ready):
                    fsm_state = MainController.FsmState.READY
            elif (fsm_state == MainController.FsmState.READY):
                pass
            elif (fsm_state == MainController.FsmState.ACQUIRE_IMAGE):
                self.pending_op_id_video = self.endpoint_video.send_cmd_async(VideoCmd(VideoCmd.Token.GET_LATEST_IMG, ()))
                ts_last_video_acquire_cmd = time.monotonic()
                fsm_state = MainController.FsmState.AWAIT_IMAGE
            elif (fsm_state == MainController.FsmState.AWAIT_IMAGE):
                video_resp = self.endpoint_video.check_for_resp(self.pending_op_id_video)
                if (video_resp is not None):
                    self.pending_op_id_video = None
                    MainController.validate_op_obj(video_resp, VideoResp, (VideoResp.Token.LATEST_IMG,))
                    if not video_resp.params[0].is_empty():
                        img_latest = video_resp.params[0]
                        ts_dc_call = time.monotonic()
                        self.pending_op_id_detection = self.endpoint_detection.send_cmd_async(DetectionCmd(DetectionCmd.Token.DETECT, (img_latest, cur_detect_thresh, cur_simpfilter_thresh, cur_adaptfilter_thresh, cur_adaptfilter_radius, filter_mode)))
                        fsm_state = MainController.FsmState.AWAIT_RESULT
                else:
                    img_elapsed_s = time.monotonic() - ts_last_video_acquire_cmd
                    if (img_elapsed_s > Const.VIDEO_MAX_IMG_REQ_DELAY_S):
                        print('failed to receive image from VideoController after ' + str(Const.VIDEO_MAX_IMG_REQ_DELAY_S) + ' s; terminating application')
                        fsm_state = MainController.FsmState.TERMINATE		# app won't know about this and will raise/hang. exit routes need some redesign...
            elif (fsm_state == MainController.FsmState.AWAIT_RESULT):
                detection_resp = self.endpoint_detection.check_for_resp(self.pending_op_id_detection)
                if (detection_resp is not None):
                    self.pending_op_id_detection = None
                    MainController.validate_op_obj(detection_resp, DetectionResp, (DetectionResp.Token.DETECTION_RESULT,))
                    detection_result = detection_resp.params[0]
                    dc_call_ms = (time.monotonic() - ts_dc_call) * 1000
                    dc_y_mm = detection_result.y_mm

                    if ((cc_mode == CcMode.AUTO) and (dc_y_mm is not None)):
                        target_req = MainController.calc_act_mm_from_dc_mm(dc_y_mm)
                    num_full_cycles += 1
                    run_dur_s = (time.monotonic() - ts_start)
                    ips = num_full_cycles / run_dur_s
                    img_age_ms = (time.time() - img_latest.timestamp) * 1000
                    if ((target_cur is None) or (target_cur == MainController.TARGET_STOP)):
                        target_str = 'STOP'
                    else:
                        target_str = '{0:.1f}'.format(target_cur)
                    cc_status = CcStatus(cc_mode, cur_detect_thresh, cur_simpfilter_thresh, cur_adaptfilter_thresh, cur_adaptfilter_radius, filter_mode, ips, dc_call_ms, img_age_ms, dc_y_mm, target_str, detection_result.img)
                    if (target_req != target_cur):
                        if (target_req == MainController.TARGET_STOP):
                            self.pending_op_id_actuator = self.endpoint_actuator.send_cmd_async(ActuatorCmd(ActuatorCmd.Token.STOP_MOTOR, ()))
                        else:
                            self.pending_op_id_actuator = self.endpoint_actuator.send_cmd_async(ActuatorCmd(ActuatorCmd.Token.SET_TARGET_MM, (target_req,)))
                        fsm_state = MainController.FsmState.AWAIT_ACTUATOR
                    else:
                        fsm_state = MainController.FsmState.ACQUIRE_IMAGE
            elif (fsm_state == MainController.FsmState.AWAIT_ACTUATOR):
                actuator_resp = self.endpoint_actuator.check_for_resp(self.pending_op_id_actuator)
                if (actuator_resp is not None):
                    self.pending_op_id_actuator = None
                    MainController.validate_op_obj(actuator_resp, ActuatorResp, (ActuatorResp.Token.OK,))
                    target_cur = target_req
                    fsm_state = MainController.FsmState.ACQUIRE_IMAGE
            elif (fsm_state == MainController.FsmState.TERMINATE):
                break
            else:
                raise CcException('MainController encountered unexpected FsmState: ' + str(fsm_state))
            # handle any incoming commands
            tup = self.endpoint.get_cmd(False)
            if tup is not None:
                (cmd_op_id, cmd) = tup
                if not isinstance(cmd, MainCmd):
                    #self.resp_error(cmd_op_id)
                    raise CcException('MainController received unexpected OpObj')
                if (cmd.token == MainCmd.Token.TERMINATE):
                    fsm_state = MainController.FsmState.TERMINATE
                    self.resp_ok(cmd_op_id)
                elif (cmd.token == MainCmd.Token.START):
                    if (fsm_state != MainController.FsmState.READY):
                        self.resp_error(cmd_op_id)
                    else:
                        ts_start = time.monotonic()
                        fsm_state = MainController.FsmState.ACQUIRE_IMAGE
                    self.resp_ok(cmd_op_id)
                elif (cmd.token == MainCmd.Token.IS_READY):
                    if (fsm_state != MainController.FsmState.STARTING):
                        self.resp_true(cmd_op_id)
                    else:
                        self.resp_false(cmd_op_id)
                elif (cmd.token == MainCmd.Token.GET_STATUS):
                    self.resp_cc_status(cmd_op_id, cc_status)
                elif (cmd.token == MainCmd.Token.SET_MODE):
                    if not isinstance(cmd.params[0], CcMode):
                        #self.resp_error(cmd_op_id)
                        raise CcException('MainController received unexpected SET_MODE parameter')
                    cc_mode = cmd.params[0]
                    if cc_mode == CcMode.MANUAL:
                        target_req = MainController.TARGET_STOP
                    self.resp_ok(cmd_op_id)
                elif (cmd.token == MainCmd.Token.TOGGLE_MODE):
                    if cc_mode == CcMode.AUTO:
                        cc_mode = CcMode.MANUAL
                        target_req = MainController.TARGET_STOP
                    elif cc_mode == CcMode.MANUAL:
                        cc_mode = CcMode.AUTO
                    else:
                        raise CcException('MainController encountered unexpected CcMode')
                    self.resp_ok(cmd_op_id)
                elif (cmd.token == MainCmd.Token.SET_DETECT_THRESH):
                    if not isinstance(cmd.params[0], float):
                        #self.resp_error(cmd_op_id)
                        raise CcException('MainController received unexpected SET_DETECT_THRESH parameter')
                    cur_detect_thresh = cmd.params[0]
                    self.resp_ok(cmd_op_id)
                elif (cmd.token == MainCmd.Token.SET_SIMPFILTER_THRESH):
                    if not isinstance(cmd.params[0], int):
                        #self.resp_error(cmd_op_id)
                        raise CcException('MainController received unexpected SET_SIMPFILTER_THRESH parameter')
                    cur_simpfilter_thresh = cmd.params[0]
                    self.resp_ok(cmd_op_id)
                elif (cmd.token == MainCmd.Token.SET_ADAPTFILTER_THRESH):
                    if not isinstance(cmd.params[0], float):
                        #self.resp_error(cmd_op_id)
                        raise CcException('MainController received unexpected SET_ADAPTFILTER_THRESH parameter')
                    cur_adaptfilter_thresh = cmd.params[0]
                    self.resp_ok(cmd_op_id)
                elif (cmd.token == MainCmd.Token.SET_ADAPTFILTER_RADIUS):
                    if not isinstance(cmd.params[0], int):
                        #self.resp_error(cmd_op_id)
                        raise CcException('MainController received unexpected SET_ADAPTFILTER_RADIUS parameter')
                    cur_adaptfilter_radius = cmd.params[0]
                    self.resp_ok(cmd_op_id)
                elif (cmd.token == MainCmd.Token.SET_FILTER_MODE):
                    if not isinstance(cmd.params[0], FilterMode):
                        #self.resp_error(cmd_op_id)
                        raise CcException('MainController received unexpected SET_FILTER_MODE parameter')
                    filter_mode = cmd.params[0]
                    self.resp_ok(cmd_op_id)
                else:
                    #self.resp_error(cmd_op_id)
                    raise CcException('MainController received unexpected MainCmd')
            # handle any incoming joystick events
            event = self.endpoint_joystick_event.check_for_event()
            if event is not None:
                MainController.validate_op_obj(event, JoystickEvent, (JoystickEvent.Token.BUTTON_DOWN, JoystickEvent.Token.POSITION))
                if (event.token == JoystickEvent.Token.BUTTON_DOWN):
                    if cc_mode == CcMode.AUTO:
                        cc_mode = CcMode.MANUAL
                        target_req = MainController.TARGET_STOP
                    elif cc_mode == CcMode.MANUAL:
                        cc_mode = CcMode.AUTO
                    else:
                        raise CcException('MainController encountered unexpected CcMode')
                else:	# (POSITION)
                    val_norm = event.params[0]	# TODO: check this and other use of params
                    if (abs(val_norm) <= Const.JOYSTICK_ZERO_MAX_NORM):
                        target_req = MainController.TARGET_STOP
                    else:
                        cc_mode = CcMode.MANUAL
                        if ((val_norm > 0) == Const.JOYSTICK_POSITIVE_IS_EXTEND):
                            target_req = Const.ACTUATOR_STROKE_MM
                        else:
                            target_req = 0
            # pace iteration
            # TODO: possible precision/boundary issue here?
            elapsed = time.monotonic() - last_loop
            if (elapsed < Const.MAIN_CONTROLLER_MIN_PERIOD_S):
                time.sleep(Const.MAIN_CONTROLLER_MIN_PERIOD_S - elapsed)
            last_loop = time.monotonic()
        # retract actuator
        print('MainController retracting actuator...')
        resp = self.endpoint_actuator.send_cmd_sync(ActuatorCmd(ActuatorCmd.Token.SET_TARGET_MM, (0,)), Const.CMD_SYNC_TIMEOUT_MS)
        MainController.validate_op_obj(resp, ActuatorResp, (ActuatorResp.Token.OK,))
        time.sleep(6)       # TODO: rather than sleep, validate position or timeout
        # stop actuator motor
        print('MainController stopping actuator motor...')
        resp = self.endpoint_actuator.send_cmd_sync(ActuatorCmd(ActuatorCmd.Token.STOP_MOTOR, ()), Const.CMD_SYNC_TIMEOUT_MS)
        MainController.validate_op_obj(resp, ActuatorResp, (ActuatorResp.Token.OK,))
        # terminate ActuatorController
        print('MainController terminating ActuatorController...')
        resp = self.endpoint_actuator.send_cmd_sync(ActuatorCmd(ActuatorCmd.Token.TERMINATE, ()), Const.CMD_SYNC_TIMEOUT_MS)
        if resp is None:
            print('Warning: timed out waiting for ActuatorController response to TERMINATE command')
        else:
            MainController.validate_op_obj(resp, ActuatorResp, (ActuatorResp.Token.OK,))
        # terminate DetectionController
        print('MainController terminating DetectionController...')
        resp = self.endpoint_detection.send_cmd_sync(DetectionCmd(DetectionCmd.Token.TERMINATE, ()), Const.CMD_SYNC_TIMEOUT_MS)
        if resp is None:
            print('Warning: timed out waiting for DetectionController response to TERMINATE command')
        else:
            MainController.validate_op_obj(resp, DetectionResp, (DetectionResp.Token.OK,))
        # terminate JoystickController
        print('MainController terminating JoystickController...')
        resp = self.endpoint_joystick.send_cmd_sync(JoystickCmd(JoystickCmd.Token.TERMINATE, ()), Const.CMD_SYNC_TIMEOUT_MS)
        if resp is None:
            print('Warning: timed out waiting for JoystickController response to TERMINATE command')
        else:
            MainController.validate_op_obj(resp, JoystickResp, (JoystickResp.Token.OK,))
        # terminate VideoController
        print('MainController terminating VideoController...')
        resp = self.endpoint_video.send_cmd_sync(VideoCmd(VideoCmd.Token.TERMINATE, ()), Const.CMD_SYNC_TIMEOUT_MS)
        if resp is None:
            print('Warning: timed out waiting for VideoController response to TERMINATE command')
        else:
            MainController.validate_op_obj(resp, VideoResp, (VideoResp.Token.OK,))

    @staticmethod
    def calc_act_mm_from_dc_mm(dc_y_mm):
        act_mm = Const.CALIBRATION_ACTUATOR_MM_AT_Y_ORIGIN - dc_y_mm
        act_mm = max(act_mm, 0)
        act_mm = min(act_mm, Const.ACTUATOR_STROKE_MM)
        return act_mm

    # convenience function
    def cmd_actuator_is_ready(self, sync):
        if (self.pending_op_id_actuator is not None):
            print('pending_op_id_actuator expected to be None, but is not')		# TODO: fatal raise
        if sync:
            self.pending_op_id_actuator = self.endpoint_actuator.send_cmd_sync(ActuatorCmd(ActuatorCmd.Token.IS_READY, ()), Const.CMD_SYNC_TIMEOUT_MS)
        else:
            self.pending_op_id_actuator = self.endpoint_actuator.send_cmd_async(ActuatorCmd(ActuatorCmd.Token.IS_READY, ()))

    # convenience function
    def cmd_detection_is_ready(self, sync):
        if (self.pending_op_id_detection is not None):
            print('pending_op_id_detection expected to be None, but is not')		# TODO: fatal raise
        if sync:
            self.pending_op_id_detection = self.endpoint_detection.send_cmd_sync(DetectionCmd(DetectionCmd.Token.IS_READY, ()), Const.CMD_SYNC_TIMEOUT_MS)
        else:
            self.pending_op_id_detection = self.endpoint_detection.send_cmd_async(DetectionCmd(DetectionCmd.Token.IS_READY, ()))

    # convenience function
    def cmd_joystick_is_ready(self, sync):
        if (self.pending_op_id_joystick is not None):
            print('pending_op_id_joystick expected to be None, but is not')		# TODO: fatal raise
        if sync:
            self.pending_op_id_joystick = self.endpoint_joystick.send_cmd_sync(JoystickCmd(JoystickCmd.Token.IS_READY, ()), Const.CMD_SYNC_TIMEOUT_MS)
        else:
            self.pending_op_id_joystick = self.endpoint_joystick.send_cmd_async(JoystickCmd(JoystickCmd.Token.IS_READY, ()))

    # convenience function
    def cmd_video_is_ready(self, sync):
        if (self.pending_op_id_video is not None):
            print('pending_op_id_video expected to be None, but is not')		# TODO: fatal raise
        if sync:
            self.pending_op_id_video = self.endpoint_video.send_cmd_sync(VideoCmd(VideoCmd.Token.IS_READY, ()), Const.CMD_SYNC_TIMEOUT_MS)
        else:
            self.pending_op_id_video = self.endpoint_video.send_cmd_async(VideoCmd(VideoCmd.Token.IS_READY, ()))

    # convenience function
    def resp_ok(self, op_id):
        self.endpoint.send_resp(op_id, MainResp(MainResp.Token.OK, ()))

    # convenience function
    def resp_error(self, op_id):
        self.endpoint.send_resp(op_id, MainResp(MainResp.Token.ERROR, ()))

    # convenience function
    def resp_true(self, op_id):
        self.endpoint.send_resp(op_id, MainResp(MainResp.Token.TRUE, ()))

    # convenience function
    def resp_false(self, op_id):
        self.endpoint.send_resp(op_id, MainResp(MainResp.Token.FALSE, ()))

    # convenience function
    def resp_cc_status(self, op_id, cc_status):
        self.endpoint.send_resp(op_id, MainResp(MainResp.Token.STATUS, (cc_status,)))

    # raises CcException
    @staticmethod
    def validate_op_obj(resp, resp_type, token_values):
        if ((resp is None) or (not isinstance(resp, resp_type))):
            raise CcException('MainController encountered unexpected value while validating an expected ' + str(resp_type))
        for val in token_values:
            if resp.token == val:
                return
        raise CcException('MainController encountered unexpected value while validating an expected ' + str(resp_type))

    # for use in a ControllerProcess
    @staticmethod
    def worker(endpoint, params):
        print('initializing MainController...')
        controller = MainController(endpoint, params)
        controller.init()
        print('starting MainController...')
        controller.start()
        print('deinitializing MainController...')
        controller.deinit()
        print('exiting MainController worker...')

