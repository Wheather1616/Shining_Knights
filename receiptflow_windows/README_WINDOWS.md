# ReceiptFlow: Windows setup

This folder is arranged to run ReceiptFlow on Windows.

## 1. Install Python

Install Python 3.10 or newer. During installation, tick **Add Python to PATH** if the installer offers it.

## 2. Run the app from source

Double-click:

```text
run_windows.bat
```

The script will:

1. create a local `.venv` virtual environment if it does not already exist
2. install the packages in `requirements.txt`
3. set `PYTHONPATH` to the local `src` folder
4. launch the app with `python -m receipt_app`

## 3. Build a Windows app

Double-click:

```text
build_windows.bat
```

The built application should appear here:

```text
dist\ReceiptFlow\ReceiptFlow.exe
```

Copy the whole `dist\ReceiptFlow` folder if you want to move the app to another Windows computer.

## 4. Where the database is stored

On Windows, this version stores settings and the default database under:

```text
%APPDATA%\ReceiptFlow\
```

The default database file is:

```text
%APPDATA%\ReceiptFlow\receipts.db
```

## 5. Moving data from the Mac version

The Mac version stores the default database at:

```text
~/Library/Application Support/ReceiptFlow/receipts.db
```

To move existing data, copy that `receipts.db` file into:

```text
%APPDATA%\ReceiptFlow\receipts.db
```

Create the folder first if it does not exist.

## 6. Notes

- The floating desktop tab should still work on Windows, but it may behave slightly differently because Windows tray/always-on-top behaviour is not identical to macOS.
- If the app does not launch, run `run_windows.bat` from Command Prompt so the error message stays visible.
