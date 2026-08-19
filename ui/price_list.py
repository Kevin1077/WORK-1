"""
ui/price_list.py — Manage standard cloth prices
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from ui.theme   import COLORS, FONTS
from ui.widgets import make_btn, make_entry, build_tree
import database as db


class PriceListFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=COLORS["card_bg"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="Price List", bg=COLORS["card_bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(side="left", padx=20, pady=14)
        tk.Frame(self, bg=COLORS["border"], height=1).pack(fill="x")

        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=24, pady=20)

        # ── Add new price row ──────────────────────────────────────────────────
        add_card = tk.Frame(body, bg=COLORS["card_bg"], padx=20, pady=18)
        add_card.pack(fill="x", pady=(0, 20))

        tk.Label(add_card, text="Add / Update Cloth Price",
                 bg=COLORS["card_bg"], fg=COLORS["text"],
                 font=FONTS["bold"]).pack(anchor="w", pady=(0, 10))

        row = tk.Frame(add_card, bg=COLORS["card_bg"])
        row.pack(fill="x")

        tk.Label(row, text="Cloth Type:", bg=COLORS["card_bg"],
                 fg=COLORS["text_dim"], font=FONTS["bold"]).pack(side="left", padx=(0, 8))

        self._cloth_var = tk.StringVar()
        self._cloth_entry = make_entry(row, textvariable=self._cloth_var, width=20)
        self._cloth_entry.pack(side="left", padx=(0, 16), ipady=5)

        tk.Label(row, text="Price (₹):", bg=COLORS["card_bg"],
                 fg=COLORS["text_dim"], font=FONTS["bold"]).pack(side="left", padx=(0, 8))

        self._price_var = tk.StringVar()
        self._price_entry = make_entry(row, textvariable=self._price_var, width=12)
        self._price_entry.pack(side="left", padx=(0, 16), ipady=5)
        self._price_entry.bind("<Return>", lambda e: self._add_price())

        make_btn(row, "➕ Add / Update", self._add_price, "primary").pack(side="left")

        # ── Price table ────────────────────────────────────────────────────────
        cols   = ("cloth_type", "default_price")
        heads  = ("Cloth Type", "Default Price (₹)")
        widths = (300, 300)

        tf, self._tree = build_tree(body, cols, heads, widths, height=20)
        tf.pack(fill="both", expand=True, pady=(0, 12))

        self._tree.bind("<Double-1>", self._on_double_click)

        # Action buttons below table
        btn_row = tk.Frame(body, bg=COLORS["bg"])
        btn_row.pack(fill="x")

        make_btn(btn_row, "✏️  Edit Selected",   self._edit_selected,   "edit").pack(side="left", padx=(0, 8))
        make_btn(btn_row, "🗑️  Delete Selected", self._delete_selected, "danger").pack(side="left", padx=(0, 8))
        make_btn(btn_row, "🔄 Refresh",          self.refresh,          "neutral").pack(side="right")

        tk.Label(body,
                 text="💡 Double-click a row to edit its price.",
                 bg=COLORS["bg"], fg=COLORS["text_muted"], font=FONTS["small"]
                 ).pack(anchor="w", pady=(8, 0))

    # ── Data ──────────────────────────────────────────────────────────────────

    def refresh(self):
        prices = db.get_all_prices()
        self._tree.delete(*self._tree.get_children())
        for i, p in enumerate(prices):
            tag = "even" if i % 2 == 0 else "odd"
            self._tree.insert("", "end",
                iid=p["cloth_type"],
                values=(p["cloth_type"], f"₹{p['default_price']:.2f}"),
                tags=(tag,)
            )

    # ── Actions ────────────────────────────────────────────────────────────────

    def _add_price(self):
        cloth = self._cloth_var.get().strip()
        price_str = self._price_var.get().strip()

        if not cloth:
            messagebox.showwarning("Validation", "Please enter a cloth type name.", parent=self)
            return
        try:
            price = float(price_str)
            if price < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Validation", "Enter a valid positive price.", parent=self)
            return

        db.set_price(cloth, price)
        self._cloth_var.set("")
        self._price_var.set("")
        self.refresh()
        messagebox.showinfo("Success",
                             f"Price for '{cloth}' set to ₹{price:.2f}", parent=self)

    def _on_double_click(self, event):
        self._edit_selected()

    def _edit_selected(self):
        sel = self._tree.focus()
        if not sel:
            messagebox.showwarning("Select", "Please select a cloth type to edit.", parent=self)
            return
        vals = self._tree.item(sel, "values")
        cloth = vals[0]
        current_price_str = vals[1].replace("₹", "").strip()

        # Pre-fill the add form
        self._cloth_var.set(cloth)
        self._price_var.set(current_price_str)
        self._cloth_entry.focus()

    def _delete_selected(self):
        sel = self._tree.focus()
        if not sel:
            messagebox.showwarning("Select", "Please select a cloth type to delete.", parent=self)
            return
        cloth = self._tree.item(sel, "values")[0]
        if messagebox.askyesno(
            "Delete",
            f"Remove '{cloth}' from the price list?",
            parent=self
        ):
            db.delete_price(cloth)
            self.refresh()
            messagebox.showinfo("Deleted", f"'{cloth}' has been removed from the price list.", parent=self)

