import sys
import os

# Put root dir on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as db
from utils.receipt import generate_receipt, generate_dispatch_challan_pdf, open_receipt_pdf, open_receipt
from utils.dispatch_slip import generate_dispatch_slip, open_dispatch_slip

def test_flow():
    db.init_db()
    print("DB Initialized.")
    
    # Test setting getter and setter
    db.set_setting("print_mode", "direct")
    mode = db.get_setting("print_mode")
    assert mode == "direct", f"Expected direct, got {mode}"
    print(f"Verified print_mode setting: {mode}")
    
    sample_order = {
        "order_id": 101,
        "customer_id": 1,
        "order_date": "2026-08-20",
        "delivery_date": "2026-08-22",
        "payment_method": "Cash",
        "name": "Jane Doe",
        "phone": "9876543210",
        "place": "Pala",
        "address": "Market Road",
        "items": [
            {"cloth_type": "Shirt", "quantity": 2, "price_per_unit": 20.0, "subtotal": 40.0, "item_number": 1, "item_notes": "Dryclean"}
        ],
        "total_amount": 40.0,
        "notes": "Urgent delivery"
    }
    
    rec_png = generate_receipt(sample_order)
    assert os.path.exists(rec_png), "PNG receipt file was not created"
    print(f"Receipt PNG created: {rec_png}")
    
    rec_pdf = generate_dispatch_challan_pdf(sample_order)
    assert os.path.exists(rec_pdf), "PDF receipt file was not created"
    print(f"Receipt PDF created: {rec_pdf}")
    
    disp_pdf = generate_dispatch_slip(sample_order)
    assert os.path.exists(disp_pdf), "Dispatch slip PDF file was not created"
    print(f"Dispatch slip PDF created: {disp_pdf}")
    
    print("ALL PRINT UTILITY & DB TESTS PASSED SUCCESSFULY!")

if __name__ == "__main__":
    test_flow()
