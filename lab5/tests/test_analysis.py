import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from analyze import edges, logs, traffic
from can_capture import crc


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

            def frame(t, bus, cycle):
                data = bytes([cycle, 1, 0, 0, 0, 0, 0])
                return f"({t}) {bus} 081#{(data + bytes([crc(data)])).hex()}\n"

            p.write_text(
                frame("1.000", "can0", 0)
                + frame("1.001", "can1", 0)
                + frame("1.020", "can0", 1)
            )
            r = traffic(p)
            self.assertAlmostEqual(r["ref_streams"]["can0:N1"]["mean_interval_ms"], 20)

    def test_missing_history_is_not_reported_as_a_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a", Path(d) / "b"
            line = "COMMIT index={} term=1 event=EVENT_N2 replayed=0\n"
            a.write_text(line.format(1) + line.format(2))
            b.write_text(line.format(2))
            result = logs([a, b])
            self.assertEqual(result["missing_indices"], [[], [1]])
            self.assertEqual(result["conflicts"], [])
            self.assertFalse(result["common_prefix_agrees"])
            with self.assertRaises(ValueError):
                logs([a])

    def test_malformed_commit_is_not_silently_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a", Path(d) / "b"
            good = "COMMIT index=1 term=1 event=EVENT_N2\n"
            a.write_text(good)
            for bad in (
                '{"index":2,"term":1,"event":-1}',
                '{"index":2,"term":1,"event":24}',
                '{"index":2,"term":0,"event":1}',
                '{"index":2,"term":1,"event":true}',
                "COMMIT index=2 term=1 event=NOT_AN_EVENT",
                "COMMIT index=-1 term=1 event=EVENT_N2",
                'COMMIT {"index":2}',
            ):
                with self.subTest(row=bad):
                    b.write_text(good + bad)
                    with self.assertRaises(ValueError):
                        logs([a, b])
