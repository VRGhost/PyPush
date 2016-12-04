"""Daemon server entry point."""
import argparse
import os
import logging
import threading

import PyPush.web as PushWeb

def get_arg_parser():
	DB_PATH = os.path.realpath(
		os.path.join(PushWeb.const.TMP_DIR, "db.sqlite"))
	
	DB_URI = "sqlite:///{}".format(DB_PATH)

	parser = argparse.ArgumentParser(description="Microbot Push management daemon.")
	parser.add_argument("--port", default=5000, type=int, help="RPC server port.")
	parser.add_argument("--host", default="localhost", help="Host to bind server socket to.")
	parser.add_argument("--db_uri", default=DB_URI, help="Database URI")
	parser.add_argument("--ble_driver", default="bgapi", help="Bluetooth Low Energy driver.")
	parser.add_argument("--ble_device", default="/dev/tty.usbmodem1", help="BLE device")
	return parser

def run(host, port, db_uri, ble_driver, ble_device):
	app = PushWeb.app.PUSH_APP

	app.flask.config.update({
		"SQLALCHEMY_DATABASE_URI": db_uri,
		"DEBUG": True,
	})
	app.setBleConfig(ble_driver, ble_device)
	app.start(host, port, debug=True)


if __name__ == "__main__":
	args = get_arg_parser().parse_args()
	logging.basicConfig(level=logging.INFO)
	run(args.host, args.port, args.db_uri, args.ble_driver, args.ble_device)