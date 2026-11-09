import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "host"))
from native import Node, lib


class StorageTests(unittest.TestCase):
    def test_all_30000_entries_reopen_and_overflow_is_refused(self):
        n = Node(2)
        try:
            for i in range(30000):
                self.assertTrue(lib.l5_host_store_append(n.ptr, 1, i % 24))
            self.assertFalse(lib.l5_host_store_append(n.ptr, 1, 22))
            self.assertTrue(lib.l5_host_reopen(n.ptr))
            self.assertEqual(lib.l5_host_store_length(n.ptr), 30000)
        finally:
            n.close()

    def test_each_bank_switch_failure_point_preserves_old_or_new_state(self):
        for cut in range(12):
            with self.subTest(cut=cut):
                n = Node(2)
                try:
                    for _ in range(10):
                        self.assertTrue(lib.l5_host_store_append(n.ptr, 1, 22))
                    lib.l5_host_fail_write(n.ptr, cut)
                    ok = lib.l5_host_truncate(n.ptr, 5)
                    lib.l5_host_fail_write(n.ptr, -1)
                    self.assertTrue(lib.l5_host_reopen(n.ptr))
                    self.assertEqual(lib.l5_host_store_length(n.ptr), 5 if ok else 10)
                finally:
                    n.close()
