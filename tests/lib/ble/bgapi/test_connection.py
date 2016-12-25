import collections
import time
import mock
import pytest
import itertools

import Queue

from bgapi.module import RemoteError as bgRemoteError

from PyPush.lib.ble.exceptions import RemoteException

import PyPush.lib.ble.bgapi.connection as ConMod

STR_TO_HEX = "PyPush.lib.ble.bgapi.byteOrder.nStrToHHex"

ServiceMock = collections.namedtuple("ServiceMock", ["uuid", "start_handle", "end_handle"])
CharacteristicMock = collections.namedtuple(
    "CharacteristicMock", ["uuid", "handle"])


def noop1(arg):
    return arg


@mock.patch(STR_TO_HEX, noop1)  # prevents service UUID translation
def test_connection_open():
    mb = mock.MagicMock()  # Microbot object
    ble = mock.MagicMock()  # BlueGiga BLE Client object.
    bleConn = ble.getChildLock.return_value

    _mkChar = lambda idx: CharacteristicMock("CHAR:{}".format(idx), idx)

    S1 = ServiceMock("SER_1", 0, 2)
    S2 = ServiceMock("SER_2", 3, 4)
    S3 = ServiceMock("SER_3", 10, 20)
    CHARS = {
        S1: [
            _mkChar(0),
        ],
        S2: [
            _mkChar(3),
            _mkChar(4),
        ],
        S3: [
            _mkChar(10),
            _mkChar(15),
            _mkChar(19),
        ],
    }

    ble.getChildLock.return_value.get_services.return_value = \
        ALL_SERVICES = (S1, S2, S3)
    ble.getChildLock.return_value.get_characteristics.return_value = \
        tuple(itertools.chain(*CHARS.values()))

    conn = ConMod.BgConnection(mb, ble)
    conn._open()


    mb.getApiTarget.assert_called_once()
    ble.connect.assert_called_once_with(mb.getApiTarget(), timeout=10)
    ble.getChildLock.assert_called_once_with(ble.connect.return_value)


    # test internal characteristic memory
    mem = conn._serviceToCharacteristics
    assert set(mem.keys()) == set(["SER_1", "SER_2", "SER_3"])
    assert set(ch.uuid for ch in mem["SER_1"]) == set(["CHAR:0"])
    assert set(ch.uuid for ch in mem["SER_2"]) == set(["CHAR:3", "CHAR:4"])
    assert set(ch.uuid for ch in mem["SER_3"]) == set(
        ["CHAR:10", "CHAR:15", "CHAR:19"])

    # test _findService
    assert conn._findService("SER_1") == S1, conn._findService("SER_1")
    assert conn._findService("SER_2") == S2
    assert conn._findService("SER_3") == S3
    with pytest.raises(KeyError):
        conn._findService("SER_0")

    # test _finCharacteristics
    assert conn._findCharacteristic(
        "SER_1", "CHAR:0").gatt == CHARS[S1][0]
    assert conn._findCharacteristic(
        "SER_3", "CHAR:15").gatt == CHARS[S3][1]

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
    Service = ServiceMock("SERV", 0, 100)
    Char = mock.Mock()
    Char.uuid = "CHAR"
    Char.handle = 10

    ble.getChildLock.return_value.get_services.return_value = (Service, )
    bleConn.get_characteristics.return_value = (Char, )

    bleConn.reset_mock()

    return {
        "service": Service,
        "char": Char,
        "connection": ConMod.BgConnection(mb, ble),
        "bleConnection": bleConn,
    }


@mock.patch(STR_TO_HEX, noop1)
@mock.patch("time.sleep", noop1)
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
@mock.patch("time.sleep", noop1)
def test_ok_read():
    conn = get_mocked_connection()
    conn["char"].is_writable.return_value = True
    conn["connection"]._open()
    conn["connection"].read("SERV", "CHAR")
    conn["bleConnection"].read_by_handle.assert_called_once_with(
        11, timeout=15)

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
        "bleConnection"].read_by_handle.call_count == 5, "Read operation retries 5 times by default"


@mock.patch(STR_TO_HEX, noop1)
@mock.patch("time.sleep", noop1)
def test_on_notify():

    cbQ = Queue.Queue()

    handle = get_mocked_connection()
    conn = handle["connection"]
    ble = handle["bleConnection"]
    ble.get_handles_by_uuid.return_value = (42, )

    conn._open()
    cb = conn.onNotify("SERV", "CHAR", cbQ.put)

    ble.characteristic_subscription.assert_called_once()
    ble.assign_attrclient_value_callback.assert_called_once()
    (_bleH, _cbHandle) = ble.assign_attrclient_value_callback.call_args[0]

    print _cbHandle
    _cbHandle("BLE DATA PASSED")
    data = cbQ.get(timeout=10)
    assert data == "BLE DATA PASSED"

    cb.cancel()

    _cbHandle("TEST 2")
    with pytest.raises(Queue.Empty):
        cbQ.get(timeout=5) # Subscription was cancelled


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
