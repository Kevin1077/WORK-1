"""
ui/print_settings.py — Comprehensive Print Settings & Page Adjustments UI for Étoffe Laundry
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os

from ui.theme import COLORS, FONTS
from ui.widgets import make_btn, make_entry
import database as db


def _get_system_printers(fast_only: bool = False):
    """Return a comprehensive list of available printer names on Windows."""
    printers_set = {"(System Default Printer)"}
    if os.name == "nt":
        # 1. Fast native win32print EnumPrinters (0ms response)
        try:
            import win32print
            flags = (
                win32print.PRINTER_ENUM_LOCAL
                | win32print.PRINTER_ENUM_CONNECTIONS
                | win32print.PRINTER_ENUM_SHARED
                | win32print.PRINTER_ENUM_NETWORK
            )
            for p in win32print.EnumPrinters(flags):
                if len(p) > 2 and p[2]:
                    printers_set.add(p[2])
        except Exception:
            pass

        # 2. Try WMI Win32_Printer via powershell as fallback only if fast_only is False and win32print returned nothing
        if not fast_only and len(printers_set) <= 1:
            try:
                import subprocess
                cmd = "powershell -Command \"Get-WmiObject Win32_Printer | Select-Object -ExpandProperty Name\""
                res = subprocess.run(cmd, capture_output=True, text=True, shell=True, creationflags=0x08000000)
                if res.returncode == 0 and res.stdout:
                    for line in res.stdout.splitlines():
                        name = line.strip()
                        if name:
                            printers_set.add(name)
            except Exception:
                pass

    res_list = ["(System Default Printer)"]
    sorted_others = sorted([p for p in printers_set if p != "(System Default Printer)"])
    res_list.extend(sorted_others)
    return res_list


class PrintSettingsFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self._build()
        self.refresh()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=COLORS["card_bg"])
        hdr.pack(fill="x")
        tk.Label(
            hdr, text="Print Settings & Page Adjustments", bg=COLORS["card_bg"],
            fg=COLORS["accent"], font=FONTS["title"]
        ).pack(side="left", padx=20, pady=14)

        make_btn(hdr, "🔄 Refresh Printers", lambda: self.refresh(full_scan=True), "neutral").pack(side="right", padx=20, pady=14)
        tk.Frame(self, bg=COLORS["border"], height=1).pack(fill="x")

        # Scrollable container for settings options
        canvas = tk.Canvas(self, bg=COLORS["bg"], highlightthickness=0)
        v_scroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        body = tk.Frame(canvas, bg=COLORS["bg"])

        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.configure(yscrollcommand=v_scroll.set)

        def _on_canvas_configure(e):
            canvas.itemconfig(canvas_window, width=e.width)

        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.pack(side="left", fill="both", expand=True, padx=(24, 0), pady=16)
        v_scroll.pack(side="right", fill="y")

        # ── Section 1: Workflow Mode & Copies ─────────────────────────────────
        mode_card = tk.Frame(body, bg=COLORS["card_bg"], padx=20, pady=16)
        mode_card.pack(fill="x", pady=(0, 16))

        tk.Label(
            mode_card, text="1. Print Workflow & Copies",
            bg=COLORS["card_bg"], fg=COLORS["text"], font=FONTS["bold"]
        ).pack(anchor="w", pady=(0, 8))

        self._mode_var = tk.StringVar(value="direct")

        rb_row = tk.Frame(mode_card, bg=COLORS["card_bg"])
        rb_row.pack(fill="x", pady=(0, 12))

        rb_direct = tk.Radiobutton(
            rb_row,
            text="⚡ Direct Automatic Print (No Preview)",
            variable=self._mode_var,
            value="direct",
            bg=COLORS["card_bg"],
            fg=COLORS["text"],
            selectcolor=COLORS["card_bg"],
            activebackground=COLORS["card_bg"],
            activeforeground=COLORS["accent"],
            font=FONTS["bold"]
        )
        rb_direct.pack(side="left", padx=(0, 20))

        rb_preview = tk.Radiobutton(
            rb_row,
            text="👁️ Open Preview Window (Manual print)",
            variable=self._mode_var,
            value="preview",
            bg=COLORS["card_bg"],
            fg=COLORS["text"],
            selectcolor=COLORS["card_bg"],
            activebackground=COLORS["card_bg"],
            activeforeground=COLORS["accent"],
            font=FONTS["default"]
        )
        rb_preview.pack(side="left")

        # Copies sub-row
        copies_row = tk.Frame(mode_card, bg=COLORS["card_bg"])
        copies_row.pack(fill="x")

        tk.Label(copies_row, text="Receipt Copies:", bg=COLORS["card_bg"], fg=COLORS["text_dim"], font=FONTS["bold"]).pack(side="left", padx=(0, 8))
        self._r_copies_var = tk.StringVar(value="1")
        r_copies_cb = ttk.Combobox(copies_row, textvariable=self._r_copies_var, values=["1", "2", "3", "4"], state="readonly", width=5)
        r_copies_cb.pack(side="left", padx=(0, 24))

        tk.Label(copies_row, text="Barcode Copies / Garment:", bg=COLORS["card_bg"], fg=COLORS["text_dim"], font=FONTS["bold"]).pack(side="left", padx=(0, 8))
        self._b_copies_var = tk.StringVar(value="1")
        b_copies_cb = ttk.Combobox(copies_row, textvariable=self._b_copies_var, values=["1", "2", "3", "4"], state="readonly", width=5)
        b_copies_cb.pack(side="left")

        # ── Section 2: Receipt Page & Print Adjustments ────────────────────────
        r_card = tk.Frame(body, bg=COLORS["card_bg"], padx=20, pady=16)
        r_card.pack(fill="x", pady=(0, 16))

        tk.Label(
            r_card, text="2. Customer Receipt Adjustments (Size, Scale & Margins)",
            bg=COLORS["card_bg"], fg=COLORS["text"], font=FONTS["bold"]
        ).pack(anchor="w", pady=(0, 12))

        # Size & Scale row
        r_grid1 = tk.Frame(r_card, bg=COLORS["card_bg"])
        r_grid1.pack(fill="x", pady=(0, 10))

        tk.Label(r_grid1, text="Paper Size:", bg=COLORS["card_bg"], fg=COLORS["text_dim"], font=FONTS["bold"], width=14, anchor="w").pack(side="left")
        self._r_size_var = tk.StringVar(value="80mm Thermal (Standard POS)")
        self._r_size_map = {
            "80mm Thermal (Standard POS)": "80mm",
            "58mm Thermal (Compact POS)": "58mm",
            "A5 Sheet (Half Page)": "A5",
            "A4 Sheet (Full Page)": "A4",
        }
        self._r_size_cb = ttk.Combobox(r_grid1, textvariable=self._r_size_var, values=list(self._r_size_map.keys()), state="readonly", width=28)
        self._r_size_cb.pack(side="left", padx=(0, 24))

        tk.Label(r_grid1, text="Print Scale:", bg=COLORS["card_bg"], fg=COLORS["text_dim"], font=FONTS["bold"], width=12, anchor="w").pack(side="left")
        self._r_scale_var = tk.StringVar(value="100%")
        self._r_scale_cb = ttk.Combobox(r_grid1, textvariable=self._r_scale_var, values=["80%", "90%", "100%", "110%", "120%"], state="readonly", width=10)
        self._r_scale_cb.pack(side="left")

        # Margins row
        r_grid2 = tk.Frame(r_card, bg=COLORS["card_bg"])
        r_grid2.pack(fill="x")

        tk.Label(r_grid2, text="Left Margin (mm):", bg=COLORS["card_bg"], fg=COLORS["text_dim"], font=FONTS["bold"], width=14, anchor="w").pack(side="left")
        self._r_mleft_var = tk.StringVar(value="0")
        r_mleft_sp = tk.Spinbox(r_grid2, from_=0, to=30, textvariable=self._r_mleft_var, width=6, bg=COLORS["input_bg"], fg=COLORS["text"])
        r_mleft_sp.pack(side="left", padx=(0, 24))

        tk.Label(r_grid2, text="Top Margin (mm):", bg=COLORS["card_bg"], fg=COLORS["text_dim"], font=FONTS["bold"], width=12, anchor="w").pack(side="left")
        self._r_mtop_var = tk.StringVar(value="0")
        r_mtop_sp = tk.Spinbox(r_grid2, from_=0, to=30, textvariable=self._r_mtop_var, width=6, bg=COLORS["input_bg"], fg=COLORS["text"])
        r_mtop_sp.pack(side="left")

        # ── Section 3: Barcode / Dispatch Label Adjustments ─────────────────────
        b_card = tk.Frame(body, bg=COLORS["card_bg"], padx=20, pady=16)
        b_card.pack(fill="x", pady=(0, 16))

        tk.Label(
            b_card, text="3. Barcode Label Adjustments (Size, Scale & Margins)",
            bg=COLORS["card_bg"], fg=COLORS["text"], font=FONTS["bold"]
        ).pack(anchor="w", pady=(0, 12))

        b_grid1 = tk.Frame(b_card, bg=COLORS["card_bg"])
        b_grid1.pack(fill="x", pady=(0, 10))

        tk.Label(b_grid1, text="Label Size:", bg=COLORS["card_bg"], fg=COLORS["text_dim"], font=FONTS["bold"], width=14, anchor="w").pack(side="left")
        self._b_size_var = tk.StringVar(value="35mm x 40mm (Standard)")
        self._b_size_map = {
            "35mm x 40mm (Standard)": "35x40mm",
            "50mm x 30mm": "50x30mm",
            "40mm x 30mm": "40x30mm",
            "38mm x 25mm": "38x25mm",
        }
        self._b_size_cb = ttk.Combobox(b_grid1, textvariable=self._b_size_var, values=list(self._b_size_map.keys()), state="readonly", width=28)
        self._b_size_cb.pack(side="left", padx=(0, 24))

        tk.Label(b_grid1, text="Print Scale:", bg=COLORS["card_bg"], fg=COLORS["text_dim"], font=FONTS["bold"], width=12, anchor="w").pack(side="left")
        self._b_scale_var = tk.StringVar(value="100%")
        self._b_scale_cb = ttk.Combobox(b_grid1, textvariable=self._b_scale_var, values=["80%", "90%", "100%", "110%", "120%"], state="readonly", width=10)
        self._b_scale_cb.pack(side="left")

        b_grid2 = tk.Frame(b_card, bg=COLORS["card_bg"])
        b_grid2.pack(fill="x")

        tk.Label(b_grid2, text="Left Margin (mm):", bg=COLORS["card_bg"], fg=COLORS["text_dim"], font=FONTS["bold"], width=14, anchor="w").pack(side="left")
        self._b_mleft_var = tk.StringVar(value="0")
        b_mleft_sp = tk.Spinbox(b_grid2, from_=0, to=30, textvariable=self._b_mleft_var, width=6, bg=COLORS["input_bg"], fg=COLORS["text"])
        b_mleft_sp.pack(side="left", padx=(0, 24))

        tk.Label(b_grid2, text="Top Margin (mm):", bg=COLORS["card_bg"], fg=COLORS["text_dim"], font=FONTS["bold"], width=12, anchor="w").pack(side="left")
        self._b_mtop_var = tk.StringVar(value="0")
        b_mtop_sp = tk.Spinbox(b_grid2, from_=0, to=30, textvariable=self._b_mtop_var, width=6, bg=COLORS["input_bg"], fg=COLORS["text"])
        b_mtop_sp.pack(side="left")

        # ── Section 4: Target Printers & Actions ────────────────────────────────
        printer_card = tk.Frame(body, bg=COLORS["card_bg"], padx=20, pady=16)
        printer_card.pack(fill="x", pady=(0, 16))

        tk.Label(
            printer_card, text="4. Printer Devices & Test Print",
            bg=COLORS["card_bg"], fg=COLORS["text"], font=FONTS["bold"]
        ).pack(anchor="w", pady=(0, 12))

        printers_list = _get_system_printers()

        # Receipt printer row
        r_p_row = tk.Frame(printer_card, bg=COLORS["card_bg"])
        r_p_row.pack(fill="x", pady=(0, 10))

        tk.Label(r_p_row, text="Receipt Printer:", bg=COLORS["card_bg"], fg=COLORS["text_dim"], font=FONTS["bold"], width=16, anchor="w").pack(side="left")
        self._receipt_printer_var = tk.StringVar()
        self._receipt_cb = ttk.Combobox(r_p_row, textvariable=self._receipt_printer_var, values=printers_list, state="normal", width=38)
        self._receipt_cb.pack(side="left", padx=(0, 10))

        # Barcode printer row
        d_p_row = tk.Frame(printer_card, bg=COLORS["card_bg"])
        d_p_row.pack(fill="x", pady=(0, 16))

        tk.Label(d_p_row, text="Barcode Printer:", bg=COLORS["card_bg"], fg=COLORS["text_dim"], font=FONTS["bold"], width=16, anchor="w").pack(side="left")
        self._dispatch_printer_var = tk.StringVar()
        self._dispatch_cb = ttk.Combobox(d_p_row, textvariable=self._dispatch_printer_var, values=printers_list, state="normal", width=38)
        self._dispatch_cb.pack(side="left", padx=(0, 10))

        # Save and Test Actions
        btn_row = tk.Frame(printer_card, bg=COLORS["card_bg"])
        btn_row.pack(fill="x")

        make_btn(btn_row, "💾 Save All Settings", self._save_settings, "primary").pack(side="left", padx=(0, 12))
        make_btn(btn_row, "🖨️ Test Receipt Print", self._test_receipt_print, "neutral").pack(side="left", padx=(0, 8))
        make_btn(btn_row, "🏷️ Test Barcode Print", self._test_barcode_print, "neutral").pack(side="left")

        self._status_lbl = tk.Label(
            printer_card, text="", bg=COLORS["card_bg"],
            fg=COLORS["success"], font=FONTS["bold"]
        )
        self._status_lbl.pack(anchor="w", pady=(12, 0))

    def refresh(self, full_scan: bool = False):
        """Load current settings from database."""
        mode = db.get_setting("print_mode", "direct")
        self._mode_var.set(mode)

        r_printer = db.get_setting("printer_receipt", "")
        self._receipt_printer_var.set(r_printer if r_printer else "(System Default Printer)")

        d_printer = db.get_setting("printer_dispatch", "")
        self._dispatch_printer_var.set(d_printer if d_printer else "(System Default Printer)")

        # Receipt adjustments
        r_size = db.get_setting("receipt_paper_size", "80mm")
        inv_r_size = {v: k for k, v in self._r_size_map.items()}
        self._r_size_var.set(inv_r_size.get(r_size, "80mm Thermal (Standard POS)"))

        r_scale = db.get_setting("receipt_scale", "100")
        self._r_scale_var.set(f"{r_scale}%")
        self._r_mleft_var.set(db.get_setting("receipt_margin_left", "0"))
        self._r_mtop_var.set(db.get_setting("receipt_margin_top", "0"))
        self._r_copies_var.set(db.get_setting("receipt_copies", "1"))

        # Barcode adjustments
        b_size = db.get_setting("barcode_label_size", "35x40mm")
        inv_b_size = {v: k for k, v in self._b_size_map.items()}
        self._b_size_var.set(inv_b_size.get(b_size, "35mm x 40mm (Standard)"))

        b_scale = db.get_setting("barcode_scale", "100")
        self._b_scale_var.set(f"{b_scale}%")
        self._b_mleft_var.set(db.get_setting("barcode_margin_left", "0"))
        self._b_mtop_var.set(db.get_setting("barcode_margin_top", "0"))
        self._b_copies_var.set(db.get_setting("barcode_copies", "1"))

        # Update available printers list (fast 0ms native pass on tab switch)
        printers_list = _get_system_printers(fast_only=not full_scan)
        self._receipt_cb["values"] = printers_list
        self._dispatch_cb["values"] = printers_list

    def _save_settings(self):
        mode = self._mode_var.get()
        r_p = self._receipt_printer_var.get()
        if r_p == "(System Default Printer)":
            r_p = ""
        d_p = self._dispatch_printer_var.get()
        if d_p == "(System Default Printer)":
            d_p = ""

        db.set_setting("print_mode", mode)
        db.set_setting("printer_receipt", r_p)
        db.set_setting("printer_dispatch", d_p)

        # Save receipt adjustments
        r_size_code = self._r_size_map.get(self._r_size_var.get(), "80mm")
        r_scale_val = self._r_scale_var.get().replace("%", "").strip()
        db.set_setting("receipt_paper_size", r_size_code)
        db.set_setting("receipt_scale", r_scale_val)
        db.set_setting("receipt_margin_left", self._r_mleft_var.get().strip() or "0")
        db.set_setting("receipt_margin_top", self._r_mtop_var.get().strip() or "0")
        db.set_setting("receipt_copies", self._r_copies_var.get().strip() or "1")

        # Save barcode adjustments
        b_size_code = self._b_size_map.get(self._b_size_var.get(), "35x40mm")
        b_scale_val = self._b_scale_var.get().replace("%", "").strip()
        db.set_setting("barcode_label_size", b_size_code)
        db.set_setting("barcode_scale", b_scale_val)
        db.set_setting("barcode_margin_left", self._b_mleft_var.get().strip() or "0")
        db.set_setting("barcode_margin_top", self._b_mtop_var.get().strip() or "0")
        db.set_setting("barcode_copies", self._b_copies_var.get().strip() or "1")

        self._status_lbl.config(
            text="✅ Print & Page adjustments saved! All printing will use these exact settings."
        )

    def _test_receipt_print(self):
        self._save_settings()
        sample_order = {
            "order_id": 999,
            "order_date": "2026-08-20",
            "payment_method": "Cash",
            "name": "Test Customer",
            "phone": "9876543210",
            "place": "Pala",
            "address": "Main Street",
            "items": [
                {"cloth_type": "Shirt", "quantity": 1, "price_per_unit": 20.0, "subtotal": 20.0, "item_number": 1}
            ],
            "total_amount": 20.0,
            "notes": "Test Print"
        }
        try:
            from utils.receipt import open_receipt
            open_receipt(sample_order)
            self._status_lbl.config(text="🖨️ Test receipt sent to printer with updated adjustments!")
        except Exception as e:
            messagebox.showerror("Test Print Error", str(e), parent=self)

    def _test_barcode_print(self):
        self._save_settings()
        sample_order = {
            "order_id": 999,
            "name": "Test Customer",
            "notes": "Test Barcode",
            "items": [
                {"cloth_type": "Shirt", "quantity": 1, "item_notes": "Silk Care"}
            ]
        }
        try:
            from utils.dispatch_slip import open_dispatch_slip
            open_dispatch_slip(sample_order)
            self._status_lbl.config(text="🏷️ Test barcode slip sent to printer with updated adjustments!")
        except Exception as e:
            messagebox.showerror("Test Print Error", str(e), parent=self)
