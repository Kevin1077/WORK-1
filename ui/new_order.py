"""
ui/new_order.py — New Order form
Handles customer lookup/creation and dynamic clothing item table.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

PAYMENT_METHODS = ["Cash", "GPay", "Unpaid"]

from ui.theme   import COLORS, FONTS
from ui.widgets import make_btn, make_entry, ScrollableFrame

try:
    from tkcalendar import DateEntry
    HAS_CAL = True
except ImportError:
    HAS_CAL = False

import database as db


# ── Item row ───────────────────────────────────────────────────────────────────

class _ItemRow:
    """Represents one row in the order items table."""

    def __init__(self, parent, cloth_types, on_change, on_delete):
        self.frame = tk.Frame(parent, bg=COLORS["card_bg2"])
        self.frame.pack(fill="x", pady=2, padx=4)
        self._cloth_types = cloth_types  # keep reference for autocomplete

        # Cloth type — free text entry with autocomplete dropdown
        self._cloth_var = tk.StringVar()
        self._cloth_cb  = ttk.Combobox(
            self.frame, textvariable=self._cloth_var,
            values=cloth_types, width=18
        )
        self._cloth_cb.grid(row=0, column=0, padx=(4, 6), pady=5, sticky="w")
        # Trigger autocomplete on every keystroke
        self._cloth_var.trace_add("write", lambda *a: self._on_cloth_type())
        self._cloth_cb.bind("<<ComboboxSelected>>", lambda e: self._on_cloth_select())

        # Quantity with up/down spin arrows
        self._qty_var = tk.StringVar(value="1")
        qty_e = tk.Spinbox(
            self.frame, from_=1, to=999, increment=1,
            textvariable=self._qty_var, width=5,
            bg=COLORS["input_bg"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat",
            highlightthickness=1, highlightbackground=COLORS["border2"],
            highlightcolor=COLORS["accent"], font=FONTS["default"],
            buttonbackground=COLORS["card_bg2"],
            command=on_change,
        )
        qty_e.grid(row=0, column=1, padx=6, pady=5, sticky="w")

        # Price per unit
        self._price_var = tk.StringVar(value="0.00")
        price_e = tk.Entry(
            self.frame, textvariable=self._price_var, width=10,
            bg=COLORS["input_bg"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat",
            highlightthickness=1, highlightbackground=COLORS["border2"],
            highlightcolor=COLORS["accent"], font=FONTS["default"]
        )
        price_e.grid(row=0, column=2, padx=6, pady=5, sticky="w")

        # Subtotal (read-only label)
        self._sub_var = tk.StringVar(value="₹0.00")
        tk.Label(
            self.frame, textvariable=self._sub_var,
            bg=COLORS["card_bg2"], fg=COLORS["accent"],
            font=FONTS["bold"], width=10, anchor="w"
        ).grid(row=0, column=3, padx=6, pady=5, sticky="w")

        # Remarks / Item Notes (optional)
        self._notes_var = tk.StringVar(value="")
        notes_e = tk.Entry(
            self.frame, textvariable=self._notes_var, width=16,
            bg=COLORS["input_bg"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat",
            highlightthickness=1, highlightbackground=COLORS["border2"],
            highlightcolor=COLORS["accent"], font=FONTS["default"]
        )
        notes_e.grid(row=0, column=4, padx=6, pady=5, sticky="w")

        # Delete button
        tk.Button(
            self.frame, text="✕", command=lambda: on_delete(self),
            bg=COLORS["btn_danger"], fg=COLORS["btn_danger_fg"],
            font=FONTS["small_bold"], relief="flat", bd=0,
            padx=8, pady=3, cursor="hand2"
        ).grid(row=0, column=5, padx=(6, 4), pady=5, sticky="w")

        # Traces
        self._qty_var.trace_add("write",   lambda *a: on_change())
        self._price_var.trace_add("write", lambda *a: on_change())
        self._on_change = on_change
        self._updating  = False  # guard against recursive trace calls

    def _on_cloth_type(self):
        """Called on every keystroke — filter dropdown + autofill price."""
        if self._updating:
            return
        typed = self._cloth_var.get()
        # Filter suggestions (case-insensitive prefix/substring match)
        matches = [ct for ct in self._cloth_types
                   if typed.lower() in ct.lower()]
        self._cloth_cb["values"] = matches if matches else self._cloth_types
        # Autofill price on exact match
        for ct in self._cloth_types:
            if ct.lower() == typed.lower():
                price = db.get_price(ct)
                self._updating = True
                self._price_var.set(f"{price:.2f}")
                self._updating = False
                self._on_change()
                break

    def _on_cloth_select(self):
        """Called when user picks from the dropdown list."""
        cloth = self._cloth_var.get()
        price = db.get_price(cloth)
        self._price_var.set(f"{price:.2f}")

    def calculate(self) -> float:
        """Calculate subtotal, update label, return value."""
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
        return {
            "cloth_type":    cloth,
            "quantity":      qty,
            "price_per_unit": price,
            "subtotal":      qty * price,
            "item_notes":    self._notes_var.get().strip(),
        }

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


# ── New Order Frame ────────────────────────────────────────────────────────────

class NewOrderFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COLORS["bg"])
        self.app         = app
        self._cust_id    = None    # set when existing customer found
        self._item_rows  = []
        self._cloth_types = []
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=COLORS["card_bg"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="New Order", bg=COLORS["card_bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(side="left", padx=20, pady=14)
        tk.Frame(self, bg=COLORS["border"], height=1).pack(fill="x")

        # Scrollable body
        scroll = ScrollableFrame(self, bg=COLORS["bg"])
        scroll.pack(fill="both", expand=True)
        body = scroll.inner
        body.config(padx=24, pady=20)

        # ── SECTION 1: Customer ────────────────────────────────────────────────
        self._build_customer_section(body)

        # ── SECTION 2: Order Info ──────────────────────────────────────────────
        self._build_order_info_section(body)

        # ── SECTION 3: Items ───────────────────────────────────────────────────
        self._build_items_section(body)

        # ── SECTION 4: Total + Submit ──────────────────────────────────────────
        self._build_submit_section(body)

    # ── Customer section ───────────────────────────────────────────────────────

    def _build_customer_section(self, body):
        card = tk.Frame(body, bg=COLORS["card_bg"], padx=20, pady=16)
        card.pack(fill="x", pady=(0, 16))

        # Title row
        title_row = tk.Frame(card, bg=COLORS["card_bg"])
        title_row.pack(fill="x", pady=(0, 12))
        tk.Label(title_row, text="Customer Details",
                 bg=COLORS["card_bg"], fg=COLORS["accent"],
                 font=FONTS["bold"]).pack(side="left")
        self._cust_badge = tk.Label(title_row, text="",
                                     bg=COLORS["card_bg"], fg=COLORS["text"],
                                     font=FONTS["small_bold"])
        self._cust_badge.pack(side="left", padx=12)

        # Phone lookup row
        ph_row = tk.Frame(card, bg=COLORS["card_bg"])
        ph_row.pack(fill="x", pady=(0, 10))

        tk.Label(ph_row, text="Phone *", bg=COLORS["card_bg"],
                 fg=COLORS["text_dim"], font=FONTS["small_bold"],
                 width=14, anchor="w").pack(side="left")

        self._phone_var = tk.StringVar()
        self._phone_entry = make_entry(ph_row, textvariable=self._phone_var, width=18)
        self._phone_entry.pack(side="left", padx=(0, 10), ipady=5)
        self._phone_entry.bind("<Return>", lambda e: self._lookup_customer())

        make_btn(ph_row, "🔍 Lookup", self._lookup_customer, "neutral").pack(side="left", padx=(0, 8))
        make_btn(ph_row, "✕ Clear",   self._clear_customer,  "neutral").pack(side="left")

        # Customer fields (2-column grid)
        fields_frame = tk.Frame(card, bg=COLORS["card_bg"])
        fields_frame.pack(fill="x")

        self._name_var    = tk.StringVar()
        self._place_var   = tk.StringVar()
        self._address_var = tk.StringVar()

        def lbl(parent, text):
            tk.Label(parent, text=text, bg=COLORS["card_bg"],
                     fg=COLORS["text_dim"], font=FONTS["small_bold"],
                     width=14, anchor="w").pack(side="left")

        # Row: Name | Place
        r1 = tk.Frame(fields_frame, bg=COLORS["card_bg"])
        r1.pack(fill="x", pady=4)
        lbl(r1, "Name *")
        self._name_entry = make_entry(r1, textvariable=self._name_var, width=24)
        self._name_entry.pack(side="left", padx=(0, 20), ipady=5)
        lbl(r1, "Place")
        self._place_entry = make_entry(r1, textvariable=self._place_var, width=22)
        self._place_entry.pack(side="left", ipady=5)

        # Row: Address
        r2 = tk.Frame(fields_frame, bg=COLORS["card_bg"])
        r2.pack(fill="x", pady=4)
        lbl(r2, "Address")
        self._address_entry = make_entry(r2, textvariable=self._address_var, width=52)
        self._address_entry.pack(side="left", ipady=5)

        self._cust_fields = [
            self._name_entry, self._place_entry, self._address_entry
        ]

    # ── Order info section ─────────────────────────────────────────────────────

    def _build_order_info_section(self, body):
        card = tk.Frame(body, bg=COLORS["card_bg"], padx=20, pady=16)
        card.pack(fill="x", pady=(0, 16))

        tk.Label(card, text="Order Details",
                 bg=COLORS["card_bg"], fg=COLORS["accent"],
                 font=FONTS["bold"]).pack(anchor="w", pady=(0, 12))

        row = tk.Frame(card, bg=COLORS["card_bg"])
        row.pack(fill="x")

        def lbl(parent, text):
            tk.Label(parent, text=text, bg=COLORS["card_bg"],
                     fg=COLORS["text_dim"], font=FONTS["small_bold"]).pack(side="left", padx=(0, 8))

        # Order date — always today, read-only
        lbl(row, "Order Date *")
        if HAS_CAL:
            self._order_date = DateEntry(
                row, width=14, date_pattern="dd-mm-yyyy",
                background=COLORS["accent"], foreground=COLORS["card_bg"],
                headersbackground=COLORS["sidebar_bg"],
                headersforeground=COLORS["accent"],
                selectbackground=COLORS["accent"],
                selectforeground=COLORS["card_bg"],
                font=FONTS["default"],
                state="readonly",
            )
            self._order_date.set_date(datetime.now())
        else:
            self._order_date = make_entry(row, width=14)
            self._order_date.insert(0, datetime.now().strftime("%d-%m-%Y"))
            self._order_date.config(state="readonly")
        self._order_date.pack(side="left", padx=(0, 24), ipady=4)

        # Payment method
        lbl(row, "Payment")
        self._payment_var = tk.StringVar(value="Cash")
        ttk.Combobox(
            row, textvariable=self._payment_var,
            values=PAYMENT_METHODS, width=10, state="readonly"
        ).pack(side="left", padx=(0, 24), ipady=4)

        # Notes
        lbl(row, "Notes")
        self._notes_var = tk.StringVar()
        make_entry(row, textvariable=self._notes_var, width=30).pack(side="left", ipady=5)

    # ── Items section ──────────────────────────────────────────────────────────

    def _build_items_section(self, body):
        self._items_card = tk.Frame(body, bg=COLORS["card_bg"], padx=20, pady=16)
        self._items_card.pack(fill="x", pady=(0, 16))

        title_row = tk.Frame(self._items_card, bg=COLORS["card_bg"])
        title_row.pack(fill="x", pady=(0, 10))

        tk.Label(title_row, text="Order Items",
                 bg=COLORS["card_bg"], fg=COLORS["accent"],
                 font=FONTS["bold"]).pack(side="left")
        make_btn(title_row, "➕ Add Item", self._add_item_row, "success").pack(side="right")

        # Column headers
        hdr = tk.Frame(self._items_card, bg=COLORS["table_header"])
        hdr.pack(fill="x", pady=(0, 4), padx=4)
        for text, w in [("Cloth Type", 16), ("Qty", 6), ("Price/Unit (₹)", 12), ("Subtotal", 10), ("Remarks / Notes", 16), ("Del", 5)]:
            tk.Label(hdr, text=text, bg=COLORS["table_header"],
                     fg=COLORS["accent"], font=FONTS["small_bold"],
                     width=w, anchor="w", padx=6, pady=6).pack(side="left")

        # Items container
        self._items_container = tk.Frame(self._items_card, bg=COLORS["card_bg"])
        self._items_container.pack(fill="x")

    # ── Submit section ─────────────────────────────────────────────────────────

    def _build_submit_section(self, body):
        card = tk.Frame(body, bg=COLORS["card_bg"], padx=20, pady=16)
        card.pack(fill="x", pady=(0, 24))

        row = tk.Frame(card, bg=COLORS["card_bg"])
        row.pack(fill="x")

        tk.Label(row, text="Grand Total:", bg=COLORS["card_bg"],
                 fg=COLORS["text_dim"], font=FONTS["bold"]).pack(side="left", padx=(0, 12))

        self._total_var = tk.StringVar(value="₹0.00")
        tk.Label(row, textvariable=self._total_var, bg=COLORS["card_bg"],
                 fg=COLORS["accent"], font=FONTS["xlarge"]).pack(side="left")

        make_btn(row, "✓  Create Order", self._submit, "primary",
                 padx=24, pady=10).pack(side="right")
        make_btn(row, "✕  Reset",       self._reset,  "neutral").pack(side="right", padx=(0, 10))

    # ── Item row management ────────────────────────────────────────────────────

    def _add_item_row(self, cloth_type="", quantity=1, price=0.0):
        row = _ItemRow(
            self._items_container,
            self._cloth_types,
            self._recalculate_total,
            self._remove_item_row,
        )
        if cloth_type:
            row.set_data(cloth_type, quantity, price)
        self._item_rows.append(row)
        self._recalculate_total()

    def _remove_item_row(self, row: _ItemRow):
        row.destroy()
        self._item_rows.remove(row)
        self._recalculate_total()

    def _recalculate_total(self):
        total = sum(r.calculate() for r in self._item_rows)
        self._total_var.set(f"₹{total:.2f}")

    # ── Customer lookup ────────────────────────────────────────────────────────

    def _lookup_customer(self):
        phone = self._phone_var.get().strip()
        if not phone:
            messagebox.showwarning("Lookup", "Enter a phone number first.", parent=self)
            return
        cust = db.get_customer_by_phone(phone)
        if cust:
            self._cust_id = cust["customer_id"]
            self._name_var.set(cust["name"])
            self._place_var.set(cust.get("place", ""))
            self._address_var.set(cust.get("address", ""))
            for e in self._cust_fields:
                e.config(state="normal")
            self._cust_badge.config(
                text="  ✔ Existing Customer  ",
                bg=COLORS["success"], fg=COLORS["text"]
            )
        else:
            self._cust_id = None
            self._name_var.set("")
            self._place_var.set("")
            self._address_var.set("")
            for e in self._cust_fields:
                e.config(state="normal")
            self._name_entry.focus()
            self._cust_badge.config(
                text="  ★ New Customer  ",
                bg=COLORS["warning"], fg=COLORS["text"]
            )

    def _clear_customer(self):
        self._cust_id = None
        self._phone_var.set("")
        self._name_var.set("")
        self._place_var.set("")
        self._address_var.set("")
        self._cust_badge.config(text="", bg=COLORS["card_bg"])

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _get_dates(self):
        if HAS_CAL:
            od = self._order_date.get_date().strftime("%Y-%m-%d")
        else:
            od = _parse_date(self._order_date.get())
        return od, ""

    # ── Submit ─────────────────────────────────────────────────────────────────

    def _submit(self):
        # Validate customer
        phone = self._phone_var.get().strip()
        name  = self._name_var.get().strip()
        if not phone:
            messagebox.showwarning("Validation", "Phone number is required.", parent=self)
            return
        if not name:
            messagebox.showwarning("Validation", "Customer name is required.", parent=self)
            return

        # Validate items
        if not self._item_rows:
            messagebox.showwarning("Validation", "Add at least one clothing item.", parent=self)
            return
        for row in self._item_rows:
            if not row.is_valid():
                messagebox.showwarning(
                    "Validation",
                    "All items must have a cloth type, quantity, and price > 0.",
                    parent=self
                )
                return

        # Get/create customer
        try:
            if self._cust_id:
                db.update_customer(
                    self._cust_id, name, phone,
                    self._place_var.get().strip(),
                    self._address_var.get().strip()
                )
                cid = self._cust_id
            else:
                # Check if phone now exists (edge case)
                existing = db.get_customer_by_phone(phone)
                if existing:
                    cid = existing["customer_id"]
                    db.update_customer(
                        cid, name, phone,
                        self._place_var.get().strip(),
                        self._address_var.get().strip()
                    )
                else:
                    cid = db.create_customer(
                        name, phone,
                        self._place_var.get().strip(),
                        self._address_var.get().strip()
                    )
        except Exception as ex:
            messagebox.showerror("Database Error", str(ex), parent=self)
            return

        # Dates and items
        order_date, delivery_date = self._get_dates()
        items = [r.get_data() for r in self._item_rows]
        notes = self._notes_var.get().strip()
        payment = self._payment_var.get()

        # Create order
        try:
            oid = db.create_order(cid, order_date, delivery_date, items, notes, payment_method=payment)
        except Exception as ex:
            messagebox.showerror("Database Error", str(ex), parent=self)
            return

        # Success - Prompt print options
        order = db.get_order_full(oid)
        self._prompt_print_options(order)
        self._reset()

    def _prompt_print_options(self, order):
        """Display dialog allowing staff to print receipt, dispatch slips, or both."""
        win = tk.Toplevel(self)
        win.title("Order Created Successfully")
        win.configure(bg=COLORS["bg"])
        win.resizable(False, False)
        win.grab_set()

        w, h = 420, 260
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"{w}x{h}+{(sw - w)//2}+{(sh - h)//2}")

        hdr = tk.Frame(win, bg=COLORS["card_bg"], padx=20, pady=16)
        hdr.pack(fill="x")
        tk.Label(
            hdr, text=f"✅ Order #{order['order_id']} Created",
            bg=COLORS["card_bg"], fg=COLORS["accent"], font=FONTS["title"]
        ).pack(anchor="w")
        tk.Label(
            hdr, text=f"Customer: {order['name']} | Total: ₹{order['total_amount']:.2f}",
            bg=COLORS["card_bg"], fg=COLORS["text_dim"], font=FONTS["small"]
        ).pack(anchor="w", pady=(4, 0))

        body = tk.Frame(win, bg=COLORS["bg"], padx=20, pady=16)
        body.pack(fill="both", expand=True)

        tk.Label(
            body, text="Select print action for this order:",
            bg=COLORS["bg"], fg=COLORS["text"], font=FONTS["bold"]
        ).pack(anchor="w", pady=(0, 12))

        btn_f = tk.Frame(body, bg=COLORS["bg"])
        btn_f.pack(fill="x")

        def _print_rec():
            try:
                from utils.receipt import open_receipt_pdf
                open_receipt_pdf(order, parent_window=win)
            except Exception as e:
                messagebox.showerror("Print Error", str(e), parent=win)

        def _whatsapp_rec():
            try:
                from utils.receipt import send_whatsapp_receipt
                send_whatsapp_receipt(order, parent_window=win)
            except Exception as e:
                messagebox.showerror("WhatsApp Error", str(e), parent=win)

        def _print_disp():
            try:
                from utils.dispatch_slip import open_dispatch_slip
                open_dispatch_slip(order)
            except Exception as e:
                messagebox.showerror("Print Error", str(e), parent=win)

        def _print_both():
            _print_rec()
            _print_disp()

        make_btn(btn_f, "🖨️ Receipt", _print_rec, "neutral").pack(side="left", padx=(0, 6))
        make_btn(btn_f, "📲 WhatsApp", _whatsapp_rec, "success").pack(side="left", padx=(0, 6))
        make_btn(btn_f, "🏷️ Dispatch", _print_disp, "neutral").pack(side="left", padx=(0, 6))

        close_f = tk.Frame(body, bg=COLORS["bg"])
        close_f.pack(fill="x", pady=(16, 0))
        make_btn(close_f, "Done", win.destroy, "neutral").pack(side="right")

        self._reset()

    def _reset(self):
        self._clear_customer()
        for row in list(self._item_rows):
            row.destroy()
        self._item_rows.clear()
        self._total_var.set("₹0.00")
        self._notes_var.set("")
        self._payment_var.set("Cash")
        # Always reset order date back to today
        if HAS_CAL:
            self._order_date.set_date(datetime.now())
        else:
            self._order_date.config(state="normal")
            self._order_date.delete(0, "end")
            self._order_date.insert(0, datetime.now().strftime("%d-%m-%Y"))
            self._order_date.config(state="readonly")

    def refresh(self):
        """Called when this frame is shown — reload cloth types."""
        self._cloth_types = db.get_cloth_types()
        # Update existing comboboxes
        for row in self._item_rows:
            try:
                row._cloth_cb["values"] = self._cloth_types
            except Exception:
                pass
        # Add first empty row if none exist
        if not self._item_rows:
            self._add_item_row()


def _parse_date(s):
    try:
        return datetime.strptime(s.strip(), "%d-%m-%Y").strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")
