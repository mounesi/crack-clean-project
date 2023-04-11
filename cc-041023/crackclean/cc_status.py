# coding=utf-8


class CcStatus(object):

    def __init__(self, cc_mode, detect_thresh, simpfilter_thresh, adaptfilter_thresh, adaptfilter_radius, filter_mode, ips, dc_call_ms, img_age_ms, dc_y_mm, target_mm_str, img):
        self.cc_mode = cc_mode
        self.detect_thresh = detect_thresh			# was: thresh
        self.simpfilter_thresh = simpfilter_thresh		# was: thresh_filt
        self.adaptfilter_thresh = adaptfilter_thresh
        self.adaptfilter_radius = adaptfilter_radius
        self.filter_mode = filter_mode
        self.ips = ips
        self.dc_call_ms = dc_call_ms
        self.img_age_ms = img_age_ms
        self.dc_y_mm = dc_y_mm
        self.target_mm_str = target_mm_str
        self.img = img

