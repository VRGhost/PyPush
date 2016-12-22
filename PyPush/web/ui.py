"""Flask UI app for the PyPush core."""
import os
import contextlib

from flask import Flask
from flask_bower import Bower
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api

from werkzeug.wsgi import DispatcherMiddleware

import PyPush.core
from . import const, views

class FlaskDbConnection(PyPush.core.iCore.iDbConnection):

    __slots__ = ("flask", "core", "uri")

    def __init__(self, core, ui):
        self.ui = ui
        self.core = core
        self.uri = None

    def open(self, uri):
        assert self.uri is None, self.uri
        self.uri = uri
        self.ui.flask.config.update(
            SQLALCHEMY_DATABASE_URI=uri,
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        self.core.db.init_app(self.ui.flask)

    @contextlib.contextmanager
    def session(self):
        with self.ui.flask.app_context():
            session = self.core.db.create_scoped_session({})
            try:
                try:
                    yield session
                except:
                    session.rollback()
                    raise
                else:
                    session.commit()
            finally:
                session.close()

class FlaskUI(PyPush.core.iCore.iUI):

    __slots__ = ("core", "flask", "bower", "restful", "host", "port", "debug")

    def __init__(self, debug, core, host, port, app_root):
        self.core = core
        self.flask = Flask("PyPush.web",
           static_folder=os.path.join(const.PUSH_WEB_DIR, "static"),
           template_folder=os.path.join(const.PUSH_WEB_DIR, "templates"),
        )

        self.bower = Bower(self.flask)
        self.restful = Api(self.flask)
        self._applyDefaultConfig()
        self.host = host
        self.port = port
        self.debug = debug
        self.flask.config.update(
            APPLICATION_ROOT=app_root,
        )

    def _applyDefaultConfig(self):
        """Apply default app config."""
        self.flask.config.update({
            "BOWER_COMPONENTS_ROOT": os.path.relpath(
                os.path.join(const.TMP_DIR, "bower_components"),
                self.flask.root_path,
            ),
        })

    def getDbConnection(self):
        """Return <iCore.iDbConnection> to be used."""
        return FlaskDbConnection(self.core, self)

    def run(self):
        views.create_views(self)

        app_root = self.flask.config.get("APPLICATION_ROOT")
        if app_root:
            def simple(env, resp):
                resp(b'200 OK', [(b'Content-Type', b'text/html')])
                return [b'<a href="{root}">{root}</a>'.format(root=app_root)]
            print self.flask.config["APPLICATION_ROOT"]
            self.flask.wsgi_app = DispatcherMiddleware(simple, {
                self.flask.config["APPLICATION_ROOT"]: self.flask.wsgi_app
            })
        # Add extra files
        extra_files = []
        for (root, _, files) in os.walk(os.path.join(const.PUSH_WEB_DIR, "templates")):
            extra_files.extend(os.path.join(root, f) for f in files)
        self.flask.run(self.host, self.port, debug=self.debug, extra_files=extra_files)