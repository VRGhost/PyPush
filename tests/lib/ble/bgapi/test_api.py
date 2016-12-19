"""PyProta bgapi library tests."""

import mock

import PyPush.lib.ble.bgapi as Mod


def fake_wraps(fn):
    """Fake functools.wraps."""
    return fn


@mock.patch("PyPush.lib.ble.bgapi.scanner.Scanner")
@mock.patch("PyPush.lib.ble.bgapi.api.BlueGigaClient")
@mock.patch("functools.wraps", fake_wraps)
def test_init_reset(BlueGigaMock, PushScanner):
    # one mandatory arg ("device")
    api = Mod.API({"device": "MYPORT"})
    api.start()
    BlueGigaMock.assert_called_once_with(
        baud=115200, port="MYPORT", timeout=0.1)
    BlueGigaMock().reset_ble_state.assert_called_once()
    PushScanner.assert_called_once()
    BlueGigaMock.reset_mock()
    PushScanner.reset_mock()

    # two args
    api = Mod.API({"device": "MYPORT", "baud": "MYBAUD"})
    api.start()
    BlueGigaMock.assert_called_once_with(
        baud="MYBAUD", port="MYPORT", timeout=0.1)
    BlueGigaMock().reset_ble_state.assert_called_once()
    PushScanner.assert_called_once()
    BlueGigaMock.reset_mock()
    PushScanner.reset_mock()

    # three args
    api = Mod.API({"device": "MYPORT", "baud": "MYBAUD", "timeout": "TM"})
    api.start()
    BlueGigaMock.assert_called_once_with(
        baud="MYBAUD", port="MYPORT", timeout="TM")
    BlueGigaMock().reset_ble_state.assert_called_once()
    PushScanner.assert_called_once()
    BlueGigaMock.reset_mock()
    PushScanner.reset_mock()
