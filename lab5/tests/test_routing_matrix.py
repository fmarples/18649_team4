"""Person 1 routing coverage against the production C core; no hardware claims."""

import itertools
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_network import Network
from test_bus_load import Serialized
from test_core import crc


class RoutingMatrixTests(unittest.TestCase):
    def test_pi_led_cut_transitions_do_not_trigger_local_error_in_models(self):
        # Inspect the transition, not just the settled graph. A rear-only flash
        # was observed on the bench; these ideal models do not include SPI,
        # OS/flash stalls, contact bounce or controller receive loss.
        for model in (Network, Serialized):
            with self.subTest(model=model.__name__):
                net = model(leader=1)
                try:
                    net.run(2000)
                    for connected, link in (
                        (False, (1, 1)), (False, (3, 0)),
                        (True, (3, 0)), (True, (1, 1)),
                    ):
                        if connected:
                            net.links.add(link)
                        else:
                            net.links.remove(link)
                        for _ in range(600):
                            net.run(1)
                            for node in net.nodes.values():
                                self.assertFalse(
                                    node.health(net.now)["error"],
                                    (model.__name__, connected, link, net.now, node.id),
                                )
                    self.settled(net, 1, 63)
                finally:
                    net.close()

    def settled(self, net, leader, links):
        rows = net.logs()
        self.assertTrue(
            all(row == rows[0] for row in rows), [n.status for n in net.nodes.values()]
        )
        for node in net.nodes.values():
            self.assertEqual(node.status["term"], 1)
            self.assertEqual(node.status["leader"], leader)
            self.assertEqual(node.status["nodes"], 7)
            self.assertEqual(node.status["links"], links)
            self.assertFalse(node.status["failed"])
            self.assertFalse(node.status["dropped"])
            self.assertTrue(node.health(net.now)["synced"])

    def test_every_single_link_with_each_leader_records_one_change(self):
        for leader, node, bus in itertools.product((1, 2, 3), (1, 2, 3), (0, 1)):
            with self.subTest(leader=leader, node=node, bus=bus):
                net = Network(leader)
                try:
                    net.run(500)
                    self.settled(net, leader, 63)
                    before = len(net.logs()[0])
                    net.links.remove((node, bus))
                    net.run(500)
                    self.settled(net, leader, 63 & ~(1 << (2 * (node - 1) + bus)))
                    changes = net.logs()[0][before:]
                    self.assertEqual(
                        [e[2] for e in changes], [10 + 2 * (2 * (node - 1) + bus)]
                    )
                    before = len(net.logs()[0])
                    net.links.add((node, bus))
                    net.run(500)
                    self.settled(net, leader, 63)
                    self.assertEqual(
                        [e[2] for e in net.logs()[0][before:]],
                        [9 + 2 * (2 * (node - 1) + bus)],
                    )
                finally:
                    net.close()

    def test_crossed_two_link_cuts_both_orders_each_leader_and_event(self):
        # Six distinct crossed topologies; each has exactly one remaining bridge.
        for leader, left, right, reverse in itertools.product(
            (1, 2, 3), (1, 2, 3), (1, 2, 3), (False, True)
        ):
            if left == right:
                continue
            with self.subTest(leader=leader, cut_a=left, cut_b=right, reverse=reverse):
                net = Network(leader)
                try:
                    net.run(500)
                    cuts = [(left, 0), (right, 1)]
                    if reverse:
                        cuts.reverse()
                    mask = 63
                    for node, bus in cuts:
                        net.links.remove((node, bus))
                        mask &= ~(1 << (2 * (node - 1) + bus))
                        net.run(500)
                    self.settled(net, leader, mask)
                    for node in net.nodes.values():
                        self.assertTrue(node.event())
                    net.run(600)
                    self.settled(net, leader, mask)
                    for event in (21, 22, 23):
                        self.assertEqual(sum(e[2] == event for e in net.logs()[0]), 1)
                    for link in reversed(cuts):
                        net.links.add(link)
                        net.run(400)
                    self.settled(net, leader, 63)
                finally:
                    net.close()

    def test_all_single_links_under_serialized_bus_load(self):
        net = Serialized()
        try:
            net.run(2000)
            for link in sorted(net.links):
                with self.subTest(link=link):
                    net.links.remove(link)
                    net.run(1000)
                    n, b = link
                    self.settled(net, 1, 63 & ~(1 << (2 * (n - 1) + b)))
                    net.links.add(link)
                    net.run(1000)
                    self.settled(net, 1, 63)
            self.assertLess(net.peak_queue, 128)
        finally:
            net.close()

    def test_legacy_frames_cross_bridge_intact_and_bad_crc_does_not(self):
        net = Network()
        try:
            net.run(500)
            net.links -= {(1, 1), (3, 0)}
            net.run(600)
            # Origin N1 -> N3 across N2; preserve the complete legacy payload.
            for ident in (0x010, 0x100, 0x200, 0x020):
                with self.subTest(can_id=ident):
                    body = bytes([1, 0, 0, 1, 0, 0, 0])
                    data = body + bytes([crc(body)])
                    net.received.clear()
                    net.nodes[2].receive_can(0, ident, data, net.now)
                    net.run(10)
                    matches = [r for r in net.received if r[1:] == (3, 1, ident, data)]
                    self.assertEqual(len(matches), 1)
                    bad = data[:-1] + bytes([data[-1] ^ 1])
                    net.received.clear()
                    net.nodes[2].receive_can(0, ident, bad, net.now)
                    net.run(10)
                    self.assertFalse(
                        any(r[3] == ident and r[4] == bad for r in net.received)
                    )
            # The reverse direction carries N3's heartbeat through the same bridge.
            body = bytes([2, 0, 0, 0, 0, 0, 0])
            data = body + bytes([crc(body)])
            net.received.clear()
            net.nodes[2].receive_can(1, 0x102, data, net.now)
            net.run(10)
            self.assertEqual(sum(r[1:] == (1, 0, 0x102, data) for r in net.received), 1)
        finally:
            net.close()

    def test_invalid_fault_reporter_never_indexes_or_relays_as_a_node(self):
        net = Network()
        try:
            net.run(500)
            net.links -= {(1, 1), (3, 0)}
            net.run(600)
            for reporter in (0, 4, 127, 255):
                with self.subTest(reporter=reporter):
                    body = bytes([1, 0, 0, reporter, 0, 0, 0])
                    data = body + bytes([crc(body)])
                    before = net.nodes[2].health(net.now)["relays"]
                    net.nodes[2].receive_can(0, 0x020, data, net.now)
                    self.assertEqual(net.nodes[2].health(net.now)["relays"], before)
                    self.assertFalse(net.nodes[2].status["failed"])
        finally:
            net.close()
