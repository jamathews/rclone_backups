import unittest
from unittest.mock import patch, MagicMock
import os
from backup_tracker import BackupTracker

class TestBackupTracker(unittest.TestCase):
    def setUp(self):
        # We need to mock BaseTracker.__init__ because it initializes sqlite3
        with patch('base_tracker.BaseTracker._init_tracker'):
            self.tracker = BackupTracker(
                filename="test.db",
                sources=["/src"],
                remote_name="remote",
                destination="dest/",
                logdir="logs",
                depth=1
            )

    @patch('socket.gethostname')
    def test_dest_prefix(self, mock_hostname):
        mock_hostname.return_value = "host"
        self.assertEqual(self.tracker.dest_prefix, "remote:dest/host")

    def test_source_prefix(self):
        self.assertEqual(self.tracker.source_prefix, "")

    @patch('os.walk')
    def test_populate_source_depth_1(self, mock_walk):
        # Mock os.walk(source, topdown=True, followlinks=False)
        # depth 0: ('/src', ['dir1', 'dir2'], [])
        # depth 1: ('/src/dir1', ['sub1'], []), ('/src/dir2', [], [])
        
        mock_walk.return_value = [
            ('/src', ['dir1', 'dir2'], []),
            ('/src/dir1', ['sub1'], []),
            ('/src/dir2', [], [])
        ]
        
        sources = self.tracker.populate_source("/src")
        
        # With depth 1:
        # /src (depth 0) -> adds dirs: /src/dir1, /src/dir2. continues to /src/dir1
        # /src/dir1 (depth 1) -> adds subdir: /src/dir1/sub1. STOPS (del dirs[:])
        # /src/dir2 (depth 1) -> adds subdir: (none). STOPS
        # Final append: /src
        
        expected = sorted(["/src/dir1", "/src/dir2", "/src/dir1/sub1", "/src"], reverse=True, key=lambda x: x.count(os.path.sep))
        self.assertEqual(sorted(sources), sorted(expected))

    @patch('os.walk')
    def test_populate_source_depth_0(self, mock_walk):
        self.tracker._depth = 0
        mock_walk.return_value = [
            ('/src', ['dir1', 'dir2'], [])
        ]
        sources = self.tracker.populate_source("/src")
        # Depth 0:
        # /src (depth 0) -> adds /src/dir1, /src/dir2. STOPS.
        # Final append: /src
        expected = ["/src/dir1", "/src/dir2", "/src"]
        self.assertEqual(sorted(sources), sorted(expected))

    def test_populate_source_negative_depth(self):
        self.tracker._depth = -1
        sources = self.tracker.populate_source("/src")
        self.assertEqual(sources, ["/src"])

if __name__ == '__main__':
    unittest.main()
