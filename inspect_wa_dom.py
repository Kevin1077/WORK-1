import time
from pathlib import Path
from whatsapp_web import _get_page, _ensure_logged_in, _SEL_ATTACH_BTN, _SEL_COMPOSER

print("Getting WhatsApp page...")
page = _get_page()

print("Ensuring logged in...")
_ensure_logged_in(page)

# If no chat is open, click the first chat in the side pane or navigate to send URL
try:
    print("Waiting for chat list / composer...")
    page.wait_for_selector(f"{_SEL_COMPOSER}, [data-testid='chat-list-item'], div[role='row']", timeout=10000)
    if not page.query_selector(_SEL_COMPOSER):
        print("No composer open. Clicking first chat in chat list...")
        chat = page.query_selector("[data-testid='chat-list-item'], div[role='row']")
        if chat:
            chat.click()
            time.sleep(2)
except Exception as e:
    print(f"Chat load note: {e}")

# Wait for composer
try:
    page.wait_for_selector(_SEL_COMPOSER, timeout=10000)
    print("Composer is visible!")
except Exception as e:
    print(f"Composer wait error: {e}")

# Dump all file inputs and their accept attributes right now
inputs = page.query_selector_all('input[type="file"]')
print(f"\n=== Found {len(inputs)} file inputs in page DOM ===")
for idx, inp in enumerate(inputs):
    accept = inp.get_attribute("accept")
    id_attr = inp.get_attribute("id")
    parent_html = inp.evaluate("el => el.parentElement.outerHTML")[:150]
    print(f"Input #{idx}: accept='{accept}', id='{id_attr}' | parent snippet: {parent_html}")

# Find attach button
attach_btn = page.query_selector(_SEL_ATTACH_BTN)
if not attach_btn:
    print("Searching for attach button via broader selectors...")
    attach_btn = page.query_selector("button[aria-label='Attach'], button[title='Attach'], span[data-icon='plus'], span[data-icon='attach-menu-plus']")

if attach_btn:
    print(f"\nFound attach button: {attach_btn}")
    attach_btn.click()
    time.sleep(1.5)

    print("\n=== Inspecting Attach Menu Items after clicking Attach button ===")
    
    # Re-check file inputs after clicking attach button
    inputs2 = page.query_selector_all('input[type="file"]')
    print(f"Found {len(inputs2)} file inputs after opening attach menu:")
    for idx, inp in enumerate(inputs2):
        accept = inp.get_attribute("accept")
        id_attr = inp.get_attribute("id")
        print(f"  Input #{idx}: accept='{accept}', id='{id_attr}'")

    # Dump all elements in the menu popover
    elements = page.query_selector_all("ul li, button, span[data-icon], div[role='button'], div[aria-label]")
    print("\n=== Detailed Menu Items ===")
    found = set()
    for el in elements:
        try:
            aria = el.get_attribute("aria-label") or ""
            icon = el.get_attribute("data-icon") or ""
            testid = el.get_attribute("data-testid") or ""
            text = el.inner_text().strip().replace("\n", " | ")
            html = el.evaluate("el => el.outerHTML")
            
            # Print if relevant
            if any(k in (aria + icon + testid + text).lower() for k in ["photo", "video", "doc", "image", "media", "camera", "sticker", "attach"]):
                info = f"text='{text}' | aria-label='{aria}' | data-icon='{icon}' | data-testid='{testid}' | html={html[:200]}"
                if info not in found:
                    found.add(info)
                    print(" ->", info)
        except Exception:
            pass
else:
    print("Attach button not found on page.")
