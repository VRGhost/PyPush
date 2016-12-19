"""Top-level API object."""
from bgapi.module import BlueGigaClient

from .. import iApi
from . import (
    scanner,
    mbRegistry,
    connection,
    byteOrder,
    libLock,
)


class API(iApi.iApi):
    """BlueGiga API."""

    def __init__(self, config):
        """Config must be a dictionary with "device" key (specifying tty of the bluegiga token)"""
        self._microbotDb = mbRegistry.MicrobotRegistry(maxAge=60 * 60)
        self._config = config

    def start(self):
        config = self._config
        
        _ble = BlueGigaClient(
            port=config["device"],
            baud=config.get("baud", 115200),
            timeout=config.get("timeout", 0.1)
        )
        self._ble = libLock.LockableBle.RootLock(_ble)
        self._ble.reset_ble_state()
        # set maximum allowed txpower for BLED112 (https://www.silabs.com/Support%20Documents/RegisteredDocs/Bluetooth_Smart_Software-BLE-1.3-API-RM.pdf page 145)
        _ble._api.ble_cmd_hardware_set_txpower(15)
        self._scanner = scanner.Scanner(
            self._ble, self._microbotDb.onScanEvent)

    def onScan(self, callback):
        return self._microbotDb.onScanCallback(callback)

    def connect(self, microbot):
        """Connect to the microbot."""
        conn = connection.BgConnection(microbot, self._ble)
        conn._open() # pylint: disable=W0212
        return conn

    _uuidCache = None

    def getUID(self):
        if self._uuidCache is None:
            self._uuidCache = byteOrder.nStrToHHex(
                self._ble.get_ble_address(), ":")
        return self._uuidCache
