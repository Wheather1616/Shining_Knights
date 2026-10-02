# ShiningKnights: customers and jobs, V1

A functional desktop customer/job application adapted from the uploaded ReceiptFlow package. This version implements the database and field configuration, with simple usable screens. It is source code, not a compiled Windows installer or Mac application bundle.

## Run on Windows

Use a new folder for this version. Do not extract it over your live ReceiptFlow installation or reuse its virtual environment.

1. Extract this ZIP into a new folder, for example `C:\Apps\ShiningKnights-V1`.
2. Use a supported 64-bit Python installation. Python 3.12 or 3.13 is a suitable starting point.
3. Run `setup_windows.bat` once. It creates an isolated `.venv` and installs dependencies. Internet access is required for setup.
4. Run `run_windows.bat` to open the application.

If Windows does not recognise `py`, install Python with the Windows Python launcher, or create the virtual environment with your installed Python executable. If pip reports that a dependency has no compatible wheel, check the Python version, CPU architecture and operating-system compatibility. The setup uses binary wheels rather than attempting to compile SQLCipher.

## Run on Mac

Extract into a new folder, open Terminal in that folder, then run:

```bash
bash setup_mac.sh
bash run_mac.sh
```

A compatible Python 3 installation and operating system supported by PySide6 are required. The encryption key is kept in macOS Keychain. Allow access when prompted.

## Try the workflow

1. Open **Field settings > Choices**, edit equipment, nature-of-job and payment-method lists, then **Save configuration**.
2. Open **Customers > Add customer**. Enter name, contact details, full address, service frequency, equipment, fee and usual payment method. Customer name is initially the only compulsory customer field.
3. Select the customer, then **Add job for customer**. Service type, equipment, fee and payment method prefill from the customer. Enter the actual job date and adjust its details if needed.
4. Mark a job completed. The completed date defaults to today when selecting Completed in the job form; you can change it for a historical visit. Payment status is separate and remains Unpaid until you change it.
5. View job history beneath the customer. Open **Jobs**, then group by customer, date or status. Double-click a job to edit it.

Changing a customer's defaults affects future jobs. Existing jobs retain their saved fee, equipment, service type and payment method. Jobs completed and last completed date are calculated from non-deleted completed jobs.

## Field configuration

**Customers** and **Jobs** have separate field definitions. Each supports labels, required flags and list-column flags. Core types and structural status choices are fixed. Optional core fields can be made compulsory.

Use **Add custom field** for text, notes, numbers, currency, dates, dropdowns, equipment-style multiple selections or booleans. Dropdown and multiple-selection choices use one line per option. Custom keys are permanent identifiers, for example `gate_code`; labels can change. Types cannot be changed after creation through the interface. Do not change an existing field's key or type by manually editing settings.

Disable a custom field to hide it, keeping historical values. Clear its Required checkbox before disabling it. Making a field required does not rewrite old records; the value must be supplied the next time that record is saved.

Removed choices remain visible on existing records as saved choices. Existing unchanged values can still be saved. New records need currently configured choices; update any affected customer defaults before creating their next job.

## Recurrence

Presets: monthly; every 6, 8, 10 or 12 weeks; quarterly; six-monthly; annual; one-off/as needed. **Other interval** supports a whole-number interval in days, weeks, months or years.

Next due is the last completed visit plus the customer's current interval. For a customer without completed jobs, **First / next service date** provides the initial due date. An already scheduled job is shown separately and does not rewrite the calculated due date. Completion does not automatically create another job. Month/year arithmetic clamps to the last valid calendar day, e.g. 31 January plus one month becomes 28 February in a non-leap year. The next cycle is based on the actual completion date.

## Storage and recovery

- Windows database: `%LOCALAPPDATA%\ShiningKnights\data\customers.db`
- Mac database: `~/Library/Application Support/ShiningKnights/data/customers.db`
- Field configuration: `crm-settings.json` in the corresponding ShiningKnights application-data directory.
- Encrypted automatic snapshots: `backups` beneath that directory, on launch, hourly while running, and on close when due. **Back up now** creates a snapshot immediately. The inherited retention policy keeps recent hourly, daily and monthly recovery points.
- Customers are deactivated rather than deleted. Existing jobs and history remain available. Reactivate them using Include inactive.
- Jobs moved to Trash are excluded from summaries and can be restored through the Trash filter.

The encryption key is in the current OS user's credential store, using the separate ShiningKnights service. There is no plaintext database fallback. A database or backup copied to another user/computer will require the matching key and a controlled recovery procedure. This release does not provide a key-transfer or restore wizard. Preserve the OS credential-store entry alongside recovery planning; a database backup alone is not sufficient for moving computers.

Database backups do not include `crm-settings.json`. Preserve that file separately to retain field definitions. CSV exports are unencrypted and contain customer details, so store them appropriately.

The new package does not read ReceiptFlow's settings or data locations. If a database at the ShiningKnights path contains only an inherited `receipts` table, it is retained untouched while new customer/job tables are added. Receipts are not automatically converted into customers. Unrecognised existing customer/job schemas stop startup rather than being silently replaced. Existing plaintext SQLite files are encrypted using the inherited verified migration process before use.

## What changed

- Replaced receipt schema and API with `CustomerDatabase`, `CustomerRecord` and `JobRecord`.
- Added linked customer/job tables, version tracking, foreign keys, validation and exact whole-cent amounts.
- Replaced receipt field settings with independent customer/job configuration and lookup lists.
- Added customer profiles, job forms, grouped job views, derived service summaries, CSV exports and job Trash.
- Retained encryption, OS key storage, single-instance control, platform data paths and encrypted backup infrastructure.
- Removed receipt-only screens and workflow modules from this customer package.
- Added launch/setup scripts and automated data/UI tests.

The charge field stores the agreed AUD fee for a visit. This version does not calculate hourly labour, GST, invoices, accounting balances or partial-payment amounts. It does not include cloud sync, mobile access, multiple users, routing, reminders or automatic recurring-job creation.

## Validation

38 automated tests passed on Linux using Python 3.12, PySide6 6.11.2, sqlcipher3 0.6.2 and keyring 25.7.0. Tests use real SQLCipher encrypted files and explicit temporary keys, plus offscreen Qt forms. They cover foreign keys, fee snapshots, custom fields, recurrence, archive/restore, search, wrong-key refusal, encrypted backups and preserved inherited receipt tables. Windows/Mac native launch and credential-store access still need testing on the target computers.

Developer command, from this folder:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

## Technical references

- SQLite foreign keys: https://sqlite.org/foreignkeys.html
- SQLite floating-point limitations: https://sqlite.org/floatingpoint.html
- SQLCipher Python driver: https://github.com/coleifer/sqlcipher3
