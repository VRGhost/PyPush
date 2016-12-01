import mock
import re

import PyPush.lib.microbot as Mod
import PyPush.lib.iLib as iLib
import PyPush.lib.ble.iApi as iBle

MB_UID = "HELLO_WORLD_MOCK_MICROBOT_UID"
PAIR_KEY = "1234567890123456"

def setup():
	bleApi = mock.create_autospec(iBle.iApi)
	bleMb = mock.create_autospec(iBle.iMicrobotPush)
	keyDb = mock.create_autospec(iLib.iPairingKeyStorage)
	bleConn = mock.create_autospec(iBle.iConnection)

	bleApi.connect.return_value = bleConn

	bleMb.getUID.return_value = MB_UID

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

	notifyH = mock.create_autospec(iBle.iNotifyHandle)
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
	db.get.return_value = PAIR_KEY
	# db["ble"]["conn"].onNotify.return_value = 

	assert not mb.isConnected()

	mb.connect()

	assert mb.isConnected()