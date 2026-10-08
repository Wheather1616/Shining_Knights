@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install --only-binary=:all: -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -c "from sqlcipher3 import dbapi2; c=dbapi2.connect(':memory:'); assert c.execute('PRAGMA cipher_version').fetchone(), 'SQLCipher unavailable'; c.close()"
if errorlevel 1 goto failed
echo Setup complete. Run run_windows.bat to open ShiningKnights.
exit /b 0
:failed
echo Setup failed. Check the message above.
pause
exit /b 1
