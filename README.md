# ClickToCoords

A local desktop app (Tkinter, no browser) that cycles a double middle-click
across 3 saved screen coordinates on a repeating timer, with a global **F6**
hotkey to start/stop it.

## What it does

- Enter (or capture) 3 screen coordinates.
- While running, it visits each point in order and sends **two middle-mouse
  clicks** at it, then moves to the next point.
- Two adjustable delays:
  - **Delay between points** — the main cycle timer.
  - **Delay between the 2 clicks** at the same point.
- **F6** toggles running on/off from anywhere, even if the window isn't
  focused. There's also an on-screen Toggle button.

## Setup

Requires Python 3.8+.

```bash
pip install -r requirements.txt
python app.py
```

## Capturing coordinates

Click a point's **Capture** button, then move your mouse to the target
location within 3 seconds — the button counts down and records the mouse
position when it reaches zero.

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
pip install -r requirements.txt
pip install -r requirements-build.txt
pyinstaller --onefile --windowed --name ClickToCoords app.py
```

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
