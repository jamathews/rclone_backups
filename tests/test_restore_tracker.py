import unittest
from unittest.mock import patch, MagicMock
import subprocess
import json
from restore_tracker import RestoreTracker

class TestRestoreTracker(unittest.TestCase):
    def setUp(self):
        with patch('base_tracker.BaseTracker._init_tracker'):
            self.tracker = RestoreTracker(
                filename="test.db",
                sources=["remote:src/"],
                remote_name="remote",
                destination="/dest",
                logdir="logs",
                depth=1
            )

    def test_dest_prefix(self):
        self.assertEqual(self.tracker.dest_prefix, "/dest/")

    def test_source_prefix(self):
        self.assertEqual(self.tracker.source_prefix, "remote:")

    @patch('subprocess.run')
    def test_populate_source_recursive(self, mock_run):
        # Mock rclone lsjson output
        mock_output = [
            {"Path": "dir1", "IsDir": True},
            {"Path": "dir1/sub1", "IsDir": True},
            {"Path": "file1.txt", "IsDir": False}
        ]
        mock_run.return_value = MagicMock(stdout=json.dumps(mock_output), returncode=0)
        
        sources = self.tracker.populate_source("src/")
        
        # depth=1
        # dir1: depth=0 (<1) -> OK
        # dir1/sub1: depth=1 (not <1) -> Skip
        # Final append: src/
        
        expected = ["src/dir1", "src/"]
        self.assertEqual(sorted(sources), sorted(expected))

    @patch('subprocess.run')
    def test_populate_source_no_depth(self, mock_run):
        self.tracker._depth = None
        mock_output = [
            {"Path": "dir1", "IsDir": True},
            {"Path": "dir1/sub1", "IsDir": True}
        ]
        mock_run.return_value = MagicMock(stdout=json.dumps(mock_output), returncode=0)
        
        sources = self.tracker.populate_source("src/")
        
        expected = ["src/dir1", "src/dir1/sub1", "src/"]
        self.assertEqual(sorted(sources), sorted(expected))

    def test_populate_source_negative_depth(self):
        self.tracker._depth = -1
        sources = self.tracker.populate_source("src/")
        self.assertEqual(sources, ["src/"])

    @patch('subprocess.run')
    def test_populate_source_error(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, "rclone", stderr="error")
        with self.assertRaises(subprocess.CalledProcessError):
            self.tracker.populate_source("src/")

if __name__ == '__main__':
    unittest.main()
