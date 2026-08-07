import sys
sys.path.append('.')
import database as db

def run_test():
    log_messages = []
    def log(msg):
        log_messages.append(msg)
        
    log("Initializing Database...")
    db.init_db()

    customer_id = 1
    # Check if a test customer exists, create if not
    with db.get_connection() as conn:
        row = conn.execute("SELECT customer_id FROM customers WHERE phone='9988776655'").fetchone()
        if not row:
            customer_id = db.create_customer("DB Tester", "9988776655", "Test Place", "Test Address")
        else:
            customer_id = row['customer_id']
            
    items = [
        {"cloth_type": "Shirt", "quantity": 1, "price_per_unit": 20.0, "subtotal": 20.0, "item_notes": ""},
        {"cloth_type": "Pants", "quantity": 1, "price_per_unit": 30.0, "subtotal": 30.0, "item_notes": ""}
    ]

    log(f"Creating order for customer {customer_id}...")
    order_id = db.create_order(customer_id, "2026-08-07", "", items)
    
    order = db.get_order_full(order_id)
    log(f"Order created with ID: {order_id}")
    
    item1 = order['items'][0]['item_id']
    item2 = order['items'][1]['item_id']

    # Testing are_all_items_returned (initially false)
    log(f"Testing are_all_items_returned (initial state): {db.are_all_items_returned(order_id)}")

    # Mark first item as returned
    db.update_item_returned(item1, True)
    log("Marking item 1 as returned...")
    log(f"Testing are_all_items_returned (one item returned): {db.are_all_items_returned(order_id)}")
    
    # Check search 
    val1 = len(db.search_orders_by_item_status(False))
    val2 = len(db.search_orders_by_item_status(True))
    log(f"Orders not returned: {val1}")
    log(f"Orders returned: {val2}")

    # Mark second item as returned
    db.update_item_returned(item2, True)
    log("Marking item 2 as returned...")
    log(f"Testing are_all_items_returned (both items returned): {db.are_all_items_returned(order_id)}")

    # Check search again
    val3 = len(db.search_orders_by_item_status(False))
    val4 = len(db.search_orders_by_item_status(True))
    log(f"Orders not returned: {val3}")
    log(f"Orders returned: {val4}")
    
    log("Testing update_order preservation...")
    db.update_order(order_id, customer_id, "2026-08-07", "", items, "Test Notes", "Received")
    order = db.get_order_full(order_id)
    # Check if item returned persisted
    for item in order['items']:
         log(f"Item {item['item_id']} returned status: {item['item_returned']}")
    
    with open('test_results_clean.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_messages))

if __name__ == '__main__':
    run_test()
