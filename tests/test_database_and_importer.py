from pathlib import Path

from receipt_app.config import DEFAULT_FIELDS
from receipt_app.database import ReceiptDatabase, ReceiptRecord
from receipt_app.importer import import_csv, normalise_amount, normalise_date


def test_manual_receipt_can_be_stored_and_found(tmp_path: Path):
    db = ReceiptDatabase(tmp_path / "receipts.db")
    db.upsert_receipt(
        ReceiptRecord(
            receipt_no="R-100",
            transaction_date="2026-05-16",
            name="Ava Smith",
            amount=42.5,
            payment_type="Card",
            member_no="M-001",
            notes="Searchable note",
            custom_fields={"category": "Dining"},
        )
    )

    rows = db.search("Ava")
    assert len(rows) == 1
    assert rows[0]["receipt_no"] == "R-100"


def test_csv_import_maps_common_headers(tmp_path: Path):
    csv_path = tmp_path / "receipts.csv"
    csv_path.write_text(
        "Receipt No,Date,Name / Customer,Amount,Payment Type,Member No,Notes\n"
        "R-200,16/05/2026,Noah Chen,$18.50,Cash,M-002,Coffee\n",
        encoding="utf-8",
    )
    db = ReceiptDatabase(tmp_path / "receipts.db")

    result = import_csv(csv_path, db, list(DEFAULT_FIELDS))

    assert result.imported == 1
    rows = db.search("Noah")
    assert len(rows) == 1
    assert rows[0]["amount"] == 18.5


def test_normalisers():
    assert normalise_amount("$1,234.50") == 1234.50
    assert normalise_date("16/05/2026") == "2026-05-16"


def test_receipts_for_date_only_returns_matching_day(tmp_path: Path):
    db = ReceiptDatabase(tmp_path / "receipts.db")
    db.upsert_receipt(ReceiptRecord(receipt_no="TODAY", transaction_date="2026-05-17", name="Today", amount=10.0))
    db.upsert_receipt(ReceiptRecord(receipt_no="OLD", transaction_date="2026-05-16", name="Old", amount=5.0))

    rows = db.receipts_for_date("2026-05-17")

    assert len(rows) == 1
    assert rows[0]["receipt_no"] == "TODAY"
