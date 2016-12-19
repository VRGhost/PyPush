"""Flask app."""

import os
import threading
import contextlib

from . import (
    iCore,
    const,
    db,
    actionLog,
)


class Core(iCore.iCore):
    """PyPush integration app object."""

    __slots__ = ("db", "db_conn", "db_lock", "db_uri", "ble", "_bleConfig", "microbotActionLog", "ui")

    def __init__(self, debug, dbUri, actionLogPath):
        self.debug = bool(debug)
        self.microbotActionLog = actionLog.MicrobotActionLog(actionLogPath)

        self.db = db.db
        self.db_conn = None
        self.db_uri = dbUri
        self.db_lock = threading.RLock()

        from .ble import MicrobotBluetoothService
        self.ble = MicrobotBluetoothService(self)
        self.ui = None

    def getPairDb(self):
        return self.ble.getPairDb()

    def setMicrobotApi(self, api):
        self.ble.setHub(api)

    def setUI(self, ui):
        assert self.ui is None, self.ui
        self.ui = ui

    def setDbConnection(self, dbConn):
        assert self.db_conn is None, self.db_conn
        dbConn.open(self.db_uri)
        self.db_conn = dbConn

    def run(self):
        if self.is_main_thread():
            with self.getDbSession():
                self.db.create_all()
            self.ble.start()

        self.ui.run()

    @contextlib.contextmanager
    def getDbSession(self):
        with self.db_lock:
            with self.db_conn.session() as session:
                yield session

    def is_main_thread(self):
        """Return if current thread is the one that will be responsible for running the app."""
        return (not self.debug) or os.environ.get("WERKZEUG_RUN_MAIN") == "true"


# convenience functions
