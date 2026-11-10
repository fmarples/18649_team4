"""Serialized 500 kbit/s CAN model; protocol/load test, not a scope substitute.

Each bus arbitrates the lowest standard ID after each frame (240 us assumed).
Software ticks every 100 us. No controller, SPI, Linux or flash-stall model.
"""

import heapq
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_network import Network


class Serialized(Network):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pending = [[], []]
        self.bus_free = [0, 0]
        self.peak_queue = 0

    def transmit(self):
        for src, node in self.nodes.items():
            for bus, can_id, data in node.outgoing():
                if src in self.active and (src, bus) in self.links:
                    self.seq += 1
                    heapq.heappush(self.pending[bus], (can_id, self.seq, src, data))
        for bus in (0, 1):
            self.peak_queue = max(self.peak_queue, len(self.pending[bus]))
            if self.bus_free[bus] > self.now or not self.pending[bus]:
                continue
            can_id, _, src, data = heapq.heappop(self.pending[bus])
            self.bus_free[bus] = self.now + 240
            for dst in self.active:
                if dst != src and (dst, bus) in self.links and (src, bus) in self.links:
                    self.seq += 1
                    heapq.heappush(
                        self.queue,
                        (self.bus_free[bus], self.seq, dst, bus, can_id, data),
                    )

    def run(self, ms):
        end = self.now + ms * 1000
        while self.now < end:
            self.now += 100
            while self.queue and self.queue[0][0] <= self.now:
                at, _, dst, bus, can_id, data = heapq.heappop(self.queue)
                if dst in self.active and (dst, bus) in self.links:
                    self.deliver(dst, bus, can_id, data, self.now)
            for i in self.active:
                self.nodes[i].update(self.now, self.upstream if i == 1 else True)
            self.transmit()


class BusLoadTests(unittest.TestCase):
    def test_serial_bus_boot_hop_election_and_recovery(self):
        net = Serialized()
        try:
            net.run(2000)
            self.assertEqual(net.nodes[1].status["links"], 63)
            net.links -= {(1, 1), (3, 0)}
            net.run(2000)
            self.assertTrue(all(n.status["term"] == 1 for n in net.nodes.values()))
            self.assertTrue(net.nodes[2].event())
            net.run(2000)
            self.assertTrue(
                all(sum(e[2] == 22 for e in n.log()) == 1 for n in net.nodes.values())
            )
            net.links = {(i, b) for i in (1, 2, 3) for b in (0, 1)}
            net.active.remove(1)
            net.run(800)
            self.assertEqual(sum(net.nodes[i].status["role"] == 2 for i in (2, 3)), 1)
            net.active.add(1)
            net.run(2500)
            logs = net.logs()
            self.assertTrue(all(log == logs[0] for log in logs))
            self.assertTrue(all(not n.status["dropped"] for n in net.nodes.values()))
            self.assertLess(net.peak_queue, 128)
        finally:
            net.close()
