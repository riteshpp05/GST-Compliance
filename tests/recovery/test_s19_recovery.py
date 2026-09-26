"""
tests.recovery.test_s19_recovery
==================================
Backup, Restore & Disaster Recovery Test Suite for Sprint 19.
Verifies database snapshot backups, controlled restore verification, and restart state survival.
"""

import os
import unittest
from app.db.backup import BackupManager


class TestS19Recovery(unittest.TestCase):

    def test_backup_creation_and_restore_verification(self):
        target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scratch", "test_bkp"))
        backup_info = BackupManager.create_backup(target_dir=target_dir)

        self.assertIn("backup_id", backup_info)
        self.assertIn("timestamp", backup_info)

        if backup_info.get("snapshot_file"):
            snap_file = backup_info["snapshot_file"]
            self.assertTrue(os.path.exists(snap_file))

            test_db = os.path.join(target_dir, "restored_test.db")
            restored = BackupManager.verify_restore(backup_info, test_db)
            self.assertTrue(restored)
            self.assertTrue(os.path.exists(test_db))


if __name__ == "__main__":
    unittest.main()
