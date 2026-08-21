import os
import sys
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

def generate_dispatch_challan_image(order_data: dict, output_path: str = None) -> str:
    """
    Generate an A5 PNG receipt image matching Victory Laundry pre-printed paper template.
    Leaves 5.7 cm top margin for pre-printed letterhead.
    """
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
        font_bold = ImageFont.truetype("arialbd.ttf", 32)
        font_norm = ImageFont.truetype("arial.ttf", 30)
        font_sm   = ImageFont.truetype("arial.ttf", 26)
        font_hdr  = ImageFont.truetype("arialbd.ttf", 32)
        font_italic = ImageFont.truetype("ariali.ttf", 28)
    except Exception:
        font_bold = ImageFont.load_default()
        font_norm = font_bold
        font_sm   = font_bold
        font_hdr  = font_bold
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

    y = max(ly, ry) + 40

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
    draw.text((ml + content_w, y), "For Victory Laundry", fill=(0, 0, 0), font=font_bold, anchor="rt")
    y += 45
    draw.text((ml + content_w, y), "Authorised Signatory", fill=(0, 0, 0), font=font_italic, anchor="rt")

    img.save(output_path, "PNG")
    return output_path

if __name__ == "__main__":
    sample = {
        "order_id": 42,
        "order_date": "2026-08-20",
        "payment_method": "Cash",
        "name": "John Doe",
        "phone": "9876543210",
        "place": "Pala",
        "address": "Main Street, Pala",
        "items": [
            {"cloth_type": "Shirt", "quantity": 2, "price_per_unit": 20.0, "subtotal": 40.0, "item_notes": ""},
            {"cloth_type": "Saree", "quantity": 1, "price_per_unit": 80.0, "subtotal": 80.0, "item_notes": "silk care"}
        ],
        "total_amount": 120.0
    }
    path = generate_dispatch_challan_image(sample)
    print("Generated A5 Challan Image:", path)
