"""High-level library exceptions."""


class PyPushException(Exception):
    """Base class for all py push exceptions."""


class Timeout(PyPushException):
    """Timeout exception."""


class ConnectionError(PyPushException):
    """Generic connection error."""

class RemoteException(ConnectionError):
    """Remote exception."""

    def __init__(self, code, message):
        super(RemoteException, self).__init__(message)
        self.code = code

class NotPaired(ConnectionError):
    """Unable to connect to the microbot due to the pairing issue."""

    def __init__(self, status, message):
        super(NotPaired, self).__init__(message)
        self.status = status
