from abc import ABCMeta, abstractmethod, abstractproperty

class iApi(object):
	__metaclass__ = ABCMeta

	@abstractmethod
	def scan(self, maxAge=0):
		"""This method returns an iterable of (timestamp, UUID) all Microbots discovered.

		the `timestamp` is a datetime with time when that device had been last seen on the air.
		
		The `maxAge` parameter specifies how far in the past the oldest "seen" device can be.

		This method has to return an iterable of <iMicrobotPush>

		"""

	@abstractmethod
	def connect(self, mbPush):
		"""This method initiates BLE connection to the <iMicrobotPush> provided as an argument.

		Returns <iConnection> object
		"""

class iMicrobotPush(object):
	__metaclass__ = ABCMeta

	@abstractmethod
	def getName(self):
		"""Returns name of this microbot."""

	@abstractmethod
	def getLastSeen(self):
		"""Returns datetime when this microbot was last observerd by the system."""

	def getUID(self):
		"""Returns an unique string identifying this particular microbot device."""

class iConnection(object):
	__metaclass__ = ABCMeta

	@abstractmethod
	def getMicrobot(self):
		"""Returns <iMicrobotPush> this connection is attached to."""

	@abstractmethod
	def getAllServices(self):
		"""Returns all service IDs available for this microbot."""

	@abstractmethod
	def getAllCharacteristics(self, serviceId):
		"""Returns dict of all CharacteristicId-> Value for the `serviceId`. """

	@abstractmethod
	def onNotify(self, serviceId, characteristicId, callback=None):
		"""Bind `callback` to execute on each notify event of the characteristic::service.

		Returns <iNotifyHandle>.
		"""

	@abstractmethod
	def write(self, serviceId, characteristicId, data):
		"""Write data to the characteristic::service."""

	@abstractmethod
	def isActive(self):
		"""Returns `True` if this connection is still active."""

	@abstractmethod
	def close(self):
		"""Closes this connection."""

class iNotifyHandle(object):
	__metaclass__ = ABCMeta

	@abstractmethod
	def cancel(self):
		"""Cancel this notify handle."""