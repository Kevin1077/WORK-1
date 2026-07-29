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
            "title", fontSize=20, fontName="Helvetica-Bold",
            alignment=TA_CENTER, textColor=colors.black, spaceAfter=2
        ),
        "tagline": ParagraphStyle(
            "tagline", fontSize=9, fontName="Helvetica-Oblique",
            alignment=TA_CENTER, textColor=colors.black, spaceAfter=6
        ),
        "section": ParagraphStyle(
            "section", fontSize=9, fontName="Helvetica-Bold",
            textColor=colors.black, spaceBefore=4, spaceAfter=2
        ),
        "normal": ParagraphStyle(
            "normal", fontSize=8.5, fontName="Helvetica",
            textColor=colors.black, leading=13
        ),
        "footer": ParagraphStyle(
            "footer", fontSize=8, fontName="Helvetica-Oblique",
            alignment=TA_CENTER, textColor=colors.black
        ),
        "total_label": ParagraphStyle(
            "total_label", fontSize=10, fontName="Helvetica-Bold",
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
    story.append(Paragraph(SHOP_TAGLINE, st["tagline"]))
    story.append(_thick_hr())

    # ── Order meta ────────────────────────────────────────────────────────────
    order_date = order_data.get("order_date", "")
    try:
        from datetime import datetime
        order_date = datetime.strptime(order_date, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        pass

    payment = order_data.get("payment_method", "") or "—"

    meta_data = [
        [Paragraph(f"<b>Order #: {order_data['order_id']}</b>", st["normal"]),
         Paragraph(f"<b>Date:</b> {order_date}", st["normal"])],
        [Paragraph(f"<b>Status:</b> {order_data.get('status','')}", st["normal"]),
         Paragraph(f"<b>Payment:</b> {payment}", st["normal"])],
    ]
    meta_table = Table(meta_data, colWidths=[70 * mm, 70 * mm])
    meta_table.setStyle(TableStyle([
        ("PADDING", (0, 0), (-1, -1), 2),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 3 * mm))
    story.append(_hr())

    # ── Customer ──────────────────────────────────────────────────────────────
    story.append(Paragraph("Customer Details", st["section"]))
    story.append(Paragraph(f"Name : {order_data.get('name','')}", st["normal"]))
    story.append(Paragraph(f"Phone: {order_data.get('phone','')}", st["normal"]))
    if order_data.get("place"):
        story.append(Paragraph(f"Place: {order_data['place']}", st["normal"]))
    if order_data.get("address"):
        story.append(Paragraph(f"Address: {order_data['address']}", st["normal"]))
    story.append(Spacer(1, 3 * mm))
    story.append(_hr())

    # ── Items table ───────────────────────────────────────────────────────────
    story.append(Paragraph("Order Items", st["section"]))
    story.append(Spacer(1, 1 * mm))

    header = ["S.No", "Item", "Qty", "Rate (₹)", "Total (₹)"]
    rows = [header]
    for i, item in enumerate(order_data.get("items", []), start=1):
        item_num = item.get("item_number", i)
        rows.append([
            str(item_num),
            item["cloth_type"],
            str(item["quantity"]),
            f"\u20b9{item['price_per_unit']:.2f}",
            f"\u20b9{item['subtotal']:.2f}",
        ])
    # Grand total row
    rows.append(["", "", "", "GRAND TOTAL", f"\u20b9{order_data.get('total_amount', 0):.2f}"])

    col_w = [18 * mm, 45 * mm, 18 * mm, 27 * mm, 27 * mm]
    tbl = Table(rows, colWidths=col_w)
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
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
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
