@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "NoDefaultCurrentDirectoryInExePath=1"
set "PYTHON_MANAGER_AUTOMATIC_INSTALL=false"
set "PYTHONUTF8=1"
set "OS_UTILS_PYTHON="
set "BOOTSTRAP_PYTHON=%LOCALAPPDATA%\Programs\Python\Python313"

pushd "%~dp0" || goto folder_error
if not exist "os_utils.py" (
    echo os_utils.py is missing. Extract the entire OS Utils ZIP and run this file from that folder.
    goto failed
)
echo Starting OS Utils...

py.exe -3 -I -c "import sys; sys.exit(not ((3, 9) <= sys.version_info[:2]))" >nul 2>&1
if not errorlevel 1 goto run_with_launcher

for /f "delims=" %%P in ('where.exe $PATH:python.exe 2^>nul') do (
    if not defined OS_UTILS_PYTHON call :check_python "%%P"
)
if not defined OS_UTILS_PYTHON call :check_python "%BOOTSTRAP_PYTHON%\python.exe"
if defined OS_UTILS_PYTHON goto run_with_python

where.exe $PATH:winget.exe >nul 2>&1
if errorlevel 1 goto missing_winget
echo Python 3.9 or newer was not found. Installing Python 3.13 with Windows Package Manager...
winget.exe install --id Python.Python.3.13 --exact --source winget --scope user --location "%BOOTSTRAP_PYTHON%" --no-upgrade
if errorlevel 1 goto install_error
call :check_python "%BOOTSTRAP_PYTHON%\python.exe"
if defined OS_UTILS_PYTHON goto run_with_python

py.exe -3 -I -c "import sys; sys.exit(not ((3, 9) <= sys.version_info[:2]))" >nul 2>&1
if not errorlevel 1 goto run_with_launcher
echo Python installed, but this window could not find it. Close this window and open run.bat again.
goto failed

:check_python
if /i "%~1"=="%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" exit /b 0
if not exist "%~1" exit /b 0
"%~1" -I -c "import sys; sys.exit(not ((3, 9) <= sys.version_info[:2]))" >nul 2>&1
if not errorlevel 1 set "OS_UTILS_PYTHON=%~1"
exit /b 0

:run_with_launcher
py.exe -3 -B os_utils.py
goto finished

:run_with_python
"%OS_UTILS_PYTHON%" -B os_utils.py

:finished
set "OS_UTILS_EXIT=%ERRORLEVEL%"
popd
if not "%OS_UTILS_EXIT%"=="0" pause
exit /b %OS_UTILS_EXIT%

:missing_winget
echo Windows Package Manager is unavailable. Install Python from https://www.python.org/downloads/windows/ and reopen run.bat.
goto failed

:install_error
echo Python setup did not finish. Review the WinGet message above, or install Python and reopen run.bat.
goto failed

:folder_error
echo Unable to open the OS Utils folder. Extract the ZIP before running this file.
pause
exit /b 1

:failed
popd
pause
exit /b 1
