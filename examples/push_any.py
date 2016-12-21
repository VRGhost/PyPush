"""This is a shor script I am using to poke various low-level device APIs."""

import shelve
import time
import logging
from pprint import pprint

logging.basicConfig(level=logging.INFO)

import PyPush

class MyKeyDb(PyPush.lib.iLib.iPairingKeyStorage):

	def __init__(self):
		self.db = shelve.open("auth.cache")

	def hasKey(self, key):
		return self.db.has_key(key)

	def get(self, key):
		return self.db[key]

	def set(self, key, value):
		self.db[key] = value

	def delete(self, key):
		try:
			del self.db[key]
		except KeyError:
			pass

def printMb(mb):
	print "ON microbot callback ({}, UUID:{!r})".format(mb, mb.getUID())

USA_MICROBOT = 'E2:49:C3:06:6F:CA'

DB = MyKeyDb()
service = PyPush.lib.PushHub(
	{"driver": "bgapi", "device": "/dev/tty.usbmodem1"},
	DB
)
service.onMicrobot(printMb, None)
service.start()
mb = service.getMicrobot(USA_MICROBOT)


try:
	mb.connect()
except PyPush.lib.exceptions.NotPaired as err:
	print err
	for rgb in mb.pair():
		print rgb
	DB.db.sync()


### Test code

print "Battery level", mb.getBatteryLevel()
(s, c) = ('1821', '2A53')
mb._conn().write(s, c, '\x03')
time.sleep(5)
print "End val", repr(mb._conn().read(s, c))


### test code end

DB.db.close()