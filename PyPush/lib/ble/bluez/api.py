"""Top-level API object."""
import threading
import subprocess

from .. import iApi

from . import (
    scanner,
    connection,
)

class API(iApi.iApi):
    """PyBluez API."""

    devName = None

    def __init__(self, config):
        super(API, self).__init__()
        self.devName = config["device"]
        self._mutex = threading.RLock()
        self._scanner = scanner.Scanner(self.devName, self._mutex)

    def start(self):
        """Start any involved threads."""
        self._scanner.start()

    def onScan(self, callback):
        return self._scanner.onScan.subscribe(callback)
    
    def createMicrobotFromUUID(self, uuid):
        assert self._running
        
        nUuid = byteOrder.hBytesToNStr(bParts)
        eturn self._microbotDb.createMicrobotFromUUID(nUuid)
	
    def connect(self, microbot):
        conn = connection.Connection(self.devName, microbot, self._mutex)
        conn._open()
        return conn

    _myUUID = None
    def getUID(self):
        if self._myUUID is None:
            dName = self.devName
            uids = []
            for line in subprocess.check_output(["hcitool", "dev"]).splitlines():
                if dName in line:
                    uids.append(line.split()[-1])
            if len(uids) != 1:
                raise Exception("Unable to determine host UUID (device {!r}, options:{})".format(dName, uid))
            else:
                self._myUUID = uids[0]
                
        return self._myUUID
