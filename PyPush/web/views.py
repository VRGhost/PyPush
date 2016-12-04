import time
from flask import render_template

from flask_restful import Resource, Api, reqparse

from . import (
	db,
)
from .const import MB_ACTIONS
from .app import PUSH_APP

api = PUSH_APP.restful
app = PUSH_APP.flask

class CUSTOM_MB_ACTIONS(object):
	PRESS = "press"

class ActionChainConstructor(object):
	"""This object helps to construct BLE action chain."""

	def __init__(self, microbotId):
		self._actions = []
		self._mbId = PUSH_APP.ble.getDbId(microbotId)
		assert self._mbId, microbotId

	def clear(self):
		self._actions[:] = []

	def append(self, action, args=(), kwargs=None):
		rec = db.Action(
			microbot_id = self._mbId,
			action = action,
			action_args=(args, kwargs or {}),
		)
		if self._actions:
			rec.prev_action = self._actions[-1]
		self._actions.append(rec)
		return rec

	def commit(self):
		if not self._actions:
			return ()

		s = PUSH_APP.db.session
		s.add_all(self._actions)
		s.commit()
		rv = [rec.id for rec in self._actions]
		PUSH_APP.ble.syncToBt()
		self.clear()

		return rv


class MicrobotList(Resource):

	def post(self, mbId):
		args = parser.parse_args()
		print repr(args)
		print repr(mbId)

	def get(self):
		out = []
		for rec in db.Microbot.query.all():
			actions = []
			
			if not rec.is_paired:
				status = "not_paired"
				actions.append(MB_ACTIONS.pair)
			elif not rec.is_connected:
				status = "not_connected"
			else:
				status = "connected"
				actions.extend([
					MB_ACTIONS.blink,
					MB_ACTIONS.extend,
					MB_ACTIONS.retract,
					MB_ACTIONS.calibrate,
					CUSTOM_MB_ACTIONS.PRESS,
				])

			out.append({
				"id": rec.uuid,
				"name": rec.name,
				"uuid": rec.uuid,
				"status": status,
				"battery": rec.battery,
				"retracted": rec.retracted,
				"calibration": rec.calibration,
				"last_seen": rec.last_seen.isoformat(),
				"error": rec.last_error,
				"actions": [str(el) for el in actions],
			})
		return out

MICROBOT_PARSER = reqparse.RequestParser()
MICROBOT_PARSER.add_argument("name")
MICROBOT_PARSER.add_argument("calibration")

class Microbot(Resource):

	def post(self, mbId):
		args = MICROBOT_PARSER.parse_args()
		newName = args["name"]
		newCalibration = args["calibration"]
		if newCalibration:
			newCalibration = float(newCalibration)

		mb = db.Microbot.query.filter_by(uuid=mbId).one()

		if newName and mb.name != newName:
			mb.name = newName
			PUSH_APP.db.session.commit()

		if mb.calibration != newCalibration:
			# Schedule calibration change
			chain = ActionChainConstructor(mbId)
			chain.append(MB_ACTIONS.retract.key)
			chain.append(
				MB_ACTIONS.calibrate.key, args=(float(newCalibration), )).prev_action_delay = 2
			chain.append(MB_ACTIONS.extend.key).prev_action_delay = 1.5
			chain.commit()

		return {
			"success": True,
		}

class MicrobotAction(Resource):

	def get(self, mbId, action):
		chain = ActionChainConstructor(mbId)
		if action in MB_ACTIONS:
			# A primive microbot action is called upon
			chain.append(action)
		elif action == CUSTOM_MB_ACTIONS.PRESS:
			chain.append(MB_ACTIONS.extend.key)
			chain.append(MB_ACTIONS.retract.key).prev_action_delay = 1.5 # Add delay between extend an retract
		else:
			raise NotImplementedError(action)

		ids = chain.commit()

		return {
			"success": True,
			"action_ids": ids
		}

api.add_resource(MicrobotList, '/api/microbots')
api.add_resource(Microbot, '/api/microbots/<string:mbId>')
api.add_resource(MicrobotAction, '/api/microbots/<string:mbId>/<string:action>')


@app.route("/")
def index():
	return render_template(
		'index.html',
    )

@app.route('/debug')
def open_debug():
   raise Exception("Debugger")