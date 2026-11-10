import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from export_ledger import export, snapshot
from analyze import logs


class ExportLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "display.sqlite"
        self.db = sqlite3.connect(self.path)
        self.addCleanup(self.db.close)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            "CREATE TABLE events(idx INTEGER PRIMARY KEY,term INTEGER,event INTEGER,row TEXT)"
        )
        self.db.commit()

    def insert(self, index, event=22, row=None):
        row = row or {"index": index, "term": 1, "event": event, "replayed": False}
        self.db.execute(
            "INSERT INTO events VALUES (?,?,?,?)", (index, 1, event, json.dumps(row))
        )
        self.db.commit()

    def test_live_wal_export_order_and_comparison(self):
        self.insert(2)
        self.insert(1)
        before = self.db.execute("SELECT * FROM events").fetchall()
        out = Path(self.temp.name) / "pi.jsonl"
        self.assertEqual(export(self.path, out), 2)
        self.assertEqual(self.db.execute("SELECT * FROM events").fetchall(), before)
        n2 = Path(self.temp.name) / "n2.txt"
        n2.write_text(
            "LOG index=1 term=1 event=EVENT_N2\nLOG index=2 term=1 event=EVENT_N2\n"
        )
        self.assertTrue(logs([out, n2])["identical_complete_logs"])
        with self.assertRaises(FileExistsError):
            export(self.path, out)
        with self.assertRaises(ValueError):
            export(self.path, self.path)

    def test_missing_empty_and_conflicting_ledger_are_rejected(self):
        with self.assertRaises(FileNotFoundError):
            snapshot(self.path.parent / "missing.sqlite")
        with self.assertRaises(ValueError):
            snapshot(self.path)
        self.insert(1, row={"index": 1, "term": 2, "event": 22})
        with self.assertRaises(ValueError):
            snapshot(self.path)

    def test_snapshot_excludes_uncommitted_transaction(self):
        self.insert(1)
        self.db.execute(
            "INSERT INTO events VALUES (2,1,22,?)",
            (json.dumps({"index": 2, "term": 1, "event": 22}),),
        )
        self.assertEqual([r["index"] for r in snapshot(self.path)], [1])
        self.db.rollback()
