"""Fault scenarios run against production C, including its persistent journal."""

import random
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "host"))
from native import Node, lib


def crc(data):
    x = 0
    for b in data:
        x ^= b
        for _ in range(8):
            x = ((x << 1) ^ 7) & 255 if x & 128 else (x << 1) & 255
    return x


def rpc(
    kind,
    src,
    dst,
    term,
    prev=0,
    prev_term=0,
    commit=0,
    index=0,
    entry_term=0,
    event=0,
    success=0,
    flags=0,
):
    p = struct.pack(
        "<BBBBHHHHHHBBBI",
        1,
        kind,
        src,
        dst,
        term,
        prev,
        prev_term,
        commit,
        index,
        entry_term,
        event,
        success,
        flags,
        0,
    )
    return p + bytes([crc(p)])


class Cluster:
    def __init__(self, leader=1, seed=1, capacity=30000):
        self.nodes = {i: Node(i, leader, seed, capacity) for i in (1, 2, 3)}
        self.active = {1, 2, 3}
        self.edges = {(a, b) for a in self.active for b in self.active if a != b}
        self.ms = 0
        self.duplicates = False
        self.loss = 0
        self.rng = random.Random(seed)

    def close(self):
        for n in self.nodes.values():
            n.close()

    def flush(self):
        for _ in range(1000):
            out = [
                (src, p)
                for src, n in self.nodes.items()
                for p in n.drain()
                if src in self.active
            ]
            if not out:
                return
            self.rng.shuffle(out)
            for src, p in out:
                for dst, n in self.nodes.items():
                    if (
                        dst == src
                        or dst not in self.active
                        or (src, dst) not in self.edges
                        or (p[3] and p[3] != dst)
                    ):
                        continue
                    if self.rng.random() < self.loss:
                        continue
                    n.receive(p, self.ms)
                    if self.duplicates:
                        n.receive(p, self.ms)
        raise AssertionError("message storm")

    def run(self, duration):
        for _ in range(duration):
            self.ms += 1
            for i in self.active:
                self.nodes[i].tick(self.ms)
            if self.ms % 20 == 0:
                for src in self.active:
                    s = self.nodes[src].status
                    if s["role"] == 2:
                        for dst in self.active:
                            if (src, dst) in self.edges:
                                self.nodes[dst].heartbeat(src, s["term"], self.ms)
            self.flush()

    def leader(self):
        return [i for i in self.active if self.nodes[i].status["role"] == 2]

    def agree(self, test):
        logs = [
            list(self.nodes[i].log())[: self.nodes[i].status["commit"]]
            for i in self.active
        ]
        test.assertTrue(all(x == logs[0] for x in logs), logs)


class RaftTests(unittest.TestCase):
    def setUp(self):
        self.c = Cluster()

    def tearDown(self):
        self.c.close()

    def test_default_boot_no_election_and_graph_only_after_commit(self):
        n = self.c.nodes[1]
        n.request(3)
        self.assertEqual(n.status["nodes"], 0)
        self.c.run(250)
        self.assertEqual(self.c.leader(), [1])
        self.c.agree(self)
        self.assertTrue(all(x.status["term"] == 1 for x in self.c.nodes.values()))
        self.assertEqual(n.status["nodes"], 1)

    def test_elect_new_leader_and_old_leader_rejoins(self):
        self.c.run(120)
        self.c.active.remove(1)
        self.c.run(400)
        self.assertEqual(len(self.c.leader()), 1)
        new = self.c.leader()[0]
        self.c.nodes[new].request(5)
        self.c.run(200)
        self.c.active.add(1)
        self.c.run(400)
        self.assertEqual(self.c.leader(), [new])
        self.c.agree(self)

    def test_random_election_seeds(self):
        for seed in range(1, 16):
            c = Cluster(0, seed)
            c.run(800)
            self.assertEqual(len(c.leader()), 1)
            c.agree(self)
            c.close()

    def test_duplicate_votes_and_appends(self):
        self.c.duplicates = True
        self.c.run(200)
        for _ in range(20):
            self.c.nodes[2].request(3)
        self.c.run(400)
        self.c.agree(self)
        self.assertEqual(sum(e == 3 for _, _, e in self.c.nodes[1].log()), 1)

    def test_minority_cannot_commit(self):
        self.c.run(200)
        before = self.c.nodes[1].status["commit"]
        self.c.edges = {(2, 3), (3, 2)}
        self.c.nodes[1].request(3)
        self.c.run(400)
        self.assertEqual(self.c.nodes[1].status["commit"], before)

    def test_divergent_suffix_repaired(self):
        self.c.run(200)
        self.c.edges = {(2, 3), (3, 2)}
        self.c.nodes[1].request(3)
        self.c.run(400)
        leader = next(i for i in (2, 3) if self.c.nodes[i].status["role"] == 2)
        self.c.nodes[leader].request(5)
        self.c.run(200)
        self.c.edges = {(a, b) for a in (1, 2, 3) for b in (1, 2, 3) if a != b}
        self.c.run(500)
        self.c.agree(self)
        self.assertNotIn(3, [e for _, _, e in self.c.nodes[leader].log()])

    def test_lost_messages_eventually_catch_up(self):
        self.c.loss = 0.2
        self.c.run(300)
        self.c.nodes[self.c.leader()[0]].request(3)
        self.c.run(1000)
        self.c.loss = 0
        self.c.run(500)
        self.c.agree(self)

    def test_committed_prefix_cannot_be_overwritten(self):
        self.c.nodes[1].request(3)
        self.c.run(200)
        n = self.c.nodes[2]
        old = list(n.log())
        n.receive(rpc(3, 3, 2, 2, prev=0, index=1, entry_term=2, event=5, flags=1), 201)
        self.assertEqual(list(n.log()), old)

    def test_stale_candidate_denied(self):
        self.c.nodes[1].request(3)
        self.c.run(200)
        n = self.c.nodes[2]
        list(n.drain())
        n.receive(rpc(1, 3, 2, 2), 201)
        replies = list(n.drain())
        self.assertTrue(replies)
        self.assertEqual(replies[-1][17], 0)

    def test_limited_log_fails_without_overwriting(self):
        c = Cluster(capacity=4)
        c.run(200)
        for e in (3, 5, 7):
            c.nodes[1].request(e)
            c.run(100)
        self.assertFalse(c.nodes[1].request(1))
        self.assertEqual(c.nodes[1].status["length"], 4)
        c.close()

    def test_graph_add_drop_and_route(self):
        for e in (3, 5, 7, 9, 13, 15, 19):
            self.c.nodes[1].request(e)
            self.c.run(120)
        self.assertEqual(self.c.nodes[1].route(3), (0, 2))
        self.c.nodes[1].request(6)
        self.c.run(150)
        self.assertEqual(self.c.nodes[1].route(3), (-1, 0))
        self.c.nodes[1].request(5)
        self.c.run(150)
        self.assertEqual(self.c.nodes[1].status["links"] & 12, 0)

    def test_persistence_failure_no_ack(self):
        n = self.c.nodes[2]
        list(n.drain())
        lib.l5_host_fail_write(n.ptr, 0)
        n.receive(rpc(1, 3, 2, 2), 10)
        self.assertEqual(n.status["failed"], 1)
        self.assertEqual(list(n.drain()), [])

    def test_restart_does_not_reassert_default_leader(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "raft.bin"
            n = Node(1, path=p)
            n.receive(rpc(3, 2, 1, 3), 20)
            n.close()
            n = Node(1, path=p)
            self.assertEqual(n.status["term"], 3)
            self.assertEqual(n.status["role"], 0)
            n.close()

    def test_truncation_power_loss_keeps_previous_bank(self):
        self.c.nodes[1].request(3)
        self.c.run(200)
        n = self.c.nodes[2]
        before = lib.l5_host_store_length(n.ptr)
        lib.l5_host_fail_write(n.ptr, 3)
        self.assertFalse(lib.l5_host_truncate(n.ptr, 0))
        lib.l5_host_fail_write(n.ptr, -1)
        self.assertTrue(lib.l5_host_reopen(n.ptr))
        self.assertEqual(lib.l5_host_store_length(n.ptr), before)


class WireClockTests(unittest.TestCase):
    def setUp(self):
        self.a = Node(1)
        self.b = Node(2)

    def tearDown(self):
        self.a.close()
        self.b.close()

    def test_fragments_reordered_duplicate_and_crc(self):
        data = next(self.a.drain())
        packets = self.a.fragment(data)
        out = []
        for i in (2, 2, 0, 3, 1, 1):
            p = self.b.packet(*packets[i], 0)
            if p:
                out.append(p)
        self.assertEqual(out, [data])
        bad = bytearray(packets[0][1])
        bad[-1] ^= 1
        self.assertIsNone(self.b.packet(packets[0][0], bad, 1))

    def test_missing_fragment_does_not_deliver(self):
        data = next(self.a.drain())
        for packet in self.a.fragment(data)[:3]:
            self.assertIsNone(self.b.packet(*packet, 0))

    def test_drift_ratio_raw_clock_and_monotonic(self):
        previous = 0
        for i in range(1, 1500):
            raw = round(i * 20000 * 1.0001)
            self.assertTrue(self.b.ref(1, 1, i * 20000, raw))
            t = self.b.global_us(raw)
            self.assertGreaterEqual(t, previous)
            previous = t
        self.assertAlmostEqual(self.b.rate, 1 / 1.0001, places=6)
        self.assertLess(
            abs(self.b.global_us(raw + 10000) - (i * 20000 + 10000 / 1.0001)), 60
        )

    def test_handover_has_bounded_step_and_preserves_time(self):
        self.b.ref(1, 1, 1000000, 1000000)
        before = self.b.global_us(1020000)
        self.b.ref(3, 2, 1021000, 1020000)
        after = self.b.global_us(1020000)
        self.assertLessEqual(after - before, 50)
        self.b.lead(2, 3, 1020000)
        self.assertEqual(self.b.global_us(1020000), after)

    def test_clock_wrap(self):
        self.b.ref(1, 1, 0xFFFF0000, 0xFFFF0000)
        for i in range(1, 10):
            t = 0xFFFF0000 + i * 20000
            self.b.ref(1, 1, t & 0xFFFFFFFF, t)
            self.assertLess(abs(self.b.global_us(t) - t), 2)

    def test_old_ref_does_not_reverse_clock(self):
        self.b.ref(1, 1, 20000, 20000)
        self.b.ref(1, 1, 40000, 40000)
        self.assertFalse(self.b.ref(1, 1, 20000, 60000))
        self.assertGreaterEqual(self.b.global_us(60000), 40000)


if __name__ == "__main__":
    unittest.main()
