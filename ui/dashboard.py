"""
ui/dashboard.py — Dashboard home screen with stats cards and recent orders
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime

from ui.theme   import COLORS, FONTS, STATUS_COLORS
from ui.widgets import make_btn, build_tree
import database as db


class DashboardFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self._build()
        # Load real data immediately on creation
        self.refresh()

    def _build(self):
        # ── Top header bar ─────────────────────────────────────────────────────
        header = tk.Frame(self, bg=COLORS["card_bg"])
        header.pack(fill="x")

        tk.Label(header, text="Dashboard", bg=COLORS["card_bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(side="left", padx=20, pady=14)

        tk.Label(header, text="Victory Laundry Management",
                 bg=COLORS["card_bg"], fg=COLORS["text_dim"],
                 font=FONTS["small"]).pack(side="right", padx=20)

        tk.Frame(self, bg=COLORS["border"], height=1).pack(fill="x")

        # ── Scrollable body ────────────────────────────────────────────────────
        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=24, pady=20)

        # Stats row
        self._stats_frame = tk.Frame(body, bg=COLORS["bg"])
        self._stats_frame.pack(fill="x", pady=(0, 20))

        self._stat_cards = {}
        stat_defs = [
            ("today_orders",    "🧺",  "Today's Orders",   COLORS["info_fg"]),
            ("today_revenue",   "💰",  "Today's Revenue",  COLORS["success_fg"]),
            ("pending",         "⏳",  "Pending Orders",   COLORS["warning_fg"]),
            ("ready",           "✅",  "Ready for Pickup", COLORS["success"]),
            ("total_customers", "👥",  "Total Customers",  COLORS["accent"]),
            ("total_orders",    "📋",  "Total Orders",     COLORS["text_dim"]),
        ]
        for col, (key, icon, label, color) in enumerate(stat_defs):
            card = self._make_stat_card(self._stats_frame, icon, label, "—", color)
            card.grid(row=0, column=col, padx=6, pady=4, sticky="nsew")
            self._stat_cards[key] = card
            self._stats_frame.columnconfigure(col, weight=1)

        # ── Quick actions ──────────────────────────────────────────────────────
        actions_frame = tk.Frame(body, bg=COLORS["bg"])
        actions_frame.pack(fill="x", pady=(0, 16))

        make_btn(actions_frame, "  ➕  New Order",
                 lambda: self.app.show_frame("new_order"),
                 style="primary").pack(side="left", padx=(0, 8))

        make_btn(actions_frame, "  🔍  Search Orders",
                 lambda: self.app.show_frame("search"),
                 style="neutral").pack(side="left", padx=(0, 8))

        make_btn(actions_frame, "  📅  Date Records",
                 lambda: self.app.show_frame("date_records"),
                 style="neutral").pack(side="left", padx=(0, 8))

        make_btn(actions_frame, "  🔄  Refresh",
                 self.refresh,
                 style="neutral").pack(side="right")

        # ── Recent orders table ────────────────────────────────────────────────
        lbl_frame = tk.Frame(body, bg=COLORS["bg"])
        lbl_frame.pack(fill="x", pady=(4, 8))
        tk.Label(lbl_frame, text="Recent Orders", bg=COLORS["bg"],
                 fg=COLORS["accent"], font=FONTS["large"]).pack(side="left")

        cols = ("order_id", "order_date", "name", "phone", "total_amount", "status", "payment_method")
        heads = ("Order #", "Date", "Customer", "Phone", "Total (₹)", "Status", "Payment")
        widths = (70, 100, 180, 120, 100, 100, 90)

        tree_frame, self._tree = build_tree(body, cols, heads, widths, height=14)
        tree_frame.pack(fill="both", expand=True)

        self._tree.bind("<Double-1>", self._on_double_click)

        # Status tags
        for status, color in STATUS_COLORS.items():
            self._tree.tag_configure(f"s_{status}", foreground=color)

    def _make_stat_card(self, parent, icon, label, value, color):
        card = tk.Frame(parent, bg=COLORS["card_bg"], padx=16, pady=16,
                        relief="flat", bd=0)
        card.columnconfigure(0, weight=1)

        tk.Label(card, text=icon, bg=COLORS["card_bg"],
                 fg=color, font=("Segoe UI", 22)).grid(row=0, column=0, sticky="w")

        val_lbl = tk.Label(card, text=value, bg=COLORS["card_bg"],
                           fg=color, font=FONTS["xxlarge"])
        val_lbl.grid(row=1, column=0, sticky="w", pady=(4, 2))

        tk.Label(card, text=label, bg=COLORS["card_bg"],
                 fg=COLORS["text_dim"], font=FONTS["small"]).grid(row=2, column=0, sticky="w")

        card._val_label = val_lbl
        card._color = color
        return card

    def _update_stat(self, key, value):
        card = self._stat_cards.get(key)
        if not card:
            return
        if key == "today_revenue":
            card._val_label.config(text=f"₹{value:,.2f}")
        else:
            card._val_label.config(text=str(value))

    def refresh(self):
        try:
            stats = db.get_dashboard_stats()
            for key, val in stats.items():
                self._update_stat(key, val)

            rows = db.get_recent_orders(limit=50)
            self._tree.delete(*self._tree.get_children())
            for i, row in enumerate(rows):
                tag_bg = "even" if i % 2 == 0 else "odd"
                tag_st = f"s_{row['status']}"
                date_disp = _fmt_date(row["order_date"])
                self._tree.insert("", "end",
                    iid=str(row["order_id"]),
                    values=(
                        f"#{row['order_id']}",
                        date_disp,
                        row["name"],
                        row["phone"],
                        f"₹{row['total_amount']:.2f}",
                        row["status"],
                        row.get("payment_method", "") or "—",
                    ),
                    tags=(tag_bg, tag_st)
                )
        except Exception:
            pass  # DB not ready yet on very first init call

    def _on_double_click(self, event):
        sel = self._tree.focus()
        if not sel:
            return
        order_id = int(sel)
        _open_details(self, order_id, self.refresh)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fmt_date(d: str) -> str:
    try:
        from datetime import datetime
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return d


def _open_details(parent_widget, order_id, refresh_cb=None):
    from ui.order_details import OrderDetailsPopup
    OrderDetailsPopup(parent_widget, order_id, refresh_cb)
