"""A Scanner object that performs BLE scan in the background."""
import threading
import datetime
import time


class _ScanThread_(threading.Thread):

	def __init__(self, ble, maxAge, callback):
		super(_ScanThread_, self).__init__()
		self.ble = ble
		self.maxAge = maxAge
		self.daemon = True
		self._cb = callback

	def run(self):
		while True:
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
			time.sleep(0.5)

class Scanner(object):

	def __init__(self, ble, mbRegistry):
		self._registry = mbRegistry
		self._scan = _ScanThread_(ble, 3600, self._onNewScanResult)
		self._scan.start()


	def _onNewScanResult(self, evt):
		"""This callback is called on discovery of a new BLE device.

		* THIS METHOD IS EXECUTED IN A CHILD THREAD *
		"""
		if self._isMicrobot(evt):
			self._registry.onScanEvent(evt)

	def _isMicrobot(self, evt):
		evt.parse_advertisement_data()
		for el in evt.adv_payload:
			if el["Type"] == "BLE_GAP_AD_TYPE_COMPLETE_LOCAL_NAME" and el["Data"] == "mibp":
				return True
		# else
		return False