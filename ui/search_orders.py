"""
ui/search_orders.py — Search orders by order number, customer name, phone, or status
"""
import tkinter as tk
from tkinter import ttk, messagebox

from ui.theme   import COLORS, FONTS, STATUS_COLORS, STATUS_LIST
from ui.widgets import make_btn, make_entry, build_tree
import database as db


class SearchOrdersFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=COLORS["card_bg"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="Search Orders", bg=COLORS["card_bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(side="left", padx=20, pady=14)
        tk.Frame(self, bg=COLORS["border"], height=1).pack(fill="x")

        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=24, pady=20)

        # ── Search card ────────────────────────────────────────────────────────
        search_card = tk.Frame(body, bg=COLORS["card_bg"], padx=20, pady=18)
        search_card.pack(fill="x", pady=(0, 18))

        tk.Label(search_card, text="Search Orders",
                 bg=COLORS["card_bg"], fg=COLORS["text"],
                 font=FONTS["bold"]).pack(anchor="w", pady=(0, 10))

        # ── Mode selector (radio buttons) ──────────────────────────────────────
        mode_row = tk.Frame(search_card, bg=COLORS["card_bg"])
        mode_row.pack(anchor="w", pady=(0, 10))

        tk.Label(mode_row, text="Search by:", bg=COLORS["card_bg"],
                 fg=COLORS["text_dim"], font=FONTS["bold"]).pack(side="left", padx=(0, 12))

        self._mode = tk.StringVar(value="order_number")
        modes = [
            ("order_number", "Order Number"),
            ("name",         "Customer Name"),
            ("phone",        "Phone Number"),
            ("status",       "Order Status"),
        ]
        for val, lbl in modes:
            tk.Radiobutton(
                mode_row, text=lbl, variable=self._mode, value=val,
                bg=COLORS["card_bg"], fg=COLORS["text"],
                selectcolor=COLORS["input_bg"],
                activebackground=COLORS["card_bg"],
                activeforeground=COLORS["text"],
                font=FONTS["default"],
                command=self._on_mode_change,
            ).pack(side="left", padx=(0, 16))

        # ── Primary query row ──────────────────────────────────────────────────
        row = tk.Frame(search_card, bg=COLORS["card_bg"])
        row.pack(fill="x")

        self._icon_lbl = tk.Label(row, text="🔢", bg=COLORS["card_bg"],
                                  fg=COLORS["text_dim"], font=("Segoe UI", 14))
        self._icon_lbl.pack(side="left", padx=(0, 8))

        self._query_var = tk.StringVar()
        self._entry = make_entry(row, textvariable=self._query_var, width=40)
        self._entry.pack(side="left", padx=(0, 10), ipady=5)
        self._entry.bind("<Return>", lambda e: self._search())

        # Status dropdown (hidden by default)
        self._status_var = tk.StringVar(value=STATUS_LIST[0])
        self._status_cb = ttk.Combobox(
            row, textvariable=self._status_var,
            values=STATUS_LIST, width=18, state="readonly"
        )
        # Not packed initially — shown only in status mode

        make_btn(row, "Search", self._search, "primary").pack(side="left", padx=(0, 8))
        make_btn(row, "Clear",  self._clear,  "neutral").pack(side="left")

        # ── Phone filter row (shown only when name search returns multiple customers) ──
        self._phone_frame = tk.Frame(search_card, bg=COLORS["card_bg"])
        # Not packed initially

        tk.Label(self._phone_frame, text="Multiple customers found — narrow by phone:",
                 bg=COLORS["card_bg"], fg=COLORS["warning_fg"],
                 font=FONTS["small"]).pack(anchor="w", pady=(10, 4))

        prow = tk.Frame(self._phone_frame, bg=COLORS["card_bg"])
        prow.pack(fill="x")

        tk.Label(prow, text="📱", bg=COLORS["card_bg"],
                 fg=COLORS["text_dim"], font=("Segoe UI", 13)).pack(side="left", padx=(0, 8))

        self._phone_var = tk.StringVar()
        self._phone_entry = make_entry(prow, textvariable=self._phone_var, width=30)
        self._phone_entry.pack(side="left", padx=(0, 10), ipady=5)
        self._phone_entry.bind("<Return>", lambda e: self._search())

        make_btn(prow, "Filter", self._search, "primary").pack(side="left")

        # ── Tip label ──────────────────────────────────────────────────────────
        self._tip_lbl = tk.Label(search_card,
                 text="Tip: Enter the order number to find a specific order",
                 bg=COLORS["card_bg"], fg=COLORS["text_muted"],
                 font=FONTS["small"])
        self._tip_lbl.pack(anchor="w", pady=(8, 0))

        # ── Results count ──────────────────────────────────────────────────────
        self._count_lbl = tk.Label(body, text="", bg=COLORS["bg"],
                                    fg=COLORS["text_dim"], font=FONTS["small"])
        self._count_lbl.pack(anchor="w", pady=(0, 6))

        # ── Results table ──────────────────────────────────────────────────────
        cols   = ("order_id", "order_date", "name", "phone", "total_amount", "status", "payment_method")
        heads  = ("Order #",  "Date",       "Customer", "Phone", "Total (₹)", "Status", "Payment")
        widths = (70, 100, 200, 120, 100, 100, 90)

        tf, self._tree = build_tree(body, cols, heads, widths, height=18)
        tf.pack(fill="both", expand=True)

        for status, color in STATUS_COLORS.items():
            self._tree.tag_configure(f"s_{status}", foreground=color)

        self._tree.bind("<Double-1>", self._on_double_click)

        # Hint label
        self._hint = tk.Label(body,
                               text="Select a search mode above and press Search.",
                               bg=COLORS["bg"], fg=COLORS["text_muted"],
                               font=FONTS["subtitle"])
        self._hint.place(relx=0.5, rely=0.55, anchor="center")

    # ── Mode change ────────────────────────────────────────────────────────────

    def _on_mode_change(self):
        mode = self._mode.get()
        tips = {
            "order_number": "Tip: Enter the order number to find a specific order",
            "name":         "Tip: Enter the customer name (partial names work too)",
            "phone":        "Tip: Enter the customer phone number",
            "status":       "Tip: Select a status from the dropdown and click Search",
        }
        icons = {"order_number": "🔢", "name": "🔍", "phone": "📱", "status": "📋"}
        self._tip_lbl.config(text=tips.get(mode, ""))
        self._icon_lbl.config(text=icons.get(mode, "🔍"))
        # Hide phone filter when mode changes
        self._phone_frame.pack_forget()
        self._phone_var.set("")
        self._query_var.set("")
        self._tree.delete(*self._tree.get_children())
        self._count_lbl.config(text="")
        self._hint.place(relx=0.5, rely=0.55, anchor="center")

        # Toggle between text entry and status dropdown
        if mode == "status":
            self._entry.pack_forget()
            self._status_cb.pack(side="left", padx=(0, 10), ipady=5,
                                  before=self._entry.master.winfo_children()[-2])  # before Search btn
            self._entry.pack_forget()
            # Re-pack: icon, status_cb, buttons
            self._icon_lbl.pack_forget()
            for w in self._entry.master.winfo_children():
                w.pack_forget()
            self._icon_lbl.pack(side="left", padx=(0, 8))
            self._status_cb.pack(side="left", padx=(0, 10), ipady=5)
            make_btn(self._entry.master, "Search", self._search, "primary").pack(side="left", padx=(0, 8))
            make_btn(self._entry.master, "Clear",  self._clear,  "neutral").pack(side="left")
        else:
            # Rebuild row with text entry
            for w in self._entry.master.winfo_children():
                w.pack_forget()
            self._icon_lbl.pack(side="left", padx=(0, 8))
            self._entry.pack(side="left", padx=(0, 10), ipady=5)
            make_btn(self._entry.master, "Search", self._search, "primary").pack(side="left", padx=(0, 8))
            make_btn(self._entry.master, "Clear",  self._clear,  "neutral").pack(side="left")

    # ── Search logic ───────────────────────────────────────────────────────────

    def _search(self):
        mode  = self._mode.get()
        query = self._query_var.get().strip()
        phone_filter = self._phone_var.get().strip()

        self._hint.place_forget()

        if mode == "status":
            status = self._status_var.get()
            results = db.search_orders_by_status(status)
            self._populate(results)
            self._count_lbl.config(
                text=f"Found {len(results)} order(s) with status '{status}'"
            )
            return

        if not query:
            messagebox.showwarning("Search", "Please enter a search term.", parent=self)
            return

        if mode == "order_number":
            # Must be numeric
            if not query.isdigit():
                messagebox.showwarning("Search",
                    "Order number must be a numeric value (e.g. 42).", parent=self)
                return
            results = db.search_orders(query)  # search_orders handles int → order_id

        elif mode == "name":
            # Search by name; if multiple *different* customers, show phone filter
            results = _search_by_name(query)
            unique_customers = {r["phone"] for r in results}
            if len(unique_customers) > 1:
                # Show phone filter row
                self._phone_frame.pack(fill="x", pady=(0, 0))
                if phone_filter:
                    # Further narrow by phone
                    results = [r for r in results
                               if phone_filter in r["phone"]]

        else:  # phone
            results = _search_by_phone(query)

        self._populate(results)
        self._count_lbl.config(
            text=f"Found {len(results)} order(s) for '{query}'"
        )

    def _clear(self):
        self._query_var.set("")
        self._phone_var.set("")
        self._phone_frame.pack_forget()
        self._tree.delete(*self._tree.get_children())
        self._count_lbl.config(text="")
        self._hint.place(relx=0.5, rely=0.55, anchor="center")

    def _populate(self, rows):
        self._tree.delete(*self._tree.get_children())
        for i, row in enumerate(rows):
            tag_bg = "even" if i % 2 == 0 else "odd"
            tag_st = f"s_{row['status']}"
            self._tree.insert("", "end",
                iid=str(row["order_id"]),
                values=(
                    f"#{row['order_id']}",
                    _fmt_date(row["order_date"]),
                    row["name"],
                    row["phone"],
                    f"₹{row['total_amount']:.2f}",
                    row["status"],
                    row.get("payment_method", "") or "—",
                ),
                tags=(tag_bg, tag_st)
            )

    def _on_double_click(self, event):
        sel = self._tree.focus()
        if not sel:
            return
        from ui.order_details import OrderDetailsPopup
        OrderDetailsPopup(self, int(sel), lambda: self._search())

    def refresh(self):
        pass  # nothing to auto-load


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _search_by_name(name: str):
    """Return orders matching customer name (LIKE search)."""
    import database as db
    like = f"%{name.strip()}%"
    with db.get_connection() as conn:
        rows = conn.execute("""
            SELECT o.order_id, o.order_date, o.delivery_date, o.total_amount,
                   o.status, o.payment_method, o.status_changed_at,
                   c.name, c.phone
            FROM orders o JOIN customers c ON o.customer_id=c.customer_id
            WHERE c.name LIKE ?
            ORDER BY o.order_id DESC
        """, (like,)).fetchall()
    return [dict(r) for r in rows]


def _search_by_phone(phone: str):
    """Return orders matching customer phone (LIKE search)."""
    import database as db
    like = f"%{phone.strip()}%"
    with db.get_connection() as conn:
        rows = conn.execute("""
            SELECT o.order_id, o.order_date, o.delivery_date, o.total_amount,
                   o.status, o.payment_method, o.status_changed_at,
                   c.name, c.phone
            FROM orders o JOIN customers c ON o.customer_id=c.customer_id
            WHERE c.phone LIKE ?
            ORDER BY o.order_id DESC
        """, (like,)).fetchall()
    return [dict(r) for r in rows]


def _fmt_date(d):
    try:
        from datetime import datetime
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return d
