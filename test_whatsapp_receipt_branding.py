"""
test_whatsapp_receipt_branding.py
Comprehensive verification test suite for the Étoffe WhatsApp receipt branding.
"""
import os
import unittest
from PIL import Image

from utils.receipt import (
    generate_whatsapp_receipt,
    _build_whatsapp_receipt_image,
    generate_receipt,
    _build_receipt_image,
    generate_dispatch_challan_pdf,
)

class TestWhatsAppReceiptBranding(unittest.TestCase):

    def setUp(self):
        self.sample_order_multi = {
            "order_id": "VICT-000123",
            "order_date": "2025-05-20 10:30 AM",
            "payment_method": "Paid (Cash)",
            "name": "Mr. Jithin Thomas",
            "phone": "9995556661",
            "place": "Pala",
            "address": "Kottayam, Kerala - 686575",
            "items": [
                {"cloth_type": "Shirt", "quantity": 2, "price_per_unit": 35.0, "subtotal": 70.0},
                {"cloth_type": "Pant", "quantity": 1, "price_per_unit": 40.0, "subtotal": 40.0},
                {"cloth_type": "Bedsheet (Double)", "quantity": 1, "price_per_unit": 120.0, "subtotal": 120.0},
                {"cloth_type": "Towel", "quantity": 2, "price_per_unit": 15.0, "subtotal": 30.0},
            ],
            "total_amount": 260.0,
            "notes": ""
        }

        self.sample_order_single = {
            "order_id": "VICT-000124",
            "order_date": "2025-05-21",
            "payment_method": "Cash",
            "name": "Anu George",
            "phone": "9876543210",
            "place": "Pala",
            "address": "",
            "items": [
                {"cloth_type": "Silk Saree", "quantity": 1, "price_per_unit": 250.0, "subtotal": 250.0},
            ],
            "total_amount": 250.0,
            "notes": ""
        }

        self.sample_order_long = {
            "order_id": "VICT-000125",
            "order_date": "2025-05-22",
            "payment_method": "Pending",
            "name": "Professor Alexander Bartholomew Montgomery-Smith III",
            "phone": "9123456789",
            "place": "Meenachil Taluk",
            "address": "Villa 402, High-End Luxury Apartments, Behind Federal Bank, Old Bypass Junction, Pala, Kottayam District, Kerala - 686575",
            "items": [
                {"cloth_type": "Heavy Embroidered Bridal Lehenga with Dupatta and Blouse Piece", "quantity": 1, "price_per_unit": 500.0, "subtotal": 500.0},
                {"cloth_type": "Gentleman Formal 3-Piece Tuxedo Suit with Waistcoat", "quantity": 2, "price_per_unit": 300.0, "subtotal": 600.0},
            ],
            "total_amount": 1100.0,
            "notes": "Handle with extreme care. Express same-day delivery requested by client."
        }

    def test_whatsapp_multi_item_generation(self):
        """Verify WhatsApp receipt generation with multiple items."""
        img_path = generate_whatsapp_receipt(self.sample_order_multi)
        self.assertTrue(os.path.exists(img_path))
        with Image.open(img_path) as img:
            self.assertEqual(img.mode, "RGB")
            self.assertEqual(img.size, (1754, 2480))

    def test_whatsapp_single_item_generation(self):
        """Verify WhatsApp receipt generation with single item."""
        img_path = generate_whatsapp_receipt(self.sample_order_single)
        self.assertTrue(os.path.exists(img_path))
        with Image.open(img_path) as img:
            self.assertEqual(img.mode, "RGB")
            self.assertEqual(img.size, (1754, 2480))

    def test_whatsapp_long_content_wrapping(self):
        """Verify long customer details, items, and notes wrap cleanly without errors."""
        img = _build_whatsapp_receipt_image(self.sample_order_long)
        self.assertIsInstance(img, Image.Image)
        self.assertGreater(img.height, 500)

    def test_fallback_when_logo_missing(self):
        """Verify graceful fallback if logo is not found."""
        orig_exists = os.path.exists
        def mock_exists(p):
            if "etoffe_logo_color_transparent.png" in p:
                return False
            return orig_exists(p)

        import unittest.mock as mock
        with mock.patch("os.path.exists", side_effect=mock_exists):
            img = _build_whatsapp_receipt_image(self.sample_order_multi)
            self.assertIsInstance(img, Image.Image)

    def test_normal_receipt_remains_unchanged(self):
        """Verify normal receipt generation produces classic B&W image without error."""
        img_path = generate_receipt(self.sample_order_multi)
        self.assertTrue(os.path.exists(img_path))
        with Image.open(img_path) as img:
            self.assertEqual(img.mode, "RGB")

    def test_dispatch_challan_pdf_remains_unchanged(self):
        """Verify dispatch challan PDF generates without error."""
        pdf_path = generate_dispatch_challan_pdf(self.sample_order_multi)
        self.assertTrue(os.path.exists(pdf_path))
        self.assertGreater(os.path.getsize(pdf_path), 500)


if __name__ == "__main__":
    unittest.main()
