"""BLE connection interface."""

import logging
import time
import collections
import threading
import contextlib
import functools
import datetime
import Queue

from bgapi.module import (
    BLEConnection, GATTService, GATTCharacteristic,
    BlueGigaModuleException, RemoteError, Timeout,
)


from PyPush.lib import async as async

from .. import (
    iApi,
    exceptions,
)

from . import byteOrder

BgCharacteristic = collections.namedtuple(
    "BgCharacteristic", ["uuid", "gatt", "human_uuid"])

RetryLog = logging.getLogger("retry_call_if_fails")
def retry_call_if_fails(connection, func, attempts, fail_delay=3,
                        delayed_unlock=0.5, retry_on_remote_err=(), retry_on_timeout=False):
    attempts_left = attempts
    while True:
        attempts_left -= 1

        try:
            with connection.delayedUnlock(delayed_unlock):
                rv = func()
        except RemoteError as err:
            # Device is in the wrong state.
            if err.code in retry_on_remote_err and attempts_left > 0:
                pass
            else:
                raise
        except Timeout:
            if retry_on_timeout and attempts_left > 0:
                pass
            else:
                raise
        else:
            return rv

        # Exception happened
        time.sleep(fail_delay)


class _ConnNotify(async.SubscribeHub):

    delay = 0.1  # seconds
    _isActive = False
    _timer = None

    def __init__(self, hub, characteristic):
        super(_ConnNotify, self).__init__()
        self.characteristic = characteristic
        self.hub = hub

    def onSubscribe(self, handle):
        super(_ConnNotify, self).onSubscribe(handle)
        self._manage()

    def onUnsubscribe(self, handle):
        super(_ConnNotify, self).onUnsubscribe(handle)
        self._manage()

    def _manage(self):
        """Manage 'subscribed' status."""
        with self._mutex:
            if self.getSubscriberCount() > 0 and not self._isActive:
                conn = self._getBleConn()
                for handle in conn.get_handles_by_uuid(
                        self.characteristic.uuid):
                    conn.assign_attrclient_value_callback(
                        handle, self._onBgapiNotify)
                retry_call_if_fails(
                    conn,
                    lambda: conn.characteristic_subscription(
                        self.characteristic.gatt, indicate=False,
                        notify=True, timeout=10
                    ),
                    attempts=5, retry_on_remote_err=(0x0181, ), retry_on_timeout=True
                )

                # Subscribed for notifications
                self._isActive = True

    def _getBleConn(self):
        conn = self.hub.conn
        assert conn.isActive(), conn
        return conn._bleConn

    def _onBgapiNotify(self, data):
        self.hub.bgapiQueue.put(
            (self, data)
        )
        self.hub.conn._updateLastCallTime()


class _ConnNotifyHub(object):

    def __init__(self, conn):
        self.conn = conn
        self.subscriberHubs = {}
        self._mutex = threading.RLock()
        self.bgapiQueue = Queue.Queue()

        self.apiThread = threading.Thread(
            name="{}.thread".format(__name__),
            target=self._hubThreadTarget,
            args=(self.bgapiQueue,) ,
        )
        self.apiThread.daemon = True
        self.apiThread.start()

    def addCallback(self, characteristic, cb):
        key = characteristic.uuid
        with self._mutex:
            try:
                subs = self.subscriberHubs[key]
            except KeyError:
                subs = _ConnNotify(self, characteristic)
                self.subscriberHubs[key] = subs
        return subs.subscribe(cb)

    def _hubThreadTarget(self, bgapiQueue):
        log = logging.getLogger("_ConnNotifyHub.thread")
        while True:
            (handler, data) = bgapiQueue.get()
            try:
                handler.fireSubscribers(data)
            except Exception:
                log.exception("Hub target exception.")

def ActiveApi(func):
    """Decorator that ensures that the connection is active before the payload function is executed.

    Also performs translation of bgapi exceptions to PyPush.lib.ble.exceptions.
    """
    @functools.wraps(func)
    def _wrapper_(self, *args, **kwargs):
        if not self.isActive():
            raise exceptions.NotConnected("The connection is no longer active")

        self._updateLastCallTime()
        try:
            return func(self, *args, **kwargs)
        except RemoteError as err:
            raise exceptions.RemoteException(err.code, err.message)
        except Timeout as err:
            raise exceptions.Timeout(str(err))
        else:
            self._updateLastCallTime()

    return _wrapper_


class BgConnection(iApi.iConnection):

    _log = logging.getLogger(__name__)
    _mb = _ble = _bleConn = None

    def __init__(self, mb, ble):
        self._mb = mb
        self._ble = ble
        self._bleConn = None
        # service UUID -> [characteristic UUID]
        self._serviceToCharacteristics = {}
        self._notifyHub = _ConnNotifyHub(self)
        self._lastCallTime = 0

    def getMicrobot(self):
        return self._mb

    def isActive(self):
        return (self._bleConn is not None) and self._bleConn.is_connected()

    def close(self):
        with self.transaction():
            if self.isActive():
                self._ble.disconnect(self._bleConn.handle)
                self._log.info("BgConnection {} closed.".format(self))
        self._bleConn = None

    def getAllServices(self):
        assert self.isActive()
        return [self._humanServiceName(el)
                for el in self._bleConn.get_services()]

    @ActiveApi
    def readAllCharacteristics(self):
        rv = {}
        for srv in self._bleConn.get_services():
            rv[self._humanServiceName(srv)] = srvData = {}
            for char in self._serviceToCharacteristics[srv.uuid]:
                if char.gatt.is_readable():
                    self._bleConn.read_by_handle(char.gatt.handle + 1)
                    value = char.gatt.value
                else:
                    value = None
                srvData[char.human_uuid] = value

        return rv

    @ActiveApi
    def onNotify(self, serviceId, characteristicId, callback):
        service = self._findService(serviceId)
        char = self._findCharacteristic(serviceId, characteristicId)
        if not char.gatt.has_notify():
            raise exceptions.NotSupported("Notify is not supported.")

        return self._notifyHub.addCallback(char, callback)

    @ActiveApi
    def write(self, serviceId, characteristicId, data):
        assert self.isActive()
        char = self._findCharacteristic(serviceId, characteristicId)

        if not char.gatt.is_writable():
            raise exceptions.NotSupported("Write is not supported.")

        return retry_call_if_fails(
            self._bleConn,
            lambda: self._bleConn.write_by_uuid(char.uuid, data, timeout=15),
            attempts=5, retry_on_remote_err=(0x0181, ),
            retry_on_timeout=True
        )

    @ActiveApi
    def read(self, serviceId, characteristicId, timeout=5):
        char = self._findCharacteristic(serviceId, characteristicId)
        if not char.gatt.is_readable():
            raise exceptions.NotSupported("Read is not supported.")

        self._bleConn.read_by_handle(char.gatt.handle + 1, timeout=timeout)
        return char.gatt.value

    @contextlib.contextmanager
    def transaction(self):
        with self._ble.transaction():
            yield

    def getLastActiveTime(self):
        return datetime.datetime.fromtimestamp(self._lastCallTime)

    def _open(self):
        """Initiate the connection."""
        assert not self.isActive()
        with self.transaction():
            conn = self._ble.connect(self._mb.getApiTarget(), timeout=10)
            conn = self._ble.getChildLock(conn)
            self._bleConn = self._initBleConnection(conn)
        self._log.info("BgConnection {} opened.".format(self))

    def _findCharacteristic(self, serviceUUID, charUUID):
        srv_uuid = self._findService(serviceUUID).uuid
        conn = self._bleConn
        for char in self._lazyLoadCharacteristics(conn, srv_uuid):
            if char.human_uuid == charUUID:
                return char
        # else
        raise KeyError([serviceUUID, charUUID])

    def _findService(self, uuid):
        for el in self._bleConn.get_services():
            if self._humanServiceName(el) == uuid:
                return el
        raise KeyError(uuid)

    def _humanServiceName(self, service):
        return byteOrder.nStrToHHex(service.uuid)

    def _initBleConnection(self, conn):
        """This method initialises internal state of the BLE connection by populating its internal dictionaries."""
        with conn.transaction():
            conn.set_min_connection_interval(0.5) # min 0.5 delay for the conn interval
            conn.read_by_group_type(
                    GATTService.PRIMARY_SERVICE_UUID, timeout=10)

        return conn

    def _lazyLoadCharacteristics(self, connection, serviceUUID):
        """Load information about a particular service."""
        try:
            return self._serviceToCharacteristics[serviceUUID]
        except KeyError:
            pass

        service = [el for el in connection.get_services() if el.uuid == serviceUUID]
        if not service:
            raise Exception("Service {!r} not found".format(serviceUUID))
        assert len(service) == 1, service
        service = service[0]

        connection.find_information(service=service)
        prevHandles = frozenset(el.handle for el in connection.get_characteristics())

        for serviceType in (
            GATTCharacteristic.CHARACTERISTIC_UUID,
            GATTCharacteristic.CLIENT_CHARACTERISTIC_CONFIG,
        ):
            try:
                connection.read_by_type(service, serviceType, timeout=10)
            except RemoteError as err:
                if err.code == 0x040A:
                    # Attribute not found. Seems to be occasional
                    # occurence with microbots.
                    pass
                else:
                    raise

        self._serviceToCharacteristics[service.uuid] = rv = tuple(
            BgCharacteristic(ch.uuid, ch, byteOrder.nStrToHHex(ch.uuid))
            for ch in connection.get_characteristics()
            if ch.handle not in prevHandles
        )
        return rv

    def _updateLastCallTime(self):
        """Updates last call time to current time."""
        self._lastCallTime = time.time()

    def __repr__(self):
        return "<{} {} ({})>".format(self.__class__.__name__,
                                     self._mb, "active" if self.isActive() else "inactive")
