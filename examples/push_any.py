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
V10_MICROBOT = 'EA:FE:E8:50:75:CB'

DB = MyKeyDb()
service = PyPush.lib.PushHub(
	{"driver": "bgapi", "device": "/dev/tty.usbmodem1"},
	DB
)
service.onMicrobot(printMb, None)
service.start()
mb = service.getMicrobot(V10_MICROBOT)


try:
	mb.connect()
except PyPush.lib.exceptions.NotPaired as err:
	print err
	for rgb in mb.pair():
		print rgb
	DB.db.sync()


### Test code

mb.extend()
print "Extended"
mb.retract()
print "Retracted"

### test code end

DB.db.close()