# coding=utf-8

import time
import tkinter
from tkinter import messagebox
import traceback

from PIL import Image, ImageTk

from .const import Const
from .filter_mode import FilterMode


class CcGui(object):
    COLOR_IMG_ABSENT    = '#D9D9D9'
    EVENT_ENTER_KEY     = '<Return>'
    EVENT_KBD_FOCUS_OUT = '<FocusOut>'

    def __init__(self, cc_app, show_images, update_period_ms):
        self.cc_app = cc_app
        self.show_images = show_images
        self.update_period_ms = update_period_ms
        self.IMG_DIM = Const.DETECTION_IMG_DIM
        self.pi_latest = None	# stores PhotoImage reference to prevent GC
        self.img_empty = Image.new('RGB', (self.IMG_DIM, self.IMG_DIM), color = CcGui.COLOR_IMG_ABSENT)

        self.root                     = None
        self.frame                    = None
        self.label_img                = None
        self.label_mode               = None
        self.label_detect_thresh      = None
        self.label_simpfilter_thresh  = None
        self.label_adaptfilter_thresh = None
        self.label_adaptfilter_radius = None
        self.label_ips                = None
        self.label_dccallms           = None
        self.label_targetmm           = None
        self.label_imgagems           = None
        self.label_ymm                = None
        self.sv_detect_thresh         = None
        self.entry_detect_thresh      = None
        self.sv_simpfilter_thresh     = None
        self.entry_simpfilter_thresh  = None
        self.sv_adaptfilter_thresh    = None
        self.entry_adaptfilter_thresh = None
        self.sv_adaptfilter_radius    = None
        self.entry_adaptfilter_radius = None
        self.tm_last_proc_check       = None

        self.iv_filtermode = None
        self.radio_filtermode_simple = None
        self.radio_filtermode_adaptive = None

    def toggle_mode(self):
        self.cc_app.toggle_mode()

    def exit(self):
        self.frame.quit()

    def service(self):
        if not self.proc_check():
            print('exiting application due to one or more terminated processes')
            self.exit()
        self.update_status()
        self.root.after(self.update_period_ms, self.service)

    def set_detect_thresh_handler(self, event):
        val_s = self.sv_detect_thresh.get()
        val = None
        try:
            val = float(val_s)
        except ValueError:
            pass
        if val is not None:								# TODO: enforce values
            self.cc_app.set_detect_thresh(val)
        self.sv_detect_thresh.set('')

    def set_simpfilter_thresh_handler(self, event):
        val_s = self.sv_simpfilter_thresh.get()
        val = None
        try:
            val = int(val_s)
        except ValueError:
            pass
        if val is not None:								# TODO: enforce values
            self.cc_app.set_simpfilter_thresh(val)
        self.sv_simpfilter_thresh.set('')

    def set_adaptfilter_thresh_handler(self, event):
        val_s = self.sv_adaptfilter_thresh.get()
        val = None
        try:
            val = float(val_s)
        except ValueError:
            pass
        if ((val is not None) and ((val >= float(0)) and (val <= float(1)))):		# TODO: add MAGIC to Const
            self.cc_app.set_adaptfilter_thresh(val)
        self.sv_adaptfilter_thresh.set('')

    def set_adaptfilter_radius_handler(self, event):
        val_s = self.sv_adaptfilter_radius.get()
        val = None
        try:
            val = int(val_s)
        except ValueError:
            pass
        if val is not None:								# TODO: enforce > 1
            self.cc_app.set_adaptfilter_radius(val)
        self.sv_adaptfilter_radius.set('')

    def filtermode_handler(self):
        val = self.iv_filtermode.get()
        if (val == 1):			# MAGIC!
            self.cc_app.set_filter_mode_simple()
        elif (val == 2):			# MAGIC!
            self.cc_app.set_filter_mode_adaptive()
        else:
            pass
            # TODO

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
                self.pi_latest = ImageTk.PhotoImage(cc_status.img)
                if self.show_images:
                    self.label_img.configure(image=self.pi_latest)
                self.label_mode.configure(text=str(cc_status.cc_mode))
                self.label_detect_thresh.configure(text=str(cc_status.detect_thresh))
                self.label_simpfilter_thresh.configure(text=str(cc_status.simpfilter_thresh))
                self.label_adaptfilter_thresh.configure(text=str(cc_status.adaptfilter_thresh))
                self.label_adaptfilter_radius.configure(text=str(cc_status.adaptfilter_radius))
                if (cc_status.filter_mode == FilterMode.SIMPLE):
                    self.radio_filtermode_simple.select()
                    self.radio_filtermode_adaptive.deselect()
                elif (cc_status.filter_mode == FilterMode.ADAPTIVE):
                    self.radio_filtermode_simple.deselect()
                    self.radio_filtermode_adaptive.select()
                else:
                    self.radio_filtermode_simple.deselect()
                    self.radio_filtermode_adaptive.deselect()
                    # TODO
                self.label_ips.configure(text='{0:.1f}'.format(cc_status.ips))
                self.label_dccallms.configure(text='{0:.1f}'.format(cc_status.dc_call_ms))
                self.label_targetmm.configure(text=cc_status.target_mm_str)
                self.label_imgagems.configure(text='{0:.1f}'.format(cc_status.img_age_ms))
                ymm_str = '(none)' if cc_status.dc_y_mm is None else '{0:.1f}'.format(cc_status.dc_y_mm)
                self.label_ymm.configure(text=ymm_str)
            else:
                self.pi_latest = ImageTk.PhotoImage(self.img_empty)
                if self.show_images:
                    self.label_img.configure(image=self.pi_latest)
                self.label_mode.configure(text='')
                self.label_detect_thresh.configure(text='')
                self.label_simpfilter_thresh.configure(text='')
                self.label_adaptfilter_thresh.configure(text='')
                self.label_adaptfilter_radius.configure(text='')
                self.radio_filtermode_simple.deselect()
                self.radio_filtermode_adaptive.deselect()
                self.label_ips.configure(text='')
                self.label_dccallms.configure(text='')
                self.label_targetmm.configure(text='')
                self.label_imgagems.configure(text='')
                self.label_ymm.configure(text='')

    def run(self):
        self.init_gui()
        self.tm_last_proc_check = time.monotonic()
        self.root.after(0, self.service)
        self.root.mainloop()
        self.root.destroy()

    def init_gui(self):
        tkinter.Tk.report_callback_exception = self.errorbox
        self.root = tkinter.Tk()
        self.root.title(Const.APP_NAME)
        self.frame = tkinter.Frame(self.root)

        menu = tkinter.Menu(self.root, tearoff=0)
        menu_file = tkinter.Menu(menu, tearoff=0)
        menu.add_cascade(label='File', menu=menu_file)
        menu_file.add_command(label='Exit', command=self.exit)

        self.root.config(menu=menu)

        # image
        self.pi_latest = ImageTk.PhotoImage(self.img_empty)
        self.label_img = tkinter.Label(self.frame, image=self.pi_latest, borderwidth=2, relief=tkinter.SUNKEN, width=self.IMG_DIM, height=self.IMG_DIM)

        # static labels
        label_mode_name               = tkinter.Label(self.frame, text='Mode: ',               anchor=tkinter.W, justify=tkinter.LEFT)
        label_detect_thresh_name      = tkinter.Label(self.frame, text='detect_thresh: ',      anchor=tkinter.W, justify=tkinter.LEFT)
        label_simpfilter_thresh_name  = tkinter.Label(self.frame, text='simpfilter_thresh: ',  anchor=tkinter.W, justify=tkinter.LEFT)
        label_adaptfilter_thresh_name = tkinter.Label(self.frame, text='adaptfilter_thresh: ', anchor=tkinter.W, justify=tkinter.LEFT)
        label_adaptfilter_radius_name = tkinter.Label(self.frame, text='adaptfilter_radius: ', anchor=tkinter.W, justify=tkinter.LEFT)
        label_ips_name                = tkinter.Label(self.frame, text='IPS: ',                anchor=tkinter.W, justify=tkinter.LEFT)
        label_dccallms_name           = tkinter.Label(self.frame, text='dc call (ms): ',       anchor=tkinter.W, justify=tkinter.LEFT)
        label_targetmm_name           = tkinter.Label(self.frame, text='target (mm): ',        anchor=tkinter.W, justify=tkinter.LEFT)
        label_imgagems_name           = tkinter.Label(self.frame, text='img age (ms): ',       anchor=tkinter.W, justify=tkinter.LEFT)
        label_ymm_name                = tkinter.Label(self.frame, text='dc_y (mm): ',          anchor=tkinter.W, justify=tkinter.LEFT)
        label_ymm_name                = tkinter.Label(self.frame, text='dc_y (mm): ',          anchor=tkinter.W, justify=tkinter.LEFT)

        # dynamic labels
        self.label_mode               = tkinter.Label(self.frame, text='', anchor=tkinter.W, justify=tkinter.LEFT, relief=tkinter.SOLID, width=8)
        self.label_detect_thresh      = tkinter.Label(self.frame, text='', anchor=tkinter.W, justify=tkinter.LEFT, relief=tkinter.SOLID, width=8)
        self.label_simpfilter_thresh  = tkinter.Label(self.frame, text='', anchor=tkinter.W, justify=tkinter.LEFT, relief=tkinter.SOLID, width=8)
        self.label_adaptfilter_thresh = tkinter.Label(self.frame, text='', anchor=tkinter.W, justify=tkinter.LEFT, relief=tkinter.SOLID, width=8)
        self.label_adaptfilter_radius = tkinter.Label(self.frame, text='', anchor=tkinter.W, justify=tkinter.LEFT, relief=tkinter.SOLID, width=8)
        self.label_ips                = tkinter.Label(self.frame, text='', anchor=tkinter.W, justify=tkinter.LEFT, relief=tkinter.SOLID, width=8)
        self.label_dccallms           = tkinter.Label(self.frame, text='', anchor=tkinter.W, justify=tkinter.LEFT, relief=tkinter.SOLID, width=8)
        self.label_targetmm           = tkinter.Label(self.frame, text='', anchor=tkinter.W, justify=tkinter.LEFT, relief=tkinter.SOLID, width=8)
        self.label_imgagems           = tkinter.Label(self.frame, text='', anchor=tkinter.W, justify=tkinter.LEFT, relief=tkinter.SOLID, width=8)
        self.label_ymm                = tkinter.Label(self.frame, text='', anchor=tkinter.W, justify=tkinter.LEFT, relief=tkinter.SOLID, width=8)

        # entry
        self.sv_detect_thresh = tkinter.StringVar()
        self.entry_detect_thresh = tkinter.Entry(self.frame, width=6, textvariable=self.sv_detect_thresh)
        self.sv_detect_thresh.set('')
        self.entry_detect_thresh.bind(CcGui.EVENT_ENTER_KEY, self.set_detect_thresh_handler)
        self.entry_detect_thresh.bind(CcGui.EVENT_KBD_FOCUS_OUT, self.set_detect_thresh_handler)
        #
        self.sv_simpfilter_thresh = tkinter.StringVar()
        self.entry_simpfilter_thresh = tkinter.Entry(self.frame, width=6, textvariable=self.sv_simpfilter_thresh)
        self.sv_simpfilter_thresh.set('')
        self.entry_simpfilter_thresh.bind(CcGui.EVENT_ENTER_KEY, self.set_simpfilter_thresh_handler)
        self.entry_simpfilter_thresh.bind(CcGui.EVENT_KBD_FOCUS_OUT, self.set_simpfilter_thresh_handler)
        #
        self.sv_adaptfilter_thresh = tkinter.StringVar()
        self.entry_adaptfilter_thresh = tkinter.Entry(self.frame, width=6, textvariable=self.sv_adaptfilter_thresh)
        self.sv_adaptfilter_thresh.set('')
        self.entry_adaptfilter_thresh.bind(CcGui.EVENT_ENTER_KEY, self.set_adaptfilter_thresh_handler)
        self.entry_adaptfilter_thresh.bind(CcGui.EVENT_KBD_FOCUS_OUT, self.set_adaptfilter_thresh_handler)
        #
        self.sv_adaptfilter_radius = tkinter.StringVar()
        self.entry_adaptfilter_radius = tkinter.Entry(self.frame, width=6, textvariable=self.sv_adaptfilter_radius)
        self.sv_adaptfilter_radius.set('')
        self.entry_adaptfilter_radius.bind(CcGui.EVENT_ENTER_KEY, self.set_adaptfilter_radius_handler)
        self.entry_adaptfilter_radius.bind(CcGui.EVENT_KBD_FOCUS_OUT, self.set_adaptfilter_radius_handler)

        # radio buttons
        self.iv_filtermode = tkinter.IntVar()
        self.radio_filtermode_simple = tkinter.Radiobutton(self.frame, text='simple', variable=self.iv_filtermode, value=1, command=self.filtermode_handler)	# MAGIC!
        self.radio_filtermode_adaptive = tkinter.Radiobutton(self.frame, text='adaptive', variable=self.iv_filtermode, value=2, command=self.filtermode_handler)	# MAGIC!

        # buttons
        btn_toggle = tkinter.Button(self.frame, text='Toggle', command=self.toggle_mode)
        btn_exit   = tkinter.Button(self.frame, text='Exit',   command=self.exit)

        # grid
        self.frame.grid(                    column=0, row=0,  columnspan=1, rowspan=1)
        #
        self.label_img.grid(                column=0, row=0,  columnspan=3, rowspan=10, padx=4, pady=4, sticky='')
        label_mode_name.grid(               column=3, row=0,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        self.label_mode.grid(               column=4, row=0,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        btn_toggle.grid(                    column=5, row=0,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))

        label_detect_thresh_name.grid(      column=3, row=1,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        self.label_detect_thresh.grid(      column=4, row=1,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        self.entry_detect_thresh.grid(      column=5, row=1,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        label_simpfilter_thresh_name.grid(  column=3, row=2,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        self.label_simpfilter_thresh.grid(  column=4, row=2,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        self.entry_simpfilter_thresh.grid(  column=5, row=2,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        label_adaptfilter_thresh_name.grid( column=3, row=3,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        self.label_adaptfilter_thresh.grid( column=4, row=3,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        self.entry_adaptfilter_thresh.grid( column=5, row=3,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        label_adaptfilter_radius_name.grid( column=3, row=4,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        self.label_adaptfilter_radius.grid( column=4, row=4,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        self.entry_adaptfilter_radius.grid( column=5, row=4,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))

        label_ips_name.grid(                column=3, row=5,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        self.label_ips.grid(                column=4, row=5,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        label_dccallms_name.grid(           column=3, row=6,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        self.label_dccallms.grid(           column=4, row=6,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        label_imgagems_name.grid(           column=3, row=7,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        self.label_imgagems.grid(           column=4, row=7,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        label_ymm_name.grid(                column=3, row=8,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        self.label_ymm.grid(                column=4, row=8,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        label_targetmm_name.grid(           column=3, row=9,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        self.label_targetmm.grid(           column=4, row=9,  columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))

        self.radio_filtermode_simple.grid(  column=0, row=10, columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        self.radio_filtermode_adaptive.grid(column=1, row=10, columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))
        btn_exit.grid(                      column=2, row=10, columnspan=1, rowspan=1,  padx=4, pady=4, sticky=(tkinter.W + tkinter.E))

    def errorbox(self, exc, val, tb):
        traceback.print_tb(tb)
        err = type(val).__name__ + ': ' + str(val)
        messagebox.showerror('Exception', err)	# blocks
        self.exit()

