"""Core-related interfaces."""

from abc import ABCMeta, abstractmethod, abstractproperty

class iDbConnection(object):
    """Database connection object."""

    @abstractmethod
    def open(self, uri):
        """Open connection to the URI."""

    @abstractmethod
    def session(self):
        """A context that returns new database session."""

class iUI(object):
    """Core User Interface object."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def run(self):
        """Run the user interface thread."""

class iCore(object):
    """PyPush core interface."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def setUI(self):
        """Set the <iUI> user interface object for the core."""

    @abstractmethod
    def run(self):
        """Run the PyPush app."""

    @abstractmethod
    def getPairDb(self):
        """Return pair db used for the microbot auth."""

    @abstractmethod
    def setMicrobotApi(self, api):
        """Sets the microbot <PyPush.lib.iLib.iHub> to be used by the core."""

    @abstractmethod
    def setDbConnection(self, db):
        """Set the <iDbConnection> connection to be used for the core."""

    @abstractmethod
    def getDbSession(self):
        """This is a context that returns (db, session) tuple for the database the core is connected to."""