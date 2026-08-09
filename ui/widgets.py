"""
ui/widgets.py — Shared reusable widget helpers for Victory Laundry UI
"""
import tkinter as tk
from tkinter import ttk
from ui.theme import COLORS, FONTS


# ── Button factory ─────────────────────────────────────────────────────────────

def make_btn(parent, text, command, style="primary", width=None, **kw):
    """
    Create a flat-styled tk.Button.
    style: 'primary' | 'success' | 'danger' | 'edit' | 'neutral' | 'warning'
    All buttons: off-white bg, colored border, colored text.
    Hover: inverts to colored bg + white text (pop effect).
    """
    cfg = {
        "primary": (COLORS["btn_primary"],  COLORS["btn_primary_fg"],  COLORS["btn_primary_border"]),
        "success": (COLORS["btn_success"],  COLORS["btn_success_fg"],  COLORS["btn_success_border"]),
        "danger":  (COLORS["btn_danger"],   COLORS["btn_danger_fg"],   COLORS["btn_danger_border"]),
        "edit":    (COLORS["btn_edit"],     COLORS["btn_edit_fg"],     COLORS["btn_edit_border"]),
        "neutral": (COLORS["btn_neutral"],  COLORS["btn_neutral_fg"],  COLORS["btn_neutral_border"]),
        "warning": (COLORS["btn_neutral"],  COLORS["warning_fg"],      COLORS["warning_fg"]),
    }
    bg, fg, border = cfg.get(style, cfg["neutral"])
    kw.setdefault("font", FONTS["bold"])
    kw.setdefault("padx", 14)
    kw.setdefault("pady", 7)

    btn = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg,
        activebackground=border, activeforeground=bg,
        relief="flat", bd=0, cursor="hand2",
        highlightthickness=2,
        highlightbackground=border,
        highlightcolor=border,
        **kw
    )
    if width:
        btn.config(width=width)

    # Hover: for orange buttons, darken; for dark-card buttons, lighten slightly
    def _enter(e):
        if bg == COLORS["btn_primary"]:  # Orange bg — darken on hover
            btn.config(bg=COLORS["accent_dark"], fg="#FFFFFF")
        else:  # Dark card btn — show colored bg on hover
            btn.config(bg=border, fg="#000000" if border == COLORS["btn_neutral_border"] else "#FFFFFF")
    def _leave(e):
        btn.config(bg=bg, fg=fg)

    btn.bind("<Enter>", _enter)
    btn.bind("<Leave>", _leave)
    return btn


def _tint(hex_color: str, amount: int) -> str:
    """Lighten a hex color by `amount`."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    r, g, b = min(255, r+amount), min(255, g+amount), min(255, b+amount)
    return f"#{r:02x}{g:02x}{b:02x}"


# ── Entry / Label helpers ──────────────────────────────────────────────────────

def make_entry(parent, textvariable=None, width=20, **kw):
    kw.setdefault("font", FONTS["default"])
    e = tk.Entry(
        parent,
        textvariable=textvariable,
        width=width,
        bg=COLORS["input_bg"],
        fg=COLORS["input_fg"],
        insertbackground=COLORS["text"],
        relief="flat",
        highlightthickness=1,
        highlightbackground=COLORS["border2"],
        highlightcolor=COLORS["accent"],
        **kw
    )
    return e


def make_label(parent, text="", style="default", **kw):
    font_map = {
        "default":  FONTS["default"],
        "bold":     FONTS["bold"],
        "title":    FONTS["title"],
        "large":    FONTS["large"],
        "small":    FONTS["small"],
        "dim":      FONTS["small"],
        "header":   FONTS["header"],
    }
    fg_map = {
        "default": COLORS["text"],
        "bold":    COLORS["text"],
        "title":   COLORS["accent"],
        "large":   COLORS["text"],
        "small":   COLORS["text"],
        "dim":     COLORS["text_dim"],
        "header":  COLORS["accent"],
    }
    kw.setdefault("bg", COLORS["card_bg"])
    return tk.Label(
        parent, text=text,
        font=font_map.get(style, FONTS["default"]),
        fg=fg_map.get(style, COLORS["text"]),
        **kw
    )


# ── Section header bar ─────────────────────────────────────────────────────────

def section_header(parent, title, bg=None):
    bg = bg or COLORS["card_bg"]
    bar = tk.Frame(parent, bg=bg)
    bar.pack(fill="x", pady=(0, 10))

    tk.Label(bar, text=title, bg=bg, fg=COLORS["text"],
             font=FONTS["title"]).pack(side="left", padx=20, pady=12)

    tk.Frame(bar, bg=COLORS["border"], height=1).pack(
        side="bottom", fill="x", padx=20
    )
    return bar


# ── Card frame ─────────────────────────────────────────────────────────────────

def card(parent, padx=16, pady=12, bg=None, **kw):
    bg = bg or COLORS["card_bg"]
    f = tk.Frame(parent, bg=bg, padx=padx, pady=pady, **kw)
    return f


# ── Scrollable frame ──────────────────────────────────────────────────────────

class ScrollableFrame(tk.Frame):
    """A tk.Frame with vertical scrollbar."""

    def __init__(self, parent, bg=None, **kw):
        bg = bg or COLORS["bg"]
        super().__init__(parent, bg=bg, **kw)

        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.vscroll = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.inner = tk.Frame(self.canvas, bg=bg)

        self.canvas.configure(yscrollcommand=self.vscroll.set)
        self.vscroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self._win = self.canvas.create_window(
            (0, 0), window=self.inner, anchor="nw"
        )
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all(
            "<MouseWheel>", self._on_mousewheel
        ))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _on_inner_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._win, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# ── Treeview builder ──────────────────────────────────────────────────────────

def build_tree(parent, columns, headings, col_widths, height=15, show_scrollbar=True):
    """
    Create a styled ttk.Treeview with optional scrollbar.
    Returns (frame, tree).
    """
    frame = tk.Frame(parent, bg=COLORS["bg"])

    tree = ttk.Treeview(frame, columns=columns, show="headings",
                        height=height, selectmode="browse")
    # Row alternating — pitch black / almost-black for subtle depth
    tree.tag_configure("odd",  background=COLORS["table_row"],  foreground=COLORS["text_dim"])
    tree.tag_configure("even", background=COLORS["table_alt"],  foreground=COLORS["text_dim"])

    for col, heading, width in zip(columns, headings, col_widths):
        tree.heading(col, text=heading, anchor="w")
        tree.column(col, width=width, minwidth=40, anchor="w")

    if show_scrollbar:
        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

    tree.pack(side="left", fill="both", expand=True)
    return frame, tree


def populate_tree(tree, rows, columns):
    """Clear and re-populate a Treeview."""
    tree.delete(*tree.get_children())
    for i, row in enumerate(rows):
        tag = "even" if i % 2 == 0 else "odd"
        values = [row.get(c, "") for c in columns]
        tree.insert("", "end", iid=str(row.get(columns[0], i)),
                    values=values, tags=(tag,))


# ── Tooltip ───────────────────────────────────────────────────────────────────

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self._tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self._tip = tk.Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self._tip, text=self.text, bg="#ffffe0", fg="#333",
                 font=FONTS["small"], relief="solid", bd=1).pack()

    def hide(self, event=None):
        if self._tip:
            self._tip.destroy()
            self._tip = None
