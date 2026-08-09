"""
utils/receipt.py — PNG image receipt generator for Victory Laundry
Uses Pillow (PIL) to create a clean, receipt-style PNG image.
Black and white only — no colours.
"""
import os
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

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

    # Canvas config
    img_width = 600
    margin = 35
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

    draw.text((margin, y), f"Name   : {order_data.get('name','')}", fill=fg_color, font=font_normal)
    y += 18
    draw.text((margin, y), f"Phone  : {order_data.get('phone','')}", fill=fg_color, font=font_normal)
    y += 18
    if order_data.get("place"):
        draw.text((margin, y), f"Place  : {order_data['place']}", fill=fg_color, font=font_normal)
        y += 18
    if order_data.get("address"):
        draw.text((margin, y), f"Address: {order_data['address']}", fill=fg_color, font=font_normal)
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

    img.save(output_path, "PNG")
    return output_path


def open_receipt(order_data: dict):
    """Generate and open the receipt PNG image with the default viewer."""
    path = generate_receipt(order_data)
    os.startfile(path)


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

    # Reuse the application's established receipt generator; no separate image
    # layout or WhatsApp-specific receipt is created.
    image_path = generate_receipt(order_data)

    # 3. Format simplified receipt message (detailed breakdown is in the image)
    customer_name = order_data.get("name") or "Customer"
    order_id = order_data.get("order_id", "")
    caption = (
        f"Hello {customer_name},\n\n"
        f"Here is your receipt for Order #{order_id}.\n\n"
        f"Thank you for choosing Victory Laundry😊"
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
