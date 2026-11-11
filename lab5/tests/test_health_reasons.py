"""Diagnostics distinguish local isolation, stale Pi report and stale input."""
import unittest
from test_core import rpc
from test_network import Network, Agent


class HealthReasonTests(unittest.TestCase):
    def test_no_peer_report_then_recovery_and_stale_report(self):
        node, sender = Agent(3), Agent(1)
        try:
            node.update(1000)
            self.assertEqual(node.health(1000)['reason_mask'], 4 | 8 | 16)
            self.assertEqual(node.health(1000)['pi_report_age_ms'], 0xffffffff)
            for ident, data in sender.fragment(rpc(7, 1, 0, 1, flags=1)):
                node.receive_can(1, ident, data, 2000)
            self.assertEqual(node.health(2000)['reason_mask'], 0)
            self.assertFalse(node.health(67000)['error'])
            self.assertEqual(node.health(68000)['reason_mask'], 4 | 8)
            self.assertEqual(node.health(68000)['pi_report_age_ms'], 66)
        finally:
            node.close(); sender.close()

    def test_input_fault_remains_distinct_from_transport_fault(self):
        net = Network()
        try:
            net.run(500)
            net.upstream = False
            net.run(40)
            for n in net.nodes.values():
                self.assertEqual(n.health(net.now)['reason_mask'], 16)
            net.upstream = True
            net.run(40)
            for n in net.nodes.values():
                self.assertEqual(n.health(net.now)['reason_mask'], 0)
        finally:
            net.close()
