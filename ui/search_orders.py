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
            ("item_status",  "Item Wash Status"),
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

        # Item wash status dropdown (hidden by default)
        self._item_status_var = tk.StringVar(value="Not Returned (In Washing)")
        self._item_status_cb = ttk.Combobox(
            row, textvariable=self._item_status_var,
            values=["Not Returned (In Washing)", "Returned"], width=24, state="readonly"
        )

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

        # ── Date filter row ────────────────────────────────────────────────────
        self._date_filter_frame = tk.Frame(search_card, bg=COLORS["card_bg"], pady=4)
        self._date_filter_frame.pack(anchor="w", pady=(4, 0))

        tk.Label(self._date_filter_frame, text="📅 Filter by Date:",
                 bg=COLORS["card_bg"], fg=COLORS["text_dim"],
                 font=FONTS["bold"]).pack(side="left", padx=(0, 12))

        self._date_filter_var = tk.StringVar(value="all")
        date_options = [
            ("all",   "All Dates"),
            ("day",   "Day (Today)"),
            ("week",  "Week (Last 7 Days)"),
            ("month", "Month (This Month)"),
        ]
        for val, lbl in date_options:
            tk.Radiobutton(
                self._date_filter_frame, text=lbl, variable=self._date_filter_var, value=val,
                bg=COLORS["card_bg"], fg=COLORS["text"],
                selectcolor=COLORS["input_bg"],
                activebackground=COLORS["card_bg"],
                activeforeground=COLORS["text"],
                font=FONTS["small"],
                command=self._apply_date_filter,
            ).pack(side="left", padx=(0, 14))

        self._raw_results = []
        self._query_desc = ""

        # ── Results count + print ──────────────────────────────────────────────
        count_row = tk.Frame(body, bg=COLORS["bg"])
        count_row.pack(fill="x", pady=(0, 6))

        self._count_lbl = tk.Label(count_row, text="", bg=COLORS["bg"],
                                    fg=COLORS["text_dim"], font=FONTS["small"])
        self._count_lbl.pack(side="left")

        self._print_btn = make_btn(count_row, "🖨️ Print PDF", self._print_pdf, "neutral")
        self._print_btn.pack(side="right")
        self._print_btn.config(state="disabled")

        self._last_print_rows = []
        self._last_print_mode = ""

        # ── Results table ──────────────────────────────────────────────────────
        # All possible columns defined once; displaycolumns switches per mode
        cols  = ("order_id", "order_date", "name", "phone", "total_amount",
                 "status", "payment_method", "item_detail", "unit_number")
        heads = ("Order #", "Date", "Customer", "Phone", "Total (₹)",
                 "Status", "Payment", "Item / Cloth Type", "Unit #")
        widths = (80, 110, 300, 120, 100, 110, 90, 380, 120)

        tf, self._tree = build_tree(body, cols, heads, widths, height=18)
        # Allow every column to stretch and fill available horizontal space
        for col, w in zip(cols, widths):
            self._tree.column(col, width=w, minwidth=40, stretch=True)
        self._tree["displaycolumns"] = ("order_id", "order_date", "name",
                                         "phone", "total_amount", "status", "payment_method")
        tf.pack(fill="both", expand=True)

        self._item_status_filter_returned = False  # track which filter is active

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
            "item_status":  "Tip: Select 'Not Returned' to find orders with clothes currently in washing facilities",
        }
        icons = {"order_number": "🔢", "name": "🔍", "phone": "📱", "status": "📋", "item_status": "🧺"}
        self._tip_lbl.config(text=tips.get(mode, ""))
        self._icon_lbl.config(text=icons.get(mode, "🔍"))
        # Hide phone filter when mode changes
        self._phone_frame.pack_forget()
        self._phone_var.set("")
        self._query_var.set("")
        self._date_filter_var.set("all")
        self._raw_results = []
        self._query_desc = ""
        self._tree.delete(*self._tree.get_children())
        self._count_lbl.config(text="")

        if mode == "item_status":
            self._tree["displaycolumns"] = ("order_id", "order_date", "name",
                                             "item_detail", "unit_number")
        else:
            self._tree["displaycolumns"] = ("order_id", "order_date", "name",
                                             "phone", "total_amount", "status", "payment_method")
        self._hint.place(relx=0.5, rely=0.55, anchor="center")

        # Toggle between text entry, order status dropdown, and item wash status dropdown
        master = self._icon_lbl.master
        for w in master.winfo_children():
            w.pack_forget()

        self._icon_lbl.pack(side="left", padx=(0, 8))
        if mode == "status":
            self._status_cb.pack(side="left", padx=(0, 10), ipady=5)
        elif mode == "item_status":
            self._item_status_cb.pack(side="left", padx=(0, 10), ipady=5)
        else:
            self._entry.pack(side="left", padx=(0, 10), ipady=5)

        make_btn(master, "Search", self._search, "primary").pack(side="left", padx=(0, 8))
        make_btn(master, "Clear",  self._clear,  "neutral").pack(side="left")

    # ── Search logic ───────────────────────────────────────────────────────────

    def _search(self):
        mode  = self._mode.get()
        query = self._query_var.get().strip()
        phone_filter = self._phone_var.get().strip()

        self._hint.place_forget()

        if mode == "status":
            status = self._status_var.get()
            results = db.search_orders_by_status(status)
            self._query_desc = f"status '{status}'"

        elif mode == "item_status":
            item_st = self._item_status_var.get()
            returned_bool = (item_st == "Returned")
            self._item_status_filter_returned = returned_bool
            results = db.search_orders_by_item_status(returned_bool)
            lbl = "Returned" if returned_bool else "Not Returned (In Washing)"
            self._query_desc = f"item status '{lbl}'"

        elif mode == "order_number":
            if not query:
                messagebox.showwarning("Search", "Please enter a search term.", parent=self)
                return
            if not query.isdigit():
                messagebox.showwarning("Search",
                    "Order number must be a numeric value (e.g. 42).", parent=self)
                return
            results = db.search_orders(query)
            self._query_desc = f"Order #{query}"

        elif mode == "name":
            if not query:
                messagebox.showwarning("Search", "Please enter a search term.", parent=self)
                return
            results = _search_by_name(query)
            unique_customers = {r["phone"] for r in results}
            if len(unique_customers) > 1:
                self._phone_frame.pack(fill="x", pady=(0, 0))
                if phone_filter:
                    results = [r for r in results if phone_filter in r["phone"]]
            self._query_desc = f"name '{query}'"

        else:  # phone
            if not query:
                messagebox.showwarning("Search", "Please enter a search term.", parent=self)
                return
            results = _search_by_phone(query)
            self._query_desc = f"phone '{query}'"

        self._raw_results = results
        self._apply_date_filter()

    def _apply_date_filter(self):
        period = self._date_filter_var.get()
        filtered = _filter_by_date(self._raw_results, period)
        row_count = self._populate(filtered)
        period_labels = {
            "all": "All Dates",
            "day": "Today",
            "week": "Last 7 Days",
            "month": "This Month",
        }
        lbl = period_labels.get(period, "")
        txt = f"Found {row_count} result(s) for {self._query_desc}"
        if period != "all":
            txt += f" ({lbl})"
        self._count_lbl.config(text=txt)
        # Enable/disable print button
        if row_count > 0:
            self._print_btn.config(state="normal")
        else:
            self._print_btn.config(state="disabled")

    def _clear(self):
        self._query_var.set("")
        self._phone_var.set("")
        self._date_filter_var.set("all")
        self._phone_frame.pack_forget()
        self._raw_results = []
        self._query_desc = ""
        self._last_print_rows = []
        self._last_print_mode = ""
        self._tree.delete(*self._tree.get_children())
        self._count_lbl.config(text="")
        self._print_btn.config(state="disabled")
        self._hint.place(relx=0.5, rely=0.55, anchor="center")

    def _populate(self, rows):
        """Populate the results table. Returns the number of rows inserted."""
        self._tree.delete(*self._tree.get_children())
        mode = self._mode.get()
        row_count = 0
        print_rows = []  # flat rows for PDF

        if mode == "item_status":
            want_returned = getattr(self, "_item_status_filter_returned", False)
            # One row per matching unit (order/date/name repeated)
            for row in rows:
                order_full = db.get_order_full(row["order_id"])
                if not order_full:
                    continue
                tag_st = f"s_{row['status']}"
                for item in order_full["items"]:
                    units = item.get("units", [])
                    for u in units:
                        # Only show units that match the selected filter
                        if bool(u.get("returned")) != want_returned:
                            continue
                        tag_bg = "even" if row_count % 2 == 0 else "odd"
                        iid = f"{row['order_id']}_{item['item_id']}_{u['unit_id']}"
                        self._tree.insert("", "end",
                            iid=iid,
                            values=(
                                f"#{row['order_id']}",
                                _fmt_date(row["order_date"]),
                                row["name"],
                                row["phone"],
                                f"\u20b9{row['total_amount']:.2f}",
                                row["status"],
                                row.get("payment_method", "") or "\u2014",
                                item["cloth_type"],
                                f"Unit #{u['unit_number']}"
                            ),
                            tags=(tag_bg, tag_st)
                        )
                        print_rows.append({
                            "order_id": row["order_id"],
                            "order_date": row["order_date"],
                            "name": row["name"],
                            "phone": row["phone"],
                            "status": row["status"],
                            "cloth_type": item["cloth_type"],
                            "unit_number": u["unit_number"],
                        })
                        row_count += 1
        else:
            for row in rows:
                tag_bg = "even" if row_count % 2 == 0 else "odd"
                tag_st = f"s_{row['status']}"
                self._tree.insert("", "end",
                    iid=str(row["order_id"]),
                    values=(
                        f"#{row['order_id']}",
                        _fmt_date(row["order_date"]),
                        row["name"],
                        row["phone"],
                        f"\u20b9{row['total_amount']:.2f}",
                        row["status"],
                        row.get("payment_method", "") or "\u2014",
                        "",
                        ""
                    ),
                    tags=(tag_bg, tag_st)
                )
                print_rows.append(dict(row))
                row_count += 1

        self._last_print_rows = print_rows
        self._last_print_mode = mode
        return row_count

    def _print_pdf(self):
        """Generate and open a PDF of the current search results."""
        if not self._last_print_rows:
            from tkinter import messagebox
            messagebox.showinfo("No Data", "Search for orders first, then print.", parent=self)
            return
        try:
            from utils.report_pdf import generate_search_report
            generate_search_report(
                self._last_print_rows,
                self._query_desc,
                self._last_print_mode
            )
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("PDF Error", str(e), parent=self)

    def _on_double_click(self, event):
        sel = self._tree.focus()
        if not sel:
            return
        # In item_status mode, iid is "order_id_item_id"; extract order_id from values
        try:
            order_id_str = self._tree.item(sel, "values")[0]  # e.g. "#42"
            order_id = int(order_id_str.lstrip("#"))
        except (IndexError, ValueError):
            return
        from ui.order_details import OrderDetailsPopup
        OrderDetailsPopup(self, order_id, lambda: self._search())

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


def _filter_by_date(rows, period):
    """Filter list of order dicts by date period ('day', 'week', 'month', 'all')."""
    from datetime import datetime, timedelta
    if not period or period == "all":
        return rows

    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    if period == "day":
        return [r for r in rows if r.get("order_date") == today_str]
    elif period == "week":
        week_ago_str = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        return [r for r in rows if r.get("order_date", "") >= week_ago_str]
    elif period == "month":
        month_prefix = today.strftime("%Y-%m")
        return [r for r in rows if r.get("order_date", "").startswith(month_prefix)]
    return rows


def _fmt_date(d):
    try:
        from datetime import datetime
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return d
