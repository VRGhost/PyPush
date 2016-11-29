import datetime
import mock

import PyPush.lib.hub as Mod

def _retBleMb(bleLib, bleMb, keyDb):
	return bleMb

@mock.patch("PyPush.lib.ble.getLib")
@mock.patch("threading.Timer")
@mock.patch("PyPush.lib.microbot.MicrobotPush", _retBleMb)
def test_microbot_gc(timerMock, bleGetLib):
	config = {}
	db = mock.Mock()

	HUB = Mod.PushHub(config, db)

	assert timerMock.call_count == 1
	now = datetime.datetime.now()
	def _getMb(lastSeenTime):
		mb = mock.Mock()
		lastSeen = now - datetime.timedelta(seconds=lastSeenTime)
		mb.getLastSeen.return_value = lastSeen
		mb.getUID.return_value = lastSeen.isoformat() 
		return mb

	# Populate with few old & new microbots
	HUB._onBleScan(_getMb(1))
	assert len(HUB.getAllMicrobots()) == 1
	HUB._onBleScan(_getMb(60))
	assert len(HUB.getAllMicrobots()) == 2
	HUB._onBleScan(_getMb(24 * 60 * 60 - 60)) # 1 minute less daytime. should remain in the list after gc
	assert len(HUB.getAllMicrobots()) == 3
	HUB._onBleScan(_getMb(24 * 60 * 60 + 1)) # 1 second over default gc max age
	assert len(HUB.getAllMicrobots()) == 4

	HUB._onBleScan(_getMb(60))
	assert len(HUB.getAllMicrobots()) == 4, "Mb with this UUID has been already added"

	# execute garbage collection callback
	(_, cb) = timerMock.call_args[0]
	
	cb()

	assert len(HUB.getAllMicrobots()) == 3, "The daytime + 1 second should be removed"