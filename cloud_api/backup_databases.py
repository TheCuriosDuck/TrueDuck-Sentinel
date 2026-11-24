"""Back up BOTH TrueDuck Sentinel SQLite databases outside the source-code folder.

The main reason for this location is that deleting an old TrueDuck Sentinel ZIP folder
should not destroy your most recent backup. On Windows the directory is:
    %LOCALAPPDATA%\\TrueDuck Sentinel\\Backups

The backup uses SQLite's online backup API (not raw file copies) so that WAL
and running transactions are handled correctly. It checks integrity, limits
retained copies, and never copies authentication-token text files. Protect the
backup folder: it still contains reports and possibly other private data.
"""

# Standard-library tools for files, SQLite and predictable timestamps.
import argparse
import os
import sqlite3
from contextlib import closing  # Ensure SQLite connections are CLOSED after backup.
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DATABASES = {
    'private': PROJECT / 'backend' / 'data' / 'scamlens.db',
    'cloud': PROJECT / 'cloud_api' / 'data' / 'cloud-dev.db',
}


def backup_root() -> Path:
    """Keep backups outside the versioned application directory by default."""
    override = os.environ.get('SCAMLENS_BACKUP_DIR')
    if override:
        return Path(override).expanduser()
    local_app = os.environ.get('LOCALAPPDATA')
    if local_app:
        return Path(local_app) / 'TrueDuck Sentinel' / 'Backups'
    return Path.home() / '.local' / 'share' / 'scamlens' / 'backups'


def save_one(name: str, source: Path, target_dir: Path | None = None, keep: int = 30) -> Path | None:
    """Make one complete SQLite snapshot, verify it and remove older backups."""
    if not source.is_file():
        print(f'{name}: database has not been created yet; nothing to back up.')
        return None
    destination = (target_dir or backup_root()).resolve() / name
    destination.mkdir(parents=True, exist_ok=True)
    # Use microseconds so two backups taken in the same second have unique names.
    time_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path = destination / f'{name}-{time_id}.sqlite3'
    try:
        # sqlite3.backup() safely reads a live DB, including its write-ahead log.
        with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro',
                                     uri=True, timeout=10)) as live:
            with closing(sqlite3.connect(path)) as saved:
                # Copy a transaction-consistent snapshot of the live database.
                live.backup(saved)
                result = saved.execute('PRAGMA integrity_check').fetchone()[0]
                if result != 'ok':
                    raise RuntimeError(f'Backup integrity check failed: {result}')
        try:
            path.chmod(0o600)
        except OSError:
            pass  # Windows permissions must be managed by the account/drive ACL.
    except Exception:
        path.unlink(missing_ok=True)
        raise
    # Retain the most recent copies; older files are deleted from THIS backup
    # folder only, never from the user's source database.
    copies = sorted(destination.glob(f'{name}-*.sqlite3'), reverse=True)
    for obsolete in copies[keep:]:
        obsolete.unlink()
    print(f'{name}: backed up to {path}')
    return path


def main():
    """Allow one database or both, with a reasonable retention limit."""
    parser = argparse.ArgumentParser(description='Back up TrueDuck Sentinel SQLite databases')
    parser.add_argument('--database', choices=['private', 'cloud', 'both'], default='both')
    parser.add_argument('--keep', type=int, default=30, help='How many copies to keep per database')
    args = parser.parse_args()
    if not 1 <= args.keep <= 365:
        parser.error('--keep must be between 1 and 365')
    selected = DATABASES if args.database == 'both' else {args.database: DATABASES[args.database]}
    for name, path in selected.items():
        save_one(name, path, keep=args.keep)
    print('Backups contain private data. Keep this Windows account secure and test restoring a copy.')


if __name__ == '__main__':
    main()
