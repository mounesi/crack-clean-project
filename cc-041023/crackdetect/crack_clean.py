from PIL import Image
import numpy as np
from crackdetect import config as c
#from edgetpu.detection.engine import DetectionEngine
import math
import time
from PIL import ImageDraw
#import time

# optional switches
DEBUG = c.DEBUG 
TIME = c.TIME
DRAW = c.DRAW
FILTER = c.FILTER

# Defining variables which change later on
#TEST_DIR_PATH = c.TEST_DIR_PATH
#model = c.MODEL_PATH
#label = c.LABEL_PATH


def ReadLabelFile(file_path):
    """
    reading labels
    """

    with open(file_path, 'r') as f:
        lines = f.readlines()
    ret = {}
    for line in lines:
        pair = line.strip().split(maxsplit=1)
        ret[int(pair[0])] = pair[1].strip()
    return ret


def read_PIL_image(i):
    """
    read the image using PIL
    """
    Path = c.DATA_PATH + '/image ({}).png'.format(i)
    img = Image.open(Path)
    # get image shape
    width, height = img.size
    # croping the image into square
    if width != height:
        img = img.crop((0, 0, min(width, height), min(width, height)))
    # resize to fit the model
    img = img.resize((300, 300), Image.ANTIALIAS)
    # RGB
    if img.mode != 'RGB':
        img = img.convert('RGB')
    return img


def filter_intensity(img, draw, crack_box, threshold_filter):
    """
    applying second filter
    """
    xc0 = int(crack_box[0])
    yc0 = int(crack_box[1])
    xc1 = int(crack_box[2])
    yc1 = int(crack_box[3])
    y_cr_px = []
    x_cr_px = []
    xy_series = []
    bw_border = threshold_filter
    for y in range(yc0, yc1):
        for x in range(xc0, xc1):
            if img.getpixel((x, y))[0] < bw_border:  # taking the first element
                y_cr_px.append(y)
                x_cr_px.append(x)
                xy_series.append(x)
                xy_series.append(y)
    A = np.vstack([x_cr_px, np.ones(len(x_cr_px))]).T
    m, b_px = np.linalg.lstsq(A, y_cr_px, rcond=None)[0]
    if DRAW:
        draw.point(xy_series)
        draw.line((0, b_px, 300, m * (300) + b_px), fill=128)
    return img, m, b_px

def filter_intensity_fast(img, draw, crack_box, threshold_filter):

    """

    applying second filter

    """
    xc0 = int(crack_box[0])
    yc0 = int(crack_box[1])
    xc1 = int(crack_box[2])
    yc1 = int(crack_box[3])
    imgarr = np.asarray(img)[:,:,0]
    crop = imgarr[yc0:yc1][xc0:xc1]
    match = np.where(crop < threshold_filter)
    A = np.vstack([match[1], np.ones(len(match[1]))]).T
    (m, b) = np.linalg.lstsq(A, match[0], rcond=None)[0]
    b_px = b + yc0
    if DRAW:

        xy_series = []

        for i in range(0, len(match[0])):

            xy_series.append((match[1][i], match[0][i] + yc0))

        draw.point(xy_series)

        draw.line((0, b_px, 300, m * (300) + b_px), fill=128)

    return (img, m, b_px)


def router_angle(img, draw, circle_center_x, circle_center_y, square_center_x, square_center_y):
    """
    get router angle since the router is supposed to be parrallel wiht camera
    """
    if DRAW:
        delta_sc_y = -(circle_center_y - square_center_y)  # the negative counts for the vice verse direction
        delta_sc_x = circle_center_x - square_center_x
        draw.line((circle_center_x, circle_center_y, square_center_x, square_center_y), fill=100)
        ang_sc_deg = math.atan2(delta_sc_y, delta_sc_x) * 180 / math.pi
        img = img.rotate(-ang_sc_deg + 90)
        # print( 'the angle in degree is = ', ang_sc_deg)
    return ang_sc_deg


def crack_end_point(m, b_px, sf): #, cr_x_px, cr_y_px, sq_x_px, sq_y_px
    # m, b_px , cr_x_px , cr_y_px, sq_x_px, sq_y_px = (-math.tan(3.1415/360*3), 141.1, 20, 34, 26, 261)
    # (-22.4/438, 22.4 , 24, 34, 24, 261)
    """
    To extrapolate the crack end point
    the equation of the line for the origninal img frame is
    y_px = m*x_px + b_px
    but since the x direction is reversed and b is shifted to the middle then
    y_px = -m*x_px + (b_px - 150)
    need these for evaluation of the set up (if guidance frames are in place)
    guid_center_y_px = 150 # (cr_y_px + sq_y_px)/2 # optimally each is 150 and is positive
    guid_len_x_px = 0 # cr_x_px - sq_x_px # supposed to be ZERO can be pos or neg
    """
#    guid_len_y_mm = 198  # [mm]
    Lg_mm = 438  # [mm] cutter to guidece frames
    guid_center_x_px = 23 #(cr_x_px + sq_x_px) / 2   ~ 23[px] optimally they are equal and positive
#    guid_len_y_px = 227 #sq_y_px - cr_y_px  ~227 px Not supposed must be measured each time
#    sf = abs(guid_len_y_mm / guid_len_y_px)  # ~ 0.8722466960352423 scaling factor [mm/px]
    Lx_mm = Lg_mm - guid_center_x_px * sf  # ~ 417.94 mm the distance from the side of the frame to the cutter because we found b earlier
    y_mm = -m * Lx_mm + (b_px - 150) * sf  # this is the scaling factor from px to mm
    return y_mm


def crack_layer(ans, img, draw, labels, crack_box_prev, threshold_filter):
    crack_detected = False
    if ans:
        for obj in ans:
            if labels[obj.label_id] == 'crack':
                crack_detected = True
                crack = obj
                crack_box = crack.bounding_box.flatten().tolist()
                if DEBUG:
                    print('crack box= ', crack_box)
                    print('crack score = ', crack.score)
                if DRAW:
                    draw.rectangle(crack_box, outline='red')
        if crack_detected is False:
            crack_box = crack_box_prev
    else:
        if DEBUG:
            print('No objects found')
        crack_box = crack_box_prev

    if FILTER:
        if not crack_detected:
            crack_box = crack_box_prev          
            crack_box_height = int((crack_box[3] - crack_box[1]))
            if crack_box_height < 50:
                delta_height = crack_box_height / 2 * 40 / 100  # adding 40% to the overall height
                crack_box = [0, crack_box[1] - delta_height, 300, crack_box[3] + delta_height]
                if DRAW:
                    draw.rectangle(crack_box, outline='orange')
            else:
                if DRAW:
                    draw.rectangle(crack_box, outline='orange')

    img, m, b_px = filter_intensity_fast(img, draw, crack_box, threshold_filter)

    return img, m, b_px, crack_detected, crack_box


def process_image(engine, labels, img, timing, crack_box, threshold, threshold_filter):
    """
    PHASE ONE: 
    running TPU
    input: RAW RGB image 300 x 300
    output: may or may not find the (crack, circle, square) box [pxl]
    """

    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # why does this speed things up?:
    #engine = DetectionEngine(c.MODEL_PATH)
    
    
    # Create draw to overlay
    draw = ImageDraw.Draw(img)
    # Run inference
    if timing:
        start_infer = time.time()


    ans = engine.DetectWithImage(img, threshold=threshold, keep_aspect_ratio=True,
                                 relative_coord=False, top_k=10)

    if timing:
        end_infer = time.time()
        inferencing_time = end_infer - start_infer
    else:
        inferencing_time = None
    
 
    """
    PHASE TWO: 
    running FILTERS on CPU
    input: image 300 x 300, with or without boxes
    output: box and score of (crack, circle, and square)
    Filters apply to the bounding box found earlier,
    however if the box is not detected then it uses the previous box
    while adding (40) percent to the overall height of the box. 
    the reason is we are not sure how the crack moved in the bounding box
    there is a 50 pixel cap for the box. To haul the increase of the height 
    due to the fact that the first filter didn't work. Once the next box
    detected the box height resets. 
    The filter counter is to recognize if the box is not detected. 
    Basically if the filter counter doesn't match with the performance counter
    it means we lost performance the filter counter increase by one while the 
    filter stays the same. 
    """
    # applying the filter
    (img, m, b_px, crack_detected, crack_box) = crack_layer(ans, img, draw, labels, crack_box, threshold_filter)
 
    # x pos in the moving direction y pos is toward the car pos
    # the scaling factor is coming from the claibration to be fixed ~0.8722466960352423
    y_mm = crack_end_point(m, b_px, 0.8722466960352423) #, circle_center_x, circle_center_y, square_center_x, square_center_y
    
    return (y_mm, img, crack_detected, inferencing_time, crack_box)

def calibration(ans):
    if ans:
        for obj in ans:
            if c.labels[obj.label_id] == 'circle':
                circle = obj
                c.circle_box = circle.bounding_box.flatten().tolist()
                circle_center_x = int((c.circle_box[0] + c.circle_box[2]) / 2)
                circle_center_y = int((c.circle_box[1] + c.circle_box[3]) / 2)
                if DEBUG:
                    print('circle box= ', c.circle_box)
                    print('circle score = ', c.circle.score)

                if DRAW:
                    draw.rectangle(c.circle_box, outline='blue')
            else:
                square = obj
                c.square_box = square.bounding_box.flatten().tolist()
                square_center_x = int((c.square_box[0] + c.square_box[2]) / 2)
                square_center_y = int((c.square_box[1] + c.square_box[3]) / 2)
                if DEBUG:
                    print('square box= ', square_box)
                    print('square score = ', square.score)
                if DRAW:
                    draw.rectangle(square_box, outline='green')
              

