@echo off
REM Builds ClickToCoords into a standalone Windows .exe (dist\ClickToCoords.exe).
REM Must be run on Windows - PyInstaller packages for whatever OS it runs on.

setlocal

REM Invoked via "python -m" throughout instead of bare "pip"/"pyinstaller",
REM since pip-installed console scripts can land in a user Scripts folder
REM that isn't on PATH (a common cause of "pyinstaller is not recognized").

python -m pip install -r requirements.txt
if errorlevel 1 goto :error

python -m pip install -r requirements-build.txt
if errorlevel 1 goto :error

python -m PyInstaller --onefile --windowed --name ClickToCoords app.py
if errorlevel 1 goto :error

echo.
echo Build complete: dist\ClickToCoords.exe
goto :eof

:error
echo.
echo Build failed.
exit /b 1
