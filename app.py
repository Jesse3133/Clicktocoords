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
POLL_SECONDS = 0.05
CAPTURE_COUNTDOWN = 3

mouse_controller = mouse.Controller()
running_event = threading.Event()

# Plain-Python settings mirror of the GUI state. The worker thread reads
# this instead of touching Tkinter variables directly, since Tk vars
# aren't safe to access off the main thread.
settings = {
    "points": [(0, 0) for _ in range(NUM_POINTS)],
    "interval": DEFAULT_INTERVAL,
    "click_gap": DEFAULT_CLICK_GAP,
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
        click_gap = settings["click_gap"]
        interval = settings["interval"]

        for x, y in points:
            if not running_event.is_set():
                break

            mouse_controller.position = (x, y)
            mouse_controller.click(Button.middle)
            wait_interruptible(click_gap)
            if not running_event.is_set():
                break
            mouse_controller.click(Button.middle)

            wait_interruptible(interval)


class ClickToCoordsApp:
    def __init__(self, root):
        self.root = root
        root.title("ClickToCoords")
        root.resizable(False, False)

        self.point_x_vars = []
        self.point_y_vars = []
        self.capture_labels = []

        main = ttk.Frame(root, padding=12)
        main.grid(row=0, column=0)

        ttk.Label(main, text="Points (middle-clicked twice, in order)", font=("", 10, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 6)
        )

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
            ttk.Button(
                main,
                textvariable=capture_label,
                command=lambda idx=i: self.start_capture(idx),
                width=10,
            ).grid(row=row, column=3, padx=(6, 0))

        sep = ttk.Separator(main, orient="horizontal")
        sep.grid(row=NUM_POINTS + 1, column=0, columnspan=4, sticky="ew", pady=8)

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

        status_row = gap_row + 1
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

        try:
            settings["interval"] = max(0.0, float(self.interval_var.get()))
        except ValueError:
            pass

        try:
            settings["click_gap"] = max(0.0, float(self.click_gap_var.get()))
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
