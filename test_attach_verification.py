import time
from pathlib import Path
from utils.receipt import generate_receipt
from whatsapp_web import _get_page, _ensure_logged_in, _open_chat_url, _attach_image, _validate_image, _SEL_ATTACH_PREVIEW

order_data = {
    'order_id': 102,
    'order_date': '2026-08-09',
    'name': 'Verification Customer',
    'phone': '9876543210',
    'payment_method': 'GPay',
    'items': [{'cloth_type': 'Jacket', 'quantity': 1, 'price_per_unit': 150.0, 'subtotal': 150.0}],
    'total_amount': 150.0,
    'notes': 'Sticker fix verification test'
}

print("1. Generating PNG receipt...")
img_path = generate_receipt(order_data)
receipt_path = _validate_image(img_path)

print("2. Opening WhatsApp Web page...")
page = _get_page()
_ensure_logged_in(page)

print("3. Navigating to chat...")
caption = f"Hello {order_data['name']},\n\nHere is your receipt for Order #{order_data['order_id']}.\n\nThank you for choosing ÉTOFFE LAUNDRY STUDIO!"
_open_chat_url(page, '9876543210', caption)

print("4. Executing _attach_image()...")
_attach_image(page, receipt_path)

print("5. Verifying preview screen and sticker toolbar absence...")
time.sleep(2)

# Check preview screen
caption_box = page.query_selector("div[data-testid='media-caption-input'], div[aria-label='Add a caption']")
assert caption_box is not None, "Media caption input box not found in preview screen!"
print("Caption box verified:", caption_box)

# Check that sticker editor elements (e.g. crop / sticker editor toolbar) are NOT present
sticker_editor = page.query_selector("[data-testid='sticker-editor'], [data-icon='sticker-crop'], button[title='Cutout']")
assert sticker_editor is None, "Sticker editor detected! Image was attached as a sticker instead of a photo!"

print("\n=== SUCCESS: Receipt attached as regular photo/video media with caption pre-filled! ===")
