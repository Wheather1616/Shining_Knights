@echo off
setlocal
set "TEST_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%TEST_PYTHON%" (
  echo Create the project virtual environment and install the test requirements first. 1>&2
  exit /b 2
)
"%TEST_PYTHON%" "%~dp0scripts\run_tests.py" %*
exit /b %errorlevel%
