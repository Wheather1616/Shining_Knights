# Settings update

## Install in your existing Shining_Knights project

1. Close ShiningKnights and keep a copy of your project folder.
2. Extract `settings-update.zip` into the project root, the folder containing `run_mac.sh`. Allow the included files to replace their previous versions. Keep the `src/customer_app/` and `tests/` paths intact.
3. Run `bash run_mac.sh` on Mac, or `run_windows.bat` on Windows.
4. Run `bash run_tests.sh --run-platform-tests` on Mac to include your native IPC check. The existing virtual environment and test dependencies can be reused.

This source update includes backend configuration and recovery modules as well as UI changes. Copy the complete patch, rather than only `field_settings.py`. No customer database, backup, credential or saved user settings is included or overwritten by extracting the patch.

## Implemented sections

- Services & equipment: individual choices, add/edit, Stop using and Use again. Taking a choice out of use keeps recorded values and excludes it from new choices.
- Payment methods: manageable choices and an optional default for new customers. Existing customers keep their own payment method.
- Screen layout: selectable customer details and job columns, a preview, editable labels, protected identifying information, starting jobs grouping and optional remembered filters. Remembered filters include status, date range and grouping; search text is not stored.
- Extra information: guided questions with readable answer types, optional required/list settings, automatically generated stable identifiers and editable choice lists. Existing question types remain fixed. Switching a question off keeps its recorded answers.
- Backups & help: last backup date, Back up now, Open backup folder, short help and a reviewed restore with a separate final confirmation.

Save changes is enabled only when the draft differs from saved settings. A successful save displays Changes saved inline. Leaving Settings or closing the window with a draft offers Save, Discard or Keep editing. Moving between Settings sections keeps the same draft.

Visit frequency, standard charges and usual equipment remain in the customer Service setup. If you stop using or rename a choice used by a customer's defaults, review that Service setup. New jobs leave unavailable choices blank; existing records keep them.

## Backups and restore

New encrypted `.db` backups have a matching `.settings.json` snapshot. Keep the pair together, or copy the whole backup folder when making an external spare copy. Settings snapshots contain the same configuration held in the normal settings file; customer and job records remain encrypted.

Restore verifies encryption/integrity, CRM schema, required columns and customer/job links. It shows the backup date, record counts and whether settings are included. A final confirmation is required. Before replacement, it creates a safety backup of current records and settings. A selected backup that changes after review is rejected. Write failures roll back records and settings, and an interrupted replacement is rolled back at next startup.

Older backups without a matching settings snapshot restore records while retaining current settings. The active database location is retained during restore. Backups require this app's matching OS-stored encryption key; moving data to another computer still requires a separate key-transfer procedure.

## Validation

The complete suite passed on Linux, Python 3.12.14 and Qt 6.11.2 offscreen: 243 passed, 1 native IPC test skipped. Combined line/branch coverage is recorded in `VALIDATION.json`. The patch adds 58 cases for preferences, Settings workflows and actual encrypted recovery, and updates the previous Settings UI tests.

All five sections were rendered at 1250 × 820 and 900 × 690. Navigation and Save remain visible; longer sections scroll. Native Mac/Windows builds, OS credential-store integration and the opt-in native IPC test still need the target-machine check.
