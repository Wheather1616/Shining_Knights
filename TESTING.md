# ShiningKnights testing suite

For the current customer workflow update, follow `CUSTOMER_WORKFLOW_UPDATE.md`.
The latest result is in `VALIDATION.json`. The new tests cover separate names, numeric input, wheel-safe dropdowns, calendar selection, equipment grids, hours snapshots, encrypted version-1 migration and legacy backup restoration.

This update provides automated tests for the PySide6 customer/job app and its
encrypted SQLCipher database, plus a repeatable runner and CI workflow.

## Install the update

If you already installed the testing suite, this correction only requires
replacing `tests` and `pytest.ini` from this archive. Then rerun
`bash run_tests.sh --run-platform-tests` on your Mac. No dependency changes
or application source changes are required for this correction.

The correction keeps the Unix capability probe in a private directory under
`/tmp` so macOS's long pytest temporary paths cannot exceed the socket address
limit. It explicitly closes the four standard SQLite test connections while
preserving transaction commits, and treats unraisable exceptions as failures
so Python 3.13 resource leaks cannot pass unnoticed. Four new unit cases check
the short probe path, cleanup, selective skipping and Windows behaviour.

**This archive contains files for the project root.** Extract it outside your
working project, then apply the folders at the matching levels:

1. Quit ShiningKnights.
2. Preserve your current test folder. On Mac, from the project root:

   ```bash
   if [ -d tests ]; then mv tests "tests_before_update_$(date +%Y%m%d_%H%M%S)"; fi
   ```

3. Merge the archive's `src/customer_app` into your existing `src/customer_app`,
   replacing matching files. Merge `scripts` into the project root. Copy the new
   `tests` folder and the root `pytest.ini`, `.coveragerc`, `requirements-test.txt`,
   `run_tests.sh` and `run_tests.bat` into the project root.
4. For GitHub CI, also copy `.github/workflows/tests.yml` into the matching path.
   Finder can show these dot-prefixed configuration files with Cmd+Shift+Period.
5. From the project root, install the testing requirements into the existing
   environment:

   ```bash
   .venv/bin/python -m pip install -r requirements-test.txt
   bash run_tests.sh
   ```

The resulting paths must include `src/customer_app/__main__.py`,
`tests/conftest.py`, `scripts/run_tests.py` and `pytest.ini`. Do not place the
whole extracted archive inside `src/customer_app`. Your working app launch/build
scripts, production database and OS credentials are not replaced by this update.

On Windows, use the equivalent commands from the project root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
.\run_tests.bat
```

For a clean checkout with no environment, first use your normal setup script to
install the application's `requirements.txt`, then install `requirements-test.txt`.
The testing requirements pin the direct application and testing libraries used
for this validation. Transitive dependencies are not fully locked.

## Why these mechanisms

| Mechanism | Purpose in this app |
| --- | --- |
| pytest fixtures and parametrised cases | Share test setup and check invalid input and boundary cases with clear failures. |
| pytest-qt | Click buttons, type into forms, manage widget lifetimes and wait for actual signals. |
| Temporary SQLCipher files | Test genuine encryption, transactions, foreign keys, migration, backups and reopening without using live data. |
| Hypothesis | Generate exact-cent money amounts and calendar recurrence cases, including month-end boundaries. |
| Failure injection at service boundaries | Test unavailable credentials, failed writes, failed backup validation and migration rollback. |
| pytest-cov | Report line and branch coverage and fail full runs below the initial 80% floor. |
| GitHub Actions platform matrix | Run the same suite on Linux/Python 3.12 and macOS and Windows/Python 3.13. |
| Native checks before releases | Inspect actual platform rendering and exercise local IPC beyond offscreen widget tests. |

These are selected for this project's Qt widgets and local encrypted storage.
Browser automation tools do not exercise the native desktop widgets. Pixel-exact
screenshot comparison is deferred because fonts and native rendering vary by
platform; current visual checks instead cover effective text contrast and asset
loading, with screenshots captured for failed UI tests.

## What is covered

- Exact money handling, invalid amounts and calendar recurrence.
- Field key/type/choice contracts, independent settings and failed atomic saves.
- Customer and job validation, relationships, snapshots, recurrence summaries,
  archiving, Trash/restore, searching and dashboard date boundaries.
- SQLCipher availability, wrong-key rejection, encrypted disk contents and
  SQLite, cipher and foreign-key integrity checks.
- Transaction rollback, encrypted backup snapshots, backup naming/retention,
  failed backup cleanup, migration rollback and legacy receipt preservation.
- OS credential-store error handling using controlled test doubles.
- Adding and cancelling customer forms, saving and editing jobs, changing
  customers, validation failures, grouping, filtering and confirmation decisions.
- Configuring custom fields and choices, applying settings to new forms and lists.
- CSV export quoting, Unicode, custom fields and formula-like text sanitisation.
- Bootstrap success/error/secondary-launch paths, native data paths and locks.
- Theme colours, contrast for selected and disabled controls, fonts and SVG assets.

## Run commands

| Task | Mac command |
| --- | --- |
| Full suite with reports and coverage gate | `bash run_tests.sh` |
| Unit tests while editing | `bash run_tests.sh -m unit --no-cov` |
| Encrypted database/recovery tests | `bash run_tests.sh -m integration --no-cov` |
| Qt workflow and theme tests | `bash run_tests.sh -m ui --no-cov` |
| Full suite including native local IPC | `bash run_tests.sh --run-platform-tests` |
| UI tests using the native Mac platform plugin | `bash run_tests.sh --native-ui -m ui --no-cov` |
| Re-run the last failures | `bash run_tests.sh --lf --no-cov` |

The Windows equivalents use `run_tests.bat` with the same arguments. On other
systems or in CI, use `python scripts/run_tests.py` with the same arguments.
The Python runner resolves the project from its own location and starts a fresh
pytest process, so it can be invoked from another working directory and measure
imports correctly. It returns a non-zero exit status on failures.

Selected test runs use `--no-cov` because a subset cannot meet a whole-app
coverage floor. Keep the gate enabled for the full suite before committing.

## Test isolation and reliability

Every test receives temporary storage. Default app data paths are redirected
into that storage, and attempts to call the real credential store fail. Encrypted
database fixtures use a clearly labelled disposable key. Test data is synthetic.
Confirmation prompts default to No unless the test explicitly exercises approval.
Qt widgets are managed through pytest-qt, and modal interactions are closed even
if the test action fails. The suite uses signal/condition waits instead of sleeps.

Property tests use 100 deterministic examples per generated test. Newly found
counterexamples should also become explicit regression cases. Unexpected Qt
warnings fail tests; only three known offscreen-plugin limitations are ignored.

The real keychain/credential locker is not exercised automatically. Add a manual
check of credential access in a disposable OS profile before distributing builds.
Native IPC is opt-in locally and enabled in CI. An independent Unix socket probe
allows a skip only when the host denies sockets with EPERM; application endpoint
errors still fail the test. The probe uses a private short `/tmp` path on Unix,
independent of pytest's longer temporary database and lock paths.

## Reports and CI

Full runs write:

- `reports/coverage/index.html`: browsable coverage with missing lines/branches.
- `reports/coverage.xml`: machine-readable coverage.
- `reports/junit.xml`: machine-readable test outcomes.
- `reports/failures/*.png`: screenshots of visible widgets for failed UI tests.

The workflow runs on pushes, pull requests and manual dispatches, and uploads
reports even when tests fail. It starts running once you add it to your GitHub
repository and push. No workflow has been executed on your repository by this
update. Add `reports/`, `.coverage*`, `.pytest_cache/` and `.hypothesis/` to your
existing `.gitignore` if not already present. Keep the archived old test folder
out of version control once you have reviewed the replacement suite.

The 80% initial coverage floor is a regression guard, not a release guarantee.
Use the HTML report to find meaningful missing cases rather than writing tests
solely to increase the percentage. Raise the floor as the app grows.

## Fixes exposed by the tests

The package includes four small fixes, with no database schema change:

1. Close backup connections on every open/copy failure, and close them before
   removing a failed temporary snapshot so cleanup also works on Windows.
2. Validate raw encryption keys before opening files and close connections on
   connection-configuration failures.
3. Reject non-object settings JSON with a clear preserved-file error.
4. Preserve the specific fractional-cent validation message instead of replacing
   it with a generic amount error.

## Local validation

Validated on Linux with Python 3.12.14, PySide6 6.11.2, SQLCipher wrapper 0.6.2,
pytest 9.1.1, pytest-qt 4.5.0, pytest-cov 7.1.0 and Hypothesis 6.168.3:

- **185 passed, 1 skipped** when explicitly requesting native IPC checks.
- **94.55% combined statement and branch coverage**; the 80% gate passed.
- Eighteen Jobs cases cover date grouping/filtering, export selections and scopes,
  linked customer navigation, configured fields, editing and layout/contrast.
- Nine font regression cases check generic, missing and private system defaults,
  platform font inventories, fallback selection and real text rendering after
  repeated theme application. The missing "Sans Serif" warning is not ignored.
- The native IPC test was skipped after the execution sandbox denied Unix sockets
  with EPERM. Lock and activation logic were exercised separately.
- The platform matrix YAML was validated. Native macOS/Windows tests and the
  GitHub-hosted jobs have not been run here.

Before releases, run native UI and IPC checks on the target systems, check keyboard
focus and screen scaling, and smoke-test a freshly built app in a disposable
profile. This suite currently tests source code, not a packaged `.app` or `.exe`.

## Research sources

The implementation follows the tools' primary documentation:

1. [pytest temporary directories](https://docs.pytest.org/en/stable/how-to/tmp_path.html)
   and [monkeypatch fixtures](https://docs.pytest.org/en/stable/how-to/monkeypatch.html).
2. [pytest-qt](https://pytest-qt.readthedocs.io/en/latest/),
   [signal waits](https://pytest-qt.readthedocs.io/en/latest/signals.html) and
   [Qt log capture](https://pytest-qt.readthedocs.io/en/latest/logging.html).
3. [Hypothesis introduction](https://hypothesis.readthedocs.io/en/latest/tutorial/introduction.html).
4. [pytest-cov configuration](https://pytest-cov.readthedocs.io/en/latest/config.html).
5. [SQLCipher API and cipher integrity checks](https://www.zetetic.net/sqlcipher/sqlcipher-api/)
   and [SQLite PRAGMAs](https://sqlite.org/pragma.html). SQLite's integrity check
   does not check foreign keys, so the suite checks them separately.
6. [GitHub Actions Python testing and platform matrices](https://docs.github.com/en/actions/tutorials/build-and-test-code/python).

Potential bias: This strategy prioritises record integrity and core user workflows.
Coverage percentages, mocks and offscreen runs leave gaps in platform integration,
packaged builds, visual layout and failures not yet modelled by the suite.


## Settings and guided recovery update (7 October 2026)

The latest suite contains 244 cases: 243 pass locally and the native IPC case is opt-in. New checks cover safe preference defaults and round trips, inactive catalogues, actual list-column changes, default payment on new customers only, automatic question identifiers, retained hidden answers, save/discard/keep-editing guards, filter persistence without search text, real encrypted restore and safety copies, invalid/wrong-key/unsupported backups, write rollback, interrupted recovery and rejection of backups changed after review. Settings geometry is checked at 1250 × 820 and 900 × 690. Use the existing platform commands above on Mac/Windows.


## Multiple customer services

`tests/integration/test_customer_services.py` exercises real encrypted version 1 and 2 upgrades, transactional rollback of the entire migration chain, customer/service ownership, snapshot pricing, usual-service synchronisation, archived services, validation and backup recovery. `tests/ui/test_customer_services.py` drives the service editor and customer screen, booking selection and overrides, unchanged historical jobs, customer changes, unfinished input preservation, service names in CSV and page geometry. `check_customer_services.py` provides reproducible synthetic previews. Current results are in `VALIDATION.json`; native platform tests remain opt-in.


## Multiple nature-of-job choices

`tests/integration/test_multiple_job_types.py` verifies list-valued work types, original version 3 data conversion, labels containing commas/JSON-like text, full migration-chain rollback, previous settings conversion, customer/usual-service synchronisation, job snapshots and backup recovery. `tests/ui/test_multiple_job_types.py` verifies independent tick interactions, saved selections, booking overrides, retired choices, readable CSV/history/Home output and grids without an internal scroll area. Current suite totals are in `VALIDATION.json`.


## Per-type Inside / Outside / Both choices

`tests/integration/test_service_sides.py` covers encrypted scope mappings, valid side values and selected-type ownership, customer/usual-service synchronisation, job snapshots, retired choices, migrations from versions 1 to 4, rollback after a last-step interruption, old/current backup restore and rejection of damaged scope data before replacing live records. `tests/ui/test_service_sides.py` covers conditional selectors beneath ticks, independent exclusive choices, keyboard activation, save/reopen, unticking, booking overrides, switching services without losing unfinished inputs, readable history/Jobs/Home/CSV output and layouts at 520 and 650 pixels. Results for the full suite are in `VALIDATION.json`.
