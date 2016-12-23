"""Lib generation routines."""

import glob
import subprocess

def populate_arg_parser(parser):
    parser.add_argument(
        "--ble_driver",
        default="bgapi",
        choices=("bgapi", "pybluez"),
        help="Bluetooth Low Energy driver."
    )
    parser.add_argument(
        "--ble_device",
        default="/dev/tty.usbmodem*",
        help="BLE device"
    )
    return parser

def create(debug, pairDb, args):
    """Create PyPush library instance."""
    import PyPush.lib
    driver = args.ble_driver

    if driver == "bgapi":
        devs = glob.glob(args.ble_device)
        assert len(devs) == 1, devs
        dev = devs[0]
    elif driver == "pybluez":
        dev = args.ble_device
        out = subprocess.check_output(["hcitool", "dev"])
        if dev not in out:
            raise Exception("No {!r} in {!r}".format(dev, out))
    else:
        raise NotImplementedError(args)

    config = {
        "driver": driver,
        "device": dev,
    }
    return PyPush.lib.PushHub(config, pairDb)