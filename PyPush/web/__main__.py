"""Daemon server entry point."""
import glob

import PyPush.web as PushWeb

if __name__ == "__main__":
    args = PushWeb.main.get_arg_parser().parse_args()

    ble_device = glob.glob(args.ble_device)
    if len(ble_device) != 1:
        raise Exception("Failed to identify the BLE decvice (arg {!r})".format(args.ble_device))
    else:
        ble_device = ble_device[0]
    
    PushWeb.main.main(
        args.debug,
        args.host, args.port,
        args.db_uri,
        args.ble_driver, ble_device
    )
