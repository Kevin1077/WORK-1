import os
import tempfile
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

def _get_font(size: int, bold: bool = False, italic: bool = False) -> ImageFont.ImageFont:
    font_names = []
    if bold and italic:
        font_names = ["arialbi.ttf", "calibriz.ttf", "segoeuiz.ttf", "DejaVuSans-BoldOblique.ttf"]
    elif bold:
        font_names = ["arialbd.ttf", "calibrib.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"]
    elif italic:
        font_names = ["ariali.ttf", "calibrii.ttf", "segoeuii.ttf", "DejaVuSans-Oblique.ttf"]
    else:
        font_names = ["arial.ttf", "calibri.ttf", "segoeui.ttf", "DejaVuSans.ttf"]

    for fn in font_names:
        try:
            return ImageFont.truetype(fn, size)
        except Exception:
            pass
    return ImageFont.load_default()

def _get_text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]

def _fmt_date_dots(iso: str) -> str:
    try:
        if " " in str(iso):
            dt_part = str(iso).split(" ")[0]
            return datetime.strptime(dt_part, "%Y-%m-%d").strftime("%d.%m.%Y")
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

def _build_whatsapp_receipt_image(order_data: dict) -> Image.Image:
    """
    Build and return a PIL Image object of the WhatsApp receipt matching
    the dispatch challan receipt layout with a digital header (Étoffe logo + address).
    """
    try:
        import database as db
        psize = db.get_setting("receipt_paper_size", "80mm")
    except Exception:
        psize = "80mm"

    if psize == "58mm":
        img_width = 520
        margin = 20
        scale = 0.76
    elif psize == "A4":
        img_width = 850
        margin = 36
        scale = 1.25
    elif psize == "A5":
        img_width = 720
        margin = 32
        scale = 1.05
    else:
        # Standard mobile-optimized WhatsApp image width (80mm)
        img_width = 680
        margin = 28
        scale = 1.0

    content_w = img_width - (2 * margin)
    bg_color = (255, 255, 255)
    fg_color = (0, 0, 0)

    # Fonts scaled appropriately
    f_title  = max(12, int(15 * scale))
    f_body   = max(11, int(13.5 * scale))
    f_sm     = max(10, int(12 * scale))
    f_italic = max(11, int(13 * scale))

    font_bold   = _get_font(f_title, bold=True)
    font_norm   = _get_font(f_body)
    font_sm     = _get_font(f_sm)
    font_hdr    = _get_font(f_title, bold=True)
    font_italic = _get_font(f_italic, italic=True)

    # Locate Étoffe logo
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

    logo_w, logo_h = 0, 0
    if logo_img:
        target_logo_w = int(content_w * 0.33)
        ratio = target_logo_w / logo_img.width
        logo_w = target_logo_w
        logo_h = int(logo_img.height * ratio)
        max_logo_h = int(130 * scale)
        if logo_h > max_logo_h:
            ratio = max_logo_h / logo_img.height
            logo_h = max_logo_h
            logo_w = int(logo_img.width * ratio)
        logo_img = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)

    addr_lines = [
        "Opp. St. Marys Church",
        "Lalam (Old) Bypass Road",
        "PALA",
        "Mob: 9846593957",
    ]
    addr_line_h = int(18 * scale)
    addr_block_h = len(addr_lines) * addr_line_h

    header_block_h = max(logo_h, addr_block_h) if logo_img else max(int(40 * scale), addr_block_h)

    # Customer & Order info strings
    order_id   = str(order_data.get("order_id", ""))
    cust_name  = str(order_data.get("name", "") or "")
    cust_phone = _strip_country_code(order_data.get("phone", ""))
    cust_place = str(order_data.get("place") or "").strip()
    cust_addr  = str(order_data.get("address") or "").strip()
    payment    = str(order_data.get("payment_method") or "").strip() or "—"
    order_date = _fmt_date_dots(order_data.get("order_date", ""))

    cust_addr_parts = []
    if cust_place:
        cust_addr_parts.append(cust_place)
    if cust_addr:
        for part in cust_addr.replace("\n", ",").split(","):
            p = part.strip()
            if p:
                cust_addr_parts.append(p)

    info_lh = int(22 * scale)
    left_w = int(content_w * 0.58)
    right_x = margin + left_w + int(12 * scale)

    # Calculate garment rows
    items = order_data.get("items", [])
    garment_list = []
    garment_counter = 1
    for item in items:
        cloth_type  = str(item.get("cloth_type", ""))
        qty         = max(1, int(item.get("quantity", 1)))
        rate        = float(item.get("price_per_unit", 0))
        item_notes  = str(item.get("item_notes") or item.get("notes") or "").strip()
        particulars = cloth_type + " DC" if not cloth_type.endswith(" DC") else cloth_type

        for _ in range(qty):
            barcode_str = f"P{order_id}-{garment_counter}"
            garment_list.append((particulars, barcode_str, item_notes, rate))
            garment_counter += 1

    total_garments = len(garment_list)

    # Dummy draw to measure precise widths
    dummy = Image.new("RGB", (100, 100), bg_color)
    d_dummy = ImageDraw.Draw(dummy)

    left_col_lbl_w = max(
        _get_text_width(d_dummy, "To    :", font_bold),
        _get_text_width(d_dummy, "Phone :", font_bold)
    ) + int(10 * scale)
    to_val_x = margin + left_col_lbl_w

    right_col_lbl_w = max(
        _get_text_width(d_dummy, "No.   :", font_bold),
        _get_text_width(d_dummy, "Date  :", font_bold)
    ) + int(10 * scale)
    no_val_x = right_x + right_col_lbl_w

    mop_lbl_w = _get_text_width(d_dummy, "Mode of Payment:", font_bold) + int(8 * scale)
    mop_val_x = right_x + mop_lbl_w

    # ── Pass 1: Measure dynamic total height ──────────────────────────────────
    y = int(20 * scale)  # Top margin
    y += header_block_h
    y += int(12 * scale) # Space before header divider line
    y += int(14 * scale) # Space after header divider line

    # Two-column customer & order section
    left_lines_cnt = 1 + len(cust_addr_parts) + 1  # To, Addr lines, Phone
    right_lines_cnt = 3                             # No, Date, Mode of Payment
    two_col_h = max(left_lines_cnt, right_lines_cnt) * info_lh
    y += two_col_h + int(16 * scale)

    # Table section
    hdr_h = int(28 * scale)
    row_h = int(25 * scale)
    total_h = int(28 * scale)
    y += hdr_h
    y += len(garment_list) * row_h
    y += 2 # divider line
    y += total_h

    # Footer section
    y += int(28 * scale) # gap before footer
    y += int(20 * scale) # For Victory Laundry
    y += int(20 * scale) # Authorised Signatory
    y += int(24 * scale) # Bottom padding

    total_height = int(y)

    # ── Pass 2: Render actual image ──────────────────────────────────────────
    img = Image.new("RGB", (img_width, total_height), bg_color)
    draw = ImageDraw.Draw(img)

    y = int(20 * scale)

    # 1. Digital Header
    header_top_y = y
    if logo_img:
        logo_y = header_top_y + (header_block_h - logo_h) // 2
        # Composite transparent PNG onto white background
        img.paste(logo_img, (margin, logo_y), mask=logo_img.split()[3])
    else:
        # Fallback text if logo missing
        f_brand = _get_font(int(18 * scale), bold=True)
        draw.text((margin, header_top_y + int(4 * scale)), "ÉTOFFE LAUNDRY", fill=fg_color, font=f_brand)

    # Address block (right-aligned to content margin, vertically centered)
    addr_start_y = header_top_y + (header_block_h - addr_block_h) // 2
    for i, line in enumerate(addr_lines):
        line_y = addr_start_y + i * addr_line_h
        draw.text((margin + content_w, line_y), line, fill=fg_color, font=font_norm, anchor="rt")

    y = header_top_y + header_block_h + int(12 * scale)

    # Thin horizontal divider below header
    draw.line([(margin, y), (margin + content_w, y)], fill=fg_color, width=1)
    y += int(14 * scale)

    # 2. Two-Column Header Block (To: / No.:)
    two_col_start_y = y
    ly = two_col_start_y
    ry = two_col_start_y

    # Left Column: To / Address / Phone
    draw.text((margin, ly), "To    :", fill=fg_color, font=font_bold)
    draw.text((to_val_x, ly), cust_name, fill=fg_color, font=font_bold)
    ly += info_lh

    if cust_addr_parts:
        draw.text((to_val_x, ly), ", " + cust_addr_parts[0], fill=fg_color, font=font_norm)
        ly += info_lh
        for frag in cust_addr_parts[1:]:
            draw.text((to_val_x + int(12 * scale), ly), frag + ",", fill=fg_color, font=font_norm)
            ly += info_lh

    draw.text((margin, ly), "Phone :", fill=fg_color, font=font_bold)
    draw.text((to_val_x, ly), cust_phone, fill=fg_color, font=font_norm)
    ly += info_lh

    # Right Column: No / Date / Mode of Payment
    draw.text((right_x, ry), "No.   :", fill=fg_color, font=font_bold)
    draw.text((no_val_x, ry), f"P{order_id}", fill=fg_color, font=font_norm)
    ry += info_lh

    draw.text((right_x, ry), "Date  :", fill=fg_color, font=font_bold)
    draw.text((no_val_x, ry), order_date, fill=fg_color, font=font_norm)
    ry += info_lh

    draw.text((right_x, ry), "Mode of Payment:", fill=fg_color, font=font_bold)
    draw.text((mop_val_x, ry), payment, fill=fg_color, font=font_norm)
    ry += info_lh

    y = max(ly, ry) + int(14 * scale)

    # 3. Table Section
    cw_part = int(content_w * 0.45)
    cw_bar  = int(content_w * 0.20)
    cw_rem  = int(content_w * 0.20)
    cw_amt  = content_w - (cw_part + cw_bar + cw_rem)

    col_x = [margin, margin + cw_part, margin + cw_part + cw_bar, margin + cw_part + cw_bar + cw_rem]

    tbl_top = y

    # Table Header Row
    draw.rectangle([margin, y, margin + content_w, y + hdr_h], outline=fg_color, width=1)
    hdr_text_y = y + (hdr_h - f_title) // 2 - 1

    draw.text((col_x[0] + int(8 * scale), hdr_text_y), "Particulars", fill=fg_color, font=font_hdr)
    draw.text((col_x[1] + cw_bar // 2, hdr_text_y), "Barcode", fill=fg_color, font=font_hdr, anchor="mt")
    draw.text((col_x[2] + cw_rem // 2, hdr_text_y), "Remark", fill=fg_color, font=font_hdr, anchor="mt")
    draw.text((col_x[3] + cw_amt - int(8 * scale), hdr_text_y), "Amount", fill=fg_color, font=font_hdr, anchor="rt")

    y += hdr_h

    # Table Data Rows (1 per physical garment)
    for particulars, barcode_str, item_notes, rate in garment_list:
        row_text_y = y + (row_h - f_body) // 2 - 1

        draw.text((col_x[0] + int(8 * scale), row_text_y), particulars, fill=fg_color, font=font_norm)
        draw.text((col_x[1] + cw_bar // 2, row_text_y), barcode_str, fill=fg_color, font=font_norm, anchor="mt")
        if item_notes:
            draw.text((col_x[2] + cw_rem // 2, row_text_y), item_notes, fill=fg_color, font=font_norm, anchor="mt")
        draw.text((col_x[3] + cw_amt - int(8 * scale), row_text_y), f"{rate:.2f}", fill=fg_color, font=font_norm, anchor="rt")

        y += row_h

    # Table TOTAL Row
    draw.line([(margin, y), (margin + content_w, y)], fill=fg_color, width=1)
    total_val = f"{float(order_data.get('total_amount', 0)):.2f}"
    total_text_y = y + (total_h - f_title) // 2 - 1

    draw.text((col_x[0] + int(8 * scale), total_text_y), "TOTAL", fill=fg_color, font=font_hdr)
    draw.text((col_x[1] + cw_bar // 2, total_text_y), str(total_garments), fill=fg_color, font=font_hdr, anchor="mt")
    draw.text((col_x[3] + cw_amt - int(8 * scale), total_text_y), total_val, fill=fg_color, font=font_hdr, anchor="rt")

    y += total_h
    tbl_bottom = y

    # Table Outer Border & Column Dividers
    draw.rectangle([margin, tbl_top, margin + content_w, tbl_bottom], outline=fg_color, width=2)
    for cx in col_x[1:]:
        draw.line([(cx, tbl_top), (cx, tbl_bottom)], fill=fg_color, width=1)

    # 4. Footer Section
    y += int(28 * scale)
    draw.text((margin + content_w, y), "For Victory Laundry", fill=fg_color, font=font_bold, anchor="rt")
    y += int(20 * scale)
    draw.text((margin + content_w, y), "Authorised Signatory", fill=fg_color, font=font_italic, anchor="rt")

    return img

if __name__ == '__main__':
    sample = {
        'order_id': 68,
        'order_date': '2025-05-20',
        'payment_method': 'Paid (Cash)',
        'name': 'Mr. Jithin Thomas',
        'phone': '9846593957',
        'place': 'Pala',
        'address': 'Kottayam, Kerala - 686575',
        'items': [
            {'cloth_type': 'Shirt', 'quantity': 2, 'price_per_unit': 35.0, 'subtotal': 70.0, 'item_notes': ''},
            {'cloth_type': 'Pant', 'quantity': 1, 'price_per_unit': 40.0, 'subtotal': 40.0, 'item_notes': ''},
            {'cloth_type': 'Saree', 'quantity': 1, 'price_per_unit': 120.0, 'subtotal': 120.0, 'item_notes': 'silk care'},
        ],
        'total_amount': 230.0,
    }
    img = _build_whatsapp_receipt_image(sample)
    out = 'test_new_whatsapp_challan.png'
    img.save(out, 'PNG')
    print('Generated', out, 'Size:', img.size)
