import tempfile
import unittest
from pathlib import Path
import sys

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
