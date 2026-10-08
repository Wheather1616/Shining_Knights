# Inside, Outside or Both for each type of work

In **Add service** and **Edit service**, tick a Nature of job option to reveal its rounded **Inside / Outside / Both** selector directly below. Each type of work has an independent choice. The chosen button is maroon with white text. Unticking a type hides its selector and omits its side when saving. Reticking before saving remembers the current form's choice.

Customer usual-service defaults and individual job forms use the same control. Choosing a saved service for a new job carries its work types and sides, fee, hours and equipment into that visit. You can change a visit's sides independently. Switching services replaces the side choices together with the service defaults, while retaining unfinished date input, payment choices and custom answers. Editing a saved service does not change an existing job's snapshot.

History, Jobs and CSV exports show the side beside each work type, for example `Screens (Both), Skylights (Outside)`. Home uses these descriptions for custom visits without a named service. Prices remain total fees; choosing sides never changes fees or multiplies hours.

Existing records have no side assigned automatically. Their selectors open with all three buttons unselected until you confirm the scope. Saving an unchanged old service keeps its scope unset. The database accepts only Inside, Outside or Both for work types that are actually selected. Saved types removed from Settings retain their historical sides; new bookings filter out unavailable types.

## Install

Close the app, extract `customer-services-update.zip`, and merge its matching `src`, `tests` and root files into your existing Shining_Knights project. Keep the application at `src/customer_app`. No additional dependencies are needed. Launch and test from the project folder:

```bash
bash run_mac.sh
bash run_tests.sh --run-platform-tests
```

This package contains code, tests and launch files. It contains no customer database, credentials or virtual environment. If using the source-only `customer_app(4).zip`, merge its `customer_app` folder into your existing project's `src` folder.

On first launch, database versions 1 to 4 upgrade transactionally to version 5. New side fields are empty mappings. Customer, service and job IDs, links, names, charges, hours, existing choices and historical snapshots remain unchanged. Interrupted upgrades roll back the entire migration chain. Use this updated application with the upgraded database. Backups from versions 1 to 4 remain supported; restore upgrades a private copy, retaining the source backup.

## Validation

The complete suite passed 413 tests, skipped one opt-in native IPC test and reached 95.58% combined line/branch coverage. `VALIDATION.json` records the result. New regressions cover conditional visibility, independent exclusive choices, keyboard activation, save/reopen, unticking, booking overrides, service switching, customer/default synchronisation, fee/hour preservation, retired choices, readable exports, narrow and wide form geometry, encrypted storage, upgrades from versions 1 to 4, interrupted migration rollback, old/current backup recovery and rejection of damaged side data before replacing live records. The complete existing suite is also run.

`check_customer_services.py` renders the workflow with disposable synthetic records and selected side controls. Native Mac/Windows appearance and packaging have not been executed on this Linux host.

The selector uses Qt's exclusive button groups: https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QButtonGroup.html
