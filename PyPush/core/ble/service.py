"""PyPush library mapping to the web server."""
import contextlib
import threading
import datetime
import traceback
import logging
import time

import enum

from sqlalchemy import exists
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func, update

import PyPush.lib as Lib
from PyPush.core import db

from . import daemon, pairDb

class MicrobotBluetoothService(object):
    """Microbot bluetooth service."""

    log = logging.getLogger(__name__)

    def __init__(self, core):
        self.core = core
        self._daemon = daemon.BLEDaemon(self)
        self._pairDb = pairDb.PairDb(self)
        self._microbots = {}  # uid -> microbot
        self._dbIds = {}  # uid -> db id
        self._hub = None

    def getPairDb(self):
        """Returns microbot pair db for the service."""
        return self._pairDb

    def setHub(self, hub):
        assert self._hub is None
        self._hub = hub

    def start(self):
        """Start the service."""
        self._hub.start()

        with self.sessionCtx() as s:
            stmt = update(db.Microbot).values(is_connected=False)
            s.execute(stmt)

        self._evtHandle = self._hub.onMicrobot(self._onMbFound, self._onMbLost)
        self._daemon.start()

    def getMicrobot(self, nameOrId):
        key = nameOrId.lower()
        for mb in self._microbots.itervalues():
            if key in (mb.getUID().lower(), ):
                return mb
        raise KeyError(nameOrId)

    def _onMbFound(self, microbot):
        key = microbot.getUID()
        self._microbots[key] = microbot
        microbot.onStateChange(lambda mb: self._onMbStateChange(key, mb))
        self._updateDbRecord(key)
        self._daemon.wakeup()

    def _onMbLost(self, microbot):
        if not microbot.isConnected():
            try:
                self._microbots.pop(microbot.getUID())
            except KeyError:
                pass
        self._daemon.wakeup()

    def stop(self):
        """Stop the service."""
        self._daemon.stop()

    def _onMbStateChange(self, uid, mb):
        try:
            self._updateDbRecord(uid)
        except Exception:
            # Cycle the connection
            self.log.exception("Microbot state change error")
            mb.disconnect()
            time.sleep(1)
            mb.connect()

    def _updateDbRecord(self, mbUid):
        with self.sessionCtx() as s:
            mb = self._microbots[mbUid]
            rec = s.query(db.Microbot).filter_by(uuid=mbUid).one_or_none()
            if not rec:
                rec = db.Microbot(uuid=mbUid, name=mb.getName())
                s.add(rec)

            is_conn = mb.isConnected()
            rec.is_connected = is_conn
            rec.is_paired = mb.isPaired()
            rec.last_seen = mb.getLastSeen()

            def mGet(fn):
                """Retreives value of the function, performs serveral re-attempts on timeout."""
                if not mb.isConnected():
                    return None
                try:
                    return fn()
                except:
                    tb = traceback.format_exc()
                    self.log.error(tb)
                    rec.last_error = tb

            rec.retracted = mGet(mb.isRetracted)
            rec.battery = mGet(mb.getBatteryLevel)
            rec.calibration = mGet(mb.getCalibration)

            s.commit()

            self._dbIds[mbUid] = rec.id

    def getDbId(self, uid):
        try:
            rv = self._dbIds[uid]
        except KeyError:
            self._reloadDbIds()
            rv = self._dbIds[uid]
        return rv

    _nextReloadOn = 0
    _RELOAD_FREQ = 60  # seconds

    def _reloadDbIds(self):
        if time.time() < self._nextReloadOn:
            return
        with self.sessionCtx() as s:
            for (dbId, uuid) in s.query(
                    db.Microbot.id, db.Microbot.uuid).all():
                self._dbIds[uuid] = dbId
        self._nextReloadOn = time.time() + self._RELOAD_FREQ

    def getBleMicrobots(self):
        return tuple(self._microbots.itervalues())

    def syncToBt(self):
        """Sync db -> BLE state."""
        self._daemon.wakeup()

    def sessionCtx(self):
        return self.core.getDbSession()
