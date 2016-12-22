import os

import enum

CORE_DIR = os.path.abspath(os.path.dirname(__file__))
REPO_ROOT = os.path.abspath(
    os.path.join(CORE_DIR, os.pardir, os.pardir))
TMP_DIR = os.path.join(REPO_ROOT, "_tmp")
assert os.path.isdir(TMP_DIR), TMP_DIR

@enum.unique
class MbActions(enum.Enum):
    """Core Api commands for the microbot."""
    
    pair = "pair"
    blink = "blink"
    extend = "extend"
    retract = "retract"
    calibrate = "calibrate"
    change_button_mode = "change_button_mode"
