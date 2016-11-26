import shelve
import time
import logging

logging.basicConfig(level=logging.INFO)
db = shelve.open("auth.cache")

import PyPush

service = PyPush.lib.PyPush(
	{"driver": "bgapi", "port": "/dev/tty.usbmodem1"},
	db
)

time.sleep(10)
found = service.scan()
assert found
pusher = found[0]
print "Pusing {}".format(pusher)
#service.setCalibration(pusher, 1.0)
#service.flashLed(pusher, 15)
service.getInfo(pusher)
service.push(pusher, 1)


db.close()