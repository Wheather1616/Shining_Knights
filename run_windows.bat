@echo off
setlocal
set "project_dir=%~dp0"
if not exist "%project_dir%src\customer_app\__main__.py" (
    echo Missing src\customer_app\__main__.py.
    echo Place the application package directly in src\customer_app, not src\customer_app\customer_app.
    pause
    exit /b 1
)
if not exist "%project_dir%.venv\Scripts\python.exe" (
    call "%project_dir%setup_windows.bat"
    if errorlevel 1 exit /b 1
)
pushd "%project_dir%src"
"%project_dir%.venv\Scripts\python.exe" -m customer_app
set "launch_exit=%ERRORLEVEL%"
popd
if not "%launch_exit%"=="0" pause
exit /b %launch_exit%
