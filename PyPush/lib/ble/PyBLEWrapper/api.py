"""PyBLE (https://github.com/brettchien/PyBLEWrapper) wrapper."""

import struct

from pyble.handlers import PeripheralHandler, ProfileHandler, ProfileHandlerMount

from .. import const, iApi

from . import scanner

class CountHandler(ProfileHandler):
	_AUTOLOAD = True
	_notifyCb = None

	def setNotifyCallback(self, cb):
		self._notifyCb = cb

	def on_notify(self, characteristic, data):
		if callable(self._notifyCb):
			self._notifyCb(data)

class DeviceInfoHandler(CountHandler):
	
	UUID = const.InfoServiceId

class PushHandler(CountHandler):
	
	UUID = const.PushServiceId

class BotHandler(CountHandler):
	
	UUID = const.MicrobotServiceId


class API(iApi.iApi):

	centralManager = knownDevices = None

	def __init__(self, pyBleLib):
		self.centralManager = pyBleLib.CentralManager()
		self.scanner = scanner.Scanner(self.centralManager)
		self.knownDevices = ()

	def scan(self, timeout):
		"""Scan for BLE devices. Returns an iterable of (device_name, device_id)."""
		
		#
		import time
		time.sleep(30)
		with self.scanner.pause():
			import time
			print "hello"
			time.sleep(10)
			1/0

		assert isinstance(timeout, (int, float)), "Timeout = number of seconds"
		try:
			self.centralManager.startScan(
				[],
				timeout,
				numOfPeripherals=0
			)
		except pyble.osx.centralManager.BLETimeoutError:
			pass

		knownDevices = []
		scanned = self.centralManager.getScanedList()
		expectedServices = frozenset([
			"180F", "180A"
		])
		out = []
		for el in scanned:
			if frozenset(el.advServiceUUIDs) == expectedServices:
				# Microbot push found
				out.append(str(el.UUID))
				knownDevices.append(el)

		self.knownDevices = knownDevices
		return out

	def connect(self, deviceId):
		dev = self._findDev(deviceId)
		profile = self.centralManager.connectPeripheral(dev)
		return profile

	def getAllCharacteristics(self, connection, serivceId):
		service = connection[serivceId]
		out = {}
		for c in service:
			out[c.name] = c.value
		return out

	def getCharacteristic(self, connection, serivceId, characteristic):
		service = connection[serivceId]
		c = service[characteristic]
		assert c.properties["read"]
		return c.value

	def setCharacteristic(self, connection, serivceId, characteristic, newVal):
		service = connection[serivceId]
		c = service[characteristic]
		assert c.properties["write"]
		if isinstance(newVal, basestring):
			newVal = bytearray(newVal)
		else:
			newVal = bytearray([newVal])
		c.value = newVal
		return newVal

	def setAndNotify(self, connection, serivceId, characteristic, newVal):
		"""This function releases when the target characteristics releases notification."""
		c = connection[serivceId][characteristic]
		assert c.properties["notify"]
		c.notify = True
		self.setCharacteristic(connection, serivceId, characteristic, newVal)

		NOTIFY_DATA = []
		def onNotifyDone(data):
			NOTIFY_DATA.append(bytearray(data))
			self.centralManager.stop()
		c.handler.setNotifyCallback(onNotifyDone)
		self.centralManager.loop()
		c.notify = False
		assert NOTIFY_DATA
		return NOTIFY_DATA[0]

	def _findDev(self, devId):
		for el in self.knownDevices:
			if devId in (el.UUID, str(el.UUID)):
				return el
		# Not found
		raise KeyError(devId)