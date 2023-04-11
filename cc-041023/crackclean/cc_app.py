# coding=utf-8

import time

from .cc_mode import CcMode
from .const import Const
from .controller_process import ControllerProcess
from .actuator_controller import ActuatorController
from .detection_controller import DetectionController
from .exceptions import CcException
from .filter_mode import FilterMode
from .main_controller import MainController
from .joystick_controller import JoystickController
from .video_controller import VideoController
from .ipc.endpoint import Endpoint
from .ipc.event_producer_endpoint import EventProducerEndpoint
from .ipc.event_consumer_endpoint import EventConsumerEndpoint
from .ipc.main_cmd import MainCmd
from .ipc.main_resp import MainResp
from .ipc.master_endpoint import MasterEndpoint
from .ipc.slave_endpoint import SlaveEndpoint


class CcApp(object):

    def __init__(self, context):
        self.context = context
        self.q_main_cmd       = None
        self.q_main_resp      = None
        self.q_actuator_cmd   = None
        self.q_actuator_resp  = None
        self.q_detection_cmd  = None
        self.q_detection_resp = None
        self.q_joystick_cmd   = None
        self.q_joystick_resp  = None
        self.q_joystick_event = None
        self.q_video_cmd      = None
        self.q_video_resp     = None
        self.ep_main_master   = None
        self.cp_main          = None
        self.cp_actuator      = None
        self.cp_detection     = None
        self.cp_joystick      = None
        self.cp_video         = None

    def start(self):
        # create queues
        self.q_main_cmd       = self.context.Queue(Const.CMD_QUEUE_MAXSIZE)
        self.q_main_resp      = self.context.Queue(Const.RESP_QUEUE_MAXSIZE)
        self.q_actuator_cmd   = self.context.Queue(Const.CMD_QUEUE_MAXSIZE)
        self.q_actuator_resp  = self.context.Queue(Const.RESP_QUEUE_MAXSIZE)
        self.q_detection_cmd  = self.context.Queue(Const.CMD_QUEUE_MAXSIZE)
        self.q_detection_resp = self.context.Queue(Const.RESP_QUEUE_MAXSIZE)
        self.q_joystick_cmd   = self.context.Queue(Const.CMD_QUEUE_MAXSIZE)
        self.q_joystick_resp  = self.context.Queue(Const.RESP_QUEUE_MAXSIZE)
        self.q_joystick_event = self.context.Queue(Const.EVENT_QUEUE_MAXSIZE)
        self.q_video_cmd      = self.context.Queue(Const.CMD_QUEUE_MAXSIZE)
        self.q_video_resp     = self.context.Queue(Const.RESP_QUEUE_MAXSIZE)
        # create endpoints
        self.ep_main_master         = MasterEndpoint(        self.q_main_cmd,       self.q_main_resp)
        ep_main_slave               = SlaveEndpoint(         self.q_main_resp,      self.q_main_cmd)
        ep_actuator_master          = MasterEndpoint(        self.q_actuator_cmd,   self.q_actuator_resp)
        ep_actuator_slave           = SlaveEndpoint(         self.q_actuator_resp,  self.q_actuator_cmd)
        ep_detection_master         = MasterEndpoint(        self.q_detection_cmd,  self.q_detection_resp)
        ep_detection_slave          = SlaveEndpoint(         self.q_detection_resp, self.q_detection_cmd)
        ep_joystick_master          = MasterEndpoint(        self.q_joystick_cmd,   self.q_joystick_resp)
        ep_joystick_slave           = SlaveEndpoint(         self.q_joystick_resp,  self.q_joystick_cmd)
        ep_joystick_event_producer  = EventProducerEndpoint( self.q_joystick_event)
        ep_joystick_event_consumer  = EventConsumerEndpoint( self.q_joystick_event)
        ep_video_master             = MasterEndpoint(        self.q_video_cmd,      self.q_video_resp)
        ep_video_slave              = SlaveEndpoint(         self.q_video_resp,     self.q_video_cmd)
        # build controller arguments
        main_controller_args      = (ep_actuator_master, ep_detection_master, ep_joystick_master, ep_joystick_event_consumer, ep_video_master)
        actuator_controller_args  = ()
        detection_controller_args = (Const.LABEL_PATH, Const.MODEL_PATH)
        joystick_controller_args  = (ep_joystick_event_producer,)
        video_controller_args     = ()
        # build worker arguments
        main_worker_args      = (ep_main_slave,      main_controller_args)
        actuator_worker_args  = (ep_actuator_slave,  actuator_controller_args)
        detection_worker_args = (ep_detection_slave, detection_controller_args)
        joystick_worker_args  = (ep_joystick_slave,  joystick_controller_args)
        video_worker_args     = (ep_video_slave,     video_controller_args)
        # instantiate ControllerProcesses
        self.cp_main      = ControllerProcess('mainworker',       self.context, MainController.worker,      main_worker_args)
        self.cp_actuator  = ControllerProcess('actuatorworker',   self.context, ActuatorController.worker,  actuator_worker_args)
        self.cp_detection = ControllerProcess('detectionworker',  self.context, DetectionController.worker, detection_worker_args)
        self.cp_joystick  = ControllerProcess('joystickworker',   self.context, JoystickController.worker,  joystick_worker_args)
        self.cp_video     = ControllerProcess('videoworker',      self.context, VideoController.worker,     video_worker_args)
        # start ControllerProcesses
        self.cp_main.startup()
        self.cp_actuator.startup()
        self.cp_detection.startup()
        self.cp_joystick.startup()
        self.cp_video.startup()
        # pause
        time.sleep(1)
        # wait until system ready
        while True:
            resp = self.ep_main_master.send_cmd_sync(MainCmd(MainCmd.Token.IS_READY, ()), Const.CMD_SYNC_TIMEOUT_MS)
            if resp is None:
                raise CcException('CcApp received no response from MainController to IS_READY command')
            if not isinstance(resp, MainResp):
                raise CcException('CcApp received unexpected response from MainController to IS_READY command')
            if (resp.token == MainResp.Token.TRUE):
                break
            elif (resp.token == MainResp.Token.FALSE):
                pass
            else:
                raise CcException('CcApp received unexpected response from MainController to IS_READY command')
            time.sleep(0.25)		# FIXME MAGIC
        # issue START command to MainController
        resp = self.ep_main_master.send_cmd_sync(MainCmd(MainCmd.Token.START, ()), Const.CMD_SYNC_TIMEOUT_MS)
        if resp is None:
            raise CcException('CcApp received no response from MainController to START command')
        if ((not isinstance(resp, MainResp)) or (resp.token != MainResp.Token.OK)):
            raise CcException('CcApp received unexpected response from MainController to START command')

    def dead_procs(self):
        dead_procs = []
        if not self.cp_main.is_alive():
            dead_procs.append(self.cp_main.name)
        if not self.cp_actuator.is_alive():
            dead_procs.append(self.cp_actuator.name)
        if not self.cp_detection.is_alive():
            dead_procs.append(self.cp_detection.name)
        if not self.cp_joystick.is_alive():
            dead_procs.append(self.cp_joystick.name)
        if not self.cp_video.is_alive():
            dead_procs.append(self.cp_video.name)
        return dead_procs

    def stop(self):
        # issue TERMINATE to MainController
        resp = self.ep_main_master.send_cmd_sync(MainCmd(MainCmd.Token.TERMINATE, ()), Const.CMD_SYNC_TIMEOUT_MS)
        if resp is None:
            print('Warning: CcApp received no response from MainController to TERMINATE command')
        else:
            if ((not isinstance(resp, MainResp)) or (resp.token != MainResp.Token.OK)):
                raise CcException('CcApp received unexpected response from MainController to TERMINATE command')
        # shutdown all queues that we write to
        Endpoint.shutdown_queue(self.q_main_cmd)

        # wait for main worker to terminate
        self.cp_main.shutdown()
        # wait for actuator worker to terminate
        self.cp_actuator.shutdown()
        # wait for detection worker to terminate
        self.cp_detection.shutdown()
        # wait for joystick worker to terminate
        self.cp_joystick.shutdown()
        # wait for video worker to terminate
        self.cp_video.shutdown()

    def get_status(self):
        resp = self.ep_main_master.send_cmd_sync(MainCmd(MainCmd.Token.GET_STATUS, ()), Const.CMD_SYNC_TIMEOUT_MS)
        if resp is None:
            raise CcException('CcApp received no response from MainController to GET_STATUS command')		# WARN?
        if not isinstance(resp, MainResp):
            raise CcException('CcApp received unexpected response from MainController to GET_STATUS command')
        if (resp.token == MainResp.Token.STATUS):
            return resp.params[0]
        else:
            raise CcException('CcApp received unexpected response from MainController to GET_STATUS command')

    def set_detect_thresh(self, val):
        resp = self.ep_main_master.send_cmd_sync(MainCmd(MainCmd.Token.SET_DETECT_THRESH, (val,)), Const.CMD_SYNC_TIMEOUT_MS)
        if resp is None:
            raise CcException('CcApp received no response from MainController to SET_DETECT_THRESH command')		# WARN?
        if ((not isinstance(resp, MainResp)) or (resp.token != MainResp.Token.OK)):
            raise CcException('CcApp received unexpected response from MainController to SET_DETECT_THRESH command')

    def set_simpfilter_thresh(self, val):
        resp = self.ep_main_master.send_cmd_sync(MainCmd(MainCmd.Token.SET_SIMPFILTER_THRESH, (val,)), Const.CMD_SYNC_TIMEOUT_MS)
        if resp is None:
            raise CcException('CcApp received no response from MainController to SET_SIMPFILTER_THRESH command')		# WARN?
        if ((not isinstance(resp, MainResp)) or (resp.token != MainResp.Token.OK)):
            raise CcException('CcApp received unexpected response from MainController to SET_SIMPFILTER_THRESH command')

    def set_adaptfilter_thresh(self, val):
        resp = self.ep_main_master.send_cmd_sync(MainCmd(MainCmd.Token.SET_ADAPTFILTER_THRESH, (val,)), Const.CMD_SYNC_TIMEOUT_MS)
        if resp is None:
            raise CcException('CcApp received no response from MainController to SET_ADAPTFILTER_THRESH command')		# WARN?
        if ((not isinstance(resp, MainResp)) or (resp.token != MainResp.Token.OK)):
            raise CcException('CcApp received unexpected response from MainController to SET_ADAPTFILTER_THRESH command')
        pass

    def set_adaptfilter_radius(self, val):
        resp = self.ep_main_master.send_cmd_sync(MainCmd(MainCmd.Token.SET_ADAPTFILTER_RADIUS, (val,)), Const.CMD_SYNC_TIMEOUT_MS)
        if resp is None:
            raise CcException('CcApp received no response from MainController to SET_ADAPTFILTER_RADIUS command')		# WARN?
        if ((not isinstance(resp, MainResp)) or (resp.token != MainResp.Token.OK)):
            raise CcException('CcApp received unexpected response from MainController to SET_ADAPTFILTER_RADIUS command')
        pass

    def set_filter_mode_simple(self):
        resp = self.ep_main_master.send_cmd_sync(MainCmd(MainCmd.Token.SET_FILTER_MODE, (FilterMode.SIMPLE,)), Const.CMD_SYNC_TIMEOUT_MS)
        if resp is None:
            raise CcException('CcApp received no response from MainController to SET_FILTER_MODE command')		# WARN?
        if ((not isinstance(resp, MainResp)) or (resp.token != MainResp.Token.OK)):
            raise CcException('CcApp received unexpected response from MainController to SET_FILTER_MODE command')

    def set_filter_mode_adaptive(self):
        resp = self.ep_main_master.send_cmd_sync(MainCmd(MainCmd.Token.SET_FILTER_MODE, (FilterMode.ADAPTIVE,)), Const.CMD_SYNC_TIMEOUT_MS)
        if resp is None:
            raise CcException('CcApp received no response from MainController to SET_FILTER_MODE command')		# WARN?
        if ((not isinstance(resp, MainResp)) or (resp.token != MainResp.Token.OK)):
            raise CcException('CcApp received unexpected response from MainController to SET_FILTER_MODE command')

    def toggle_mode(self):
        resp = self.ep_main_master.send_cmd_sync(MainCmd(MainCmd.Token.TOGGLE_MODE, ()), Const.CMD_SYNC_TIMEOUT_MS)
        if resp is None:
            raise CcException('CcApp received no response from MainController to TOGGLE_MODE command')		# WARN?
        if ((not isinstance(resp, MainResp)) or (resp.token != MainResp.Token.OK)):
            raise CcException('CcApp received unexpected response from MainController to TOGGLE_MODE command')

    def set_mode_manual(self):
        resp = self.ep_main_master.send_cmd_sync(MainCmd(MainCmd.Token.SET_MODE, (CcMode.MANUAL,)), Const.CMD_SYNC_TIMEOUT_MS)
        if resp is None:
            raise CcException('CcApp received no response from MainController to SET_MODE command')		# WARN?
        if ((not isinstance(resp, MainResp)) or (resp.token != MainResp.Token.OK)):
            raise CcException('CcApp received unexpected response from MainController to SET_MODE command')

    def set_mode_auto(self):
        resp = self.ep_main_master.send_cmd_sync(MainCmd(MainCmd.Token.SET_MODE, (CcMode.AUTO,)), Const.CMD_SYNC_TIMEOUT_MS)
        if resp is None:
            raise CcException('CcApp received no response from MainController to SET_MODE command')		# WARN?
        if ((not isinstance(resp, MainResp)) or (resp.token != MainResp.Token.OK)):
            raise CcException('CcApp received unexpected response from MainController to SET_MODE command')

