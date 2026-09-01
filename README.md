# ClickToCoords

A local desktop app (Tkinter, no browser) that cycles a double middle-click
across 3 saved screen coordinates on a repeating timer, with global
hotkeys to start/stop it or run it once.

## What it does

- Enter (or capture) up to 3 screen coordinates. Points 2 and 3 can be
  switched off with the **On** checkbox next to each, so the app can be run
  with just 1 or 2 points if you don't need all 3.
- While running, it visits each active point in order and sends **two
  middle-mouse clicks** at it, then moves to the next point.
- Three adjustable delays:
  - **Delay between points** — spacing between points within one set.
  - **Delay between the 2 clicks** at the same point.
  - **Delay after full set** — how long to wait after the last active point
    before starting the set over from the first point (e.g. click all 3
    points, then wait 10 seconds before doing another pass). Not applied
    after a Single Use run, since there's no next pass to wait for. A live
    countdown ("Next set in Xs") shows in the bottom-right of the window
    while this wait is in progress.
  - Every one of these delays gets an extra random amount added on top
    each time it's waited on (independently, per wait) — configurable via
    the **Random jitter added (s)** min/max fields (default 0.3 to 0.5).
    This only ever adds to the configured delay, never subtracts from it,
    so timing doesn't look perfectly mechanical. Set both to 0 to disable
    jitter entirely.
- **F6** toggles continuous running on/off from anywhere, even if the
  window isn't focused. There's also an on-screen Toggle button.
- **\\ (backslash)** runs one pass through the active points a single time,
  then stops automatically. There's also an on-screen **Single Use**
  button — click it again (or press \\ again) while it's running to cancel
  the pass early. Both are disabled while continuous automation is running.
- A **Dark mode** checkbox switches the whole UI between light and dark.
  Your choice is remembered between launches (stored in a small config
  file under your user profile — `%APPDATA%\ClickToCoords\config.json` on
  Windows, `~/.config/ClickToCoords/config.json` on Linux, `~/Library/
  Application Support/ClickToCoords/config.json` on macOS).

## Setup

Requires Python 3.8+.

```bash
pip install -r requirements.txt
python app.py
```

## Capturing coordinates

Click a point's **Capture** button (it changes to "Click MMB"), then move
your mouse to the target location and **middle-click**. That records the
click's position into the point's X/Y fields. The click itself isn't
suppressed, so it still acts as a normal middle click wherever it lands.
Capture is disabled while the automation is running (starting the
automation also cancels any capture in progress), since the automation's
own middle clicks would otherwise get picked up as a capture.

## Getting a pre-built .exe (GitHub Actions)

Every push to `main` runs `.github/workflows/build-windows-exe.yml`, which
builds on an actual `windows-latest` GitHub Actions runner and uploads the
result. To grab it: open the repo's **Actions** tab → the latest "Build
Windows exe" run → download the `ClickToCoords-windows-exe` artifact from
the run summary (it's a zip containing `ClickToCoords.exe`). You can also
trigger a build on demand from that workflow's page with **Run workflow**.

## Building a standalone .exe (Windows)

PyInstaller packages `app.py` and its dependencies into a single
`dist\ClickToCoords.exe` that runs without a separate Python install. It
must be built **on Windows** — PyInstaller packages for whatever OS it runs
on, it doesn't cross-compile.

```bat
build.bat
```

This installs the runtime and build dependencies and runs PyInstaller for
you. The result is `dist\ClickToCoords.exe` — copy that one file wherever
you like and run it directly.

To do it by hand instead:

```bat
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt
python -m PyInstaller --onefile --windowed --name ClickToCoords app.py
```

Using `python -m PyInstaller` (rather than the bare `pyinstaller` command)
avoids "pyinstaller is not recognized" errors, which happen when pip
installs its console scripts into a user Scripts folder that isn't on
PATH — `python -m ...` always works since it doesn't depend on PATH at all.

Windows Defender / SmartScreen may flag a freshly built, unsigned exe on
first run ("Windows protected your PC") since it isn't code-signed — choose
"More info" → "Run anyway", or build it yourself from source as above so
you know exactly what's in it.

## Platform notes

- **Windows**: works out of the box.
- **macOS**: grant your terminal/Python **Accessibility** and **Input
  Monitoring** permissions (System Settings → Privacy & Security) for the
  global hotkey and simulated clicks to work.
- **Linux**: works under X11. Under Wayland, global hotkeys and simulated
  input via `pynput` may not work depending on your compositor — X11 (or
  XWayland with the right permissions) is recommended.

## Safety

The automation only clicks the mouse at the 3 configured coordinates — it
never types, reads screen content, or interacts with anything else. Always
double-check your coordinates and target window before starting it.
