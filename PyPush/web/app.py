"""Flask app."""

import os
import threading

from flask import Flask
from flask_bower import Bower
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api

from werkzeug.wsgi import DispatcherMiddleware

from . import (
    const,
    db,
    actionLog,
)


class PyPushApp(object):
    """PyPush integration app object."""

    __slots__ = ("flask", "db", "db_lock", "bower", "ble", "restful", "_bleConfig", "microbotActionLog")

    def __init__(self):
        self.flask = Flask("PyPush.web",
                           static_folder=os.path.join(
                               const.PUSH_WEB_DIR, "static"),
                           template_folder=os.path.join(
                               const.PUSH_WEB_DIR, "templates"),
                           )
        self._applyDefaultConfig()

        self.microbotActionLog = actionLog.MicrobotActionLog(
            os.path.join(const.TMP_DIR, "microbot_action_log.csv"),
        )

        self.restful = Api(self.flask)
        self.bower = Bower(self.flask)
        self.db = db.db
        self.db_lock = threading.RLock()

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

        if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not self.flask.debug:
            self.ble.start(*self._bleConfig)

        app_root = self.flask.config.get("APPLICATION_ROOT")
        if app_root:
            def simple(env, resp):
                resp(b'200 OK', [(b'Content-Type', b'text/html')])
                return [b'<a href="{root}">{root}</a>'.format(root=app_root)]
            print self.flask.config["APPLICATION_ROOT"]
            self.flask.wsgi_app = DispatcherMiddleware(simple, {
                self.flask.config["APPLICATION_ROOT"]: self.flask.wsgi_app
            })

        self.flask.run(
            host=host, port=port,
            debug=debug,
        )


PUSH_APP = PyPushApp()

# convenience functions
