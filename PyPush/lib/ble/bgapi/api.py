"""Top-level API object."""
import time
import threading
import logging
import contextlib
import functools
from bgapi.module import BlueGigaClient

from .. import iApi
from . import (
	scanner,
	mbRegistry,
	connection,
)


class LockableBle(object):
	"""This object wraps all calls to the BLE API into threading mutex."""

	def __init__(self, ble, mutex):
		self._ble = ble
		self._mutex = mutex
		self._nextCallMinTime = 0

	def __getattr__(self, name):
		with self._mutex:
			_realAttr = getattr(self._ble, name)

		if callable(_realAttr):
			@functools.wraps(_realAttr)
			def _wrapper_(*args, **kwargs):
				with self._mutex:
					
					# Delay call if previous unlock is still effective.
					dt = self._nextCallMinTime - time.time()
					if dt > 0:
						time.sleep(dt)

					return _realAttr(*args, **kwargs)
			setattr(self, name, _wrapper_)
			rv = _wrapper_
		else:
			rv = _realAttr
		return rv

	@contextlib.contextmanager
	def transaction(self):
		"""Entering this context will lock BLE library exclusively for the current thread."""
		with self._mutex:
			yield

	@contextlib.contextmanager
	def delayedUnlock(self, timeout):
		"""Same as transaction, but the `ble` is locked for the `timeout` seconds."""
		with self.transaction():
			yield
			self._nextCallMinTime = time.time() + timeout

	@classmethod
	def RootLock(cls, obj):
		mutex = threading.RLock()
		return cls(obj, mutex)

	def getChildLock(self, obj):
		return self.__class__(obj, self._mutex)

class API(iApi.iApi):
	"""BlueGiga API."""

	def __init__(self, config):
		"""Config must be a dict with "port" key (specifying tty of the bluegiga token)"""
		self._mbDb = mbRegistry.MicrobotRegistry(maxAge=3600)
		_ble = BlueGigaClient(
			port=config["port"],
			baud=config.get("baud", 115200),
			timeout=config.get("timeout", 0.1)
		)
		_ble.CONNECTION_OBJECT
		self._ble = LockableBle.RootLock(_ble)
		self._ble.reset_ble_state()
		self._scanner = scanner.Scanner(self._ble, self._mbDb)

	def scan(self, maxAge=0):
		return self._mbDb.getBots(maxAge)

	def connect(self, microbot):
		conn = connection.BgConnection(microbot, self._ble)
		conn._open()
		print conn
		return conn