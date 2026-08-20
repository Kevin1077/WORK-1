import win32print
import subprocess
import json

def test_printer_enumeration():
    print("=== 1. win32print EnumPrinters test ===")
    flags = [
        ("PRINTER_ENUM_LOCAL", win32print.PRINTER_ENUM_LOCAL),
        ("PRINTER_ENUM_CONNECTIONS", win32print.PRINTER_ENUM_CONNECTIONS),
        ("PRINTER_ENUM_SHARED", win32print.PRINTER_ENUM_SHARED),
        ("PRINTER_ENUM_NETWORK", win32print.PRINTER_ENUM_NETWORK),
        ("LOCAL | CONNECTIONS", win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS),
        ("ALL", win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS | win32print.PRINTER_ENUM_NETWORK | win32print.PRINTER_ENUM_SHARED),
    ]
    for name, flag in flags:
        try:
            printers = [p[2] for p in win32print.EnumPrinters(flag)]
            print(f"{name}: {printers}")
        except Exception as e:
            print(f"{name} Error: {e}")

    print("\n=== 2. PowerShell Get-Printer ===")
    try:
        res = subprocess.run(
            ["powershell", "-Command", "Get-Printer | Select-Name Name, DriverName, PortName, PrinterStatus | ConvertTo-Json"],
            capture_output=True, text=True, check=True
        )
        print(res.stdout)
    except Exception as e:
        print("PowerShell Get-Printer Error:", e)

    print("\n=== 3. WMI Win32_Printer ===")
    try:
        res = subprocess.run(
            ["powershell", "-Command", "Get-WmiObject Win32_Printer | Select-Object Name | ConvertTo-Json"],
            capture_output=True, text=True, check=True
        )
        print(res.stdout)
    except Exception as e:
        print("WMI Error:", e)

if __name__ == "__main__":
    test_printer_enumeration()
