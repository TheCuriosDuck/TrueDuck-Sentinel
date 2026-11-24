"""Verify that SQLite backups preserve data, integrity, and retention."""
from contextlib import closing  # Ensure SQLite files are released on Windows.
import sqlite3
import tempfile
import unittest
from pathlib import Path
from cloud_api.backup_databases import save_one


class BackupTests(unittest.TestCase):
    def test_backup_is_readable_and_preserves_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            db = root / 'source.db'
            with closing(sqlite3.connect(db)) as conn, conn:
                conn.execute('CREATE TABLE samples (id INTEGER PRIMARY KEY, value TEXT)')
                conn.execute('INSERT INTO samples (value) VALUES (?)', ('example.test',))
            backup = save_one('private', db, root / 'safe', keep=2)
            self.assertTrue(backup.is_file())
            with closing(sqlite3.connect(backup)) as conn, conn:
                self.assertEqual(conn.execute('SELECT value FROM samples').fetchone()[0], 'example.test')
                self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            # Subsequent backups should not change or delete the real database.
            for _ in range(3):
                save_one('private', db, root / 'safe', keep=2)
            self.assertEqual(len(list((root / 'safe' / 'private').glob('*.sqlite3'))), 2)
            self.assertTrue(db.is_file())

    def test_missing_database_never_creates_empty_fake_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertIsNone(save_one('cloud', root / 'absent.db', root / 'safe'))
            self.assertFalse((root / 'absent.db').exists())


if __name__ == '__main__':
    unittest.main()
