DEBUG = False  # must choose True for one image
TIME = True
DRAW = True
SAVE = True
# This switch must be ON for the final version.
FILTER = True

i_cap = 100 # default(100)
crack_box_default = [0, 40, 300, 140]  # crack bounding box  [pxl]

SAVE_PATH = '../data/output'
DATA_PATH = '../data/original'
MODEL_PATH = '../data/optimizedQ_tpu.tflite'
LABEL_PATH = '../data/crack_labels.txt'
