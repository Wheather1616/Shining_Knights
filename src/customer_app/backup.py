from __future__ import annotations

from datetime import datetime, timedelta
import os
from pathlib import Path

from .db_crypto import (
    is_plaintext_sqlite,
    migrate_plaintext_database,
    open_encrypted_connection,
    verify_encrypted_database,
)


class DatabaseBackupManager:
    """Create encrypted SQLCipher backups and prune old recovery points."""

    def __init__(self, db_path: Path, backup_dir: Path, key_hex: str, *, settings_store=None):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.key_hex = key_hex
        self.settings_store = settings_store
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Backups created before SQLCipher was enabled were plaintext SQLite.
        # Convert them in-place so sensitive historical data is not left exposed.
        self.migrate_existing_plaintext_backups()

    def _backup_files(self) -> list[Path]:
        return sorted(
            self.backup_dir.glob("customers_*.db"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

    def latest_backup(self) -> Path | None:
        backups = self._backup_files()
        return backups[0] if backups else None

    def backup_is_due(self, minimum_interval: timedelta = timedelta(hours=1)) -> bool:
        latest = self.latest_backup()
        if latest is None:
            return True

        latest_time = datetime.fromtimestamp(latest.stat().st_mtime)
        return datetime.now() - latest_time >= minimum_interval

    def migrate_existing_plaintext_backups(self) -> list[Path]:
        """Encrypt legacy plaintext backup snapshots in place."""
        migrated: list[Path] = []
        for backup in self._backup_files():
            if is_plaintext_sqlite(backup):
                stat = backup.stat()
                migrate_plaintext_database(backup, self.key_hex)
                # Preserve the snapshot's original age so retention still reflects
                # when the recovery point was created, not when it was encrypted.
                try:
                    backup.touch(exist_ok=True)
                    os.utime(backup, (stat.st_atime, stat.st_mtime))
                except OSError:
                    pass
                migrated.append(backup)
            # Existing encrypted backups were verified when they were created.
            # Re-running full SQLite + SQLCipher integrity checks across every
            # historical snapshot on every app launch adds startup cost without
            # improving the safety of the live database. Plaintext backups are
            # still detected and migrated here.
        return migrated

    def create_backup(self) -> Path:
        """Create a transactionally consistent encrypted SQLCipher snapshot."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Customer database does not exist: {self.db_path}")

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_path = self.backup_dir / f"customers_{timestamp}.db"

        counter = 1
        while backup_path.exists():
            backup_path = self.backup_dir / f"customers_{timestamp}_{counter:02d}.db"
            counter += 1

        # Build the snapshot under a temporary name, verify it, then publish it
        # atomically. A crash or forced shutdown can therefore leave at worst a
        # .tmp file, never a corrupt file that looks like a valid recovery point.
        temp_path = backup_path.with_name(backup_path.name + ".tmp")
        temp_path.unlink(missing_ok=True)

        from .recovery import settings_snapshot_path
        snapshot = settings_snapshot_path(backup_path)
        snapshot_tmp = snapshot.with_name(snapshot.name + '.tmp')
        source = destination = None
        try:
            try:
                source = open_encrypted_connection(self.db_path, self.key_hex, validate=True)
                destination = open_encrypted_connection(temp_path, self.key_hex, validate=False)
                # Both connections are keyed before invoking the encrypted backup API.
                source.backup(destination)
            finally:
                # Close before removing a failed snapshot, including on Windows.
                if destination is not None: destination.close()
                if source is not None: source.close()
            verify_encrypted_database(temp_path, self.key_hex)
            if os.name == "posix":
                temp_path.chmod(0o600)
            if self.settings_store:
                # Write settings first; only a verified published .db counts as a backup.
                import json
                with snapshot_tmp.open('w', encoding='utf-8') as handle:
                    json.dump(self.settings_store.load().to_dict(), handle, indent=2, ensure_ascii=False)
                    handle.flush()
                    os.fsync(handle.fileno())
                if os.name == 'posix':
                    snapshot_tmp.chmod(0o600)
                os.replace(snapshot_tmp, snapshot)
            os.replace(temp_path, backup_path)
        except Exception:
            temp_path.unlink(missing_ok=True)
            snapshot_tmp.unlink(missing_ok=True)
            snapshot.unlink(missing_ok=True)
            raise

        return backup_path

    def create_backup_if_due(
        self,
        minimum_interval: timedelta = timedelta(hours=1),
    ) -> Path | None:
        if not self.backup_is_due(minimum_interval):
            return None

        backup_path = self.create_backup()
        self.prune_backups()
        return backup_path

    def prune_backups(self) -> list[Path]:
        """Apply a 24-hour / 30-day / 12-month retention policy."""
        backups = self._backup_files()
        if not backups:
            return []

        now = datetime.now()
        keep: set[Path] = {backups[0]}
        daily_buckets: set[str] = set()
        monthly_buckets: set[str] = set()

        for backup in backups:
            backup_time = datetime.fromtimestamp(backup.stat().st_mtime)
            age = now - backup_time

            if age <= timedelta(hours=24):
                keep.add(backup)
                continue

            if age <= timedelta(days=30):
                bucket = backup_time.strftime("%Y-%m-%d")
                if bucket not in daily_buckets:
                    daily_buckets.add(bucket)
                    keep.add(backup)
                continue

            if age <= timedelta(days=366):
                bucket = backup_time.strftime("%Y-%m")
                if bucket not in monthly_buckets:
                    monthly_buckets.add(bucket)
                    keep.add(backup)

        removed: list[Path] = []
        for backup in backups:
            if backup in keep:
                continue
            backup.unlink(missing_ok=True)
            from .recovery import settings_snapshot_path
            settings_snapshot_path(backup).unlink(missing_ok=True)
            removed.append(backup)

        return removed
