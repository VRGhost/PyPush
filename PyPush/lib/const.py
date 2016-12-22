import enum

MicrobotServiceId = "1831"
PushServiceId = "1821"
InfoServiceId = "180A"

DeviceCalibration = "2A35"
DeviceStatus = "2A15"

@enum.unique
class ButtonMode(enum.IntEnum):
    """Microbot supports few behaviours for the case when user touches button on the device itself.

    This enum represents those states.
    """

    default = 0x00 # retracted by default, extends when user touches the button
    inverted = 0x01 # extended by default, retracts when user toucher the button