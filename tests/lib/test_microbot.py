import mock
import re
import pytest
import itertools

import PyPush.lib.async.subscribe as Subscribe
import PyPush.lib.microbot as Mod
import PyPush.lib.iLib as iLib
import PyPush.lib.ble.iApi as iBle
import PyPush.lib.exceptions as excpt

MB_UID = "HELLO_WORLD_MOCK_MICROBOT_UID"
PAIR_KEY = "1234567890123456"

def setup():
	bleApi = mock.create_autospec(iBle.iApi)
	bleMb = mock.create_autospec(iBle.iMicrobotPush)
	keyDb = mock.create_autospec(iLib.iPairingKeyStorage)
	bleConn = mock.create_autospec(iBle.iConnection)

	bleApi.connect.return_value = bleConn

	bleMb.getUID.return_value = MB_UID
	keyDb.get.return_value = PAIR_KEY

	mb = Mod.MicrobotPush(bleApi, bleMb, keyDb)

	rv = {
		"mb": mb,
		"db": keyDb,
		"ble": {
			"api": bleApi,
			"mb": bleMb,
			"conn": bleConn,
			"conn_status": "\x01" + ("\x00" * 15),
			"exp_data": [
				"^.*{}$".format(PAIR_KEY),
			],
			"handle_cb": []
		}
	}

	notifyH = mock.create_autospec(Subscribe.iHandle)
	bleConn.onNotify.return_value = notifyH

	def _connWrite(service, char, data):
		assert service == "1831", service
		assert char == "2A98", char

		exp = rv["ble"]["exp_data"].pop(0)
		assert re.match(exp, data), (exp, data)
		if not rv["ble"]["exp_data"]:
			# No more data is expected
			for ((service, char, cb), kw) in bleConn.onNotify.call_args_list:
				cb(rv["ble"]["conn_status"])

	bleConn.write.side_effect = _connWrite

	return rv

def test_nopair_connect():
	data = setup()
	mb = data["mb"]
	db = data["db"]

	db.hasKey.return_value = True

	assert not mb.isConnected()

	mb.connect()

	assert mb.isConnected()

def test_conn_refused():
	data = setup()
	mb = data["mb"]
	db = data["db"]

	db.hasKey.return_value = True
	
	data["ble"]["conn_status"] = "\x03" * 16

	assert not mb.isConnected()

	with pytest.raises(excpt.NotPaired):
		mb.connect()

	assert not mb.isConnected()

def test_no_my_key():
	data = setup()
	mb = data["mb"]
	db = data["db"]

	db.hasKey.return_value = False

	assert not mb.isConnected()

	with pytest.raises(excpt.NotPaired):
		mb.connect()

	assert not mb.isConnected()

def test_led():
	data = setup()
	mb = data["mb"]
	db = data["db"]
	conn = data["ble"]["conn"]

	mb.connect()

	conn.write.side_effect = None
	for (r, g, b) in itertools.product([0, 1], [0, 1], [0, 1]):
		for dur in xrange(1, 255):
			mb.led(r, g, b, dur)
			((srv, ch, data), kw) = conn.write.call_args
			assert not kw
			assert (srv, ch) == ("1831", "2A14")
			bitTag = b << 2 | g << 1 | r
			expData = "\x01{}\x00\x00\x00{}".format(chr(bitTag), chr(dur))
			assert data == expData, (data, expData)
	