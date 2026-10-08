# Several job types for one service

**Nature of job** now works like **Equipment required**: tick every type of work included in a service. For example, Whole house can include External windows, Internal windows and Screens with one total fee and one hours estimate.

The tick-box grid wraps to the available width and has no internal scroll area. This is used in the service editor, customer usual-service defaults and individual job forms. The whole form can scroll when more room is needed. If no types are available, the form explains that they can be added in Settings.

Selecting a named service when booking carries all its available work types into the job, together with its fee, hours and equipment. Adjust the job's ticks for that visit without changing the saved service. Changing the service later does not replace a saved job's choices. Saved types that are no longer offered remain visible on existing records; new bookings use available choices.

Job history, Jobs and CSV exports show readable comma-separated type names. A custom visit without a named service also shows its types on Home. Selecting several types does not add fees or multiply hours: the service retains one total charge and one hours estimate.

## Install

Close the app, extract `customer-services-update.zip` and merge its matching folders and root files into your existing Shining_Knights project. Keep the package at `src/customer_app`, and launch from the project folder:

```bash
bash run_mac.sh
bash run_tests.sh --run-platform-tests
```

No new dependencies are needed. This package contains source, tests, launch files and the current screens, without customer records or credentials.

On first launch, database versions 1, 2 or 3 upgrade transactionally to version 4. Each old single choice becomes a one-item list; blank choices become empty lists. Labels containing commas remain one whole choice. Customer/service/job IDs, service names, prices, hours, custom answers, equipment and history links remain intact. Interrupted upgrade tests verify rollback of the entire chain. Use the updated app with the upgraded database. Versions 1, 2 and 3 backups remain supported; restore upgrades a private copy while retaining the original backup.

Existing settings keep their labels, required flags, browse preferences and custom questions. The core Nature of job question changes from a single-choice field to several choices automatically. Custom dropdown questions retain their own types.

## Validation

The Linux/offscreen suite passed 384 tests, skipped one opt-in native IPC test and reached 95.48% combined line/branch coverage. Detailed results are in `VALIDATION.json`. The regression suite includes encrypted database and restore tests plus Qt interactions for saving and reopening multiple choices, booking defaults, visit overrides, retired choices, history/CSV output, and wrapped layouts at 520 and 650 pixels. `check_customer_services.py` reproduces previews using disposable synthetic data. Native Mac/Windows testing remains outstanding.

Qt's official checkbox reference: https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QCheckBox.html
