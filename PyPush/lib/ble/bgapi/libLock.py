"""Library lock."""

import threading
import functools
import time
import contextlib

class LibLock(object):

	__slots__ = ("lock", "nextMinTime")

	def __init__(self):
		self.lock = threading.RLock()
		self.nextMinTime = 0

	def setNextCallIn(self, dt):
		assert dt >= 0
		self.nextMinTime = max(self.nextMinTime, time.time() + dt)

	def waitUntilCanCall(self):
		dt = self.nextMinTime - time.time()
		if dt > 0:
			time.sleep(dt)

class LockableBle(object):
	"""This object wraps all calls to the BLE API into threading mutex."""

	def __init__(self, ble, lock):
		self._ble = ble
		self._lock = lock

	def __getattr__(self, name):
		with self._lock.lock:
			_realAttr = getattr(self._ble, name)

		if callable(_realAttr):
			@functools.wraps(_realAttr)
			def _wrapper_(*args, **kwargs):
				with self._lock.lock:
					self._lock.waitUntilCanCall()
					return _realAttr(*args, **kwargs)
			setattr(self, name, _wrapper_)
			rv = _wrapper_
		else:
			rv = _realAttr
		return rv

	@contextlib.contextmanager
	def transaction(self):
		"""Entering this context will lock BLE library exclusively for the current thread."""
		with self._lock.lock:
			yield

	@contextlib.contextmanager
	def delayedUnlock(self, timeout):
		"""Same as transaction, but the `ble` is locked for the `timeout` seconds."""
		with self.transaction():
			yield
			self._lock.setNextCallIn(timeout)

	@classmethod
	def RootLock(cls, obj):
		return cls(obj, LibLock())

	def getChildLock(self, obj):
		return self.__class__(obj, self._lock)