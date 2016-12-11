"""Main run script for the PyPush.web."""

import argparse
import os
import sys
import logging
import logging.handlers


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
    parser.add_argument(
        "--application_root",
        default=None,
        help="Application root url."
    )
    parser.add_argument("--db_uri", default=DB_URI, help="Database URI")
    parser.add_argument(
        "--ble_driver",
        default="bgapi",
        help="Bluetooth Low Energy driver.")
    parser.add_argument(
        "--ble_device",
        default="/dev/tty.usbmodem*",
        help="BLE device")
    return parser

def setupLogging(debug):
    """Configure the logging subsystem."""
    import PyPush.web as PushWeb

    lvl = logging.DEBUG if debug else logging.INFO

    formatter = logging.Formatter('%(asctime)s %(module)-17s line:%(lineno)-4d %(levelname)-8s %(message)s')
    
    rotHandler = logging.handlers.RotatingFileHandler(
        os.path.join(PushWeb.const.TMP_DIR, "PyPush.log"),
        maxBytes=10485760,
        backupCount=5,
    )
    rotHandler.setFormatter(formatter)

    stdoutHandler = logging.StreamHandler(sys.stdout)
    stdoutHandler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(lvl)
    root_logger.addHandler(rotHandler)
    root_logger.addHandler(stdoutHandler)


l = logging.getLogger("asdasd")

def main(debug, host, port, app_root, db_uri, ble_driver, ble_device):
    """Main entrypoint into the program."""
    import PyPush.web as PushWeb
    setupLogging(debug)
    
    logging.info("---- Starting PyPush ----")
    try:
        app = PushWeb.app.PUSH_APP

        app.flask.config.update({
            "SQLALCHEMY_DATABASE_URI": db_uri,
            "APPLICATION_ROOT": app_root,
            "DEBUG": debug,
        })
        app.setBleConfig(ble_driver, ble_device)
        app.start(host, port, debug=debug)
    except Exception:
        logging.exception("Top-level exception.")
        raise
    