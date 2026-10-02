@echo off
setlocal
cd /d "%~dp0"

echo Building Shining Knights for Windows...

where py >nul 2>nul
if errorlevel 1 (
    echo Python launcher not found. Please install Python 3.10 or newer first.
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
pyinstaller --noconfirm --clean --windowed --name ShiningKnights --icon "src\customer_app\assets\Logo.ico" --paths src --collect-all keyring --collect-all sqlcipher3 --add-data "src/customer_app/assets:customer_app/assets" main.py

if errorlevel 1 (
    echo.
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo Built app should appear at: dist\ShiningKnights\ShiningKnights.exe
echo You can copy the whole dist\ShiningKnights folder to another Windows computer.
pause
