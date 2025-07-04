#!/usr/bin/env python3
import tkinter as tk
from datetime import datetime

def main():
    # Create main window
    root = tk.Tk()
    root.title("OpenAI Stock Price")

    # Window size and centering
    w, h = 400, 140
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.resizable(False, False)

    # Message to display
    msg = (
        "OpenAI is a privately held company\n"
        "and does not have a publicly-traded stock price.\n\n"
        f"Checked: {datetime.now():%Y-%m-%d %H:%M:%S}"
    )
    lbl = tk.Label(root, text=msg, font=("Segoe UI", 11), justify="center")
    lbl.pack(expand=True, padx=10, pady=10)

    # Start GUI loop
    root.mainloop()

if __name__ == "__main__":
    main()
