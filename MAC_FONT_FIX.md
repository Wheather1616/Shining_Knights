# macOS test font fix

The reported run passed 158 tests, including customer/database tests and native
IPC. The bootstrap test failed because strict Qt warning capture detected a
missing "Sans Serif" family.

The theme was applying Qt's GeneralFont directly. The offscreen plugin can return
the generic "Sans Serif" name. The updated theme checks available, non-private
font families, preserves a concrete system default when available, and otherwise
selects an available readable fallback. It excludes generic aliases. Branded
heading fonts, the light palette and strict warning checks are retained.

## Install

1. Quit the app and extract this archive outside your project.
2. Merge its `src` and `tests` directories into your Shining_Knights project root,
   replacing these two matching files:
   - `src/customer_app/ui/theme.py`
   - `tests/ui/test_theme.py`
3. Run from the project root:

   ```bash
   bash run_tests.sh --run-platform-tests
   ```

No dependency changes or database migration are required.

## Validation

167 passed, 1 skipped on Linux / Python 3.12.14 / Qt offscreen.
Combined statement and branch coverage: 93.49%.
The skipped native IPC test was blocked by this host (EPERM).
Nine added cases cover generic/missing/private font defaults and real text
rendering after repeated theme application. Qt warnings are still failures.
The existing bootstrap, database and customer-page tests passed.

The macOS failure was user-reported. This update requires a macOS rerun to
confirm the original warning is resolved on that platform.

Reference: https://doc.qt.io/qt-6/qfontdatabase.html
