"""
utils/receipt.py — PNG image receipt generator for ÉTOFFE LAUNDRY STUDIO
Uses Pillow (PIL) to create a clean, receipt-style PNG image.
Black and white only — no colours.
"""
import os
import tempfile
import logging
from pathlib import Path

_logger = logging.getLogger(__name__)

from PIL import Image, ImageDraw, ImageFont


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



def _fmt_date_dots(iso: str) -> str:
    """Convert YYYY-MM-DD -> DD.MM.YYYY (dots)."""
    if not iso:
        return ""
    parts = iso.split("-")
    if len(parts) == 3:
        return f"{parts[2]}.{parts[1]}.{parts[0]}"
    return iso

def _strip_country_code(phone: str) -> str:
    """Return a bare 10-digit Indian number, stripping leading +91/0091/91."""
    if not phone:
        return ""
    digits = "".join(filter(str.isdigit, phone))
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return digits

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

    # ── 1. Full-width Navy Header ─────────────────────────────────────────────
    NAVY       = (13,  36,  71)      # dark navy  #0D2447
    ADDR_BG    = (243, 244, 246)     # light gray #F3F4F6  (address strip)
    ADDR_FG    = (55,  65,  81)      # dark gray  #374151  (address text)

    navy_h     = 500                 # px — height of navy block
    addr_strip_h = 100               # px — address strip height
    hdr_total  = navy_h + addr_strip_h  # total header zone

    # Navy rectangle — full canvas width
    draw.rectangle([0, 0, w, navy_h], fill=NAVY)

    # Load logo and build a full-white version for the navy background
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
                raw = Image.open(cand).convert("RGBA")
                # Make every visible pixel white so the logo shows clearly on navy
                px = raw.getdata()
                white_px = [
                    (255, 255, 255, p[3]) if p[3] > 10 else (0, 0, 0, 0)
                    for p in px
                ]
                raw.putdata(white_px)
                bbox = raw.getbbox()
                logo_img = raw.crop(bbox) if bbox else raw
                break
            except Exception:
                pass

    # Fit logo inside navy block with generous padding
    max_logo_w = int(w * 0.55)
    max_logo_h = navy_h - 60
    navy_mid_y = navy_h // 2
    if logo_img:
        lw, lh = logo_img.size
        if lw > 0 and lh > 0:
            scale = min(max_logo_w / lw, max_logo_h / lh)
            fit_w = max(1, int(lw * scale))
            fit_h = max(1, int(lh * scale))
        else:
            fit_w, fit_h = max_logo_w, max_logo_h
        logo_resized = logo_img.resize((fit_w, fit_h), Image.Resampling.LANCZOS)
        logo_x = (w - fit_w) // 2
        logo_y = navy_mid_y - fit_h // 2
        img.paste(logo_resized, (logo_x, logo_y),
                  mask=logo_resized.split()[3] if logo_resized.mode == "RGBA" else None)
    else:
        # Fallback text branding on navy
        f_brand = _get_font(60, bold=True)
        draw.text((w // 2, navy_mid_y - 30), "ÉTOFFE", fill=(255, 255, 255), font=f_brand, anchor="mm")
        f_sub = _get_font(36)
        draw.text((w // 2, navy_mid_y + 40), "LAUNDRY STUDIO", fill=(220, 220, 220), font=f_sub, anchor="mm")

    # ── Address strip (light gray) ────────────────────────────────────────────
    draw.rectangle([0, navy_h, w, navy_h + addr_strip_h], fill=ADDR_BG)

    try:
        font_addr_strip = ImageFont.truetype("arial.ttf", 28)
    except Exception:
        font_addr_strip = _get_font(28)

    addr_single = "Opp. St. Mary's Church, Lalam (Old), Bypass Road, PALA, Mob: 9846593957"
    draw.text((w // 2, navy_h + addr_strip_h // 2), addr_single,
              fill=ADDR_FG, font=font_addr_strip, anchor="mm")

    # Sharp bottom border of the entire header zone
    border_y = hdr_total
    draw.rectangle([0, border_y, w, border_y + 3], fill=(180, 180, 180))

    # ── 2. Content area — comfortable gap after header ────────────────────────
    y = border_y + 56


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
    deliv_date = _fmt_date_dots(order_data.get("delivery_date", ""))

    # Header Two Columns
    left_w = int(content_w * 0.62)
    right_x = ml + left_w + 48
    lh = 48  # line height

    # Address font: bold, 1 px larger than font_norm (31 instead of 30)
    try:
        font_addr_bold = ImageFont.truetype("arialbd.ttf", 31)
    except Exception:
        font_addr_bold = _get_font(31, bold=True)

    # Customer name font: bold, 1 px larger (33 instead of 32)
    try:
        font_name_bold = ImageFont.truetype("arialbd.ttf", 33)
    except Exception:
        font_name_bold = _get_font(33, bold=True)

    # Left Column
    ly = y
    to_label = "TO:"
    to_label_w = _get_text_width(draw, to_label + "  ", font_bold)
    draw.text((ml, ly), to_label, fill=(0, 0, 0), font=font_bold)
    draw.text((ml + to_label_w, ly), cust_name, fill=(0, 0, 0), font=font_name_bold)
    ly += lh

    cust_addr_lines = []
    if cust_place:
        cust_addr_lines.append(cust_place)
    if cust_addr:
        for part in cust_addr.replace("\n", ",").split(","):
            part = part.strip()
            if part:
                cust_addr_lines.append(part)

    addr_indent = ml + to_label_w
    if cust_addr_lines:
        draw.text((addr_indent, ly), cust_addr_lines[0], fill=(0, 0, 0), font=font_addr_bold)
        ly += lh
        for frag in cust_addr_lines[1:]:
            draw.text((addr_indent, ly), frag, fill=(0, 0, 0), font=font_addr_bold)
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

    draw.text((right_x, ry), "Delivery Date:", fill=(0, 0, 0), font=font_bold)
    lbl_w = _get_text_width(draw, "Delivery Date: ", font_bold)
    draw.text((right_x + lbl_w, ry), deliv_date, fill=(0, 0, 0), font=font_norm)
    ry += lh

    # 0.3 cm shift down = 35 px at 300 DPI (30px original gap + 35px = 65px)
    y = max(ly, ry) + 65

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
    Generate an A5 PDF dispatch challan matching the ÉTOFFE LAUNDRY STUDIO paper template.

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
      │                      For ÉTOFFE LAUNDRY STUDIO     │
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
    to_label    = "TO:"
    to_lbl_w    = stringWidth(to_label + "  ", F_BOLD, S_NORM)
    indent      = lx + to_lbl_w
    val_w       = LEFT_W - to_lbl_w - 2 * mm   # max width for value text
    S_ADDR      = S_NORM + 1  # address font size: 1 pt larger

    # "TO: <name>"
    c.setFont(F_BOLD, S_NORM);      c.drawString(lx, ly, to_label)
    c.setFont(F_BOLD, S_ADDR);      c.drawString(indent, ly, _trunc(cust_name, F_BOLD, S_ADDR, val_w))
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
        c.setFont(F_BOLD, S_ADDR)
        # First address fragment aligned under TO: value column
        c.drawString(indent, ly, _trunc(addr_lines[0], F_BOLD, S_ADDR, val_w + to_lbl_w))
        ly -= LH
        for frag in addr_lines[1:]:
            c.drawString(indent + 2 * mm, ly, _trunc(frag, F_BOLD, S_ADDR, val_w + to_lbl_w - 2 * mm))
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

    _rline("No.   :",         f"P{order_id}")
    _rline("Date  :",         order_date)
    _rline("Delivery Date: ", deliv_date)

    # Advance y past the taller of the two columns, shifting table down by extra 0.3 cm (3mm)
    header_bottom = min(ly, ry)   # lower y = visually lower on page
    y = header_bottom - 7 * mm

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
    c.drawRightString(ML + CONTENT_W, y, "For ÉTOFFE LAUNDRY STUDIO")
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
    Generate an A5 PNG receipt image matching ÉTOFFE LAUNDRY STUDIO pre-printed paper template.
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
    deliv_date = _fmt_date_dots(order_data.get("delivery_date", ""))

    # Header Two Columns
    left_w = int(content_w * 0.62)
    right_x = ml + left_w + 48
    lh = 48  # line height

    # Left Column
    ly = y
    draw.text((ml, ly), "    To:", fill=(0, 0, 0), font=font_bold)
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
        draw.text((ml + 120, ly), ", " + addr_lines[0], fill=(0, 0, 0), font=font_bold)
        ly += lh
        for frag in addr_lines[1:]:
            draw.text((ml + 140, ly), frag + ",", fill=(0, 0, 0), font=font_bold)
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



    draw.text((right_x, ry), "Delivery Date:", fill=(0, 0, 0), font=font_bold)
    lbl_w = _get_text_width(draw, "Delivery Date: ", font_bold)
    draw.text((right_x + lbl_w, ry), deliv_date, fill=(0, 0, 0), font=font_norm)
    ry += lh

    # 0.3 cm shift down = 35 px at 300 DPI (30px original gap + 35px = 65px)
    y = max(ly, ry) + 65

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
        f"Your ÉTOFFE LAUNDRY STUDIO order #{order_data['order_id']} is ready for pickup.\n\n"
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
