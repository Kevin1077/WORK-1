"""
ui/app_window.py — Main application window with sidebar navigation
Branded with Étoffe Laundry Studio logo and warm off-white palette.
"""
import os
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from PIL import Image, ImageTk

from ui.theme import COLORS, FONTS, SHOP_NAME, SHOP_TAGLINE

from ui.dashboard import DashboardFrame
from ui.new_order import NewOrderFrame
from ui.search_orders import SearchOrdersFrame
from ui.date_records import DateRecordsFrame
from ui.progress import ProgressFrame
from ui.all_orders import AllOrdersFrame
from ui.customers import CustomersFrame
from ui.price_list import PriceListFrame
from ui.print_settings import PrintSettingsFrame


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
        self.root.title("Étoffe Laundry — Management System")
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

        # Treeview — clean white / cream rows, charcoal text, gold selection
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
            foreground=COLORS["table_header_fg"],
            font=FONTS["bold"],
            relief="flat",
            borderwidth=1,
        )
        style.map("Treeview",
            background=[("selected", COLORS["table_sel_bg"])],
            foreground=[("selected", COLORS["table_sel_fg"])],
        )
        style.map("Treeview.Heading",
            background=[("active", COLORS["border"])],
            foreground=[("active", COLORS["text"])],
        )

        # Scrollbar — off-white themed
        style.configure("Vertical.TScrollbar",
            background=COLORS["border"],
            troughcolor=COLORS["bg"],
            arrowcolor=COLORS["text_dim"],
            borderwidth=0,
        )
        style.configure("Horizontal.TScrollbar",
            background=COLORS["border"],
            troughcolor=COLORS["bg"],
            borderwidth=0,
        )

        # Combobox — off-white themed
        style.configure("TCombobox",
            fieldbackground=COLORS["input_bg"],
            background=COLORS["input_bg"],
            foreground=COLORS["text"],
            arrowcolor=COLORS["text_dim"],
            bordercolor=COLORS["border"],
            lightcolor=COLORS["border"],
            darkcolor=COLORS["border"],
        )
        style.map("TCombobox",
            fieldbackground=[("readonly", COLORS["input_bg"])],
            foreground=[("readonly", COLORS["text"])],
        )

        # Notebook
        style.configure("TNotebook", background=COLORS["bg"])
        style.configure("TNotebook.Tab",
            background=COLORS["card_bg2"],
            foreground=COLORS["text_dim"],
            padding=[12, 6],
        )
        style.map("TNotebook.Tab",
            background=[("selected", COLORS["card_bg"])],
            foreground=[("selected", COLORS["accent"])],
        )

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_layout(self):
        # Gold accent bar at very top
        top_bar = tk.Frame(self.root, bg=COLORS["accent"], height=3)
        top_bar.pack(side="top", fill="x")

        main = tk.Frame(self.root, bg=COLORS["bg"])
        main.pack(fill="both", expand=True)

        # Sidebar (warm cream)
        self.sidebar = tk.Frame(main, bg=COLORS["sidebar_bg"], width=230)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # 1px warm gray separator between sidebar and content
        tk.Frame(main, bg=COLORS["border"], width=1).pack(side="left", fill="y")

        # Content area
        self.content = tk.Frame(main, bg=COLORS["bg"])
        self.content.pack(side="left", fill="both", expand=True)

    def _build_sidebar(self):
        sb = self.sidebar

        # Logo block
        logo_frame = tk.Frame(sb, bg=COLORS["sidebar_bg"])
        logo_frame.pack(fill="x", pady=(18, 16), padx=16)

        self._logo_photo = None
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logo_candidates = [
            os.path.join(base_dir, "assets", "etoffe_logo_color_transparent.png"),
            os.path.join("assets", "etoffe_logo_color_transparent.png"),
            os.path.abspath("assets/etoffe_logo_color_transparent.png"),
        ]
        for cand in logo_candidates:
            if cand and os.path.exists(cand):
                try:
                    src_img = Image.open(cand).convert("RGBA")
                    data = src_img.getdata()
                    new_data = []
                    has_opaque_white = False
                    for item in data:
                        if item[0] > 235 and item[1] > 235 and item[2] > 235:
                            new_data.append((255, 255, 255, 0))
                            has_opaque_white = True
                        else:
                            new_data.append(item)
                    if has_opaque_white:
                        src_img.putdata(new_data)
                    bbox = src_img.getbbox()
                    if bbox:
                        src_img = src_img.crop(bbox)

                    target_w = 170
                    ratio = target_w / src_img.width
                    target_h = int(src_img.height * ratio)
                    max_h = 100
                    if target_h > max_h:
                        ratio = max_h / src_img.height
                        target_h = max_h
                        target_w = int(src_img.width * ratio)

                    resized = src_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    # Composite smoothly onto sidebar background color
                    sb_hex = COLORS["sidebar_bg"].lstrip("#")
                    bg_rgb = tuple(int(sb_hex[i:i+2], 16) for i in (0, 2, 4))
                    canvas = Image.new("RGB", (target_w, target_h), bg_rgb)
                    canvas.paste(resized, (0, 0), mask=resized.split()[3])
                    self._logo_photo = ImageTk.PhotoImage(canvas)
                    break
                except Exception:
                    pass

        if self._logo_photo:
            tk.Label(logo_frame, image=self._logo_photo, bg=COLORS["sidebar_bg"]).pack(pady=(0, 6))
        else:
            tk.Label(logo_frame, text="✦", bg=COLORS["sidebar_bg"],
                     fg=COLORS["accent"], font=("Segoe UI", 24, "bold")).pack()
            tk.Label(logo_frame, text="ÉTOFFE LAUNDRY", bg=COLORS["sidebar_bg"],
                     fg=COLORS["text"], font=("Segoe UI", 11, "bold")).pack()

        tk.Label(logo_frame, text=SHOP_TAGLINE, bg=COLORS["sidebar_bg"],
                 fg=COLORS["text_dim"], font=FONTS["small"]).pack()

        # Separator
        tk.Frame(sb, bg=COLORS["border"], height=1).pack(fill="x", padx=16, pady=(0, 10))

        # Nav items
        self._nav_items = [
            ("dashboard",      "🏠", "Dashboard"),
            ("new_order",      "➕", "New Order"),
            ("search",         "🔍", "Search Orders"),
            ("date_records",   "📅", "Date Records"),
            ("progress",       "📊", "Progress"),
            ("all_orders",     "📋", "All Orders"),
            ("customers",      "👥", "Customers"),
            ("price_list",     "💰", "Price List"),
            ("print_settings", "⚙️", "Print Settings"),
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
                             fg=COLORS["text_dim"], font=("Segoe UI", 13))
        icon_lbl.pack(side="left", padx=(0, 10))

        text_lbl = tk.Label(inner, text=label, bg=COLORS["sidebar_bg"],
                             fg=COLORS["text_dim"], font=("Segoe UI", 10))
        text_lbl.pack(side="left")

        all_w = [outer, inner, icon_lbl, text_lbl]

        def on_click(e, k=key):
            self.show_frame(k)

        def on_enter(e, k=key):
            if self._current != k:
                hover_bg = COLORS["sidebar_hover"]
                for w in [inner, icon_lbl, text_lbl]:
                    w.config(bg=hover_bg)

        def on_leave(e, k=key):
            if self._current != k:
                for w in [inner, icon_lbl, text_lbl]:
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
                # Active: gold highlight with dark charcoal text
                inner_bg   = COLORS["sidebar_active"]
                icon_fg    = COLORS["btn_primary_fg"]
                text_fg    = COLORS["btn_primary_fg"]
                outer_bg   = COLORS["sidebar_bg"]
            else:
                inner_bg   = COLORS["sidebar_bg"]
                icon_fg    = COLORS["text_dim"]
                text_fg    = COLORS["text_dim"]
                outer_bg   = COLORS["sidebar_bg"]

            widgets["outer"].config(bg=outer_bg)
            widgets["inner"].config(bg=inner_bg)
            widgets["icon"].config(bg=inner_bg, fg=icon_fg)
            widgets["text"].config(bg=inner_bg, fg=text_fg)

    def _tick(self):
        self._clock.config(
            text=datetime.now().strftime("%d-%m-%Y   %H:%M:%S"),
            fg=COLORS["text_muted"],
        )
        self.root.after(1000, self._tick)

    # ── Frame management ──────────────────────────────────────────────────────

    def _create_frames(self):
        self.frames = {}
        self._frame_factories = {
            "dashboard":      lambda: DashboardFrame(self.content, self),
            "new_order":      lambda: NewOrderFrame(self.content, self),
            "search":         lambda: SearchOrdersFrame(self.content, self),
            "date_records":   lambda: DateRecordsFrame(self.content, self),
            "progress":       lambda: ProgressFrame(self.content, self),
            "all_orders":     lambda: AllOrdersFrame(self.content, self),
            "customers":      lambda: CustomersFrame(self.content, self),
            "price_list":     lambda: PriceListFrame(self.content, self),
            "print_settings": lambda: PrintSettingsFrame(self.content, self),        
        }

    def show_frame(self, name: str):
        if self._current and self._current in self.frames:
            self.frames[self._current].pack_forget()

        if name not in self.frames and name in self._frame_factories:
            self.frames[name] = self._frame_factories[name]()

        if name in self.frames:
            self.frames[name].pack(fill="both", expand=True)
            self._current = name
            self._activate_nav(name)
            frame = self.frames[name]
            if hasattr(frame, "refresh"):
                frame.refresh()
