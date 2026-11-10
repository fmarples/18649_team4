"""Synthetic fixtures exercise the decoder; they are not vehicle measurements."""

import csv
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from test_core import Node, rpc
from test_network import Network
from can_capture import analyze_capture, crc


def line(at, bus, ident, data):
    return f"({at / 1000000:.6f}) {bus} {ident:03X}#{data.hex()}\n"


def ref(cycle, term=1):
    body = (
        bytes([cycle])
        + term.to_bytes(2, "little")
        + (cycle * 20000).to_bytes(4, "little")
    )
    return body + bytes([crc(body)])


def repack(data, position, value):
    body = bytearray(data[:7])
    body[position] = value
    return bytes(body) + bytes([crc(body)])


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "can.log"
        self.node = Node(1)
        self.addCleanup(self.node.close)

    def analyze(self, text, output=None):
        self.path.write_text(text, encoding="utf-8")
        return analyze_capture(self.path, output)

    def packets(self, frames, at=0, bus="can0"):
        return "".join(
            line(at + i * 240, bus, ident, data)
            for i, (ident, data) in enumerate(frames)
        )

    def test_production_fragments_decode_append_vote_and_csv(self):
        text = ""
        for at, message in (
            (0, rpc(3, 1, 2, 1)),
            (100000, rpc(3, 1, 2, 1)),
            (120000, rpc(3, 1, 2, 1, index=4, entry_term=1, event=22, flags=1)),
            (140000, rpc(1, 1, 0, 2)),
        ):
            text += self.packets(self.node.fragment(message), at)
        output = Path(self.temp.name) / "decoded.csv"
        result = self.analyze(text, output)
        self.assertEqual(result["rpc_types"], {"can0:APPEND": 3, "can0:REQ_VOTE": 1})
        self.assertEqual(result["vote_requests_observed"], 1)
        self.assertEqual(
            result["empty_append_streams"]["can0:N1->N2:term1"]["mean_interval_ms"], 100
        )
        with output.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(rows[2]["index"], "4")
        self.assertEqual(rows[2]["empty_append"], "False")
        self.assertEqual(rows[2]["event"], "22")
        self.assertEqual(rows[0]["first_fragment_s"], "0.000000")

    def test_interfaces_never_complete_each_others_message(self):
        frames = self.node.fragment(rpc(3, 1, 2, 1))
        result = self.analyze(
            self.packets(frames[:2]) + self.packets(frames[2:], 500, "can1")
        )
        self.assertEqual(result["rpc_types"], {})
        self.assertEqual(result["quality"]["incomplete_rpc_sequences"], 2)

    def test_reordered_duplicates_and_sequence_wrap(self):
        frames = self.node.fragment(rpc(3, 1, 2, 1))
        text = ""
        for at, seq in ((0, 255), (100000, 0)):
            packet = [(ident, repack(data, 0, seq)) for ident, data in frames]
            packet = [packet[i] for i in (3, 0, 0, 2, 1, 1)]
            text += self.packets(packet, at)
        result = self.analyze(text)
        self.assertEqual(result["rpc_types"]["can0:APPEND"], 2)
        self.assertEqual(result["quality"]["duplicate_or_stale_fragments"], 4)

    def test_crc_identity_conflicts_and_timeout_do_not_decode(self):
        frames = self.node.fragment(rpc(3, 1, 2, 1))
        bad_crc = [(ident, data[:-1] + bytes([data[-1] ^ 1])) for ident, data in frames]
        result = self.analyze(self.packets(bad_crc))
        self.assertEqual(result["quality"]["bad_frame_crc"], 4)
        invalid_whole = list(frames)
        ident, data = invalid_whole[3]
        invalid_whole[3] = ident, repack(data, 6, data[6] ^ 1)
        result = self.analyze(self.packets(invalid_whole))
        self.assertEqual(result["quality"]["invalid_rpc"], 1)
        mismatch = [(ident + 0x10, data) for ident, data in frames]
        result = self.analyze(self.packets(mismatch))
        self.assertEqual(result["quality"]["invalid_rpc"], 1)
        ident, data = frames[0]
        conflicting = [frames[0], (ident, repack(data, 1, data[1] ^ 1))] + frames[1:]
        result = self.analyze(self.packets(conflicting))
        self.assertEqual(result["quality"]["conflicting_fragments"], 1)
        self.assertEqual(result["rpc_types"], {})
        result = self.analyze(
            self.packets(frames[:2]) + self.packets(frames[2:], 251000)
        )
        self.assertEqual(result["quality"]["incomplete_rpc_sequences"], 2)
        self.assertEqual(result["rpc_types"], {})

    def test_ref_wrap_missing_duplicate_and_term_cadence(self):
        text = "".join(
            line(at, "can0", 0x81, ref(cycle, term))
            for at, cycle, term in (
                (0, 255, 1),
                (20000, 0, 1),
                (21000, 0, 1),
                (60000, 2, 1),
                (80000, 0, 2),
                (100000, 1, 2),
            )
        )
        result = self.analyze(text)["ref_streams"]["can0:N1"]
        self.assertEqual(result["missing_cycles_within_250ms"], 1)
        self.assertEqual(result["duplicate_cycles"], 1)
        self.assertIsNone(result["mean_interval_ms"])
        self.assertEqual(result["by_term"]["1"]["max_interval_ms"], 40)
        self.assertEqual(result["by_term"]["2"]["mean_interval_ms"], 20)

    def test_empty_backwards_unsupported_and_overwrite(self):
        with self.assertRaises(ValueError):
            self.analyze("")
        with self.assertRaises(ValueError):
            self.analyze(
                line(20000, "can0", 0x81, ref(1)) + line(10000, "can0", 0x81, ref(0))
            )
        result = self.analyze(
            "unreadable\n(0.0) can0 00000081#0001000000000000\n"
            + line(20000, "can0", 0x81, ref(1))
        )
        self.assertEqual(result["quality"]["unsupported_frames"], 1)
        self.assertEqual(result["quality"]["unparsed_lines"], 1)
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            analyze_capture(self.path, self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_generated_network_capture_healthy_then_bridged(self):
        net = Network()
        try:
            net.run(600)
            net.frames.clear()
            net.run(600)
            result = self.analyze(
                "".join(
                    line(t, f"can{bus}", ident, data)
                    for t, _, bus, ident, data in net.frames
                )
            )
            self.assertEqual(result["vote_requests_observed"], 0)
            self.assertEqual(result["quality"].get("bad_frame_crc", 0), 0)
            self.assertEqual(len(result["empty_append_streams"]), 4)
            for stream in result["empty_append_streams"].values():
                self.assertEqual(stream["mean_interval_ms"], 100)
            for stream in result["ref_streams"].values():
                self.assertEqual(stream["mean_interval_ms"], 20)
            net.links -= {(1, 1), (3, 0)}
            net.run(600)
            net.frames.clear()
            net.nodes[2].event()
            net.run(500)
            output = Path(self.temp.name) / "bridged.csv"
            result = self.analyze(
                "".join(
                    line(t, f"can{bus}", ident, data)
                    for t, _, bus, ident, data in net.frames
                ),
                output,
            )
            self.assertEqual(result["vote_requests_observed"], 0)
            with output.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            # N1's EVENT_N2 append is actually visible on the remote B bus.
            self.assertTrue(
                any(
                    r["interface"] == "can1"
                    and r["kind"] == "APPEND"
                    and r["source"] == "1"
                    and r["event"] == "22"
                    for r in rows
                )
            )
        finally:
            net.close()
