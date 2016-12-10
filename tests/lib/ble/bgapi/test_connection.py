import collections
import time
import mock
import pytest

from bgapi.module import RemoteError as bgRemoteError

from PyPush.lib.ble.exceptions import RemoteException

import PyPush.lib.ble.bgapi.connection as ConMod

STR_TO_HEX = "PyPush.lib.ble.bgapi.byteOrder.nStrToHHex"

ServiceMock = collections.namedtuple("ServiceMock", ["uuid"])
CharacteristicMock = collections.namedtuple(
    "CharacteristicMock", ["uuid", "handle"])


def noop1(arg):
    return arg


@mock.patch(STR_TO_HEX, noop1)  # prevents service UUID translation
def test_connection_open():
    mb = mock.MagicMock()  # Microbot object
    ble = mock.MagicMock()  # BlueGiga BLE Client object.
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
    assert bleConn.read_by_type.call_count == len(ALL_SERVICES) * 2

    # test internal characteristic memory
    mem = conn._serviceToCharacteristics
    assert set(mem.keys()) == set(["SER_1", "SER_2", "SER_3"])
    assert set(ch.uuid for ch in mem["SER_1"]) == set(["CHAR:0"])
    assert set(ch.uuid for ch in mem["SER_2"]) == set(["CHAR:1", "CHAR:2"])
    assert set(ch.uuid for ch in mem["SER_3"]) == set(
        ["CHAR:3", "CHAR:4", "CHAR:5", "CHAR:6"])

    # test _findService
    assert conn._findService("SER_1") == S1, conn._findService("SER_1")
    assert conn._findService("SER_2") == S2
    assert conn._findService("SER_3") == S3
    with pytest.raises(KeyError):
        conn._findService("SER_0")

    # test _finCharacteristics
    assert conn._findCharacteristic(
        "SER_1", "CHAR:0").gatt == CHAR_MEMORY["ch"][0]
    assert conn._findCharacteristic(
        "SER_3", "CHAR:4").gatt == CHAR_MEMORY["ch"][4]

    with pytest.raises(KeyError):
        conn._findCharacteristic("SER_0", "CHAR:0")

    with pytest.raises(KeyError):
        conn._findCharacteristic("SER_1", "CHAR:4")


def get_mocked_connection():
    """
    Creates an openable `BgConnection`.

    The connection contains a single service "SERV" with one characteristics "CHAR"
    when opened.
    """
    mb = mock.MagicMock()  # Microbot object
    ble = mock.MagicMock()  # BlueGiga BLE Client object.
    bleConn = ble.getChildLock.return_value
    Service = ServiceMock("SERV")
    Char = mock.Mock()
    Char.uuid = "CHAR"
    Char.handle = 10

    def _charRvIter():
        yield ()
        yield (Char, )

    ble.getChildLock.return_value.get_services.return_value = (Service, )
    bleConn.get_characteristics.side_effect = _charRvIter().next

    bleConn.reset_mock()

    return {
        "service": Service,
        "char": Char,
        "connection": ConMod.BgConnection(mb, ble),
        "bleConnection": bleConn,
    }


@mock.patch(STR_TO_HEX, noop1)
def test_ok_write():
    conn = get_mocked_connection()
    conn["char"].is_writable.return_value = True
    conn["connection"]._open()
    conn["connection"].write("SERV", "CHAR", 42)
    conn["bleConnection"].write_by_uuid.assert_called_once_with(
        "CHAR", 42, timeout=15)

    conn["bleConnection"].reset_mock()
    conn["connection"].write("SERV", "CHAR", "\x00\x43")
    conn["bleConnection"].write_by_uuid.assert_called_once_with(
        "CHAR", "\x00\x43", timeout=15)


@mock.patch(STR_TO_HEX, noop1)
def test_ok_read():
    conn = get_mocked_connection()
    conn["char"].is_writable.return_value = True
    conn["connection"]._open()
    conn["connection"].read("SERV", "CHAR")
    conn["bleConnection"].read_by_handle.assert_called_once_with(
        11, timeout=5)

    conn["bleConnection"].reset_mock()
    conn["connection"].read("SERV", "CHAR", -42)
    conn["bleConnection"].read_by_handle.assert_called_once_with(
        11, timeout=-42)


@mock.patch(STR_TO_HEX, noop1)
@mock.patch("time.sleep", noop1)
def test_fail_write():
    conn = get_mocked_connection()
    conn["char"].is_writable.return_value = True
    conn["connection"]._open()
    conn["bleConnection"].write_by_uuid.side_effect = bgRemoteError(0x0181)
    with pytest.raises(RemoteException):
        conn["connection"].write("SERV", "CHAR", 42)
    assert conn[
        "bleConnection"].write_by_uuid.call_count == 5, "Write operation performs 5 retries by default"


@mock.patch(STR_TO_HEX, noop1)
@mock.patch("time.sleep", noop1)
def test_fail_read():
    conn = get_mocked_connection()
    conn["char"].is_writable.return_value = True
    conn["connection"]._open()
    conn["bleConnection"].read_by_handle.side_effect = bgRemoteError(0x0181)
    with pytest.raises(RemoteException):
        conn["connection"].read("SERV", "CHAR")
    assert conn[
        "bleConnection"].read_by_handle.call_count == 1, "Read operation does not retry"


@mock.patch(STR_TO_HEX, noop1)
def test_on_notify():
    callFn = mock.MagicMock()
    handle = get_mocked_connection()
    conn = handle["connection"]
    ble = handle["bleConnection"]
    ble.get_handles_by_uuid.return_value = (42, )

    conn._open()
    cb = conn.onNotify("SERV", "CHAR", callFn)

    ble.characteristic_subscription.assert_called_once()
    ble.assign_attrclient_value_callback.assert_called_once()
    (_bleH, _cbHandle) = ble.assign_attrclient_value_callback.call_args[0]

    _cbHandle("BLE DATA PASSED")
    time.sleep(0.2) # Give internal thread a chance to work
    callFn.assert_called_once_with("BLE DATA PASSED")

    callFn.reset_mock()
    cb.cancel()

    _cbHandle("TEST 2")
    assert callFn.call_count == 0, "Subscription was cancelled."


@mock.patch(STR_TO_HEX, noop1)
@mock.patch("time.sleep", noop1)
def test_notify_error():
    callFn = mock.MagicMock()
    handle = get_mocked_connection()
    conn = handle["connection"]
    ble = handle["bleConnection"]

    conn._open()

    ble.get_handles_by_uuid.return_value = (42, )
    ble.characteristic_subscription.side_effect = bgRemoteError(0x0181)

    with pytest.raises(RemoteException):
        conn.onNotify("SERV", "CHAR", callFn)

    assert ble.characteristic_subscription.call_count == 5
