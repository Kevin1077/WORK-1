"""
utils/dispatch_slip.py — PDF dispatch slip generator for Victory Drycleaners

Label: 3.5cm wide × 4cm tall  →  PORTRAIT  (35mm × 40mm)
PDF page matches label exactly. All content is drawn at absolute coordinates
so it is guaranteed to fit on a single label with no overflow.
1 slip per garment.
"""
import os
import tempfile
import io
import barcode
from barcode.writer import ImageWriter

from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth

BRANCH_NAME = "Victory Drycleaners - Pala"

# ── Label: 3.5 cm wide × 4 cm tall (portrait) ────────────────────────────────
PAGE_W = 43.8 * mm    # 3.5 cm  ← width
PAGE_H = 43.8 * mm    # 4.0 cm  ← height (taller than wide = portrait)
MARGIN = 3  * mm    # safe non-printable zone on all four edges
USABLE = PAGE_W - 2 * MARGIN   # 29 mm usable width
# ─────────────────────────────────────────────────────────────────────────────


def _fit(text: str, font: str, size: float, max_w: float) -> str:
    """Return text truncated with '…' to fit within max_w points."""
    if stringWidth(text, font, size) <= max_w:
        return text
    while text:
        candidate = text + "…"
        if stringWidth(candidate, font, size) <= max_w:
            return candidate
        text = text[:-1]
    return "…"


def _draw_slip(c: canvas.Canvas,
               ref_code: str,
               cust_name: str,
               item_desc: str,
               notes_text: str,
               barcode_path: str) -> None:
    """
    Draw one complete dispatch slip.
    Coordinate origin = bottom-left, y increases upward.

    Portrait layout (* denotes centred):
        *  Victory Drycleaners - Pala
        ──────────────────────────────
        *        [BARCODE]
        *      P{id}-{n}
        ──────────────────────────────
           Cust: <name>
           Item: <type (n/total)>
           Rmk:  <note>   (if present)
    """
    cx   = PAGE_W / 2          # horizontal centre
    left = MARGIN

    # ── start y cursor at top-inside-margin ──────────────────────────────
    y = PAGE_H - MARGIN

    # Branch name ─────────────────────────────────────────────────────────
    FHB, SHB = "Helvetica-Bold", 9
    y -= 3.5 * mm
    c.setFont(FHB, SHB)
    c.drawCentredString(cx, y, _fit(BRANCH_NAME, FHB, SHB, USABLE))

    # HR ──────────────────────────────────────────────────────────────────
    y -= 2 * mm
    c.setLineWidth(0.6)
    c.line(left, y, PAGE_W - left, y)

    # Barcode (width ≤ USABLE, height compact) ────────────────────────────
    bar_w = USABLE - 1 * mm    # 28 mm
    bar_h = 12 * mm
    y -= 1 * mm + bar_h        # top of barcode slot (y = barcode bottom)
    c.drawImage(barcode_path,
                (PAGE_W - bar_w) / 2, y,
                width=bar_w, height=bar_h,
                preserveAspectRatio=False)

    # Ref code ────────────────────────────────────────────────────────────
    FRB, SRB = "Helvetica-Bold", 10
    y -= 3.5 * mm
    c.setFont(FRB, SRB)
    c.drawCentredString(cx, y, _fit(ref_code, FRB, SRB, USABLE))

    # HR ──────────────────────────────────────────────────────────────────
    y -= 2 * mm
    c.setLineWidth(0.4)
    c.line(left, y, PAGE_W - left, y)

    # Text fields ─────────────────────────────────────────────────────────
    FB, FV, ST = "Helvetica-Bold", "Helvetica-Bold", 10
    pfx_w = stringWidth("Cust: ", FB, ST)   # same width for all labels
    val_w = USABLE - pfx_w

    def row(label: str, value: str, italic: bool = False) -> None:
        nonlocal y
        vfont = "Helvetica-BoldOblique" if italic else FV
        y -= 3.2 * mm
        if y < MARGIN:          # safety: stop if we'd go below bottom margin
            return
        c.setFont(FB, ST)
        c.drawString(left, y, label)
        c.setFont(vfont, ST)
        c.drawString(left + pfx_w, y, _fit(value, vfont, ST, val_w))

    row("Cust: ", cust_name)
    row("Item: ", item_desc)
    if notes_text:
        row("Rmk:  ", notes_text, italic=True)


def generate_dispatch_slip(order_data: dict, output_path: str = None) -> str:
    """Generate a PDF with one dispatch slip page per garment."""
    order_id = order_data.get("order_id", 0)
    if output_path is None:
        output_path = os.path.join(
            tempfile.gettempdir(),
            f"victory_dispatch_slips_order_{order_id}.pdf"
        )

    items          = order_data.get("items", [])
    total_garments = sum(max(1, int(i.get("quantity", 1))) for i in items) or 1
    cust_name      = order_data.get("name", "—")
    order_notes    = order_data.get("notes", "").strip()

    garment_counter = 0
    temp_files      = []

    c = canvas.Canvas(output_path, pagesize=(PAGE_W, PAGE_H))

    try:
        code128_class = barcode.get_barcode_class("code128")

        for item in items:
            cloth_type = item.get("cloth_type", "Garment")
            qty        = max(1, int(item.get("quantity", 1)))
            notes_text = item.get("item_notes", "").strip() or order_notes

            for sub in range(1, qty + 1):
                garment_counter += 1
                ref_code  = f"P{order_id}-{garment_counter}"
                item_desc = cloth_type + (
                    f" ({sub}/{qty})" if qty > 1
                    else f" ({garment_counter}/{total_garments})"
                )

                # barcode PNG
                rv = io.BytesIO()
                bc = code128_class(ref_code, writer=ImageWriter())
                bc.write(rv, options={
                    "write_text":    False,
                    "module_height": 6.0,
                    "module_width":  0.2,
                    "quiet_zone":    1.5,
                })
                rv.seek(0)

                tf = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                tf.write(rv.getvalue())
                tf.close()
                temp_files.append(tf.name)

                _draw_slip(c, ref_code, cust_name, item_desc,
                           notes_text, tf.name)
                c.showPage()      # each garment = one label

        c.save()

    finally:
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass

    return output_path


def open_dispatch_slip(order_data: dict) -> None:
    """Generate and silently print the dispatch slip PDF to the default printer."""
    from utils.receipt import silent_print_pdf
    silent_print_pdf(generate_dispatch_slip(order_data))