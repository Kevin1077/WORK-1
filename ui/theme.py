"""
ui/theme.py — Color palette, fonts, and style constants for Victory Laundry
iOS Calculator-inspired dark theme.
"""

COLORS = {
    # ── Backgrounds ──────────────────────────────────────────────────────────
    "bg":              "#000000",   # Pitch Black — main window background
    "sidebar_bg":      "#1C1C1E",   # Very Dark Grey — sidebar
    "sidebar_active":  "#FF9500",   # Vibrant Orange — active nav item highlight
    "card_bg":         "#333333",   # Dark Grey — stat cards, header bar
    "card_bg2":        "#2C2C2E",   # Slightly lighter dark — menus/popovers

    # ── Accent ───────────────────────────────────────────────────────────────
    "accent":          "#FF9500",   # Vibrant Orange — primary accent
    "accent_dark":     "#E08800",   # Darker orange for pressed states
    "accent_light":    "#FFB347",   # Lighter orange tint

    # ── Text ─────────────────────────────────────────────────────────────────
    "text":            "#FFFFFF",   # Pure White — primary text
    "text_dim":        "#A6A6A6",   # Light Grey — secondary / subtitle text
    "text_muted":      "#636366",   # Muted grey — clock, minor labels

    # ── Status colours (dark-mode vivid variants) ─────────────────────────
    "success":         "#32D74B",   # Neon Green — Ready / Delivered
    "success_fg":      "#32D74B",
    "danger":          "#FF453A",   # Bright Red — Cancelled / errors
    "danger_fg":       "#FF453A",
    "warning":         "#FFD60A",   # Bright Yellow — In Progress
    "warning_fg":      "#FFD60A",
    "info_fg":         "#0A84FF",   # Bright Blue — Received

    # ── Borders & inputs ─────────────────────────────────────────────────────
    "border":          "#1C1C1E",   # Very Dark Grey — dividers
    "border2":         "#3A3A3C",   # Slightly lighter — input outlines
    "input_bg":        "#2C2C2E",   # Dark input background
    "input_fg":        "#FFFFFF",   # White input text

    # ── Table / Treeview ─────────────────────────────────────────────────────
    "table_header":    "#333333",   # Dark Grey header row
    "table_row":       "#000000",   # Pitch Black rows
    "table_alt":       "#0A0A0A",   # Almost-black alternating rows
    "table_sel_bg":    "#FF9500",   # Orange selected row
    "table_sel_fg":    "#FFFFFF",   # White text on selected row

    # ── Buttons ──────────────────────────────────────────────────────────────
    # Primary → Orange bg, white text (New Order)
    "btn_primary":        "#FF9500",
    "btn_primary_fg":     "#FFFFFF",
    "btn_primary_border": "#FF9500",
    # Success → dark card bg, neon-green text
    "btn_success":        "#333333",
    "btn_success_fg":     "#32D74B",
    "btn_success_border": "#32D74B",
    # Danger → dark card bg, bright-red text
    "btn_danger":         "#333333",
    "btn_danger_fg":      "#FF453A",
    "btn_danger_border":  "#FF453A",
    # Neutral → dark card bg, white text (Search, Date Records, Refresh)
    "btn_neutral":        "#333333",
    "btn_neutral_fg":     "#FFFFFF",
    "btn_neutral_border": "#3A3A3C",
    # Edit → dark card bg, bright-blue text
    "btn_edit":           "#333333",
    "btn_edit_fg":        "#0A84FF",
    "btn_edit_border":    "#0A84FF",
}

FONTS = {
    "default":   ("Segoe UI", 10),
    "bold":      ("Segoe UI", 10, "bold"),
    "small":     ("Segoe UI", 9),
    "small_bold":("Segoe UI", 9, "bold"),
    "large":     ("Segoe UI", 13, "bold"),
    "xlarge":    ("Segoe UI", 20, "bold"),
    "xxlarge":   ("Segoe UI", 28, "bold"),
    "title":     ("Segoe UI", 16, "bold"),
    "subtitle":  ("Segoe UI", 12),
    "mono":      ("Consolas", 10),
    "header":    ("Segoe UI", 11, "bold"),
}

STATUS_COLORS = {
    "Received":    "#0A84FF",   # Bright Blue
    "In Progress": "#FFD60A",   # Bright Yellow
    "Ready":       "#32D74B",   # Neon Green
    "Delivered":   "#32D74B",   # Neon Green (same as Ready)
    "Cancelled":   "#FF453A",   # Bright Red
}

STATUS_LIST = ["Received", "In Progress", "Ready", "Delivered", "Cancelled"]

SHOP_NAME = "Victory Laundry"
SHOP_TAGLINE = "Professional Laundry Services"
SHOP_PHONE = ""   # fill in shop contact if needed

