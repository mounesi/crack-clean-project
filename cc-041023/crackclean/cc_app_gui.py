# coding=utf-8

import atexit

from .cc_app import CcApp
from .cc_gui import CcGui


class CcAppGui(object):

    def __init__(self, context, show_images, update_period_ms):
        self.cc_app = CcApp(context)
        self.show_images = show_images
        self.update_period_ms = update_period_ms

    def run(self):
        atexit.register(self.atexit_func)
        self.cc_app.start()
        cc_gui = CcGui(self.cc_app, self.show_images, self.update_period_ms)
        cc_gui.run()
        self.cc_app.stop()
        atexit.unregister(self.atexit_func)

    def atexit_func(self):
        self.cc_app.stop()

