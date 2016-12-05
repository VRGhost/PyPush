"""Interfaces for high-level API object this library uses/provides."""

from abc import ABCMeta, abstractmethod, abstractproperty


class iPairingKeyStorage(object):
    """This is an expected interface for the pairing key storage object this library uses.

    The storage object is provided by the librarys' user.

    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def hasKey(self, uid):
        """Returns `True` if the library contains key for the uid `UID`.
        Returns `False` otherwise

        `UID` is string.
        """

    @abstractmethod
    def get(self, uid):
        """Returns pairing key for the `uid` (string). Raises KeyError if not found."""

    @abstractmethod
    def set(self, uid, key):
        """Saves pairing key `key` (string) for `uid` (string). Overwrites previous key if existed."""

    @abstractmethod
    def delete(self, uid):
        """Deletes pairing key for `uid` if existed. Silently returns if there was no such key."""


class iHub(object):
    """Microbot management hub. Top-level interface for this library."""
    __metaclass__ = ABCMeta

    @abstractmethod
    def onMicrobot(self, onDiscovered, onLost):
        """Executes `onDiscovered` callback when a new microbot is discovered, calls `onLost` callback when a microbot is lost."""

    @abstractmethod
    def getMicrobot(self, nameOrUid, timeout=0):
        """Returns Microbot object mathing the name or UID provided.

        Blocks for about `timeout` seconds if no such object is yet found (if timeout > 0).

        """

    @abstractmethod
    def getAllMicrobots(self):
        """Returns an interable of all microbots currently known to the system."""


class iMicrobot(object):
    """High-level microbot interface."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def getLastSeen(self):
        """Returns datetime when this microbot had shown signs of life for the last time."""

    @abstractmethod
    def getName(self):
        """Returns name of this microbot."""

    @abstractmethod
    def getUID(self):
        """Returns UID of this microbot."""

    @abstractmethod
    def isPaired(self):
        """Returns `True` if there is a pairing key for this microbot."""

    @abstractmethod
    def isConnected(self):
        """Returns `True` if the system has active connection to this microbot."""

    @abstractmethod
    def led(self, r, g, b, duration):
        """Lights microbot's LED to the (r, g, b) color (each element is either True or False, no shades) for the `duration` seconds."""

    @abstractmethod
    def connect(self):
        """Connect to the Microbot.

        Raises exception if unable to traverse complete connect & auth sequence.

        """

    @abstractmethod
    def disconnect(self):
        """Disconnect from the microbot."""

    @abstractmethod
    def extend(self):
        """Extend microbot's pusher."""

    @abstractmethod
    def retract(self):
        """Retract microbot's pusher."""

    @abstractmethod
    def isRetracted(self):
        """Return `True` if the arm is retracted."""

    @abstractmethod
    def setCalibration(self, percentage):
        """Set how far the microbot should extend its arm."""

    @abstractmethod
    def getCalibration(self):
        """Retreive device's calibration level (0...1)."""

    @abstractmethod
    def getBatteryLevel(self):
        """Retreive battery level (0...1)."""

    @abstractmethod
    def deviceBlink(self, seconds):
        """Blink device for a `seconds` seconds."""

    @abstractmethod
    def pair(self):
        """Performs pairing with this microbot.

        Rewrites the pairing key stored in the key database.

        THIS METHOD IS RETURNS AN ITERATOR.

        The iterator yields (r, g, b) tuples (with each element being either `True` or `False`) while the microbot is waiting for the user touch.
        Colours returned coincide wit the colours microbot's LED is showing at the moment.
        """

    @abstractmethod
    def onStateChange(self, cb):
        """Registers a new callback that will be fired whenever this microbot object experiences a change of state."""
