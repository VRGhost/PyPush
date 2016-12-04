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

DB = MyKeyDb()
service = PyPush.lib.PushHub(
	{"driver": "bgapi", "device": "/dev/tty.usbmodem1"},
	DB
)
mb = service.getMicrobot('D6:CF:D7:59:7F:ED')


try:
	mb.connect()
except PyPush.lib.exceptions.NotPaired as err:
	print err
	for rgb in mb.pair():
		print rgb
	DB.db.sync()


ret = []
ext = []

# while True:
# 	print mb.isRetracted()
# 	time.sleep(5)




#mb.setCalibration(0.5)
#print mb.getCalibration()
#print mb.getBatteryLevel()
#mb.setCalibration(0.5)
# mb.extend()
# time.sleep(4)
# mb.retract()
while True:
	print mb.isRetracted()
	time.sleep(5)
#mb.led(0, 1, 0, duration=10)
#mb.disconnect()


DB.db.close()