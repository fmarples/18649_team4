import unittest
from frame_history import FrameHistory, WINDOW_NS, CAPACITY

class HistoryTests(unittest.TestCase):
    def test_same_bus_or_opposite_copy_is_suppressed(self):
        h = FrameHistory()
        self.assertTrue(h.first_copy(0x010, 0, 7, 0))
        self.assertFalse(h.first_copy(0x010, 0, 7, 1))

    def test_intervening_sequence_does_not_erase_history(self):
        h = FrameHistory()
        self.assertTrue(h.first_copy(0x010, 0, 7, 0))
        self.assertTrue(h.first_copy(0x010, 0, 8, 1))
        self.assertFalse(h.first_copy(0x010, 0, 7, 2))

    def test_fault_sources_are_independent(self):
        h = FrameHistory()
        self.assertTrue(h.first_copy(0x020, 1, 0, 0))
        self.assertTrue(h.first_copy(0x020, 3, 0, 0))

    def test_sequence_wrap(self):
        h = FrameHistory()
        for n in range(33):
            self.assertTrue(h.first_copy(0x010, 0, n & 15, n * 20_000_000))

    def test_reboot_expiry_not_extended_by_duplicates(self):
        h = FrameHistory()
        self.assertTrue(h.first_copy(0x010, 0, 0, 0))
        self.assertFalse(h.first_copy(0x010, 0, 0, WINDOW_NS))
        self.assertTrue(h.first_copy(0x010, 0, 0, WINDOW_NS + 1))

    def test_full_history_does_not_evict_live_entries(self):
        h = FrameHistory()
        for n in range(CAPACITY):
            self.assertTrue(h.first_copy(n, 0, 0, 0))
        with self.assertRaises(OverflowError): h.first_copy(100, 0, 0, 0)
        self.assertFalse(h.first_copy(0, 0, 0, 1))
        self.assertTrue(h.first_copy(100, 0, 0, WINDOW_NS + 1))

if __name__ == '__main__': unittest.main()
