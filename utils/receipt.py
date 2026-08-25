"""
utils/receipt.py — PNG image receipt generator for Victory Laundry
Uses Pillow (PIL) to create a clean, receipt-style PNG image.
Black and white only — no colours.
"""
import os
import tempfile
import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# --- Phase 0: Persistent file-based debug logging ---
_LOG_PATH = os.path.join(tempfile.gettempdir(), "victory_print_debug.log")
_logger = logging.getLogger("victory_print")
if not _logger.handlers:
    _handler = logging.FileHandler(_LOG_PATH, encoding="utf-8")
    _handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"
    ))
    _logger.addHandler(_handler)
    _logger.setLevel(logging.DEBUG)

_logger.info("=" * 60)
_logger.info("receipt.py module loaded from: %s", os.path.abspath(__file__))
try:
    _logger.info("File last modified: %s", os.path.getmtime(__file__))
except Exception:
    pass

SHOP_NAME = "Victory Laundry"
SHOP_TAGLINE = "Professional Laundry Services"


def _get_font(size: int, bold: bool = False, italic: bool = False) -> ImageFont.ImageFont:
    """Return TrueType font if available, falling back to PIL default font."""
    font_names = []
    if bold and italic:
        font_names = ["arialbi.ttf", "calibriz.ttf", "DejaVuSans-BoldOblique.ttf"]
    elif bold:
        font_names = ["arialbd.ttf", "calibrib.ttf", "DejaVuSans-Bold.ttf"]
    elif italic:
        font_names = ["ariali.ttf", "calibrii.ttf", "DejaVuSans-Oblique.ttf"]
    else:
        font_names = ["arial.ttf", "calibri.ttf", "DejaVuSans.ttf"]

    for fn in font_names:
        try:
            return ImageFont.truetype(fn, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


def _get_text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    """Calculate text width in pixels."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _build_receipt_image(order_data: dict) -> Image.Image:
    """Build and return a PIL Image object of the receipt (RGB mode, B&W design)."""
    # Canvas config based on paper size setting
    try:
        import database as db
        psize = db.get_setting("receipt_paper_size", "80mm")
    except Exception:
        psize = "80mm"

    if psize == "58mm":
        img_width = 384
        margin = 20
    elif psize == "A4":
        img_width = 800
        margin = 45
    elif psize == "A5":
        img_width = 600
        margin = 35
    else:
        # 80mm Thermal (Standard POS)
        img_width = 576
        margin = 30

    content_width = img_width - (2 * margin)
    bg_color = (255, 255, 255)
    fg_color = (0, 0, 0)

    # Fonts
    font_title = _get_font(24, bold=True)
    font_tagline = _get_font(12, italic=True)
    font_section = _get_font(14, bold=True)
    font_normal = _get_font(12)
    font_bold = _get_font(12, bold=True)
    font_footer = _get_font(12, italic=True)

    # 1st Pass: Calculate height dynamically
    dummy_img = Image.new("RGB", (img_width, 100), bg_color)
    draw = ImageDraw.Draw(dummy_img)

    y = 35
    # Header
    y += 28 + 6  # Title
    y += 18 + 12 # Tagline
    y += 3 + 12  # Thick HR

    # Order Details
    y += 20 + 6  # Section header
    y += 18 * 3  # 3 detail lines
    y += 10 + 1 + 10 # HR

    # Customer Details
    y += 20 + 6  # Section header
    cust_lines = 2
    if order_data.get("place"):
        cust_lines += 1
    if order_data.get("address"):
        cust_lines += 1
    y += 18 * cust_lines
    y += 10 + 1 + 10 # HR

    # Order Items
    y += 20 + 6  # Section header
    y += 30      # Table Header row
    items = order_data.get("items", [])
    y += len(items) * 26 # Table Data rows
    y += 30      # Grand Total row
    y += 12

    # Notes
    if order_data.get("notes"):
        y += 1 + 10 # HR
        y += 20     # Notes text
        y += 10

    # Footer
    y += 3 + 12  # Thick HR
    y += 20      # Footer text
    y += 35      # Bottom margin

    total_height = y

    # 2nd Pass: Render actual receipt image
    img = Image.new("RGB", (img_width, total_height), bg_color)
    draw = ImageDraw.Draw(img)

    y = 35

    # ── Header ────────────────────────────────────────────────────────────────
    tw = _get_text_width(draw, SHOP_NAME, font_title)
    draw.text(((img_width - tw) // 2, y), SHOP_NAME, fill=fg_color, font=font_title)
    y += 32

    tw = _get_text_width(draw, SHOP_TAGLINE, font_tagline)
    draw.text(((img_width - tw) // 2, y), SHOP_TAGLINE, fill=fg_color, font=font_tagline)
    y += 24

    # Thick HR
    draw.rectangle([margin, y, margin + content_width, y + 2], fill=fg_color)
    y += 12

    # ── Order Details ─────────────────────────────────────────────────────────
    order_date = order_data.get("order_date", "")
    try:
        from datetime import datetime
        order_date = datetime.strptime(order_date, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        pass

    payment = order_data.get("payment_method", "") or "—"

    draw.text((margin, y), "Order Details", fill=fg_color, font=font_section)
    y += 22

    draw.text((margin, y), f"Order #: {order_data['order_id']}", fill=fg_color, font=font_normal)
    y += 18
    draw.text((margin, y), f"Date   : {order_date}", fill=fg_color, font=font_normal)
    y += 18
    draw.text((margin, y), f"Payment: {payment}", fill=fg_color, font=font_normal)
    y += 24

    # Thin HR
    draw.line([(margin, y), (margin + content_width, y)], fill=fg_color, width=1)
    y += 12

    # ── Customer Details ──────────────────────────────────────────────────────
    draw.text((margin, y), "Customer Details", fill=fg_color, font=font_section)
    y += 22

    draw.text((margin, y), f"Name   : {order_data.get('name','')}", fill=fg_color, font=font_bold)
    y += 18
    draw.text((margin, y), f"Phone  : {order_data.get('phone','')}", fill=fg_color, font=font_bold)
    y += 18
    if order_data.get("place"):
        draw.text((margin, y), f"Place  : {order_data['place']}", fill=fg_color, font=font_bold)
        y += 18
    if order_data.get("address"):
        draw.text((margin, y), f"Address: {order_data['address']}", fill=fg_color, font=font_bold)
        y += 18
    y += 6

    # Thin HR
    draw.line([(margin, y), (margin + content_width, y)], fill=fg_color, width=1)
    y += 12

    # ── Items Table ───────────────────────────────────────────────────────────
    draw.text((margin, y), "Order Items", fill=fg_color, font=font_section)
    y += 24

    # Table columns: S.No (45), Item (225), Qty (60), Rate (100), Total (100)
    col_w = [45, 225, 60, 100, 100]
    col_x = [margin]
    for w in col_w[:-1]:
        col_x.append(col_x[-1] + w)

    # Header Row
    header_h = 28
    draw.rectangle([margin, y, margin + content_width, y + header_h], fill=(0, 0, 0))
    headers = ["S.No", "Item", "Qty", "Rate", "Total"]

    # S.No (centered)
    tw = _get_text_width(draw, headers[0], font_bold)
    draw.text((col_x[0] + (col_w[0] - tw) // 2, y + 6), headers[0], fill=(255, 255, 255), font=font_bold)
    # Item (left)
    draw.text((col_x[1] + 8, y + 6), headers[1], fill=(255, 255, 255), font=font_bold)
    # Qty (centered)
    tw = _get_text_width(draw, headers[2], font_bold)
    draw.text((col_x[2] + (col_w[2] - tw) // 2, y + 6), headers[2], fill=(255, 255, 255), font=font_bold)
    # Rate (right)
    tw = _get_text_width(draw, headers[3], font_bold)
    draw.text((col_x[3] + col_w[3] - tw - 8, y + 6), headers[3], fill=(255, 255, 255), font=font_bold)
    # Total (right)
    tw = _get_text_width(draw, headers[4], font_bold)
    draw.text((col_x[4] + col_w[4] - tw - 8, y + 6), headers[4], fill=(255, 255, 255), font=font_bold)

    y += header_h

    # Data Rows
    row_h = 26
    for i, item in enumerate(items, start=1):
        item_num = str(item.get("item_number", i))
        cloth_type = str(item["cloth_type"])
        qty_str = str(item["quantity"])
        rate_str = f"{item['price_per_unit']:.2f}"
        tot_str = f"{item['subtotal']:.2f}"

        # Draw row outer box / cell borders
        draw.rectangle([margin, y, margin + content_width, y + row_h], outline=(0, 0, 0), width=1)
        for cx in col_x[1:]:
            draw.line([(cx, y), (cx, y + row_h)], fill=(0, 0, 0), width=1)

        # Draw cell text
        tw = _get_text_width(draw, item_num, font_normal)
        draw.text((col_x[0] + (col_w[0] - tw) // 2, y + 4), item_num, fill=fg_color, font=font_normal)

        draw.text((col_x[1] + 8, y + 4), cloth_type, fill=fg_color, font=font_normal)

        tw = _get_text_width(draw, qty_str, font_normal)
        draw.text((col_x[2] + (col_w[2] - tw) // 2, y + 4), qty_str, fill=fg_color, font=font_normal)

        tw = _get_text_width(draw, rate_str, font_normal)
        draw.text((col_x[3] + col_w[3] - tw - 8, y + 4), rate_str, fill=fg_color, font=font_normal)

        tw = _get_text_width(draw, tot_str, font_normal)
        draw.text((col_x[4] + col_w[4] - tw - 8, y + 4), tot_str, fill=fg_color, font=font_normal)

        y += row_h

    # Grand Total Row
    draw.rectangle([margin, y, margin + content_width, y + header_h], fill=(0, 0, 0))
    label = "GRAND TOTAL"
    total_val = f"{order_data.get('total_amount', 0):.2f}"

    tw = _get_text_width(draw, label, font_bold)
    draw.text((col_x[3] + col_w[3] - tw - 8, y + 6), label, fill=(255, 255, 255), font=font_bold)

    tw = _get_text_width(draw, total_val, font_bold)
    draw.text((col_x[4] + col_w[4] - tw - 8, y + 6), total_val, fill=(255, 255, 255), font=font_bold)

    y += header_h + 12

    # ── Notes ─────────────────────────────────────────────────────────────────
    if order_data.get("notes"):
        draw.line([(margin, y), (margin + content_width, y)], fill=fg_color, width=1)
        y += 10
        draw.text((margin, y), f"Notes: {order_data['notes']}", fill=fg_color, font=font_tagline)
        y += 24

    # ── Footer ────────────────────────────────────────────────────────────────
    draw.rectangle([margin, y, margin + content_width, y + 2], fill=fg_color)
    y += 14

    footer_text = "Thank you for choosing Victory Laundry!"
    tw = _get_text_width(draw, footer_text, font_footer)
    draw.text(((img_width - tw) // 2, y), footer_text, fill=fg_color, font=font_footer)

    return img


def generate_receipt(order_data: dict, output_path: str = None) -> str:
    """
    Generate a PNG image receipt for the given order_data dict.
    Returns the path to the generated PNG image.
    """
    if output_path is None:
        tmp = tempfile.gettempdir()
        output_path = os.path.join(
            tmp, f"victory_receipt_order_{order_data['order_id']}.png"
        )

    img = _build_receipt_image(order_data)
    img.save(output_path, "PNG")
    return output_path


def _draw_dashed_line(draw: ImageDraw.ImageDraw, x0: int, x1: int, y: int, color=(140, 140, 140), dash_len=5, space_len=4, width=1):
    """Draw a subtle horizontal dashed line."""
    cur_x = x0
    while cur_x < x1:
        end_x = min(cur_x + dash_len, x1)
        draw.line([(cur_x, y), (end_x, y)], fill=color, width=width)
        cur_x += dash_len + space_len


def _draw_vector_heart(draw: ImageDraw.ImageDraw, cx: float, cy: float, size: float = 14, outline=(184, 134, 27), fill=None, width: int = 2):
    """Draw a vector heart motif centered at (cx, cy)."""
    import math
    scale = size / 32.0
    points = []
    for deg in range(0, 360, 6):
        t = math.radians(deg)
        x = 16 * (math.sin(t) ** 3)
        y = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
        points.append((cx + x * scale, cy + y * scale))
    draw.polygon(points, fill=fill, outline=outline, width=width)


def _draw_gold_divider_with_heart(draw: ImageDraw.ImageDraw, x0: int, x1: int, y: int, color=(184, 134, 27), size: int = 15):
    """Draw a gold accent horizontal divider with a centered vector heart motif."""
    mid_x = (x0 + x1) // 2
    gap = size + 16
    draw.line([(x0, y), (mid_x - gap // 2, y)], fill=color, width=2)
    draw.line([(mid_x + gap // 2, y), (x1, y)], fill=color, width=2)
    _draw_vector_heart(draw, mid_x, y, size=size, outline=color, fill=None, width=2)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    if not words:
        return [""]
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        if _get_text_width(draw, test_line, font) <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def _build_whatsapp_receipt_image(order_data: dict) -> Image.Image:
    """
    Build and return an A5 (1754x2480 px @ 300 DPI) PIL Image of the WhatsApp receipt.
    Uses the exact same canvas dimensions, margins, font sizes, table structure,
    and footer as generate_dispatch_challan_image, with a digital header (Étoffe logo
    and shop address) in the top 0-673px zone.
    """
    from datetime import datetime

    # A5 size at 300 DPI: 1754 x 2480 pixels
    w, h = 1754, 2480
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Margins & top offset (matching generate_dispatch_challan_image)
    ml = 118          # 10 mm left margin
    mr = 94           # 8 mm right margin
    content_w = w - ml - mr  # 1542 px

    try:
        font_bold   = ImageFont.truetype("arialbd.ttf", 32)
        font_norm   = ImageFont.truetype("arial.ttf", 30)
        font_sm     = ImageFont.truetype("arial.ttf", 26)
        font_hdr    = ImageFont.truetype("arialbd.ttf", 32)
        font_italic = ImageFont.truetype("ariali.ttf", 28)
        font_addr   = ImageFont.truetype("arial.ttf", 39)
    except Exception:
        font_bold   = _get_font(32, bold=True)
        font_norm   = _get_font(30)
        font_sm     = _get_font(26)
        font_hdr    = _get_font(32, bold=True)
        font_italic = _get_font(28, italic=True)
        font_addr   = _get_font(39)

    # ── 1. Digital Header (in top 0–673px zone) ──────────────────────────────
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_candidates = [
        os.path.join(base_dir, "assets", "etoffe_logo_color_transparent.png"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "etoffe_logo_color_transparent.png"),
        os.path.join("assets", "etoffe_logo_color_transparent.png"),
        os.path.abspath("assets/etoffe_logo_color_transparent.png"),
    ]
    logo_img = None
    for cand in logo_candidates:
        if cand and os.path.exists(cand):
            try:
                logo_img = Image.open(cand).convert("RGBA")
                break
            except Exception:
                pass

    header_top = 80
    header_bottom = 600
    header_mid = (header_top + header_bottom) // 2

    # Split header into two equal halves for mirror symmetry
    left_half_mid = ml + (content_w // 4)        # Midpoint of left half
    right_half_mid = ml + 3 * (content_w // 4)    # Midpoint of right half

    target_logo_w = 660
    logo_badge_center_y = header_mid + 185  # fallback if logo image is missing
    if logo_img:
        ratio = target_logo_w / logo_img.width
        target_logo_h = int(logo_img.height * ratio)
        max_logo_h = 490
        if target_logo_h > max_logo_h:
            ratio = max_logo_h / logo_img.height
            target_logo_h = max_logo_h
            target_logo_w = int(logo_img.width * ratio)
        logo_resized = logo_img.resize((target_logo_w, target_logo_h), Image.Resampling.LANCZOS)
        logo_x = left_half_mid - (target_logo_w // 2)
        logo_y = header_mid - (target_logo_h // 2)
        img.paste(logo_resized, (logo_x, logo_y), mask=logo_resized.split()[3])

        # Vertical center of the "DRY CLEAN | LAUNDRY" badge
        # In the original 1024x725 asset, the badge spans rows 619 to 680 (center ~649.5)
        badge_top_orig, badge_bottom_orig = 619, 680
        logo_badge_center_y = logo_y + int(((badge_top_orig + badge_bottom_orig) / 2) * ratio)
    else:
        f_brand = _get_font(42, bold=True)
        draw.text((left_half_mid, header_mid - 25), "ÉTOFFE LAUNDRY", fill=(0, 0, 0), font=f_brand, anchor="mt")

    # Address block: 4 lines, horizontally centered in the right half.
    # The 4th line ("Mob:9846593957") aligns vertically with the "DRY CLEAN | LAUNDRY" badge.
    addr_lines = [
        "Opp.St.Marys Church Lalam(Old)",
        "Bypass Road",
        "PALA",
        "Mob:9846593957",
    ]

    cx_addr = right_half_mid
    addr_lh = 60
    n = len(addr_lines)

    for i, line in enumerate(addr_lines):
        line_center_y = logo_badge_center_y - (n - 1 - i) * addr_lh
        draw.text((cx_addr, line_center_y), line, fill=(0, 0, 0), font=font_addr, anchor="mm")

    # Thin horizontal rule at the bottom of header zone
    draw.line([(ml, 630), (ml + content_w, 630)], fill=(0, 0, 0), width=2)

    # ── 2. Content below 673px (matches generate_dispatch_challan_image) ─────
    y = 673

    def _fmt_date_dots(iso: str) -> str:
        try:
            if " " in str(iso):
                iso = str(iso).split(" ")[0]
            return datetime.strptime(str(iso), "%Y-%m-%d").strftime("%d.%m.%Y")
        except Exception:
            return str(iso) if iso else ""

    def _strip_country_code(phone: str) -> str:
        raw = str(phone or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if raw.startswith(("00", "+0")) and len(digits) > 10:
            digits = digits[2:]
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        return digits if digits else raw

    order_id   = order_data.get("order_id", "")
    cust_name  = order_data.get("name", "")
    cust_phone = _strip_country_code(order_data.get("phone", ""))
    cust_place = (order_data.get("place") or "").strip()
    cust_addr  = (order_data.get("address") or "").strip()
    payment    = (order_data.get("payment_method") or "").strip()
    order_date = _fmt_date_dots(order_data.get("order_date", ""))

    # Header Two Columns
    left_w = int(content_w * 0.62)
    right_x = ml + left_w + 48
    lh = 48  # line height

    # Left Column
    ly = y
    draw.text((ml, ly), "To    :", fill=(0, 0, 0), font=font_bold)
    draw.text((ml + 120, ly), cust_name, fill=(0, 0, 0), font=font_bold)
    ly += lh

    cust_addr_lines = []
    if cust_place:
        cust_addr_lines.append(cust_place)
    if cust_addr:
        for part in cust_addr.replace("\n", ",").split(","):
            part = part.strip()
            if part:
                cust_addr_lines.append(part)

    if cust_addr_lines:
        draw.text((ml + 120, ly), ", " + cust_addr_lines[0], fill=(0, 0, 0), font=font_norm)
        ly += lh
        for frag in cust_addr_lines[1:]:
            draw.text((ml + 140, ly), frag + ",", fill=(0, 0, 0), font=font_norm)
            ly += lh

    draw.text((ml, ly), "Phone :", fill=(0, 0, 0), font=font_bold)
    draw.text((ml + 120, ly), cust_phone, fill=(0, 0, 0), font=font_norm)
    ly += lh

    # Right Column
    ry = y
    draw.text((right_x, ry), "No.   :", fill=(0, 0, 0), font=font_bold)
    draw.text((right_x + 100, ry), f"P{order_id}", fill=(0, 0, 0), font=font_norm)
    ry += lh

    draw.text((right_x, ry), "Date  :", fill=(0, 0, 0), font=font_bold)
    draw.text((right_x + 100, ry), order_date, fill=(0, 0, 0), font=font_norm)
    ry += lh

    draw.text((right_x, ry), "Mode of Payment:", fill=(0, 0, 0), font=font_bold)
    draw.text((right_x + 280, ry), payment, fill=(0, 0, 0), font=font_norm)
    ry += lh

    y = max(ly, ry) + 30

    # Table Column Widths
    cw_part = int(content_w * 0.45)
    cw_bar  = int(content_w * 0.20)
    cw_rem  = int(content_w * 0.20)
    cw_amt  = int(content_w * 0.15)

    col_x = [ml, ml + cw_part, ml + cw_part + cw_bar, ml + cw_part + cw_bar + cw_rem]

    hdr_h = 60
    row_h = 52

    tbl_top = y

    # Header Row Box
    draw.rectangle([ml, y, ml + content_w, y + hdr_h], outline=(0, 0, 0), width=2)
    draw.text((col_x[0] + 15, y + 12), "Particulars", fill=(0, 0, 0), font=font_hdr)
    draw.text((col_x[1] + cw_bar // 2, y + 12), "Barcode", fill=(0, 0, 0), font=font_hdr, anchor="mt")
    draw.text((col_x[2] + cw_rem // 2, y + 12), "Remark", fill=(0, 0, 0), font=font_hdr, anchor="mt")
    draw.text((col_x[3] + cw_amt - 15, y + 12), "Amount", fill=(0, 0, 0), font=font_hdr, anchor="rt")
    y += hdr_h

    # Data Rows
    items = order_data.get("items", [])
    garment_counter = 1
    total_garments = 0

    for item in items:
        cloth_type  = str(item.get("cloth_type", ""))
        qty         = max(1, int(item.get("quantity", 1)))
        rate        = float(item.get("price_per_unit", 0))
        item_notes  = (item.get("item_notes") or "").strip()
        particulars = cloth_type + " DC" if not cloth_type.endswith(" DC") else cloth_type

        for _ in range(qty):
            barcode_str = f"P{order_id}-{garment_counter}"
            text_y = y + 10

            draw.text((col_x[0] + 15, text_y), particulars, fill=(0, 0, 0), font=font_norm)
            draw.text((col_x[1] + cw_bar // 2, text_y), barcode_str, fill=(0, 0, 0), font=font_norm, anchor="mt")
            if item_notes:
                draw.text((col_x[2] + cw_rem // 2, text_y), item_notes, fill=(0, 0, 0), font=font_norm, anchor="mt")
            draw.text((col_x[3] + cw_amt - 15, text_y), f"{rate:.2f}", fill=(0, 0, 0), font=font_norm, anchor="rt")

            y += row_h
            garment_counter += 1

    total_garments = garment_counter - 1

    # Divider line
    draw.line([(ml, y), (ml + content_w, y)], fill=(0, 0, 0), width=2)
    y += 10

    # TOTAL row
    total_h = 60
    total_val = f"{float(order_data.get('total_amount', 0)):.2f}"
    text_y = y + 12

    draw.text((col_x[0] + 15, text_y), "TOTAL", fill=(0, 0, 0), font=font_hdr)
    draw.text((col_x[1] + cw_bar // 2, text_y), str(total_garments), fill=(0, 0, 0), font=font_hdr, anchor="mt")
    draw.text((col_x[3] + cw_amt - 15, text_y), total_val, fill=(0, 0, 0), font=font_hdr, anchor="rt")
    y += total_h

    tbl_bottom = y

    # Outer border + Column dividers
    draw.rectangle([ml, tbl_top, ml + content_w, tbl_bottom], outline=(0, 0, 0), width=3)
    for cx in col_x[1:]:
        draw.line([(cx, tbl_top), (cx, tbl_bottom)], fill=(0, 0, 0), width=2)

    # Footer
    y += 60
    draw.text((ml + content_w, y), "For ÉTOFFE LAUNDRY STUDIO", fill=(0, 0, 0), font=font_bold, anchor="rt")
    y += 45
    draw.text((ml + content_w, y), "Authorised Signatory", fill=(0, 0, 0), font=font_italic, anchor="rt")

    return img


def generate_whatsapp_receipt(order_data: dict, output_path: str = None) -> str:
    """
    Generate an A5 PNG receipt image matching dispatch challan layout with Étoffe digital header
    specifically for WhatsApp sharing.
    Returns the path to the generated PNG image.
    """
    if output_path is None:
        tmp = tempfile.gettempdir()
        output_path = os.path.join(
            tmp, f"etoffe_whatsapp_receipt_order_{order_data['order_id']}.png"
        )

    img = _build_whatsapp_receipt_image(order_data)
    img.save(output_path, "PNG", dpi=(300, 300))
    return output_path


def generate_dispatch_challan_pdf(order_data: dict, output_path: str = None) -> str:
    """
    Generate an A5 PDF dispatch challan matching the Victory Laundry paper template.

    Layout (below the 5.7 cm pre-printed letterhead zone):
      ┌─────────────────────────────┬──────────────────────┐
      │ To   : <NAME>               │ No.  : P<ORDER_ID>   │
      │       , <ADDRESS>           │ Date : DD.MM.YYYY    │
      │ Phone: <PHONE>              │ Date of Delivery:    │
      │                             │   DD.MM.YYYY         │
      ├─────────────┬──────────┬────┴──────┬───────────────┤
      │ Particulars │ Barcode  │  Remark   │    Amount     │
      ├─────────────┼──────────┼───────────┼───────────────┤
      │ Shirt DC    │ P42-1   │           │        20.00  │
      │ Shirt DC    │ P42-1   │           │        20.00  │  ← same barcode repeated per unit
      │ Saree DC    │ P42-3   │ silk care │        80.00  │
      ├─────────────┴──────────┴───────────┼───────────────┤
      │ TOTAL                        <cnt> │       120.00  │
      │                      For Victory Laundry           │
      │                      Authorised Signatory          │
      └────────────────────────────────────────────────────┘

    One row per PHYSICAL GARMENT.  The barcode counter increments by the
    quantity of each item line — all units of the same line share one barcode.
    """
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.units import mm
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from datetime import datetime

    if output_path is None:
        tmp = tempfile.gettempdir()
        output_path = os.path.join(
            tmp, f"victory_challan_order_{order_data['order_id']}.pdf"
        )

    PAGE_W, PAGE_H = A5                          # 148.5 × 210 mm portrait
    ML = 10 * mm                                 # left margin
    MR = 8  * mm                                 # right margin
    TOP_OFFSET = 57 * mm                         # blank zone — pre-printed letterhead
    CONTENT_W = PAGE_W - ML - MR                 # ≈ 130.5 mm usable width

    F_BOLD   = "Helvetica-Bold"
    F_NORM   = "Helvetica"
    F_ITALIC = "Helvetica-Oblique"
    S_HDR    = 9    # section / header font size
    S_NORM   = 8    # normal body text
    S_SM     = 7.5  # small (address continuation, delivery label)
    LH       = 4.5 * mm   # standard line height

    def _fmt_date_dots(iso: str) -> str:
        """Convert YYYY-MM-DD → DD.MM.YYYY (dots)."""
        try:
            return datetime.strptime(iso, "%Y-%m-%d").strftime("%d.%m.%Y")
        except Exception:
            return iso or ""

    def _strip_country_code(phone: str) -> str:
        """Return a bare 10-digit Indian number, stripping leading +91/0091/91."""
        raw = str(phone or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if raw.startswith(("00", "+0")) and len(digits) > 10:
            digits = digits[2:]
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        return digits if digits else raw

    c = rl_canvas.Canvas(output_path, pagesize=A5)

    # ── y cursor: start just below the pre-printed letterhead zone ────────────
    y = PAGE_H - TOP_OFFSET

    # ──────────────────────────────────────────────────────────────────────────
    # HEADER — two columns
    # Left col ≈ 65 % of content width, right col ≈ 35 %
    # ──────────────────────────────────────────────────────────────────────────
    LEFT_W  = CONTENT_W * 0.62
    RIGHT_X = ML + LEFT_W + 4 * mm
    RIGHT_W = CONTENT_W - LEFT_W - 4 * mm

    order_id    = order_data.get("order_id", "")
    cust_name   = order_data.get("name", "")
    cust_phone  = _strip_country_code(order_data.get("phone", ""))
    cust_place  = (order_data.get("place") or "").strip()
    cust_addr   = (order_data.get("address") or "").strip()
    payment     = (order_data.get("payment_method") or "").strip()
    order_date  = _fmt_date_dots(order_data.get("order_date", ""))
    deliv_date  = _fmt_date_dots(order_data.get("delivery_date", ""))

    # Helper: truncate text to fit within max_pts points width
    def _trunc(text: str, font: str, size: float, max_pts: float) -> str:
        while text and stringWidth(text, font, size) > max_pts:
            text = text[:-1]
        return text

    # --- Left column ---
    lx = ML
    ly = y
    lbl_w  = stringWidth("Phone : ", F_BOLD, S_NORM)
    val_w  = LEFT_W - lbl_w - 2 * mm   # max width for value text
    indent = lx + lbl_w

    # "To    : <name>"
    c.setFont(F_BOLD, S_NORM);  c.drawString(lx, ly, "To    :")
    c.setFont(F_BOLD, S_NORM);  c.drawString(indent, ly, _trunc(cust_name, F_BOLD, S_NORM, val_w))
    ly -= LH

    # Address — build a list of non-empty address fragments to print
    addr_lines = []
    if cust_place:
        addr_lines.append(cust_place)
    if cust_addr:
        # split long address on commas/newlines into separate printed lines
        for part in cust_addr.replace("\n", ",").split(","):
            part = part.strip()
            if part:
                addr_lines.append(part)

    if addr_lines:
        c.setFont(F_NORM, S_NORM)
        # First address fragment: comma-prefixed, aligned under value column
        c.drawString(indent, ly, _trunc(", " + addr_lines[0], F_NORM, S_NORM, val_w + lbl_w))
        ly -= LH
        for frag in addr_lines[1:]:
            c.drawString(indent + 2 * mm, ly, _trunc(frag + ",", F_NORM, S_NORM, val_w + lbl_w - 2 * mm))
            ly -= LH

    # "Phone : <number>"
    c.setFont(F_BOLD, S_NORM);  c.drawString(lx, ly, "Phone :")
    c.setFont(F_NORM, S_NORM);  c.drawString(indent, ly, cust_phone)
    ly -= LH

    # --- Right column: each label drawn with its own indent width ---
    rx = RIGHT_X
    ry = y

    def _rline(label: str, value: str, font_lbl: str = F_BOLD, size_lbl: float = S_NORM,
               font_val: str = F_NORM, size_val: float = S_NORM):
        """Draw label + value on the same line, value offset by label width."""
        nonlocal ry
        lw = stringWidth(label, font_lbl, size_lbl)
        c.setFont(font_lbl, size_lbl);  c.drawString(rx, ry, label)
        c.setFont(font_val, size_val);  c.drawString(rx + lw + 1 * mm, ry, value)
        ry -= LH

    _rline("No.   :",            f"P{order_id}")
    _rline("Date  :",            order_date)
    _rline("Mode of Payment:",   payment)

    # Advance y past the taller of the two columns
    header_bottom = min(ly, ry)   # lower y = visually lower on page
    y = header_bottom - 4 * mm

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE
    # Columns: Particulars | Barcode | Remark | Amount
    # Widths (% of CONTENT_W):  45% | 20% | 20% | 15%
    # ──────────────────────────────────────────────────────────────────────────
    CW_PART = CONTENT_W * 0.45
    CW_BAR  = CONTENT_W * 0.20
    CW_REM  = CONTENT_W * 0.20
    CW_AMT  = CONTENT_W * 0.15

    col_widths = [CW_PART, CW_BAR, CW_REM, CW_AMT]
    col_x = [ML]
    for w in col_widths[:-1]:
        col_x.append(col_x[-1] + w)

    HDR_H = 5.5 * mm
    ROW_H = 4.8 * mm
    PAD   = 1.2 * mm

    # Table outer top-left corner; we'll track as we draw
    tbl_top = y

    # ── Header row (outlined box, no fill, bold text) ─────────────────────────
    c.setLineWidth(0.6)
    c.rect(ML, y - HDR_H, CONTENT_W, HDR_H, fill=0, stroke=1)
    # NOTE: full-height vertical column dividers are drawn AFTER the outer rect
    # is known (i.e. after tbl_bottom is computed). We save col_x for that step.

    c.setFont(F_BOLD, S_HDR)
    text_y = y - HDR_H + 1.5 * mm
    c.drawString(col_x[0] + PAD,                     text_y, "Particulars")
    c.drawCentredString(col_x[1] + CW_BAR / 2,       text_y, "Barcode")
    c.drawCentredString(col_x[2] + CW_REM / 2,       text_y, "Remark")
    c.drawRightString(col_x[3] + CW_AMT - PAD,       text_y, "Amount")
    y -= HDR_H

    # ── Data rows (borderless — no individual row outlines) ───────────────────
    items = order_data.get("items", [])
    garment_counter = 1          # running counter; advances by qty per item line
    all_rows = []                # collect (particulars, barcode_str, remark, amount)

    for item in items:
        cloth_type  = str(item.get("cloth_type", ""))
        qty         = max(1, int(item.get("quantity", 1)))
        rate        = float(item.get("price_per_unit", 0))
        item_notes  = (item.get("item_notes") or "").strip()
        particulars = cloth_type + " DC"

        for _ in range(qty):
            # Each physical unit gets its OWN barcode — matches dispatch label
            barcode_str = f"P{order_id}-{garment_counter}"
            all_rows.append((
                particulars,
                barcode_str,
                item_notes,
                f"{rate:.2f}"
            ))
            garment_counter += 1   # advance per physical unit

    total_garments = garment_counter - 1
    data_top = y

    c.setFont(F_NORM, S_NORM)
    for row_part, row_bar, row_rem, row_amt in all_rows:
        text_y = y - ROW_H + 1.5 * mm
        c.drawString(col_x[0] + PAD,               text_y, row_part)
        c.drawCentredString(col_x[1] + CW_BAR / 2, text_y, row_bar)
        if row_rem:
            c.drawCentredString(col_x[2] + CW_REM / 2, text_y, row_rem)
        c.drawRightString(col_x[3] + CW_AMT - PAD, text_y, row_amt)
        y -= ROW_H

    # Divider line above TOTAL row
    c.setLineWidth(0.5)
    c.line(ML, y, ML + CONTENT_W, y)
    y -= 1 * mm

    # ── TOTAL row ─────────────────────────────────────────────────────────────
    TOTAL_H = 5.5 * mm
    total_val = f"{order_data.get('total_amount', 0):.2f}"

    text_y = y - TOTAL_H + 1.5 * mm
    c.setFont(F_BOLD, S_HDR)
    c.drawString(col_x[0] + PAD,                          text_y, "TOTAL")
    c.drawCentredString(col_x[1] + CW_BAR / 2,            text_y, str(total_garments))
    c.drawRightString(col_x[3] + CW_AMT - PAD,            text_y, total_val)
    y -= TOTAL_H

    # Outer border + full-height internal column dividers
    tbl_bottom = y
    c.setLineWidth(0.6)
    c.rect(ML, tbl_bottom, CONTENT_W, tbl_top - tbl_bottom, fill=0, stroke=1)
    # Draw vertical dividers from top of table to bottom (through header + data + total)
    c.setLineWidth(0.5)
    for cx in col_x[1:]:
        c.line(cx, tbl_bottom, cx, tbl_top)

    # ── Footer: right-aligned, two lines ──────────────────────────────────────
    y -= 5 * mm
    c.setFont(F_BOLD, S_NORM)
    c.drawRightString(ML + CONTENT_W, y, "For Victory Laundry")
    y -= LH + 1 * mm
    c.setFont(F_ITALIC, S_NORM)
    c.drawRightString(ML + CONTENT_W, y, "Authorised Signatory")

    c.save()
    return output_path


def silent_print_image(image_path: str, printer_name: str = None,
                       margin_left_mm: float = None, margin_top_mm: float = None,
                       scale_pct: float = None, copies: int = None,
                       rotate_180: bool = None) -> bool:
    """Silently print an image file directly to a printer with size, scale, margin, and copy adjustments."""
    import traceback

    _logger.info("---- silent_print_image START ----")
    _logger.info("build marker: DEBUG-BUILD-0007")
    _logger.info("image_path=%s", image_path)

    is_barcode = "dispatch" in image_path.lower() or "slip" in image_path.lower()
    setting_pfx = "barcode" if is_barcode else "receipt"
    _logger.info("is_barcode=%s setting_pfx=%s", is_barcode, setting_pfx)

    try:
        import database as db
        if not printer_name:
            printer_name = db.get_setting(f"printer_{setting_pfx}", "")
        if margin_left_mm is None:
            margin_left_mm = float(db.get_setting(f"{setting_pfx}_margin_left", "0"))
        if margin_top_mm is None:
            margin_top_mm = float(db.get_setting(f"{setting_pfx}_margin_top", "0"))
        if scale_pct is None:
            scale_pct = float(db.get_setting(f"{setting_pfx}_scale", "100"))
        if copies is None:
            copies = int(db.get_setting(f"{setting_pfx}_copies", "1"))
        if rotate_180 is None:
            raw_rot = db.get_setting(f"{setting_pfx}_rotate180", "0")
            _logger.info("raw rotate180 setting from DB = %r", raw_rot)
            rotate_180 = (raw_rot == "1")
    except Exception:
        _logger.error("Failed reading settings from database:\n%s", traceback.format_exc())
        if margin_left_mm is None: margin_left_mm = 0
        if margin_top_mm is None: margin_top_mm = 0
        if scale_pct is None: scale_pct = 100
        if copies is None: copies = 1
        if rotate_180 is None: rotate_180 = False

    _logger.info("RESOLVED SETTINGS: printer_name=%r margin_left_mm=%s margin_top_mm=%s "
                 "scale_pct=%s copies=%s rotate_180=%s",
                 printer_name, margin_left_mm, margin_top_mm, scale_pct, copies, rotate_180)

    if os.name == "nt":
        # 1. Try Win32 GDI direct printer DC (100% silent, fully adjustable)
        try:
            import win32print
            import win32gui
            import win32ui
            import win32con
            from PIL import Image, ImageWin

            target_printer = printer_name or win32print.GetDefaultPrinter()
            _logger.info("target_printer=%r", target_printer)

            img = Image.open(image_path)
            _logger.info("Loaded image size=%s mode=%s dpi=%s", img.size, img.mode, img.info.get("dpi"))

            if rotate_180:
                img = img.rotate(180)
                _logger.info("Applied img.rotate(180). New size=%s", img.size)
            else:
                _logger.info("rotate_180 is False — NOT rotating in software")

            # Determine paper size and orientation for in-memory per-job DEVMODE
            hDC = None
            try:
                hprinter = win32print.OpenPrinter(target_printer)
                try:
                    props = win32print.GetPrinter(hprinter, 2)
                    devmode = props.get("pDevMode")
                    if devmode is not None:
                        # Paper size detection
                        paper_size_code = None
                        try:
                            import database as db
                            psize = db.get_setting(f"{setting_pfx}_paper_size", "").upper()
                        except Exception:
                            psize = ""

                        # Detect A5 or A4 if set or if image matches A5/A4 sheet size
                        img_w, img_h = img.size
                        aspect = img_h / float(img_w) if img_w > 0 else 1.0

                        if "A5" in psize or (abs(aspect - 1.414) < 0.15 and max(img_w, img_h) >= 2000 and min(img_w, img_h) <= 1800):
                            paper_size_code = win32con.DMPAPER_A5
                            _logger.info("Configured DEVMODE for A5 paper (DMPAPER_A5)")
                        elif "A4" in psize or (abs(aspect - 1.414) < 0.15 and min(img_w, img_h) > 2000):
                            paper_size_code = win32con.DMPAPER_A4
                            _logger.info("Configured DEVMODE for A4 paper (DMPAPER_A4)")
                        elif "LETTER" in psize:
                            paper_size_code = win32con.DMPAPER_LETTER
                            _logger.info("Configured DEVMODE for Letter paper (DMPAPER_LETTER)")

                        if paper_size_code is not None:
                            devmode.PaperSize = paper_size_code
                            devmode.Fields |= win32con.DM_PAPERSIZE

                        devmode.Orientation = win32con.DMORIENT_PORTRAIT
                        devmode.Fields |= win32con.DM_ORIENTATION

                        # Create DC with custom in-memory DEVMODE
                        hdc_handle = win32gui.CreateDC("WINSPOOL", target_printer, devmode)
                        if hdc_handle:
                            hDC = win32ui.CreateDCFromHandle(hdc_handle)
                            _logger.info("Created DC with custom DEVMODE (Orientation=PORTRAIT, PaperSize=%s)", paper_size_code)
                finally:
                    win32print.ClosePrinter(hprinter)
            except Exception:
                _logger.warning("Custom DEVMODE setup failed, falling back to default printer DC:\n%s", traceback.format_exc())

            if hDC is None:
                hDC = win32ui.CreateDC()
                hDC.CreatePrinterDC(target_printer)
                _logger.info("Created standard printer DC")

            printable_w = hDC.GetDeviceCaps(win32con.HORZRES)
            printable_h = hDC.GetDeviceCaps(win32con.VERTRES)
            dpi_x = hDC.GetDeviceCaps(win32con.LOGPIXELSX) or 300
            dpi_y = hDC.GetDeviceCaps(win32con.LOGPIXELSY) or 300

            phys_w = hDC.GetDeviceCaps(win32con.PHYSICALWIDTH) or printable_w
            phys_h = hDC.GetDeviceCaps(win32con.PHYSICALHEIGHT) or printable_h
            phys_off_x = hDC.GetDeviceCaps(win32con.PHYSICALOFFSETX) or 0
            phys_off_y = hDC.GetDeviceCaps(win32con.PHYSICALOFFSETY) or 0

            _logger.info("DC caps: printable_w=%s printable_h=%s dpi_x=%s dpi_y=%s "
                         "phys_w=%s phys_h=%s phys_off_x=%s phys_off_y=%s",
                         printable_w, printable_h, dpi_x, dpi_y,
                         phys_w, phys_h, phys_off_x, phys_off_y)

            img_w, img_h = img.size
            img_dpi = img.info.get("dpi", (300, 300))[0] or 300

            img_w_inches = img_w / float(img_dpi)
            img_h_inches = img_h / float(img_dpi)
            phys_w_inches = phys_w / float(dpi_x)
            phys_h_inches = phys_h / float(dpi_y)

            is_sheet_match = (phys_w > 0 and abs(img_w_inches - phys_w_inches) < 0.35)
            if is_sheet_match:
                base_target_w = phys_w
                base_target_h = phys_h
                _logger.info("Using FULL PAGE SHEET MATCH branch")
            else:
                base_target_w = int(img_w_inches * dpi_x)
                base_target_h = int(img_h_inches * dpi_y)
                if base_target_w > printable_w:
                    base_scale = printable_w / float(base_target_w)
                    base_target_w = printable_w
                    base_target_h = int(base_target_h * base_scale)
                _logger.info("Using SCALED-TO-PHYSICAL-INCHES branch")

            custom_scale = scale_pct / 100.0
            target_w = int(base_target_w * custom_scale)
            target_h = int(base_target_h * custom_scale)

            user_off_x = int((margin_left_mm / 25.4) * dpi_x)
            user_off_y = int((margin_top_mm / 25.4) * dpi_y)

            if is_sheet_match:
                x1 = user_off_x - phys_off_x
                y1 = user_off_y - phys_off_y
            else:
                if is_barcode and printable_w > target_w:
                    center_offset_x = (printable_w - target_w) // 2
                    x1 = max(0, center_offset_x + user_off_x - phys_off_x)
                else:
                    x1 = user_off_x
                y1 = user_off_y

            x2 = x1 + target_w
            y2 = y1 + target_h

            _logger.info("Final draw rect: x1=%s y1=%s x2=%s y2=%s (target_w=%s target_h=%s)",
                         x1, y1, x2, y2, target_w, target_h)

            hDC.StartDoc(os.path.basename(image_path))
            dib = ImageWin.Dib(img)

            for i in range(max(1, copies)):
                hDC.StartPage()
                dib.draw(hDC.GetHandleOutput(), (x1, y1, x2, y2))
                hDC.EndPage()
                _logger.info("Printed copy %d/%d", i + 1, copies)

            hDC.EndDoc()
            hDC.DeleteDC()
            _logger.info("GDI print path SUCCEEDED — returning True")
            _logger.info("---- silent_print_image END ----")
            return True
        except Exception:
            _logger.error("GDI print path FAILED:\n%s", traceback.format_exc())

        # 2. Try PowerShell print
        try:
            _logger.warning("Falling back to PowerShell print method (NOTE: this method "
                            "prints the ORIGINAL file from disk and does NOT apply rotate_180)")
            import subprocess
            target_printer = printer_name or ""
            ps_cmd = (
                f"Start-Process -FilePath '{image_path}' "
                + (f"-Verb PrintTo -ArgumentList '\"{target_printer}\"' " if target_printer else "-Verb Print ")
                + "-WindowStyle Hidden"
            )
            subprocess.run(["powershell", "-Command", ps_cmd], check=True, creationflags=0x08000000)
            _logger.info("PowerShell print path SUCCEEDED — returning True")
            return True
        except Exception:
            _logger.error("PowerShell print path FAILED:\n%s", traceback.format_exc())

        # 3. Fallback ShellExecute
        try:
            _logger.warning("Falling back to ShellExecute method (NOTE: this method "
                            "prints the ORIGINAL file from disk and does NOT apply rotate_180)")
            import win32api
            if printer_name:
                win32api.ShellExecute(0, "printto", image_path, f'"{printer_name}"', ".", 0)
            else:
                win32api.ShellExecute(0, "print", image_path, None, ".", 0)
            _logger.info("ShellExecute print path SUCCEEDED — returning True")
            return True
        except Exception:
            _logger.error("ShellExecute print path FAILED:\n%s", traceback.format_exc())
            if hasattr(os, "startfile"):
                os.startfile(image_path, "print")
                _logger.info("os.startfile print fallback used — returning True")
                return True

    _logger.error("All print methods exhausted — returning False")
    _logger.info("---- silent_print_image END ----")
    return False


def silent_print_pdf(pdf_path: str, printer_name: str = None) -> bool:
    """Silently print a PDF document directly to a printer without showing a preview window."""
    if not printer_name:
        try:
            import database as db
            if "dispatch" in pdf_path.lower() or "challan" in pdf_path.lower():
                printer_name = db.get_setting("printer_dispatch", "") or db.get_setting("printer_receipt", "")
            else:
                printer_name = db.get_setting("printer_receipt", "")
        except Exception:
            printer_name = ""

    if os.name == "nt":
        # 1. Try Win32 ShellExecute / win32api
        try:
            import win32api
            if printer_name:
                win32api.ShellExecute(0, "printto", pdf_path, f'"{printer_name}"', ".", 0)
            else:
                win32api.ShellExecute(0, "print", pdf_path, None, ".", 0)
            return True
        except Exception:
            pass

        # 2. Try PowerShell hidden print
        try:
            import subprocess
            target_printer = printer_name or ""
            ps_cmd = (
                f"Start-Process -FilePath '{pdf_path}' "
                + (f"-Verb PrintTo -ArgumentList '\"{target_printer}\"' " if target_printer else "-Verb Print ")
                + "-WindowStyle Hidden"
            )
            subprocess.run(["powershell", "-Command", ps_cmd], check=True, creationflags=0x08000000)
            return True
        except Exception:
            pass

        # 3. Fallback os.startfile
        try:
            if hasattr(os, "startfile"):
                try:
                    os.startfile(pdf_path, "print")
                except Exception:
                    os.startfile(pdf_path)
                return True
        except Exception:
            pass
    return False


def generate_dispatch_challan_image(order_data: dict, output_path: str = None) -> str:
    """
    Generate an A5 PNG receipt image matching Victory Laundry pre-printed paper template.
    Leaves 5.7 cm top margin for pre-printed letterhead.
    """
    from datetime import datetime

    if output_path is None:
        import tempfile
        output_path = os.path.join(
            tempfile.gettempdir(), f"victory_challan_img_{order_data['order_id']}.png"
        )

    # A5 size at 300 DPI: 1754 x 2480 pixels
    w, h = 1754, 2480
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Margins & top offset (5.7 cm = 673 px at 300 DPI)
    ml = 118          # 10 mm left margin
    mr = 94           # 8 mm right margin
    content_w = w - ml - mr  # 1542 px
    y = 673           # 57 mm top offset for pre-printed letterhead

    try:
        font_bold   = ImageFont.truetype("arialbd.ttf", 32)
        font_norm   = ImageFont.truetype("arial.ttf", 30)
        font_sm     = ImageFont.truetype("arial.ttf", 26)
        font_hdr    = ImageFont.truetype("arialbd.ttf", 32)
        font_italic = ImageFont.truetype("ariali.ttf", 28)
    except Exception:
        font_bold   = ImageFont.load_default()
        font_norm   = font_bold
        font_sm     = font_bold
        font_hdr    = font_bold
        font_italic = font_bold

    def _fmt_date_dots(iso: str) -> str:
        try:
            return datetime.strptime(iso, "%Y-%m-%d").strftime("%d.%m.%Y")
        except Exception:
            return iso or ""

    def _strip_country_code(phone: str) -> str:
        raw = str(phone or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if raw.startswith(("00", "+0")) and len(digits) > 10:
            digits = digits[2:]
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        return digits if digits else raw

    order_id   = order_data.get("order_id", "")
    cust_name  = order_data.get("name", "")
    cust_phone = _strip_country_code(order_data.get("phone", ""))
    cust_place = (order_data.get("place") or "").strip()
    cust_addr  = (order_data.get("address") or "").strip()
    payment    = (order_data.get("payment_method") or "").strip()
    order_date = _fmt_date_dots(order_data.get("order_date", ""))

    # Header Two Columns
    left_w = int(content_w * 0.62)
    right_x = ml + left_w + 48
    lh = 48  # line height

    # Left Column
    ly = y
    draw.text((ml, ly), "To    :", fill=(0, 0, 0), font=font_bold)
    draw.text((ml + 120, ly), cust_name, fill=(0, 0, 0), font=font_bold)
    ly += lh

    addr_lines = []
    if cust_place:
        addr_lines.append(cust_place)
    if cust_addr:
        for part in cust_addr.replace("\n", ",").split(","):
            part = part.strip()
            if part:
                addr_lines.append(part)

    if addr_lines:
        draw.text((ml + 120, ly), ", " + addr_lines[0], fill=(0, 0, 0), font=font_norm)
        ly += lh
        for frag in addr_lines[1:]:
            draw.text((ml + 140, ly), frag + ",", fill=(0, 0, 0), font=font_norm)
            ly += lh

    draw.text((ml, ly), "Phone :", fill=(0, 0, 0), font=font_bold)
    draw.text((ml + 120, ly), cust_phone, fill=(0, 0, 0), font=font_norm)
    ly += lh

    # Right Column
    ry = y
    draw.text((right_x, ry), "No.   :", fill=(0, 0, 0), font=font_bold)
    draw.text((right_x + 100, ry), f"P{order_id}", fill=(0, 0, 0), font=font_norm)
    ry += lh

    draw.text((right_x, ry), "Date  :", fill=(0, 0, 0), font=font_bold)
    draw.text((right_x + 100, ry), order_date, fill=(0, 0, 0), font=font_norm)
    ry += lh

    draw.text((right_x, ry), "Mode of Payment:", fill=(0, 0, 0), font=font_bold)
    draw.text((right_x + 280, ry), payment, fill=(0, 0, 0), font=font_norm)
    ry += lh

    y = max(ly, ry) + 30

    # Table Column Widths
    cw_part = int(content_w * 0.45)
    cw_bar  = int(content_w * 0.20)
    cw_rem  = int(content_w * 0.20)
    cw_amt  = int(content_w * 0.15)

    col_x = [ml, ml + cw_part, ml + cw_part + cw_bar, ml + cw_part + cw_bar + cw_rem]

    hdr_h = 60
    row_h = 52

    tbl_top = y

    # Header Row Box
    draw.rectangle([ml, y, ml + content_w, y + hdr_h], outline=(0, 0, 0), width=2)
    draw.text((col_x[0] + 15, y + 12), "Particulars", fill=(0, 0, 0), font=font_hdr)
    draw.text((col_x[1] + cw_bar // 2, y + 12), "Barcode", fill=(0, 0, 0), font=font_hdr, anchor="mt")
    draw.text((col_x[2] + cw_rem // 2, y + 12), "Remark", fill=(0, 0, 0), font=font_hdr, anchor="mt")
    draw.text((col_x[3] + cw_amt - 15, y + 12), "Amount", fill=(0, 0, 0), font=font_hdr, anchor="rt")
    y += hdr_h

    # Data Rows
    items = order_data.get("items", [])
    garment_counter = 1
    total_garments = 0

    for item in items:
        cloth_type  = str(item.get("cloth_type", ""))
        qty         = max(1, int(item.get("quantity", 1)))
        rate        = float(item.get("price_per_unit", 0))
        item_notes  = (item.get("item_notes") or "").strip()
        particulars = cloth_type + " DC"

        for _ in range(qty):
            barcode_str = f"P{order_id}-{garment_counter}"
            text_y = y + 10

            draw.text((col_x[0] + 15, text_y), particulars, fill=(0, 0, 0), font=font_norm)
            draw.text((col_x[1] + cw_bar // 2, text_y), barcode_str, fill=(0, 0, 0), font=font_norm, anchor="mt")
            if item_notes:
                draw.text((col_x[2] + cw_rem // 2, text_y), item_notes, fill=(0, 0, 0), font=font_norm, anchor="mt")
            draw.text((col_x[3] + cw_amt - 15, text_y), f"{rate:.2f}", fill=(0, 0, 0), font=font_norm, anchor="rt")

            y += row_h
            garment_counter += 1

    total_garments = garment_counter - 1

    # Divider line
    draw.line([(ml, y), (ml + content_w, y)], fill=(0, 0, 0), width=2)
    y += 10

    # TOTAL row
    total_h = 60
    total_val = f"{order_data.get('total_amount', 0):.2f}"
    text_y = y + 12

    draw.text((col_x[0] + 15, text_y), "TOTAL", fill=(0, 0, 0), font=font_hdr)
    draw.text((col_x[1] + cw_bar // 2, text_y), str(total_garments), fill=(0, 0, 0), font=font_hdr, anchor="mt")
    draw.text((col_x[3] + cw_amt - 15, text_y), total_val, fill=(0, 0, 0), font=font_hdr, anchor="rt")
    y += total_h

    tbl_bottom = y

    # Outer border + Column dividers
    draw.rectangle([ml, tbl_top, ml + content_w, tbl_bottom], outline=(0, 0, 0), width=3)
    for cx in col_x[1:]:
        draw.line([(cx, tbl_top), (cx, tbl_bottom)], fill=(0, 0, 0), width=2)

    # Footer
    y += 60
    draw.text((ml + content_w, y), "For ÉTOFFE LAUNDRY STUDIO", fill=(0, 0, 0), font=font_bold, anchor="rt")
    y += 45
    draw.text((ml + content_w, y), "Authorised Signatory", fill=(0, 0, 0), font=font_italic, anchor="rt")

    img.save(output_path, "PNG", dpi=(300, 300))
    return output_path


def open_receipt(order_data: dict):
    """Generate and print or open the receipt PNG image based on print_mode setting."""
    try:
        import database as db
        print_mode = db.get_setting("print_mode", "direct")
    except Exception:
        print_mode = "direct"

    path = generate_dispatch_challan_image(order_data)
    if print_mode == "preview":
        if hasattr(os, "startfile"):
            os.startfile(path)
    else:
        silent_print_image(path)
    return path


def open_receipt_pdf(order_data: dict, parent_window=None) -> str:
    """Generate and print or open receipt based on print_mode setting."""
    try:
        import database as db
        print_mode = db.get_setting("print_mode", "direct")
    except Exception:
        print_mode = "direct"

    if print_mode == "preview":
        path = generate_dispatch_challan_pdf(order_data)
        try:
            if hasattr(os, "startfile"):
                os.startfile(path)
            else:
                import subprocess, sys
                if sys.platform == "darwin":
                    subprocess.run(["open", path], check=False)
                else:
                    subprocess.run(["xdg-open", path], check=False)
        except Exception:
            pass
        return path
    else:
        # Direct automatic GDI print with 5.7cm pre-printed letterhead offset
        return open_receipt(order_data)




def normalize_whatsapp_phone(phone: object) -> str:
    """Return a WhatsApp-compatible E.164 number (without ``+``).

    The application stores Indian customer numbers without an explicit country
    code, so a ten-digit number is treated as an Indian mobile number.  Other
    numbers must already include their country code.
    """
    raw = str(phone or "").strip()
    digits = "".join(char for char in raw if char.isdigit())
    if raw.startswith("00"):
        digits = digits[2:]
    if len(digits) == 10:
        digits = "91" + digits
    if not 8 <= len(digits) <= 15:
        raise ValueError(
            "Enter a valid WhatsApp number with country code, or a 10-digit Indian mobile number."
        )
    return digits


def _valid_parent(parent_window):
    """Return parent_window if it exists and is not destroyed, else None."""
    if parent_window is not None:
        try:
            if hasattr(parent_window, "winfo_exists") and parent_window.winfo_exists():
                return parent_window
        except Exception:
            pass
    return None


def send_whatsapp_receipt(order_data: dict, parent_window=None) -> str | None:
    """
    Generate the normal receipt image, then prepare a WhatsApp Web chat.
    Staff attach the image and message, ready for review.
    """
    from tkinter import messagebox

    if not order_data.get("items"):
        try:
            import database as db
            full_order = db.get_order_full(order_data["order_id"])
            if full_order:
                order_data = full_order
        except Exception:
            pass

    # Validate before creating a temporary receipt file.
    try:
        digits = normalize_whatsapp_phone(order_data.get("phone"))
    except ValueError as exc:
        messagebox.showerror(
            "WhatsApp Error",
            str(exc),
            parent=_valid_parent(parent_window)
        )
        return None

    # Generate WhatsApp-specific receipt with branded Étoffe header design
    image_path = generate_whatsapp_receipt(order_data)

    # 3. Format simplified receipt message (detailed breakdown is in the image)
    customer_name = order_data.get("name") or "Customer"
    order_id = order_data.get("order_id", "")
    caption = (
        f"Hello {customer_name},\n\n"
        f"Here is your receipt for Order #{order_id}.\n\n"
        f"Thank you for choosing ÉTOFFE LAUNDRY STUDIO 😊"
    )

    _open_whatsapp_receipt_manual(digits, caption, image_path, parent_window)
    return image_path


def send_whatsapp_ready_notification(order_data: dict, parent_window=None) -> bool:
    """Prepare a WhatsApp Web ready-order notification for staff to send."""
    from tkinter import messagebox

    try:
        digits = normalize_whatsapp_phone(order_data.get("phone"))
    except ValueError as exc:
        messagebox.showerror("WhatsApp Error", str(exc), parent=_valid_parent(parent_window))
        return False

    customer = order_data.get("name") or "Customer"
    message = (
        f"Hello {customer},\n\n"
        f"Your Victory Laundry order #{order_data['order_id']} is ready. "
        "Please contact us to arrange pickup/delivery.\n\n"
        "Thank you!"
    )
    _open_whatsapp_text_manual(digits, message, parent_window)
    return True


def prompt_whatsapp_ready_notification(order_data: dict, parent_window=None) -> bool:
    """Offer staff a ready-order WhatsApp notification after a status transition."""
    from tkinter import messagebox

    order_id = order_data["order_id"]
    customer = order_data.get("name") or "this customer"
    if not messagebox.askyesno(
        "Order Ready",
        f"Order #{order_id} is now Ready.\n\n"
        f"Send a WhatsApp notification to {customer}?",
        parent=_valid_parent(parent_window),
    ):
        return False
    return send_whatsapp_ready_notification(order_data, parent_window)


def _open_whatsapp_receipt_manual(digits: str, caption: str, image_path: str, parent_window=None):
    """Prepare a receipt in WhatsApp Web with image attached without sending it automatically."""
    from tkinter import messagebox
    try:
        from whatsapp_web import send_receipt
        send_receipt(digits, image_path, caption)
    except Exception as exc:
        # Silently ignore errors from user closing the browser — that's normal workflow
        err = str(exc).lower()
        if "closed" in err or "target page" in err or "browser" in err:
            return
        messagebox.showerror("WhatsApp Web Error", str(exc), parent=_valid_parent(parent_window))
        return


def _open_whatsapp_text_manual(digits: str, message: str, parent_window=None):
    """Prepare a ready-order notification in WhatsApp Web."""
    from tkinter import messagebox
    try:
        from whatsapp_web import prepare_message
        prepare_message(digits, message)
    except Exception as exc:
        # Silently ignore errors from user closing the browser — that's normal workflow
        err = str(exc).lower()
        if "closed" in err or "target page" in err or "browser" in err:
            return
        messagebox.showerror("WhatsApp Web Error", str(exc), parent=_valid_parent(parent_window))
        return
