"""Sunscribe/callback architecture."""
from abc import ABCMeta, abstractmethod, abstractproperty

import logging
from threading import RLock


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


class MultiHandle(iHandle):
    """A `handle` object that relays any API call to a number of other `handle` objects."""

    def __init__(self, children):
        self._children = tuple(children)

    def cancel(self):
        for ch in self._children:
            ch.cancel()


class SubscribeHub(object):
    """A hub object that can register/unregister callbacks."""

    HANDLE_CLS = SubscriptionHandle
    log = logging.getLogger(__name__)

    _callbacks = ()
    _mutex = None

    def __init__(self):
        self._callbacks = []
        self._mutex = RLock()

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
            except:
                self.log.exception("Callback exception")

    def getSubscriberCount(self):
        return len(self._callbacks)

    def _unsubscribe(self, handle):
        with self._mutex:
            self._callbacks.remove(handle)
        self.onUnsubscribe(handle)
