"""Bound repeated state-query work while preserving uncommitted suffix semantics."""

import tempfile
import unittest
from pathlib import Path

from test_core import Node, lib, rpc


def elect(node, peer, term):
    node.tick(500)
    node.receive(rpc(10, peer, node.id, term, success=1), 501)
    node.receive(rpc(2, peer, node.id, term, success=1), 502)
    assert node.status["role"] == 2


class PendingGraphTests(unittest.TestCase):
    def test_held_events_count_once_and_follow_pi_acknowledgements(self):
        n = Node(3, leader=3)
        try:
            def commit(ms):
                list(n.drain())
                n.receive(rpc(4, 2, 3, n.status["term"],
                              index=n.status["length"], success=1), ms)
                list(n.drain())
            commit(0)
            event_indices = []
            for i in range(600):
                n.request(5)
                n.request(6)
                commit(i * 20 + 1)
                if i % 100 == 0:
                    self.assertTrue(n.event())
                    n.tick(i * 20 + 2)
                    commit(i * 20 + 3)
                    event_indices.append(n.status["length"])
            self.assertEqual(lib.l5_host_held_events(n.ptr), 6)
            reads = n.status["entry_reads"]
            for _ in range(20):
                self.assertEqual(lib.l5_host_held_events(n.ptr), 6)
            self.assertEqual(n.status["entry_reads"], reads)
            for count, index in enumerate(event_indices, 1):
                n.receive(rpc(4, 1, 3, n.status["term"], index=index, success=1), 13000)
                self.assertEqual(lib.l5_host_held_events(n.ptr), 6 - count)
            # A leadership change resets match[]; the committed history stays.
            n.receive(rpc(1, 2, 3, 2, index=n.status["length"], entry_term=1), 13001)
            n.tick(14000)
            n.receive(rpc(10, 2, 3, 3, success=1), 14001)
            n.receive(rpc(2, 2, 3, 3, success=1), 14002)
            self.assertEqual(n.status["role"], 2)
            self.assertEqual(lib.l5_host_held_events(n.ptr), 6)
        finally:
            n.close()

    def test_duplicate_ack_does_not_multiply_catchup_traffic(self):
        n = Node(1)
        try:
            for _ in range(20):
                n.request(5)
                n.request(6)
                list(n.drain())
            ack = rpc(4, 2, 1, 1, index=1, success=1)
            n.receive(ack, 1)
            self.assertTrue(list(n.drain()))
            for tick in range(2, 22):
                n.receive(ack, tick)
            self.assertEqual(list(n.drain()), [])
            # Periodic retries still recover a lost next entry.
            n.tick(101)
            self.assertTrue(list(n.drain()))
        finally:
            n.close()

    def test_idempotent_state_requests_do_not_rescan_a_long_suffix(self):
        n = Node(1)
        try:
            for _ in range(600):
                self.assertTrue(n.request(5))  # NODE_2_UP
                self.assertTrue(n.request(6))  # NODE_2_DOWN, no quorum
                list(n.drain())
            length = n.status["length"]
            reads = n.status["entry_reads"]
            for _ in range(20):
                self.assertTrue(n.request(6))
            self.assertEqual(n.status["entry_reads"], reads)
            self.assertEqual(n.status["length"], length)
            self.assertEqual(n.status["nodes"], 0)  # still not committed
        finally:
            n.close()

    def test_restart_reconstructs_pending_state_without_publishing_it(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "raft.bin"
            n = Node(1, path=path)
            n.request(5)
            n.request(13)  # NODE_2's A link
            n.close()
            n = Node(1, path=path)
            try:
                elect(n, 2, 2)
                length = n.status["length"]
                self.assertTrue(n.request(13))
                self.assertEqual(n.status["length"], length)
                self.assertEqual(n.status["links"], 0)
            finally:
                n.close()

    def test_conflicting_suffix_rebuilds_pending_state(self):
        n = Node(2)
        try:
            n.receive(rpc(3, 1, 2, 1, index=1, entry_term=1, event=5, flags=1), 1)
            n.receive(rpc(3, 1, 2, 1, prev=1, prev_term=1,
                          index=2, entry_term=1, event=13, flags=1), 2)
            # The new leader replaces the uncommitted link-up with node-down.
            n.receive(rpc(3, 3, 2, 2, prev=1, prev_term=1,
                          index=2, entry_term=2, event=6, flags=1), 3)
            elect(n, 3, 3)
            length = n.status["length"]
            self.assertTrue(n.request(5))
            self.assertTrue(n.request(13))
            self.assertEqual(n.status["length"], length + 2)
            self.assertEqual(n.status["nodes"], 0)
        finally:
            n.close()
