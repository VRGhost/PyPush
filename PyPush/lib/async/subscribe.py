"""Sunscribe/callback architecture."""
from abc import ABCMeta, abstractmethod, abstractproperty

import logging
import threading
import Queue


class iHandle(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def cancel(self):
        """Cancel the subscription."""


class SubscriptionHandle(iHandle):
    """A handle that allows to manage callback subscription."""

    def __init__(self, hub, cb):
        self._hub = hub
        self.callback = cb

    def cancel(self):
        """Cancel the subscription."""
        self._hub._unsubscribe(self)

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.callback)


class MultiHandle(iHandle):
    """A `handle` object that relays any API call to a number of other `handle` objects."""

    def __init__(self, children):
        self._children = tuple(children)

    def cancel(self):
        for ch in self._children:
            ch.cancel()

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self._children)

class SubscribeHub(object):
    """A hub object that can register/unregister callbacks."""

    HANDLE_CLS = SubscriptionHandle
    log = logging.getLogger(__name__)

    _callbacks = ()
    _mutex = None

    def __init__(self):
        self._callbacks = []
        self._mutex = threading.RLock()

    def subscribe(self, callback):
        assert callable(callback), callback
        handle = self.HANDLE_CLS(self, callback)
        with self._mutex:
            self._callbacks.append(handle)
        self.onSubscribe(handle)
        return handle

    def onSubscribe(self, handle):
        """Method called on each new subscription added to the hub."""

    def onUnsubscribe(self, handle):
        """Method called on subscription cancelled."""

    def fireSubscribers(self, *args, **kwargs):
        """Call all subscribed functions."""
        for handle in tuple(self._callbacks):
            try:
                handle.callback(*args, **kwargs)
            except Exception:
                self.log.exception("Callback exception")
                raise

    def getSubscriberCount(self):
        return len(self._callbacks)

    def _unsubscribe(self, handle):
        with self._mutex:
            try:
                self._callbacks.remove(handle)
            except ValueError:
                # No longer in the list
                pass

        self.onUnsubscribe(handle)

class SubscribeHubDict(object):
    """A dict-like object that manages multiple subscriber hubs at once."""

    def __init__(self):
        self.mutex = threading.RLock()
        self.subscriberHubs = {}

    def __getitem__(self, key):
        """Return SubscriberHub."""
        with self.mutex:
            try:
                return self.subscriberHubs[key]
            except KeyError:
                rv = self._makeSubscriberHub(key)
                self.subscriberHubs[key] = rv
                return rv

    def _makeSubscriberHub(self, key):
        return SubscribeHub()