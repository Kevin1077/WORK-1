import win32print
import win32ui
import win32con
from PIL import Image, ImageWin, ImageDraw, ImageFont

def test_gdi():
    printer_name = win32print.GetDefaultPrinter()
    print("Testing GDI print to printer:", printer_name)
    
    # Create dummy image
    img = Image.new("RGB", (400, 300), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 390, 290], outline=(0, 0, 0), width=2)
    draw.text((30, 50), "Test Silent Print", fill=(0, 0, 0))
    
    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)
    
    printable_width = hDC.GetDeviceCaps(win32con.HORZRES)
    printable_height = hDC.GetDeviceCaps(win32con.VERTRES)
    print(f"Printable dimensions: {printable_width} x {printable_height}")
    
    hDC.StartDoc("Test Job")
    hDC.StartPage()
    
    dib = ImageWin.Dib(img)
    img_w, img_h = img.size
    scale = min(printable_width / img_w, printable_height / img_h)
    target_w = int(img_w * scale)
    target_h = int(img_h * scale)
    
    dib.draw(hDC.GetHandleOutput(), (0, 0, target_w, target_h))
    
    hDC.EndPage()
    hDC.EndDoc()
    hDC.DeleteDC()
    print("Print job sent successfully!")

if __name__ == "__main__":
    test_gdi()
