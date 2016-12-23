"""The Scanner object is responsible for performing BLE scans and identifying microbots."""
import threading
import logging
import time
import datetime
import collections

from bluetooth.ble import DiscoveryService, GATTRequester

from PyPush.lib import async

from .. import iApi

class _ScanThread_(threading.Thread):
    log = logging.getLogger(__name__)

    def __init__(self, discoveryService, token, callback):
        super(_ScanThread_, self).__init__()
        self.discoveryService = discoveryService
        self.token = token
        self.daemon = True
        self._cb = callback

    def run(self):
        while True:
            try:
                with self.token:
                    self.step(self.discoveryService)
            except Exception:
                self.log.exception("Scan thread exception.")
            time.sleep(3)

    def step(self, discService):
        devices = discService.discover_advanced(1)
        for (address, seg_data) in devices.items():
            self._cb(address, seg_data)

class DiscoveredMicrobot(iApi.iMicrobotPush):

    def __init__(self, address, adv_data):
        self.address = address
        self.adv_data = adv_data.copy()
        self._pingTime()

    def getName(self):
        """Returns name of this microbot."""
        return "Microbot Push ({}:{})".format(*self.address.split(":")[-2:])

    def getLastSeen(self):
        """Returns datetime when this microbot was last observerd by the system."""
        return self._lastSeen

    def getUID(self):
        """Returns an unique string identifying this particular microbot device."""
        return self.address

    def _pingTime(self):
        self._lastSeen = datetime.datetime.utcnow()

    def __repr__(self):
        return "<{} {!r} ({!r})>".format(
            self.__class__.__name__, self.getName(), self.getUID())

class Scanner(object):
    """Top-level scanner object."""

    max_seen_mbs = 1024
    _seenMbs = _notMbs = None

    def __init__(self, devName, bleAccessToken):
        self.onScan = async.SubscribeHub()
        self.devName = devName
        self._token = bleAccessToken
        self._thread = _ScanThread_(
            DiscoveryService(devName), self._token, self._onDeviceDiscovered)
        self._seenMbs = collections.OrderedDict()
        self._notMbs = collections.deque(maxlen=self.max_seen_mbs)

    def start(self):
        self._thread.start()

    def _onDeviceDiscovered(self, uuid, seg_data):
        if uuid in self._seenMbs:
            self._seenMbs[uuid]._pingTime()
        elif uuid in self._notMbs:
            # Ignore the event
            pass
        elif self._isMicrobot(uuid, seg_data):
            with self._token:
                dev = DiscoveredMicrobot(uuid, seg_data)
                self._seenMbs[uuid] = dev
                self.onScan.fireSubscribers(dev)
                self._gcMicrobots()
        else:
            self._notMbs.append(uuid)

    def _gcMicrobots(self):
        """Remove any microbots that should have been long forgotten."""
        with self._token:
            while len(self._seenMbs) > self.max_seen_mbs:
                self._seenMbs.popitem()

    def _isMicrobot(self, uuid, seg_data):
        if seg_data["bdaddr_type"] != 1:
            return False
        name = seg_data.get("name")
        if name:
            rv = name in ("mibp", "mib-push")
        else:
            # Maybe this is a paired microbot.
            rv = self._tryQueryMbService(uuid)
        return rv

    def _tryQueryMbService(self, uuid):
        conn = GATTRequester(uuid, False, self.devName)
        try:
            conn.connect(False, "random")
            max_time = time.time() + 5
            while not conn.is_connected():
                if time.time() > max_time:
                    return False
                time.sleep(0.5)

            DEV_NAME_SERVICE_UUID = "00002a00-0000-1000-8000-00805f9b34fb" # 2A00, device name
            try:
                value = "".join(conn.read_by_uuid(DEV_NAME_SERVICE_UUID))
            except RuntimeError as err:
                msg = err.message.lower()
                if "no attribute found":
                    return False
                else:
                    raise
            value = value.lower()
            return ("mibp" in value or "mib-push" in value)
        finally:
            if conn.is_connected():
                conn.disconnect()
                while conn.is_connected():
                    time.sleep(0.5)