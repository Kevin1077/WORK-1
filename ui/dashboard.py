"""
ui/dashboard.py — Dashboard home screen with stats cards and recent orders
"""
import tkinter as tk
from tkinter import ttk, messagebox
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
        self._tree.bind("<Button-3>", self._show_context_menu)

        # Context menu
        self._ctx_menu = tk.Menu(self, tearoff=0,
                                  bg=COLORS["card_bg2"],
                                  fg=COLORS["text"],
                                  activebackground=COLORS["sidebar_active"],
                                  activeforeground=COLORS["accent"],
                                  font=FONTS["default"])
        self._ctx_menu.add_command(label="📄 View Details", command=self._view_selected)
        self._ctx_menu.add_command(label="✏️  Edit Order",  command=self._edit_selected)
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="📲  WhatsApp Receipt (PDF)", command=self._whatsapp_selected)
        self._ctx_menu.add_command(label="🖨️  Print Receipt", command=self._print_selected)
        self._ctx_menu.add_command(label="🏷️  Print Dispatch Slip", command=self._print_dispatch_selected)
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="🗑️  Delete Order",  command=self._delete_selected)

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

    def _get_selected_id(self):
        sel = self._tree.focus()
        return int(sel) if sel else None

    def _on_double_click(self, event):
        oid = self._get_selected_id()
        if oid:
            _open_details(self, oid, self.refresh)

    def _show_context_menu(self, event):
        item = self._tree.identify_row(event.y)
        if item:
            self._tree.selection_set(item)
            self._tree.focus(item)
            self._ctx_menu.post(event.x_root, event.y_root)

    def _view_selected(self):
        oid = self._get_selected_id()
        if oid:
            _open_details(self, oid, self.refresh)

    def _edit_selected(self):
        oid = self._get_selected_id()
        if oid:
            from ui.edit_order import EditOrderPopup
            EditOrderPopup(self, oid, self.refresh)

    def _print_selected(self):
        oid = self._get_selected_id()
        if not oid:
            return
        order = db.get_order_full(oid)
        if order:
            try:
                from utils.receipt import open_receipt
                open_receipt(order)
            except Exception as e:
                messagebox.showerror("Print Error", str(e), parent=self)

    def _whatsapp_selected(self):
        oid = self._get_selected_id()
        if not oid:
            return
        order = db.get_order_full(oid)
        if order:
            try:
                from utils.receipt import send_whatsapp_receipt
                send_whatsapp_receipt(order, parent_window=self)
            except Exception as e:
                messagebox.showerror("WhatsApp Error", str(e), parent=self)

    def _print_dispatch_selected(self):
        oid = self._get_selected_id()
        if not oid:
            return
        order = db.get_order_full(oid)
        if order:
            try:
                from utils.dispatch_slip import open_dispatch_slip
                open_dispatch_slip(order)
            except Exception as e:
                messagebox.showerror("Print Error", str(e), parent=self)

    def _delete_selected(self):
        oid = self._get_selected_id()
        if not oid:
            return
        if messagebox.askyesno(
            "Delete Order",
            f"Are you sure you want to permanently delete Order #{oid}?\nThis cannot be undone.",
            parent=self
        ):
            db.delete_order(oid)
            self.refresh()


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
