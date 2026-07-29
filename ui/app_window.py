"""
ui/app_window.py — Main application window with sidebar navigation
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime

from ui.theme import COLORS, FONTS, SHOP_NAME


class AppWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._setup_window()
        self._setup_styles()
        self._build_layout()
        self._build_sidebar()
        self._create_frames()
        self.show_frame("dashboard")

    # ── Window setup ──────────────────────────────────────────────────────────

    def _setup_window(self):
        self.root.title(f"{SHOP_NAME} — Management System")
        self.root.geometry("1300x800")
        self.root.minsize(1100, 680)
        self.root.configure(bg=COLORS["bg"])
        # Center on screen
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"+{(sw - w)//2}+{(sh - h)//2}")
        self.root.iconbitmap(default="")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Treeview
        style.configure("Treeview",
            background=COLORS["table_row"],
            foreground=COLORS["text"],
            fieldbackground=COLORS["table_row"],
            rowheight=34,
            font=FONTS["default"],
            borderwidth=0,
        )
        style.configure("Treeview.Heading",
            background=COLORS["table_header"],
            foreground=COLORS["accent"],
            font=FONTS["bold"],
            relief="flat",
            borderwidth=0,
        )
        style.map("Treeview",
            background=[("selected", COLORS["table_sel_bg"])],
            foreground=[("selected", COLORS["table_sel_fg"])],
        )
        style.map("Treeview.Heading",
            background=[("active", COLORS["sidebar_active"])],
        )

        # Scrollbar
        style.configure("Vertical.TScrollbar",
            background=COLORS["border"],
            troughcolor=COLORS["card_bg"],
            arrowcolor=COLORS["text_dim"],
            borderwidth=0,
        )
        style.configure("Horizontal.TScrollbar",
            background=COLORS["border"],
            troughcolor=COLORS["card_bg"],
            borderwidth=0,
        )

        # Combobox
        style.configure("TCombobox",
            fieldbackground=COLORS["input_bg"],
            background=COLORS["input_bg"],
            foreground=COLORS["text"],
            arrowcolor=COLORS["text_dim"],
            bordercolor=COLORS["border2"],
            lightcolor=COLORS["border2"],
            darkcolor=COLORS["border2"],
        )
        style.map("TCombobox",
            fieldbackground=[("readonly", COLORS["input_bg"])],
            foreground=[("readonly", COLORS["text"])],
        )

        # Notebook (not used but good to have)
        style.configure("TNotebook", background=COLORS["bg"])
        style.configure("TNotebook.Tab",
            background=COLORS["card_bg"],
            foreground=COLORS["text_dim"],
            padding=[12, 6],
        )

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_layout(self):
        # Thin black accent line at top
        top_bar = tk.Frame(self.root, bg="#080707", height=3)
        top_bar.pack(side="top", fill="x")

        main = tk.Frame(self.root, bg=COLORS["bg"])
        main.pack(fill="both", expand=True)

        # Sidebar
        self.sidebar = tk.Frame(main, bg=COLORS["sidebar_bg"], width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Thin separator line between sidebar and content
        tk.Frame(main, bg="#BBBBBB", width=1).pack(side="left", fill="y")

        # Content area
        self.content = tk.Frame(main, bg=COLORS["bg"])
        self.content.pack(side="left", fill="both", expand=True)

    def _build_sidebar(self):
        sb = self.sidebar

        # Logo block
        logo_frame = tk.Frame(sb, bg=COLORS["sidebar_bg"])
        logo_frame.pack(fill="x", pady=(24, 28), padx=18)

        tk.Label(logo_frame, text="✦", bg=COLORS["sidebar_bg"],
                 fg=COLORS["accent"], font=("Segoe UI", 26, "bold")).pack()
        tk.Label(logo_frame, text=SHOP_NAME.upper(), bg=COLORS["sidebar_bg"],
                 fg=COLORS["accent"], font=("Segoe UI", 11, "bold")).pack()
        tk.Label(logo_frame, text="Management System", bg=COLORS["sidebar_bg"],
                 fg=COLORS["text_muted"], font=FONTS["small"]).pack()

        # Separator
        tk.Frame(sb, bg=COLORS["border"], height=1).pack(fill="x", padx=16, pady=(0, 10))

        # Nav items
        self._nav_items = [
            ("dashboard",    "🏠", "Dashboard"),
            ("new_order",    "➕", "New Order"),
            ("search",       "🔍", "Search Orders"),
            ("date_records", "📅", "Date Records"),
            ("progress",     "📊", "Progress"),
            ("all_orders",   "📋", "All Orders"),
            ("price_list",   "💰", "Price List"),
        ]
        self._nav_btns = {}
        self._current = None

        for key, icon, label in self._nav_items:
            self._make_nav_btn(key, icon, label)

        # Bottom clock
        tk.Frame(sb, bg=COLORS["border"], height=1).pack(
            side="bottom", fill="x", padx=16, pady=(0, 8)
        )
        self._clock = tk.Label(sb, bg=COLORS["sidebar_bg"],
                               fg=COLORS["text_muted"], font=FONTS["small"])
        self._clock.pack(side="bottom", pady=(0, 12))
        self._tick()

    def _make_nav_btn(self, key, icon, label):
        outer = tk.Frame(self.sidebar, bg=COLORS["sidebar_bg"], cursor="hand2")
        outer.pack(fill="x", padx=8, pady=2)

        inner = tk.Frame(outer, bg=COLORS["sidebar_bg"], padx=12, pady=10)
        inner.pack(fill="x")

        icon_lbl = tk.Label(inner, text=icon, bg=COLORS["sidebar_bg"],
                             fg=COLORS["text_dim"], font=("Segoe UI", 14))
        icon_lbl.pack(side="left", padx=(0, 10))

        text_lbl = tk.Label(inner, text=label, bg=COLORS["sidebar_bg"],
                             fg=COLORS["text_dim"], font=("Segoe UI", 10))
        text_lbl.pack(side="left")

        all_w = [outer, inner, icon_lbl, text_lbl]

        def on_click(e, k=key):
            self.show_frame(k)

        def on_enter(e, k=key):
            if self._current != k:
                for w in all_w:
                    w.config(bg=COLORS["sidebar_active"])

        def on_leave(e, k=key):
            if self._current != k:
                for w in all_w:
                    w.config(bg=COLORS["sidebar_bg"])

        for w in all_w:
            w.bind("<Button-1>", on_click)
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

        self._nav_btns[key] = {"outer": outer, "inner": inner,
                                "icon": icon_lbl, "text": text_lbl}

    def _activate_nav(self, key):
        for k, widgets in self._nav_btns.items():
            if k == key:
                bg = COLORS["sidebar_active"]
                fg_icon = COLORS["accent"]
                fg_text = COLORS["text"]
            else:
                bg = COLORS["sidebar_bg"]
                fg_icon = COLORS["text_dim"]
                fg_text = COLORS["text_dim"]
            for w in widgets.values():
                w.config(bg=bg)
            widgets["icon"].config(fg=fg_icon)
            widgets["text"].config(fg=fg_text)

    def _tick(self):
        self._clock.config(
            text=datetime.now().strftime("📅 %d-%m-%Y  🕐 %H:%M:%S"),
            fg=COLORS["text_muted"],
        )
        self.root.after(1000, self._tick)

    # ── Frame management ──────────────────────────────────────────────────────

    def _create_frames(self):
        from ui.dashboard     import DashboardFrame
        from ui.new_order     import NewOrderFrame
        from ui.search_orders import SearchOrdersFrame
        from ui.date_records  import DateRecordsFrame
        from ui.progress      import ProgressFrame
        from ui.all_orders    import AllOrdersFrame
        from ui.price_list    import PriceListFrame

        self.frames = {
            "dashboard":    DashboardFrame(self.content, self),
            "new_order":    NewOrderFrame(self.content, self),
            "search":       SearchOrdersFrame(self.content, self),
            "date_records": DateRecordsFrame(self.content, self),
            "progress":     ProgressFrame(self.content, self),
            "all_orders":   AllOrdersFrame(self.content, self),
            "price_list":   PriceListFrame(self.content, self),
        }

    def show_frame(self, name: str):
        if self._current and self._current in self.frames:
            self.frames[self._current].pack_forget()
        self.frames[name].pack(fill="both", expand=True)
        self._current = name
        self._activate_nav(name)
        frame = self.frames[name]
        if hasattr(frame, "refresh"):
            frame.refresh()
