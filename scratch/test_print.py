import sys
import os
import win32print
import win32api
import subprocess

def test_printers():
    default_printer = win32print.GetDefaultPrinter()
    print(f"Default printer: {default_printer}")
    
    printers = [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
    print(f"Available printers: {printers}")

if __name__ == "__main__":
    test_printers()
