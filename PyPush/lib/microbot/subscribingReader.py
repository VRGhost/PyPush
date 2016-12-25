"""This module contains a 'reader' class that reads values from the BLE connection
    and automatically subsribes to value updates.

"""
import logging
import time


from .. import async
from ..ble import exceptions as bleExceptions

class SubscribingReader(object):
    """A handler object that auto-subscribes to notifications on the characteristics being read.

    This allows for all successive reads to the microbot to be much faster as no read command is
    actually issued.
    """

    log = logging.getLogger(__name__)
    UNSUPPORTED_REFRESH_FREQ = 5 * 60  # seconds

    def __init__(self, mb):
        self.mb = mb
        self._handles = {}  # List of all notify handles
        self._values = {}  # Cache of all values
        self._unsupportedValues = {}  # key -> (value, expire_time)
        # List of all read() addresses that do not support notify.
        self._unsupported = set()
        self.callbacks = async.SubscribeHubDict()

    def clear(self):
        """Forgets all notify subscriptions.

        Does not forget list of endpoints not supporting notify
        as this won't change on the connection restore.
        """
        for handle in self._handles.itervalues():
            handle.cancel()
        self._handles.clear()
        self._values.clear()

    def read(self, service, char):
        """Performs BLE read if not subscribed to the notification.

        Returns cached value if subscribed to the notification.
        """
        key = (service, char)
        conn = self.mb._conn()

        try:
            if key in self._unsupported:
                rv = self._readUnsupported(conn, service, char)
            else:
                try:
                    rv = self._values[key]
                except KeyError:
                    try:
                        self._handles.pop(key).cancel()
                    except KeyError:
                        pass
                    # Not cached yet
                    rv = conn.read(service, char, timeout=15)
                    try:
                        self._subscribe(conn, service, char)
                    except bleExceptions.NotSupported:
                        self._unsupported.add(key)
                    else:
                        self._values[key] = rv
        except bleExceptions.Timeout:
            self.log.exception("BLE timeout")
            raise exceptions.Timeout("Read timeout")
        return rv

    def _readUnsupported(self, conn, service, char):
        key = (service, char)
        try:
            (oldVal, expireTime) = self._unsupportedValues[key]
        except KeyError:
            oldVal = None
            expireTime = 0

        now = time.time()
        if now > expireTime:
            # Re-read the data
            rv = conn.read(service, char)
            self._unsupportedValues[key] = (
                rv, now + self.UNSUPPORTED_REFRESH_FREQ)
        else:
            rv = oldVal
        return rv

    def _setCache(self, service, characteristics, value):
        key = (service, characteristics)
        self._unsupportedValues[key] = (
            value, time.time() + self.UNSUPPORTED_REFRESH_FREQ)
        self._values[key] = value

    def reSubscribe(self):
        """Resubscribe for to all notifications this object had been subscribed for.

        Normally executed on the reconnect.
        """
        _oldSubscriptions = self._handles.keys()
        self.clear()

        conn = self.mb._conn()
        for (service, char) in _oldSubscriptions:
            self._subscribe(conn, service, char)

    def _subscribe(self, conn, service, char):
        key = (service, char)
        if key not in self._handles:
            self._handles[key] = conn.onNotify(
                service, char, lambda data: self._onNotify(key, data))

    def _onNotify(self, key, data):
        oldValue = self._values.get(key)
        self._values[key] = data
        self._fireChangeEvents(key, oldValue, data)

    def _fireChangeEvents(self, key, oldValue, newValue):
        self.callbacks[key].fireSubscribers(key, oldValue, newValue)
        if oldValue != newValue:
            self.mb._fireChangeState()

