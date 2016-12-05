import datetime

from sqlalchemy import (
    ForeignKey
)

from sqlalchemy.orm import (
    relationship,
    backref,
)

from flask_sqlalchemy import SQLAlchemy

from . import const

db = SQLAlchemy()
OLD_TIME = datetime.datetime.fromtimestamp(0)


class PairingKey(db.Model):
    __tablename__ = "pairing_keys"

    id = db.Column(db.Integer, primary_key=True)
    # UUID is a 128-bit (16-byte) value
    uuid = db.Column(db.String(16), unique=True, nullable=False)
    pairKey = db.Column(db.PickleType(), nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.datetime.utcnow,
        nullable=False)


class Microbot(db.Model):
    __tablename__ = "microbots"

    id = db.Column(db.Integer, primary_key=True)
    # UUID is a 128-bit (16-byte) value
    uuid = db.Column(db.String(16), unique=True, nullable=False)
    name = db.Column(db.String(255), unique=True, nullable=False)

    is_paired = db.Column(db.Boolean(), nullable=False)
    is_connected = db.Column(db.Boolean(), nullable=False)

    retracted = db.Column(db.Boolean(), nullable=True)
    battery = db.Column(db.Float(), nullable=True)
    calibration = db.Column(db.Float(), nullable=True)

    last_error = db.Column(db.Text(), nullable=True)
    last_seen = db.Column(db.DateTime, nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.datetime.utcnow,
        nullable=False)

    actions = relationship("Action")


class Action(db.Model):
    __tablename__ = "actions"

    id = db.Column(db.Integer, primary_key=True)
    microbot_id = db.Column(
        db.Integer,
        ForeignKey("microbots.id"),
        nullable=False)
    microbot = relationship(
        "Microbot",
        back_populates="actions",
        uselist=False)

    prev_action_id = db.Column(
        db.Integer,
        ForeignKey("actions.id"),
        nullable=True)

    next_actions = relationship(
        'Action', backref=backref(
            'prev_action', remote_side=[id]))

    prev_action_delay = db.Column(db.Float, nullable=False, default=0.0)

    # Number of times this command will be retried if call raises an exception
    retries_left = db.Column(db.Integer, nullable=False, default=5)
    scheduled_at = db.Column(db.DateTime, default=OLD_TIME, nullable=False)

    action = db.Column(db.Enum(*[str(el) for el in const.MB_ACTIONS]))
    action_args = db.Column(
        db.PickleType(),
        default=(),
        nullable=False)  # (<args>, <kwargs>)

    created_at = db.Column(
        db.DateTime,
        default=datetime.datetime.utcnow,
        nullable=False)
