# coding=utf-8

import PIL.Image
import PySpin

from .const import Const
from .exceptions import SpinCamException


class SpinCam(object):

    def __init__(self):
        self.spin_system = None
        self.spin_cams = None
        self.spin_cam = None

    def init(self):
        # NOTE: it's unclear if GetInstance(), GetCameras(), GetSize(), or Init()
        # can raise SpinnakerException
        try:
            self.spin_system = PySpin.System.GetInstance()
            self.spin_cams = self.spin_system.GetCameras()
            num_cams = self.spin_cams.GetSize()
            if num_cams < 1:
                raise SpinCamException('unable to find camera')
            elif num_cams > 1:
                raise SpinCamException('multiple cameras found')
            self.spin_cam = self.spin_cams[0]
            self.spin_cam.Init()
            self.config_cam()
        except PySpin.SpinnakerException as e:
            self.clean_spin_refs()
            raise SpinCamException('SpinCam init failed: SpinnakerException: %s' % e)
        except SpinCamException as e:
            self.clean_spin_refs()
            raise SpinCamException('SpinCamController init failed: SpinCamException: %s' % e)

    # TODO: document why this is important
    def clean_spin_refs(self):
        try:
            if self.spin_cam is not None:
                # DeInit() appears to be benign if camera not yet initialized
                self.spin_cam.DeInit()
            del self.spin_cam
        except AttributeError:
            pass
        try:
            if self.spin_cams is not None:
                self.spin_cams.Clear()
            del self.spin_cams
        except AttributeError:
            pass
        try:
            if self.spin_system is not None:
                self.spin_system.ReleaseInstance()
            del self.spin_system
        except AttributeError:
            pass

    def deinit(self):
        print('entering SpinCam.deinit()')
        self.clean_spin_refs()
        print('exiting SpinCam.deinit()')

    # NOTE: it's unclear what here, if anything, can raise SpinnakerException
    def config_cam(self):
        nodemap = self.spin_cam.GetNodeMap()
        nodemap_tldevice = self.spin_cam.GetTLDeviceNodeMap()
        nodemap_tlstream = self.spin_cam.GetTLStreamNodeMap()
        # load defaults
        SpinCam.geni_set_enum(nodemap, 'UserSetSelector', 'Default')
        SpinCam.geni_exec_cmd(nodemap, 'UserSetLoad')
        # set packet parameters
        SpinCam.geni_set_int(nodemap, 'GevSCPSPacketSize', Const.CAMERA_STREAM_CHANNEL_PACKET_SIZE)
        SpinCam.geni_set_int(nodemap, 'GevSCPD', Const.CAMERA_STREAM_CHANNEL_PACKET_DELAY)
        # set pixel format
        SpinCam.geni_set_enum(nodemap, 'PixelFormat', Const.CAMERA_PIXEL_FORMAT)
        # set video mode
        SpinCam.geni_set_enum(nodemap, 'VideoMode', Const.CAMERA_VIDEO_MODE)
        # set image geometry
        SpinCam.geni_set_int(nodemap, 'Width', Const.CAMERA_WIDTH)
        SpinCam.geni_set_int(nodemap, 'Height', Const.CAMERA_HEIGHT)
        # set image offset
        SpinCam.geni_set_int(nodemap, 'OffsetX', Const.CAMERA_OFFSET_X)
        SpinCam.geni_set_int(nodemap, 'OffsetY', Const.CAMERA_OFFSET_Y)
        # configure trigger
        SpinCam.geni_set_enum(nodemap, 'TriggerMode', 'Off')
        #SpinCam.geni_set_enum(nodemap, 'TriggerSource', 'Software')
        #SpinCam.geni_set_enum(nodemap, 'TriggerMode', 'On')
        # set acquisition mode
        SpinCam.geni_set_enum(nodemap, 'AcquisitionMode', 'Continuous')
        # set stream buffer parameters
        SpinCam.geni_set_enum(nodemap_tlstream, 'StreamBufferCountMode', 'Auto')
        #SpinCam.geni_set_enum(nodemap_tlstream, 'StreamBufferCountMode', 'Manual')
        #SpinCam.geni_set_int(nodemap_tlstream, 'StreamBufferCountManual', 3)‧‧‧# TODO: investigate
        SpinCam.geni_set_enum(nodemap_tlstream, 'StreamBufferHandlingMode', 'NewestOnly')

    def begin_acquisition(self):
        try:
            self.spin_cam.BeginAcquisition()
        except PySpin.SpinnakerException as e:
            raise SpinCamException('SpinnakerException: %s' % e)

    def end_acquisition(self):
        try:
            self.spin_cam.EndAcquisition()
        except PySpin.SpinnakerException as e:
            raise SpinCamException('SpinnakerException: %s' % e)

    # returns next image as a processed PIL image
    # returns None if image is incomplete
    def get_next_image(self):
        try:
            img_result = self.spin_cam.GetNextImage()
        except PySpin.SpinnakerException as e:
            raise SpinCamException('SpinnakerException: %s' % e)
        if img_result.IsIncomplete():
            return None
        img_ndarray = img_result.GetNDArray()
#        # sanity checks
#        width = img_result.GetWidth()
#        height = img_result.GetHeight()
#        if ((width != Const.CAMERA_WIDTH) or height != Const.CAMERA_HEIGHT):
#            raise SpinCamException('VideoController acquired image with unexpected geometry')
#
#        # TODO: check PixelFormat?
        # release image (Spinnaker docs don't make it clear why this is only required on success)
        img_result.Release()
        img_pil = PIL.Image.fromarray(img_ndarray, mode=Const.DETECTION_PIL_IMG_MODE)
        img_pil_resized = img_pil.resize((Const.DETECTION_IMG_DIM, Const.DETECTION_IMG_DIM), Const.DETECTION_PIL_RESAMP)
        return img_pil_resized

    @staticmethod
    def geni_set_int(nodemap, node_name, value):
        int_ptr = PySpin.CIntegerPtr(nodemap.GetNode(node_name))
        if not (PySpin.IsAvailable(int_ptr) and PySpin.IsWritable(int_ptr)):
            raise SpinCamException('CIntegerPtr "' + node_name + '" unavailable or unwritable')
        int_ptr.SetValue(value)

    @staticmethod
    def geni_set_enum(nodemap, node_name, entry_name):
        enum_ptr = PySpin.CEnumerationPtr(nodemap.GetNode(node_name))
        if not (PySpin.IsAvailable(enum_ptr) and PySpin.IsWritable(enum_ptr)):
            raise SpinCamException('CEnumerationPtr "' + node_name + '" unavailable or unwritable')
        #entry_ptr = enum_ptr.GetEntryByName(entry_name)
        entry_ptr = PySpin.CEnumEntryPtr(enum_ptr.GetEntryByName(entry_name))
        if not (PySpin.IsAvailable(entry_ptr) and PySpin.IsReadable(entry_ptr)):
            raise SpinCamException('CEnumEntryPtr "' + entry_name + '" unavailable or unreadable')
        enum_ptr.SetIntValue(entry_ptr.GetValue())

    @staticmethod
    def geni_exec_cmd(nodemap, node_name):
        cmd_ptr = PySpin.CCommandPtr(nodemap.GetNode(node_name))
        if not (PySpin.IsAvailable(cmd_ptr) and PySpin.IsWritable(cmd_ptr)):
            raise SpinCamException('CCommandPtr "' + node_name + '" unavailable or unwritable')
        cmd_ptr.Execute()

