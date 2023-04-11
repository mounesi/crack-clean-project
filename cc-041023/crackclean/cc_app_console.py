# coding=utf-8

import atexit
import time

from .cc_app import CcApp
from .const import Const


class CcAppConsole(object):

    def __init__(self, context, update_period_ms):
        self.cc_app = CcApp(context)
        self.update_period_s = (update_period_ms / 1000)
        self.tm_last_proc_check = None

    def run(self):
        atexit.register(self.atexit_func)
        self.cc_app.start()
        self.tm_last_proc_check = time.monotonic()
        while True:
            if not self.proc_check():
                print('exiting application due to one or more terminated processes')
                break
            self.update_status()
            time.sleep(self.update_period_s)
        self.cc_app.stop()
        atexit.unregister(self.atexit_func)

    # returns False if terminated proc found, else True
    def proc_check(self):
        tm = time.monotonic()
        if ((tm - self.tm_last_proc_check) >= Const.APP_PROC_CHECK_MIN_INTERVAL_S):
            self.tm_last_proc_check = tm
            dead_procs = self.cc_app.dead_procs()
            if (len(dead_procs) > 0):
                for dp in dead_procs:
                    print('process "' + dp + '" has terminated')
                return False
        return True

    def update_status(self):
        cc_status = self.cc_app.get_status()
        if cc_status is not False:
            if cc_status is not None:
                print(
                    'mode: '               + str(cc_status.cc_mode)            + ';  ' +
                    'detect_thresh: '      + str(cc_status.detect_thresh)      + ';  ' +
                    'simpfilter_thresh: '  + str(cc_status.simpfilter_thresh)  + ';  ' +
                    'adaptfilter_thresh: ' + str(cc_status.adaptfilter_thresh) + ';  ' +
                    'adaptfilter_radius: ' + str(cc_status.adaptfilter_radius) + ';  ' +
                    'filter_mode: '        + str(cc_status.filter_mode)        + ';  ' +
                    'ips: '                + str(cc_status.ips)                + ';  ' +
                    'dc_call_ms: '         + str(cc_status.dc_call_ms)         + ';  ' +
                    'img_age_ms: '         + str(cc_status.img_age_ms)         + ';  ' +
                    'dc_y_mm: '            + str(cc_status.dc_y_mm)            + ';  ' +
                    'img: '                + str(cc_status.img)
                )
            else:
                print('[no status]')

    def atexit_func(self):
        self.cc_app.stop()

