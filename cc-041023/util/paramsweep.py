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

SIMPTHRESH_BEGIN = 0
SIMPTHRESH_END   = 255
SIMPTHRESH_INC   = 1
SIMPTHRESH_DRAW  = 108

ADAPTRADIUS_BEGIN = 1
ADAPTRADIUS_END   = 50
ADAPTRADIUS_INC   = 1
ADAPTRADIUS_DRAW  = 27

ADAPTTHRESH_PCT_BEGIN = -50
ADAPTTHRESH_PCT_END   = 50
ADAPTTHRESH_PCT_INC   = 1
ADAPTTHRESH_PCT_DRAW  = -7

COLOR_BBOX     = '#FF0000'
COLOR_FILTERPT = '#00FF00'

FIELDS_SIMP = [
    'IMAGE',
    'SIMP_THRESH',
    '#FN',
    '#TP',
    '#FP',
    'XC0',
    'YC0',
    'XC1',
    'YC1',
    'ERR'
]
FIELDS_ADAPT = [
    'IMAGE',
    'ADAPT_THRESH',
    'ADAPT_RADIUS',
    '#FN',
    '#TP',
    '#FP',
    'XC0',
    'YC0',
    'XC1',
    'YC1',
    'ERR'
]
FIELDS_SIMP_AVG = [
    'SIMP_THRESH',
    'ERR'
]
FIELDS_ADAPT_AVG = [
    'ADAPT_THRESH',
    'ADAPT_RADIUS',
    'ERR'
]


def main(argv):
    # process args
    try:
        (opts, args) = getopt.getopt(
            argv,
            "hd:i:l:k:m:o:r:",
            [
                "help",
                "dthresh=",
                "image=",
                "labelid=",
                "mask=",
                "model=",
                "outdir=",
                "ratios="
            ]
        )
    except getopt.GetoptError:
        usage(1)
    arg_dthresh = None
    arg_image   = None
    arg_labelid = None
    arg_mask    = None
    arg_model   = None
    arg_outdir  = None
    arg_ratios  = None
    for (opt,arg) in opts:
        if opt in ("-h", "--help"):
            usage(0)
        elif opt in ("-d", "--dthresh"):
            arg_dthresh = arg
        elif opt in ("-i", "--image"):
            arg_image = arg
        elif opt in ("-l", "--labelid"):
            arg_labelid = arg
        elif opt in ("-k", "--mask"):
            arg_mask = arg
        elif opt in ("-m", "--model"):
            arg_model = arg
        elif opt in ("-o", "--outdir"):
            arg_outdir = arg
        elif opt in ("-r", "--ratios"):
            arg_ratios = arg
        else:
            usage(1)
    if (
        (arg_dthresh is None) or
        (arg_image   is None) or
        (arg_labelid is None) or
        (arg_mask    is None) or
        (arg_model   is None) or
        (arg_outdir  is None) or
        (arg_ratios  is None)
    ):
        usage(1)
    # parse detect_thresh
    try:
        detect_thresh = float(arg_dthresh)
    except ValueError:
        usage(1)
    if ((detect_thresh < float(0)) or (detect_thresh > float(1))):
        usage(1)
    # parse path_img
    path_img = arg_image
    # parse label_id
    try:
        label_id = int(arg_labelid)
    except ValueError:
        usage(1)
    # parse path_mask
    path_mask = arg_mask
    # parse path_model
    path_model = arg_model
    # parse path_outdir
    path_outdir = arg_outdir
    # parse value_ratios
    value_ratios = []
    ratio_args = arg_ratios.split(',', -1)
    for ra in ratio_args:
        try:
            r = float(ra)
        except ValueError:
            usage(1)
        value_ratios.append(r)
    # process
    res = process(path_img, path_mask, path_model, label_id, value_ratios, detect_thresh, path_outdir)
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
    print('  -i, --image=   IMAGE      image to process (300x300 8-bit grayscale)')
    print('  -k, --mask=    MASK       mask image (300x300 24-bit RGB, mask pixels 0xFF0000)')
    print('  -r, --ratios=  RATIOS     comma-separated list of value ratios')
    print('  -m, --model=   MODEL      model file')
    print('  -l, --labelid= LABEL_ID   crack label ID')
    print('  -d, --dthresh= DTHRESH    detection threshold')
    print('  -o, --outdir=  OUTPUT_DIR output directory')
    print('')
    print('OPTIONAL PARAMS:')
    print('  -h, --help        show this usage synopsis')
    print('')
    sys.exit(exit_code)

def process(path_img, path_mask, path_model, label_id, value_ratios, detect_thresh, path_outdir):
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
    # load image
    img = Image.open(path_img)
    if (img.mode != 'L'):
        print('error: invalid image mode')
        return False
    if ((img.width != IMG_DIM) or (img.height != IMG_DIM)):
        print('error: invalid image dimensions')
        return False
    # load mask image
    img_mask = Image.open(path_mask)
    if (img_mask.mode != 'RGB'):
        print('error: invalid mask image mode')
        return False
    if ((img_mask.width != IMG_DIM) or (img_mask.height != IMG_DIM)):
        print('error: invalid mask image dimensions')
        return False
    # build crack point truth set
    crack_pts = set()
    for y in range(0, img_mask.height):
        for x in range(0, img_mask.width):
            coord = (x,y)
            gp = img_mask.getpixel(coord)
            if ((gp[0] == 0xFF) and (gp[1] == 0x00) and (gp[2] == 0x00)):
                crack_pts.add(coord)
    # initialize DetectionEngine
    engine = DetectionEngine(path_model)
    # save mask image for reference purposes
    img_mask.save(os.path.join(path_outdir, 'mask.png'))
    # process images
    map_simple = None
    map_adaptive = None
    for vr in value_ratios:
        print('processing ' + str(vr) + '...')
        # build test image
        img_test = make_img(img, vr)
        name_test = 'img_' + '{:4.2f}'.format(vr)
        # process image
        res = process_image(name_test, img_test, crack_pts, engine, label_id, detect_thresh, path_outdir)
        if res is None:
            return False
        (ms, ma, img_s, img_a) = res
        img_s.save(os.path.join(path_outdir, name_test + '-simple.png'))
        img_a.save(os.path.join(path_outdir, name_test + '-adaptive.png'))
        ms_keys = set(ms.keys())
        ma_keys = set(ma.keys())
        if map_simple is None:
            map_simple = {}
        else:
           if (set(map_simple.keys()) != ms_keys):
               print('error: assertion failed')
               return False
        if map_adaptive is None:
            map_adaptive = {}
        else:
           if (set(map_adaptive.keys()) != ma_keys):
               print('error: assertion failed')
               return False
        for k in ms_keys:
            if map_simple.get(k) is None:
                map_simple[k] = ms[k]
            else:
                map_simple[k] += ms[k]
        for k in ma_keys:
            if map_adaptive.get(k) is None:
                map_adaptive[k] = ma[k]
            else:
                map_adaptive[k] += ma[k]
    fn_csv = 'simple-averages.csv'
    path_csv = os.path.join(path_outdir, fn_csv)
    with open(path_csv, 'w', newline='\n') as f_out:
        writer = csv.DictWriter(
            f_out,
            fieldnames=FIELDS_SIMP_AVG,
            delimiter=',',
            doublequote=True,
            lineterminator='\n',
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL,
            skipinitialspace=False
        )
        writer.writeheader()
        for k in sorted(ms_keys):
            simp_thresh = k
            dict_row = {
                'SIMP_THRESH' : str(simp_thresh),
                'ERR'         : str(map_simple[k] / len(value_ratios))
            }
            writer.writerow(dict_row)
    fn_csv = 'adaptive-averages.csv'
    path_csv = os.path.join(path_outdir, fn_csv)
    with open(path_csv, 'w', newline='\n') as f_out:
        writer = csv.DictWriter(
            f_out,
            fieldnames=FIELDS_ADAPT_AVG,
            delimiter=',',
            doublequote=True,
            lineterminator='\n',
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL,
            skipinitialspace=False
        )
        writer.writeheader()
        for k in sorted(ma_keys):
            (adapt_radius, adapt_thresh) = k
            dict_row = {
                'ADAPT_THRESH' : str(adapt_thresh),
                'ADAPT_RADIUS' : str(adapt_radius),
                'ERR'          : str(map_adaptive[k] / len(value_ratios))
            }
            writer.writerow(dict_row)
    return True

# contract: width==height==IMG_DIM
def process_image(name, img, crack_pts, engine, label_id, detect_thresh, path_outdir):
    img_dim = img.width
    img_rgb = img.convert('RGB')
    cands = engine.DetectWithImage(
        img_rgb,
        threshold=detect_thresh,
        keep_aspect_ratio=True,
        relative_coord=False,
        top_k=10
    )
    x0 = None
    y0 = None
    x1 = None
    y1 = None
    for obj in cands:
        if (obj.label_id == label_id):
            #print('score: ' + str(obj.score))
            if x0 is None:
                x0 = max(0, int(round(obj.bounding_box[0][0])))
                y0 = max(0, int(round(obj.bounding_box[0][1])))
                x1 = min((img_dim - 1), int(round(obj.bounding_box[1][0])))
                y1 = min((img_dim - 1), int(round(obj.bounding_box[1][1])))
            else:
                print('warning: >1 crack detected; using first')
                break
    if x0 is None:
        print('error: <1 crack detected')
        return None
    imgarr = numpy.asarray(img)
    crop = imgarr[y0:(y1+1),x0:(x1+1)]
    imgbytes = crop.tobytes(order='C')
    map_simple = {}
    map_adaptive = {}
    img_s = img_rgb.copy()
    draw_s = ImageDraw.Draw(img_s)
    img_a = img_rgb.copy()
    draw_a = ImageDraw.Draw(img_a)
    # do simple
    fn_csv = name + '_' + 'simple' + '.csv'
    path_csv = os.path.join(path_outdir, fn_csv)
    with open(path_csv, 'w', newline='\n') as f_out:
        writer = csv.DictWriter(
            f_out,
            fieldnames=FIELDS_SIMP,
            delimiter=',',
            doublequote=True,
            lineterminator='\n',
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL,
            skipinitialspace=False
        )
        writer.writeheader()
        simpthresh = SIMPTHRESH_BEGIN
        while (simpthresh <= SIMPTHRESH_END):
            width = x1 - x0 + 1
            height = y1 - y0 + 1
            (x_vals, y_vals, xy_vals) = crackthresh.filter_simple(imgbytes, width, height, x0, y0, simpthresh)
            if (simpthresh == SIMPTHRESH_DRAW):
                draw_s.point(xy_vals, fill=COLOR_FILTERPT)
            crack_pts_crop = crop_points(crack_pts, x0, y0, x1, y1)
            (tp,fp,fn) = get_set_info(crack_pts_crop, x_vals, y_vals)
            err = (len(fp) + len(fn)) / (width * height)
            map_simple[simpthresh] = err
            dict_row = {
                'IMAGE'       : name,
                'SIMP_THRESH' : str(simpthresh),
                '#FN'         : str(len(fn)),
                '#TP'         : str(len(tp)),
                '#FP'         : str(len(fp)),
                'XC0'         : str(x0),
                'YC0'         : str(y0),
                'XC1'         : str(x1),
                'YC1'         : str(y1),
                'ERR'         : str(err)
            }
            writer.writerow(dict_row)
            simpthresh += SIMPTHRESH_INC
    # do adaptive
    fn_csv = name + '_' + 'adaptive' + '.csv'
    path_csv = os.path.join(path_outdir, fn_csv)
    with open(path_csv, 'w', newline='\n') as f_out:
        writer = csv.DictWriter(
            f_out,
            fieldnames=FIELDS_ADAPT,
            delimiter=',',
            doublequote=True,
            lineterminator='\n',
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL,
            skipinitialspace=False
        )
        writer.writeheader()
        adaptradius = ADAPTRADIUS_BEGIN
        while (adaptradius <= ADAPTRADIUS_END):
            adaptthresh_pct = ADAPTTHRESH_PCT_BEGIN
            while (adaptthresh_pct <= ADAPTTHRESH_PCT_END):
                adaptthresh = adaptthresh_pct / 100
                width = x1 - x0 + 1
                height = y1 - y0 + 1
                (x_vals, y_vals, xy_vals) = crackthresh.filter_adaptive(imgbytes, width, height, x0, y0, adaptthresh, adaptradius)
                if ((adaptthresh_pct == ADAPTTHRESH_PCT_DRAW) and (adaptradius == ADAPTRADIUS_DRAW)):
                    draw_a.point(xy_vals, fill=COLOR_FILTERPT)
                crack_pts_crop = crop_points(crack_pts, x0, y0, x1, y1)
                (tp,fp,fn) = get_set_info(crack_pts_crop, x_vals, y_vals)
                err = (len(fp) + len(fn)) / (width * height)
                map_adaptive[(adaptradius, adaptthresh)] = err
                dict_row = {
                    'IMAGE'        : name,
                    'ADAPT_THRESH' : '{:4.2f}'.format(adaptthresh),
                    'ADAPT_RADIUS' : str(adaptradius),
                    '#FN'          : str(len(fn)),
                    '#TP'          : str(len(tp)),
                    '#FP'          : str(len(fp)),
                    'XC0'          : str(x0),
                    'YC0'          : str(y0),
                    'XC1'          : str(x1),
                    'YC1'          : str(y1),
                    'ERR'          : str(err)
                }
                writer.writerow(dict_row)
                adaptthresh_pct += ADAPTTHRESH_PCT_INC
            adaptradius += ADAPTRADIUS_INC
    draw_s.rectangle([x0, y0, x1+1, y1+1], outline=COLOR_BBOX)
    draw_a.rectangle([x0, y0, x1+1, y1+1], outline=COLOR_BBOX)
    return (map_simple, map_adaptive, img_s, img_a)

def crop_points(pts, x0, y0, x1, y1):
    cropped = set()
    for p in pts:
        (x, y) = p
        if ((x >= x0) and (x <= x1) and (y >= y0) and (y <= y1)):
            cropped.add(p)
    return cropped

def get_set_info(crack_pts, x_vals, y_vals):
    result_pts = set()
    for i in range(0, len(x_vals)):
        result_pts.add((x_vals[i], y_vals[i]))
    tp = (crack_pts & result_pts)
    fp = (result_pts - crack_pts)
    fn = (crack_pts - result_pts)
    return (tp,fp,fn)

def make_img(img_src, ratio):
    vmap = {}
    for i in range(0,255+1):
        vmap[i] = max(0, min(255, int(round(i * ratio))))
    width = img_src.width
    height = img_src.height
    img_out = Image.new('L', (width, height))
    draw = ImageDraw.Draw(img_out)
    for y in range(0, height):
        for x in range(0, width):
            coord = (x,y)
            val = img_src.getpixel(coord)
            draw.point([coord], fill=vmap[val])
    return img_out


if __name__ == '__main__':
    appname = sys.argv[0]
    main(sys.argv[1:])

