"""
utils/dispatch_slip.py — PDF dispatch slip generator for Victory Drycleaners
Generates tag-sized (101.6mm x 101.6mm / 4in x 4in) PDF slips for physical garments with Code128 barcodes,
matching the die-cut label stock configured on the Honeywell IH-2 printer.
1 slip per individual garment.
"""
import os
import tempfile
import io
import barcode
from barcode.writer import ImageWriter

from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, HRFlowable, PageBreak
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

BRANCH_NAME = "Victory Drycleaners - Pala"


def _styles():
    return {
        "header": ParagraphStyle(
            "hdr", fontSize=10, leading=12, fontName="Helvetica-Bold",
            alignment=TA_CENTER, textColor=colors.black
        ),
        "ref_code": ParagraphStyle(
            "ref", fontSize=10, leading=12, fontName="Helvetica-Bold",
            alignment=TA_CENTER, textColor=colors.black
        ),
        "label": ParagraphStyle(
            "lbl", fontSize=8.5, leading=11, fontName="Helvetica-Bold",
            textColor=colors.black
        ),
        "value": ParagraphStyle(
            "val", fontSize=8.5, leading=11, fontName="Helvetica",
            textColor=colors.black
        ),
        "remarks": ParagraphStyle(
            "rem", fontSize=8, leading=10, fontName="Helvetica-BoldOblique",
            textColor=colors.black
        ),
    }


def generate_dispatch_slip(order_data: dict, output_path: str = None) -> str:
    """
    Generate a PDF containing 1 dispatch slip page per garment in the order.
    Returns the path to the generated PDF file.
    """
    order_id = order_data.get("order_id", 0)
    if output_path is None:
        tmp = tempfile.gettempdir()
        output_path = os.path.join(
            tmp, f"victory_dispatch_slips_order_{order_id}.pdf"
        )

    # Label size: 101.6mm x 101.6mm (4in x 4in die-cut label stock, per printer driver "Edit Stock" settings)
    page_width = 101.6 * mm
    page_height = 101.6 * mm
    # Keep margin comfortably inside the 1.3mm exposed liner on each side so nothing gets clipped
    margin = 4 * mm

    doc = SimpleDocTemplate(
        output_path,
        pagesize=(page_width, page_height),
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin,
    )

    st = _styles()
    story = []

    # Calculate total garments count across all items
    items = order_data.get("items", [])
    total_garments = sum(max(1, int(item.get("quantity", 1))) for item in items)
    if total_garments == 0:
        total_garments = 1

    cust_name = order_data.get("name", "—")
    order_notes = order_data.get("notes", "").strip()

    garment_counter = 0
    temp_files = []

    try:
        code128_class = barcode.get_barcode_class("code128")

        for item_idx, item in enumerate(items, start=1):
            cloth_type = item.get("cloth_type", "Garment")
            qty = max(1, int(item.get("quantity", 1)))
            item_notes = item.get("item_notes", "").strip()
            notes_text = item_notes or order_notes

            for garment_sub_idx in range(1, qty + 1):
                garment_counter += 1
                ref_code = f"P{order_id}-{garment_counter}"

                # Generate Code128 barcode image
                rv = io.BytesIO()
                # Disable text under barcode from python-barcode since we render clean text flowable below
                bc = code128_class(ref_code, writer=ImageWriter())
                bc.write(rv, options={"write_text": False, "module_height": 8.0, "module_width": 0.25, "quiet_zone": 2.0})
                rv.seek(0)

                tf = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                tf.write(rv.getvalue())
                tf.close()
                temp_files.append(tf.name)

                # ── Header ──
                story.append(Spacer(1, 3 * mm))
                story.append(Paragraph(BRANCH_NAME, st["header"]))
                story.append(Spacer(1, 2 * mm))
                story.append(HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceAfter=2))
                story.append(Spacer(1, 3 * mm))

                # ── Barcode ──
                # Barcode Image flowable (width 70mm, height 20mm) — sized up to use the taller 101.6mm label
                img = Image(tf.name, width=70 * mm, height=20 * mm)
                img.hAlign = "CENTER"
                story.append(img)
                story.append(Spacer(1, 2 * mm))

                # Reference Code text below barcode
                story.append(Paragraph(ref_code, st["ref_code"]))
                story.append(Spacer(1, 3 * mm))
                story.append(HRFlowable(width="100%", thickness=0.4, color=colors.black, spaceAfter=2))
                story.append(Spacer(1, 3 * mm))

                # ── Garment & Customer Info ──
                item_desc = f"{cloth_type}"
                if qty > 1:
                    item_desc += f" ({garment_sub_idx}/{qty})"
                else:
                    item_desc += f" ({garment_counter}/{total_garments})"

                story.append(Paragraph(f"<b>Cust:</b> {cust_name}", st["value"]))
                story.append(Spacer(1, 1.5 * mm))
                story.append(Paragraph(f"<b>Item:</b> {item_desc}", st["value"]))

                if notes_text:
                    story.append(Spacer(1, 1.5 * mm))
                    story.append(Paragraph(f"<b>Remarks:</b> {notes_text}", st["remarks"]))

                # Page break between garments
                if garment_counter < total_garments:
                    story.append(PageBreak())

        doc.build(story)
    finally:
        # Clean up temporary barcode images
        for tmp_img in temp_files:
            try:
                if os.path.exists(tmp_img):
                    os.remove(tmp_img)
            except Exception:
                pass

    return output_path


def open_dispatch_slip(order_data: dict):
    """Generate and open the dispatch slip PDF with the default system viewer."""
    path = generate_dispatch_slip(order_data)
    os.startfile(path)