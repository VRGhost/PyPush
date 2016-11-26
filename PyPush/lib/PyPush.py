import datetime
import time
import struct
import Queue

from . import ble, const

class PyPush(object):
	"""Top-level PyPush service."""

	_ble = _connections = _keyStorage = None

	def __init__(self, bleConfig, keyStorage):
		"""Key Storage is an object with __getitem__/__setitem__ magics.
		
		This dictionary is used to store authentication data and hence
		must be persistent.
		"""
		self._ble = ble.getLib(bleConfig)
		self._connections = {}
		self._keyStorage = keyStorage

	def scan(self):
		return self._ble.scan(5)

	def push(self, device, timeout):
		"""Pushes `device` and releases after `timeout`"""
		self._extend(device)
		time.sleep(timeout)
		self._retract(device)

	def getInfo(self, device):
		"""Returns status of the microbot push."""
		conn = self._getConnection(device)
		return conn.getAllCharacteristics(const.InfoServiceId)

	def setCalibration(self, device, percentage):
		value = int(percentage * 0xFF)
		value = max(1, min(value, 0xFF))


		conn = self._getConnection(device)
		self._ble.setCharacteristic(
			conn, const.PushServiceId, const.DeviceSetCalibration,
			value
		)

	def flashLed(self, device, seconds):
		conn = self._getConnection(device)
		self._ble.setCharacteristic(
			conn, const.MicrobotServiceId, const.LedFlash,
			seconds
		)

	def _initiate(self, devId, conn):
		"""Authorise device connection."""
		ts = time.mktime(datetime.datetime.utcnow().timetuple())
		ts = int(ts)
		try:
			key = self._keyStorage[devId]
		except KeyError:
			# Not paired yet.
			key = 0
		data = struct.pack('!ii', ts, key)


		writeQ = Queue.Queue()
		def _onWrite(data):
			writeQ.put(data)

		handle = conn.onNotify(const.MicrobotServiceId, const.InitAddr, _onWrite)
		conn.write(
			const.MicrobotServiceId, const.InitAddr,
			data
		)
		writeRv = writeQ.get()
		handle.cancel()
		print repr(writeRv)
		1/0

		raise rv
		if rv[0] == 0x1:
			# Already paired
			pass
		elif rv[0] == 0x2:
			# Uninitialised Microbot.
			pass
		elif rv[0] == 0x3:
			raise Exception("Incorrect pairing!")
		else:
			raise Exception("Unexpected status code {!r}".format(rv[0]))

	def _extend(self, device):
		"""Extends the microbot via `connection`."""
		conn = self._getConnection(device)
		self._ble.setCharacteristic(
			conn, const.PushServiceId, const.DeviceExtend,
			1
		)
		self._ble.setCharacteristic(
			conn, const.PushServiceId, '2A16',
			1
		)

	def _retract(self, device):
		"""Orders connected microbot to retract its pusher."""
		conn = self._getConnection(device)
		return self._ble.setCharacteristic(
			conn, const.PushServiceId, const.DeviceRetract,
			1
		)

	def _getConnection(self, iMb):
		uid = iMb.getUID()

		conn = None
		try:
			conn = self._connections[uid]
			if not conn.isActive():
				conn.close()
				conn = None
		except KeyError:
			pass

		if conn is None:
			conn = self._ble.connect(iMb)
			self._initiate(uid, conn)
			self._connections[uid] = conn
		return conn