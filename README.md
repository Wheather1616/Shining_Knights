# ShiningKnights: customers, jobs and settings

A PySide6 desktop app for a window-cleaning business, with linked customers/jobs, SQLCipher-encrypted records, customer Service setup, day-grouped jobs, CSV export and plain-language Settings, a minimal Home overview and a streamlined customer workflow with multiple named services per customer. This download contains source code.

## Update an existing project

Close the app, extract `customer-workflow-update.zip` into the project root and replace the included files. Keep the `src/customer_app/` and `tests/` paths intact. Run `bash run_mac.sh` or `run_windows.bat`. See `CUSTOMER_WORKFLOW_UPDATE.md` for the full change list and installation steps. The first launch upgrades version-1 customer databases to version 2 in a transaction, adding separate name fields and optional hours without changing record IDs or job links. Existing full names remain intact. Backups, the virtual environment and credentials stay in their existing locations.

## Fresh setup

Keep the extracted source structure intact. Do not place the complete project inside `src/customer_app` or reuse the ReceiptFlow data folder.

On Mac:

```bash
bash setup_mac.sh
bash run_mac.sh
```

On Windows, run `setup_windows.bat`, then `run_windows.bat`. Setup requires a compatible 64-bit Python installation and access to the dependency packages. Python 3.12 or 3.13 is the tested starting point. The launch scripts use the existing virtual environment rather than reinstalling packages on every launch.

## Home overview

Home shows today’s open jobs, the next seven days including today, and active customers due in that period or overdue without a future open booking. Upcoming visits show the first five jobs; selecting a visit opens its details. Needs a booking shows the first five customers with customer-specific Add job actions, and can show the complete list. A separate notice links to overdue open jobs. Summary cards open the corresponding lists. The date and counts refresh after record changes and when the day changes.

The branded header keeps Home, Customers, Jobs and Settings together, with the active page highlighted in maroon. Alt+H, Alt+C, Alt+J and Alt+S switch pages. Leaving unsaved Settings still offers Save, Discard and Keep editing.

## Workflow

1. Use Settings to manage services, equipment and payment methods. Save changes when finished.
2. Add a customer with separate first/last name inputs and contact/address details. Service setup uses a numeric repeat interval plus days, weeks, months or years; 0 means one-off. Choose an optional service date with the calendar, tick equipment, and enter the total service fee and optional hours. Dropdown choices do not change when the mouse wheel scrolls the form.
3. Add a linked job. It starts with that customer's available choices, fee and hours. Existing jobs retain their recorded amounts, hours and choices when customer defaults change.
4. Record completion and payment status separately. Completion contributes to service history and next-due calculations; it does not automatically create another job.
5. On Jobs, filter and group visits, tick jobs or whole days and export selected or all filtered jobs to CSV.

Customers also have a **Services** tab. Add Indoor windows and Whole house with separate fees and hours, choose a usual service, and select one when booking a job. Saved jobs keep their own service name and visit details. Frequency and payment preferences remain customer-wide. Nature of job is a tick-box grid supporting several types of work within one service. See `CUSTOMER_SERVICES_UPDATE.md` and `MULTIPLE_JOB_TYPES_UPDATE.md` for the workflow and installation details.

Settings provides Services & equipment, Payment methods, Screen layout, Extra information, and Backups & help. Core field types stay protected. Extra questions use automatic stable identifiers; hiding them retains answers. A default payment method applies only to newly added customers. Optional remembered job filters exclude search text.

New records store first and last names independently and retain a combined name for existing lists, job links and exports. Existing full names are not automatically split; the edit form preserves them in the First name input until you separate them. Customer lists start compact, with More detail revealing configured extra fields.

Phone and postcode inputs allow digits only, preserving leading zeroes. Saving checks a 10–15-digit phone number, four-digit Australian postcode and email syntax including `@`. Blank optional contact fields remain allowed. These are format checks, not checks that a phone number or mailbox exists.

The fee remains the agreed total AUD charge. Optional hours accept up to two decimal places and do not multiply the fee or calculate an hourly rate. New jobs snapshot both fee and hours. Old jobs have no hours estimate unless you enter one.

Customer next due is based on the last non-deleted completed visit plus the current interval. For a customer without completed jobs, First / next service date supplies the initial due date. Monthly/yearly intervals clamp to valid calendar dates. Scheduled visits are shown separately.

Customers can be deactivated/reactivated while retaining history. Job Trash hides a job from summaries and supports restoring that individual job.

## Data and recovery

- Windows records: `%LOCALAPPDATA%\ShiningKnights\data\customers.db`.
- Mac records: `~/Library/Application Support/ShiningKnights/data/customers.db`.
- Configuration: `crm-settings.json` in the app support directory.
- Backups: the `backups` folder in the same app support directory.

Records are encrypted with the current OS user's ShiningKnights credential-store key. There is no plaintext record fallback. Settings are stored separately as JSON. This app does not use ReceiptFlow's settings/data location.

Automatic snapshots run at startup, hourly while open, and on shutdown when due. Manual backups are available from Settings; the Home footer links to Backups & help. New backups include a matching settings snapshot. Keep both files together when copying a backup, or copy the entire folder. Retention keeps recent hourly, daily and monthly recovery points.

Settings offers a guided restore with integrity/schema/link validation, backup date and contents, final confirmation, and a safety copy before replacing current records. Older record-only backups keep current settings. Restoring does not change the active database location. Backups from another user/computer need the matching encryption key and a controlled transfer procedure; this release does not transfer keys.

CSV exports contain readable customer information. Store them as business records. The fee is the agreed AUD charge for a visit; the app does not calculate GST, hourly labour, invoice balances or partial-payment amounts. Cloud sync, multi-user access, routing and automatic recurring-job creation are outside this version.

## Tests and builds

Install test dependencies into the existing environment:

```bash
.venv/bin/python -m pip install -r requirements-test.txt
bash run_tests.sh
bash run_tests.sh --run-platform-tests
```

On Windows use `.venv\Scripts\python.exe -m pip install -r requirements-test.txt` and `run_tests.bat`. See `TESTING.md` for coverage, isolation and platform checks.

Latest validation: 384 tests passed, 1 native-platform test skipped, with 95.48% combined line/branch coverage. Detailed results are recorded in `VALIDATION.json`. It covers encrypted database queries and links, multiple-service storage and price snapshots, migration and backup restore, and Qt interactions. Customers, Services and the service editor were checked at normal and minimum supported sizes. Native Mac/Windows testing and packaged app checks remain to be run on those operating systems.

After source verification on the target computer, `bash build_mac.sh` builds `dist/ShiningKnights.app`; `build_windows.bat` builds the Windows output folder. These scripts use `requirements-build.txt`. Copy the complete Windows build folder. Native packaging must be tested on its corresponding OS.
