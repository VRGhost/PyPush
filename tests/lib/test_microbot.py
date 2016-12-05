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
HOST_UID = "MOCKED_HOST_UID"
PAIR_KEY = "1234567890123456"


def setup():
    bleApi = mock.create_autospec(iBle.iApi)
    bleMb = mock.create_autospec(iBle.iMicrobotPush)
    keyDb = mock.create_autospec(iLib.iPairingKeyStorage)
    bleConn = mock.create_autospec(iBle.iConnection)

    bleApi.connect.return_value = bleConn

    bleMb.getUID.return_value = MB_UID
    keyDb.get.return_value = PAIR_KEY
    bleApi.getUID.return_value = HOST_UID

    mb = Mod.MicrobotPush(bleApi, bleMb, keyDb)

    rv = {
        "mb": mb,
        "db": keyDb,
        "ble": {
            "api": bleApi,
            "mb": bleMb,
            "conn": bleConn,
            "data": {
                ("1831", "2A98"): [
                    # Receive a string
                    {"t": "RECV", "d": "^.*{}$".format(PAIR_KEY)},
                    # Send a string
                    {"t": "SEND", "d": "\x01" + ("\x00" * 15)},
                ]
            },
            "handle_cb": []
        }
    }

    notifyH = mock.create_autospec(Subscribe.iHandle)
    bleConn.onNotify.return_value = notifyH

    def _connWrite(service, char, data):
        key = (service, char)
        assert key in rv["ble"]["data"], rv["ble"]["data"]
        script = rv["ble"]["data"][key]

        exp = script.pop(0)
        assert exp["t"] == "RECV", exp  # Expecing an 'expect command'
        assert re.match(exp["d"], data), (key, exp["d"], data)
        if script and script[0]["t"] == "SEND":
            # Send command
            data = script.pop(0)["d"]
            for ((cbService, cbChar, cb),
                 kw) in bleConn.onNotify.call_args_list:
                if cbService == service and cbChar == char:
                    cb(data)

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

    # change the return code to the authorisation request
    data["ble"]["data"][("1831", "2A98")][-1]["d"] = "\x03" * 16

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


def test_pair_success():
    data = setup()
    mb = data["mb"]
    db = data["db"]

    assert not mb.isConnected()

    data["ble"]["data"].update({
        ("1831", "2A98"): [
            # change the return code to the authorisation request
            {"t": "RECV", "d": ".*\x00{16}"},
            {"t": "SEND", "d": "\x02" * 16},
        ],
        ("1831", "2A90"): [
            # Pair service dialogue
            {"t": "RECV", "d": chr(len(HOST_UID)) + HOST_UID + ".*"},
            {"t": "RECV", "d": "\x00"},
            {"t": "SEND", "d": "\x01" + PAIR_KEY},
        ],
        ("1831", "2A14"): [
            # LED writes
            {"t": "RECV", "d": ".*"},
        ],
    })

    for x in mb.pair():
        pass

    assert mb.isConnected()
    db.set.assert_called_with(MB_UID, PAIR_KEY)


def test_pair_no_touch():
    data = setup()
    mb = data["mb"]
    db = data["db"]

    assert not mb.isConnected()

    data["ble"]["data"].update({
        ("1831", "2A98"): [
            # change the return code to the authorisation request
            {"t": "RECV", "d": ".*\x00{16}"},
            {"t": "SEND", "d": "\x02" * 16},
        ],
        ("1831", "2A90"): [
            # Pair service dialogue
            {"t": "RECV", "d": chr(len(HOST_UID)) + HOST_UID + ".*"},
            {"t": "RECV", "d": "\x00"},
            {"t": "SEND", "d": "\x04" * 17},
        ],
        ("1831", "2A14"): [
            # LED writes
            {"t": "RECV", "d": ".*"},
        ],
    })

    with pytest.raises(excpt.NotPaired):
        for x in mb.pair():
            pass

    assert not mb.isConnected()
