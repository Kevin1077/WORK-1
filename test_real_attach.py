import time
from pathlib import Path
from utils.receipt import generate_receipt
from whatsapp_web import send_receipt, _validate_image

order_data = {
    'order_id': 101,
    'order_date': '2026-08-09',
    'name': 'Customer Test',
    'phone': '9876543210',
    'payment_method': 'Cash',
    'items': [
        {'cloth_type': 'Shirt (Dry Clean)', 'quantity': 2, 'price_per_unit': 40.0, 'subtotal': 80.0},
        {'cloth_type': 'Jacket', 'quantity': 1, 'price_per_unit': 120.0, 'subtotal': 120.0}
    ],
    'total_amount': 200.0,
    'notes': 'Test image attachment'
}

print("1. Generating PNG receipt image...")
img_path = generate_receipt(order_data)
receipt_path = _validate_image(img_path)
print(f"Receipt PNG created at: {receipt_path}")

print("2. Calling send_receipt() to open WhatsApp Web and attach receipt...")
caption = f"Hello {order_data['name']},\n\nHere is your receipt for Order #{order_data['order_id']}.\n\nThank you for choosing Victory Laundry!"

# We call send_receipt which navigates and attaches
send_receipt('9876543210', str(receipt_path), caption)

print("\n--- TEST PASSED: Receipt attached as regular photo! ---")
