import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from analyze import edges, logs, traffic


class AnalysisTests(unittest.TestCase):
    def test_scope_edge_pairing_detects_missing_edge(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "edges.csv"
            p.write_text(
                "signal,time_s\n"
                + "".join(f"FL,{i}\nRL,{i+.0004}\n" for i in range(10))
            )
            self.assertTrue(edges(p)["FL_RL"]["ten_edge_1ms_check"])
            p.write_text(p.read_text() + "FL,10\n")
            self.assertFalse(edges(p)["FL_RL"]["ten_edge_1ms_check"])

    def test_log_comparison_refuses_empty_and_detects_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a", Path(d) / "b"
            a.write_text("COMMIT index=1 term=1 event=EVENT_N2 replayed=0\n")
            b.write_text("COMMIT index=1 term=1 event=EVENT_N3 replayed=0\n")
            self.assertFalse(logs([a, b])["common_prefix_agrees"])
            b.write_text("")
            with self.assertRaises(ValueError):
                logs([a, b])

    def test_bus_periods_keep_separate_interfaces(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "can.log"
            p.write_text(
                "(1.000) can0 081#0001000000000000\n(1.001) can1 081#0001000000000000\n(1.020) can0 081#0101000000000000\n"
            )
            r = traffic(p)
            self.assertAlmostEqual(r["ref_streams"]["can0:N1"]["mean_interval_ms"], 20)
