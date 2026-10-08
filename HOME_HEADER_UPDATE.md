# Home overview and app header update

## Install

1. Close ShiningKnights.
2. Extract `home-header-update.zip` into your project root and merge its folders, replacing matching files. Keep `src/customer_app/` and `tests/` at those exact paths. The update includes the complete application source and test folders so the previous Customers, Jobs and Settings pages remain available.
3. Run `bash run_mac.sh` on Mac, or `run_windows.bat` on Windows.
4. Run `bash run_tests.sh --run-platform-tests` on Mac to check your native platform. Windows uses `run_tests.bat --run-platform-tests`.

There are no new dependencies or database schema changes. Your records, configuration, backups, virtual environment and OS credential-store key stay in their existing locations. The zip contains source code, not a built Mac or Windows application. If your local code has other changes beyond the uploaded files, compare those changes before replacing it.

## What changed

- A branded Shining Knights header with Home, Customers, Jobs and Settings alongside the name. The selected page is maroon. Keyboard shortcuts are Alt+H, Alt+C, Alt+J and Alt+S.
- Overview heading with the current date; Add customer and Add job actions.
- Three clickable cards: Today's jobs, Next 7 days, Needs a booking.
- Upcoming visits: first five open jobs in date order, with customer, suburb and service. Clicking a visit or pressing Enter opens that specific job in Jobs. View all jobs opens the complete Jobs list.
- Needs a booking: first five active customers due soon or overdue, with individual Add job actions. Customer names open their profiles. View all, or the summary card, reveals the full booking list.
- An overdue-job notice only when past scheduled jobs remain open, with a Review jobs link.
- A quiet backup-status footer linking directly to Backups & help in Settings.
- Counts and lists refresh after changes, restore and date rollover. Existing Settings save/discard protection also applies to the new header.

## Count rules

Today's jobs and Next 7 days include Scheduled and In progress jobs, excluding Trash, Completed and Cancelled. The seven-day window includes today through six days later. Existing open visits remain visible if their customer has since become inactive.

Needs a booking includes active customers whose next service due date is before or within the seven-day window. Any open, non-trashed booking dated today or later suppresses that reminder, even if booked beyond seven days. Past or undated jobs do not suppress it. Due dates continue to use the last non-trashed completed visit plus the customer's current repeat interval, or the initial service date when no visit has been completed. Completion never automatically creates another job.

## Verification

The new encrypted-database cases cover date boundaries, year rollover, leap days, duplicate customer names, inactive customers, recurrence, completed/cancelled jobs, Trash and existing future bookings. UI cases cover links, actual job creation with service defaults, all booking reminders, header navigation, unsaved Settings decisions, day rollover, text space and rendered contrast at 1250x820 and 900x690.

`VALIDATION.json` records this build's full-suite result. To inspect synthetic previews locally, run `PYTHONPATH=src .venv/bin/python check_home_layout.py` on Mac. Preview records live only in a temporary database and are never added to your real records. Native Mac/Windows rendering and packaging still need checking on those operating systems.
