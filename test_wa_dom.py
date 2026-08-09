from playwright.sync_api import sync_playwright
import tempfile
from pathlib import Path
from utils.receipt import generate_receipt
from whatsapp_web import _attach_image, _SEL_ATTACH_PREVIEW, _validate_image

order_data = {
    'order_id': 99,
    'order_date': '2026-08-08',
    'name': 'Test User',
    'phone': '9876543210',
    'payment_method': 'Cash',
    'items': [{'cloth_type': 'Shirt', 'quantity': 1, 'price_per_unit': 50.0, 'subtotal': 50.0}],
    'total_amount': 50.0,
    'notes': 'E2E Test'
}

img_path = generate_receipt(order_data)
receipt_path = _validate_image(img_path)
print(f"Receipt PNG: {receipt_path}")

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(channel="chrome", headless=True)
    except Exception:
        browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Create mock WhatsApp Web DOM layout with composer, attach button, and file inputs
    mock_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Mock WhatsApp Web</title></head>
    <body>
        <div id="pane-side"><div data-testid="chat-list">Chat List</div></div>
        <footer>
            <div contenteditable="true" data-tab="10" id="composer">Hello Test User</div>
            <button aria-label="Attach" id="attach_btn">
                <span data-icon="plus">+</span>
            </button>
        </footer>

        <!-- Mock Attach Menu (initially hidden) -->
        <div id="attach_menu" style="display:none;">
            <div aria-label="Photos & videos" id="photos_btn">
                <span data-icon="attach-image">Photos</span>
            </div>
            <div aria-label="Document" id="doc_btn">
                <span data-icon="attach-document">Document</span>
            </div>
        </div>

        <!-- Hidden file inputs -->
        <input type="file" accept="image/*,video/mp4,video/3gpp,video/quicktime" id="img_input" style="display:none;">
        <input type="file" accept="*" id="doc_input" style="display:none;">

        <!-- Mock Preview Screen (initially hidden) -->
        <div id="preview" style="display:none;">
            <div data-testid="media-caption-input" contenteditable="true">Hello Test User</div>
            <span data-icon="send">Send</span>
        </div>

        <script>
            const attachBtn = document.getElementById('attach_btn');
            const attachMenu = document.getElementById('attach_menu');
            const photosBtn = document.getElementById('photos_btn');
            const imgInput = document.getElementById('img_input');
            const preview = document.getElementById('preview');

            attachBtn.addEventListener('click', () => {
                attachMenu.style.display = 'block';
            });

            photosBtn.addEventListener('click', () => {
                imgInput.click();
            });

            imgInput.addEventListener('change', () => {
                preview.style.display = 'block';
            });
        </script>
    </body>
    </html>
    """

    page.set_content(mock_html)
    print("Mock WhatsApp Web page loaded.")

    print("Executing _attach_image on page...")
    _attach_image(page, receipt_path)
    print("Method 1 / 2 completed without error!")

    # Verify preview is visible
    preview_elem = page.query_selector(_SEL_ATTACH_PREVIEW)
    assert preview_elem is not None, "Preview selector not found after attachment!"
    print("Preview selector confirmed visible:", preview_elem.inner_text())

    # Verify input file was attached
    files = page.eval_on_selector('#img_input', 'el => el.files.length')
    print(f"Attached files count on image input: {files}")
    assert files == 1, "Image input file count is not 1!"

    browser.close()

print("\n--- E2E DOM MOCK ATTACHMENT TEST PASSED ---")
