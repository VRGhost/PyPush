"""Daemon server entry point."""
import argparse
import os
import logging
import logging.config
import threading
import sys

import PyPush.web as PushWeb


def get_arg_parser():
    DB_PATH = os.path.realpath(
        os.path.join(PushWeb.const.TMP_DIR, "db.sqlite"))

    DB_URI = "sqlite:///{}".format(DB_PATH)

    parser = argparse.ArgumentParser(
        description="Microbot Push management daemon.")
    parser.add_argument(
        "--debug",
        default=False, action='store_true',
        help="Run in debug mode",
    )
    parser.add_argument(
        "--port",
        default=5000,
        type=int,
        help="RPC server port.")
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind server socket to.")
    parser.add_argument("--db_uri", default=DB_URI, help="Database URI")
    parser.add_argument(
        "--ble_driver",
        default="bgapi",
        help="Bluetooth Low Energy driver.")
    parser.add_argument(
        "--ble_device",
        default="/dev/tty.usbmodem1",
        help="BLE device")
    return parser




def run(debug, host, port, db_uri, ble_driver, ble_device):
    if debug:
        logging.basicConfig(level=logging.INFO)
    else:
        logFile = os.path.join(PushWeb.const.TMP_DIR, "PyPush.log")
        logging.config.dictConfig({
            'version': 1,
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': 'INFO',
                    'formatter': 'detailed',
                    'stream': 'ext://sys.stdout',
                },
                'file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': 'DEBUG',
                    'formatter': 'detailed',
                    'filename': logFile,
                    'mode': 'a',
                    'maxBytes': 10485760,
                    'backupCount': 5,
                },

            },
            'formatters': {
                'detailed': {
                    'format': '%(asctime)s %(module)-17s line:%(lineno)-4d ' \
                    '%(levelname)-8s %(message)s',
                },
                'email': {
                    'format': 'Timestamp: %(asctime)s\nModule: %(module)s\n' \
                    'Line: %(lineno)d\nMessage: %(message)s',
                },
            },
            'loggers': {
                'extensive': {
                    'level':'DEBUG',
                    'handlers': ['file',]
                    },
            },
            })
        logging.basicConfig(
            filename=logFile,
            level=logging.INFO
        )

    app = PushWeb.app.PUSH_APP

    app.flask.config.update({
        "SQLALCHEMY_DATABASE_URI": db_uri,
        "DEBUG": debug,
    })
    app.setBleConfig(ble_driver, ble_device)
    app.start(host, port, debug=debug)


if __name__ == "__main__":
    args = get_arg_parser().parse_args()
    
    run(args.debug, args.host, args.port, args.db_uri, args.ble_driver, args.ble_device)
