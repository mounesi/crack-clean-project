#!/usr/bin/env python3
# coding=utf-8

import csv
import getopt
import os
import sys

from edgetpu.detection.engine import DetectionEngine
import numpy
from PIL import Image
from PIL import ImageDraw

import crackthresh


IMG_DIM = 300
PIL_RESAMP = Image.ANTIALIAS


def main(argv):
    # process args
    try:
        (opts, args) = getopt.getopt(
            argv,
            "a:d:hi:l:m:o:r:s:",
            [
                "athresh=",
                "dthresh=",
                "help",
                "indir=",
                "labelid=",
                "model=",
                "outdir="
                "aradius=",
                "sthresh=",
            ]
        )
    except getopt.GetoptError:
        usage(1)
    arg_athresh = None
    arg_dthresh = None
    arg_indir   = None
    arg_labelid = None
    arg_model   = None
    arg_outdir  = None
    arg_aradius = None
    arg_sthresh = None
    for (opt,arg) in opts:
        if opt in ("-a", "--athresh"):
            arg_athresh = arg
        elif opt in ("-d", "--dthresh"):
            arg_dthresh = arg
        elif opt in ("-h", "--help"):
            usage(0)
        elif opt in ("-i", "--indir"):
            arg_indir = arg
        elif opt in ("-l", "--labelid"):
            arg_labelid = arg
        elif opt in ("-m", "--model"):
            arg_model = arg
        elif opt in ("-o", "--outdir"):
            arg_outdir = arg
        elif opt in ("-r", "--aradius"):
            arg_aradius = arg
        elif opt in ("-s", "--sthresh"):
            arg_sthresh = arg
        else:
            usage(1)
    if (
        (arg_athresh is None) or
        (arg_dthresh is None) or
        (arg_indir   is None) or
        (arg_labelid is None) or
        (arg_model   is None) or
        (arg_outdir  is None) or
        (arg_aradius is None) or
        (arg_sthresh is None)
    ):
        usage(1)
    # parse adaptive_thresh
    try:
        adaptive_thresh = float(arg_athresh.replace('_','-'))
    except ValueError:
        usage(1)
# allow negative
#    if ((adaptive_thresh < float(0)) or (adaptive_thresh > float(1))):
#        usage(1)
    # parse detect_thresh
    try:
        detect_thresh = float(arg_dthresh)
    except ValueError:
        usage(1)
    if ((detect_thresh < float(0)) or (detect_thresh > float(1))):
        usage(1)
    # parse path_indir
    path_indir = arg_indir
    # parse label_id
    try:
        label_id = int(arg_labelid)
    except ValueError:
        usage(1)
    # parse path_model
    path_model = arg_model
    # parse path_outdir
    path_outdir = arg_outdir
    # parse adaptive_radius
    try:
        adaptive_radius = int(arg_aradius)
    except ValueError:
        usage(1)
    if (adaptive_radius < 1):
        usage(1)
    # parse simple_thresh
    try:
        simple_thresh = int(arg_sthresh)
    except ValueError:
        usage(1)
    if ((simple_thresh < 0) or (simple_thresh > 255)):
        usage(1)
    # process
    res = process(path_indir, path_model, label_id, detect_thresh, simple_thresh, adaptive_radius, adaptive_thresh, path_outdir)
    if (res):
        print('[success]')
        sys.exit(0)
    else:
        print('[failure]')
        sys.exit(1)

def usage(exit_code):
    print('USAGE:')
    print('  ' + appname + ' PARAMS')
    print('')
    print('REQUIRED PARAMS:')
    print('  -i, --indir=   INPUT_DIR  directory of images to process')
    print('  -m, --model=   MODEL      model file')
    print('  -l, --labelid= LABEL_ID   crack label ID')
    print('  -d, --dthresh= DTHRESH    detection threshold')
    print('  -s, --sthresh= STHRESH    simple threshold')
    print('  -a, --athresh= ATHRESH    adaptive threshold (use "_" for negative)')
    print('  -r, --aradius= ARADIUS    adaptive radius')
    print('  -o, --outdir=  OUTPUT_DIR output directory')
    print('')
    print('OPTIONAL PARAMS:')
    print('  -h, --help        show this usage synopsis')
    print('')
    sys.exit(exit_code)

def process(path_indir, path_model, label_id, detect_thresh, simple_thresh, adaptive_radius, adaptive_thresh, path_outdir):
    #
    if not os.access(path_indir, os.R_OK):
        print('error: input directory not readable')
        return False
    #
    try:
        os.mkdir(path_outdir)
    except PermissionError:
        print('error: PermissionError creating output directory')
        return False
    except FileExistsError:
        print('warning: output directory already exists')
    if not os.access(path_outdir, os.W_OK):
        print('error: output directory not writable')
        return False
    path_outdir_simple = os.path.join(path_outdir, 'simple')
    try:
        os.mkdir(path_outdir_simple)
    except PermissionError:
        print('error: PermissionError creating simple output directory')
        return False
    except FileExistsError:
        print('warning: simple output directory already exists')
    if not os.access(path_outdir_simple, os.W_OK):
        print('error: simple output directory not writable')
        return False
    path_outdir_adaptive = os.path.join(path_outdir, 'adaptive')
    try:
        os.mkdir(path_outdir_adaptive)
    except PermissionError:
        print('error: PermissionError creating adaptive output directory')
        return False
    except FileExistsError:
        print('warning: adaptive output directory already exists')
    if not os.access(path_outdir_adaptive, os.W_OK):
        print('error: adaptive output directory not writable')
        return False
    # initialize DetectionEngine
    engine = DetectionEngine(path_model)
    #
    num_lt_one = 0
    num_eq_one = 0
    num_gt_one = 0
    for fn in os.listdir(path_indir):
        if not (fn.endswith('.png') or fn.endswith('.PNG')):
            print('skipping file: ' + fn)
            continue
        nd = process_image(path_indir, fn, engine, label_id, detect_thresh, simple_thresh, adaptive_radius, adaptive_thresh, path_outdir_simple, path_outdir_adaptive)
        if nd is None:
            print('error processing image')
            return False
        if (nd < 1):
            num_lt_one += 1
        elif (nd == 1):
            num_eq_one += 1
        elif (nd > 1):
            num_gt_one += 1
    print('REPORT:')
    print('  detection threshold:                  ' + str(detect_thresh))
    print('  simple threshold:                     ' + str(simple_thresh))
    print('  adaptive threshold:                   ' + '{:4.2f}'.format(adaptive_thresh))
    print('  adaptive radius:                      ' + str(adaptive_radius))
    print('  # images w/ <1 crack detected:        ' + str(num_lt_one))
    print('  # images w/ exactly 1 crack detected: ' + str(num_eq_one))
    print('  # images w/ >1 crack detected:        ' + str(num_gt_one))
    return True

# returns None on error
def process_image(path_indir, fn_img, engine, label_id, detect_thresh, simple_thresh, adaptive_radius, adaptive_thresh, path_outdir_simple, path_outdir_adaptive):
    # load image
    img = Image.open(os.path.join(path_indir, fn_img))
    if (img.mode != 'L'):
        print('error: invalid image mode')
        return None
    if (img.width < img.height):
        print('error: invalid image dimensions: ' + str(img.width) + ',' + str(img.height))
        return None

    img = img.crop(((img.width-img.height),0,img.width,img.height))
    if (img.width != img.height):
        print('error: crop')
        return None
    if (img.width != IMG_DIM):
        img = img.resize((IMG_DIM,IMG_DIM), PIL_RESAMP)
    img_dim = img.width
    img_rgb = img.convert('RGB')
    ans = engine.DetectWithImage(
        img_rgb,
        threshold=detect_thresh,
        keep_aspect_ratio=True,
        relative_coord=False,
        top_k=10
    )
    #
    img_simple = img_rgb.copy()
    draw_simple = ImageDraw.Draw(img_simple)
    img_adaptive = img_rgb.copy()
    draw_adaptive = ImageDraw.Draw(img_adaptive)
    #
    num_detections = 0
    #
    xc0 = None
    yc0 = None
    xc1 = None
    yc1 = None
    if ans:
        for obj in ans:
            if (obj.label_id == label_id):
                num_detections += 1
                xc0 = max(0, int(round(obj.bounding_box[0][0])))
                yc0 = max(0, int(round(obj.bounding_box[0][1])))
                xc1 = min((img_dim - 1), int(round(obj.bounding_box[1][0])))
                yc1 = min((img_dim - 1), int(round(obj.bounding_box[1][1])))
    if (num_detections != 1):
        img_simple.save(os.path.join(path_outdir_simple, fn_img))
        img_adaptive.save(os.path.join(path_outdir_adaptive, fn_img))
        return num_detections
    #
    imgarr = numpy.asarray(img)
    crop = imgarr[yc0:(yc1+1),xc0:(xc1+1)]
    imgbytes = crop.tobytes(order='C')
    # do simple
    (x_vals, y_vals, xy_vals) = crackthresh.filter_simple(imgbytes, xc1-xc0+1, yc1-yc0+1, xc0, yc0, simple_thresh)
    draw_simple.point(xy_vals)
    A = numpy.vstack([x_vals, numpy.ones(len(x_vals))]).T
    (m, b_px) = numpy.linalg.lstsq(A, y_vals, rcond=None)[0]
    draw_simple.line((0, b_px, (img_dim - 1), (m * (img_dim - 1)) + b_px), fill=128)
    draw_simple.rectangle(((xc0,yc0),(xc1+1,yc1+1)), outline='red')
    img_simple.save(os.path.join(path_outdir_simple, fn_img))
    # do adaptive
    (x_vals, y_vals, xy_vals) = crackthresh.filter_adaptive(imgbytes, xc1-xc0+1, yc1-yc0+1, xc0, yc0, adaptive_thresh, adaptive_radius)
    draw_adaptive.point(xy_vals)
    A = numpy.vstack([x_vals, numpy.ones(len(x_vals))]).T
    (m, b_px) = numpy.linalg.lstsq(A, y_vals, rcond=None)[0]
    draw_adaptive.line((0, b_px, (img_dim - 1), (m * (img_dim - 1)) + b_px), fill=128)
    draw_adaptive.rectangle(((xc0,yc0),(xc1+1,yc1+1)), outline='red')
    img_adaptive.save(os.path.join(path_outdir_adaptive, fn_img))
    return num_detections


if __name__ == '__main__':
    appname = sys.argv[0]
    main(sys.argv[1:])

