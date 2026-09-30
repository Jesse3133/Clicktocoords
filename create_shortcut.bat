@echo off
REM Creates a Desktop shortcut to ClickToCoords.exe for easy double-click
REM launching, instead of having to find and run the exe file each time.
REM
REM Usage: create_shortcut.bat [path\to\ClickToCoords.exe]
REM   With no argument, looks for ClickToCoords.exe in this script's own
REM   folder - e.g. run it straight from a folder you extracted a
REM   downloaded build into.

setlocal

set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=%~dp0ClickToCoords.exe"

if not exist "%TARGET%" (
    echo ClickToCoords.exe not found: "%TARGET%"
    echo Run this script from the folder that contains ClickToCoords.exe,
    echo or pass its path as an argument.
    if not defined CTC_NO_PAUSE pause
    exit /b 1
)

for %%F in ("%TARGET%") do set "TARGET_DIR=%%~dpF"

powershell -NoProfile -Command ^
    "$ws = New-Object -ComObject WScript.Shell;" ^
    "$shortcut = $ws.CreateShortcut([System.IO.Path]::Combine($ws.SpecialFolders('Desktop'), 'ClickToCoords.lnk'));" ^
    "$shortcut.TargetPath = '%TARGET%';" ^
    "$shortcut.WorkingDirectory = '%TARGET_DIR%';" ^
    "$shortcut.IconLocation = '%TARGET%';" ^
    "$shortcut.Description = 'ClickToCoords - coordinate click automation';" ^
    "$shortcut.Save()"

if errorlevel 1 (
    echo Failed to create desktop shortcut.
    if not defined CTC_NO_PAUSE pause
    exit /b 1
)

echo Desktop shortcut created: ClickToCoords.lnk
if not defined CTC_NO_PAUSE pause
