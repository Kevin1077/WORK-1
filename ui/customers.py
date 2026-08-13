"""
ui/customers.py — Customers section with aggregation, detail view, per-customer & bulk WhatsApp messaging
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import threading
import time
import logging

from ui.theme   import COLORS, FONTS, STATUS_COLORS
from ui.widgets import make_btn, make_entry, build_tree
from ui.order_details import OrderDetailsPopup
import database as db

LOGGER = logging.getLogger(__name__)


def _fmt_date(d_str):
    if not d_str or d_str == "—":
        return "—"
    try:
        dt = datetime.strptime(str(d_str)[:10], "%Y-%m-%d")
        return dt.strftime("%d-%m-%Y")
    except Exception:
        return str(d_str)


# ── Customers Main Frame ──────────────────────────────────────────────────────

class CustomersFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self._all_customers = []
        self._filtered_customers = []
        self._build()
        self.refresh()

    def _build(self):
        # Header bar
        hdr = tk.Frame(self, bg=COLORS["card_bg"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="Customers", bg=COLORS["card_bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(side="left", padx=20, pady=14)
        tk.Label(hdr, text="Victory Laundry Management", bg=COLORS["card_bg"],
                 fg=COLORS["text_dim"], font=FONTS["small"]).pack(side="right", padx=20)
        tk.Frame(self, bg=COLORS["border"], height=1).pack(fill="x")

        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=24, pady=20)

        # ── Toolbar ──────────────────────────────────────────────────────────
        toolbar = tk.Frame(body, bg=COLORS["card_bg"], padx=16, pady=12)
        toolbar.pack(fill="x", pady=(0, 14))

        # Search box
        tk.Label(toolbar, text="Search:", bg=COLORS["card_bg"],
                 fg=COLORS["text_dim"], font=FONTS["bold"]).pack(side="left", padx=(0, 6))

        self._search_var = tk.StringVar()
        search_e = make_entry(toolbar, textvariable=self._search_var, width=22)
        search_e.pack(side="left", padx=(0, 16), ipady=3)
        self._search_var.trace_add("write", lambda *a: self._apply_filter_and_sort())

        # Sort selector
        tk.Label(toolbar, text="Sort by:", bg=COLORS["card_bg"],
                 fg=COLORS["text_dim"], font=FONTS["bold"]).pack(side="left", padx=(0, 6))

        self._sort_var = tk.StringVar(value="Last Visit (Newest)")
        sort_opts = [
            "Last Visit (Newest)",
            "Total Orders (High to Low)",
            "Total Spent (High to Low)",
            "Name (A-Z)"
        ]
        sort_cb = ttk.Combobox(toolbar, textvariable=self._sort_var,
                               values=sort_opts, width=22, state="readonly")
        sort_cb.pack(side="left", padx=(0, 16), ipady=3)
        sort_cb.bind("<<ComboboxSelected>>", lambda e: self._apply_filter_and_sort())

        # Action Buttons
        make_btn(toolbar, "📢 Message All", self._open_bulk_message, "primary").pack(side="right", padx=(8, 0))
        make_btn(toolbar, "🔄 Refresh", self.refresh, "neutral").pack(side="right")

        # Count label
        self._count_lbl = tk.Label(body, text="", bg=COLORS["bg"],
                                    fg=COLORS["text_dim"], font=FONTS["small"])
        self._count_lbl.pack(anchor="w", pady=(0, 6))

        # ── Customers Table ───────────────────────────────────────────────────
        cols   = ("name", "phone", "total_orders", "total_spent", "last_visit", "action")
        heads  = ("Customer Name", "Phone Number", "Total Orders", "Total Spent (₹)", "Last Visit", "Message")
        widths = (200, 140, 110, 130, 120, 100)

        tf, self._tree = build_tree(body, cols, heads, widths, height=18)
        tf.pack(fill="both", expand=True)

        self._tree.bind("<ButtonRelease-1>", self._on_row_click)
        self._tree.bind("<Button-3>",        self._show_context_menu)

        # Context menu
        self._ctx_menu = tk.Menu(self, tearoff=0,
                                  bg=COLORS["card_bg2"],
                                  fg=COLORS["text"],
                                  activebackground=COLORS["sidebar_active"],
                                  activeforeground=COLORS["accent"],
                                  font=FONTS["default"])
        self._ctx_menu.add_command(label="📄 View Details & History", command=self._view_selected_details)
        self._ctx_menu.add_command(label="💬 Send WhatsApp Message",  command=self._message_selected)
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="🗑️ Delete Customer",       command=self._delete_selected_customer)

    def refresh(self):
        self._all_customers = db.get_customer_aggregations()
        self._apply_filter_and_sort()

    def _apply_filter_and_sort(self):
        query = self._search_var.get().strip().lower()
        if query:
            filtered = [
                c for c in self._all_customers
                if query in c["name"].lower() or query in c["phone"].lower() or query in c["normalized_phone"].lower()
            ]
        else:
            filtered = list(self._all_customers)

        sort_mode = self._sort_var.get()
        if sort_mode == "Total Orders (High to Low)":
            filtered.sort(key=lambda c: c["total_orders"], reverse=True)
        elif sort_mode == "Total Spent (High to Low)":
            filtered.sort(key=lambda c: c["total_spent"], reverse=True)
        elif sort_mode == "Name (A-Z)":
            filtered.sort(key=lambda c: c["name"].lower())
        else: # Last Visit (Newest)
            filtered.sort(key=lambda c: c["last_visit"], reverse=True)

        self._filtered_customers = filtered
        self._populate_tree(filtered)

    def _populate_tree(self, customers):
        self._tree.delete(*self._tree.get_children())
        for i, cust in enumerate(customers):
            tag_bg = "even" if i % 2 == 0 else "odd"
            phone_disp = cust["phone"]
            if not phone_disp.startswith("+") and len(phone_disp) == 10:
                phone_disp = f"+91 {phone_disp}"
            self._tree.insert("", "end",
                iid=str(cust["normalized_phone"]),
                values=(
                    cust["name"],
                    phone_disp,
                    str(cust["total_orders"]),
                    f"₹{cust['total_spent']:,.2f}",
                    _fmt_date(cust["last_visit"]),
                    "💬 Message",
                ),
                tags=(tag_bg,)
            )
        self._count_lbl.config(text=f"Showing {len(customers)} customer(s)")

    def _get_cust_by_iid(self, iid: str):
        """Look up a customer dict by its treeview iid (normalised phone)."""
        if not iid:
            return None
        for c in self._filtered_customers:
            if str(c["normalized_phone"]) == str(iid):
                return c
        return None

    def _get_selected_cust(self):
        sel = self._tree.focus()
        return self._get_cust_by_iid(sel)

    def _on_row_click(self, event):
        """Open customer detail on any single click on a data row."""
        iid = self._tree.identify_row(event.y)
        if not iid:
            return
        # Set tree focus/selection so context menu and keyboard actions stay consistent
        self._tree.selection_set(iid)
        self._tree.focus(iid)
        cust = self._get_cust_by_iid(iid)
        if cust:
            CustomerDetailDialog(self, cust, self.refresh)

    def _show_context_menu(self, event):
        item = self._tree.identify_row(event.y)
        if item:
            self._tree.selection_set(item)
            self._tree.focus(item)
            self._ctx_menu.post(event.x_root, event.y_root)

    def _view_selected_details(self):
        cust = self._get_selected_cust()
        if cust:
            CustomerDetailDialog(self, cust, self.refresh)

    def _message_selected(self):
        cust = self._get_selected_cust()
        if cust:
            CustomerMessageDialog(self, cust)

    def _delete_selected_customer(self):
        cust = self._get_selected_cust()
        if not cust:
            return
        if messagebox.askyesno(
            "Confirm Delete Customer",
            f"Are you sure you want to delete customer '{cust['name']}' ({cust['phone']}) and all their {cust['total_orders']} order(s)?\n\n"
            "This action cannot be undone.",
            parent=self
        ):
            db.delete_customer_by_phone(cust["phone"])
            self.refresh()

    def _open_bulk_message(self):
        if not self._all_customers:
            messagebox.showinfo("Message All", "No customers available to message.", parent=self)
            return
        BulkMessageDialog(self, self._all_customers)


# ── Customer Detail Dialog ────────────────────────────────────────────────────

class CustomerDetailDialog(tk.Toplevel):
    def __init__(self, parent, customer: dict, refresh_cb=None):
        super().__init__(parent)
        self.customer = customer
        self.refresh_cb = refresh_cb

        self.title(f"Customer Profile — {customer['name']}")
        self.geometry("850x600")
        self.minsize(750, 500)
        self.configure(bg=COLORS["bg"])
        # No grab_set() — keep the parent list interactive so clicking
        # another customer row while this dialog is open works correctly.
        self.lift()
        self.focus_set()

        self._build()
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w)//2}+{(sh - h)//2}")

    def _build(self):
        # Header profile card
        card = tk.Frame(self, bg=COLORS["card_bg"], padx=20, pady=16)
        card.pack(fill="x", padx=16, pady=16)

        left = tk.Frame(card, bg=COLORS["card_bg"])
        left.pack(side="left", fill="both", expand=True)

        tk.Label(left, text=self.customer["name"], bg=COLORS["card_bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(anchor="w")

        phone_str = self.customer["phone"]
        if not phone_str.startswith("+") and len(phone_str) == 10:
            phone_str = f"+91 {phone_str}"
        tk.Label(left, text=f"📞 {phone_str}", bg=COLORS["card_bg"],
                 fg=COLORS["text"], font=FONTS["header"]).pack(anchor="w", pady=(2, 8))

        stats_text = (
            f"Total Orders: {self.customer['total_orders']}   |   "
            f"Total Spent: ₹{self.customer['total_spent']:,.2f}   |   "
            f"First Visit: {_fmt_date(self.customer['first_visit'])}   |   "
            f"Last Visit: {_fmt_date(self.customer['last_visit'])}"
        )
        tk.Label(left, text=stats_text, bg=COLORS["card_bg"],
                 fg=COLORS["text_dim"], font=FONTS["small"]).pack(anchor="w")

        btn_box = tk.Frame(card, bg=COLORS["card_bg"])
        btn_box.pack(side="right")

        make_btn(btn_box, "💬 Send WhatsApp Message",
                 lambda: CustomerMessageDialog(self, self.customer),
                 "primary").pack(side="left", padx=(0, 8))

        make_btn(btn_box, "🗑️ Delete Customer",
                 self._delete_customer,
                 "danger").pack(side="left")

        # Order history — must be called last so it fills remaining space
        self._build_order_history()

    def _delete_customer(self):
        if messagebox.askyesno(
            "Confirm Delete Customer",
            f"Are you sure you want to delete customer '{self.customer['name']}' ({self.customer['phone']}) and all their {self.customer['total_orders']} order(s)?\n\n"
            "This action cannot be undone.",
            parent=self
        ):
            db.delete_customer_by_phone(self.customer["phone"])
            self.destroy()
            if self.refresh_cb:
                self.refresh_cb()

    def _build_order_history(self):
        """Build the order history treeview section — called from _build()."""
        # Order history section header
        history_hdr = tk.Frame(self, bg=COLORS["bg"], padx=16)
        history_hdr.pack(fill="x", pady=(0, 6))

        tk.Label(history_hdr, text="Order History", bg=COLORS["bg"],
                 fg=COLORS["accent"], font=FONTS["large"]).pack(side="left")

        # History Treeview
        cols   = ("order_id", "order_date", "total_amount", "status", "payment_method")
        heads  = ("Order #", "Date", "Total (₹)", "Status", "Payment Method")
        widths = (80, 130, 120, 130, 140)

        tf, self._tree = build_tree(self, cols, heads, widths, height=12)
        tf.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        for status, color in STATUS_COLORS.items():
            self._tree.tag_configure(f"s_{status}", foreground=color)

        self._populate_order_history()
        self._tree.bind("<Double-1>", self._on_order_double_click)

    def _populate_order_history(self):
        """Clear and re-fill the order history treeview from self.customer['orders']."""
        self._tree.delete(*self._tree.get_children())
        orders = self.customer.get("orders", [])
        for i, row in enumerate(orders):
            tag_bg = "even" if i % 2 == 0 else "odd"
            tag_st = f"s_{row.get('status', '')}"
            self._tree.insert("", "end",
                iid=str(row["order_id"]),
                values=(
                    f"#{row['order_id']}",
                    _fmt_date(row["order_date"]),
                    f"₹{row['total_amount']:.2f}",
                    row.get("status", "Received"),
                    row.get("payment_method", "") or "—",
                ),
                tags=(tag_bg, tag_st)
            )

    def _on_order_double_click(self, event):
        sel = self._tree.focus()
        if sel and sel.isdigit():
            OrderDetailsPopup(self, int(sel), self._on_order_updated)

    def _on_order_updated(self):
        if self.refresh_cb:
            self.refresh_cb()
        # Reload this customer's aggregated data (orders may have changed)
        norm_p = self.customer["normalized_phone"]
        for c in db.get_customer_aggregations():
            if c["normalized_phone"] == norm_p:
                self.customer = c
                break
        self._populate_order_history()


# ── Customer Message Dialog (Per-Customer Free-Text WhatsApp) ─────────────────

class CustomerMessageDialog(tk.Toplevel):
    def __init__(self, parent, customer: dict):
        super().__init__(parent)
        self.customer = customer

        self.title(f"WhatsApp Message — {customer['name']}")
        self.geometry("520x380")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.grab_set()
        self.focus_set()

        self._build()
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w)//2}+{(sh - h)//2}")

    def _build(self):
        card = tk.Frame(self, bg=COLORS["card_bg"], padx=18, pady=14)
        card.pack(fill="x", padx=16, pady=16)

        phone_str = self.customer["phone"]
        if not phone_str.startswith("+") and len(phone_str) == 10:
            phone_str = f"+91 {phone_str}"

        tk.Label(card, text=f"Recipient: {self.customer['name']}", bg=COLORS["card_bg"],
                 fg=COLORS["text"], font=FONTS["bold"]).pack(anchor="w")
        tk.Label(card, text=f"WhatsApp Number: {phone_str}", bg=COLORS["card_bg"],
                 fg=COLORS["text_dim"], font=FONTS["small"]).pack(anchor="w", pady=(2, 0))

        # Message box
        msg_frame = tk.Frame(self, bg=COLORS["bg"], padx=16)
        msg_frame.pack(fill="both", expand=True)

        tk.Label(msg_frame, text="Message Text:", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=FONTS["bold"]).pack(anchor="w", pady=(0, 6))

        self.txt_area = tk.Text(
            msg_frame, height=7,
            bg=COLORS["input_bg"], fg=COLORS["input_fg"],
            insertbackground=COLORS["text"], relief="flat",
            font=FONTS["default"], highlightthickness=1,
            highlightbackground=COLORS["border2"],
            highlightcolor=COLORS["accent"]
        )
        self.txt_area.pack(fill="both", expand=True)
        default_msg = f"Hello {self.customer['name']},\n\nThank you for choosing Victory Laundry! "
        self.txt_area.insert("1.0", default_msg)

        # Quick templates
        tmpl_frame = tk.Frame(msg_frame, bg=COLORS["bg"])
        tmpl_frame.pack(fill="x", pady=6)
        tk.Label(tmpl_frame, text="Quick templates:", bg=COLORS["bg"],
                 fg=COLORS["text_muted"], font=FONTS["small"]).pack(side="left", padx=(0, 6))

        def _set_tmpl(t_str):
            self.txt_area.delete("1.0", "end")
            self.txt_area.insert("1.0", t_str.format(name=self.customer['name']))

        t1 = "Hello {name},\nWe have a special 10% discount on laundry services this week! Visit Victory Laundry today."
        t2 = "Hello {name},\nJust checking in from Victory Laundry! Let us know if you need pickup for your laundry."

        tk.Button(tmpl_frame, text="Promo Offer", command=lambda: _set_tmpl(t1),
                  bg=COLORS["card_bg"], fg=COLORS["text_dim"], font=FONTS["small"], relief="flat", padx=6, pady=2, cursor="hand2").pack(side="left", padx=2)
        tk.Button(tmpl_frame, text="Greeting", command=lambda: _set_tmpl(t2),
                  bg=COLORS["card_bg"], fg=COLORS["text_dim"], font=FONTS["small"], relief="flat", padx=6, pady=2, cursor="hand2").pack(side="left", padx=2)

        # Buttons
        btn_bar = tk.Frame(self, bg=COLORS["bg"], padx=16, pady=16)
        btn_bar.pack(fill="x")

        make_btn(btn_bar, "📲 Open in WhatsApp Web", self._send, "primary").pack(side="right", padx=(8, 0))
        make_btn(btn_bar, "Cancel", self.destroy, "neutral").pack(side="right")

    def _send(self):
        text = self.txt_area.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Empty Message", "Please type a message before sending.", parent=self)
            return

        phone = self.customer["phone"]
        self.destroy()

        def _bg_send():
            try:
                from whatsapp_web import prepare_message
                prepare_message(phone, text)
            except Exception as exc:
                err = str(exc).lower()
                if "closed" in err or "target page" in err or "browser" in err:
                    return
                messagebox.showerror("WhatsApp Error", f"Could not prepare WhatsApp message:\n{exc}")

        threading.Thread(target=_bg_send, daemon=True).start()


# ── Bulk Message Dialog (Broadcast to All/Selected) ───────────────────────────

class BulkMessageDialog(tk.Toplevel):
    def __init__(self, parent, customers: list):
        super().__init__(parent)
        self.customers = list(customers)
        self._checkbox_vars = {}

        self.title("Message All Customers — WhatsApp Broadcast")
        self.geometry("680x560")
        self.minsize(600, 480)
        self.configure(bg=COLORS["bg"])
        self.grab_set()
        self.focus_set()

        self._build()
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w)//2}+{(sh - h)//2}")

    def _build(self):
        hdr = tk.Frame(self, bg=COLORS["card_bg"], padx=18, pady=12)
        hdr.pack(side="top", fill="x")
        tk.Label(hdr, text="📢 Broadcast WhatsApp Message", bg=COLORS["card_bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(anchor="w")
        tk.Label(hdr, text="Send promotional messages or announcements to multiple customers.",
                 bg=COLORS["card_bg"], fg=COLORS["text_dim"], font=FONTS["small"]).pack(anchor="w", pady=(2, 0))

        # Footer live count & action buttons (packed side="bottom" first so it stays pinned at bottom)
        footer = tk.Frame(self, bg=COLORS["bg"], padx=18, pady=12)
        footer.pack(side="bottom", fill="x")

        self.count_lbl = tk.Label(footer, text="", bg=COLORS["bg"],
                                  fg=COLORS["accent"], font=FONTS["bold"])
        self.count_lbl.pack(side="left")

        make_btn(footer, "🚀 Send", self._confirm_send, "primary").pack(side="right", padx=(8, 0))
        make_btn(footer, "Cancel", self.destroy, "neutral").pack(side="right")

        # Body area
        body = tk.Frame(self, bg=COLORS["bg"], padx=18, pady=14)
        body.pack(side="top", fill="both", expand=True)

        # Message text box
        tk.Label(body, text="Message Content:", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=FONTS["bold"]).pack(anchor="w", pady=(0, 4))

        self.txt_area = tk.Text(
            body, height=5,
            bg=COLORS["input_bg"], fg=COLORS["input_fg"],
            insertbackground=COLORS["text"], relief="flat",
            font=FONTS["default"], highlightthickness=1,
            highlightbackground=COLORS["border2"],
            highlightcolor=COLORS["accent"]
        )
        self.txt_area.pack(fill="x", pady=(0, 10))
        self.txt_area.insert("1.0", "Greetings from Victory Laundry!\n\nWe have an exclusive offer for our valued customers. Visit us today for premium laundry services.")

        # Recipients list header with Select All
        recip_hdr = tk.Frame(body, bg=COLORS["bg"])
        recip_hdr.pack(fill="x", pady=(0, 6))

        tk.Label(recip_hdr, text="Select Recipients:", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=FONTS["bold"]).pack(side="left")

        self._select_all_var = tk.BooleanVar(value=True)
        chk_all = tk.Checkbutton(
            recip_hdr, text="Select All", variable=self._select_all_var,
            command=self._toggle_select_all, bg=COLORS["bg"], fg=COLORS["accent"],
            activebackground=COLORS["bg"], activeforeground=COLORS["accent"],
            selectcolor=COLORS["card_bg"], font=FONTS["small_bold"]
        )
        chk_all.pack(side="right")

        # Scrollable list of customers with checkboxes
        list_frame = tk.Frame(body, bg=COLORS["card_bg"], highlightthickness=1, highlightbackground=COLORS["border2"])
        list_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(list_frame, bg=COLORS["card_bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scroll_content = tk.Frame(canvas, bg=COLORS["card_bg"])

        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        canvas_win = canvas.create_window((0, 0), window=scroll_content, anchor="nw")
        scroll_content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_win, width=e.width))

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", lambda ev: canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        for cust in self.customers:
            norm_p = cust["normalized_phone"]
            var = tk.BooleanVar(value=True)
            self._checkbox_vars[norm_p] = (cust, var)
            var.trace_add("write", lambda *a: self._update_live_count())

            phone_disp = cust["phone"]
            if not phone_disp.startswith("+") and len(phone_disp) == 10:
                phone_disp = f"+91 {phone_disp}"

            chk_lbl = f"{cust['name']} ({phone_disp})"
            cb = tk.Checkbutton(
                scroll_content, text=chk_lbl, variable=var,
                bg=COLORS["card_bg"], fg=COLORS["text"],
                activebackground=COLORS["card_bg"], activeforeground=COLORS["text"],
                selectcolor=COLORS["bg"], font=FONTS["default"], anchor="w"
            )
            cb.pack(fill="x", padx=10, pady=4)

        self._update_live_count()

    def _toggle_select_all(self):
        val = self._select_all_var.get()
        for _, (_, var) in self._checkbox_vars.items():
            var.set(val)

    def _update_live_count(self):
        selected_cnt = sum(1 for _, (_, var) in self._checkbox_vars.items() if var.get())
        total_cnt = len(self._checkbox_vars)
        self.count_lbl.config(text=f"This will be sent to {selected_cnt} of {total_cnt} customer(s)")

    def _confirm_send(self):
        msg_text = self.txt_area.get("1.0", "end").strip()
        if not msg_text:
            messagebox.showwarning("Empty Message", "Please enter a message before sending.", parent=self)
            return

        selected_custs = [cust for _, (cust, var) in self._checkbox_vars.items() if var.get()]
        if not selected_custs:
            messagebox.showwarning("No Recipients", "Please select at least one customer to message.", parent=self)
            return

        if not messagebox.askyesno(
            "Confirm Broadcast",
            f"Are you sure you want to send this WhatsApp message to {len(selected_custs)} customer(s)?\n\n"
            "WhatsApp Web will open each chat one by one.",
            parent=self
        ):
            return

        self.destroy()
        # Launch Progress Window
        BulkProgressDialog(self.master, selected_custs, msg_text)


# ── Bulk Send Progress Dialog ──────────────────────────────────────────────────

class BulkProgressDialog(tk.Toplevel):
    def __init__(self, parent, targets: list, message: str):
        super().__init__(parent)
        self.targets = targets
        self.message = message
        self.succeeded = []
        self.failed = []

        self.title("Sending WhatsApp Broadcast...")
        self.geometry("450x220")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.grab_set()
        self.focus_set()

        self._build()
        self._center()

        # Start process in thread
        threading.Thread(target=self._run_bulk_send, daemon=True).start()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w)//2}+{(sh - h)//2}")

    def _build(self):
        body = tk.Frame(self, bg=COLORS["card_bg"], padx=20, pady=20)
        body.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(body, text="📢 Sending WhatsApp Messages...", bg=COLORS["card_bg"],
                 fg=COLORS["accent"], font=FONTS["large"]).pack(anchor="w")

        self.status_lbl = tk.Label(body, text="Initializing WhatsApp driver...", bg=COLORS["card_bg"],
                                   fg=COLORS["text"], font=FONTS["default"])
        self.status_lbl.pack(anchor="w", pady=(12, 10))

        self.pbar = ttk.Progressbar(body, orient="horizontal", mode="determinate", maximum=len(self.targets))
        self.pbar.pack(fill="x", pady=(0, 10))

        self.sub_lbl = tk.Label(body, text=f"0 of {len(self.targets)} completed", bg=COLORS["card_bg"],
                               fg=COLORS["text_dim"], font=FONTS["small"])
        self.sub_lbl.pack(anchor="w")

    def _update_progress(self, current_idx, total, current_name, current_phone):
        def _ui():
            self.pbar["value"] = current_idx
            self.status_lbl.config(text=f"Sending {current_idx} of {total}: {current_name} ({current_phone})")
            self.sub_lbl.config(text=f"Completed {current_idx} of {total}")
        self.after(0, _ui)

    def _run_bulk_send(self):
        from whatsapp_web import send_message  # auto-send variant for broadcast

        total = len(self.targets)
        for i, cust in enumerate(self.targets, start=1):
            phone = cust["phone"]
            name = cust["name"]
            self._update_progress(i, total, name, phone)

            try:
                send_message(phone, self.message)
                self.succeeded.append(cust)
                LOGGER.info("Bulk auto-send success for %s (%s)", name, phone)
            except Exception as exc:
                LOGGER.error("Bulk auto-send failed for %s (%s): %s", name, phone, exc)
                self.failed.append((cust, str(exc)))

            # Delay between recipients so WhatsApp Web fully loads the next chat
            if i < total:
                time.sleep(3.0)

        self.after(0, self._on_finished)

    def _on_finished(self):
        self.destroy()
        succ_cnt = len(self.succeeded)
        fail_cnt = len(self.failed)

        summary_msg = "WhatsApp Broadcast Complete!\n\n"
        summary_msg += f"✅ Successfully sent: {succ_cnt}\n"
        if fail_cnt > 0:
            summary_msg += f"❌ Failed: {fail_cnt}\n\nFailed Recipients:\n"
            for cust, err in self.failed[:5]:
                summary_msg += f"• {cust['name']} ({cust['phone']}): {err}\n"
            if fail_cnt > 5:
                summary_msg += f"... and {fail_cnt - 5} more."
        else:
            summary_msg += "All messages were sent successfully!"

        messagebox.showinfo("Broadcast Summary", summary_msg)
