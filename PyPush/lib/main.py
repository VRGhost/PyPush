"""Lib generation routines."""

import glob

def populate_arg_parser(parser):
    parser.add_argument(
        "--ble_driver",
        default="bgapi",
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
    devs = glob.glob(args.ble_device)
    assert len(devs) == 1, devs
    config = {
        "driver": args.ble_driver,
        "device": devs[0],
    }
    return PyPush.lib.PushHub(config, pairDb)