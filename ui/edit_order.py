"""
ui/edit_order.py — Edit existing order (Toplevel modal popup)
Pre-fills all fields from the database and allows saving changes.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from ui.theme   import COLORS, FONTS, STATUS_LIST

PAYMENT_METHODS = ["Cash", "GPay"]
from ui.widgets import make_btn, make_entry, ScrollableFrame

try:
    from tkcalendar import DateEntry
    HAS_CAL = True
except ImportError:
    HAS_CAL = False

import database as db


# ── Item row (same as in new_order.py, duplicated to keep modules independent) ─

class _ItemRow:
    def __init__(self, parent, cloth_types, on_change, on_delete):
        self.frame = tk.Frame(parent, bg=COLORS["card_bg2"])
        self.frame.pack(fill="x", pady=2, padx=4)

        self._cloth_var = tk.StringVar()
        self._cloth_cb  = ttk.Combobox(
            self.frame, textvariable=self._cloth_var,
            values=cloth_types, width=18
        )
        self._cloth_cb.grid(row=0, column=0, padx=(4, 6), pady=5, sticky="w")
        self._cloth_cb.bind("<<ComboboxSelected>>", lambda e: self._on_cloth_select())

        self._qty_var = tk.StringVar(value="1")
        tk.Entry(
            self.frame, textvariable=self._qty_var, width=6,
            bg=COLORS["input_bg"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat",
            highlightthickness=1, highlightbackground=COLORS["border2"],
            highlightcolor=COLORS["accent"], font=FONTS["default"]
        ).grid(row=0, column=1, padx=6, pady=5, sticky="w")

        self._price_var = tk.StringVar(value="0.00")
        tk.Entry(
            self.frame, textvariable=self._price_var, width=10,
            bg=COLORS["input_bg"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat",
            highlightthickness=1, highlightbackground=COLORS["border2"],
            highlightcolor=COLORS["accent"], font=FONTS["default"]
        ).grid(row=0, column=2, padx=6, pady=5, sticky="w")

        self._sub_var = tk.StringVar(value="₹0.00")
        tk.Label(
            self.frame, textvariable=self._sub_var,
            bg=COLORS["card_bg2"], fg=COLORS["accent"],
            font=FONTS["bold"], width=10, anchor="w"
        ).grid(row=0, column=3, padx=6, pady=5, sticky="w")

        self._notes_var = tk.StringVar(value="")
        tk.Entry(
            self.frame, textvariable=self._notes_var, width=16,
            bg=COLORS["input_bg"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat",
            highlightthickness=1, highlightbackground=COLORS["border2"],
            highlightcolor=COLORS["accent"], font=FONTS["default"]
        ).grid(row=0, column=4, padx=6, pady=5, sticky="w")

        tk.Button(
            self.frame, text="✕", command=lambda: on_delete(self),
            bg=COLORS["btn_danger"], fg=COLORS["text"],
            font=FONTS["small_bold"], relief="flat", bd=0,
            padx=8, pady=3, cursor="hand2"
        ).grid(row=0, column=5, padx=(6, 4), pady=5, sticky="w")

        self._qty_var.trace_add("write",   lambda *a: on_change())
        self._price_var.trace_add("write", lambda *a: on_change())

    def _on_cloth_select(self):
        price = db.get_price(self._cloth_var.get())
        self._price_var.set(f"{price:.2f}")

    def calculate(self) -> float:
        try:
            qty   = max(1, int(self._qty_var.get() or 1))
            price = float(self._price_var.get() or 0)
            sub   = qty * price
        except ValueError:
            sub = 0.0
        self._sub_var.set(f"₹{sub:.2f}")
        return sub

    def get_data(self) -> dict:
        cloth = self._cloth_var.get().strip()
        try:
            qty   = max(1, int(self._qty_var.get() or 1))
            price = float(self._price_var.get() or 0)
        except ValueError:
            qty, price = 1, 0.0
        return {"cloth_type": cloth, "quantity": qty,
                "price_per_unit": price, "subtotal": qty * price,
                "item_notes": self._notes_var.get().strip()}

    def set_data(self, cloth_type, quantity, price_per_unit, item_notes=""):
        self._cloth_var.set(cloth_type)
        self._qty_var.set(str(quantity))
        self._price_var.set(f"{price_per_unit:.2f}")
        self._notes_var.set(item_notes)
        self.calculate()

    def is_valid(self) -> bool:
        d = self.get_data()
        return bool(d["cloth_type"]) and d["quantity"] > 0 and d["price_per_unit"] > 0

    def destroy(self):
        self.frame.destroy()


# ── Edit Order Popup ───────────────────────────────────────────────────────────

class EditOrderPopup(tk.Toplevel):
    def __init__(self, parent, order_id: int, refresh_cb=None):
        super().__init__(parent)
        self.order_id   = order_id
        self.refresh_cb = refresh_cb
        self._order     = None
        self._item_rows = []
        self._cloth_types = db.get_cloth_types()

        self.title(f"Edit Order #{order_id} — Victory Laundry")
        self.configure(bg=COLORS["bg"])
        self.geometry("900x700")
        self.grab_set()
        self.focus_set()

        order = db.get_order_full(order_id)
        if not order:
            messagebox.showerror("Error", f"Order #{order_id} not found.", parent=self)
            self.destroy()
            return
        self._order = order
        self._build()
        self._prefill()
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w)//2}+{(sh - h)//2}")

    # ── Build UI ───────────────────────────────────────────────────────────────

    def _build(self):
        tk.Frame(self, bg=COLORS["accent"], height=4).pack(fill="x")

        # Header
        hdr = tk.Frame(self, bg=COLORS["card_bg"], padx=20, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"Edit Order #{self.order_id}",
                 bg=COLORS["card_bg"], fg=COLORS["accent"],
                 font=FONTS["title"]).pack(side="left")
        make_btn(hdr, "✕ Close", self.destroy, "neutral").pack(side="right")
        tk.Frame(self, bg=COLORS["border"], height=1).pack(fill="x")

        # Scrollable body
        scroll = ScrollableFrame(self, bg=COLORS["bg"])
        scroll.pack(fill="both", expand=True)
        body = scroll.inner
        body.config(padx=24, pady=20)

        # ── Customer section ───────────────────────────────────────────────────
        cust_card = tk.Frame(body, bg=COLORS["card_bg"], padx=20, pady=16)
        cust_card.pack(fill="x", pady=(0, 16))

        tk.Label(cust_card, text="Customer Details",
                 bg=COLORS["card_bg"], fg=COLORS["accent"],
                 font=FONTS["bold"]).pack(anchor="w", pady=(0, 12))

        def lbl(parent, text):
            tk.Label(parent, text=text, bg=COLORS["card_bg"],
                     fg=COLORS["text_dim"], font=FONTS["small_bold"],
                     width=14, anchor="w").pack(side="left")

        # Phone row
        r0 = tk.Frame(cust_card, bg=COLORS["card_bg"])
        r0.pack(fill="x", pady=4)
        lbl(r0, "Phone")
        self._phone_var = tk.StringVar()
        make_entry(r0, textvariable=self._phone_var, width=18).pack(side="left", ipady=5)

        # Name | Place
        r1 = tk.Frame(cust_card, bg=COLORS["card_bg"])
        r1.pack(fill="x", pady=4)
        lbl(r1, "Name *")
        self._name_var = tk.StringVar()
        make_entry(r1, textvariable=self._name_var, width=24).pack(side="left", padx=(0, 20), ipady=5)
        lbl(r1, "Place")
        self._place_var = tk.StringVar()
        make_entry(r1, textvariable=self._place_var, width=22).pack(side="left", ipady=5)

        # Address
        r2 = tk.Frame(cust_card, bg=COLORS["card_bg"])
        r2.pack(fill="x", pady=4)
        lbl(r2, "Address")
        self._address_var = tk.StringVar()
        make_entry(r2, textvariable=self._address_var, width=52).pack(side="left", ipady=5)

        # ── Order info section ─────────────────────────────────────────────────
        info_card = tk.Frame(body, bg=COLORS["card_bg"], padx=20, pady=16)
        info_card.pack(fill="x", pady=(0, 16))

        tk.Label(info_card, text="Order Details",
                 bg=COLORS["card_bg"], fg=COLORS["accent"],
                 font=FONTS["bold"]).pack(anchor="w", pady=(0, 12))

        info_row = tk.Frame(info_card, bg=COLORS["card_bg"])
        info_row.pack(fill="x")

        def ilbl(text):
            tk.Label(info_row, text=text, bg=COLORS["card_bg"],
                     fg=COLORS["text_dim"], font=FONTS["small_bold"]).pack(side="left", padx=(0, 8))

        ilbl("Order Date")
        self._order_date_lbl = tk.Label(
            info_row, bg=COLORS["card_bg"], fg=COLORS["text"],
            font=FONTS["default"]
        )
        self._order_date_lbl.pack(side="left", padx=(0, 20))

        ilbl("Status")
        self._status_var = tk.StringVar()
        ttk.Combobox(
            info_row, textvariable=self._status_var,
            values=STATUS_LIST, width=16, state="readonly"
        ).pack(side="left", padx=(0, 20), ipady=4)

        ilbl("Payment")
        self._payment_var = tk.StringVar(value="Cash")
        ttk.Combobox(
            info_row, textvariable=self._payment_var,
            values=PAYMENT_METHODS, width=10, state="readonly"
        ).pack(side="left", padx=(0, 20), ipady=4)

        ilbl("Notes")
        self._notes_var = tk.StringVar()
        make_entry(info_row, textvariable=self._notes_var, width=28).pack(side="left", ipady=5)

        # ── Items section ──────────────────────────────────────────────────────
        items_card = tk.Frame(body, bg=COLORS["card_bg"], padx=20, pady=16)
        items_card.pack(fill="x", pady=(0, 16))

        title_row = tk.Frame(items_card, bg=COLORS["card_bg"])
        title_row.pack(fill="x", pady=(0, 10))
        tk.Label(title_row, text="Order Items",
                 bg=COLORS["card_bg"], fg=COLORS["accent"],
                 font=FONTS["bold"]).pack(side="left")
        make_btn(title_row, "➕ Add Item", self._add_item_row, "success").pack(side="right")

        # Column headers
        hdr2 = tk.Frame(items_card, bg=COLORS["table_header"])
        hdr2.pack(fill="x", pady=(0, 4), padx=4)
        for text, w in [("Cloth Type", 16), ("Qty", 6), ("Price/Unit (₹)", 12), ("Subtotal", 10), ("Remarks / Notes", 16), ("Del", 5)]:
            tk.Label(hdr2, text=text, bg=COLORS["table_header"],
                     fg=COLORS["accent"], font=FONTS["small_bold"],
                     width=w, anchor="w", padx=6, pady=6).pack(side="left")

        self._items_container = tk.Frame(items_card, bg=COLORS["card_bg"])
        self._items_container.pack(fill="x")

        # ── Total + submit ─────────────────────────────────────────────────────
        bottom = tk.Frame(body, bg=COLORS["card_bg"], padx=20, pady=16)
        bottom.pack(fill="x", pady=(0, 24))

        btn_row = tk.Frame(bottom, bg=COLORS["card_bg"])
        btn_row.pack(fill="x")

        tk.Label(btn_row, text="Total:", bg=COLORS["card_bg"],
                 fg=COLORS["text_dim"], font=FONTS["bold"]).pack(side="left", padx=(0, 10))
        self._total_var = tk.StringVar(value="₹0.00")
        tk.Label(btn_row, textvariable=self._total_var,
                 bg=COLORS["card_bg"], fg=COLORS["accent"],
                 font=FONTS["xlarge"]).pack(side="left")

        make_btn(btn_row, "💾  Save Changes", self._save, "primary",
                 padx=24, pady=10).pack(side="right")
        make_btn(btn_row, "✕  Cancel",        self.destroy, "neutral").pack(side="right", padx=(0, 10))

    # ── Pre-fill from existing order ───────────────────────────────────────────

    def _prefill(self):
        o = self._order
        self._phone_var.set(o.get("phone", ""))
        self._name_var.set(o.get("name", ""))
        self._place_var.set(o.get("place", ""))
        self._address_var.set(o.get("address", ""))
        self._status_var.set(o.get("status", "Received"))
        self._notes_var.set(o.get("notes", ""))
        self._payment_var.set(o.get("payment_method", "Cash") or "Cash")

        # Dates
        od = o.get("order_date", "")
        self._order_date_str = od  # keep for saving
        self._order_date_lbl.config(
            text=_to_display(od) if od else "—"
        )

        # Items
        for item in o.get("items", []):
            row = self._add_item_row()
            row.set_data(item["cloth_type"], item["quantity"], item["price_per_unit"], item.get("item_notes", ""))

    # ── Item helpers ──────────────────────────────────────────────────────────

    def _add_item_row(self):
        row = _ItemRow(
            self._items_container,
            self._cloth_types,
            self._recalculate,
            self._remove_row,
        )
        self._item_rows.append(row)
        self._recalculate()
        return row

    def _remove_row(self, row):
        row.destroy()
        self._item_rows.remove(row)
        self._recalculate()

    def _recalculate(self):
        total = sum(r.calculate() for r in self._item_rows)
        self._total_var.set(f"₹{total:.2f}")

    # ── Save ──────────────────────────────────────────────────────────────────

    def _save(self):
        name = self._name_var.get().strip()
        if not name:
            messagebox.showwarning("Validation", "Customer name is required.", parent=self)
            return

        if not self._item_rows:
            messagebox.showwarning("Validation", "Add at least one item.", parent=self)
            return

        for row in self._item_rows:
            if not row.is_valid():
                messagebox.showwarning(
                    "Validation",
                    "All items must have a cloth type, quantity, and price > 0.",
                    parent=self
                )
                return

        # Dates — keep the original order date unchanged
        order_date    = self._order_date_str or datetime.now().strftime("%Y-%m-%d")
        delivery_date = ""

        # Update customer
        cid = self._order["customer_id"]
        try:
            db.update_customer(
                cid, name,
                self._phone_var.get().strip(),
                self._place_var.get().strip(),
                self._address_var.get().strip()
            )
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)
            return

        items  = [r.get_data() for r in self._item_rows]
        status = self._status_var.get()
        became_ready = self._order.get("status") != "Ready" and status == "Ready"
        notes  = self._notes_var.get().strip()
        payment = self._payment_var.get()

        try:
            db.update_order(
                self.order_id, cid,
                order_date, delivery_date,
                items, notes, status, payment_method=payment
            )
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)
            return

        messagebox.showinfo(
            "Saved",
            f"Order #{self.order_id} updated successfully!",
            parent=self
        )

        if became_ready:
            try:
                from utils.receipt import prompt_whatsapp_ready_notification
                prompt_whatsapp_ready_notification(
                    db.get_order_full(self.order_id), parent_window=self
                )
            except Exception as exc:
                messagebox.showerror("WhatsApp Error", str(exc), parent=self)
        if self.refresh_cb:
            self.refresh_cb()
        self.destroy()


def _parse_date(s):
    try:
        return datetime.strptime(s.strip(), "%d-%m-%Y").strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def _to_display(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return ""
