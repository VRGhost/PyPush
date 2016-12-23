"""PyBluez BLE connection."""
import threading
import time
import struct
import logging
import datetime
import functools

import bluetooth.ble

from PyPush.lib import async as async

from .. import (
    iApi,
    exceptions,
)

class PushGattRequester(bluetooth.ble.GATTRequester):
    """PyPush gatt requester."""

    _notifyCb = None
    def setNotificationCallback(self, cb):
        assert callable(cb)
        assert self._notifyCb is None
        self._notifyCb = cb

    def on_notification(self, handle, data):
        if self._notifyCb:
            self._notifyCb(handle, data)

class PushBluezRequesterProxy(object):
    """Requester proxy that helps to map exceptions to PyPush classes."""

    log = logging.getLogger(__name__)

    def __init__(self, requester, parent):
        self.requester = requester
        self.parent = parent

    def __getattr__(self, name):
        realFn = getattr(self.requester, name)
        assert callable(realFn), (realFn, name)

        @functools.wraps(realFn)
        def _wrapper_(*args, **kwargs):
            retries = 3
            while True:
                try:
                    return realFn(*args, **kwargs)
                except RuntimeError as err:
                    print err
                    msg = err.message.lower()
                    isSoftError = any([
                        "device is not responding" in msg,
                        "busy" in msg,
                    ])
                    retries -= 1
                    if isSoftError and retries > 0:
                        time.sleep(1) # wait a bit and retry the call
                    else:
                        self.log.exception("Error calling {!r} with {!r}, {!r}".format(name, args, kwargs))
                        if "device is not responding" in msg:
                            raise exceptions.Timeout(err.message)
                        elif "attribute can't be read" in msg:
                            raise exceptions.NotSupported(err.message)
                        else:
                            raise exceptions.BleException(err.message)

        setattr(self, name, _wrapper_)
        return _wrapper_

class Connection(iApi.iConnection):
    
    log = logging.getLogger(__name__)

    mb = hciDev = gattReq = token = None
    _serviceCache = _charCache = _subscriptions = _lastActiveTime = None

    def __init__(self, hciDev, discoveredMb, token):
        self.mb = discoveredMb
        self.hciDev = hciDev
        self.token = token
        self._subscriptions = set() # set of (servName, charName)
        self.notifyEvtDict = async.SubscribeHubDict()

    def _open(self):
        assert not self.isActive()
        with self.transaction():
            conn = PushGattRequester(
                self.mb.getUID(),
                False, # do_connect
                self.hciDev,
            )
            conn = PushBluezRequesterProxy(conn, self)
            self.gattReq = conn
            conn.setNotificationCallback(self._on_notification)
            conn.connect(False, "random")
            while not conn.is_connected():
                time.sleep(0.5)
            self._populateCaches()

            # Activate any pending subscriptions
            for (sName, cName) in self._subscriptions:
                self._sendSubscription(sName, cName)

    def getMicrobot(self):
        return self.mb

    def readAllCharacteristics(self):
        out = dict((srv, {}) for srv in self._serviceCache.keys())
        for (chName, ch) in self._charCache.iteritems():
            serviceName = [name for (name, srv) in self._serviceCache.iteritems()
                if srv["end"] >= ch["value_handle"] >= srv["start"]]
            assert len(serviceName) == 1, (serviceName, ch)
            serviceName = serviceName[0]
            try:
                val = self.read(serviceName, chName)
            except exceptions.NotSupported:
                val = None
            out[serviceName][chName] = val 
        return out


    def onNotify(self, serviceId, characteristicId, callback):
        self._subscribe(serviceId, characteristicId)
        return self.notifyEvtDict[characteristicId].subscribe(callback)

    def write(self, serviceId, characteristicId, data):
        ch = self._findCharacteristic(serviceId, characteristicId)
        self._bumpActiveTime()
        return self.gattReq.write_by_handle(ch["value_handle"], data)

    def read(self, serviceId, characteristicId, timeout=5):
        ch = self._findCharacteristic(serviceId, characteristicId)
        rv = self.gattReq.read_by_handle(ch["value_handle"])
        self._bumpActiveTime()
        return "".join(rv)

    def isActive(self):
        return bool(self.gattReq and self.gattReq.is_connected())

    def close(self):
        if self.isActive():
            with self.token:
                self.gattReq.disconnect()
                self.gattReq = None

    def transaction(self):
        return self.token

    def getLastActiveTime(self):
        return self._lastActiveTime

    def _bumpActiveTime(self):
        self._lastActiveTime = datetime.datetime.utcnow()

    def _findCharacteristic(self, srvId, charId):
        """Retrun a characteristic with name `charId` that belongs to service `srvId`."""
        ch = self._charCache[charId]
        srv = self._serviceCache[srvId]
        h1 = ch["handle"]
        h2 = ch["value_handle"]
        start = srv["start"]
        end = srv["end"]
        assert end >= h1 >= start, (start, h1, end)
        assert end >= h2 >= start, (start, h2, end)
        return ch

    def _uuidToHumanName(self, uuid):
        return uuid.split("-")[0][-4:].upper()

    def _subscribe(self, servName, charName):
        """This function subscribes to the notifications if connection is already active.

        If not, it schedules subscription for the time when connection activates.
        """
        self._subscriptions.add((servName, charName))
        if self.isActive():
            with self.token:
                self._sendSubscription(servName, charName)

    def _sendSubscription(self, servName, charName):
        assert self.isActive()
        ch = self._findCharacteristic(servName, charName)
        self.log.debug("Subscribing to {}".format(ch))
        char_config_handle = ch["value_handle"]+1 # XXX: this is a hack. How can I read 'Client Characteristic Configuration' with this lib?
        rv = self.gattReq.write_by_handle(char_config_handle, '\x01\x00')

    def _populateCaches(self):
        """Populate connection information caches."""
        conn = self.gattReq
        with self.token:
            self._serviceCache = _cache = {}
            for service in conn.discover_primary():
                name = self._uuidToHumanName(service["uuid"])
                _cache[name] = service.copy()

            self._charCache = _cache = {}
            for char in conn.discover_characteristics():
                name = self._uuidToHumanName(char["uuid"])
                _cache[name] = char

    def _on_notification(self, chHandle, data):
        """This callback is called when the device notifies us of characteristic change."""
        self._bumpActiveTime()
        ch = [el for el in self._charCache.itervalues() if el["value_handle"] == chHandle]
        assert len(ch) == 1, ch
        chName = self._uuidToHumanName(ch[0]["uuid"])
        self.notifyEvtDict[chName].fireSubscribers(data[3:]) # data is prefixed with three bytes purpose of whom I have no idea of.