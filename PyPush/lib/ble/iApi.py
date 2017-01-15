from abc import ABCMeta, abstractmethod, abstractproperty


class iApi(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def start(self):
        """Start any associated daemon threads."""

    @abstractmethod
    def onScan(self, callback):
        """This method calls `callback` on every microbot push detect via BLE scan.

        The callback will receive an <iMicrobotPush> object as an argument.

        This function returns a canceller (callable that deregisters `callback` from onScan method).

        """

    @abstractmethod
    def connect(self, mbPush):
        """This method initiates BLE connection to the <iMicrobotPush> provided as an argument.

        Returns <iConnection> object
        """

    @abstractmethod
    def createMicrobotFromUUID(self, uuid):
        """Create microbot object from an UUID.
        
            UUID is a human-readable form of the UUID
        """

    @abstractmethod
    def getUID(self):
        """Return UUID this host is using to access BLE."""


class iMicrobotPush(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def getName(self):
        """Returns name of this microbot."""

    @abstractmethod
    def getLastSeen(self):
        """Returns datetime when this microbot was last observerd by the system."""

    def getUID(self):
        """Returns an unique string identifying this particular microbot device."""


class iConnection(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def getMicrobot(self):
        """Returns <iMicrobotPush> this connection is attached to."""

    @abstractmethod
    def readAllCharacteristics(self):
        """Returns dict of all Service id -> CharacteristicId-> Value for the `serviceId`.

        This is a debug function that is used for analysing changes in the bot's state.
        """

    @abstractmethod
    def onNotify(self, serviceId, characteristicId, callback):
        """Bind `callback` to execute on each notify event of the characteristic::service.

        Returns <PyPush.lib.async.SubscriptionHandle>.

        Raises exceptions.NotSupported if notify capability is not supported.
        """

    @abstractmethod
    def write(self, serviceId, characteristicId, data):
        """Write data to the characteristic::service."""

    @abstractmethod
    def read(self, serviceId, characteristicId, timeout=5):
        """Reads data for the characteristic::service."""

    @abstractmethod
    def isActive(self):
        """Returns `True` if this connection is still active."""

    @abstractmethod
    def close(self):
        """Closes this connection."""

    @abstractmethod
    def transaction(self):
        """This context locks the connection for the duration of the context."""

    @abstractmethod
    def getLastActiveTime(self):
        """Returns datetime.datetime of when the last activity on the connection had been detected."""
