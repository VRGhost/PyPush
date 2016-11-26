"""BLE connection interface."""

import logging
import time
import collections
import threading

from bgapi.module import BLEConnection, GATTService, GATTCharacteristic, BlueGigaModuleException

from .. import iApi

from . import bOrder

BgCharacteristic = collections.namedtuple("BgCharacteristic", ["uuid", "gatt", "human_uuid"])

class BgNotifyHandle(iApi.iNotifyHandle):

	_LAST_VALUE_ = None

	def __init__(self, hub, characteristic):
		self._hub = hub
		self._char = characteristic
		self._valueEvt = threading.Event()
		self._callbacks = []
		self._opMutex = threading.Lock()
		self._waiting = 0

	def cancel(self):
		self._hub._unsubscribe(self._char, self)


	def addCallback(self, cb):
		assert callable(cb), cb
		self._callbacks.append(cb)

	def _onValue(self, value):
		"""Method that is called when new value becomes available."""
		for cb in tuple(self._callbacks):
			cb(value)

class _ConnNotifyHub(object):

	def __init__(self, bgConnection):
		self._bgConn = bgConnection
		self._handles = collections.defaultdict(lambda: [False, None, []]) # uuid -> (subscription_active, characteristic, [handles])

	def getNewHandle(self, bgCharacteristic):
		"""Returns new Notify handle instance."""
		assert bgCharacteristic.gatt.has_notify(), bgCharacteristic

		handle = BgNotifyHandle(self, bgCharacteristic)
		item = self._handles[bgCharacteristic.uuid]
		
		item[1] = bgCharacteristic
		item[2].append(handle)
		
		self._manageSubscriptions()
		return handle

	def _manageSubscriptions(self):
		for (key, [is_active, char, handles]) in self._handles.iteritems():
			
			shouldBeActive = len(handles) > 0

			def _getCbFn():
				# This binds 'char' value to the scope
				return lambda value: self._onCharValue(char, value)

			if shouldBeActive != is_active:
				conn = self._getBleConn()
				for handle in conn.get_handles_by_uuid(char.uuid):
					conn.assign_attrclient_value_callback(handle, _getCbFn())

				with conn.delayedUnlock(0.5):
					conn.characteristic_subscription(char.gatt, indicate=False, notify=shouldBeActive)

				# State synced.
				self._handles[key][0] = shouldBeActive

	def _getBleConn(self):
		assert self._bgConn.isActive(), self._bgConn
		return self._bgConn._bleConn

	def _onCharValue(self, char, value):
		"""Callback fired on every characteristic change."""
		for listener in tuple(self._handles[char.uuid][2]):
			listener._onValue(value)

	def _unsubscribe(self, char, handle):
		"""Unsubscribe `handle` from updates on characteristic."""
		self._handles[char.uuid][2].remove(handle)

class BgConnection(iApi.iConnection):

	_log = logging.getLogger(__name__)
	_mb = _ble = _bleConn = None

	def __init__(self, mb, ble):
		self._mb = mb
		self._ble = ble
		self._bleConn = None
		self._serviceToCharacteristics = {} # service UUID -> [characteristic UUID]
		self._notifyHub = _ConnNotifyHub(self)

	def getMicrobot(self):
		return self._mb

	def isActive(self):
		return self._bleConn is not None

	def close(self):
		with self._ble.transaction():
			if self.isActive():
				self._bleConn.disconnect()
				self._bleConn = None
				self._log.info("BgConnection {} closed.".format(self))

	def getAllServices(self):
		assert self.isActive()
		return [self._humanServiceName(el) for el in self._bleConn.get_services()]			

	def getAllCharacteristics(self, serviceUUID):
		assert self.isActive()
		
		srv = self._findService(serviceUUID)

		for char in self._serviceToCharacteristics[srv.uuid]:
			print char
			print self._bleConn.read_by_handle(char.handle)
		1/0
		return rv

	def onNotify(self, serviceId, characteristicId, callback=None):
		assert self.isActive()
		service = self._findService(serviceId)
		char = self._findCharacteristic(serviceId, characteristicId)
		rv = self._notifyHub.getNewHandle(char)
		if callable(callback):
			rv.addCallback(callback)
		return rv

	def write(self, serviceId, characteristicId, data):
		char = self._findCharacteristic(serviceId, characteristicId)
		assert char.gatt.is_writable(), char
		with self._bleConn.delayedUnlock(0.5):
			self._bleConn.write_by_uuid(char.uuid, data, timeout=5)

	def _open(self):
		"""Initiate the connection."""
		assert not self.isActive()
		with self._ble.transaction():
			conn = self._ble.connect(self._mb.getApiTarget(), timeout=10)
			self._bleConn = self._ble.getChildLock(conn)
			self._initBleConnection(self._bleConn)
		self._log.info("BgConnection {} opened.".format(self))
	
	def _findCharacteristic(self, serviceUUID, charUUID):
		srv_uuid = self._findService(serviceUUID).uuid
		for char in self._serviceToCharacteristics[srv_uuid]:
			if char.human_uuid == charUUID:
				return char
		# else
		raise KeyError([serviceUUID, charUUID])

	def _findService(self, uuid):
		for el in self._bleConn.get_services():
			if self._humanServiceName(el) == uuid:
				return el
		raise KeyError(uuid)

	def _humanServiceName(self, service):
		return bOrder.nStrToHHex(service.uuid)

	def _initBleConnection(self, conn):
		"""This method initialises internal state of the BLE connection by populating its internal dictionaries."""
		with conn.transaction():
			conn.read_by_group_type(GATTService.PRIMARY_SERVICE_UUID)
			conn.read_by_group_type(GATTService.SECONDARY_SERVICE_UUID)
			
			oldChars = frozenset(el.handle for el in conn.get_characteristics())

			for service in conn.get_services():
				conn.find_information(service)
				conn.read_by_type(service, GATTCharacteristic.CHARACTERISTIC_UUID, timeout=10)
				conn.read_by_type(service, GATTCharacteristic.CLIENT_CHARACTERISTIC_CONFIG, timeout=10)
				conn.read_by_type(service, GATTCharacteristic.USER_DESCRIPTION, timeout=10)

				allChars = conn.get_characteristics()
				newChars = frozenset(el.handle for el in allChars)
				self._serviceToCharacteristics[service.uuid] = tuple(
					BgCharacteristic(ch.uuid, ch, bOrder.nStrToHHex(ch.uuid))
					for ch in allChars if ch.handle in newChars
				)
				oldChars = newChars

	def __repr__(self):
		return "<{} {} ({})>".format(self.__class__.__name__, self._mb, "active" if self.isActive() else "inactive")
