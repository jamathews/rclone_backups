import unittest
from backup import verbosity_to_log_level
import logging

class TestBackupUtils(unittest.TestCase):
    def test_verbosity_to_log_level(self):
        self.assertEqual(verbosity_to_log_level(0), logging.CRITICAL)
        self.assertEqual(verbosity_to_log_level(1), logging.ERROR)
        self.assertEqual(verbosity_to_log_level(2), logging.WARNING)
        self.assertEqual(verbosity_to_log_level(3), logging.INFO)
        self.assertEqual(verbosity_to_log_level(4), logging.DEBUG)
        self.assertEqual(verbosity_to_log_level(5), logging.DEBUG)
        self.assertEqual(verbosity_to_log_level(-1), logging.CRITICAL)

if __name__ == '__main__':
    unittest.main()
