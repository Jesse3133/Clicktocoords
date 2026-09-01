"""ClickToCoords - cycles a middle-click pair across 3 saved screen coordinates.

Runs as a local desktop app (Tkinter GUI). Press F6 anywhere (even when this
window isn't focused) to toggle continuous automation on/off, or \\ to run
one pass through the active points a single time.
"""
import json
import os
import random
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from pynput import keyboard, mouse
from pynput.mouse import Button

NUM_POINTS = 3
DEFAULT_INTERVAL = 1.0
DEFAULT_CLICK_GAP = 0.1
DEFAULT_CYCLE_DELAY = 10.0
DEFAULT_JITTER_MIN = 0.3
DEFAULT_JITTER_MAX = 0.5
POLL_SECONDS = 0.05
STATUS_REFRESH_MS = 150

COLOR_RUNNING = "#2ecc71"
COLOR_STOPPED = "#e74c3c"

LIGHT_COLORS = {
    "bg": "#f0f0f0",
    "fg": "#000000",
    "entry_bg": "#ffffff",
    "entry_fg": "#000000",
    "button_bg": "#e1e1e1",
    "active_bg": "#d0d0d0",
}
DARK_COLORS = {
    "bg": "#2b2b2b",
    "fg": "#e6e6e6",
    "entry_bg": "#3c3c3c",
    "entry_fg": "#e6e6e6",
    "button_bg": "#454545",
    "active_bg": "#565656",
}

def _config_path():
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "ClickToCoords" / "config.json"


CONFIG_PATH = _config_path()


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_config(config):
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f)
    except OSError:
        pass


mouse_controller = mouse.Controller()
running_event = threading.Event()
single_shot_event = threading.Event()

# Plain-Python settings mirror of the GUI state. The worker thread reads
# this instead of touching Tkinter variables directly, since Tk vars
# aren't safe to access off the main thread.
settings = {
    "points": [(0, 0) for _ in range(NUM_POINTS)],
    "enabled": [True] * NUM_POINTS,
    "interval": DEFAULT_INTERVAL,
    "click_gap": DEFAULT_CLICK_GAP,
    "cycle_delay": DEFAULT_CYCLE_DELAY,
    "jitter_min": DEFAULT_JITTER_MIN,
    "jitter_max": DEFAULT_JITTER_MAX,
}


def should_continue():
    return running_event.is_set() or single_shot_event.is_set()


def wait_interruptible(seconds):
    deadline = time.time() + seconds
    while should_continue():
        remaining = deadline - time.time()
        if remaining <= 0:
            return
        time.sleep(min(POLL_SECONDS, remaining))


def jittered(seconds):
    # Adds a random amount on top of the configured delay so automated
    # timing doesn't look perfectly mechanical - only ever adds, never
    # subtracts from what the user configured.
    lo = settings["jitter_min"]
    hi = max(lo, settings["jitter_max"])
    return seconds + random.uniform(lo, hi)


def click_active_points(wait_after_last):
    points = settings["points"]
    enabled = settings["enabled"]
    active_points = [p for p, en in zip(points, enabled) if en]
    if not active_points:
        return

    click_gap = settings["click_gap"]
    interval = settings["interval"]
    cycle_delay = settings["cycle_delay"]
    last_index = len(active_points) - 1

    for i, (x, y) in enumerate(active_points):
        if not should_continue():
            break

        mouse_controller.position = (x, y)
        mouse_controller.click(Button.middle)
        wait_interruptible(jittered(click_gap))
        if not should_continue():
            break
        mouse_controller.click(Button.middle)

        is_last = i == last_index
        if is_last:
            # After the last point in the set, wait the longer cycle delay
            # before looping back to the first point - but only when a
            # continuous run will actually follow (single-shot stops here).
            if wait_after_last:
                wait_interruptible(jittered(cycle_delay))
        else:
            wait_interruptible(jittered(interval))


def worker_loop():
    while True:
        if running_event.is_set():
            click_active_points(wait_after_last=True)
            continue

        if single_shot_event.is_set():
            click_active_points(wait_after_last=False)
            single_shot_event.clear()
            continue

        time.sleep(POLL_SECONDS)


class ClickToCoordsApp:
    def __init__(self, root):
        self.root = root
        root.title("ClickToCoords")
        root.resizable(False, False)

        self.point_x_vars = []
        self.point_y_vars = []
        self.capture_labels = []
        self.enabled_vars = [None] * NUM_POINTS
        self.point_widgets = []
        self.capture_listener = None
        self.capturing_index = None

        self.config = load_config()
        initial_dark = bool(self.config.get("dark_mode", False))

        self.style = ttk.Style(root)
        self.dark_mode_var = tk.BooleanVar(value=initial_dark)
        self.apply_theme(dark=initial_dark)

        main = ttk.Frame(root, padding=12)
        main.grid(row=0, column=0)

        ttk.Label(main, text="Points (middle-clicked twice, in order)", font=("", 10, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 6)
        )
        ttk.Label(main, text="On", font=("", 10, "bold")).grid(row=0, column=4, pady=(0, 6))

        for i in range(NUM_POINTS):
            row = i + 1
            x_var = tk.StringVar(value="0")
            y_var = tk.StringVar(value="0")
            self.point_x_vars.append(x_var)
            self.point_y_vars.append(y_var)

            ttk.Label(main, text=f"Point {i + 1}:").grid(row=row, column=0, sticky="w", padx=(0, 6))

            x_entry = ttk.Entry(main, textvariable=x_var, width=6)
            x_entry.grid(row=row, column=1, padx=2)
            y_entry = ttk.Entry(main, textvariable=y_var, width=6)
            y_entry.grid(row=row, column=2, padx=2)

            x_var.trace_add("write", lambda *_a, idx=i: self.sync_settings())
            y_var.trace_add("write", lambda *_a, idx=i: self.sync_settings())

            capture_label = tk.StringVar(value="Capture")
            self.capture_labels.append(capture_label)
            capture_btn = ttk.Button(
                main,
                textvariable=capture_label,
                command=lambda idx=i: self.start_capture(idx),
                width=10,
            )
            capture_btn.grid(row=row, column=3, padx=(6, 0))
            self.point_widgets.append((x_entry, y_entry, capture_btn))

            # Point 1 is always active (the tool needs at least one point);
            # points 2 and 3 can be turned off to run with fewer points.
            if i > 0:
                enabled_var = tk.BooleanVar(value=True)
                self.enabled_vars[i] = enabled_var
                ttk.Checkbutton(
                    main, variable=enabled_var, command=lambda idx=i: self.on_enabled_toggle(idx)
                ).grid(row=row, column=4)

        sep = ttk.Separator(main, orient="horizontal")
        sep.grid(row=NUM_POINTS + 1, column=0, columnspan=5, sticky="ew", pady=8)

        timer_row = NUM_POINTS + 2
        ttk.Label(main, text="Delay between points (s):").grid(row=timer_row, column=0, columnspan=2, sticky="w")
        self.interval_var = tk.StringVar(value=str(DEFAULT_INTERVAL))
        ttk.Entry(main, textvariable=self.interval_var, width=8).grid(row=timer_row, column=2, columnspan=2, sticky="w")
        self.interval_var.trace_add("write", lambda *_a: self.sync_settings())

        gap_row = timer_row + 1
        ttk.Label(main, text="Delay between the 2 clicks (s):").grid(row=gap_row, column=0, columnspan=2, sticky="w")
        self.click_gap_var = tk.StringVar(value=str(DEFAULT_CLICK_GAP))
        ttk.Entry(main, textvariable=self.click_gap_var, width=8).grid(row=gap_row, column=2, columnspan=2, sticky="w")
        self.click_gap_var.trace_add("write", lambda *_a: self.sync_settings())

        cycle_row = gap_row + 1
        ttk.Label(main, text="Delay after full set (s):").grid(row=cycle_row, column=0, columnspan=2, sticky="w")
        self.cycle_delay_var = tk.StringVar(value=str(DEFAULT_CYCLE_DELAY))
        ttk.Entry(main, textvariable=self.cycle_delay_var, width=8).grid(row=cycle_row, column=2, columnspan=2, sticky="w")
        self.cycle_delay_var.trace_add("write", lambda *_a: self.sync_settings())

        jitter_row = cycle_row + 1
        ttk.Label(main, text="Random jitter added (s):").grid(row=jitter_row, column=0, columnspan=2, sticky="w")
        self.jitter_min_var = tk.StringVar(value=str(DEFAULT_JITTER_MIN))
        ttk.Entry(main, textvariable=self.jitter_min_var, width=5).grid(row=jitter_row, column=2, sticky="w")
        ttk.Label(main, text="to").grid(row=jitter_row, column=3)
        self.jitter_max_var = tk.StringVar(value=str(DEFAULT_JITTER_MAX))
        ttk.Entry(main, textvariable=self.jitter_max_var, width=5).grid(row=jitter_row, column=4, sticky="w")
        self.jitter_min_var.trace_add("write", lambda *_a: self.sync_settings())
        self.jitter_max_var.trace_add("write", lambda *_a: self.sync_settings())

        status_row = jitter_row + 1
        self.status_var = tk.StringVar(value="STOPPED")
        self.status_label = ttk.Label(main, textvariable=self.status_var, font=("", 11, "bold"))
        self.status_label.grid(row=status_row, column=0, columnspan=2, sticky="w", pady=(10, 0))

        ttk.Button(main, text="Toggle (F6)", command=self.toggle).grid(
            row=status_row, column=2, columnspan=2, pady=(10, 0), sticky="e"
        )

        single_shot_row = status_row + 1
        self.single_shot_btn = ttk.Button(main, text="Single Use (\\)", command=self.run_single_shot)
        self.single_shot_btn.grid(row=single_shot_row, column=0, columnspan=5, pady=(6, 0), sticky="ew")

        theme_row = single_shot_row + 1
        ttk.Checkbutton(
            main, text="Dark mode", variable=self.dark_mode_var, command=self.on_theme_toggle
        ).grid(row=theme_row, column=0, columnspan=5, sticky="w", pady=(8, 0))

        self._refresh_status()
        self.sync_settings()

    def start_capture(self, index):
        self._cancel_capture()

        self.capturing_index = index
        self.capture_labels[index].set("Click MMB")

        def on_click(x, y, button, pressed):
            if button == Button.middle and pressed:
                self.root.after(0, lambda: self._finish_capture(index, x, y))
                return False  # stop the listener

        listener = mouse.Listener(on_click=on_click)
        self.capture_listener = listener
        listener.start()

    def _finish_capture(self, index, x, y):
        self.point_x_vars[index].set(str(x))
        self.point_y_vars[index].set(str(y))
        self.capture_labels[index].set("Capture")
        if self.capturing_index == index:
            self.capturing_index = None
            self.capture_listener = None

    def _cancel_capture(self):
        if self.capture_listener is not None:
            self.capture_listener.stop()
            self.capture_listener = None
        if self.capturing_index is not None:
            self.capture_labels[self.capturing_index].set("Capture")
            self.capturing_index = None

    def on_enabled_toggle(self, index):
        enabled_var = self.enabled_vars[index]
        state = "normal" if enabled_var.get() else "disabled"
        x_entry, y_entry, _capture_btn = self.point_widgets[index]
        x_entry.configure(state=state)
        y_entry.configure(state=state)
        if not enabled_var.get():
            self._cancel_capture_if(index)
        self.update_status_label()
        self.sync_settings()

    def _cancel_capture_if(self, index):
        if self.capturing_index == index:
            self._cancel_capture()

    def sync_settings(self):
        points = []
        for x_var, y_var in zip(self.point_x_vars, self.point_y_vars):
            try:
                x = int(float(x_var.get()))
                y = int(float(y_var.get()))
            except ValueError:
                x, y = 0, 0
            points.append((x, y))
        settings["points"] = points
        settings["enabled"] = [
            enabled_var.get() if enabled_var is not None else True for enabled_var in self.enabled_vars
        ]

        try:
            settings["interval"] = max(0.0, float(self.interval_var.get()))
        except ValueError:
            pass

        try:
            settings["click_gap"] = max(0.0, float(self.click_gap_var.get()))
        except ValueError:
            pass

        try:
            settings["cycle_delay"] = max(0.0, float(self.cycle_delay_var.get()))
        except ValueError:
            pass

        try:
            settings["jitter_min"] = max(0.0, float(self.jitter_min_var.get()))
        except ValueError:
            pass

        try:
            settings["jitter_max"] = max(0.0, float(self.jitter_max_var.get()))
        except ValueError:
            pass

    def toggle(self):
        if running_event.is_set():
            running_event.clear()
        else:
            self._cancel_capture()
            single_shot_event.clear()
            running_event.set()
        self.update_status_label()

    def run_single_shot(self):
        if single_shot_event.is_set():
            single_shot_event.clear()  # a click of the button/hotkey again cancels it
        elif not running_event.is_set():
            self._cancel_capture()
            single_shot_event.set()
        self.update_status_label()

    def _refresh_status(self):
        self.update_status_label()
        self.root.after(STATUS_REFRESH_MS, self._refresh_status)

    def update_status_label(self):
        running = running_event.is_set()
        single_shot_active = single_shot_event.is_set()
        busy = running or single_shot_active

        if running:
            self.status_var.set("RUNNING")
            self.status_label.configure(foreground=COLOR_RUNNING)
        elif single_shot_active:
            self.status_var.set("RUNNING (once)")
            self.status_label.configure(foreground=COLOR_RUNNING)
        else:
            self.status_var.set("STOPPED")
            self.status_label.configure(foreground=COLOR_STOPPED)

        # Capture clashes with the automation's own synthetic clicks, so
        # disable Capture buttons while busy (respecting each point's own
        # enabled/disabled state once stopped again).
        for i, (_, _, capture_btn) in enumerate(self.point_widgets):
            enabled_var = self.enabled_vars[i]
            point_enabled = enabled_var is None or enabled_var.get()
            capture_btn.configure(state="normal" if (point_enabled and not busy) else "disabled")

        # Single Use stays clickable during its own run (to allow cancelling
        # it), but not while continuous automation is running.
        self.single_shot_btn.configure(state="disabled" if running else "normal")

    def on_theme_toggle(self):
        dark = self.dark_mode_var.get()
        self.apply_theme(dark=dark)
        self.config["dark_mode"] = dark
        save_config(self.config)

    def apply_theme(self, dark):
        colors = DARK_COLORS if dark else LIGHT_COLORS
        style = self.style
        style.theme_use("clam")
        style.configure(".", background=colors["bg"], foreground=colors["fg"])
        style.configure("TFrame", background=colors["bg"])
        style.configure("TLabel", background=colors["bg"], foreground=colors["fg"])
        style.configure("TCheckbutton", background=colors["bg"], foreground=colors["fg"])
        style.map("TCheckbutton", background=[("active", colors["bg"])])
        style.configure("TSeparator", background=colors["bg"])
        style.configure(
            "TButton", background=colors["button_bg"], foreground=colors["fg"], bordercolor=colors["bg"]
        )
        style.map("TButton", background=[("active", colors["active_bg"]), ("disabled", colors["bg"])])
        style.configure(
            "TEntry",
            fieldbackground=colors["entry_bg"],
            foreground=colors["entry_fg"],
            insertcolor=colors["fg"],
        )
        style.map("TEntry", fieldbackground=[("disabled", colors["bg"])])
        self.root.configure(background=colors["bg"])


def main():
    root = tk.Tk()
    app = ClickToCoordsApp(root)

    # Hotkey callbacks run on the pynput listener thread, so marshal the
    # GUI update back onto the Tk main thread via root.after.
    def handle_toggle():
        root.after(0, app.toggle)

    def handle_single_shot():
        root.after(0, app.run_single_shot)

    hotkeys = keyboard.GlobalHotKeys({"<f6>": handle_toggle, "\\": handle_single_shot})
    hotkeys.start()

    worker = threading.Thread(target=worker_loop, daemon=True)
    worker.start()

    def on_close():
        running_event.clear()
        app._cancel_capture()
        hotkeys.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
