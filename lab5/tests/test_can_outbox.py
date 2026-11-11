"""Exercise finite transmit buffers, partial RPCs and a disconnected bus."""
import errno
import sys
import unittest
import can
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pi'))
from can_outbox import CanOutbox
from test_core import Node, rpc
from vehicle.can_protocol import crc8, valid


class OutboxTests(unittest.TestCase):
    def test_full_ten_frame_buffer_recovers_complete_rpc_without_blocking(self):
        sender, receiver = Node(1), Node(2)
        try:
            messages = [rpc(7, 1, 0, 525, prev=6, prev_term=6, flags=1),
                        rpc(3, 1, 2, 525, prev=0), rpc(3, 1, 3, 525, prev=0)]
            frames = [f for m in messages for f in sender.fragment(m)]
            q, now, capacity, sent = CanOutbox(), [0.0], [10], []
            def send(ident, data):
                if not capacity[0]:
                    raise OSError(errno.ENOBUFS, 'full')
                capacity[0] -= 1
                sent.append((ident, data))
            for ident, data in frames:
                q.enqueue(ident, data, 0.0, 0.0)
            q.flush(send, lambda: now[0])
            self.assertEqual(len(sent), 10)
            self.assertEqual(len(q.frames), 2)
            now[0], capacity[0] = .001, 10
            q.flush(send, lambda: now[0])
            decoded = [r for ident, data in sent if (r := receiver.packet(ident, data, 1))]
            self.assertEqual(decoded, messages)
            self.assertFalse(q.frames)
        finally:
            sender.close(); receiver.close()

    def test_blocked_bus_does_not_stop_other_bus(self):
        queues = [CanOutbox(), CanOutbox()]
        for q in queues:q.enqueue(0x111, bytes(8), 0, 0)
        def blocked(*_):raise OSError(errno.ENOBUFS, 'full')
        queues[0].flush(blocked, lambda: 0)
        sent=[]
        queues[1].flush(lambda *f:sent.append(f), lambda: 0)
        self.assertEqual(len(sent), 1)
        self.assertEqual(len(queues[0].frames), 1)

    def test_expiry_prevents_replaying_disconnected_bus_backlog(self):
        q=CanOutbox()
        q.enqueue(0x111, b'oldbytes', 0, 0)
        def blocked(*_):raise OSError(errno.ENOBUFS, 'full')
        q.flush(blocked, lambda: 0)
        q.enqueue(0x111, b'newbytes', .025, .025)
        sent=[]
        q.flush(lambda *f:sent.append(f), lambda: .025)
        self.assertEqual(sent, [(0x111, b'newbytes')])
        self.assertEqual(q.counts['expired'], 1)

    def test_full_queue_is_bounded_and_retry_is_paced(self):
        q=CanOutbox(capacity=4)
        for _ in range(100):q.enqueue(0x111, bytes(8), 0, 0)
        self.assertEqual(len(q.frames), 4)
        self.assertEqual(q.counts['overflow'], 96)
        def blocked(*_):raise OSError(errno.EAGAIN, 'full')
        for _ in range(100):q.flush(blocked, lambda: 0)
        self.assertEqual(q.counts['backpressure'], 1)
        q.flush(blocked, lambda: .001)
        self.assertEqual(q.counts['backpressure'], 2)

    def test_reference_compensation_is_not_added_twice_on_retry(self):
        q=CanOutbox()
        prefix=bytes([1, 1, 0])+(100).to_bytes(4,'little')
        q.enqueue(0x81, prefix+bytes([crc8(prefix)]), 1, 1)
        attempted=[]
        def blocked(ident,data):
            attempted.append(data)
            raise OSError(errno.ENOBUFS, 'full')
        q.flush(blocked, lambda: 1.003)
        q.flush(lambda ident,data:attempted.append(data), lambda: 1.005)
        self.assertEqual([int.from_bytes(p[3:7],'little') for p in attempted], [3100,5100])
        self.assertTrue(all(valid(p) for p in attempted))

    def test_permanent_error_is_counted_without_retry_loop(self):
        q=CanOutbox()
        q.enqueue(0x111, bytes(8), 0, 0)
        def failed(*_):raise OSError(errno.ENETDOWN, 'interface down')
        q.flush(failed, lambda: 0)
        self.assertEqual(q.counts['send_error'], 1)
        self.assertFalse(q.frames)

    def test_packet_already_stale_after_slow_tick_is_not_enqueued(self):
        q=CanOutbox()
        q.enqueue(0x81, bytes(8), 0, .125)
        self.assertFalse(q.frames)
        self.assertEqual(q.counts['expired'], 1)

    def test_python_can_socket_error_code_is_retried(self):
        q = CanOutbox()
        q.enqueue(0x111, bytes(8), 0, 0)
        def blocked(*_):
            raise can.CanOperationError('full', error_code=errno.ENOBUFS)
        q.flush(blocked, lambda: 0)
        self.assertEqual(len(q.frames), 1)
        self.assertEqual(q.counts['backpressure'], 1)
