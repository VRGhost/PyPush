"""Byte order-related functions."""

import sys

DO_REVERSE = (sys.byteorder == "little")

def hBytesToNStr(arg):
    """byte array to a network-ordered string."""
    if DO_REVERSE:
        arg = reversed(arg)
    return "".join(chr(el) for el in arg)

def nStrToHBytes(arg):
    """Network string to Host bytes."""
    if DO_REVERSE:
        arg = reversed(arg)
    return (ord(ch) for ch in arg)


def nStrToHHex(arg, sep=""):
    """Network string to Host hex-encoded byte string."""
    return sep.join("{:02X}".format(el) for el in nStrToHBytes(arg))
