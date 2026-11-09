"""Persistent, index-keyed display history; disk and printing stay off the CAN loop."""

import json
from pathlib import Path
import queue
import sqlite3
import threading
from contextlib import closing


class Ledger:
    def __init__(self, path, emit=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.emit = emit or (lambda row: None)
        self.queue = queue.Queue(maxsize=4096)
        self.error = None
        self.dropped = 0
        # Schema creation is before live control starts.
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                "CREATE TABLE IF NOT EXISTS events (idx INTEGER PRIMARY KEY, term INTEGER NOT NULL, event INTEGER NOT NULL, row TEXT NOT NULL)"
            )
            db.commit()
        self.thread = threading.Thread(
            target=self._run, name="lab5-ledger", daemon=True
        )
        self.thread.start()

    def submit(self, row):
        if self.error:
            return False
        try:
            self.queue.put_nowait(dict(row))
            return True
        except queue.Full:
            self.dropped += 1
            return False

    def _run(self):
        try:
            with closing(sqlite3.connect(self.path)) as db:
                db.execute("PRAGMA synchronous=FULL")
                while (row := self.queue.get()) is not None:
                    old = db.execute(
                        "SELECT term,event FROM events WHERE idx=?", (row["index"],)
                    ).fetchone()
                    if old is not None:
                        if old != (row["term"], row["event"]):
                            raise RuntimeError(
                                "Conflicting committed index; preserve both state files for diagnosis"
                            )
                        continue
                    db.execute(
                        "INSERT INTO events VALUES (?,?,?,?)",
                        (row["index"], row["term"], row["event"], json.dumps(row)),
                    )
                    db.commit()
                    self.emit(row)
        except Exception as exc:
            self.error = str(exc)

    def close(self):
        if self.thread.is_alive():
            self.queue.put(None)
            self.thread.join(timeout=10)
        if self.thread.is_alive():
            raise RuntimeError("Display journal did not finish; preserve its files")
        if self.error:
            raise RuntimeError(self.error)

    def rows(self):
        with closing(sqlite3.connect(self.path)) as db:
            return [
                json.loads(x[0])
                for x in db.execute("SELECT row FROM events ORDER BY idx")
            ]


class Console:
    def __init__(self):
        self.queue = queue.Queue(maxsize=4096)
        self.dropped = 0
        self.thread = threading.Thread(
            target=self._run, name="lab5-console", daemon=True
        )
        self.thread.start()

    def write(self, text):
        try:
            self.queue.put_nowait(text)
        except queue.Full:
            self.dropped += 1

    def _run(self):
        while (text := self.queue.get()) is not None:
            print(text, flush=True)

    def close(self):
        self.queue.put(None)
        self.thread.join(timeout=5)
