"""
ui/all_orders.py — View all orders with status filter and quick actions
"""
import tkinter as tk
from tkinter import ttk, messagebox

from ui.theme   import COLORS, FONTS, STATUS_COLORS, STATUS_LIST
from ui.widgets import make_btn, build_tree
import database as db


class AllOrdersFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self._all_rows = []
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=COLORS["card_bg"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="All Orders", bg=COLORS["card_bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(side="left", padx=20, pady=14)
        tk.Frame(self, bg=COLORS["border"], height=1).pack(fill="x")

        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=24, pady=20)

        # ── Filter / toolbar ───────────────────────────────────────────────────
        toolbar = tk.Frame(body, bg=COLORS["card_bg"], padx=16, pady=12)
        toolbar.pack(fill="x", pady=(0, 14))

        tk.Label(toolbar, text="Filter by Status:", bg=COLORS["card_bg"],
                 fg=COLORS["text_dim"], font=FONTS["bold"]).pack(side="left", padx=(0, 8))

        self._status_var = tk.StringVar(value="All")
        status_opts = ["All"] + STATUS_LIST
        status_cb = ttk.Combobox(toolbar, textvariable=self._status_var,
                                  values=status_opts, width=16, state="readonly")
        status_cb.pack(side="left", padx=(0, 12), ipady=4)
        status_cb.bind("<<ComboboxSelected>>", lambda e: self._apply_filter())

        make_btn(toolbar, "🔄 Refresh",    self.refresh, "neutral").pack(side="left", padx=(0, 8))
        make_btn(toolbar, "➕ New Order", lambda: self.app.show_frame("new_order"),
                 "primary").pack(side="right")

        # Count label
        self._count_lbl = tk.Label(body, text="", bg=COLORS["bg"],
                                    fg=COLORS["text_dim"], font=FONTS["small"])
        self._count_lbl.pack(anchor="w", pady=(0, 6))

        # ── Orders table ───────────────────────────────────────────────────────
        cols   = ("order_id", "order_date", "name", "phone", "total_amount", "status", "payment_method")
        heads  = ("Order #",  "Date",       "Customer", "Phone", "Total (₹)", "Status", "Payment")
        widths = (70, 100, 200, 120, 100, 100, 90)

        tf, self._tree = build_tree(body, cols, heads, widths, height=18)
        tf.pack(fill="both", expand=True)

        for status, color in STATUS_COLORS.items():
            self._tree.tag_configure(f"s_{status}", foreground=color)

        self._tree.bind("<Double-1>",  self._on_double_click)
        self._tree.bind("<Button-3>",  self._show_context_menu)

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
        self._ctx_menu.add_command(label="🖨️  Print Receipt", command=self._print_selected)
        self._ctx_menu.add_command(label="📲  WhatsApp Receipt (PNG)", command=self._whatsapp_selected)
        self._ctx_menu.add_command(label="🏷️  Print Dispatch Slip", command=self._print_dispatch_selected)
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="✅ Mark as Ready",     command=lambda: self._quick_status("Ready"))
        self._ctx_menu.add_command(label="📦 Mark as Delivered",  command=lambda: self._quick_status("Delivered"))
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="🗑️  Delete Order",  command=self._delete_selected)

    # ── Data loading ───────────────────────────────────────────────────────────

    def refresh(self):
        self._all_rows = db.get_recent_orders(limit=500)
        self._status_var.set("All")
        self._apply_filter()

    def _apply_filter(self):
        status = self._status_var.get()
        if status == "All":
            rows = self._all_rows
        else:
            rows = [r for r in self._all_rows if r["status"] == status]

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
        self._count_lbl.config(text=f"Showing {len(rows)} order(s)")

    # ── Actions ────────────────────────────────────────────────────────────────

    def _get_selected_id(self):
        sel = self._tree.focus()
        return int(sel) if sel else None

    def _on_double_click(self, event):
        oid = self._get_selected_id()
        if oid:
            self._open_details(oid)

    def _show_context_menu(self, event):
        item = self._tree.identify_row(event.y)
        if item:
            self._tree.selection_set(item)
            self._tree.focus(item)
            self._ctx_menu.post(event.x_root, event.y_root)

    def _view_selected(self):
        oid = self._get_selected_id()
        if oid:
            self._open_details(oid)

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

    def _quick_status(self, status):
        oid = self._get_selected_id()
        if not oid:
            return
        
        if status == "Ready":
            if not db.are_all_items_returned(oid):
                messagebox.showwarning(
                    "Items Pending Wash",
                    "Cannot change status to 'Ready'!\n\nSome clothes in this order are still in washing facilities.",
                    parent=self
                )
                return

        order = db.get_order_full(oid)
        became_ready = order and order.get("status") != "Ready" and status == "Ready"
        db.update_order_status(oid, status)
        self.refresh()
        if became_ready:
            try:
                from utils.receipt import prompt_whatsapp_ready_notification
                prompt_whatsapp_ready_notification(
                    db.get_order_full(oid), parent_window=self
                )
            except Exception as exc:
                messagebox.showerror("WhatsApp Error", str(exc), parent=self)

    def _delete_selected(self):
        oid = self._get_selected_id()
        if not oid:
            return
        if messagebox.askyesno(
            "Delete Order",
            f"Are you sure you want to permanently delete Order #{oid}?\n"
            "This cannot be undone.",
            parent=self
        ):
            db.delete_order(oid)
            self.refresh()

    def _open_details(self, order_id):
        from ui.order_details import OrderDetailsPopup
        OrderDetailsPopup(self, order_id, self.refresh)


def _fmt_date(d):
    try:
        from datetime import datetime
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return d
