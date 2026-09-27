from __future__ import annotations

import os
from pathlib import Path

from sqlcipher3 import dbapi2 as sqlcipher

SQLITE_HEADER = b"SQLite format 3\x00"


class DatabaseEncryptionError(RuntimeError):
    """Raised when an encrypted database cannot be safely opened or migrated."""


def is_plaintext_sqlite(path: Path) -> bool:
    path = Path(path)
    if not path.exists() or path.stat().st_size < len(SQLITE_HEADER):
        return False
    with path.open("rb") as handle:
        return handle.read(len(SQLITE_HEADER)) == SQLITE_HEADER


def _raw_key_sql(key_hex: str) -> str:
    if len(key_hex) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in key_hex):
        raise DatabaseEncryptionError("Invalid SQLCipher raw key format.")
    return f'"x\'{key_hex}\'"'


def _quote_sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def open_encrypted_connection(
    path: Path,
    key_hex: str,
    *,
    validate: bool = True,
):
    """Open a SQLCipher database using a 256-bit raw key."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlcipher.connect(str(path), timeout=10)
    conn.row_factory = sqlcipher.Row

    # SQLCipher requires the key before any operation that touches database pages.
    conn.execute(f"PRAGMA key = {_raw_key_sql(key_hex)}")
    conn.execute("PRAGMA cipher_memory_security = ON")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA secure_delete = ON")
    conn.execute("PRAGMA busy_timeout = 5000")

    if validate:
        try:
            conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
        except Exception as exc:
            conn.close()
            raise DatabaseEncryptionError(
                f"ReceiptFlow could not decrypt database: {path}. The stored key may "
                "not match this database, or the database may be damaged."
            ) from exc

    return conn


def verify_encrypted_database(path: Path, key_hex: str) -> None:
    conn = open_encrypted_connection(path, key_hex, validate=True)
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
        if not integrity or str(integrity[0]).lower() != "ok":
            raise DatabaseEncryptionError(
                f"SQLite integrity check failed for encrypted database: {path}"
            )

        # SQLCipher provides an additional page-level authentication check.
        try:
            cipher_rows = conn.execute("PRAGMA cipher_integrity_check").fetchall()
            if cipher_rows:
                problems = [str(row[0]) for row in cipher_rows if str(row[0]).strip()]
                if problems:
                    raise DatabaseEncryptionError(
                        "SQLCipher integrity check reported problems: " + "; ".join(problems)
                    )
        except DatabaseEncryptionError:
            raise
        except Exception:
            # Older builds may not expose this PRAGMA. Standard integrity_check above
            # still provides a useful validation step.
            pass
    finally:
        conn.close()


def migrate_plaintext_database(path: Path, key_hex: str) -> None:
    """Atomically replace a plaintext SQLite database with a SQLCipher database.

    The original plaintext database is kept untouched until the encrypted copy has
    been exported and verified. A temporary plaintext rename exists only during the
    final swap and is removed after the encrypted replacement has been validated.
    """
    path = Path(path)
    if not path.exists() or not is_plaintext_sqlite(path):
        return

    original_mode = path.stat().st_mode
    encrypted_tmp = path.with_name(path.name + ".encrypted.tmp")
    plaintext_swap = path.with_name(path.name + ".plaintext-migration.tmp")

    encrypted_tmp.unlink(missing_ok=True)
    plaintext_swap.unlink(missing_ok=True)

    source = sqlcipher.connect(str(path), timeout=10)
    try:
        # No key is supplied to main because the source is intentionally plaintext.
        source.execute("SELECT count(*) FROM sqlite_master").fetchone()

        source_count = None
        try:
            source_count = source.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
        except Exception:
            pass

        attach_path = _quote_sql_string(str(encrypted_tmp))
        source.execute(
            f"ATTACH DATABASE {attach_path} AS encrypted KEY {_raw_key_sql(key_hex)}"
        )
        source.execute("SELECT sqlcipher_export('encrypted')")
        source.execute("DETACH DATABASE encrypted")
    except Exception as exc:
        encrypted_tmp.unlink(missing_ok=True)
        raise DatabaseEncryptionError(
            f"Could not migrate plaintext database to SQLCipher: {path}"
        ) from exc
    finally:
        source.close()

    verify_encrypted_database(encrypted_tmp, key_hex)

    if source_count is not None:
        check = open_encrypted_connection(encrypted_tmp, key_hex)
        try:
            encrypted_count = check.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
        finally:
            check.close()
        if encrypted_count != source_count:
            encrypted_tmp.unlink(missing_ok=True)
            raise DatabaseEncryptionError(
                "Encrypted migration validation failed: receipt counts did not match."
            )

    try:
        os.replace(path, plaintext_swap)
        os.replace(encrypted_tmp, path)
        verify_encrypted_database(path, key_hex)
    except Exception:
        # Restore the original plaintext file if the final replacement fails.
        if plaintext_swap.exists():
            path.unlink(missing_ok=True)
            os.replace(plaintext_swap, path)
        encrypted_tmp.unlink(missing_ok=True)
        raise
    else:
        plaintext_swap.unlink(missing_ok=True)
        if os.name == "posix":
            try:
                path.chmod(original_mode & 0o777)
            except OSError:
                pass

        # Remove plaintext SQLite sidecars that may remain from a prior WAL or
        # rollback-journal session. Their contents are superseded by the verified
        # encrypted database.
        for suffix in ("-wal", "-shm", "-journal"):
            path.with_name(path.name + suffix).unlink(missing_ok=True)
