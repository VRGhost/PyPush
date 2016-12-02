"""BLE-level microbot exceptions."""

class BleException(Exception):
	"""Parent class for all exceptions in this module."""

class NotConnected(BleException):
	"""Exception raised when the connection is no longer active."""

class NotSupported(BleException):
	"""Exception raised when the requested function is not supported by the target service/characteristic."""

class Timeout(BleException):
	"""Function timed out."""

class RemoteException(BleException):
	"""The remote device reported an error."""

	def __init__(self, code, message):
		super(RemoteException, self).__init__(message)
		self.code = code