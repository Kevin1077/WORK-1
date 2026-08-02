"""
ui/order_details.py — Order details popup (Toplevel modal window)
Shows full order info, allows status update, edit, delete and print receipt.
"""
import tkinter as tk
from tkinter import ttk, messagebox

from ui.theme   import COLORS, FONTS, STATUS_COLORS, STATUS_LIST
from ui.widgets import make_btn
import database as db


class OrderDetailsPopup(tk.Toplevel):
    def __init__(self, parent, order_id: int, refresh_cb=None):
        super().__init__(parent)
        self.order_id   = order_id
        self.refresh_cb = refresh_cb
        self._order     = None

        self.title(f"Order #{order_id} — Victory Laundry")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.grab_set()
        self.focus_set()

        self._load_and_build()
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w)//2}+{(sh - h)//2}")

    # ── Data ──────────────────────────────────────────────────────────────────

    def _load_and_build(self):
        self._order = db.get_order_full(self.order_id)
        if not self._order:
            messagebox.showerror("Error", f"Order #{self.order_id} not found.", parent=self)
            self.destroy()
            return
        self._build()

    def _build(self):
        o = self._order

        # ── Top bar ───────────────────────────────────────────────────────────
        tk.Frame(self, bg=COLORS["accent"], height=4).pack(fill="x")

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=COLORS["card_bg"], padx=24, pady=16)
        hdr.pack(fill="x")

        tk.Label(hdr, text=f"Order #{o['order_id']}",
                 bg=COLORS["card_bg"], fg=COLORS["accent"],
                 font=FONTS["title"]).pack(side="left")

        status_color = STATUS_COLORS.get(o["status"], COLORS["text"])
        tk.Label(hdr, text=f"  {o['status']}  ",
                 bg=status_color, fg=COLORS["card_bg"],
                 font=FONTS["small_bold"], padx=8, pady=3).pack(side="left", padx=16)

        self.destroy_btn = make_btn(hdr, "✕ Close", self.destroy, "neutral")
        self.destroy_btn.pack(side="right")

        tk.Frame(self, bg=COLORS["border"], height=1).pack(fill="x")

        # ── Main content ───────────────────────────────────────────────────────
        content = tk.Frame(self, bg=COLORS["bg"])
        content.pack(fill="both", expand=True, padx=24, pady=20)

        # Two-column top section
        top = tk.Frame(content, bg=COLORS["bg"])
        top.pack(fill="x", pady=(0, 16))

        # Customer card
        cust_card = tk.Frame(top, bg=COLORS["card_bg"], padx=16, pady=14)
        cust_card.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(cust_card, text="Customer Details",
                 bg=COLORS["card_bg"], fg=COLORS["accent"],
                 font=FONTS["bold"]).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        fields = [
            ("Name",    o.get("name",    "")),
            ("Phone",   o.get("phone",   "")),
            ("Place",   o.get("place",   "—")),
            ("Address", o.get("address", "—")),
        ]
        for r, (lbl, val) in enumerate(fields, start=1):
            tk.Label(cust_card, text=f"{lbl}:", bg=COLORS["card_bg"],
                     fg=COLORS["text_dim"], font=FONTS["small_bold"]).grid(
                row=r, column=0, sticky="nw", padx=(0, 10), pady=2)
            tk.Label(cust_card, text=val or "—", bg=COLORS["card_bg"],
                     fg=COLORS["text"], font=FONTS["default"],
                     wraplength=220, justify="left").grid(
                row=r, column=1, sticky="nw", pady=2)

        # Order meta card
        meta_card = tk.Frame(top, bg=COLORS["card_bg"], padx=16, pady=14)
        meta_card.pack(side="left", fill="both", expand=True, padx=(10, 0))

        tk.Label(meta_card, text="Order Information",
                 bg=COLORS["card_bg"], fg=COLORS["accent"],
                 font=FONTS["bold"]).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        order_date = _fmt_date(o.get("order_date", ""))
        payment = o.get("payment_method", "") or "—"
        status_time = o.get("status_changed_at", "") or "—"

        meta_fields = [
            ("Order Date",      order_date),
            ("Payment",         payment),
            ("Notes",           o.get("notes", "—") or "—"),
            ("Status Changed",  status_time),
        ]
        for r, (lbl, val) in enumerate(meta_fields, start=1):
            tk.Label(meta_card, text=f"{lbl}:", bg=COLORS["card_bg"],
                     fg=COLORS["text_dim"], font=FONTS["small_bold"]).grid(
                row=r, column=0, sticky="nw", padx=(0, 10), pady=2)
            tk.Label(meta_card, text=val, bg=COLORS["card_bg"],
                     fg=COLORS["text"], font=FONTS["default"],
                     wraplength=200, justify="left").grid(
                row=r, column=1, sticky="nw", pady=2)

        # Status update row
        r_next = len(meta_fields) + 1
        tk.Label(meta_card, text="Update Status:", bg=COLORS["card_bg"],
                 fg=COLORS["text_dim"], font=FONTS["small_bold"]).grid(
            row=r_next, column=0, sticky="w", padx=(0, 10), pady=(12, 2))

        self._status_var = tk.StringVar(value=o["status"])
        status_cb = ttk.Combobox(meta_card, textvariable=self._status_var,
                                  values=STATUS_LIST, width=16, state="readonly")
        status_cb.grid(row=r_next, column=1, sticky="w", pady=(12, 2), ipady=3)

        make_btn(meta_card, "Save Status", self._save_status, "success").grid(
            row=r_next + 1, column=1, sticky="w", pady=(6, 0)
        )

        # ── Items table ────────────────────────────────────────────────────────
        tk.Frame(content, bg=COLORS["border"], height=1).pack(fill="x", pady=(0, 12))
        tk.Label(content, text="Order Items",
                 bg=COLORS["bg"], fg=COLORS["accent"],
                 font=FONTS["bold"]).pack(anchor="w", pady=(0, 8))

        tbl_frame = tk.Frame(content, bg=COLORS["card_bg"])
        tbl_frame.pack(fill="x")

        # Header row
        hdr_row = tk.Frame(tbl_frame, bg=COLORS["table_header"])
        hdr_row.pack(fill="x")
        for text, w in [("S.No", 50), ("Cloth Type", 150), ("Qty", 50), ("Price/Unit (₹)", 110), ("Subtotal (₹)", 110), ("Remarks", 120)]:
            tk.Label(hdr_row, text=text, bg=COLORS["table_header"],
                     fg=COLORS["accent"], font=FONTS["small_bold"],
                     width=w // 10, anchor="w", padx=8, pady=6).pack(side="left")

        # Item rows
        for i, item in enumerate(o.get("items", []), start=1):
            row_bg = COLORS["table_row"] if i % 2 != 0 else COLORS["table_alt"]
            row_f = tk.Frame(tbl_frame, bg=row_bg)
            row_f.pack(fill="x")
            item_num = item.get("item_number", i)
            vals = [
                (str(item_num),                     50),
                (item["cloth_type"],                150),
                (str(item["quantity"]),              50),
                (f"₹{item['price_per_unit']:.2f}",  110),
                (f"₹{item['subtotal']:.2f}",         110),
                (item.get("item_notes", "") or "—", 120),
            ]
            for val, w in vals:
                tk.Label(row_f, text=val, bg=row_bg,
                         fg=COLORS["text"], font=FONTS["default"],
                         width=w // 10, anchor="w", padx=8, pady=8).pack(side="left")

        # Total row
        total_row = tk.Frame(tbl_frame, bg=COLORS["accent"])
        total_row.pack(fill="x")
        tk.Label(total_row, text="TOTAL",
                 bg=COLORS["accent"], fg=COLORS["card_bg"],
                 font=FONTS["bold"], padx=10, pady=8).pack(side="left")
        tk.Label(total_row, text=f"₹{o['total_amount']:.2f}",
                 bg=COLORS["accent"], fg=COLORS["card_bg"],
                 font=FONTS["large"]).pack(side="right", padx=20)

        # ── Action buttons ─────────────────────────────────────────────────────
        tk.Frame(content, bg=COLORS["border"], height=1).pack(fill="x", pady=(16, 12))
        btn_row = tk.Frame(content, bg=COLORS["bg"])
        btn_row.pack(fill="x")

        make_btn(btn_row, "✏️  Edit Order",           self._edit,             "edit").pack(side="left", padx=(0, 8))
        make_btn(btn_row, "🖨️  Print Receipt",       self._print_receipt,    "neutral").pack(side="left", padx=(0, 8))
        make_btn(btn_row, "🏷️  Print Dispatch Slip", self._print_dispatch,   "neutral").pack(side="left", padx=(0, 8))
        make_btn(btn_row, "🗑️  Delete",              self._delete,           "danger").pack(side="left", padx=(0, 8))
        make_btn(btn_row, "✕  Close",                self.destroy,           "neutral").pack(side="right", padx=(8, 0))
        make_btn(btn_row, "📲  WhatsApp Receipt (PDF)", self._whatsapp_receipt, "success").pack(side="right")

    # ── Button handlers ────────────────────────────────────────────────────────

    def _save_status(self):
        new_status = self._status_var.get()
        became_ready = self._order.get("status") != "Ready" and new_status == "Ready"
        db.update_order_status(self.order_id, new_status)
        if self.refresh_cb:
            self.refresh_cb()
        messagebox.showinfo("Status Updated",
                            f"Order #{self.order_id} status set to '{new_status}'.",
                            parent=self)
        if became_ready:
            try:
                from utils.receipt import prompt_whatsapp_ready_notification
                prompt_whatsapp_ready_notification(
                    db.get_order_full(self.order_id), parent_window=self
                )
            except Exception as exc:
                messagebox.showerror("WhatsApp Error", str(exc), parent=self)
        self.destroy()
        # Re-open with fresh data
        OrderDetailsPopup(self.master, self.order_id, self.refresh_cb)

    def _edit(self):
        self.destroy()
        from ui.edit_order import EditOrderPopup
        EditOrderPopup(self.master, self.order_id, self.refresh_cb)

    def _print(self):
        self._print_receipt()

    def _print_receipt(self):
        order = db.get_order_full(self.order_id)
        if order:
            try:
                from utils.receipt import open_receipt
                open_receipt(order)
            except Exception as e:
                messagebox.showerror("Print Error", str(e), parent=self)

    def _whatsapp_receipt(self):
        order = db.get_order_full(self.order_id)
        if order:
            try:
                from utils.receipt import send_whatsapp_receipt
                send_whatsapp_receipt(order, parent_window=self)
            except Exception as e:
                p = self if hasattr(self, "winfo_exists") and self.winfo_exists() else None
                messagebox.showerror("WhatsApp Error", str(e), parent=p)

    def _print_dispatch(self):
        order = db.get_order_full(self.order_id)
        if order:
            try:
                from utils.dispatch_slip import open_dispatch_slip
                open_dispatch_slip(order)
            except Exception as e:
                messagebox.showerror("Print Error", str(e), parent=self)

    def _delete(self):
        if messagebox.askyesno(
            "Delete Order",
            f"Permanently delete Order #{self.order_id}?\nThis cannot be undone.",
            parent=self
        ):
            db.delete_order(self.order_id)
            if self.refresh_cb:
                self.refresh_cb()
            self.destroy()


def _fmt_date(d):
    try:
        from datetime import datetime
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return d or ""
