"""Immutable constants."""
import os

import enum

from PyPush.core.const import (
    REPO_ROOT,
    TMP_DIR,
    MbActions,
)

PUSH_WEB_DIR = os.path.abspath(os.path.dirname(__file__))


@enum.unique
class ComplexMbActions(enum.Enum):
    """This enum extends low-level microbot actions with virtual actions that resolve into several low-level ones."""
    press = "press"
