import time
from pathlib import Path
from utils.receipt import generate_receipt
from whatsapp_web import _get_page, _ensure_logged_in, _open_chat_url, _attach_image, _validate_image

order_data = {
    'order_id': 103,
    'order_date': '2026-08-09',
    'name': 'DOM Inspector',
    'phone': '9876543210',
    'payment_method': 'GPay',
    'items': [{'cloth_type': 'Jacket', 'quantity': 1, 'price_per_unit': 150.0, 'subtotal': 150.0}],
    'total_amount': 150.0
}

img_path = generate_receipt(order_data)
receipt_path = _validate_image(img_path)

page = _get_page()
_ensure_logged_in(page)
_open_chat_url(page, '9876543210', 'Test message caption')

print("Attaching image...")
_attach_image(page, receipt_path)
time.sleep(3)

print("\n=== DUMPING ALL PREVIEW SCREEN ELEMENTS ===")
elements = page.query_selector_all("div[contenteditable='true'], div[role='button'], button, span[data-icon], div[data-testid]")
for el in elements:
    try:
        aria = el.get_attribute("aria-label") or ""
        icon = el.get_attribute("data-icon") or ""
        testid = el.get_attribute("data-testid") or ""
        text = el.inner_text().strip().replace("\n", " | ")
        tag = el.evaluate("el => el.tagName.toLowerCase()")
        placeholder = el.get_attribute("placeholder") or ""
        
        if any(k in (aria + icon + testid + text + placeholder).lower() for k in ["caption", "send", "add", "media", "sticker", "crop", "edit", "image", "photo"]):
            print(f" -> tag={tag} | text='{text}' | aria='{aria}' | testid='{testid}' | icon='{icon}' | placeholder='{placeholder}'")
    except Exception:
        pass
