@echo off
REM Builds ClickToCoords into a standalone Windows .exe (dist\ClickToCoords.exe).
REM Must be run on Windows - PyInstaller packages for whatever OS it runs on.

setlocal

pip install -r requirements.txt
if errorlevel 1 goto :error

pip install -r requirements-build.txt
if errorlevel 1 goto :error

pyinstaller --onefile --windowed --name ClickToCoords app.py
if errorlevel 1 goto :error

echo.
echo Build complete: dist\ClickToCoords.exe
goto :eof

:error
echo.
echo Build failed.
exit /b 1
