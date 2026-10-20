"""Exercise bridge reception through python-can's real Notifier and virtual bus."""
import csv
from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
import threading
from unittest.mock import patch
import unittest
import uuid
import can
import can_protocol as protocol
import cockpit_bridge
from cockpit_bridge import Receiver


class CapturedLog:
    def __init__(self):
        self.rows = []
        self.received = threading.Event()

    def write(self, **row):
        self.rows.append(row)
        self.received.set()


class ReceiverIntegrationTests(unittest.TestCase):
    def test_real_main_constructs_notifiers_and_sends_dual_bus_commands(self):
        real_bus = can.Bus
        buses = []
        prefix = 'lab3-main-' + uuid.uuid4().hex
        def virtual_bus(*args, **kwargs):
            bus = real_bus(interface='virtual', channel=prefix + kwargs['channel'])
            buses.append(bus)
            self.addCleanup(bus.shutdown)
            return bus
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bridge.csv'
            with patch.object(sys, 'argv', ['cockpit_bridge', '--force-demo', '--log', str(path)]), \
                 patch.object(cockpit_bridge.can, 'Bus', side_effect=virtual_bus), \
                 patch.object(cockpit_bridge.time, 'sleep', side_effect=KeyboardInterrupt), \
                 redirect_stdout(io.StringIO()):
                cockpit_bridge.main()
            with path.open(newline='') as stream:
                rows = list(csv.DictReader(stream))
            controls = [row for row in rows if row['event']=='CAN_TX' and row['id_hex']=='0x010']
            self.assertEqual({row['interface'] for row in controls}, {'can0', 'can1'})
            self.assertEqual(len(controls), 2)
            tasks = {row['event']: float(row['latency_us']) for row in rows if row['event'].startswith('TASK_')}
            self.assertEqual(set(tasks), {'TASK_HB_MON', 'TASK_HB_TX', 'TASK_BLINK_TX'})
            self.assertTrue(all(value >= 0 for value in tasks.values()))

    def test_cmd_tx_marker_follows_both_ctrl_writes(self):
        order = []
        real_bus = can.Bus
        prefix = 'lab3-order-' + uuid.uuid4().hex
        def virtual_bus(*args, **kwargs):
            bus = real_bus(interface='virtual', channel=prefix + kwargs['channel'])
            self.addCleanup(bus.shutdown)
            real_send = bus.send
            def send(msg, timeout=None):
                order.append(('send', kwargs['channel'], msg.arbitration_id))
                return real_send(msg, timeout)
            bus.send = send
            return bus
        class Trace:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def udp_rx(self): pass
            def can_tx(self, bus): pass
            def cmd_tx(self): order.append(('cmd_tx',))
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(sys, 'argv', ['cockpit_bridge', '--force-demo', '--log', str(Path(directory) / 'b.csv')]), \
                 patch.object(cockpit_bridge.can, 'Bus', side_effect=virtual_bus), \
                 patch.object(cockpit_bridge, 'create_trace', return_value=Trace()), \
                 patch.object(cockpit_bridge.time, 'sleep', side_effect=KeyboardInterrupt), \
                 redirect_stdout(io.StringIO()):
                cockpit_bridge.main()
        marker = order.index(('cmd_tx',))
        self.assertEqual(order[marker-2:marker], [('send', 'can0', protocol.CTRL), ('send', 'can1', protocol.CTRL)])

    def test_notifier_delivers_heartbeat_to_bridge_state_and_log(self):
        channel = 'lab3-test-' + uuid.uuid4().hex
        log = CapturedLog()
        heartbeats, states = {}, {}
        receiver = Receiver(log, heartbeats, states, {'counter': 0}, {'latched': False})
        with can.Bus(interface='virtual', channel=channel) as receiving, \
             can.Bus(interface='virtual', channel=channel) as sending:
            notifier = can.Notifier(receiving, [receiver], timeout=0.05)
            try:
                sending.send(can.Message(arbitration_id=protocol.HB_N2, is_extended_id=False,
                    data=protocol.pack_heartbeat(3, protocol.STATE_OK, True, True)))
                self.assertTrue(log.received.wait(1), repr(notifier.exception))
                self.assertIsNone(notifier.exception)
                self.assertEqual(states[protocol.ZONE_N2], protocol.STATE_OK)
                self.assertGreater(heartbeats[(protocol.ZONE_N2, channel)], 0)
                self.assertEqual(log.rows[0]['event'], 'CAN_RX')
                self.assertEqual(log.rows[0]['detail'], 'valid_crc')
                self.assertEqual(log.rows[0]['seq'], 3)
                self.assertGreaterEqual(float(log.rows[0]['latency_us']), 0)
            finally:
                notifier.stop(timeout=1)


if __name__ == '__main__':
    unittest.main()
