# coding=utf-8

from edgetpu.detection.engine import DetectionEngine

from .const import Const
from .controller import Controller
from .crack_detect import CrackDetect
from .detection_result import DetectionResult
from .exceptions import DetectionException
from .filter_mode import FilterMode
from .ipc.detection_cmd import DetectionCmd
from .ipc.detection_resp import DetectionResp
from .ipc.endpoint import Endpoint


class DetectionController(Controller):

    def __init__(self, endpoint, params):
        super().__init__(endpoint, params)
        self.label_path = self.params[0]
        self.model_path = self.params[1]
        self.labels = None
        self.engine = None

    def init(self):
        lmap = DetectionController.load_label_map(self.label_path)
        labels = [
            Const.DETECTION_LABEL_CRACK,
            Const.DETECTION_LABEL_CIRCLE,
            Const.DETECTION_LABEL_SQUARE
        ]
        (lid_crack, lid_circle, lid_square) = DetectionController.lookup_labels(lmap, labels)
        self.engine = DetectionEngine(self.model_path)
        self.crackdetect = CrackDetect(
            Const.DETECTION_IMG_DIM,
            lid_crack,
            lid_circle,
            lid_square,
            Const.CALIBRATION_LG_MM,
            Const.CALIBRATION_GUID_CENTER_X_PX,
            Const.CALIBRATION_SCALING_FACTOR,
        )

    def deinit(self):
        # shutdown all queues that we write to
        Endpoint.shutdown_queue(self.endpoint.txq)
        # delete refs
        del self.labels
        del self.engine
        del self.crackdetect

    def start(self):
        crack_box = Const.DETECTION_CRACK_BOX_DEFAULT
        while True:
            tup = self.endpoint.get_cmd(True)
            (cmd_op_id, cmd) = tup
            if not isinstance(cmd, DetectionCmd):
                self.endpoint.send_resp(cmd_op_id, DetectionResp(DetectionResp.Token.ERROR, ()))
                raise DetectionException('DetectionController received unexpected OpObj')
            if (cmd.token == DetectionCmd.Token.TERMINATE):
                self.endpoint.send_resp(cmd_op_id, DetectionResp(DetectionResp.Token.OK, ()))
                break
            elif (cmd.token == DetectionCmd.Token.IS_READY):
                self.endpoint.send_resp(cmd_op_id, DetectionResp(DetectionResp.Token.TRUE, ()))
            elif (cmd.token == DetectionCmd.Token.DETECT):				# TODO: validate # args/types?/vals?/etc.
                img_latest = cmd.params[0]
                detect_thresh = cmd.params[1]
                simpfilter_thresh = cmd.params[2]
                adaptfilter_thresh = cmd.params[3]
                adaptfilter_radius = cmd.params[4]
                filter_mode = cmd.params[5]
                # TODO: use crack_det_cnt, ultimately in CcStatus
                (y_mm, img, crack_det_cnt, inferencing_time, crack_box) = self.crackdetect.process_image(
                    self.engine,
                    img_latest.img,
                    crack_box,
                    detect_thresh,
                    simpfilter_thresh,
                    adaptfilter_thresh,
                    adaptfilter_radius,
                    (filter_mode == FilterMode.ADAPTIVE)
                )
                #print('0:\t' + str(crack_detected) + '\t' + str(crack_box))
                # FIXME: crackdetect is currently returning type numpy.float64, not float
                # TODO: can it ever return None for y_mm?
                y_mm = None if (y_mm is None) else float(y_mm)
                result = DetectionResult(y_mm, img)
                self.endpoint.send_resp(cmd_op_id, DetectionResp(DetectionResp.Token.DETECTION_RESULT, (result,)))
            else:
                self.endpoint.send_resp(cmd_op_id, DetectionResp(DetectionResp.Token.ERROR, ()))
                raise DetectionException('DetectionController received unexpected command')

    @staticmethod
    def lookup_labels(lmap, labels):
        lids = []
        for label in labels:
            lid = lmap.get(label)
            if lid is None:
                raise DetectionException('error looking up label "' + label + '"')
            lids.append(lid)
        return lids

    @staticmethod
    def load_label_map(path):
        with open(path, 'rU') as f:
            lmap = {}
            lids = set()
            while True:
                line = f.readline()
                if not line:
                    break
                fields = line.split()
                if (len(fields) != 2):
                    raise DetectionException('error parsing label file')
                lid = int(fields[0])
                if (lid in lids):
                    raise DetectionException('error parsing label file: duplicate label ID encountered')
                label = fields[1]
                if (label in lmap):
                    raise DetectionException('error parsing label file: duplicate label encountered')
                lids.add(lid)
                lmap[label] = lid
        return lmap

    # for use in a ControllerProcess
    @staticmethod
    def worker(endpoint, params):
        print('initializing DetectionController...')
        controller = DetectionController(endpoint, params)
        controller.init()
        print('starting DetectionController...')
        try:
            controller.start()
        except DetectionException as e:
            print('DetectionException: ' + str(e))
        print('deinitializing DetectionController...')
        controller.deinit()
        print('exiting DetectionController worker...')

