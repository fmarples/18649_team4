import sys
import ctypes as C
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "host"))
from native import Node, lib


class StorageTests(unittest.TestCase):
    def entries(self, n):
        result = []
        for i in range(1, lib.l5_host_store_length(n.ptr) + 1):
            row = (C.c_uint16 * 2)()
            self.assertTrue(lib.l5_host_entry(n.ptr, i, row))
            result.append(tuple(row))
        return result

    def full_journal(self):
        n = Node(2)
        for _ in range(10):
            self.assertTrue(lib.l5_host_store_append(n.ptr, 1, 22))
        term = 1
        while lib.l5_host_store_state(n.ptr, 2) < 508:
            term += 1
            self.assertTrue(lib.l5_host_store_hardstate(n.ptr, term, 2))
        return n, term

    def test_boot_compaction_preserves_full_journal_and_all_entries(self):
        n, term = self.full_journal()
        try:
            entries = self.entries(n)
            self.assertTrue(lib.l5_host_store_prepare_boot(n.ptr))
            self.assertTrue(lib.l5_host_reopen(n.ptr))
            self.assertEqual(lib.l5_host_store_state(n.ptr, 0), term)
            self.assertEqual(lib.l5_host_store_state(n.ptr, 1), 2)
            self.assertEqual(lib.l5_host_store_state(n.ptr, 2), 1)
            self.assertEqual(self.entries(n), entries)
            generation = lib.l5_host_store_state(n.ptr, 3)
            self.assertTrue(lib.l5_host_store_prepare_boot(n.ptr))
            self.assertEqual(lib.l5_host_store_state(n.ptr, 3), generation)
        finally:
            n.close()

    def test_interrupted_boot_compaction_keeps_history_and_can_retry(self):
        for cut in range(15):
            with self.subTest(cut=cut):
                n, term = self.full_journal()
                try:
                    lib.l5_host_fail_write(n.ptr, cut)
                    lib.l5_host_store_prepare_boot(n.ptr)
                    lib.l5_host_fail_write(n.ptr, -1)
                    self.assertTrue(lib.l5_host_reopen(n.ptr))
                    self.assertEqual(lib.l5_host_store_state(n.ptr, 0), term)
                    self.assertEqual(lib.l5_host_store_state(n.ptr, 1), 2)
                    self.assertEqual(lib.l5_host_store_length(n.ptr), 10)
                    self.assertTrue(lib.l5_host_store_prepare_boot(n.ptr))
                    self.assertEqual(self.entries(n), [(1, 22)] * 10)
                finally:
                    n.close()

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
