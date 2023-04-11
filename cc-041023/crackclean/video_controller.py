# coding=utf-8

import time

from .controller import Controller
from .exceptions import SpinCamException
from .exceptions import VideoException
from .spin_cam import SpinCam
from .video_image import VideoImage
from .ipc.endpoint import Endpoint
from .ipc.video_cmd import VideoCmd
from .ipc.video_resp import VideoResp


class VideoController(Controller):

    def __init__(self, endpoint, params):
        super().__init__(endpoint, params)
        self.img_latest = None
        self.spin_cam   = None

    def init(self):
        self.img_latest = VideoImage(None, None)
        self.spin_cam = SpinCam()
        try:
            self.spin_cam.init()
        except SpinCamException as e:
            self.deinit()
            raise VideoException('VideoController init failed: SpinCamException: %s' % e)

    def deinit(self):
        self.spin_cam.deinit()
        # shutdown all queues that we write to
        Endpoint.shutdown_queue(self.endpoint.txq)
        # delete refs
        del self.img_latest
        del self.spin_cam

    # TODO: catch/handle SpinCamException
    def start(self):
        self.spin_cam.begin_acquisition()
        while True:
            tup = self.endpoint.get_cmd(False)
            if tup is not None:
                (cmd_op_id, cmd) = tup
                if not isinstance(cmd, VideoCmd):
                    self.endpoint.send_resp(cmd_op_id, VideoResp(VideoResp.Token.ERROR, ()))
                    raise VideoException('VideoController received unexpected OpObj')
                if (cmd.token == VideoCmd.Token.TERMINATE):
                    self.endpoint.send_resp(cmd_op_id, VideoResp(VideoResp.Token.OK, ()))
                    break
                elif (cmd.token == VideoCmd.Token.IS_READY):
                    self.endpoint.send_resp(cmd_op_id, VideoResp(VideoResp.Token.TRUE, ()))
                elif (cmd.token == VideoCmd.Token.GET_LATEST_IMG):
                    self.endpoint.send_resp(cmd_op_id, VideoResp(VideoResp.Token.LATEST_IMG, (self.img_latest,)))
                else:
                    self.endpoint.send_resp(cmd_op_id, VideoResp(VideoResp.Token.ERROR, ()))
                    raise VideoException('VideoController received unexpected command')
            img_pil = self.spin_cam.get_next_image()
            img_time = time.time()
            if img_pil is not None:
                self.img_latest = VideoImage(img_pil, img_time)
            else:
                # TODO: log
                #print('image incomplete; image status = %d' % img_result.GetImageStatus())
                pass
            #time.sleep(0.001)		# not needed; loop is not hot

    # for use in a ControllerProcess
    @staticmethod
    def worker(endpoint, params):
        print('initializing VideoController...')
        controller = VideoController(endpoint, params)
        controller.init()
        print('starting VideoController...')
        try:
            controller.start()
        except VideoException as e:
            print('VideoException: ' + str(e))
        controller.spin_cam.end_acquisition()
        print('deinitializing VideoController...')
        controller.deinit()
        print('exiting VideoController worker...')

