"""Main run script for the PyPush.web."""

import argparse
import os
import logging
import logging.config


def get_arg_parser():
    """Argument parser for the command-line entry."""

    import PyPush.web as PushWeb

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


def main(debug, host, port, db_uri, ble_driver, ble_device):
    """Main entrypoint into the program."""
    
    import PyPush.web as PushWeb

    if debug:
        fmt = '%(asctime)s %(module)-17s line:%(lineno)-4d %(levelname)-8s %(message)s'
        logging.basicConfig(level=logging.DEBUG, format=fmt)
    else:
        logFile = os.path.join(PushWeb.const.TMP_DIR, "PyPush.log")
        logging.config.dictConfig({
            'version': 1,
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': 'DEBUG',
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
                '': {
                    'level':'DEBUG' if debug else 'INFO',
                    'handlers': ['file', 'console']
                },
            },
            })

    logging.info("---- Starting PyPush ----")
    try:
        app = PushWeb.app.PUSH_APP

        app.flask.config.update({
            "SQLALCHEMY_DATABASE_URI": db_uri,
            "DEBUG": debug,
        })
        app.setBleConfig(ble_driver, ble_device)
        app.start(host, port, debug=debug)
    except Exception:
        logging.exception("Top-level exception.")
        raise
    