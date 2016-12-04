"""PyPush library mapping to the web server."""
import contextlib
import threading
import datetime
import traceback
import logging
import time

import enum

from sqlalchemy import exists
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func, update

import PyPush.lib as Lib
from PyPush.web import db

from .const import MB_ACTIONS

class PairDb(Lib.iLib.iPairingKeyStorage):
	"""Accessor to the pairing key storage."""

	def __init__(self, mbService):
		self.service = mbService

	def hasKey(self, uid):
		with self._session() as s:
			cnt = self._queryByUid(s, uid).count()
		assert cnt in (0, 1)
		return cnt == 1

	def get(self, uid):
		with self._session() as s:
			return self._queryByUid(s, uid).one().pairKey

	def set(self, uid, key):
		with self._session() as s:
			record = self._queryByUid(s, uid).one_or_none()
			if record:
				record.pairKey = key
			else:
				record = db.PairingKey(uuid=uid, pairKey=key)
				s.add(record)

	def delete(self, uid):
		with self._session() as s:
			rec = self._queryByUid(s, uid).one_or_none()
			if rec:
				s.delete(rec)

	def _queryByUid(self, session, uid):
		return session.query(db.PairingKey).filter_by(uuid=uid)

	@contextlib.contextmanager
	def _session(self):
		with self.service.sessionCtx() as session:
			yield session
			
class ActionWriter(object):

	log = logging.getLogger(__name__)

	def __init__(self, mbService):
		self.service = mbService
		self._wakeup = threading.Event()
		self._writeThread = threading.Thread(target=self._writeActions, name="ActionWriterThread")
		self._writeThread.daemon = True

	def start(self):
		self._writeThread.start()

	def wakeup(self):
		self._wakeup.set()

	def _writeActions(self):
		"""A separate daemon thread that writes back actions scheduled in the db."""
		while True:
			with self.service.sessionCtx() as session:
				self._step(session, self.service.getBleMicrobots())
				nextActionTime = session.query(
					func.min(db.Action.scheduled_at)
				).filter(
					db.Action.prev_action == None
				).scalar()
			
			if nextActionTime is None:
				waitTime = 30
			else:
				waitTime = (nextActionTime - datetime.datetime.utcnow()).seconds
				waitTime = min(max(waitTime, 1), 10)

			self._wakeup.wait(waitTime)
			self._wakeup.clear()

	def _step(self, session, microbots):
		completedActions = []
		chainsToRemove = []
		commandedThisTurn = set()

		delayedBy = lambda secs: datetime.datetime.utcnow() + datetime.timedelta(seconds=max(secs, 1))

		for action in session.query(db.Action).filter(
			db.Action.prev_action == None,
			db.Action.scheduled_at <= datetime.datetime.utcnow()
		).order_by(db.Action.id):
			uuid = action.microbot.uuid
			if uuid in commandedThisTurn:
				# This microbot already received a command this turn. Delay any following commands by a second
				action.scheduled_at = delayedBy(1)
				continue

			commandedThisTurn.add(uuid)
			cmd = action.action
			argsPkg = action.action_args
			if argsPkg:
				assert len(argsPkg) == 2, argsPkg
				(args, kwargs) = argsPkg
			else:
				args = ()
				kwargs = {}
			
			try:
				actionResult = self._callAction(uuid, cmd, args, kwargs)
			except:
				tb = traceback.format_exc()
				self.log.error(tb)
				action.retries_left -= 1
				action.microbot.last_error = tb
				if action.retries_left <= 0:
					chainsToRemove.append(action) # No more retries remain, remove the action & its children.
				continue
			
			action.microbot.last_error = None
			if actionResult is True:
				completedActions.append(action)
			elif isinstance(actionResult, (float, int)) and actionResult >= 0:
				self.log.info("Action {!r} re-scheduled for {} seconds".format(cmd, actionResult))
				action.scheduled_at = delayedBy(actionResult)
			else:
				raise Exception("Unexpected action result {!r}".format(actionResult))

		now = datetime.datetime.utcnow()
		for action in completedActions:
			# update all actions that depended on sucessful completion of this one.
			for child in action.next_actions:
				child.prev_action = None #  the current parent action will be deleted soon
				child.scheduled_at = now + datetime.timedelta(seconds=child.prev_action_delay)
			session.delete(action)

		while chainsToRemove:
			action = chainsToRemove.pop()
			for child in action.next_actions:
				chainsToRemove.append(child)
			session.delete(action)

	def _callAction(self, uuid, cmd, args, kwargs):
		try:
			mb = self.service.getMicrobot(uuid)
		except KeyError:
			self.log.info("Microbot {!r} not found".format(uuid))
			return 30 # Retry in 30 seconds

		if cmd == MB_ACTIONS.pair.key:
			for colour in mb.pair():
				print colour
		elif cmd == MB_ACTIONS.blink.key:
			mb.deviceBlink(30)
		elif cmd == MB_ACTIONS.extend.key:
			mb.extend()
		elif cmd == MB_ACTIONS.retract.key:
			mb.retract()
		elif cmd == MB_ACTIONS.calibrate.key:
			assert len(args) == 1, (args, kwargs)
			mb.setCalibration(args[0])
		else:
			raise Exception([cmd, args, kwargs])

		return True # Success


class MicrobotBluetoothService(object):
	"""Microbot bluetooth service."""

	log = logging.getLogger(__name__)

	def __init__(self, pushApp):
		self.app = pushApp
		self._writer = ActionWriter(self)
		self._pairDb = PairDb(self)
		self._microbots = {} # uid -> microbot
		self._dbIds = {} # uid -> db id

	def start(self, bleDriver, bleDevice):
		"""Start the service."""
		config = {
			"driver": bleDriver,
			"device": bleDevice,
		}
		with self.sessionCtx() as s:
			stmt = update(db.Microbot).values(is_connected=False)
			s.execute(stmt)

		self._hub = Lib.PushHub(config, self._pairDb)
		self._evtHandle = self._hub.onMicrobot(self._onMbFound, self._onMbLost)
		self._writer.start()

	def getMicrobot(self, nameOrId):
		key = nameOrId.lower()
		for mb in self._microbots.itervalues():
			if key in (mb.getUID().lower(), ):
				return mb
		raise KeyError(nameOrId)

	def _onMbFound(self, microbot):
		key = microbot.getUID()
		self._microbots[key] = microbot
		self._updateDbRecord(key)
		microbot.onStateChange(lambda mb: self._onMbStateChange(key, mb))
		if microbot.isPaired():
			microbot.connect()

	def _onMbLost(self, microbot):
		if not microbot.isConnected():
			try:
				self._microbots.pop(microbot.getUID())
			except KeyError:
				pass

	def stop(self):
		"""Stop the service."""

	def _onMbStateChange(self, uid, mb):
		try:
			self._updateDbRecord(uid)
		except:
			# Cycle the connection
			self.log.exception("Microbot state change error")
			mb.disconnect()
			time.sleep(1)
			mb.connect()

	def _updateDbRecord(self, mbUid):
		with self.sessionCtx() as s:
			mb = self._microbots[mbUid]
			rec = s.query(db.Microbot).filter_by(uuid = mbUid).one_or_none()
			if not rec:
				rec = db.Microbot(uuid=mbUid, name=mb.getName())
				s.add(rec)

			is_conn = mb.isConnected()
			rec.is_connected = is_conn
			rec.is_paired = mb.isPaired()			
			rec.last_seen = mb.getLastSeen()

			def mGet(fn):
				"""Retreives value of the function, performs serveral re-attempts on timeout."""
				if not mb.isConnected():
					return None
				try:
					return fn()
				except:
					tb = traceback.format_exc()
					self.log.error(tb)
					rec.last_error = tb

			rec.retracted = mGet(mb.isRetracted)
			rec.battery = mGet(mb.getBatteryLevel)
			rec.calibration = mGet(mb.getCalibration)

			s.commit()

			self._dbIds[mbUid] = rec.id

	def getDbId(self, uid):
		try:
			rv = self._dbIds[uid]
		except KeyError:
			self._reloadDbIds()
			rv = self._dbIds[uid]
		return rv

	_nextReloadOn = 0
	_RELOAD_FREQ = 60 # seconds
	def _reloadDbIds(self):
		if time.time() < self._nextReloadOn:
			return
		with self.sessionCtx() as s:
			for (dbId, uuid) in s.query(db.Microbot.id, db.Microbot.uuid).all():
				self._dbIds[uuid] = dbId
		self._nextReloadOn = time.time() + self._RELOAD_FREQ

	def getBleMicrobots(self):
		return tuple(self._microbots.itervalues())

	def syncToBt(self):
		"""Sync db -> BLE state."""
		self._writer.wakeup()

	@contextlib.contextmanager
	def sessionCtx(self):
		with self.app.flask.app_context():
			session = self.app.db.create_scoped_session({})
			try:
				try:
					yield session
				except:
					session.rollback()
					raise
				else:
					session.commit()
			finally:
				session.close()
