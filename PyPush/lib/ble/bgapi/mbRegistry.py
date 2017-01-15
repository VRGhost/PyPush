"""This module contains microbot interface and microbot db that this library is currently aware of.

This module MUST be thread-safe.
"""

import threading
import time
import datetime

from .. import iApi

from . import byteOrder


class BgMicrobot(iApi.iMicrobotPush):

    def __init__(self, binAddr, name):
        """`binAddr` is binary string representing this microbot."""
        self._name = name
        self._addr = binAddr
        self._lastSeen = time.time()

    def getName(self):
        return self._name

    def getLastSeen(self):
        return datetime.datetime.fromtimestamp(self._lastSeen)

    def getBinaryUUID(self):
        return self._addr

    def getUID(self):
        return self.getNiceAddr()

    def getNiceAddr(self):
        return byteOrder.nStrToHHex(self._addr, sep=":")

    def _setLastSeen(self, time):
        assert isinstance(time, float), time
        self._lastSeen = time

    def _update(self, other):
        """Update data stored in this object with the data for the same microbot but stored in another object."""
        assert self == other, (self, other)
        self._lastSeen = max(self._lastSeen, other._lastSeen)
        self._name = other._name

    def __eq__(self, other):
        return self._addr == other._addr

    def __repr__(self):
        return "<{} {!r} ({!r})>".format(
            self.__class__.__name__, self.getName(), self.getNiceAddr())


class MicrobotRegistry(object):

    _lock = _bots = None

    def __init__(self, maxAge=0):
        """Any microbot that had not been showing signs of life for over `maxAge` (if > 0) will be erased from the registry."""
        self._lock = threading.RLock()
        self._bots = {}
        self._maxAge = maxAge
        self._scanCallbacks = []

    def onScanCallback(self, callback):
        assert callable(callback), callback
        self._scanCallbacks.append(callback)

    def createMicrobotFromUUID(self, uuid):
        name = "Hidden microbot ({:02X}:{:02X})".format(*byteOrder.nStrToHBytes(uuid[:2]))
        rv = BgMicrobot(uuid, name)
        return rv

    def onScanEvent(self, evt):
        """This method is called when microbot is discovered via BLE scan."""
        addr = evt.get_sender_address()
        newBot = self._botFromEvt(evt)
        try:
            bot = self._bots[addr]
        except KeyError:
            with self._lock:
                self._bots[addr] = newBot
        else:
            bot._update(newBot)

        evtBot = self._bots[addr]

        # trigger onScan callbacks
        for cb in self._scanCallbacks:
            cb(evtBot)

        self._gcOldMicrobots()

    def _botFromEvt(self, evt):
        """Creates new BgMicrobot instance from the bluetooth scan event."""
        evt.parse_advertisement_data()
        addr = evt.get_sender_address()
        name = "Unknown Microbot ({:02X}:{:02X})".format(
            *byteOrder.nStrToHBytes(addr[:2]))

        for el in evt.adv_payload:
            if el.type_name == "BLE_GAP_AD_TYPE_MANUFACTURER_SPECIFIC_DATA":
                data = el.data
                if data.startswith("\x00\x00"):
                    # This is microbot's real name
                    name = data[2:]

        rv = BgMicrobot(addr, name)
        rv._setLastSeen(evt.created)
        return rv

    def _gcOldMicrobots(self):
        """Forget all microbots that are older than max age."""
        if self._maxAge <= 0:
            return

        cutoffTime = time.time() - self._maxAge
        toRemove = []
        for (key, mb) in tuple(self._bots.items()):
            if mb._lastSeen < cutoffTime:
                toRemove.append(key)

        with self._lock:
            for key in toRemove:
                self._bots.pop(key)
