import collections

import mock
import pytest

import PyPush.lib.ble.bgapi.connection as ConMod

ServiceMock = collections.namedtuple("ServiceMock", ["uuid"])
CharacteristicMock = collections.namedtuple(
	"CharacteristicMock", ["uuid", "handle"])

def noop1(arg):
	return arg

@mock.patch("PyPush.lib.ble.bgapi.bOrder.nStrToHHex", noop1) # prevents service UUID translation
def test_connection_open():
	mb = mock.MagicMock() # Microbot object
	ble = mock.MagicMock() # BlueGiga BLE Client object.
	bleConn = ble.getChildLock.return_value

	CHAR_MEMORY = {
		"ch": [],
		"idx": 0
	}
	def _genNewChars():
		CHAR_MEMORY["idx"] += 1
		if CHAR_MEMORY["idx"] == 1:
			# Ignore the first call
			return

		# each sucessive call generates one more char than the previous one
		start_idx = len(CHAR_MEMORY["ch"])
		end_idx = start_idx + (start_idx + 1)
		for idx in xrange(start_idx, end_idx):
			sIdx = str(idx)
			char = CharacteristicMock(
				"CHAR:" + sIdx, "HANDLE:" + sIdx)
			CHAR_MEMORY["ch"].append(char)
		return tuple(CHAR_MEMORY["ch"])

	bleConn.get_characteristics.side_effect = _genNewChars

	S1 = ServiceMock("SER_1")
	S2 = ServiceMock("SER_2")
	S3 = ServiceMock("SER_3")

	ble.getChildLock.return_value.get_services.return_value = \
		ALL_SERVICES = (S1, S2, S3)

	conn = ConMod.BgConnection(mb, ble)
	conn._open()

	mb.getApiTarget.assert_called_once()
	ble.connect.assert_called_once_with(mb.getApiTarget(), timeout=10)
	ble.getChildLock.assert_called_once_with(ble.connect.return_value)

	bleConn.read_by_group_type.assert_called_once()
	assert bleConn.find_information.call_count == len(ALL_SERVICES)
	assert bleConn.get_characteristics.call_count == len(ALL_SERVICES) + 1
	assert bleConn.read_by_type.call_count == len(ALL_SERVICES) * 3

	# test internal characteristic memory
	mem = conn._serviceToCharacteristics
	assert set(mem.keys()) == set(["SER_1", "SER_2", "SER_3"])
	assert set(ch.uuid for ch in mem["SER_1"]) == set(["CHAR:0"])
	assert set(ch.uuid for ch in mem["SER_2"]) == set(["CHAR:1", "CHAR:2"])
	assert set(ch.uuid for ch in mem["SER_3"]) == set(["CHAR:3", "CHAR:4", "CHAR:5", "CHAR:6"])

	# test _findService
	assert conn._findService("SER_1") == S1
	assert conn._findService("SER_2") == S2
	assert conn._findService("SER_3") == S3
	with pytest.raises(KeyError):
		conn._findService("SER_0")

	# test _finCharacteristics
	assert conn._findCharacteristic("SER_1", "CHAR:0").gatt == CHAR_MEMORY["ch"][0]
	assert conn._findCharacteristic("SER_3", "CHAR:4").gatt == CHAR_MEMORY["ch"][4]

	with pytest.raises(KeyError):
		conn._findCharacteristic("SER_0", "CHAR:0")

	with pytest.raises(KeyError):
		conn._findCharacteristic("SER_1", "CHAR:4")