# Jobs page update

This update builds on the uploaded Customers UI and the macOS font fix. It adds
a Jobs workspace with distinctive maroon filter dropdowns, independent checkbox
selection for CSV export, collapsible day groups and a selected-job details card.

## Install

1. Quit ShiningKnights. Extract `jobs-page-update.zip` outside your project.
2. Merge the archive's `src` directory into your project root, replacing matching
   files. Include the new `ui/jobs_page.py`, `ui/styles/jobs.py` and
   `assets/theme/chevron-down-white.svg`. The arrow asset is required by the new
   style token. These paths are beneath `src/customer_app`.
3. Merge the archive's `tests` directory into your project root, replacing matching
   files. It includes the existing suite, the latest font checks and the Jobs tests.
4. From the project root, run:

   ```bash
   bash run_tests.sh --run-platform-tests
   bash run_mac.sh
   ```

No database migration or new dependencies are required. Keep the existing
database, settings, virtual environment and launch/build scripts. The larger
`customer_app(2).zip` is the updated complete source and test harness for reference;
the smaller patch is sufficient to install this change.

## Using Jobs

- Search and status filters retain the existing All, Upcoming, Overdue, Scheduled,
  In progress, Completed, Cancelled and Trash options. Upcoming includes open jobs;
  combine it with a date range for a future work list.
- Group by Scheduled day (default), Completed day, Customer or Status. Scheduled
  groups use scheduled dates only; completed groups use completion dates only.
  Missing dates appear as Unscheduled or No completion date. Duplicate customer
  names remain separate when grouping by customer ID.
- Date ranges include All dates (default), Today, This week (Monday to Sunday),
  Next 7 days (today plus six days), This month and an inclusive Custom range.
  Completed-day grouping uses completion dates for these ranges; the other
  groupings use scheduled dates. Reversed custom dates show guidance and no rows.
- Maroon dropdowns use white text and arrows, with an explicit popup highlight
  and keyboard-focus state. Export buttons retain the cyan treatment.
- Day/group checkboxes select their currently filtered child jobs. Individual
  checkboxes support partial day selection. Select all filtered and Clear
  selection are also available. Collapse/expand preserves checked jobs.
- Filter changes clear export selection, with a message in the selection bar.
  Ordinary data refreshes retain surviving checked job IDs, focused job and
  collapsed groups. Removed records cannot remain selected for export.
- Clicking a job opens its details independently of export selection. The details
  include linked customer address/contact data and all enabled configured job
  fields. Notes remain plain text and scroll independently. Long details scroll
  while job actions remain visible.
- Edit job and double-clicking a job open the existing editor. Mark completed is
  enabled for Scheduled/In progress jobs. More contains Move to Trash with the
  existing confirmation; Restore appears for a focused trashed job. View customer
  opens the linked customer, including inactive customers.
- The main list always provides Service, Status, Fee and Payment summaries.
  Additional fields marked for browsing follow them, including configured labels
  and custom fields. Columns scroll horizontally rather than being squeezed.
- Export CSV offers Export selected jobs and Export all filtered jobs, with
  explicit record counts. Both produce a flat CSV with one row per job, customer
  IDs/names, both dates and enabled configured fields. A selected group itself is
  never an exported record. Existing CSV quoting and spreadsheet-formula
  protection are retained.
- Fee totals use exact decimal arithmetic. Missing fees are identified separately.
  Fee totals are job charges, not payment receipts or profit.

## Validation

The full suite passed: **185 passed, 1 skipped**, with **94.55% combined
statement and branch coverage** on Linux / Python 3.12.14 / Qt offscreen.
The skipped native IPC test was blocked by this host (EPERM). See
`VALIDATION.json` and `validation_reports/` for the full results.
The Jobs regression tests cover grouping/date boundaries, leap years, invalid
custom ranges, checkbox propagation, partial selection, collapse/refresh,
selection/focus separation, search clearing, both CSV scopes, duplicate customer
IDs, inactive navigation, configured fields/labels, plain notes, edit-button and
double-click editing, long content, dropdown contrast and rendering at 1250 × 820
and 900 × 690 pixels. Existing database and recovery tests remain included.

Actual Qt screenshots under `preview/` use synthetic data. The preview's compact
column selection was made using the existing field configuration. Your configured
extra columns remain available and may require horizontal scrolling.

Primary Qt references:
- https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QTreeWidgetItem.html
- https://doc.qt.io/qtforpython-6/PySide6/QtCore/QSignalBlocker.html
- https://doc.qt.io/qtforpython-6/overviews/qtwidgets-stylesheet-customizing.html

Potential bias: local checks use Linux offscreen rendering. Native macOS/Windows
fonts, scaling and packaged builds still need platform verification.
