"""Service daemon thread(s)."""
import datetime
import collections
import time
import logging
import threading
import traceback

from sqlalchemy import func, update

from ..const import MB_ACTIONS

from PyPush.web import db

import PyPush.lib as Lib


class ActionWriter(object):
    """Object that relays delayed actions from the database to the microbots."""
    log = logging.getLogger(__name__)

    def __init__(self, service):
        self.service = service


    def step(self, session):
        """Write pending actions from the database."""
        completedActions = []
        chainsToRemove = []
        commandedThisTurn = set()

        delayedBy = lambda secs: datetime.datetime.utcnow(
        ) + datetime.timedelta(seconds=max(secs, 1))

        for action in session.query(db.Action).filter(
                db.Action.prev_action == None,
                db.Action.scheduled_at <= datetime.datetime.utcnow()
        ).order_by(db.Action.id):
            uuid = action.microbot.uuid
            if uuid in commandedThisTurn:
                # This microbot already received a command this turn. Delay any
                # following commands by a second
                action.scheduled_at = delayedBy(1)
                continue

            commandedThisTurn.add(uuid)
            cmd = action.action
            argsPkg = action.action_args
            self.log.info("Executing {}".format([cmd, argsPkg]))
            if argsPkg:
                assert len(argsPkg) == 2, argsPkg
                (args, kwargs) = argsPkg
            else:
                args = ()
                kwargs = {}

            action.microbot.last_error = None
            try:
                actionResult = self._callAction(uuid, cmd, args, kwargs)
            except:
                self.log.exception("Error calling action")
                tb = traceback.format_exc()
                self.log.error(tb)
                action.retries_left -= 1
                action.microbot.last_error = tb
                if action.retries_left <= 0:
                    # No more retries remain, remove the action & its children.
                    chainsToRemove.append(action)
                continue

            self.service.app.microbotActionLog.logOrderCompleted(
                action.microbot, cmd, args, kwargs,
            )

            if actionResult is True:
                completedActions.append(action)
            elif isinstance(actionResult, (float, int)) and actionResult >= 0:
                self.log.info(
                    "Action {!r} re-scheduled for {} seconds".format(cmd, actionResult))
                action.scheduled_at = delayedBy(actionResult)
            else:
                raise Exception(
                    "Unexpected action result {!r}".format(actionResult))

        now = datetime.datetime.utcnow()
        for action in completedActions:
            # update all actions that depended on sucessful completion of this
            # one.
            for child in action.next_actions:
                child.prev_action = None  # the current parent action will be deleted soon
                child.scheduled_at = now + \
                    datetime.timedelta(seconds=child.prev_action_delay)
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
            return 30  # Retry in 30 seconds



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

        return True  # Success

class MicrobotReconnector(object):
    """This object reconnects disconnected microbots."""

    RECONNECT_DELAY = 60 # seconds
    log = logging.getLogger(__name__)

    def __init__(self, service):
        self.service = service
        self.minReconnectTime = collections.defaultdict(lambda: 0) # UID -> min time.time

    def step(self):
        """Reconnect all previously disconnected microbots."""
        for mb in self.service.getBleMicrobots():
            if not mb.isConnected() and mb.isPaired():
                uid = mb.getUID()
                if self.minReconnectTime[uid] < time.time():
                    self.log.info("Connecting to {!r}".format(uid))
                    try:
                        mb.connect()
                    except Lib.exceptions.Timeout:
                        self.log.exception("Timeout while reconnecting")
                    finally:
                        self.minReconnectTime[uid] = time.time() + self.RECONNECT_DELAY

class BLEDaemon(object):

    log = logging.getLogger(__name__)
    running = False

    def __init__(self, mbService):
        self.service = mbService
        self._wakeup = threading.Event()

        self.actionWriter = ActionWriter(self.service)
        self.reconnector = MicrobotReconnector(self.service)

        self._daemon = threading.Thread(
            target=self._run, name="ActionWriterThread")
        self._daemon.daemon = True

    def start(self):
        self.running = True
        self._daemon.start()

    def stop(self):
        self.running = False

    def wakeup(self):
        self._wakeup.set()

    def _run(self):
        """A separate daemon thread that writes back actions scheduled in the db."""
        while self.running:
            with self.service.sessionCtx() as session:
                try:
                    self.reconnector.step()
                except Exception:
                    self.log.exception("Error reconnecting to a microbot.")

                try:
                    self.actionWriter.step(session)
                except Exception:
                    self.log.exception("Write actions exception.")
                    
                nextActionTime = session.query(
                    func.min(db.Action.scheduled_at)
                ).filter(
                    db.Action.prev_action == None
                ).scalar()

            now = datetime.datetime.utcnow()
            if nextActionTime is None:
                waitTime = 30
            elif nextActionTime < now:
                waitTime = 0;
            else:
                waitTime = (nextActionTime - now).seconds
                waitTime = min(max(waitTime, 1), 10)

            self._wakeup.wait(waitTime)
            self._wakeup.clear()