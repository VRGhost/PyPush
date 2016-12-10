"""An opbject to record microbot push order receipts & executions."""

import datetime
import csv
import json
import shutil
import os
import threading

class MicrobotActionLog(object):

    def __init__(self, fname, maxSize=1024, backupCount=5):
        self.fname = fname
        self.maxSize = maxSize # records
        self.backupCount = backupCount
        self.mutex = threading.RLock()      
        self.rotateFiles()
        

    def logOrderReceived(self, microbot, action, args, kwargs):
        """Logs receipt of the order for the <db.Microbot>."""
        with self.mutex:
            writer = self._getWriter()
            writer.writerow([
                datetime.datetime.utcnow().isoformat(),
                microbot.uuid, microbot.name,
                "received",
                action, json.dumps(args), json.dumps(kwargs)
            ])
            self._curSize += 1

    def logOrderCompleted(self, microbot, action, args, kwargs):
        """Logs order executed for the <db.Microbot>"""
        with self.mutex:
            writer = self._getWriter()
            writer.writerow([
                datetime.datetime.utcnow().isoformat(),
                microbot.uuid, microbot.name, 
                "executed",
                action, json.dumps(args), json.dumps(kwargs)
            ])
            self._curSize += 1

    def readAll(self):
        """Return all log records from all log files."""
        with self.mutex:
            if self._curOut:
                self._curOut.flush()

            for fname in self.allFileNames():
                if os.path.exists(fname):
                    with open(fname, "rb") as fobj:
                        yield fobj.read()

    _curOut = _csvWriter = None
    _curSize = 0
    def _getWriter(self):
        with self.mutex:
            if self._curOut and self._curSize > self.maxSize:
                self._curOut.close()
                self._curOut = None
                self.rotateFiles()

            if self._curOut is None:
                self._curOut = open(self.fname, "wb")
                self._curSize = 0
                self._csvWriter = csv.writer(self._curOut)
                self._csvWriter.writerow([
                    "Timestamp",
                    "UUID", "Name",
                    "type", "action",
                    "args", "kwargs",
                ])

        return self._csvWriter

    def rotateFiles(self):
        """Age all files by one generation.

        This has side effect of releaseing first file name.
        """
        with self.mutex:
            print tuple(self.allFileNames())
            allFnames = list(self.allFileNames())
            allFnames.reverse()
            for (fname, older) in zip(allFnames[1:], allFnames):
                if os.path.exists(fname):
                    os.rename(fname, older)

    def allFileNames(self):
        """Iterate over all log file names managed by this action log."""
        yield self.fname
        (name, ext) = os.path.splitext(self.fname)
        for idx in xrange(1, self.backupCount+1):
            yield "{}_{}{}".format(name, idx, ext)