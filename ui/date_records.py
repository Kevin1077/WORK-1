"""
ui/date_records.py — Retrieve orders between two dates with summary stats
"""
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

from ui.theme   import COLORS, FONTS, STATUS_COLORS
from ui.widgets import make_btn, build_tree

try:
    from tkcalendar import DateEntry
    HAS_CAL = True
except ImportError:
    HAS_CAL = False

import database as db


class DateRecordsFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self._last_rows = []      # keep last fetched rows for PDF
        self._last_dates = ("", "")
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=COLORS["card_bg"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="Date-wise Records", bg=COLORS["card_bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(side="left", padx=20, pady=14)
        tk.Frame(self, bg=COLORS["border"], height=1).pack(fill="x")

        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=24, pady=20)

        # ── Filter card ────────────────────────────────────────────────────────
        filter_card = tk.Frame(body, bg=COLORS["card_bg"], padx=20, pady=18)
        filter_card.pack(fill="x", pady=(0, 18))

        tk.Label(filter_card, text="Select Date Range",
                 bg=COLORS["card_bg"], fg=COLORS["text"],
                 font=FONTS["bold"]).pack(anchor="w", pady=(0, 12))

        row = tk.Frame(filter_card, bg=COLORS["card_bg"])
        row.pack(fill="x")

        # From date
        tk.Label(row, text="From:", bg=COLORS["card_bg"],
                 fg=COLORS["text_dim"], font=FONTS["bold"]).pack(side="left", padx=(0, 6))

        if HAS_CAL:
            self._from_entry = DateEntry(
                row, width=14, date_pattern="dd-mm-yyyy",
                background=COLORS["input_bg"], foreground=COLORS["text"],
                bordercolor=COLORS["border2"], headersbackground=COLORS["sidebar_bg"],
                headersforeground=COLORS["accent"], weekendforeground=COLORS["danger_fg"],
                othermonthforeground=COLORS["text_muted"],
                selectbackground=COLORS["accent"], selectforeground=COLORS["card_bg"],
                font=FONTS["default"],
            )
        else:
            self._from_entry = tk.Entry(row, width=14, bg=COLORS["input_bg"],
                                         fg=COLORS["text"], relief="flat",
                                         highlightthickness=1,
                                         highlightbackground=COLORS["border2"])
            self._from_entry.insert(0, datetime.now().strftime("%d-%m-%Y"))
        self._from_entry.pack(side="left", padx=(0, 20), ipady=4)

        # To date
        tk.Label(row, text="To:", bg=COLORS["card_bg"],
                 fg=COLORS["text_dim"], font=FONTS["bold"]).pack(side="left", padx=(0, 6))

        if HAS_CAL:
            self._to_entry = DateEntry(
                row, width=14, date_pattern="dd-mm-yyyy",
                background=COLORS["input_bg"], foreground=COLORS["text"],
                bordercolor=COLORS["border2"], headersbackground=COLORS["sidebar_bg"],
                headersforeground=COLORS["accent"], weekendforeground=COLORS["danger_fg"],
                othermonthforeground=COLORS["text_muted"],
                selectbackground=COLORS["accent"], selectforeground=COLORS["card_bg"],
                font=FONTS["default"],
            )
        else:
            self._to_entry = tk.Entry(row, width=14, bg=COLORS["input_bg"],
                                       fg=COLORS["text"], relief="flat",
                                       highlightthickness=1,
                                       highlightbackground=COLORS["border2"])
            self._to_entry.insert(0, datetime.now().strftime("%d-%m-%Y"))
        self._to_entry.pack(side="left", padx=(0, 20), ipady=4)

        make_btn(row, "Fetch Records", self._fetch, "primary").pack(side="left", padx=(0, 8))
        make_btn(row, "Today",         self._set_today, "neutral").pack(side="left", padx=(0, 8))
        make_btn(row, "This Month",    self._set_month, "neutral").pack(side="left", padx=(0, 8))
        make_btn(row, "🖨️ Print PDF",  self._print_pdf, "neutral").pack(side="left")

        # Info label — shown after each fetch
        self._as_of_lbl = tk.Label(
            filter_card,
            text="",
            bg=COLORS["card_bg"], fg=COLORS["text_muted"],
            font=FONTS["small"]
        )
        self._as_of_lbl.pack(anchor="w", pady=(8, 0))

        # ── Summary stats ──────────────────────────────────────────────────────
        self._summary_frame = tk.Frame(body, bg=COLORS["bg"])
        self._summary_frame.pack(fill="x", pady=(0, 12))

        self._total_orders_lbl = tk.Label(
            self._summary_frame, text="", bg=COLORS["bg"],
            fg=COLORS["text_dim"], font=FONTS["bold"]
        )
        self._total_orders_lbl.pack(side="left", padx=(0, 20))

        self._total_rev_lbl = tk.Label(
            self._summary_frame, text="", bg=COLORS["bg"],
            fg=COLORS["success_fg"], font=FONTS["bold"]
        )
        self._total_rev_lbl.pack(side="left")

        # ── Results table ──────────────────────────────────────────────────────
        cols   = ("order_id", "order_date", "name", "phone", "total_amount", "status", "payment_method")
        heads  = ("Order #",  "Date",       "Customer", "Phone", "Total (₹)", "Status", "Payment")
        widths = (70, 100, 200, 120, 100, 100, 90)

        tf, self._tree = build_tree(body, cols, heads, widths, height=16)
        tf.pack(fill="both", expand=True)

        for status, color in STATUS_COLORS.items():
            self._tree.tag_configure(f"s_{status}", foreground=color)

        self._tree.bind("<Double-1>", self._on_double_click)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _get_dates(self):
        """Return (from_date, to_date) as YYYY-MM-DD strings."""
        if HAS_CAL:
            fd = self._from_entry.get_date().strftime("%Y-%m-%d")
            td = self._to_entry.get_date().strftime("%Y-%m-%d")
        else:
            fd = _parse_date(self._from_entry.get())
            td = _parse_date(self._to_entry.get())
        return fd, td

    def _fetch(self):
        fd, td = self._get_dates()
        if not fd or not td:
            messagebox.showwarning("Date Error",
                                   "Enter dates as DD-MM-YYYY", parent=self)
            return
        if fd > td:
            messagebox.showwarning("Date Error",
                                   "From date must be before To date.", parent=self)
            return
        rows = db.get_orders_by_date_range(fd, td)
        self._last_rows = rows
        self._last_dates = (fd, td)
        self._populate(rows)
        total_rev = sum(r["total_amount"] for r in rows)
        self._total_orders_lbl.config(
            text=f"Orders: {len(rows)}"
        )
        self._total_rev_lbl.config(
            text=f"Total Revenue: ₹{total_rev:,.2f}"
        )
        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        self._as_of_lbl.config(text=f"Showing all orders up to {now}")

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

    def _print_pdf(self):
        """Generate and open a PDF report of the currently displayed records."""
        if not self._last_rows:
            messagebox.showinfo("No Data", "Fetch records first, then print.", parent=self)
            return
        try:
            from utils.report_pdf import open_date_report
            open_date_report(self._last_rows, self._last_dates[0], self._last_dates[1])
        except Exception as e:
            messagebox.showerror("PDF Error", str(e), parent=self)

    def _set_today(self):
        today = datetime.now()
        if HAS_CAL:
            self._from_entry.set_date(today)
            self._to_entry.set_date(today)
        else:
            s = today.strftime("%d-%m-%Y")
            for e in (self._from_entry, self._to_entry):
                e.delete(0, "end")
                e.insert(0, s)
        self._fetch()

    def _set_month(self):
        today = datetime.now()
        first = today.replace(day=1)
        # Last day of the month: go to 1st of next month then back 1 day
        import calendar
        last_day = calendar.monthrange(today.year, today.month)[1]
        last = today.replace(day=last_day)
        if HAS_CAL:
            self._from_entry.set_date(first)
            self._to_entry.set_date(last)
        else:
            self._from_entry.delete(0, "end")
            self._from_entry.insert(0, first.strftime("%d-%m-%Y"))
            self._to_entry.delete(0, "end")
            self._to_entry.insert(0, last.strftime("%d-%m-%Y"))
        self._fetch()

    def _on_double_click(self, event):
        sel = self._tree.focus()
        if not sel:
            return
        from ui.order_details import OrderDetailsPopup
        OrderDetailsPopup(self, int(sel), self._fetch)

    def refresh(self):
        pass


def _fmt_date(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return d


def _parse_date(s):
    """Parse DD-MM-YYYY → YYYY-MM-DD."""
    try:
        return datetime.strptime(s.strip(), "%d-%m-%Y").strftime("%Y-%m-%d")
    except Exception:
        return ""
