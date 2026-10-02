from pathlib import Path

from customer_app.config import DEFAULT_FIELDS
from customer_app.database import ReceiptDatabase, ReceiptRecord


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




def test_receipts_for_date_only_returns_matching_day(tmp_path: Path):
    db = ReceiptDatabase(tmp_path / "receipts.db")
    db.upsert_receipt(ReceiptRecord(receipt_no="TODAY", transaction_date="2026-05-17", name="Today", amount=10.0))
    db.upsert_receipt(ReceiptRecord(receipt_no="OLD", transaction_date="2026-05-16", name="Old", amount=5.0))

    rows = db.receipts_for_date("2026-05-17")

    assert len(rows) == 1
    assert rows[0]["receipt_no"] == "TODAY"
