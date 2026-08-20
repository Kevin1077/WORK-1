import io
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont

def create_slip_image(ref_code: str, cust_name: str, item_desc: str, notes_text: str) -> Image.Image:
    # 300 DPI label canvas: 413 px wide x 472 px tall (3.5 cm x 4.0 cm)
    w, h = 413, 472
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arialbd.ttf", 22)
        font_bold = ImageFont.truetype("arialbd.ttf", 22)
        font_norm = ImageFont.truetype("arial.ttf", 20)
        font_code = ImageFont.truetype("arialbd.ttf", 26)
    except Exception:
        font_title = ImageFont.load_default()
        font_bold = font_title
        font_norm = font_title
        font_code = font_title

    # Header
    draw.text((w // 2, 20), "Victory Drycleaners - Pala", fill=(0, 0, 0), font=font_title, anchor="mm")
    draw.line([(20, 36), (w - 20, 36)], fill=(0, 0, 0), width=2)

    # Barcode
    code128_class = barcode.get_barcode_class("code128")
    rv = io.BytesIO()
    bc = code128_class(ref_code, writer=ImageWriter())
    bc.write(rv, options={"write_text": False, "module_height": 7.0, "module_width": 0.35, "quiet_zone": 1.0})
    rv.seek(0)
    bc_img = Image.open(rv)
    
    # Fit barcode image
    bc_w, bc_h = bc_img.size
    target_bc_w = w - 60
    target_bc_h = 110
    bc_resized = bc_img.resize((target_bc_w, target_bc_h), Image.Resampling.LANCZOS)
    img.paste(bc_resized, (30, 46))

    # Ref Code
    draw.text((w // 2, 172), ref_code, fill=(0, 0, 0), font=font_code, anchor="mm")
    draw.line([(20, 192), (w - 20, 192)], fill=(0, 0, 0), width=2)

    # Details
    y = 208
    draw.text((25, y), f"Cust: {cust_name[:18]}", fill=(0, 0, 0), font=font_bold)
    y += 32
    draw.text((25, y), f"Item: {item_desc[:18]}", fill=(0, 0, 0), font=font_bold)
    if notes_text:
        y += 32
        draw.text((25, y), f"Rmk: {notes_text[:18]}", fill=(0, 0, 0), font=font_norm)

    return img

if __name__ == "__main__":
    test_img = create_slip_image("P42-1", "Jane Doe", "Shirt (1/2)", "Dryclean")
    test_img.save("c:/Code/WORK-1/scratch/test_slip.png")
    print("Test dispatch slip PNG generated successfully!")
