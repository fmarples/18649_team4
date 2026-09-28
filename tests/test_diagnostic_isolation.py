"""Block real diagnostic sinks and verify command producers remain responsive."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import threading
import unittest

from pi.background_io import BackgroundIO
from windows.wheel_input_log import InputLoggingSocket
from test_wheel_input_log import packet


class BlockedFile:
    def __init__(self, file):
        self.file = file
        self.entered = threading.Event()
        self.release = threading.Event()

    def write(self, text):
        self.entered.set()
        if not self.release.wait(5):
            raise TimeoutError('test sink was not released')
        return self.file.write(text)

    def flush(self): self.file.flush()
    def close(self): self.file.close()


class DiagnosticIsolationTests(unittest.TestCase):
    def test_full_queue_drops_logs_instead_of_waiting_for_storage(self):
        entered, release = threading.Event(), threading.Event()
        def consume(item):
            entered.set()
            release.wait(5)
        worker = BackgroundIO(consume, capacity=1)
        try:
            self.assertTrue(worker.submit(1))
            self.assertTrue(entered.wait(1))
            self.assertTrue(worker.submit(2))
            self.assertFalse(worker.submit(3))
            self.assertEqual(worker.dropped, 1)
        finally:
            release.set()
            self.assertTrue(worker.close())

    def test_sink_failure_is_observable_and_does_not_escape_to_control(self):
        failed = threading.Event()
        def consume(item):
            failed.set()
            raise OSError('disk full')
        worker = BackgroundIO(consume)
        worker.submit('record')
        self.assertTrue(failed.wait(1))
        self.assertTrue(worker.close())
        self.assertIn('disk full', worker.error)
        self.assertFalse(worker.submit('next record'))

    def test_wheel_packets_continue_while_gui_log_file_is_blocked(self):
        from windows.telemetry_gui import SessionLog
        sent, errors = [], []
        class Transport:
            def sendto(self, data, destination):
                sent.append((data, destination))
                return len(data)
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            log = SessionLog(directory)
            gate = BlockedFile(log.file)
            log.file = gate
            observed = InputLoggingSocket(Transport(), log)
            finished = threading.Event()
            def produce():
                try:
                    for i in range(100): observed.sendto(packet(steer=i), ('127.0.0.1', 8000))
                except Exception as error: errors.append(error)
                finally: finished.set()
            thread = threading.Thread(target=produce)
            try:
                thread.start()
                self.assertTrue(gate.entered.wait(1))
                self.assertTrue(finished.wait(1), 'disk IO blocked wheel transmission')
                self.assertEqual(len(sent), 100)
                self.assertEqual(errors, [])
            finally:
                gate.release.set()
                thread.join(2)
                log.close()

    def test_pi_command_loop_continues_while_csv_write_is_blocked(self):
        import struct
        from unittest.mock import patch
        from test_bridge_freshness import capture, wheel
        import part2_bridge as bridge
        from bridge_diagnostics import BridgeDiagnostics
        import part2_protocol as protocol
        body = protocol.STATUS.pack(b'L2', 1, 2, 1, 20, 0, 1, 0, 32767, 32767, 0, 0, 0, 5, 0)
        import zlib
        status = body + struct.pack('<I', zlib.crc32(body))
        with tempfile.TemporaryDirectory() as directory:
            diagnostics = BridgeDiagnostics(Path(directory) / 'status.csv')
            gate = BlockedFile(diagnostics.file)
            diagnostics.file = gate
            sent, errors = [], []
            def run():
                try:
                    with patch.object(bridge, 'BridgeDiagnostics', return_value=diagnostics):
                        capture([(i * .02, wheel(i, 32767)) for i in range(30)], .6,
                                received_status=status, writes_out=sent)
                except Exception as error: errors.append(error)
            thread = threading.Thread(target=run)
            try:
                thread.start()
                self.assertTrue(gate.entered.wait(1))
                # The fake clock's command loop runs to completion, then joins
                # the deliberately blocked diagnostic writer for at most 2 s.
                thread.join(3)
                self.assertFalse(thread.is_alive())
                self.assertEqual(errors, [])
                self.assertGreaterEqual(len(sent), 30)
                self.assertTrue(all(fields[3] == 32767 for _, fields in sent))
            finally:
                gate.release.set()
                thread.join(2)
                diagnostics.close()
