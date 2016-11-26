"""Bluetooth Low Energy library abstraction layer.

The API object returned is expected to conform to the PyPush.iApi interface.
"""

from .. import const

from . import iApi

def getBgApi(config):
	from . import bgapi
	return bgapi.API(config)

def getPyBle():
	"""OSX BLE library."""
	import pyble
	from . import PyBLEWrapper
	return PyBLEWrapper.API(pyble)

def getLib(config):
	"""Automatically detect & deploy one of supported Python BLE libs."""
	if config["driver"] == "bgapi":
		rv = getBgApi(config)
	else:
		raise NotImplementedError(config)

	assert isinstance(rv, iApi.iApi)
	return rv