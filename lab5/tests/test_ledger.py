import tempfile
import unittest
from pathlib import Path
import sys
import sqlite3
from contextlib import closing

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pi"))
from ledger import Ledger


class LedgerTests(unittest.TestCase):
    def test_restart_replay_is_index_idempotent_and_ordered(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "display.sqlite"
            shown = []
            log = Ledger(path, shown.append)
            self.assertEqual(log.durable_index, 0)
            for i in range(1, 4):
                log.submit(dict(index=i, term=1, event=22, replayed=False))
            log.close()
            self.assertEqual(log.durable_index, 3)
            log = Ledger(path, shown.append)
            self.assertEqual(log.durable_index, 3)
            for i in range(1, 7):
                log.submit(dict(index=i, term=1, event=22, replayed=i <= 5))
            log.close()
            self.assertEqual(log.durable_index, 6)
            self.assertEqual([r["index"] for r in shown], list(range(1, 7)))
            self.assertEqual([r["index"] for r in log.rows()], list(range(1, 7)))
            self.assertEqual([r["replayed"] for r in shown[3:]], [True, True, False])

    def test_conflicting_commit_is_reported_not_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            log = Ledger(Path(d) / "events.db")
            log.submit(dict(index=1, term=1, event=22))
            log.submit(dict(index=1, term=2, event=23))
            with self.assertRaises(RuntimeError):
                log.close()
            self.assertEqual(log.rows()[0]["term"], 1)

    def test_existing_gap_is_not_reported_durable_and_replay_repairs_it(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "events.db"
            log = Ledger(path)
            for i in range(1, 4):
                log.submit(dict(index=i, term=1, event=22, replayed=False))
            log.close()
            # Reproduce a saved journal with an older missing notification.
            with closing(sqlite3.connect(path)) as db:
                db.execute("DELETE FROM events WHERE idx=2")
                db.commit()
            shown = []
            log = Ledger(path, shown.append)
            self.assertEqual(log.durable_index, 1)
            for i in range(1, 4):
                log.submit(dict(index=i, term=1, event=22, replayed=True))
            log.close()
            self.assertEqual(log.durable_index, 3)
            self.assertEqual([r["index"] for r in log.rows()], [1, 2, 3])
            self.assertEqual([r["index"] for r in shown], [2])
            self.assertTrue(shown[0]["replayed"])

    def test_new_gap_does_not_advance_durable_prefix_past_missing_row(self):
        with tempfile.TemporaryDirectory() as d:
            log = Ledger(Path(d) / "events.db")
            for i in (1, 3):
                log.submit(dict(index=i, term=1, event=22))
            log.close()
            self.assertEqual(log.durable_index, 1)
