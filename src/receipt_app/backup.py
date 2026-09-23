from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from .db_crypto import (
    is_plaintext_sqlite,
    migrate_plaintext_database,
    open_encrypted_connection,
    verify_encrypted_database,
)


class DatabaseBackupManager:
    """Create encrypted SQLCipher backups and prune old recovery points."""

    def __init__(self, db_path: Path, backup_dir: Path, key_hex: str):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.key_hex = key_hex
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Backups created before SQLCipher was enabled were plaintext SQLite.
        # Convert them in-place so sensitive historical data is not left exposed.
        self.migrate_existing_plaintext_backups()

    def _backup_files(self) -> list[Path]:
        return sorted(
            self.backup_dir.glob("receipts_*.db"),
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
                    import os
                    os.utime(backup, (stat.st_atime, stat.st_mtime))
                except OSError:
                    pass
                migrated.append(backup)
            else:
                # Do not silently accept an unreadable encrypted file.
                verify_encrypted_database(backup, self.key_hex)
        return migrated

    def create_backup(self) -> Path:
        """Create a transactionally consistent encrypted SQLCipher snapshot."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Receipt database does not exist: {self.db_path}")

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_path = self.backup_dir / f"receipts_{timestamp}.db"

        counter = 1
        while backup_path.exists():
            backup_path = self.backup_dir / f"receipts_{timestamp}_{counter:02d}.db"
            counter += 1

        source = open_encrypted_connection(self.db_path, self.key_hex, validate=True)
        destination = open_encrypted_connection(backup_path, self.key_hex, validate=False)

        try:
            # SQLCipher supports online encrypted->encrypted backup. Both source and
            # destination are keyed before the backup API is invoked.
            source.backup(destination)
        except Exception:
            backup_path.unlink(missing_ok=True)
            raise
        finally:
            destination.close()
            source.close()

        verify_encrypted_database(backup_path, self.key_hex)
        try:
            import os
            if os.name == "posix":
                backup_path.chmod(0o600)
        except OSError:
            pass
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
            removed.append(backup)

        return removed
