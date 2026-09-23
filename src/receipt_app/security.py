from __future__ import annotations

import re
import secrets

import keyring
from keyring.errors import KeyringError

SERVICE_NAME = "ReceiptFlow"
DATABASE_KEY_ACCOUNT = "database-key-v1"
_KEY_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class SecureKeyStoreError(RuntimeError):
    """Raised when ReceiptFlow cannot safely read or write its database key."""


class SecureKeyStore:
    """Store ReceiptFlow secrets in the operating system credential store.

    keyring maps to macOS Keychain on macOS and Windows Credential Locker on
    Windows. ReceiptFlow deliberately has no plaintext-file fallback.
    """

    def get_or_create_database_key(self) -> str:
        try:
            existing = keyring.get_password(SERVICE_NAME, DATABASE_KEY_ACCOUNT)
        except KeyringError as exc:
            raise SecureKeyStoreError(
                "ReceiptFlow could not access the operating system credential store. "
                "The database key will not be stored in a file as a fallback."
            ) from exc

        if existing:
            self._validate_key(existing)
            return existing.lower()

        key_hex = secrets.token_hex(32)  # 256-bit random raw SQLCipher key.

        try:
            keyring.set_password(SERVICE_NAME, DATABASE_KEY_ACCOUNT, key_hex)
            round_trip = keyring.get_password(SERVICE_NAME, DATABASE_KEY_ACCOUNT)
        except KeyringError as exc:
            raise SecureKeyStoreError(
                "ReceiptFlow could not store its encryption key in the operating "
                "system credential store. No database migration was performed."
            ) from exc

        if round_trip != key_hex:
            raise SecureKeyStoreError(
                "ReceiptFlow could not verify the encryption key after storing it "
                "in the operating system credential store."
            )

        return key_hex

    @staticmethod
    def _validate_key(key_hex: str) -> None:
        if not _KEY_RE.fullmatch(key_hex):
            raise SecureKeyStoreError(
                "The ReceiptFlow database key stored by the operating system has an "
                "unexpected format. Refusing to open the database to avoid data loss."
            )

    @staticmethod
    def backend_name() -> str:
        try:
            backend = keyring.get_keyring()
            return f"{backend.__class__.__module__}.{backend.__class__.__name__}"
        except Exception:
            return "unknown"
