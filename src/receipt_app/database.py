from __future__ import annotations

import json
from sqlcipher3 import dbapi2 as sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .config import CORE_FIELD_KEYS, FieldDefinition
from .db_crypto import (
    is_plaintext_sqlite,
    migrate_plaintext_database,
    open_encrypted_connection,
    verify_encrypted_database,
)
from .security import SecureKeyStore

SORT_OPTIONS: dict[str, str] = {
    "Newest first": "transaction_date DESC, id DESC",
    "Oldest first": "transaction_date ASC, id ASC",
    "Name A-Z": "LOWER(name) ASC, transaction_date DESC",
    "Name Z-A": "LOWER(name) DESC, transaction_date DESC",
    "Amount low-high": "amount ASC, transaction_date DESC",
    "Amount high-low": "amount DESC, transaction_date DESC",
    "Receipt No": "receipt_no ASC, transaction_date DESC",
}


@dataclass
class ReceiptRecord:
    receipt_no: str = ""
    transaction_date: str = ""
    name: str = ""
    amount: float | None = None
    payment_type: str = ""
    member_no: str = ""
    notes: str = ""
    custom_fields: dict[str, Any] | None = None
    source: str = "manual"

    def normalised_search_text(self) -> str:
        parts = [
            self.receipt_no,
            self.transaction_date,
            self.name,
            str(self.amount if self.amount is not None else ""),
            self.payment_type,
            self.member_no,
            self.notes,
            self.source,
        ]
        if self.custom_fields:
            parts.extend(str(value) for value in self.custom_fields.values())
        return " ".join(part for part in parts if part).lower()


class ReceiptDatabase:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # The key exists only in the OS credential store and process memory.
        self.key_hex = SecureKeyStore().get_or_create_database_key()

        # Existing ReceiptFlow installations used plaintext SQLite. Migrate them
        # once, only after an encrypted copy has been created and verified.
        if self.db_path.exists() and self.db_path.stat().st_size > 0:
            if is_plaintext_sqlite(self.db_path):
                migrate_plaintext_database(self.db_path, self.key_hex)
            else:
                verify_encrypted_database(self.db_path, self.key_hex)

        self.initialise()
        if __import__("os").name == "posix":
            try:
                self.db_path.chmod(0o600)
            except OSError:
                pass

    def connect(self) -> sqlite3.Connection:
        return open_encrypted_connection(self.db_path, self.key_hex, validate=True)

    def cipher_version(self) -> str:
        with self.connect() as conn:
            row = conn.execute("PRAGMA cipher_version").fetchone()
            return str(row[0]) if row and row[0] else "unknown"

    def initialise(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS receipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    receipt_no TEXT,
                    transaction_date TEXT,
                    name TEXT,
                    amount REAL,
                    payment_type TEXT,
                    member_no TEXT,
                    notes TEXT,
                    custom_fields TEXT NOT NULL DEFAULT '{}',
                    source TEXT NOT NULL DEFAULT 'manual',
                    search_text TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_receipts_date ON receipts(transaction_date);
                CREATE INDEX IF NOT EXISTS idx_receipts_name ON receipts(name);
                CREATE INDEX IF NOT EXISTS idx_receipts_amount ON receipts(amount);
                CREATE INDEX IF NOT EXISTS idx_receipts_receipt_no ON receipts(receipt_no);
                CREATE INDEX IF NOT EXISTS idx_receipts_member_no ON receipts(member_no);
                """
            )
            self._ensure_column(conn, "receipts", "deleted_at", "TEXT")
            self._ensure_column(conn, "receipts", "deleted_reason", "TEXT")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_receipts_deleted_at ON receipts(deleted_at)"
            )
            self._initialise_fts(conn)
            conn.commit()

    def _ensure_column(
        self,
        conn: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        existing = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _initialise_fts(self, conn: sqlite3.Connection) -> None:
        try:
            conn.executescript(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS receipts_fts USING fts5(
                    receipt_no,
                    transaction_date,
                    name,
                    amount,
                    payment_type,
                    member_no,
                    notes,
                    custom_fields,
                    source,
                    content='receipts',
                    content_rowid='id'
                );

                CREATE TRIGGER IF NOT EXISTS receipts_ai AFTER INSERT ON receipts BEGIN
                    INSERT INTO receipts_fts(rowid, receipt_no, transaction_date, name, amount, payment_type, member_no, notes, custom_fields, source)
                    VALUES (new.id, new.receipt_no, new.transaction_date, new.name, new.amount, new.payment_type, new.member_no, new.notes, new.custom_fields, new.source);
                END;

                CREATE TRIGGER IF NOT EXISTS receipts_ad AFTER DELETE ON receipts BEGIN
                    INSERT INTO receipts_fts(receipts_fts, rowid, receipt_no, transaction_date, name, amount, payment_type, member_no, notes, custom_fields, source)
                    VALUES('delete', old.id, old.receipt_no, old.transaction_date, old.name, old.amount, old.payment_type, old.member_no, old.notes, old.custom_fields, old.source);
                END;

                CREATE TRIGGER IF NOT EXISTS receipts_au AFTER UPDATE ON receipts BEGIN
                    INSERT INTO receipts_fts(receipts_fts, rowid, receipt_no, transaction_date, name, amount, payment_type, member_no, notes, custom_fields, source)
                    VALUES('delete', old.id, old.receipt_no, old.transaction_date, old.name, old.amount, old.payment_type, old.member_no, old.notes, old.custom_fields, old.source);
                    INSERT INTO receipts_fts(rowid, receipt_no, transaction_date, name, amount, payment_type, member_no, notes, custom_fields, source)
                    VALUES (new.id, new.receipt_no, new.transaction_date, new.name, new.amount, new.payment_type, new.member_no, new.notes, new.custom_fields, new.source);
                END;
                """
            )
        except sqlite3.OperationalError:
            # Some Python/SQLite builds may not include FTS5. The app still works using LIKE fallback.
            pass

    def upsert_receipt(self, record: ReceiptRecord) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        custom_fields = record.custom_fields or {}
        search_text = record.normalised_search_text()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO receipts (
                    receipt_no, transaction_date, name, amount, payment_type, member_no, notes,
                    custom_fields, source, search_text, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.receipt_no,
                    record.transaction_date,
                    record.name,
                    record.amount,
                    record.payment_type,
                    record.member_no,
                    record.notes,
                    json.dumps(custom_fields, ensure_ascii=False),
                    record.source,
                    search_text,
                    now,
                    now,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def get_receipt(self, receipt_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM receipts WHERE id = ?", (receipt_id,)).fetchone()

    def update_receipt(self, receipt_id: int, record: ReceiptRecord) -> bool:
        now = datetime.now().isoformat(timespec="seconds")
        custom_fields = record.custom_fields or {}
        search_text = record.normalised_search_text()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE receipts
                SET receipt_no = ?,
                    transaction_date = ?,
                    name = ?,
                    amount = ?,
                    payment_type = ?,
                    member_no = ?,
                    notes = ?,
                    custom_fields = ?,
                    source = ?,
                    search_text = ?,
                    updated_at = ?
                WHERE id = ?
                  AND deleted_at IS NULL
                """,
                (
                    record.receipt_no,
                    record.transaction_date,
                    record.name,
                    record.amount,
                    record.payment_type,
                    record.member_no,
                    record.notes,
                    json.dumps(custom_fields, ensure_ascii=False),
                    record.source,
                    search_text,
                    now,
                    receipt_id,
                ),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_receipt(self, receipt_id: int) -> bool:
        now = datetime.now().isoformat(timespec="seconds")

        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE receipts
                SET deleted_at = ?,
                    updated_at = ?
                WHERE id = ?
                AND deleted_at IS NULL
                """,
                (now, now, receipt_id),
            )

            conn.commit()
            return cursor.rowcount > 0

    def restore_receipt(self, receipt_id: int) -> bool:
        now = datetime.now().isoformat(timespec="seconds")

        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE receipts
                SET deleted_at = NULL,
                    deleted_reason = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (now, receipt_id),
            )

            conn.commit()
            return cursor.rowcount > 0
    
    def search(
        self,
        query: str = "",
        sort: str = "Newest first",
        limit: int = 500,
    ) -> list[sqlite3.Row]:
        """Search active (non-trashed) receipts only."""
        order_by = SORT_OPTIONS.get(sort, SORT_OPTIONS["Newest first"])
        query = query.strip()

        with self.connect() as conn:
            if query:
                try:
                    fts_query = self._to_fts_query(query)
                    return conn.execute(
                        f"""
                        SELECT receipts.*
                        FROM receipts_fts
                        JOIN receipts ON receipts_fts.rowid = receipts.id
                        WHERE receipts_fts MATCH ?
                          AND receipts.deleted_at IS NULL
                        ORDER BY {order_by}
                        LIMIT ?
                        """,
                        (fts_query, limit),
                    ).fetchall()
                except sqlite3.OperationalError:
                    like = f"%{query.lower()}%"
                    return conn.execute(
                        f"""
                        SELECT *
                        FROM receipts
                        WHERE deleted_at IS NULL
                          AND LOWER(search_text) LIKE ?
                        ORDER BY {order_by}
                        LIMIT ?
                        """,
                        (like, limit),
                    ).fetchall()

            return conn.execute(
                f"""
                SELECT *
                FROM receipts
                WHERE deleted_at IS NULL
                ORDER BY {order_by}
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def trashed_receipts(self, limit: int = 500) -> list[sqlite3.Row]:
        """Return soft-deleted receipts, newest deletion first."""
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT *
                FROM receipts
                WHERE deleted_at IS NOT NULL
                ORDER BY deleted_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def _to_fts_query(self, query: str) -> str:
        tokens = [token.strip('"*:()') for token in query.split() if token.strip('"*:()')]
        if not tokens:
            return '""'
        return " AND ".join(f'{token}*' for token in tokens)


    def receipts_for_date(self, transaction_date: str, limit: int = 50) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT *
                FROM receipts
                WHERE transaction_date = ?
                  AND deleted_at IS NULL
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (transaction_date, limit),
            ).fetchall()

    def export_rows(self, rows: Iterable[sqlite3.Row], path: Path, fields: list[FieldDefinition]) -> None:
        import csv

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        core_labels = [field_def.label for field_def in fields if field_def.browse_column]
        core_keys = [field_def.key for field_def in fields if field_def.browse_column]
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(core_labels + ["Source", "Created At"])
            for row in rows:
                custom = json.loads(row["custom_fields"] or "{}")
                values = []
                for key in core_keys:
                    if key in CORE_FIELD_KEYS:
                        values.append(row[key])
                    else:
                        values.append(custom.get(key, ""))
                writer.writerow(values + [row["source"], row["created_at"]])

    def grouped_by_date(self, rows: Iterable[sqlite3.Row]) -> dict[str, list[sqlite3.Row]]:
        grouped: dict[str, list[sqlite3.Row]] = {}
        for row in rows:
            key = row["transaction_date"] or "No date"
            grouped.setdefault(key, []).append(row)
        return grouped

    def rebuild_search_index(self) -> None:
        with self.connect() as conn:
            try:
                conn.execute("INSERT INTO receipts_fts(receipts_fts) VALUES('rebuild')")
            except sqlite3.OperationalError:
                pass
            conn.commit()
