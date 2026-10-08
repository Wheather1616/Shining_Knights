# Customer screen update

This documents the earlier Customers redesign. For the current combined UI
update, follow `JOBS_PAGE_UPDATE.md`, which also installs the new Jobs arrow asset.

The Customers page now uses a compact directory on the left and the selected
customer's overview and linked jobs on the right. Search, inactive filtering,
customer selection, edits and CSV export continue to use the existing database.

## Install into Shining_Knights

1. Quit ShiningKnights and extract this archive outside your project.
2. Copy the contents of `src/customer_app/ui` into your project's matching
   `src/customer_app/ui` folder, merging directories and replacing matching files.
   Include the new `customer_page.py` and `styles/customers.py`. Do not put the
   archive itself, or its `src` folder, inside your existing `customer_app` folder.
3. Copy the archive's `tests` folder into the project root, merging and replacing
   matching files. The existing workflow tests are updated for the new activation
   controls, and `tests/ui/test_customer_page.py` adds ten regression cases.
4. From the project root, run:

   ```bash
   bash run_tests.sh --run-platform-tests
   bash run_mac.sh
   ```

No dependency installation or database migration is required for this screen
update. The existing production database, settings and credential store are
used as before. The archive includes the complete source and test harness for
reference; applying this update only requires the UI and tests folders above.

## Behaviour

- Directory entries display name, suburb, frequency, next due date and non-empty
  custom fields marked for browsing. Tooltips include configured browse values.
- Search and inactive filtering update the directory count and CSV export.
- Selection uses customer IDs and survives refreshes while that customer remains
  in the filtered results. No match clears the selected workspace and its actions.
- The overview shows contact details, active status, completed-job count, last
  completion and next due date. Due and scheduled dates remain separate.
- Jobs is the default detail tab. Add job preselects the customer. Editing uses
  the selected linked job, either from its toolbar button or a double-click.
- Job headers are shortened only for the default labels; customised labels and
  configured additional columns are retained. Fees align right, and narrow views
  scroll horizontally instead of squeezing columns. Both service dates remain
  available as separate configured columns.
- Service setup includes all other enabled customer fields, including custom
  fields. Its activation action changes label with the customer's current state.
- Inactive customers retain their history and can be edited and reactivated;
  their Add job button is disabled.
- Notes are plain text, selectable and scrollable. Edit customer changes them.
- Existing cream, bordeaux and cyan styling is retained. Idiqlat remains for
  branded headings; records use a regular system font. The shared body-font token
  also improves record and form typography elsewhere in the app.
- The divider is adjustable. The window minimum is 900 × 690 pixels; the overview
  is bounded and can scroll for unusually long contact data, leaving room for the
  job table. Edit selected job sits beside Add job to preserve vertical space.

## Validation

The full suite passed on Linux / Python 3.12.14 / Qt offscreen: **167 passed,
1 skipped**, with **93.49% combined statement and branch coverage**. The native
IPC test skipped because this execution host denied Unix sockets with EPERM.
The new customer-page module's measured statements and branches were exercised.

The theme now resolves generic or missing system font names to a concrete,
available font family before applying the application font. This addresses the
macOS offscreen warning about missing "Sans Serif" without ignoring warnings.
Nine additional cases check generic defaults with macOS, Windows and Linux font
inventories, private and missing defaults, unknown installed fallbacks, case
matching, an unusable inventory and repeated theme application with text rendering.
The macOS failure was reported by the user; this fix has not been rerun on macOS.

The ten new cases cover duplicate-name customers, ID-linked histories, preserved
selection, empty/search states, inactive reactivation, custom fields, Notes,
linked-job editing, configured job headers, filtered export, long content at two
window sizes, primary-button contrast and visible summary values.

Actual rendered screenshots were inspected at 1250 × 820 and 900 × 690 pixels,
plus Service setup and Notes states. Preview images use synthetic data and are
included under `preview/`. Test reports are under `validation_reports/`.

Relevant Qt documentation:
- [QSplitter](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QSplitter.html)
- [QScrollArea](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QScrollArea.html)
- [QFontDatabase](https://doc.qt.io/qt-6/qfontdatabase.html)

Potential bias: these checks use offscreen Linux rendering. Native macOS and
Windows fonts, scaling and packaged applications still need visual verification.
