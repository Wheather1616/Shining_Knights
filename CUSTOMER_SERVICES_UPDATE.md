# Multiple services per customer

Customers can now have named services with different charges, estimated hours, equipment, one or several types of work and notes. For example, save Indoor windows at $500 for 3 hours and Whole house at $600 for 4 hours under the same customer.

## Install

Close the app, extract `customer-services-update.zip`, and merge its `src`, `tests` and root files into your existing Shining_Knights project, keeping the matching paths. This package includes the current Home, Customers, Jobs and Settings screens and the test suite. It does not include customer records, credentials or a virtual environment.

From the project folder, run:

```bash
bash run_mac.sh
bash run_tests.sh --run-platform-tests
```

The first launch upgrades an existing version 1, 2, 3 or 4 encrypted database to version 5. Use this updated app with the upgraded database. Existing encrypted version 1, 2, 3 and 4 backups can still be inspected and restored; restore upgrades a private copy and retains the source backup.

## Use it

1. Select a customer and open **Services**.
2. The existing defaults are carried over as **Usual service**. Select it and choose **Edit service** to rename it to Indoor windows and set its fee to 500 and hours to 3.
3. Choose **Add service** to save Whole house with a fee of 600 and hours of 4.
4. When adding a job, choose the service in the **Service** dropdown. Its fee, hours, equipment, one or several types of work and notes are filled in. Adjust these for the individual visit if needed.
5. **Make usual** controls which service is selected for new jobs. Customer form defaults and the usual service stay in sync.
6. **Archive service** removes a service from new bookings while retaining its history. **Show archived** and **Restore service** bring it back. Choose another usual service before archiving the current usual service.

The job stores a snapshot of the service name and visit details. Changing or archiving the service later does not alter existing jobs. Editing an old job opens its saved charge and hours. Choosing another service explicitly applies that service's defaults while retaining dates, status, payment choices, custom answers and personal notes. A custom visit can have no saved service and still retain its entered values.

Charges are totals in AUD. Hours are estimates and never multiply the charge. Service frequency, the first/next due date and usual payment method remain customer-wide. This release selects one service per job, which suits alternating Indoor windows and Whole house visits; it does not combine several services into one invoice.

Named services appear in job history, Jobs, the Home visit list and job CSV exports. Existing jobs are retained without guessing which new service they belonged to. Existing IDs, customer/job links, recorded charges, hours, custom answers and inherited receipt tables are preserved.

Nature of job uses the same tick-box grid as equipment, allowing several types of work within one named service. Each selected type now has an Inside / Outside / Both selector beneath it. See `SERVICE_SIDES_UPDATE.md` for the latest change and `MULTIPLE_JOB_TYPES_UPDATE.md` for the original multi-choice update.

## Validation

The detailed result is recorded in `VALIDATION.json`. Tests use disposable SQLCipher databases and actual Qt interactions. New regressions cover service/customer ownership, independent prices, snapshots, duplicate names, validation, default synchronisation, archive/restore, migration from versions 1 and 2, interrupted migration rollback, old and current backup recovery, booking edits, screen geometry and CSV output. Native Mac/Windows rendering and packaging have not been executed on this Linux host.

`check_customer_services.py` reproduces the screen previews with synthetic records. It does not use real customer data or OS credentials.
