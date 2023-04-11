# coding=utf-8

import math
import time
import numpy
from PIL import Image
from PIL import ImageDraw

import crackthresh


class CrackDetect(object):

    COLOR_FILTER_PTS        = '#FFFF00FF'
    COLOR_LINE              = '#0000FFFF'
    COLOR_BBOX_DETECTED     = '#00FF00FF'
    COLOR_BBOX_NOT_DETECTED = '#FF0000FF'

    BBOX_VERT_GROWTH_FACTOR       = 0.4
    BBOX_VERT_GROWTH_THRESHOLD_PX = 100
    DETECTION_MAX_OBJECTS         = 10
    LSTSQ_MIN_PTS                 = 40

    def __init__(self, img_dim, lid_crack, lid_circle, lid_square, lg_mm, guid_center_x_px, scaling_factor):
        self.img_dim = img_dim
        self.lid_crack = lid_crack
        self.lid_circle = lid_circle
        self.lid_square = lid_square
        self.lg_mm = lg_mm
        self.guid_center_x_px = guid_center_x_px
        self.scaling_factor = scaling_factor
        #
        self.lx_mm = lg_mm - (guid_center_x_px * self.scaling_factor)

    def process_image(self, engine, img_l, cbox_prev, detect_thresh, simpfilter_thresh, adaptfilter_thresh, adaptfilter_radius, adaptive):
        img_rgb = img_l.convert('RGB')
        draw_rgb = ImageDraw.Draw(img_rgb)
        # perform detection
        ts_begin = time.monotonic()
        cands = engine.DetectWithImage(img_rgb, threshold=detect_thresh, keep_aspect_ratio=True, relative_coord=False, top_k=CrackDetect.DETECTION_MAX_OBJECTS)
        infer_time = time.monotonic() - ts_begin
        # get highest-scoring crack_obj
        crack_obj = None
        crack_det_cnt = 0
        if cands:
            hi_score = None
            for obj in cands:
                if (obj.label_id == self.lid_crack):
                    if ((hi_score is None) or (hi_score < obj.score)):
                        crack_obj = obj
                        hi_score = obj.score
                    crack_det_cnt += 1
        # determine region to filter
        (x0, y0, x1, y1) = [None] * 4
        if crack_obj is not None:
            # calculate region by transforming and clipping detected bounding box
            x0 = max(0, int(round(crack_obj.bounding_box[0][0])))
            y0 = max(0, int(round(crack_obj.bounding_box[0][1])))
            x1 = min((self.img_dim - 1), int(round(crack_obj.bounding_box[1][0])))
            y1 = min((self.img_dim - 1), int(round(crack_obj.bounding_box[1][1])))
        else:
            # estimate region
            prev_height = int((cbox_prev[3] - cbox_prev[1] + 1))
            if (prev_height < CrackDetect.BBOX_VERT_GROWTH_THRESHOLD_PX):
                # base region on previous cbox, adding 40% to the height and maxing out the width
                delta_y = int(round(prev_height * CrackDetect.BBOX_VERT_GROWTH_FACTOR / 2))
                x0 = 0
                y0 = max(0, cbox_prev[1] - delta_y)
                x1 = self.img_dim - 1
                y1 = min((self.img_dim - 1), cbox_prev[3] + delta_y)
            else:
                # use previous cbox as-is
                (x0, y0, x1, y1) = cbox_prev
        # execute filter
        imgbytes = CrackDetect.__crop_to_bytes(img_l, x0, y0, x1, y1)
        if adaptive:
            (x_vals, y_vals, xy_vals) = crackthresh.filter_adaptive(imgbytes, x1-x0+1, y1-y0+1, x0, y0, adaptfilter_thresh, adaptfilter_radius)
        else:
            (x_vals, y_vals, xy_vals) = crackthresh.filter_simple(imgbytes, x1-x0+1, y1-y0+1, x0, y0, simpfilter_thresh)
        # draw filter points
        draw_rgb.point(xy_vals, fill=CrackDetect.COLOR_FILTER_PTS)
        # conditionally calculate y_mm
        if (len(xy_vals) > CrackDetect.LSTSQ_MIN_PTS):
            (m, b_px) = CrackDetect.__least_squares(x_vals, y_vals)
            y_mm = -m * self.lx_mm + (b_px - (self.img_dim / 2)) * self.scaling_factor
            # draw line
            draw_rgb.line((0, b_px, (self.img_dim - 1), (m * (self.img_dim - 1)) + b_px), fill=CrackDetect.COLOR_LINE)
        else:
            y_mm = None
        # draw cbox
        if crack_obj is not None:
            rect_color = CrackDetect.COLOR_BBOX_DETECTED
        else:
            rect_color = CrackDetect.COLOR_BBOX_NOT_DETECTED
        cbox = [x0, y0, x1, y1]
        # PIL rectangle() docs seem to indicate that it follows the usual PIL convention in which
        # the second point of a bounding box addresses the column/row just beyond the box ("The
        # second point is just outside the drawn rectangle.".  However, rectangle() doesn't behave
        # this way, at least not in the versions that I've tested.  Examining the source indicates
        # the same.  So, rather than using [x0, y0, x1 + 1, y1 + 1], we use [x0, y0, x1, y1] here.
        draw_rgb.rectangle(cbox, outline=rect_color)
        # return results
        return (y_mm, img_rgb, crack_det_cnt, infer_time, cbox)

    @staticmethod
    def __least_squares(x_vals, y_vals):
        a = numpy.vstack([x_vals, numpy.ones(len(x_vals))]).T
        (m, b_px) = numpy.linalg.lstsq(a, y_vals, rcond=None)[0]
        return (m, b_px)

    # convert a cropped region of a PIL mode-L image to a Python bytes object
    @staticmethod
    def __crop_to_bytes(img_l, x0, y0, x1, y1):
        imgarr = numpy.asarray(img_l)
        crop = imgarr[y0:(y1+1), x0:(x1+1)]
        return crop.tobytes(order='C')

