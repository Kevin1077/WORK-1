"""
ui/theme.py — Color palette, fonts, and style constants for Étoffe Laundry
Refined, elegant Off-White, Warm Cream, Gold, and Charcoal theme.
"""

COLORS = {
    # ── Backgrounds ──────────────────────────────────────────────────────────
    "bg":              "#F7F4EE",   # Off-white / Warm Cream — main window background
    "sidebar_bg":      "#EFEAE1",   # Warm Cream — sidebar background
    "sidebar_active":  "#C9A84E",   # Étoffe Gold — active nav item highlight
    "sidebar_hover":   "#E5DFD5",   # Subtle cream hover for sidebar items
    "card_bg":         "#FFFFFF",   # Pure White — main card background
    "card_bg2":        "#F2EEE7",   # Warm Cream — secondary card / popup background
    "header_bg":       "#FFFFFF",   # Crisp White — top header bar background

    # ── Accent ───────────────────────────────────────────────────────────────
    "accent":          "#C9A84E",   # Primary Étoffe Gold accent
    "accent_dark":     "#A88732",   # Darker Gold for hover / pressed states
    "accent_light":    "#E5D39A",   # Lighter Gold tint

    # ── Text ─────────────────────────────────────────────────────────────────
    "text":            "#242424",   # Deep Charcoal — primary text
    "text_dim":        "#6F6A62",   # Warm Charcoal — secondary / subtitle text
    "text_muted":      "#969087",   # Muted taupe — clock, minor labels

    # ── Status colours (premium softened variants) ───────────────────────────
    "success":         "#3F8F5B",   # Forest Green — Ready / Delivered
    "success_fg":      "#3F8F5B",
    "danger":          "#C94B4B",   # Soft Crimson — Cancelled / errors
    "danger_fg":       "#C94B4B",
    "warning":         "#C9972E",   # Warm Amber — In Progress
    "warning_fg":      "#C9972E",
    "info_fg":         "#4A78A8",   # Steel Blue — Received

    # ── Borders & inputs ─────────────────────────────────────────────────────
    "border":          "#D9D2C7",   # Warm gray — dividers and cards
    "border2":         "#E5DFD5",   # Secondary border — inputs
    "input_bg":        "#FFFFFF",   # White input background
    "input_fg":        "#242424",   # Deep Charcoal input text

    # ── Table / Treeview ─────────────────────────────────────────────────────
    "table_header":    "#E8E1D6",   # Warm cream header row
    "table_header_fg": "#242424",   # Charcoal header text
    "table_row":       "#FFFFFF",   # Clean White rows
    "table_alt":       "#FAF8F4",   # Very light warm cream alternating rows
    "table_sel_bg":    "#D8C27A",   # Soft Gold selected row
    "table_sel_fg":    "#242424",   # Charcoal text on selected row

    # ── Buttons ──────────────────────────────────────────────────────────────
    # Primary → Gold bg, charcoal text (New Order, Save, etc.)
    "btn_primary":        "#C9A84E",
    "btn_primary_fg":     "#242424",
    "btn_primary_border": "#C9A84E",
    # Success → White bg, green text/border
    "btn_success":        "#FFFFFF",
    "btn_success_fg":     "#3F8F5B",
    "btn_success_border": "#3F8F5B",
    # Danger → White bg, red text/border
    "btn_danger":         "#FFFFFF",
    "btn_danger_fg":      "#C94B4B",
    "btn_danger_border":  "#C94B4B",
    # Neutral → White bg, charcoal text, warm-gray border (Search, Date Records, Refresh)
    "btn_neutral":        "#FFFFFF",
    "btn_neutral_fg":     "#242424",
    "btn_neutral_border": "#D9D2C7",
    # Edit / Info → White bg, blue text/border
    "btn_edit":           "#FFFFFF",
    "btn_edit_fg":        "#4A78A8",
    "btn_edit_border":    "#4A78A8",
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
    "Received":    "#4A78A8",   # Steel Blue
    "In Progress": "#C9972E",   # Warm Amber
    "Ready":       "#3F8F5B",   # Forest Green
    "Delivered":   "#3F8F5B",   # Forest Green (same as Ready)
    "Cancelled":   "#C94B4B",   # Soft Crimson
}

STATUS_LIST = ["Received", "In Progress", "Ready", "Delivered", "Cancelled"]

SHOP_NAME = "ÉTOFFE LAUNDRY"
SHOP_TAGLINE = "Management System"
SHOP_FULL_TITLE = "ÉTOFFE LAUNDRY MANAGEMENT SYSTEM"
SHOP_PHONE = ""
