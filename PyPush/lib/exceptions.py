"""High-level library exceptions."""


class PyPushException(Exception):
    """Base class for all py push exceptions."""


class Timeout(PyPushException):
    """Timeout exception."""

class StateChangeError(Timeout):
    """This exception is raised when microbot's state is not as expected."""

class ConnectionError(PyPushException):
    """Generic connection error."""

class IOError(ConnectionError):
    """An Input/Output error with the microbot occured."""

class WrongConnectionState(ConnectionError):
    """Not connected to the destination when has to be, disconnected when hasn't."""

class RemoteException(ConnectionError):
    """Remote exception."""

    def __init__(self, code, message):
        super(RemoteException, self).__init__(message)
        self.code = code

class NotPaired(ConnectionError):
    """Unable to connect to the microbot due to the pairing issue."""

    def __init__(self, code, message):
        super(NotPaired, self).__init__("{} ({:02X})".format(message, code))
        self.code = code
