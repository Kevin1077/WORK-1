"""
ui/theme.py — Color palette, fonts, and style constants for Victory Laundry
"""

COLORS = {
    # Backgrounds
    "bg":              "#FAF9F6",
    "sidebar_bg":      "#F0EFE9",
    "sidebar_active":  "#D9D8D2",
    "card_bg":         "#ECEAE4",
    "card_bg2":        "#E8E7E1",

    # Accent (off-white on dark, dark on light)
    "accent":          "#080707",
    "accent_dark":     "#1a1a1a",
    "accent_light":    "#333333",

    # Text
    "text":            "#080707",
    "text_dim":        "#444444",
    "text_muted":      "#666666",

    # Status
    "success":         "#238636",
    "success_fg":      "#1a7a30",
    "danger":          "#da3633",
    "danger_fg":       "#c0392b",
    "warning":         "#9e6a03",
    "warning_fg":      "#b8860b",
    "info_fg":         "#1565c0",

    # Borders & inputs
    "border":          "#CCCCCC",
    "border2":         "#BBBBBB",
    "input_bg":        "#FFFFFF",
    "input_fg":        "#080707",

    # Table / Treeview
    "table_header":    "#F0EFE9",
    "table_row":       "#FAF9F6",
    "table_alt":       "#F5F4F0",
    "table_sel_bg":    "#080707",
    "table_sel_fg":    "#FAF9F6",

    # Buttons
    "btn_primary":     "#FAF9F6",
    "btn_primary_fg":  "#080707",
    "btn_primary_border": "#080707",
    "btn_success":     "#FAF9F6",
    "btn_success_fg":  "#1a7a30",
    "btn_success_border": "#1a7a30",
    "btn_danger":      "#FAF9F6",
    "btn_danger_fg":   "#c0392b",
    "btn_danger_border": "#c0392b",
    "btn_neutral":     "#FAF9F6",
    "btn_neutral_fg":  "#080707",
    "btn_neutral_border": "#080707",
    "btn_edit":        "#FAF9F6",
    "btn_edit_fg":     "#1565c0",
    "btn_edit_border": "#1565c0",
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
    "Received":    "#1565c0",
    "In Progress": "#b8860b",
    "Ready":       "#1a7a30",
    "Delivered":   "#666666",
    "Cancelled":   "#c0392b",
}

STATUS_LIST = ["Received", "In Progress", "Ready", "Delivered", "Cancelled"]

SHOP_NAME = "Victory Laundry"
SHOP_TAGLINE = "Professional Laundry Services"
SHOP_PHONE = ""   # fill in shop contact if needed
