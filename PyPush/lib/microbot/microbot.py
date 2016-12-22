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
import threading
import contextlib

from .. import (
    iLib,
    exceptions,
    const,
    async,
)

from ..ble import exceptions as bleExceptions

from .subscribingReader import SubscribingReader
from .stableConnection import StableAuthorisedConnection

from . import fwMicrobot

LedStatus = collections.namedtuple("LedStatus", ["r", "g", "b"])


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

def get_firmware_version(connection):
    """Acquire firmware version tuple from the connection."""
    data = connection.read(const.MicrobotServiceId, "2A21")
    if data and len(data) == 3:
        rv = struct.unpack("BBB", data)
    else:
        self.log.error("Unexpected firmware version string: {!r}".format(data))
        rv = (0, 1, 0) # Stock factory firmware
    return rv

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
        self.reader = SubscribingReader(self)
        self._fwOverlay = None

    @NotConnectedApi
    def connect(self):
        with self._mutex:
            if self.isPaired():
                self._stableConn = StableAuthorisedConnection(
                    self, self._sneakyConnect())
            else:
                raise exceptions.NotPaired(0xFE, "This connection is not paired.")
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
            fwOverlayCls = self._getFwOverlay(get_firmware_version(conn))
            self._fwOverlay = fwOverlayCls(self)

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
                self.reader.clear()
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
        """Extend the pusher."""
        if self.isRetracted() is False: # 'None' should not get into this `if`
            self.log.info("The pusher is already extended.")
            return

        with self._mutex:
            self.log.info("Extending the pusher.")
            try:
                with self._waitForPusherStateChange():
                    self._conn().write(
                        const.PushServiceId, "2A11",
                        '\x01'
                    )
            except exceptions.StateChangeError:
                raise exceptions.IOError("Sending extend command did not affect state of the device.")
                
            if self.isRetracted():
                raise exceptions.IOError("Device is not extended although the extended command had been sent.")

    @ConnectedApi
    def retract(self):
        """Retract the pusher."""

        if self.isRetracted():
            self.log.info("The pusher is already retracted")
            return

        with self._mutex:
            self.log.info("Retracting the pusher.")
            try:
                with self._waitForPusherStateChange():
                    self._conn().write(
                        const.PushServiceId, "2A12",
                        '\x01'
                    )
            except exceptions.StateChangeError:
                raise exceptions.IOError("Sending retract command did not affect state of the device.")

            if not self.isRetracted():
                raise exceptions.IOError("Device is not retracted although the retract command had been sent.")

    def _waitForPusherStateChange(self):
        """This context blocks until pusher's state changes."""
        return self._fwOverlay.waitForPusherStateChange()

    @ConnectedApi
    def isRetracted(self):
        return self._fwOverlay.isRetracted()

    @ConnectedApi
    def setCalibration(self, percentage):
        self.log.info("Setting calibration.")
        data = min(max(int(percentage * 100), 0x10), 100)
        data = struct.pack("B", data)
        self._conn().write(
            const.PushServiceId, const.DeviceCalibration,
            data
        )
        self.reader._setCache(
            const.PushServiceId,
            const.DeviceCalibration,
            data
        )

    @ConnectedApi
    def getCalibration(self):
        self.log.info("Getting calibration.")
        data = self.reader.read(const.PushServiceId, const.DeviceCalibration)
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
        data = self.reader.read(const.MicrobotServiceId, "2A19")
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
    def getFirmwareVersion(self):
        return get_firmware_version(self.reader)

    @ConnectedApi
    def getButtonMode(self):
        data = self.reader.read(const.PushServiceId, "2A53")
        if data and len(data) == 1:
            rv = const.ButtonMode(ord(data))
        else:
            self.log.error("Unexpected button mode: {!r}".format(data))
            rv = None # Unknown
        return rv

    @ConnectedApi
    def setButtonMode(self, mode):
        if isinstance(mode, int):
            val = const.ButtonMode(mode)
        elif isinstance(mode, basestring):
            val = const.ButtonMode[mode]
        else:
            raise NotImplementedError(mode)
        self.log.info("Setting button mode to {!r}".format(val))
        data = struct.pack("B", int(val))
        self._conn().write(const.PushServiceId, "2A53", data)
        self._fireChangeState()

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

    @contextlib.contextmanager
    def _waitForRegisterStateChange(self, keys, timeout=10):
        evt = threading.Event()
        handles = []

        def _evtCb(key, oldVal, newValue):
            if oldVal != newValue:
                evt.set()

        for key in keys:
            # key is (service, characteristics)
            handles.append(self.reader.callbacks[key].subscribe(_evtCb))

        try:
            yield
            evtSet = evt.wait(timeout)
        finally:
            for handle in handles:
                handle.cancel()

        if not evtSet:
            raise exceptions.StateChangeError("State change did not arrive")

    def _fireChangeState(self):
        self._onChangeCbs.fireSubscribers(self)

    def _onReconnect(self):
        """Callback executed on reconnection to the microbot."""
        self.reader.reSubscribe()

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
                return 0xFF
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
            LedStatus(True, False, True),
            LedStatus(True, True, False),
        )

    def _getFwOverlay(self, fwVersion):
        """This method returns firmware overlay class appropriate for the firmware verison provided."""
        if fwVersion == (0, 1, 0):
            rv = fwMicrobot.FirmwareV010
        else:
            rv = fwMicrobot.FirmwareV015
        return rv

    def __repr__(self):
        return "<{} {!r} ({!r})>".format(
            self.__class__.__name__, self.getName(), self.getUID())
