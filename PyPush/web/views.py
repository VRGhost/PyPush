import time
from flask import render_template

from flask_restful import Resource, Api

from . import (
	db,
)
from .const import MB_ACTIONS
from .app import PUSH_APP

api = PUSH_APP.restful
app = PUSH_APP.flask

class CUSTOM_MB_ACTIONS(object):
	PRESS = "press"

class Microbot(Resource):

	def get(self):
		out = []
		for rec in db.Microbot.query.all():
			actions = []
			
			if not rec.is_paired:
				status = "Not Paired"
				actions.append(MB_ACTIONS.pair)
			elif not rec.is_connected:
				status = "Not Connected"
			else:
				status = "Connected"
				actions.extend([
					MB_ACTIONS.blink,
					MB_ACTIONS.extend,
					MB_ACTIONS.retract,
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

class MicrobotAction(Resource):

	def get(self, mbId, action):
		ble = PUSH_APP.ble
		db_id = ble.getDbId(mbId)

		recs = []
		def newRec(action, args=(), kwargs=None):
			rec = db.Action(
				microbot_id=db_id,
				action=action,
				action_args=(args, kwargs or {}),
			)
			if recs:
				rec.prev_action = recs[-1]
			recs.append(rec)

		if action in MB_ACTIONS:
			# A primive microbot action is called upon
			newRec(action)
		elif action == CUSTOM_MB_ACTIONS.PRESS:
			newRec(MB_ACTIONS.extend.key)
			newRec(MB_ACTIONS.retract.key)
			recs[-1].prev_action_delay = 1.5 # Add delay between extend an retract
		else:
			raise NotImplementedError(action)

		ids = []
		if recs:
			s = PUSH_APP.db.session
			s.add_all(recs)
			s.commit()
			ble.syncToBt()
			ids = [rec.id for rec in recs]

		return {
			"success": True,
			"action_ids": ids
		}

api.add_resource(Microbot, '/api/microbot/')
api.add_resource(MicrobotAction, '/api/microbot/<string:mbId>/<string:action>')


@app.route("/")
def index():
	return render_template(
		'index.html',
    )