from datetime import datetime
import json
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageDraw
import pystray

# Διαδρομή για το εικονίδιο
ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clippy.ico")

def get_tray_icon_image():
    """Φορτώνει το δικό σου αρχείο .ico, ή φτιάχνει ένα default αν δεν υπάρχει."""
    if os.path.exists(ICON_PATH):
        return Image.open(ICON_PATH)
    else:
        # Fallback εικονίδιο αν λείπει το αρχείο .ico
        image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((8, 8, 56, 56), fill='#4A90E2')
        return image

class AdvancedReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Scheduled Reminder Manager")
        self.root.geometry("460x450")

        # 1. Ορισμός εικονιδίου στο παράθυρο της εφαρμογής (πάνω αριστερά)
        if os.path.exists(ICON_PATH):
            try:
                self.root.iconbitmap(ICON_PATH)
            except Exception:
                pass

        self.reminders = load_reminders()
        self.tray_icon = None

# Optional dependencies for audio and system tray
try:
    import winsound
except ImportError:
    winsound = None

try:
    from PIL import Image, ImageDraw
    import pystray
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

DATA_FILE = os.path.expanduser("~/reminders_data.json")

def load_reminders():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_reminders(reminders):
    with open(DATA_FILE, "w") as f:
        json.dump(reminders, f, indent=2)

def play_alert_sound():
    """Play native alert audio if available."""
    if winsound:
        winsound.MessageBeep(winsound.MB_ICONASTERISK)

def create_tray_icon():
    """Generate a simple dynamic bell icon for the system tray."""
    image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 56, 56), fill='#4A90E2')
    return image

class AdvancedReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Scheduled Reminder Manager")
        self.root.geometry("460x450")

        self.reminders = load_reminders()
        self.tray_icon = None

        # UI Setup
        self.frame = ttk.Frame(root, padding="10")
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Input Section - Text
        self.entry_label = ttk.Label(self.frame, text="New Reminder Text:")
        self.entry_label.pack(anchor=tk.W, pady=(0, 2))

        self.entry = ttk.Entry(self.frame, width=40)
        self.entry.pack(fill=tk.X, pady=(0, 8))
        # Bind Enter key on text entry field
        self.entry.bind("<Return>", lambda event: self.add_reminder())

        # Input Section - Time Selection UI
        self.use_time_var = tk.BooleanVar(value=False)
        self.time_checkbox = ttk.Checkbutton(
            self.frame, 
            text="Set Specific Time (24hr)", 
            variable=self.use_time_var,
            command=self.toggle_time_pickers
        )
        self.time_checkbox.pack(anchor=tk.W, pady=(0, 4))

        self.time_frame = ttk.Frame(self.frame)
        self.time_frame.pack(anchor=tk.W, pady=(0, 8))

        # Hour Spinner (00 to 23)
        self.hour_spin = ttk.Spinbox(
            self.time_frame, 
            from_=0, 
            to=23, 
            width=3, 
            format="%02.0f", 
            wrap=True,
            state="disabled"
        )
        self.hour_spin.set("09")
        self.hour_spin.pack(side=tk.LEFT)
        # Bind Enter key on hour spinner
        self.hour_spin.bind("<Return>", lambda event: self.add_reminder())

        ttk.Label(self.time_frame, text=" : ").pack(side=tk.LEFT)

        # Minute Spinner (00 to 59)
        self.minute_spin = ttk.Spinbox(
            self.time_frame, 
            from_=0, 
            to=59, 
            width=3, 
            format="%02.0f", 
            wrap=True,
            state="disabled"
        )
        self.minute_spin.set("00")
        self.minute_spin.pack(side=tk.LEFT)
        # Bind Enter key on minute spinner
        self.minute_spin.bind("<Return>", lambda event: self.add_reminder())

        self.add_button = ttk.Button(self.frame, text="Add Reminder", command=self.add_reminder)
        self.add_button.pack(anchor=tk.W, pady=(4, 10))

        # List Section
        self.list_label = ttk.Label(self.frame, text="Active Reminders:")
        self.list_label.pack(anchor=tk.W, pady=(0, 2))

        self.listbox = tk.Listbox(self.frame, height=8)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.delete_button = ttk.Button(self.frame, text="Delete Selected", command=self.delete_reminder)
        self.delete_button.pack(anchor=tk.E)

        self.refresh_listbox()
        self.show_startup_popup()

        # Handle window minimize/close to minimize to tray
        self.root.protocol('WM_DELETE_WINDOW', self.minimize_to_tray)

        if TRAY_AVAILABLE:
            self.setup_tray()

        # Start background schedule checker
        self.check_schedule()

    def toggle_time_pickers(self):
        """Enable or disable hour/minute spinners based on checkbox."""
        state = "normal" if self.use_time_var.get() else "disabled"
        self.hour_spin.config(state=state)
        self.minute_spin.config(state=state)

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for item in self.reminders:
            time_str = f" [{item['time']}]" if item.get('time') else " [Startup]"
            self.listbox.insert(tk.END, f"{item['text']}{time_str}")

    def add_reminder(self):
        text = self.entry.get().strip()
        time_val = ""

        if self.use_time_var.get():
            try:
                h = int(self.hour_spin.get())
                m = int(self.minute_spin.get())
                time_val = f"{h:02d}:{m:02d}"
            except ValueError:
                messagebox.showerror("Invalid Time", "Please enter valid numbers for time.")
                return

        if text:
            new_item = {"text": text, "time": time_val, "triggered_today": False}
            self.reminders.append(new_item)
            save_reminders(self.reminders)
            self.refresh_listbox()
            self.entry.delete(0, tk.END)
            self.use_time_var.set(False)
            self.toggle_time_pickers()

    def delete_reminder(self):
        selected = self.listbox.curselection()
        if selected:
            idx = selected[0]
            del self.reminders[idx]
            save_reminders(self.reminders)
            self.refresh_listbox()

    def show_startup_popup(self):
        startup_items = [r['text'] for r in self.reminders if not r.get('time')]
        if startup_items:
            play_alert_sound()
            msg = "Startup Reminders:\n\n" + "\n".join(f"• {item}" for item in startup_items)
            messagebox.showinfo("Startup Reminders", msg)

    def check_schedule(self):
        """Runs in background using root.after to check if time matches."""
        now_str = datetime.now().strftime("%H:%M")
        
        for item in self.reminders:
            target_time = item.get("time")
            if target_time == now_str and not item.get("triggered_today"):
                play_alert_sound()
                self.restore_from_tray()
                messagebox.showinfo("Scheduled Reminder", f"⏰ Reminder: {item['text']}")
                item["triggered_today"] = True
                save_reminders(self.reminders)
            elif target_time != now_str:
                item["triggered_today"] = False

        self.root.after(10000, self.check_schedule)

    def setup_tray(self):
        """Ρύθμιση του System Tray με το δικό σου εικονίδιο."""
        menu = pystray.Menu(
            pystray.MenuItem("Open Manager", self.restore_from_tray),
            pystray.MenuItem("Exit Completely", self.exit_app)
        )
        # Χρήση της συνάρτησης get_tray_icon_image()
        self.tray_icon = pystray.Icon("ReminderApp", get_tray_icon_image(), "Reminder Manager", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def minimize_to_tray(self):
        """Hide window to system tray."""
        if TRAY_AVAILABLE:
            self.root.withdraw()
        else:
            self.exit_app()

    def restore_from_tray(self):
        """Restore window from system tray."""
        self.root.deiconify()
        self.root.lift()

    def exit_app(self):
        """Cleanly close the application."""
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()
        sys.exit()

if __name__ == "__main__":
    root = tk.Tk()
    app = AdvancedReminderApp(root)
    root.mainloop()