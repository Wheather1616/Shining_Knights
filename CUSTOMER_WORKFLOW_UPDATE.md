# Customer layout and input workflow update

## Install

1. Close ShiningKnights. In Settings, you can use Back up now before closing if you want a fresh recovery point.
2. Extract `customer-workflow-update.zip` into the project root and merge its folders, replacing matching files. Preserve the paths `src/customer_app/`, `tests/` and `scripts/`. This archive includes the complete application source and tests, including Home, Jobs and Settings.
3. Run `bash run_mac.sh` on Mac, or `run_windows.bat` on Windows. There are no new dependencies.
4. Run `bash run_tests.sh --run-platform-tests` on Mac, or `run_tests.bat --run-platform-tests` on Windows.

The application automatically adds separate first/last name columns and optional customer/job hours when it opens a version-1 customer database. The transaction keeps customer IDs, linked jobs, fees, custom answers and inherited receipt tables intact. A failed migration rolls back. Once upgraded, use this app version or newer; older code does not understand database version 2. Old encrypted backups remain supported: restore upgrades a staged copy and keeps the original backup unchanged, with the existing safety-copy process.

`src.zip` contains only the updated source folder. The workflow update archive also supplies the new tests, migration fixture, preview script and this guide. The complete `customer_app(2).zip` contains the full project including setup/build scripts. These downloads contain source code, not native application builds.

## Page changes

- Compact three-line customer cards with readable dark names and light cyan selection. More detail reveals your configured extra fields; Compact list returns to the shorter view.
- Softer cards, clearer spacing and a profile divider between contact details and service summary.
- Jobs, Service setup and Notes use understated underline tabs.
- Job history uses lighter row separators and labelled status/payment badges. Edit selected job and Add job remain above the table so the layout fits the minimum window size.

## Form behaviour

| Request | Implemented behaviour |
| --- | --- |
| Flexible service frequency | Number box plus days/weeks/months/years dropdown. 0 is one-off; a repeat interval can be 1–3650. One-off is stored using the existing null-interval convention. |
| First and last names | Separate inputs and database columns; lists and exports retain the combined name. First name is required; last name can be blank for a person with one name. Existing full names stay intact and appear in First name until you split them yourself. |
| Phone | Digits-only form input. Saving checks 10–15 digits; blanks are allowed. Existing formatted numbers are presented as digits when editing. |
| Email | Saving checks email syntax including one `@` and a domain. Blanks are allowed. |
| State / territory | Dropdown ignores wheel events. Explicit clicks and keyboard selection remain available. |
| Postcode | Digits-only input and four-digit save check. Leading zeroes are preserved. |
| First / next service date | Editable date with a dropdown calendar, clear button and Alt+Down shortcut. A blank date stays blank. |
| Equipment | All configured options shown as a wrapping tick-box grid without an internal scrollbar. Previously saved choices remain available when editing. The whole form still scrolls. |
| Fee and hours | Numeric fee input beside optional Number of hours. Both allow at most two decimal places. Fee is the total charge and is not multiplied by hours. New jobs copy fee and hours; existing jobs retain their saved values. |
| Payment method | Click-operated dropdown ignores wheel events. Existing saved choices remain available when editing. |

Contact validation checks formatting rather than whether a number or mailbox exists. Numbers saved through older APIs can retain their formatting until edited in this form. New form entries contain digits only.

## Verification

43 new regression cases cover separate names, duplicate names, job links, hours snapshots, numeric typing, leading zeroes, save errors, repeat units and one-offs, actual calendar interaction, explicit dropdown choices, wheel events, equipment grids, CSV columns, compact/detailed directory selection and page geometry. Encrypted database cases verify version-1 migration, rollback, preservation of inherited records and restore of old backups without modifying the originals.

The full Linux/offscreen run passed 314 tests, skipped the opt-in native IPC case and reached 95.30% combined line/branch coverage. Native Mac/Windows rendering and packaging must still be checked on those operating systems. `VALIDATION.json` records the detailed result.

Preview synthetic layouts on Mac with:

```bash
PYTHONPATH=src .venv/bin/python check_customer_layout.py
PYTHONPATH=src .venv/bin/python check_customer_inputs.py
```

These preview scripts use temporary encrypted files and do not add records to your real database.

## Implementation sources

Native text validation and calendar controls follow the official Qt for Python documentation:

- https://doc.qt.io/qtforpython-6/PySide6/QtGui/QRegularExpressionValidator.html
- https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QCalendarWidget.html
- https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QComboBox.html
