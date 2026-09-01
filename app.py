"""ClickToCoords - cycles a middle-click pair across 3 saved screen coordinates.

Runs as a local desktop app (Tkinter GUI). Press F6 anywhere (even when this
window isn't focused) to toggle the automation on/off.
"""
import threading
import time
import tkinter as tk
from tkinter import ttk

from pynput import keyboard, mouse
from pynput.mouse import Button

NUM_POINTS = 3
DEFAULT_INTERVAL = 1.0
DEFAULT_CLICK_GAP = 0.1
DEFAULT_CYCLE_DELAY = 10.0
POLL_SECONDS = 0.05
CAPTURE_COUNTDOWN = 3

mouse_controller = mouse.Controller()
running_event = threading.Event()

# Plain-Python settings mirror of the GUI state. The worker thread reads
# this instead of touching Tkinter variables directly, since Tk vars
# aren't safe to access off the main thread.
settings = {
    "points": [(0, 0) for _ in range(NUM_POINTS)],
    "enabled": [True] * NUM_POINTS,
    "interval": DEFAULT_INTERVAL,
    "click_gap": DEFAULT_CLICK_GAP,
    "cycle_delay": DEFAULT_CYCLE_DELAY,
}


def wait_interruptible(seconds):
    deadline = time.time() + seconds
    while running_event.is_set():
        remaining = deadline - time.time()
        if remaining <= 0:
            return
        time.sleep(min(POLL_SECONDS, remaining))


def worker_loop():
    while True:
        if not running_event.is_set():
            time.sleep(POLL_SECONDS)
            continue

        points = settings["points"]
        enabled = settings["enabled"]
        active_points = [p for p, en in zip(points, enabled) if en]
        click_gap = settings["click_gap"]
        interval = settings["interval"]
        cycle_delay = settings["cycle_delay"]

        if not active_points:
            time.sleep(POLL_SECONDS)
            continue

        last_index = len(active_points) - 1

        for i, (x, y) in enumerate(active_points):
            if not running_event.is_set():
                break

            mouse_controller.position = (x, y)
            mouse_controller.click(Button.middle)
            wait_interruptible(click_gap)
            if not running_event.is_set():
                break
            mouse_controller.click(Button.middle)

            # After the last point in the set, wait the longer cycle delay
            # instead of the normal point-to-point interval before looping
            # back to the first point.
            wait_interruptible(cycle_delay if i == last_index else interval)


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

        status_row = cycle_row + 1
        self.status_var = tk.StringVar(value="STOPPED")
        self.status_label = ttk.Label(main, textvariable=self.status_var, font=("", 11, "bold"))
        self.status_label.grid(row=status_row, column=0, columnspan=2, sticky="w", pady=(10, 0))

        ttk.Button(main, text="Toggle (F6)", command=self.toggle).grid(
            row=status_row, column=2, columnspan=2, pady=(10, 0), sticky="e"
        )

        self.update_status_label()
        self.sync_settings()

    def start_capture(self, index):
        self._countdown(index, CAPTURE_COUNTDOWN)

    def _countdown(self, index, seconds_left):
        if seconds_left <= 0:
            x, y = mouse_controller.position
            self.point_x_vars[index].set(str(x))
            self.point_y_vars[index].set(str(y))
            self.capture_labels[index].set("Capture")
            return
        self.capture_labels[index].set(f"...{seconds_left}")
        self.root.after(1000, lambda: self._countdown(index, seconds_left - 1))

    def on_enabled_toggle(self, index):
        enabled_var = self.enabled_vars[index]
        state = "normal" if enabled_var.get() else "disabled"
        for widget in self.point_widgets[index]:
            widget.configure(state=state)
        self.sync_settings()

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

    def toggle(self):
        if running_event.is_set():
            running_event.clear()
        else:
            running_event.set()
        self.update_status_label()

    def update_status_label(self):
        if running_event.is_set():
            self.status_var.set("RUNNING")
            self.status_label.configure(foreground="green")
        else:
            self.status_var.set("STOPPED")
            self.status_label.configure(foreground="red")


def main():
    root = tk.Tk()
    app = ClickToCoordsApp(root)

    # Hotkey callbacks run on the pynput listener thread, so marshal the
    # GUI update back onto the Tk main thread via root.after.
    def handle_toggle():
        root.after(0, app.toggle)

    hotkeys = keyboard.GlobalHotKeys({"<f6>": handle_toggle})
    hotkeys.start()

    worker = threading.Thread(target=worker_loop, daemon=True)
    worker.start()

    def on_close():
        running_event.clear()
        hotkeys.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
