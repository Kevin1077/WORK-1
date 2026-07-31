"""
utils/receipt.py — PDF receipt generator for Victory Laundry
Uses reportlab to create an A5-sized receipt PDF.
Black and white only — no colours.
"""
import os
import tempfile

from reportlab.lib.pagesizes import A5
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

SHOP_NAME = "Victory Laundry"
SHOP_TAGLINE = "Professional Laundry Services"

# ── Paragraph Styles ───────────────────────────────────────────────────────────

def _styles():
    return {
        "title": ParagraphStyle(
            "title", fontSize=20, leading=24, fontName="Helvetica-Bold",
            alignment=TA_CENTER, textColor=colors.black, spaceAfter=4
        ),
        "tagline": ParagraphStyle(
            "tagline", fontSize=9, leading=12, fontName="Helvetica-Oblique",
            alignment=TA_CENTER, textColor=colors.black, spaceAfter=8
        ),
        "section": ParagraphStyle(
            "section", fontSize=9.5, leading=13, fontName="Helvetica-Bold",
            textColor=colors.black, spaceBefore=4, spaceAfter=3
        ),
        "normal": ParagraphStyle(
            "normal", fontSize=8.5, leading=13, fontName="Helvetica",
            textColor=colors.black
        ),
        "footer": ParagraphStyle(
            "footer", fontSize=8, leading=11, fontName="Helvetica-Oblique",
            alignment=TA_CENTER, textColor=colors.black
        ),
        "total_label": ParagraphStyle(
            "total_label", fontSize=10, leading=13, fontName="Helvetica-Bold",
            alignment=TA_RIGHT, textColor=colors.black
        ),
    }


def _hr():
    return HRFlowable(width="100%", thickness=0.5, color=colors.black, spaceAfter=3)


def _thick_hr():
    return HRFlowable(width="100%", thickness=1.5, color=colors.black, spaceAfter=4)


# ── Main generator ─────────────────────────────────────────────────────────────

def generate_receipt(order_data: dict, output_path: str = None) -> str:
    """
    Generate a PDF receipt for the given order_data dict.
    Returns the path to the generated PDF.
    """
    if output_path is None:
        tmp = tempfile.gettempdir()
        output_path = os.path.join(
            tmp, f"victory_receipt_order_{order_data['order_id']}.pdf"
        )

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A5,
        rightMargin=14 * mm, leftMargin=14 * mm,
        topMargin=14 * mm,  bottomMargin=14 * mm,
    )

    st = _styles()
    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph(SHOP_NAME, st["title"]))
    story.append(Spacer(1, 1 * mm))
    story.append(Paragraph(SHOP_TAGLINE, st["tagline"]))
    story.append(Spacer(1, 2 * mm))
    story.append(_thick_hr())

    # ── Order Details ─────────────────────────────────────────────────────────
    order_date = order_data.get("order_date", "")
    try:
        from datetime import datetime
        order_date = datetime.strptime(order_date, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        pass

    payment = order_data.get("payment_method", "") or "—"

    story.append(Paragraph("Order Details", st["section"]))
    story.append(Paragraph(f"Order #: {order_data['order_id']}", st["normal"]))
    story.append(Paragraph(f"Date   : {order_date}", st["normal"]))
    story.append(Paragraph(f"Payment: {payment}", st["normal"]))
    story.append(Spacer(1, 3 * mm))
    story.append(_hr())

    # ── Customer Details ──────────────────────────────────────────────────────
    story.append(Paragraph("Customer Details", st["section"]))
    story.append(Paragraph(f"Name   : {order_data.get('name','')}", st["normal"]))
    story.append(Paragraph(f"Phone  : {order_data.get('phone','')}", st["normal"]))
    if order_data.get("place"):
        story.append(Paragraph(f"Place  : {order_data['place']}", st["normal"]))
    if order_data.get("address"):
        story.append(Paragraph(f"Address: {order_data['address']}", st["normal"]))
    story.append(Spacer(1, 3 * mm))
    story.append(_hr())

    # ── Items table ───────────────────────────────────────────────────────────
    story.append(Paragraph("Order Items", st["section"]))
    story.append(Spacer(1, 1 * mm))

    header = ["S.No", "Item", "Qty", "Rate", "Total"]
    rows = [header]
    for i, item in enumerate(order_data.get("items", []), start=1):
        item_num = item.get("item_number", i)
        rows.append([
            str(item_num),
            item["cloth_type"],
            str(item["quantity"]),
            f"{item['price_per_unit']:.2f}",
            f"{item['subtotal']:.2f}",
        ])
    # Grand total row
    rows.append(["", "", "", "GRAND TOTAL", f"{order_data.get('total_amount', 0):.2f}"])

    # Total usable width on A5 with 14mm margins on both sides: 148mm - 28mm = 120mm
    col_w = [14 * mm, 42 * mm, 16 * mm, 24 * mm, 24 * mm]
    tbl = Table(rows, colWidths=col_w, hAlign='LEFT')
    tbl.setStyle(TableStyle([
        # Header row — black bg, white text
        ("BACKGROUND", (0, 0), (-1, 0), colors.black),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 8.5),
        # Data rows — white bg
        ("BACKGROUND", (0, 1), (-1, -2), colors.white),
        ("TEXTCOLOR",  (0, 1), (-1, -2), colors.black),
        # Grand total row — black bg, white text
        ("BACKGROUND", (0, -1), (-1, -1), colors.black),
        ("TEXTCOLOR",  (0, -1), (-1, -1), colors.white),
        ("FONTNAME",   (0, -1), (-1, -1), "Helvetica-Bold"),
        # Alignment
        ("ALIGN",  (0, 0), (0, -1), "CENTER"),   # S.No
        ("ALIGN",  (2, 0), (2, -1), "CENTER"),   # Qty
        ("ALIGN",  (3, 0), (-1, -1), "RIGHT"),   # Rate, Total
        ("ALIGN",  (-2, -1), (-2, -1), "RIGHT"), # GRAND TOTAL label
        # Grid
        ("GRID",      (0, 0), (-1, -2), 0.4, colors.black),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        # Padding
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 4 * mm))

    # ── Notes ─────────────────────────────────────────────────────────────────
    if order_data.get("notes"):
        story.append(_hr())
        story.append(Paragraph(
            f"<i>Notes: {order_data['notes']}</i>", st["normal"]
        ))
        story.append(Spacer(1, 3 * mm))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(_thick_hr())
    story.append(Paragraph(
        "Thank you for choosing Victory Laundry!", st["footer"]
    ))

    doc.build(story)
    return output_path


def open_receipt(order_data: dict):
    """Generate and open the receipt PDF with the default viewer."""
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


def send_whatsapp_receipt(order_data: dict, parent_window=None) -> str | None:
    """
    Generate the normal receipt PDF, then prepare a WhatsApp Desktop chat.
    Staff attach the already-open PDF manually, avoiding brittle browser automation.
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
            parent=parent_window
        )
        return None

    # Reuse the application's established receipt generator; no separate PDF
    # layout or WhatsApp-specific receipt is created.
    pdf_path = generate_receipt(order_data)

    # 3. Format receipt message
    order_date = order_data.get("order_date", "")
    try:
        from datetime import datetime
        order_date = datetime.strptime(order_date, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        pass

    items_list = []
    for item in order_data.get("items", []):
        items_list.append(f" • {item['cloth_type']} (x{item['quantity']}) - ₹{item['subtotal']:.2f}")
    items_str = "\n".join(items_list) if items_list else " —"

    caption = (
        f"🧺 *Victory Laundry — Order Receipt*\n\n"
        f"*Order #:* #{order_data['order_id']}\n"
        f"*Date:* {order_date}\n"
        f"*Customer:* {order_data.get('name', '')}\n"
        f"*Status:* {order_data.get('status', 'Received')}\n\n"
        f"*Items Purchased:*\n{items_str}\n\n"
        f"*Grand Total:* ₹{order_data.get('total_amount', 0):.2f}\n"
        f"*Payment Method:* {order_data.get('payment_method', '') or '—'}\n\n"
        f"Thank you for choosing Victory Laundry!"
    )

    _open_whatsapp_receipt_manual(digits, caption, pdf_path, parent_window)
    return pdf_path


def send_whatsapp_ready_notification(order_data: dict, parent_window=None) -> bool:
    """Prepare a WhatsApp Desktop ready-order notification for staff to send."""
    from tkinter import messagebox

    try:
        digits = normalize_whatsapp_phone(order_data.get("phone"))
    except ValueError as exc:
        messagebox.showerror("WhatsApp Error", str(exc), parent=parent_window)
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
        parent=parent_window,
    ):
        return False
    return send_whatsapp_ready_notification(order_data, parent_window)


def _open_whatsapp_receipt_manual(digits: str, caption: str, pdf_path: str, parent_window=None):
    """Prepare a receipt in WhatsApp Desktop without sending it automatically."""
    from tkinter import messagebox
    try:
        from whatsapp_desktop import send_receipt
        send_receipt(digits, pdf_path, caption)
    except Exception as exc:
        messagebox.showerror("WhatsApp Desktop Error", str(exc), parent=parent_window)
        return
    messagebox.showinfo(
        "WhatsApp Receipt Ready",
        "The receipt PDF and message are ready in WhatsApp Desktop. Review them and press Send.",
        parent=parent_window,
    )


def _open_whatsapp_text_manual(digits: str, message: str, parent_window=None):
    """Prepare a ready-order notification in WhatsApp Desktop."""
    from tkinter import messagebox
    try:
        from whatsapp_desktop import prepare_message
        prepare_message(digits, message)
    except Exception as exc:
        messagebox.showerror("WhatsApp Desktop Error", str(exc), parent=parent_window)
        return
    messagebox.showinfo(
        "WhatsApp Notification Ready",
        "The ready-order notification is prepared in WhatsApp Desktop. Review it and press Send.",
        parent=parent_window,
    )
