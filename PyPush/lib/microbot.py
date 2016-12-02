"""High-level microbot object."""

import collections
import threading
import datetime
import time
import logging
import itertools
import struct
import Queue

from . import (
	iLib,
	exceptions,
	const,
)

from .ble import exceptions as bleExceptions

LedStatus = collections.namedtuple("LedStatus", ["r", "g", "b"])

class _SubscribedReader(object):
	"""A handler object that auto-subscribes to notifications on the characteristics being read.

	This allows for all successive reads to the microbot to be much faster as no read command is
	actually issued.
	"""

	def __init__(self, mb):
		self.mb = mb
		self._handles = {} # List of all notify handles
		self._values = {} # Cache of all values
		self._unsupported = set() # List of all read() addresses that do not support notify.

	def clear(self):
		"""Forgets all notify subscriptions.

		Does not forget list of endpoints not supporting notify as this won't change on the connection
		restore.
		"""
		self._handles.clear()
		self._values.clear()

	def read(self, service, char):
		"""Performs BLE read if not subscribed to the notification.

		Returns cached value if subscribed to the notification.
		"""
		key = (service, char)
		conn = self.mb._conn()
		if key in self._unsupported:
			rv = conn.read(service, char)
		elif key in self._handles:
			rv = self._values[key]
		else:
			# Not cached yet
			rv = conn.read(service, char)
			try:
				handle = conn.onNotify(service, char, lambda data: self._onNotify(key, data))
			except bleExceptions.NotSupported:
				self._unsupported.add(key)
			else:
				self._values[key] = rv
				self._handles[key] = handle
		return rv

	def _onNotify(self, key, data):
		self._values[key] = data

class MicrobotPush(iLib.iMicrobot):

	log = logging.getLogger(__name__)

	_bleApi = _bleMb = _bleConn = None
	_keyDb = None

	def __init__(self, ble, bleMicrobot, keyDb):
		self._bleApi = ble
		self._bleMb = bleMicrobot
		self._keyDb = keyDb
		self._mutex = threading.RLock()
		self._reader = _SubscribedReader(self)
		# self._notifyData = {} # uid -> value
		# self._notifyDaemons = []

	def connect(self):
		self.log.info("Connecting.")
		assert not self.isConnected()
		uid = self.getUID()

		with self._mutex:
			if not self._keyDb.hasKey(uid):
				raise exceptions.NotPaired(None, "Pairing DB has no key for this device (uid {!r}).".format(
					uid))
			key = self._keyDb.get(uid)
			status = self._checkStatus(key)

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
				self.disconnect()
				raise exceptions.NotPaired(status, msg)

	def disconnect(self):
		with self._mutex:
			if self.isConnected():
				self._reader.clear()
				self._bleConn.close()
				self._bleConn = None

	def pair(self):
		self.log.info("Pairing with {!r}".format(self._bleMb))

		time.sleep(5)
		status = self._checkStatus(None)
		if status == 0x02:
			# Uninitialised microbot
			pass
		else:
			raise exceptions.NotPaired(status, "Microbot is not pairable (status 0x{:02X})".format(status))

		SERVICE_ID = const.MicrobotServiceId
		PAIR_CH = "2A90"
		HOST_UID = self._getHostUUID()

		conn = self._conn()

		_DATA_QUEUE_ = Queue.Queue()

		with conn.transaction():

			handle = conn.onNotify(SERVICE_ID, PAIR_CH, _DATA_QUEUE_.put)

			# send host's handshake
			send_data = chr(len(HOST_UID)) + HOST_UID
			data_part1 = send_data[:20]
			data_part2 = "\x00" + send_data[20:]
			conn.write(SERVICE_ID, PAIR_CH, data_part1)
			conn.write(SERVICE_ID, PAIR_CH, data_part2)
			self.log.info("Pairing data sent. Waiting for user to touch the button.")
			ITER_PERIOD = 5
			for colour in itertools.cycle(self._getPairColourSequence()):
				iterStart = time.time()
				self.led(colour.r, colour.g, colour.b, ITER_PERIOD)
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
		elif status == 0x04:
			raise exceptions.NotPaired(status, "User did not touch the microbot")
		else:
			raise exceptions.NotPaired(status, "Unexpected status 0x{:02X}".format(status))

	def led(self, r, g, b, duration):
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

		conn = self._conn()
		data = struct.pack("BBxxxB", 1, colourInt, duration)
		conn.write(const.MicrobotServiceId, "2A14", data)

	def extend(self):
		self.log.info("Extending the pusher.")
		self._conn().write(
			const.PushServiceId, "2A11",
			'\x01'
		)

	def retract(self):
		self.log.info("Retracting the pusher.")
		self._conn().write(
			const.PushServiceId, "2A12",
			'\x01'
		)

	def isRetracted(self):
		status = self._reader.read(const.PushServiceId, const.DeviceStatus)
		if status:
			rv = (status[1] == "\x00")
		else:
			rv = None
		return rv

	def setCalibration(self, percentage):
		self.log.info("Setting calibration.")
		data = min(max(int(percentage * 100), 0x10), 100)
		self._conn().write(
			const.PushServiceId, const.DeviceCalibration,
			struct.pack("B", data)
		)

	def getCalibration(self):
		self.log.info("Getting calibration.")
		rv = self._reader.read(const.PushServiceId, const.DeviceCalibration)
		(rv, ) = struct.unpack('B', rv)
		return rv / 100.0

	def getBatteryLevel(self):
		self.log.info("Getting battery level.")
		rv = self._reader.read(const.MicrobotServiceId, "2A19")
		(rv, ) = struct.unpack('B', rv)
		return rv / 100.0

	def deviceBlink(self, seconds):
		self.log.info("Blinking device.")
		seconds = min(0xFF, max(0, int(seconds)))
		self._conn().write(const.MicrobotServiceId, "2A13", struct.pack("B", seconds))

	def DEBUG_getFullState(self):
		"""THIS IS DEBUG METHOD FOR ACQUIRING COMPLETE STATE OF ALL READABLE CHARACTERISTICS OF THE MICROBOT."""
		return self._conn().readAllCharacteristics()

	def getUID(self):
		return self._bleMb.getUID()

	def getName(self):
		return self._bleMb.getName()

	def getLastSeen(self):
		rv = self._bleMb.getLastSeen()
		if self._bleConn:
			rv = max(rv, self._bleConn.getLastActiveTime())
		return rv

	def isConnected(self):
		return self._bleConn and self._bleConn.isActive()

	def isPaired(self):
		return self._keyDb.hasKey(self.getUID())

	def _checkStatus(self, pairKey):
		if not pairKey:
			pairKey = "\x00" * 16

		assert len(pairKey) == 16
		ts = time.mktime(datetime.datetime.utcnow().timetuple())
		data = struct.pack('=I', int(ts)) + pairKey
		assert len(data) == 20, repr(data)

		SERVICE_ID = const.MicrobotServiceId
		STATUS_CHAR = "2A98"
		_NOTIFY_Q_ = Queue.Queue()
		conn = self._conn()
		with conn.transaction():
			handle = conn.onNotify(SERVICE_ID, STATUS_CHAR, _NOTIFY_Q_.put)
			conn.write(SERVICE_ID, STATUS_CHAR, data)
			try:
				reply = _NOTIFY_Q_.get(timeout=20)
			except Queue.Empty:
				self.log.info("Failed to check status of {!r}".format(self._bleMb))
				conn.close()
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
		with self._mutex:
			if self._bleConn and self._bleConn.isActive():
				rv = self._bleConn
			else:
				if self._bleConn:
					self._bleConn.close()
				self.log.info("Opening new BLE connection to {}".format(self._bleMb))
				rv = self._bleApi.connect(self._bleMb)
				self._bleConn = rv
		return rv

	def _getPairColourSequence(self):
		"""Return colour sequence the Microbot is cycling trough while waiting for user touch."""
		return (
			LedStatus(False, True, True),
			LedStatus(True, False, True),
			LedStatus(True, True, False),			
		)

	def __repr__(self):
		return "<{} {!r} ({!r})>".format(self.__class__.__name__, self.getName(), self.getUID())