# ReceiptFlow

ReceiptFlow is a Mac-friendly desktop application for capturing, importing, browsing and exporting receipt transactions from a local SQLite database.

It is designed as a generalised version of the original receipt spreadsheet workflow. Instead of rebuilding the database only from Excel workbooks, the app supports direct receipt entry through a desktop popup, CSV/Excel import, configurable fields, full database browsing and export.

## Current features

- Home dashboard with clear actions
- Quick receipt popup for immediate transaction entry
- Local SQLite database stored by default in `~/Library/Application Support/ReceiptFlow/receipts.db`
- Settings screen for database path, default import folder, quick-access tray behaviour and configurable receipt fields
- CSV and Excel import with automatic column/header mapping
- Browse screen with one flexible search bar
- Sort options including newest, oldest, name and amount
- Optional group-by-date results view
- Export current results to CSV
- Menu bar/tray quick actions for adding a new receipt, opening Browse or showing the desktop tab
- Draggable desktop tab inspired by macOS event widgets, with quick receipt entry, Enter-to-save, a styled visible background, an expandable scrollable today's receipts menu and configurable panel size


## Desktop tab behaviour

The desktop tab is designed as a fast-entry widget rather than a passive summary panel. It uses the fields marked as `Quick` in Settings, saves when Return/Enter is pressed, and uses a visible app-styled card background so it remains readable over the macOS desktop. The `Today’s receipts` control expands into a scrollable dropdown-style list of receipts created today. The tab size can be adjusted in Settings under `Desktop size`.

## Why this is a stronger portfolio project

The project now shows more than basic spreadsheet processing. It demonstrates:

- desktop GUI design with PySide6/Qt
- local-first data storage
- schema design and indexing
- dynamic form generation from settings
- CSV/Excel import mapping and validation
- search and sort strategy
- macOS packaging with PyInstaller

## Mac setup

From the project folder:

```bash
./run_mac.sh
```

This creates a virtual environment, installs dependencies and runs the app.

Manual setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
export PYTHONPATH="$PWD/src"
python -m receipt_app
```

## Build a macOS app bundle

After testing the app locally:

```bash
./build_mac.sh
```

The bundled app should be created at:

```text
dist/ReceiptFlow.app
```

## Suggested development roadmap

### Phase 1: Working desktop MVP

- Direct receipt entry
- Import CSV/Excel
- Search, sort and export
- Settings-driven fields

### Phase 2: Better import workflow

- Add a visual column-mapping screen before import
- Preview the first few rows before saving
- Show row-level validation errors
- Support duplicate detection by receipt number/date/amount

### Phase 3: Stronger data model

- Add receipt categories and tags
- Add attachments or scanned receipt images
- Add audit history for edits and deletes
- Add more advanced reporting by date, category, payment method and customer/member

### Phase 4: Packaging polish

- Refine the desktop tab with user-selectable position, opacity and default list mode
- Add a proper macOS app icon
- Add code signing/notarisation if distributing outside your own machine
- Add auto-backup of the SQLite database

## Project structure

```text
receipt_desktop_app/
├── src/receipt_app/
│   ├── app.py           # PySide6 desktop UI, quick-entry dialog and desktop tab
│   ├── config.py        # settings and dynamic field definitions
│   ├── database.py      # SQLite schema, indexes, search, sort and export
│   ├── importer.py      # CSV/Excel import and header mapping
│   └── styles.py        # Qt stylesheet adapted from the uploaded CSS direction
├── docs/
│   └── algorithm_notes.md
├── examples/
│   └── sample_receipts.csv
├── tests/
│   └── test_database_and_importer.py
├── run_mac.sh
├── build_mac.sh
├── requirements.txt
└── pyproject.toml
```

## Notes

The UI styling has been adapted from the uploaded CSS direction: light background, white cards, soft borders, rounded controls, blue/purple accent colours and clear action buttons.
