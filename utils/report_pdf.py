"""
utils/report_pdf.py — Date-range report PDF generator for ÉTOFFE LAUNDRY STUDIO
Creates an A4 landscape PDF with an Excel-like table of orders.
"""
import os
import tempfile
from datetime import datetime

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


def generate_date_report(rows: list, from_date: str, to_date: str, output_path: str = None) -> str:
    """
    Generate a tabular PDF report of orders between from_date and to_date.
    rows: list of dicts with keys: order_id, order_date, name, phone, total_amount, status, payment_method
    Returns path to the generated PDF.
    """
    if output_path is None:
        tmp = tempfile.gettempdir()
        output_path = os.path.join(tmp, f"victory_report_{from_date}_to_{to_date}.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        rightMargin=15 * mm, leftMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )

    # Styles
    title_style = ParagraphStyle(
        "title", fontSize=16, fontName="Helvetica-Bold",
        alignment=TA_CENTER, textColor=colors.black, spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        "subtitle", fontSize=10, fontName="Helvetica",
        alignment=TA_CENTER, textColor=colors.black, spaceAfter=8
    )
    footer_style = ParagraphStyle(
        "footer", fontSize=9, fontName="Helvetica",
        alignment=TA_LEFT, textColor=colors.black
    )

    story = []

    # Title
    story.append(Paragraph("ÉTOFFE LAUNDRY STUDIO — Order Report", title_style))

    # Date range display
    try:
        fd = datetime.strptime(from_date, "%Y-%m-%d").strftime("%d-%m-%Y")
        td = datetime.strptime(to_date, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        fd, td = from_date, to_date

    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    story.append(Paragraph(f"Period: {fd}  to  {td}    |    Generated: {now}", subtitle_style))
    story.append(Spacer(1, 4 * mm))

    # Table header
    header = ["S.No", "Order #", "Date", "Customer", "Phone", "Total (₹)", "Status", "Payment"]
    table_data = [header]

    for i, row in enumerate(rows, start=1):
        # Format date
        od = row.get("order_date", "")
        try:
            od = datetime.strptime(od, "%Y-%m-%d").strftime("%d-%m-%Y")
        except Exception:
            pass

        table_data.append([
            str(i),
            f"#{row.get('order_id', '')}",
            od,
            row.get("name", ""),
            row.get("phone", ""),
            f"₹{row.get('total_amount', 0):.2f}",
            row.get("status", ""),
            row.get("payment_method", "") or "—",
        ])

    # Summary row
    total_revenue = sum(r.get("total_amount", 0) for r in rows)
    table_data.append([
        "", "", "", "", f"Total Orders: {len(rows)}",
        f"₹{total_revenue:,.2f}", "", ""
    ])

    # Column widths (landscape A4 ~ 277mm usable)
    col_w = [16 * mm, 22 * mm, 28 * mm, 55 * mm, 38 * mm, 32 * mm, 28 * mm, 28 * mm]
    tbl = Table(table_data, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), colors.black),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 9),
        # Data rows
        ("FONTSIZE",   (0, 1), (-1, -2), 8.5),
        ("FONTNAME",   (0, 1), (-1, -2), "Helvetica"),
        ("TEXTCOLOR",  (0, 1), (-1, -2), colors.black),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f0f0f0")]),
        # Summary row
        ("BACKGROUND", (0, -1), (-1, -1), colors.black),
        ("TEXTCOLOR",  (0, -1), (-1, -1), colors.white),
        ("FONTNAME",   (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",   (0, -1), (-1, -1), 9),
        # Alignment
        ("ALIGN", (0, 0), (0, -1), "CENTER"),   # S.No
        ("ALIGN", (1, 0), (1, -1), "CENTER"),   # Order #
        ("ALIGN", (5, 0), (5, -1), "RIGHT"),    # Total
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        # Padding
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        # Valign
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(tbl)

    doc.build(story)
    return output_path


def open_date_report(rows: list, from_date: str, to_date: str):
    """Generate and open the report PDF with the default viewer."""
    path = generate_date_report(rows, from_date, to_date)
    os.startfile(path)


def generate_search_report(rows: list, query_desc: str, mode: str, output_path: str = None) -> str:
    """
    Generate and open a search-results PDF.
    For item_status mode, rows have: order_id, order_date, name, phone, status, cloth_type, unit_number
    For other modes, rows have the standard order dict keys.
    """
    if output_path is None:
        tmp = tempfile.gettempdir()
        safe = "".join(c if c.isalnum() or c in "._- " else "_" for c in query_desc)[:40]
        output_path = os.path.join(tmp, f"victory_search_{safe}.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        rightMargin=15 * mm, leftMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )

    title_style = ParagraphStyle(
        "title", fontSize=16, fontName="Helvetica-Bold",
        alignment=TA_CENTER, textColor=colors.black, spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        "subtitle", fontSize=10, fontName="Helvetica",
        alignment=TA_CENTER, textColor=colors.black, spaceAfter=8
    )

    story = []
    story.append(Paragraph("ÉTOFFE LAUNDRY STUDIO — Search Results", title_style))
    now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    story.append(Paragraph(f"Search: {query_desc}    |    Generated: {now}", subtitle_style))
    story.append(Spacer(1, 4 * mm))

    if mode == "item_status":
        header = ["S.No", "Order #", "Date", "Customer", "Item / Cloth Type", "Unit #"]
        col_w = [13*mm, 20*mm, 26*mm, 85*mm, 95*mm, 22*mm]
        table_data = [header]
        for i, row in enumerate(rows, start=1):
            od = row.get("order_date", "")
            try:
                od = datetime.strptime(od, "%Y-%m-%d").strftime("%d-%m-%Y")
            except Exception:
                pass
            table_data.append([
                str(i),
                f"#{row.get('order_id', '')}",
                od,
                row.get("name", ""),
                row.get("cloth_type", ""),
                f"Unit #{row.get('unit_number', '')}",
            ])
        table_data.append(["", "", "", "", f"Total: {len(rows)}", ""])
    else:
        header = ["S.No", "Order #", "Date", "Customer", "Phone", "Total (₹)", "Status", "Payment"]
        col_w = [13*mm, 20*mm, 26*mm, 55*mm, 36*mm, 30*mm, 28*mm, 28*mm]
        table_data = [header]
        for i, row in enumerate(rows, start=1):
            od = row.get("order_date", "")
            try:
                od = datetime.strptime(od, "%Y-%m-%d").strftime("%d-%m-%Y")
            except Exception:
                pass
            table_data.append([
                str(i),
                f"#{row.get('order_id', '')}",
                od,
                row.get("name", ""),
                row.get("phone", ""),
                f"\u20b9{row.get('total_amount', 0):.2f}",
                row.get("status", ""),
                row.get("payment_method", "") or "\u2014",
            ])
        total_revenue = sum(r.get("total_amount", 0) for r in rows)
        table_data.append(["", "", "", "", f"Total Orders: {len(rows)}", f"\u20b9{total_revenue:,.2f}", "", ""])

    tbl = Table(table_data, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.black),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 9),
        ("FONTSIZE",   (0, 1), (-1, -2), 8.5),
        ("FONTNAME",   (0, 1), (-1, -2), "Helvetica"),
        ("TEXTCOLOR",  (0, 1), (-1, -2), colors.black),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f0f0f0")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.black),
        ("TEXTCOLOR",  (0, -1), (-1, -1), colors.white),
        ("FONTNAME",   (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",   (0, -1), (-1, -1), 9),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(tbl)
    doc.build(story)
    os.startfile(output_path)
    return output_path
