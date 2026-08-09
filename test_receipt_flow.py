import os
import sys
from PIL import Image

import database as db
from utils.receipt import generate_receipt

print("1. Initializing DB and creating sample order...")
db.init_db()

with db.get_connection() as conn:
    row = conn.execute("SELECT customer_id FROM customers LIMIT 1").fetchone()
    cid = row['customer_id'] if row else None

if not cid:
    cid = db.create_customer('Test Customer', '9876543210', 'Central Market', 'Main St 123')

items = [
    {'cloth_type': 'Shirt (Dry Clean)', 'quantity': 2, 'price_per_unit': 40.0, 'subtotal': 80.0, 'item_notes': ''},
    {'cloth_type': 'Suit 2-Piece', 'quantity': 1, 'price_per_unit': 250.0, 'subtotal': 250.0, 'item_notes': ''}
]
oid = db.create_order(cid, '2026-08-08', 'GPay', items, notes="Handle with care")
order = db.get_order_full(oid)

print(f"Sample order #{oid} fetched.")

print("2. Generating PNG receipt image...")
output_path = generate_receipt(order)
print(f"Receipt generated at: {output_path}")

assert os.path.exists(output_path), "Receipt PNG file does not exist!"
assert output_path.endswith(".png"), "Receipt output path does not end with .png!"

img = Image.open(output_path)
print(f"Receipt Image loaded successfully. Format: {img.format}, Size: {img.size}, Mode: {img.mode}")
assert img.format == "PNG", f"Expected PNG format, got {img.format}"
assert img.size[0] == 600, f"Expected width 600, got {img.size[0]}"

print("3. Testing receipt PNG validation in whatsapp_web...")
from whatsapp_web import _validate_image
validated = _validate_image(output_path)
print(f"Validated image path: {validated}")

print("\n--- PNG RECEIPT GENERATION TEST PASSED ---")
