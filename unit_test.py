import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import database as db
db.init_db()

with db.get_connection() as conn:
    row = conn.execute("SELECT customer_id FROM customers LIMIT 1").fetchone()
    cid = row['customer_id'] if row else None

if not cid:
    cid = db.create_customer('Unit Test', '5544332211', 'Test', 'Addr')

items = [{'cloth_type': 'Jacket', 'quantity': 3, 'price_per_unit': 50.0, 'subtotal': 150.0, 'item_notes': ''}]
oid = db.create_order(cid, '2026-08-07', '', items)
order = db.get_order_full(oid)

item = order['items'][0]
units = item['units']
log = []
log.append(f"Order {oid}: {item['cloth_type']} x{item['quantity']}")
log.append(f"Units: {[(u['unit_id'], u['unit_number'], u['returned']) for u in units]}")

db.update_unit_returned(units[0]['unit_id'], True)
db.update_unit_returned(units[1]['unit_id'], True)
log.append(f"After marking unit1+unit2 returned — are_all_items_returned: {db.are_all_items_returned(oid)}")

db.update_unit_returned(units[2]['unit_id'], True)
log.append(f"After marking unit3 returned — are_all_items_returned: {db.are_all_items_returned(oid)}")

with open('unit_test_results.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(log))
