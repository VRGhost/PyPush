import os

import enum

PUSH_WEB_DIR = os.path.abspath(os.path.dirname(__file__))
REPO_ROOT = os.path.join(PUSH_WEB_DIR, os.pardir, os.pardir)
TMP_DIR = os.path.join(REPO_ROOT, "_tmp")

MB_ACTIONS = enum.Enum("pair", "blink", "extend", "retract")