"""Physical two-bus simulator: application packets, not direct Raft calls.

No hardware timing claim: fixed 240 us receive latency with 1 ms task ticks.
"""

import heapq
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "host"))
from native import Agent


class Network:
    def __init__(self, leader=1, seed=1):
        self.nodes = {i: Agent(i, leader, seed) for i in (1, 2, 3)}
        self.links = {(i, b) for i in self.nodes for b in (0, 1)}
        self.active = set(self.nodes)
        self.now = 0
        self.queue = []
        self.seq = 0
        self.upstream = True
        self.frames = []
        self.received = []

    def deliver(self, dst, bus, can_id, data, at):
        self.received.append((at, dst, bus, can_id, data))
        self.nodes[dst].receive_can(bus, can_id, data, at)

    def close(self):
        for n in self.nodes.values():
            n.close()

    def transmit(self):
        for src, n in self.nodes.items():
            for bus, can_id, data in n.outgoing():
                if src not in self.active or (src, bus) not in self.links:
                    continue
                self.frames.append((self.now, src, bus, can_id, data))
                for dst in self.active:
                    if dst != src and (dst, bus) in self.links:
                        self.seq += 1
                        heapq.heappush(
                            self.queue,
                            (self.now + 240, self.seq, dst, bus, can_id, data),
                        )

    def run(self, ms):
        end = self.now + ms * 1000
        while self.now < end:
            self.now += 1000
            for i in self.active:
                self.nodes[i].update(self.now, self.upstream if i == 1 else True)
            self.transmit()
            while self.queue and self.queue[0][0] <= self.now:
                at, _, dst, bus, can_id, data = heapq.heappop(self.queue)
                if dst in self.active and (dst, bus) in self.links:
                    self.deliver(dst, bus, can_id, data, at)
            self.transmit()

    def logs(self):
        return [
            list(self.nodes[i].log())[: self.nodes[i].status["commit"]]
            for i in self.active
        ]


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.n = Network()

    def tearDown(self):
        self.n.close()

    def agree(self):
        logs = self.n.logs()
        self.assertTrue(
            all(x == logs[0] for x in logs), [n.status for n in self.n.nodes.values()]
        )

    def test_cold_boot_then_proxy_start(self):
        self.n.upstream = False
        self.n.run(500)
        self.agree()
        self.assertTrue(
            all(n.health(self.n.now)["error"] for n in self.n.nodes.values())
        )
        self.n.upstream = True
        self.n.run(500)
        self.agree()
        self.assertTrue(
            all(not n.health(self.n.now)["error"] for n in self.n.nodes.values())
        )
        self.assertTrue(all(n.status["links"] == 63 for n in self.n.nodes.values()))

    def test_single_link_loss_no_election_and_restore(self):
        self.n.run(500)
        self.n.links.remove((2, 0))
        self.n.run(500)
        self.agree()
        self.assertTrue(all(n.status["term"] == 1 for n in self.n.nodes.values()))
        self.assertEqual(self.n.nodes[1].status["links"], 63 & ~4)
        self.n.links.add((2, 0))
        self.n.run(400)
        self.agree()
        self.assertEqual(self.n.nodes[1].status["links"], 63)

    def test_two_cut_hop_keeps_leader_and_clock(self):
        self.n.run(500)
        self.n.links -= {(1, 1), (3, 0)}
        self.n.run(800)
        self.agree()
        self.assertTrue(
            all(n.status["term"] == 1 for n in self.n.nodes.values()),
            [n.status for n in self.n.nodes.values()],
        )
        self.assertTrue(self.n.nodes[3].health(self.n.now)["synced"])
        self.assertGreater(self.n.nodes[2].health(self.n.now)["relays"], 0)

    def test_pi_failure_election_and_return(self):
        self.n.run(500)
        self.n.active.remove(1)
        self.n.run(100)
        self.assertTrue(
            all(self.n.nodes[i].health(self.n.now)["error"] for i in (2, 3))
        )
        self.n.run(700)
        leaders = [i for i in (2, 3) if self.n.nodes[i].status["role"] == 2]
        self.assertEqual(len(leaders), 1)
        self.n.active.add(1)
        self.n.run(1000)
        self.agree()
        self.assertEqual(self.n.nodes[1].status["role"], 0)

    def test_stm_leader_loss_does_not_fail_cockpit(self):
        self.n.close()
        self.n = Network(0, 8)
        self.n.run(1000)
        leader = next(i for i, n in self.n.nodes.items() if n.status["role"] == 2)
        if leader == 1:
            self.skipTest("seed elected Pi")
        self.n.active.remove(leader)
        self.n.run(500)
        self.assertTrue(
            all(not self.n.nodes[i].health(self.n.now)["error"] for i in self.n.active)
        )

    def test_network_relay_does_not_loop(self):
        self.n.run(500)
        self.n.links -= {(1, 1), (3, 0)}
        self.n.run(1000)
        self.assertTrue(all(n.status["dropped"] == 0 for n in self.n.nodes.values()))
        self.assertLess(len(self.n.frames), 12000)

    def test_cold_follower_recovers_epoch_after_multiple_ref_wraps(self):
        # Leader uptime exceeds two 32-bit microsecond wraps; a newly booted
        # follower's raw clock is near zero. Send actual REPORT/REF packets.
        leader, follower = self.n.nodes[1], self.n.nodes[2]
        epoch = (2 << 32) + 123456789
        for elapsed in range(1000, 301000, 1000):
            leader.update(epoch + elapsed)
            follower.update(elapsed)
            for bus, frame_id, data in leader.outgoing():
                follower.receive_can(bus, frame_id, data, elapsed + 240)
            # Drain replies: this test targets clock bootstrap, not replication.
            list(follower.outgoing())
        self.assertTrue(follower.health(300240)["synced"])
        self.assertLess(abs(follower.global_us(300240) - (epoch + 300240)), 100)


if __name__ == "__main__":
    unittest.main()
