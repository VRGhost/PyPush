"""A Scanner object that performs BLE scan in the background."""
import threading
import datetime
import time
import logging

class _ScanThread_(threading.Thread):

    log = logging.getLogger(__name__)

    def __init__(self, ble, maxAge, callback):
        super(_ScanThread_, self).__init__()
        self.ble = ble
        self.maxAge = maxAge
        self.daemon = True
        self._cb = callback

    def run(self):
        while True:
            try:
                self.step()
            except Exception:
                self.log.exception("Scan thread exception.")
            time.sleep(0.5)

    def step(self):
        results = self.ble.scan_all(timeout=0.5)

        # deduplicate & remove old scan responses
        if results:
            results.sort(key=lambda el: el.created, reverse=True)
            seen = set()
            minTime = time.time() - self.maxAge
            for el in results:
                addr = el.get_sender_address()
                if addr not in seen or el.created >= minTime:
                    self._cb(el)
                seen.add(addr)

class Scanner(object):

    def __init__(self, ble, onScanCb):
        assert callable(onScanCb), onScanCb
        self._myUUID = ble.get_ble_address()
        self._cb = onScanCb
        self._scan = _ScanThread_(ble, 3600, self._onNewScanResult)
        self._scan.start()

    def _onNewScanResult(self, evt):
        """This callback is called on discovery of a new BLE device.

        * THIS METHOD IS EXECUTED IN A CHILD THREAD *
        """
        if self._isMicrobot(evt):
            self._cb(evt)

    def _isMicrobot(self, evt):
        evt.parse_advertisement_data()
        for el in evt.adv_payload:
            if el.type_name == "BLE_GAP_AD_TYPE_COMPLETE_LOCAL_NAME" and el.data == "mibp":
                return True
            # The event type codes for paired microbots discovered so far are:
            #   0xD9
            #   0xC8
            # As I do not know if there are any other type codes, I've decided to opt for safer
            #   option of using "> 200" condition
            if el.type_code > 200 and el.data == self._myUUID[-4:]:
                # Microbots have this appearing when they've been pairted with
                # someting
                return True
        # else
        return False
