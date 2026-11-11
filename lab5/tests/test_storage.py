import sys
import ctypes as C
import unittest
import random
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

    def test_rollback_write_failure_preserves_old_or_new_state(self):
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

    def test_runtime_rollback_does_not_erase_or_change_retained_prefix(self):
        n = Node(3)
        try:
            for i in range(2505):
                self.assertTrue(lib.l5_host_store_append(n.ptr, 1, i % 24))
            before = self.entries(n)
            erases = lib.l5_host_store_state(n.ptr, 5)
            self.assertTrue(lib.l5_host_truncate(n.ptr, 2501))
            self.assertTrue(lib.l5_host_store_hardstate(n.ptr, 2, 2))
            for _ in range(4):
                self.assertTrue(lib.l5_host_store_append(n.ptr, 2, 22))
            self.assertEqual(lib.l5_host_store_state(n.ptr, 5), erases)
            self.assertTrue(lib.l5_host_reopen(n.ptr))
            self.assertEqual(self.entries(n), before[:2501] + [(2, 22)] * 4)
            self.assertEqual(lib.l5_host_store_state(n.ptr, 4), 2510)
        finally:
            n.close()

    def test_full_runtime_journal_spills_without_erasing(self):
        n, term = self.full_journal()
        try:
            erases = lib.l5_host_store_state(n.ptr, 5)
            for t in range(term + 1, term + 11):
                self.assertTrue(lib.l5_host_store_hardstate(n.ptr, t, t % 4))
                self.assertTrue(lib.l5_host_store_append(n.ptr, t, 22))
            self.assertTrue(lib.l5_host_truncate(n.ptr, 15))
            self.assertEqual(lib.l5_host_store_state(n.ptr, 5), erases)
            self.assertTrue(lib.l5_host_reopen(n.ptr))
            self.assertEqual(lib.l5_host_store_state(n.ptr, 0), term + 10)
            self.assertEqual(lib.l5_host_store_state(n.ptr, 1), (term + 10) % 4)
            entries = self.entries(n)
            self.assertTrue(lib.l5_host_store_prepare_boot(n.ptr))
            self.assertTrue(lib.l5_host_reopen(n.ptr))
            self.assertEqual(self.entries(n), entries)
            self.assertEqual(lib.l5_host_store_state(n.ptr, 4), 15)
            self.assertEqual(lib.l5_host_store_state(n.ptr, 2), 1)
        finally:
            n.close()

    def test_random_rollbacks_reopen_and_boot_reclamation(self):
        n, expected, rng = Node(2), [], random.Random(524)
        try:
            for step in range(1200):
                if expected and rng.randrange(5) == 0:
                    count = rng.randrange(len(expected) + 1)
                    self.assertTrue(lib.l5_host_truncate(n.ptr, count))
                    expected = expected[:count]
                else:
                    event = rng.randrange(24)
                    self.assertTrue(lib.l5_host_store_append(n.ptr, 1, event))
                    expected.append((1, event))
                if step % 31 == 0:
                    self.assertTrue(lib.l5_host_reopen(n.ptr))
                    self.assertEqual(self.entries(n), expected)
            self.assertTrue(lib.l5_host_store_prepare_boot(n.ptr))
            self.assertTrue(lib.l5_host_reopen(n.ptr))
            self.assertEqual(self.entries(n), expected)
            self.assertEqual(lib.l5_host_store_state(n.ptr, 4), len(expected))
        finally:
            n.close()

    def test_interrupted_reclamation_of_rollback_preserves_log_and_vote(self):
        for cut in range(15):
            with self.subTest(cut=cut):
                n = Node(2)
                try:
                    for i in range(10):
                        self.assertTrue(lib.l5_host_store_append(n.ptr, 1, i))
                    self.assertTrue(lib.l5_host_truncate(n.ptr, 5))
                    self.assertTrue(lib.l5_host_store_hardstate(n.ptr, 2, 3))
                    self.assertTrue(lib.l5_host_store_append(n.ptr, 2, 22))
                    expected = self.entries(n)
                    lib.l5_host_fail_write(n.ptr, cut)
                    lib.l5_host_store_prepare_boot(n.ptr)
                    lib.l5_host_fail_write(n.ptr, -1)
                    self.assertTrue(lib.l5_host_reopen(n.ptr))
                    self.assertEqual(self.entries(n), expected)
                    self.assertEqual(lib.l5_host_store_state(n.ptr, 0), 2)
                    self.assertEqual(lib.l5_host_store_state(n.ptr, 1), 3)
                    self.assertTrue(lib.l5_host_store_prepare_boot(n.ptr))
                    self.assertEqual(self.entries(n), expected)
                finally:
                    n.close()

    def test_physical_space_exhaustion_preserves_prefix_and_reclaims_at_boot(self):
        n = Node(2)
        try:
            # Fill the log, then repeatedly replace its last uncommitted entry.
            for i in range(30000):
                self.assertTrue(lib.l5_host_store_append(n.ptr, 1, i % 24))
            prefix = self.entries(n)[:29999]
            erases = lib.l5_host_store_state(n.ptr, 5)
            for _ in range((32256 - 30000) // 2):
                self.assertTrue(lib.l5_host_truncate(n.ptr, 29999))
                self.assertTrue(lib.l5_host_store_append(n.ptr, 1, 22))
            self.assertFalse(lib.l5_host_truncate(n.ptr, 29999))
            self.assertEqual(lib.l5_host_store_state(n.ptr, 5), erases)
            self.assertTrue(lib.l5_host_reopen(n.ptr))
            self.assertEqual(self.entries(n), prefix + [(1, 22)])
            self.assertTrue(lib.l5_host_store_prepare_boot(n.ptr))
            self.assertEqual(lib.l5_host_store_state(n.ptr, 4), 30000)
            self.assertTrue(lib.l5_host_truncate(n.ptr, 29999))
        finally:
            n.close()
