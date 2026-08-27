"""
utils/dispatch_slip.py — PDF dispatch slip generator for ÉTOFFE LAUNDRY STUDIO

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

BRANCH_NAME = "ÉTOFFE LAUNDRY STUDIO"

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
        *  ÉTOFFE LAUNDRY STUDIO
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
    FV, ST = "Helvetica-Bold", 10

    def row(value: str) -> None:
        nonlocal y
        y -= 3.2 * mm
        if y < MARGIN:          # safety: stop if we'd go below bottom margin
            return
        c.setFont(FV, ST)
        c.drawString(left, y, _fit(value, FV, ST, USABLE))

    row(cust_name)
    row(item_desc)


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


def _fit_image_text(draw, text: str, font, max_w: int) -> str:
    """Return text truncated with '…' to fit within max_w pixels."""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    if text_w <= max_w:
        return text
    while text:
        candidate = text + "…"
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_w:
            return candidate
        text = text[:-1]
    return "…"


def generate_dispatch_slip_images(order_data: dict) -> list[str]:
    """Generate PNG images (one per garment) for direct GDI printing without opening PDF viewers."""
    from PIL import Image, ImageDraw, ImageFont

    order_id       = order_data.get("order_id", 0)
    items          = order_data.get("items", [])
    total_garments = sum(max(1, int(i.get("quantity", 1))) for i in items) or 1
    cust_name      = order_data.get("name", "—")
    order_notes    = order_data.get("notes", "").strip()

    garment_counter = 0
    image_paths     = []
    code128_class   = barcode.get_barcode_class("code128")

    try:
        import database as db
        lsize = db.get_setting("barcode_label_size", "35x40mm")
    except Exception:
        lsize = "35x40mm"

    if lsize == "50x30mm":
        w, h = 590, 354
    elif lsize == "40x30mm":
        w, h = 472, 354
    elif lsize == "38x25mm":
        w, h = 448, 295
    else:
        # Default 35mm x 40mm
        w, h = 413, 472

    scale = min(1.0, h / 450.0)
    s_title = max(18, int(24 * scale))
    s_bold  = max(26, int(34 * scale))
    s_code  = max(26, int(34 * scale))
    s_rmk   = max(18, int(24 * scale))

    try:
        font_title = ImageFont.truetype("arialbd.ttf", s_title)
        font_bold  = ImageFont.truetype("arialbd.ttf", s_bold)
        font_norm  = ImageFont.truetype("arialbd.ttf", s_rmk)
        font_code  = ImageFont.truetype("arialbd.ttf", s_code)
    except Exception:
        font_title = ImageFont.load_default()
        font_bold  = font_title
        font_norm  = font_title
        font_code  = font_title

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

            img = Image.new("RGB", (w, h), (255, 255, 255))
            draw = ImageDraw.Draw(img)

            # Header
            pad_top = int(22 * scale)
            draw.text((w // 2, pad_top), BRANCH_NAME, fill=(0, 0, 0), font=font_title, anchor="mm")
            line1_y = pad_top + int(16 * scale)
            draw.line([(25, line1_y), (w - 25, line1_y)], fill=(0, 0, 0), width=2)

            # Barcode
            rv = io.BytesIO()
            bc = code128_class(ref_code, writer=ImageWriter())
            bc.write(rv, options={"write_text": False, "module_height": 7.0, "module_width": 0.35, "quiet_zone": 1.0})
            rv.seek(0)
            bc_img = Image.open(rv)

            target_bc_w = w - 60
            target_bc_h = int(105 * scale)
            bc_resized = bc_img.resize((target_bc_w, target_bc_h), Image.Resampling.LANCZOS)
            bc_y = line1_y + int(8 * scale)
            img.paste(bc_resized, ((w - target_bc_w) // 2, bc_y))

            # Ref Code
            ref_y = bc_y + target_bc_h + int(16 * scale)
            draw.text((w // 2, ref_y), ref_code, fill=(0, 0, 0), font=font_code, anchor="mm")
            line2_y = ref_y + int(18 * scale)
            draw.line([(25, line2_y), (w - 25, line2_y)], fill=(0, 0, 0), width=2)

            # Details
            margin_x = 30
            max_text_w = w - (2 * margin_x)
            y_pos = line2_y + int(14 * scale)

            cust_line = _fit_image_text(draw, cust_name, font_bold, max_text_w)
            draw.text((margin_x, y_pos), cust_line, fill=(0, 0, 0), font=font_bold)
            y_pos += int(36 * scale)

            item_line = _fit_image_text(draw, item_desc, font_bold, max_text_w)
            draw.text((margin_x, y_pos), item_line, fill=(0, 0, 0), font=font_bold)

            out_file = os.path.join(tempfile.gettempdir(), f"victory_dispatch_slip_order_{order_id}_{garment_counter}.png")
            img.save(out_file, "PNG", dpi=(300, 300))
            image_paths.append(out_file)

    return image_paths


def open_dispatch_slip(order_data: dict) -> str:
    """Generate and print or preview the dispatch slip based on print_mode setting."""
    try:
        import database as db
        print_mode = db.get_setting("print_mode", "direct")
        dispatch_printer = db.get_setting("printer_dispatch", "") or db.get_setting("printer_receipt", "")
    except Exception:
        print_mode = "direct"
        dispatch_printer = ""

    if print_mode == "preview":
        path = generate_dispatch_slip(order_data)
        if hasattr(os, "startfile"):
            os.startfile(path)
        else:
            import subprocess, sys
            cmd = ["open", path] if sys.platform == "darwin" else ["xdg-open", path]
            subprocess.run(cmd, check=False)
        return path
    else:
        from utils.receipt import silent_print_image
        image_paths = generate_dispatch_slip_images(order_data)
        for img_path in image_paths:
            silent_print_image(img_path, printer_name=dispatch_printer)
        return image_paths[0] if image_paths else ""

