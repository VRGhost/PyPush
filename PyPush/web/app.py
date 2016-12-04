"""Flask app."""

import os

from flask import Flask
from flask_bower import Bower
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api

from . import const, db


class PyPushApp(object):
	"""PyPush integration app object."""

	__slots__ = ("flask", "db", "bower", "ble", "restful", "_bleConfig")

	def __init__(self):
		self.flask = Flask("PyPush.web",
			static_folder = os.path.join(const.PUSH_WEB_DIR, "static"),
			template_folder = os.path.join(const.PUSH_WEB_DIR, "templates"),
		)
		self._applyDefaultConfig()

		self.restful = Api(self.flask)
		self.bower = Bower(self.flask)
		self.db = db.db

		from .ble import MicrobotBluetoothService
		self.ble = MicrobotBluetoothService(self)

		self._bleConfig = ()

	def _applyDefaultConfig(self):
		"""Apply default app config."""
		self.flask.config.update({
			"SQLALCHEMY_TRACK_MODIFICATIONS": False,
			"BOWER_COMPONENTS_ROOT": os.path.relpath(
				os.path.join(const.TMP_DIR, "bower_components"),
				self.flask.root_path,
			),
			"BLE_DRIVER": "bgapi",
			"BLE_DEVICE": None,
		})

	def setBleConfig(self, driver, device):
		self._bleConfig = (driver, device)

	def start(self, host, port, debug=False):
		"""Start the web app."""
		self.db.init_app(self.flask)
		with self.flask.app_context():
			self.db.create_all()

		if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
			self.ble.start(*self._bleConfig)

		self.flask.run(
			host=host, port=port,
			debug=debug,
		)


PUSH_APP = PyPushApp()

# convenience functions