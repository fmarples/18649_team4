"""Regression for queued frames on a reconnecting CAN bus blocking its peer."""

import unittest

from test_core import Node, rpc


class WireBusTests(unittest.TestCase):
    def setUp(self):
        self.sender = Node(1)
        self.receiver = Node(2)
        self.message = rpc(7, 1, 0, 519, prev=6, prev_term=6, flags=1)
        # Use production fragmentation/CRC and its natural 8-bit wrap. Frames
        # 252/253 were queued before wrap; 125/126 are the current generation.
        self.packets = [self.sender.fragment(self.message) for _ in range(383)]

    def tearDown(self):
        self.sender.close()
        self.receiver.close()

    def deliver(self, packets, bus, ms):
        return [result for can_id, data in packets
                if (result := self.receiver.packet(can_id, data, ms, bus=bus))]

    def test_queued_b_frames_do_not_block_current_a_reports(self):
        self.assertEqual(self.deliver(self.packets[381], 0, 1000), [self.message])
        self.deliver(self.packets[381], 1, 1001)
        self.deliver(self.packets[252], 1, 1002)
        self.deliver(self.packets[253], 1, 1008)
        # Before the fix B's stale sequence 253 rejected A's current 126
        # until a 250 ms assembly reset, exceeding the 66 ms presence limit.
        self.assertEqual(self.deliver(self.packets[382], 0, 1020), [self.message])

    def test_fragments_from_different_buses_cannot_complete_one_message(self):
        frames = self.packets[0]
        self.assertEqual(self.deliver(frames[:2], 0, 0), [])
        self.assertEqual(self.deliver(frames[2:], 1, 1), [])
        self.assertEqual(self.deliver(frames[2:], 0, 2), [self.message])
        self.assertEqual(self.deliver(frames[:2], 1, 3), [self.message])
        self.assertEqual(self.deliver(frames, 0, 4), [])
        self.assertEqual(self.deliver(frames, 1, 4), [])

    def test_both_buses_accept_natural_sequence_wrap(self):
        for i, frames in enumerate(self.packets):
            for bus in (0, 1):
                self.assertEqual(self.deliver(frames, bus, i * 20), [self.message])

    def test_invalid_bus_is_rejected_without_mutating_valid_stream(self):
        self.assertEqual(self.deliver(self.packets[0], 2, 0), [])
        self.assertEqual(self.deliver(self.packets[0], 0, 1), [self.message])


if __name__ == "__main__":
    unittest.main()
