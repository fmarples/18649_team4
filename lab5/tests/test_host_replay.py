"""Large committed-prefix replay must not overflow the Pi display adapter."""

import unittest

from test_core import Node, rpc


class HostReplayTests(unittest.TestCase):
    def test_replay_larger_than_old_notification_queue(self):
        self.check_replay(2201)

    def test_full_capacity_replay_is_lossless_and_can_be_drained_in_batches(self):
        self.check_replay(30000)

    def check_replay(self, count):
        node = Node(2)
        self.addCleanup(node.close)
        for i in range(1, count + 1):
            node.receive(rpc(3, 1, 2, 1, prev=i - 1,
                             prev_term=1 if i > 1 else 0,
                             index=i, entry_term=1, event=22, flags=1,
                             commit=count), i)
            list(node.drain())
        node.receive(rpc(3, 1, 2, 1, prev=count, prev_term=1,
                         commit=count), count + 1)
        self.assertEqual(node.status["applied"], count)
        self.assertEqual(node.status["dropped"], 0)
        self.assertEqual(list(node.applied(limit=0)), [])
        first = list(node.applied(limit=64))
        self.assertEqual(len(first), 64)
        rest = list(node.applied())
        self.assertEqual([r[0] for r in first + rest], list(range(1, count + 1)))
        self.assertTrue(all(r[1:3] == (1, 22) for r in first + rest))
        self.assertTrue(all(r[3] for r in first + rest))
        self.assertEqual(list(node.applied()), [])
