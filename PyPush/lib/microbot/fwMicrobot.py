"""This module contains firmware version-dependant functonality of the microbot."""

from abc import ABCMeta, abstractmethod, abstractproperty
import logging
import threading
import contextlib
import time

from .. import (
    const,
    exceptions,
    async,
)

class iFwApi(object):
    """Shared interface object to enforce the api."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def isRetracted(self):
        """Return 'True' if the pusher is retracted, 'False' if extended, 'None' if unknown."""

    @abstractmethod
    def waitForPusherStateChange(self):
        """Context that waits for the pusher to complete extension/release process."""

class FirmwareBase(iFwApi):
    """Base class for firmware overlays."""

    def __init__(self, microbot):
        self.mb = microbot
        self.reader = self.mb.reader

class FirmwareV010(FirmwareBase):
    """v 1.0"""

    _retractedState = None
    _isRetracted = None

    log = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        super(FirmwareV010, self).__init__(*args, **kwargs)
        self.retractedStateChange = async.SubscribeHub()

    def isRetracted(self):
        """Old firmware: use status register(s)"""
        with self.mb._mutex:
            if self._retractedState is None:
                self._retractedState = {
                    "is_retracted": True,
                }

                def _setRetracted(val):
                    oldVal = self._retractedState["is_retracted"]
                    self.log.debug("Retracted := {} (old = {})".format(val, oldVal))
                    self._retractedState["is_retracted"] = val
                    if val != oldVal:
                        time.sleep(1)
                        self.retractedStateChange.fireSubscribers(oldVal, val)
                        self.mb._fireChangeState()

                srv = const.PushServiceId
                self.reader.callbacks[(srv, "2A11")].subscribe(lambda *a, **kw: _setRetracted(False))
                self.reader.callbacks[(srv, "2A12")].subscribe(lambda *a, **kw: _setRetracted(True))

                self.reader.read(srv, "2A11") # Calling 'read' also subscribes for the event notifications
                self.reader.read(srv, "2A12") # Calling 'read' also subscribes for the event notifications
                
                self.mb._conn().write(srv, "2A12", '\x01') # Force microbot to retract on init.
                time.sleep(2) # give it time to react

        return self._retractedState["is_retracted"]

    @contextlib.contextmanager
    def waitForPusherStateChange(self, timeout=20):
        oldValue = self.mb.isRetracted()
        releaseEvt = threading.Event()

        def _onPusherStateChange(_, newVal):
            if oldValue != newVal:
                releaseEvt.set()

        handle = self.retractedStateChange.subscribe(_onPusherStateChange)
        try:
            yield
            evtSet = releaseEvt.wait(timeout)
        finally:
            handle.cancel()
        
        if not evtSet:
            raise exceptions.StateChangeError("Pusher change did not happen.")

class FirmwareV015(FirmwareBase):
    """v 1.5"""

    def isRetracted(self):
        """ New firmware api: use DeviceStatus register """
        status = self.reader.read(const.PushServiceId, const.DeviceStatus)
        if status:
            rv = (status[1] == "\x00")
        else:
            rv = None
        return rv

    def waitForPusherStateChange(self):
        return self._waitForRegisterStateChange((
            (const.PushServiceId, const.DeviceStatus),
        ))