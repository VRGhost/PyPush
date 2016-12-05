"""Top-level API object."""
from bgapi.module import BlueGigaClient

from .. import iApi
from . import (
    scanner,
    mbRegistry,
    connection,
    bOrder,
    libLock,
)


class API(iApi.iApi):
    """BlueGiga API."""

    def __init__(self, config):
        """Config must be a dict with "port" key (specifying tty of the bluegiga token)"""
        self._mbDb = mbRegistry.MicrobotRegistry(maxAge=60 * 60)
        _ble = BlueGigaClient(
            port=config["device"],
            baud=config.get("baud", 115200),
            timeout=config.get("timeout", 0.1)
        )
        self._ble = libLock.LockableBle.RootLock(_ble)
        self._ble.reset_ble_state()
        self._scanner = scanner.Scanner(self._ble, self._mbDb.onScanEvent)

    def onScan(self, callback):
        return self._mbDb.onScanCallback(callback)

    def connect(self, microbot):
        conn = connection.BgConnection(microbot, self._ble)
        conn._open()
        return conn

    _uidCache = None

    def getUID(self):
        if self._uidCache is None:
            self._uidCache = bOrder.nStrToHHex(
                self._ble.get_ble_address(), ":")
        return self._uidCache
