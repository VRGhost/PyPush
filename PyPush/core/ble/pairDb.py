"""Pairing data database."""

import PyPush.lib as Lib
from PyPush.core import db

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

    def _session(self):
        return self.service.sessionCtx()