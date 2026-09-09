@echo off
setlocal
cd /d "%~dp0"

echo Starting ReceiptFlow on Windows...

where py >nul 2>nul
if errorlevel 1 (
    echo Python launcher not found. Please install Python 3.10 or newer from python.org or the Microsoft Store.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Failed to create the virtual environment.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

set "PYTHONPATH=%CD%\src"
python -m receipt_app

if errorlevel 1 (
    echo.
    echo ReceiptFlow stopped with an error.
    pause
)
