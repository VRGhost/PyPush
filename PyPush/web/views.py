import time

import enum

from flask import render_template, Response
from flask_restful import Resource, Api, reqparse

from PyPush.core import db
from .const import (
    ComplexMbActions,
    MbActions,
)




class ActionChainConstructor(object):
    """This object helps to construct BLE action chain."""

    def __init__(self, flaskUI, microbotId):
        super(ActionChainConstructor, self).__init__()
        self.flaskUI = flaskUI
        self._actions = []
        self._actionLog = flaskUI.core.microbotActionLog
        
        _mbId = flaskUI.core.ble.getDbId(microbotId)
        self._microbot = flaskUI.core.db.session.query(db.Microbot).get(_mbId)

    def clear(self):
        """Clear the action chain."""
        self._actions[:] = []

    def append(self, action, args=(), kwargs=None):
        """Append new action to the end of the action chain."""
        action_args=(args, kwargs or {})
        print action_args

        rec = db.Action(
            microbot_id=self._microbot.id,
            action=action.value,
            action_args=(args, kwargs or {}),
            retries_left=5 * 3, # the microbot will be disconnected every 5 retries.
        )
        if self._actions:
            rec.prev_action = self._actions[-1]
        self._actions.append(rec)
        self._actionLog.logOrderReceived(
            self._microbot,
            action,
            action_args[0], action_args[1],
        )
        return rec

    def commit(self):
        """Commit the constructed action log to the database."""

        if not self._actions:
            return ()

        core = self.flaskUI.core
        with core.db_lock:
            s = core.db.session
            s.add_all(self._actions)
            s.commit()
        rv = [rec.id for rec in self._actions]
        core.ble.syncToBt()
        self.clear()

        return rv


class MicrobotList(Resource):

    def __init__(self, flaskUI):
        super(MicrobotList, self).__init__()
        self.flaskUI = flaskUI

    def get(self):
        out = []
        for rec in db.Microbot.query.all():
            actions = []

            if not rec.is_paired:
                status = "not_paired"
                actions.append(MbActions.pair)
            elif not rec.is_connected:
                status = "not_connected"
            else:
                status = "connected"
                actions.extend([
                    MbActions.blink,
                    MbActions.extend,
                    MbActions.retract,
                    MbActions.calibrate,
                    MbActions.change_button_mode,
                    ComplexMbActions.press,
                ])

            sFirmwareVersion = None
            if rec.firmware_version is not None:
                sFirmwareVersion = ".".join(str(el)
                    for el in rec.firmware_version)

            bMode = None
            if rec.button_mode is not None:
                bMode = rec.button_mode.name

            out.append({
                "id": rec.uuid,
                "name": rec.name,
                "uuid": rec.uuid,
                "status": status,
                "battery": rec.battery,
                "retracted": rec.retracted,
                "calibration": rec.calibration,
                "firmware_version": sFirmwareVersion,
                "button_mode": bMode,
                "last_seen": rec.last_seen.isoformat(),
                "error": rec.last_error,
                "actions": [el.value for el in actions],
            })
        return out

MICROBOT_PARSER = reqparse.RequestParser()
MICROBOT_PARSER.add_argument("name")
MICROBOT_PARSER.add_argument("calibration")


class Microbot(Resource):

    def __init__(self, flaskUI):
        super(Microbot, self).__init__()
        self.flaskUI = flaskUI

    def post(self, mbId):
        args = MICROBOT_PARSER.parse_args()
        newName = args["name"]
        newCalibration = args["calibration"]
        if newCalibration:
            newCalibration = float(newCalibration)

        mb = db.Microbot.query.filter_by(uuid=mbId).one()

        if newName and mb.name != newName:
            mb.name = newName
            self.flaskUI.core.db.session.commit()

        if mb.calibration != newCalibration:
            # Schedule calibration change
            chain = ActionChainConstructor(self.flaskUI, mbId)
            chain.append(WebMicrobotActions.retract.key)
            chain.append(
                WebMicrobotActions.calibrate.key, args=(float(newCalibration), )).prev_action_delay = 2
            chain.append(WebMicrobotActions.extend.key).prev_action_delay = 1.5
            chain.commit()

        return {
            "success": True,
        }

ActionArgParser = reqparse.RequestParser()
ActionArgParser.add_argument("args", action="append")
ActionArgParser.add_argument("kwargs", action="append")

class MicrobotAction(Resource):

    def __init__(self, flaskUI):
        super(MicrobotAction, self).__init__()
        self.flaskUI = flaskUI

    def get(self, mbId, action):
        chain = ActionChainConstructor(self.flaskUI, mbId)
        reqArgs = ActionArgParser.parse_args()
        if reqArgs.args:
            args = tuple(reqArgs.args)
        else:
            args = ()

        if reqArgs.kwargs:
            kwargs = dict(reqArgs.kwargs)
        else:
            kwargs = {}

        metaAction = None
        try:
            metaAction = ComplexMbActions(action)
        except ValueError:
            pass

        if metaAction is None:
            try:
                action = MbActions(action)
            except ValueError:
                raise NotImplementedError(action)
            else:
                chain.append(action, args, kwargs)
        else:
            # not none
            if metaAction == ComplexMbActions.press:
                actions = [MbActions.extend, MbActions.retract]
            else:
                raise NotImplementedError(metaAction)

            for action in actions:
                chAction = chain.append(action, args, kwargs)
                # Add delay between action chain elements
                chAction.prev_action_delay = 1.5

        ids = chain.commit()

        return {
            "success": True,
            "action_ids": ids
        }


class FlaskRoutes(object):

    def __init__(self, flaskUI):
        self.flaskUI = flaskUI

    def get_action_log(self):
        return Response(
            self.flaskUI.core.microbotActionLog.readAll(),
            mimetype='text/csv',
        )

    def index(self):
        return render_template(
            'index.html',
        )

def create_views(flaskUI):
    """Assign Web views to the flask app."""
    restful = flaskUI.restful
    flask = flaskUI.flask

    kw = {"flaskUI": flaskUI}

    routes = FlaskRoutes(flaskUI)
    flask.route("/")(routes.index)
    flask.route("/info/action_log.csv")(routes.get_action_log)


    restful.add_resource(MicrobotList, '/api/microbots', resource_class_kwargs=kw)
    restful.add_resource(Microbot, '/api/microbots/<string:mbId>', resource_class_kwargs=kw)
    restful.add_resource(
        MicrobotAction,
        '/api/microbots/<string:mbId>/<string:action>',
        resource_class_kwargs=kw,
    )