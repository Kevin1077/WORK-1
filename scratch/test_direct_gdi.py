import os
import sys
import win32print
import win32ui
import win32con
from PIL import Image, ImageWin, ImageDraw, ImageFont

def silent_print_pil_image(img: Image.Image, printer_name: str = None, doc_name: str = "Victory Print Job") -> bool:
    """Send a PIL Image directly to a Windows Printer DC via GDI. 100% silent, no viewer window."""
    if not printer_name or printer_name == "(System Default Printer)":
        printer_name = win32print.GetDefaultPrinter()

    print(f"Sending silent print job to printer: '{printer_name}'...")

    try:
        hDC = win32ui.CreateDC()
        hDC.CreatePrinterDC(printer_name)

        printable_w = hDC.GetDeviceCaps(win32con.HORZRES)
        printable_h = hDC.GetDeviceCaps(win32con.VERTRES)

        hDC.StartDoc(doc_name)
        hDC.StartPage()

        dib = ImageWin.Dib(img)
        img_w, img_h = img.size

        # Fit image to printable area keeping aspect ratio
        scale = min(printable_w / img_w, printable_h / img_h)
        target_w = int(img_w * scale)
        target_h = int(img_h * scale)

        dib.draw(hDC.GetHandleOutput(), (0, 0, target_w, target_h))

        hDC.EndPage()
        hDC.EndDoc()
        hDC.DeleteDC()
        print("Success! Print job sent silently.")
        return True
    except Exception as e:
        print(f"Error printing PIL image directly via GDI: {e}")
        return False

if __name__ == "__main__":
    printer = win32print.GetDefaultPrinter()
    print(f"Default printer: {printer}")
