# ReceiptFlow SQLCipher migration

This patch changes ReceiptFlow from standard SQLite to SQLCipher and stores the
256-bit database key in the operating-system credential store using Python
`keyring`.

## What changes

- `security.py` creates/retrieves a random 256-bit database key.
- The key is stored by the OS keyring (macOS Keychain / Windows Credential Locker).
- `db_crypto.py` opens SQLCipher connections and safely migrates existing plaintext SQLite files.
- `database.py` uses SQLCipher for every application connection.
- `backup.py` creates encrypted-to-encrypted SQLCipher snapshots and migrates old plaintext backups.
- `app.py` stops safely if the OS key or encrypted database cannot be opened.
- Settings display the SQLCipher version in use.
- Build scripts collect `keyring` and `sqlcipher3` binaries/submodules for PyInstaller.

## Dependencies

The patch adds:

- `sqlcipher3>=0.6.2`
- `keyring>=25.7.0`

Your normal `run_mac.sh` / `run_windows.bat` will install them from `requirements.txt`.

## First launch migration

1. ReceiptFlow asks the operating system keyring for `ReceiptFlow / database-key-v1`.
2. If no key exists, a cryptographically random 32-byte key is generated and saved to the OS keyring.
3. If the current database starts with the standard `SQLite format 3` plaintext header, ReceiptFlow:
   - leaves the original untouched;
   - creates a temporary SQLCipher database;
   - copies the complete schema/data using `sqlcipher_export()`;
   - validates the encrypted copy;
   - compares the receipt count;
   - atomically swaps the encrypted copy into the original path;
   - validates the final database again;
   - removes the temporary plaintext copy and SQLite sidecar files.
4. Existing plaintext automatic backups are migrated using the same process.
5. Future backups are SQLCipher encrypted from creation.

If validation fails at any point, ReceiptFlow restores/retains the original rather
than overwriting it.

## Important recovery note

The SQLCipher key is intentionally *not* stored in `settings.json`, the project,
the database directory, or the backup directory. That means loss of the operating
system credential store can make encrypted database files unrecoverable.

Before relying on off-machine encrypted backups, store a recovery copy of the key
in an organisation-approved password manager or another controlled secret store.
Do not place a recovery key beside the database or in the ReceiptFlow repository.

## Verify encryption after first launch

### macOS

First check the database path shown in ReceiptFlow Settings. For the default path:

```bash
xxd -l 16 "$HOME/Library/Application Support/ReceiptFlow/data/receipts.db"
```

### Windows PowerShell

For the default path:

```powershell
Format-Hex -Path "$env:LOCALAPPDATA\ReceiptFlow\data\receipts.db" -Count 16
```

An encrypted SQLCipher database should **not** begin with the readable bytes/text:

```text
SQLite format 3
```

Also confirm ReceiptFlow itself opens, displays existing receipts, can add/edit a
test receipt, can move it to Trash/restore it, and creates a new backup.

## Do not delete old external copies yet

If you have historical database copies outside ReceiptFlow's managed backup folder
(for example old OneDrive copies), this patch cannot discover them automatically.
Treat those as plaintext until you have deliberately encrypted or removed them.
