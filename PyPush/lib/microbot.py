"""High-level microbot object."""

import collections
import threading
import datetime
import time
import logging
import itertools
import struct
import Queue
import functools

from . import (
    iLib,
    exceptions,
    const,
    async,
)

from .ble import exceptions as bleExceptions

LedStatus = collections.namedtuple("LedStatus", ["r", "g", "b"])


class _SubscribedReader(object):
    """A handler object that auto-subscribes to notifications on the characteristics being read.

    This allows for all successive reads to the microbot to be much faster as no read command is
    actually issued.
    """

    log = logging.getLogger()
    UNSUPPORTED_REFRESH_FREQ = 5 * 60  # seconds

    def __init__(self, mb):
        self.mb = mb
        self._handles = {}  # List of all notify handles
        self._values = {}  # Cache of all values
        self._unsupportedValues = {}  # key -> (value, expire_time)
        # List of all read() addresses that do not support notify.
        self._unsupported = set()

    def clear(self):
        """Forgets all notify subscriptions.

        Does not forget list of endpoints not supporting notify
        as this won't change on the connection restore.
        """
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
            elif key in self._handles:
                rv = self._values[key]
            else:
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
        if data != self._values[key]:
            self._values[key] = data
            self.mb._fireChangeState()


class _StableAuthorisedConnection(object):
    """Auto-reconnecting BLE connection.

    This is a wrapper for the BLE connection that auto-reconnects to
    the device & re-authorises connection with the microbot.

    This wrapper performs `retries` connection-reattempts at most.
    """

    _active = True

    def __init__(self, microbot, bleConnection, retries=5):
        self._mb = microbot
        self._conn = bleConnection
        self._maxRetries = retries
        self._mutex = threading.RLock()

    def get(self):
        """Returns an established BLE connection."""
        retry = 0
        if not self._active:
            raise exceptions.ConnectionError("Connection closed.")

        with self._mutex:
            while not self._conn.isActive() and retry < self._maxRetries:
                self._restoreConnection()
                # Sleep for a bit to give the device time to recover
                time.sleep(retry)
                retry += 1

            if not self._conn.isActive():
                # Exceeded retry count
                self._active = False
                raise exceptions.ConnectionError("Connection failed")
        return self._conn

    def isActive(self):
        return self._active

    def close(self):
        """Close the connection."""
        with self._mutex:
            if self._conn.isActive():
                self._conn.close()
            self._active = False

    def _restoreConnection(self):
        with self._mutex:
            assert self._active
            assert not self._conn.isActive(), self._conn

            self._conn = self._mb._sneakyConnect()
            self._mb._onReconnect()


def ConnectedApi(fn):
    """A function that is callable only when the `MicrobotPush` object is CONNECTED to someting."""

    @functools.wraps(fn)
    def _wrapper_(self, *args, **kwargs):
        if not self.isConnected():
            raise exceptions.WrongConnectionState(
                "This API endpoint is callable only when connected.")
        try:
            return fn(self, *args, **kwargs)
        except bleExceptions.RemoteException as err:
            self.log.exception("BLE remote exception")
            raise exceptions.RemoteException(err.code, err.message)

    return _wrapper_


def NotConnectedApi(fn):
    """A function callable when the microbot is NOT connected to something."""

    @functools.wraps(fn)
    def _wrapper_(self, *args, **kwargs):
        if self.isConnected():
            raise exceptions.WrongConnectionState(
                "This API endpoint is callable only when disconnected.")
        return fn(self, *args, **kwargs)

    return _wrapper_

class MicrobotPush(iLib.iMicrobot):

    log = logging.getLogger(__name__)

    _bleApi = _bleMb = None
    _keyDb = None
    _stableConn = None

    def __init__(self, ble, bleMicrobot, keyDb):
        self._bleApi = ble
        self._bleMb = bleMicrobot
        self._keyDb = keyDb
        self._mutex = threading.RLock()
        self._onChangeCbs = async.SubscribeHub()
        self._reader = _SubscribedReader(self)

    @NotConnectedApi
    def connect(self):
        with self._mutex:
            self._stableConn = _StableAuthorisedConnection(
                self, self._sneakyConnect())
        self._fireChangeState()

    def _sneakyConnect(self):
        """Private connect procedure that does not validate preexisting connection state.

        Used in the `connect()` API endpoint and in the implementation
        of stable connection object.

        Returns naked BLE connection.
        """
        self.log.info("Connecting.")
        uid = self.getUID()

        with self._mutex:
            if not self._keyDb.hasKey(uid):
                raise exceptions.NotPaired(None, "Pairing DB has no key for this device (uid {!r}).".format(
                    uid))

            key = self._keyDb.get(uid)
            conn = self._bleApi.connect(self._bleMb)

            status = self._checkStatus(conn, key)

            if status == 0x01:
                # Connection sucessful
                msg = None
            elif status == 0x02:
                msg = "Unitialised microbot."
            elif status == 0x03:
                msg = "Pairing key mismatch."
            else:
                msg = "Unexpected status 0x{:02X}".format(status)

            if msg is not None:
                # Connection not sucessful
                conn.close()
                if self.isPaired():
                    self._keyDb.delete(uid)
                    # This changes 'isPaired' status
                    self._fireChangeState() 
                raise exceptions.NotPaired(status, msg)

            return conn

    def disconnect(self):
        with self._mutex:
            if self.isConnected():
                self._reader.clear()
                self._stableConn.close()
                self._stableConn = None

    @NotConnectedApi
    def pair(self):
        self.log.info("Pairing with {!r}".format(self._bleMb))

        conn = self._bleApi.connect(self._bleMb)
        status = self._checkStatus(conn, None)
        if status == 0x02:
            # Uninitialised microbot
            pass
        else:
            raise exceptions.NotPaired(
                status, "Microbot is not pairable (status 0x{:02X})".format(status))

        SERVICE_ID = const.MicrobotServiceId
        PAIR_CH = "2A90"
        HOST_UID = self._getHostUUID()
        _DATA_QUEUE_ = Queue.Queue()

        with conn.transaction():
            handle = conn.onNotify(SERVICE_ID, PAIR_CH, _DATA_QUEUE_.put)
            # send host's handshake
            send_data = chr(len(HOST_UID)) + HOST_UID
            data_part1 = send_data[:20]
            data_part2 = "\x00" + send_data[20:]
            conn.write(SERVICE_ID, PAIR_CH, data_part1)
            conn.write(SERVICE_ID, PAIR_CH, data_part2)
            self.log.info(
                "Pairing data sent. Waiting for user to touch the button.")
            ITER_PERIOD = 5
            for colour in itertools.cycle(self._getPairColourSequence()):
                iterStart = time.time()
                self._sneakyLed(
                    colour.r,
                    colour.g,
                    colour.b,
                    ITER_PERIOD,
                    conn)
                yield colour
                timeRemains = max(ITER_PERIOD - (time.time() - iterStart), 0.1)
                try:
                    pairData = _DATA_QUEUE_.get(timeout=timeRemains)
                except Queue.Empty:
                    pass
                else:
                    # pair data acquired
                    break

        status = ord(pairData[0])
        key = pairData[1:]
        assert len(key) >= 16, repr(key)

        if status == 0x01:
            # Pairing sucessfull.
            self._keyDb.set(self.getUID(), key[:16])
            self._stableConn = _StableAuthorisedConnection(self, conn)
            self._fireChangeState()
        else:
            conn.close()
            if status == 0x04:
                raise exceptions.NotPaired(
                    status, "User did not touch the microbot")
            else:
                raise exceptions.NotPaired(
                    status, "Unexpected status 0x{:02X}".format(status))

    @ConnectedApi
    def led(self, r, g, b, duration):
        return self._sneakyLed(r, g, b, duration, self._conn())

    def _sneakyLed(self, r, g, b, duration, conn):
        """Workaround function to allow blinker colour changes during pairing.

        This method uses a connection object explicitly passed to it.
        """
        self.log.info("Setting LED colour.")
        duration = int(duration)
        assert duration > 0 and duration < 0xFF, duration
        colourInt = 0
        if r:
            colourInt |= 1
        if g:
            colourInt |= 2
        if b:
            colourInt |= 4

        data = struct.pack("BBxxxB", 1, colourInt, duration)
        conn.write(const.MicrobotServiceId, "2A14", data)

    @ConnectedApi
    def extend(self):
        self.log.info("Extending the pusher.")
        self._conn().write(
            const.PushServiceId, "2A11",
            '\x01'
        )

    @ConnectedApi
    def retract(self):
        self.log.info("Retracting the pusher.")
        self._conn().write(
            const.PushServiceId, "2A12",
            '\x01'
        )

    @ConnectedApi
    def isRetracted(self):
        status = self._reader.read(const.PushServiceId, const.DeviceStatus)
        if status:
            rv = (status[1] == "\x00")
        else:
            rv = None
        return rv

    @ConnectedApi
    def setCalibration(self, percentage):
        self.log.info("Setting calibration.")
        data = min(max(int(percentage * 100), 0x10), 100)
        data = struct.pack("B", data)
        self._conn().write(
            const.PushServiceId, const.DeviceCalibration,
            data
        )
        self._reader._setCache(
            const.PushServiceId,
            const.DeviceCalibration,
            data)

    @ConnectedApi
    def getCalibration(self):
        self.log.info("Getting calibration.")
        data = self._reader.read(const.PushServiceId, const.DeviceCalibration)
        try:
            (rv, ) = struct.unpack('B', data)
        except:
            self.log.exception("Data: {!r}".format(data))
            rv = None
        else:
            rv = rv / 100.0
        return rv

    @ConnectedApi
    def getBatteryLevel(self):
        self.log.info("Getting battery level.")
        data = self._reader.read(const.MicrobotServiceId, "2A19")
        try:
            (rv, ) = struct.unpack('B', data)
        except:
            self.log.exception("Data: {!r}".format(data))
            rv = None
        else:
            rv = rv / 100.0
        return rv

    @ConnectedApi
    def deviceBlink(self, seconds):
        self.log.info("Blinking device.")
        seconds = min(0xFF, max(0, int(seconds)))
        self._conn().write(const.MicrobotServiceId, "2A13", struct.pack("B", seconds))

    @ConnectedApi
    def DEBUG_getFullState(self):
        """THIS IS DEBUG METHOD FOR ACQUIRING COMPLETE STATE OF ALL READABLE CHARACTERISTICS OF THE MICROBOT."""
        return self._conn().readAllCharacteristics()

    def onStateChange(self, cb):
        return self._onChangeCbs.subscribe(cb)

    def getUID(self):
        return self._bleMb.getUID()

    def getName(self):
        return self._bleMb.getName()

    def getLastSeen(self):
        rv = self._bleMb.getLastSeen()
        if self.isConnected():
            rv = max(rv, self._conn().getLastActiveTime())
        return rv

    def isConnected(self):
        with self._mutex:
            return bool(self._stableConn and self._stableConn.isActive())

    def isPaired(self):
        return self._keyDb.hasKey(self.getUID())

    def _fireChangeState(self):
        self._onChangeCbs.fireSubscribers(self)

    def _onReconnect(self):
        """Callback executed on reconnection to the microbot."""
        self._reader.reSubscribe()

    def _checkStatus(self, bleConnection, pairKey):
        if not pairKey:
            pairKey = "\x00" * 16

        assert len(pairKey) == 16, repr(pairKey)
        ts = time.mktime(datetime.datetime.utcnow().timetuple())
        data = struct.pack('=I', int(ts)) + pairKey
        assert len(data) == 20, repr(data)

        SERVICE_ID = const.MicrobotServiceId
        STATUS_CHAR = "2A98"
        notifyQ = Queue.Queue()
        with bleConnection.transaction():
            handle = bleConnection.onNotify(
                SERVICE_ID, STATUS_CHAR, notifyQ.put)
            bleConnection.write(SERVICE_ID, STATUS_CHAR, data)
            try:
                reply = notifyQ.get(timeout=20)
            except Queue.Empty:
                self.log.info(
                    "Failed to check status of {!r}".format(
                        self._bleMb))
                return ord("\xff")
            finally:
                handle.cancel()

        return ord(reply[0])

    def _getHostUUID(self):
        """Returns BLE UUID host running this code uses.

        This function returns host UID in a format used when talking to the microbot.
        """
        return self._bleApi.getUID().replace(":", "")

    def _conn(self):
        """Returns BLE connection to this microbot. Opens it if it needed."""
        return self._stableConn.get()

    def _getPairColourSequence(self):
        """Return colour sequence the Microbot is cycling trough while waiting for user touch."""
        return (
            LedStatus(False, True, True),
            LedStatus(True, False, True),
            LedStatus(True, True, False),
        )

    def __repr__(self):
        return "<{} {!r} ({!r})>".format(
            self.__class__.__name__, self.getName(), self.getUID())
