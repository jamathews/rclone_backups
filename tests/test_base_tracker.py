import unittest
from unittest.mock import patch, MagicMock
import sqlite3
import os
from base_tracker import BaseTracker

class MockTracker(BaseTracker):
    @property
    def dest_prefix(self):
        return "dest_prefix"
    
    @property
    def source_prefix(self):
        return "source_prefix"
    
    def populate_source(self, source):
        return [source]

class TestBaseTracker(unittest.TestCase):
    def setUp(self):
        self.filename = "test_tracker.db"
        self.sources = ["/src1", "/src2"]
        self.remote_name = "remote"
        self.destination = "dest"
        self.logdir = "logs"

    @patch('base_tracker.BaseTracker._init_tracker')
    @patch('signal.signal')
    def test_init(self, mock_signal, mock_init):
        tracker = MockTracker(self.filename, self.sources, self.remote_name, self.destination, self.logdir)
        self.assertEqual(tracker._filename, self.filename)
        self.assertEqual(tracker._top_level_sources, self.sources)
        self.assertEqual(tracker.destination, "dest/")
        self.assertEqual(tracker.remote_name, "remote")

    def test_bytes_to_str(self):
        self.assertEqual(BaseTracker._bytes_to_str(b"hello"), "hello")
        self.assertEqual(BaseTracker._bytes_to_str("already_str"), "already_str")
        # b"\xff" cannot be decoded by utf-8 or ascii.
        # errors="backslashreplace" in _decode will turn it into '\xff'
        self.assertEqual(BaseTracker._bytes_to_str(b"\xff"), "\\xff")

    def test_sleep_on_cap_exceeded(self):
        with patch('base_tracker.BaseTracker._init_tracker'):
            tracker = MockTracker(self.filename, self.sources, self.remote_name, self.destination, self.logdir)
            first_sleep = tracker.sleep_on_cap_exceeded
            self.assertEqual(first_sleep, 300)
            # After first access, _sleep_on_cap_exceeded becomes 600
            second_sleep = tracker.sleep_on_cap_exceeded
            self.assertEqual(second_sleep, 600)
            # After second access, it becomes 1200
            
            tracker._sleep_on_cap_exceeded = 3500
            third_sleep = tracker.sleep_on_cap_exceeded
            self.assertEqual(third_sleep, 3500)
            # After third access, it should be 7000, but capped at 3600
            self.assertEqual(tracker._sleep_on_cap_exceeded, 3600)
            
            fourth_sleep = tracker.sleep_on_cap_exceeded
            self.assertEqual(fourth_sleep, 3600)

if __name__ == '__main__':
    unittest.main()
