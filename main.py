"""
main.py — Entry point for Étoffe Laundry Management System
"""
import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from database import init_db
from ui.app_window import AppWindow


def main():
    init_db()
    root = tk.Tk()
    app = AppWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
