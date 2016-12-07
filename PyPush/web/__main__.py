"""Daemon server entry point."""
import PyPush.web as PushWeb

if __name__ == "__main__":
    args = PushWeb.main.get_arg_parser().parse_args()
    
    PushWeb.main.main(
        args.debug,
        args.host, args.port,
        args.db_uri,
        args.ble_driver, args.ble_device
    )
