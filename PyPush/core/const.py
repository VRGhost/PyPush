import os

import enum

CORE_DIR = os.path.abspath(os.path.dirname(__file__))
REPO_ROOT = os.path.abspath(
    os.path.join(CORE_DIR, os.pardir, os.pardir))
TMP_DIR = os.path.join(REPO_ROOT, "_tmp")
assert os.path.isdir(TMP_DIR), TMP_DIR

MB_ACTIONS = enum.Enum("pair", "blink", "extend", "retract", "calibrate")
