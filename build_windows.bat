@echo off
setlocal
cd /d "%~dp0"
if not exist "src\customer_app\__main__.py" (
    echo Expected the application package directly in src\customer_app.
    pause
    exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
    call setup_windows.bat
    if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --name ShiningKnights --icon "src\customer_app\assets\Logo.ico" --paths src --collect-all keyring --collect-all sqlcipher3 --add-data "src/customer_app/assets:customer_app/assets" main.py
if errorlevel 1 goto failed
echo Built app: dist\ShiningKnights\ShiningKnights.exe
pause
exit /b 0
:failed
echo Build failed. Check the message above.
pause
exit /b 1
