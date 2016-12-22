"""This module provides a connection object proxy that automatically reconnects."""

import logging
import threading

class StableAuthorisedConnection(object):
    """Auto-reconnecting BLE connection.

    This is a wrapper for the BLE connection that auto-reconnects to
    the device & re-authorises connection with the microbot.

    This wrapper performs `retries` connection-reattempts at most.
    """

    _active = True
    log = logging.getLogger(__name__)

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
            try:
                while not self._conn.isActive() and retry < self._maxRetries:
                    self._restoreConnection()
                    # Sleep for a bit to give the device time to recover
                    time.sleep(retry)
                    retry += 1
            except Exception:
                self.log.exception("Error restoring BLE connection")
                self._active = False

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

