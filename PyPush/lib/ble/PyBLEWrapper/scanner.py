import threading
import time
from contextlib import contextmanager

import pyble


class IdleScanThread(threading.Thread):

    centralManager = None

    def __init__(self, centralManager, scanMutex):
        super(IdleScanThread, self).__init__(name="PyBle Idle Scan Thread")
        self.daemon = True
        self.centralManager = centralManager
        self.scanMutex = scanMutex

    def run(self):
        while True:
            print "Thread started"
            time.sleep(0.1)
            with self.scanMutex:
                try:
                    self.centralManager.startScan(
                        timeout=0, numOfPeripherals=1)
                except pyble.osx.centralManager.BLETimeoutError:
                    pass


class Scanner(object):
    """PyBle microbot scanner & detector."""

    def __init__(self, centralManager):
        self.manager = centralManager
        centralManager.startScan(timeout=0, numOfPeripherals=1)
        self._scanMutex = threading.Lock()
        self._scanThread = IdleScanThread(centralManager, self._scanMutex)
        self._scanThread.start()

    @contextmanager
    def pause(self):
        """Entering this context pauses idle BLE scan."""
        with self._scanMutex:
            print self.manager.getScanedList()
            1 / 0
            yield
