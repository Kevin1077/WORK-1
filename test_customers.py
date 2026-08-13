"""
Unit test for Customer Aggregation Logic
"""
import unittest
import database as db

class TestCustomerAggregation(unittest.TestCase):
    def test_customer_aggregation(self):
        db.init_db()
        test_phone = "9876500001"
        
        # Check if customer already exists, get or create
        existing = db.get_customer_by_phone(test_phone)
        if existing:
            cid1 = existing["customer_id"]
            db.update_customer(cid1, "kevin", test_phone, "Test Place", "Address 1")
        else:
            cid1 = db.create_customer("kevin", test_phone, "Test Place", "Address 1")
            
        oid1 = db.create_order(cid1, "2026-01-01", "2026-01-02", [{"cloth_type": "Shirt", "quantity": 2, "price_per_unit": 20.0, "subtotal": 40.0}])
        
        # Update customer name to "Kevin" for second order
        db.update_customer(cid1, "Kevin", test_phone, "Test Place", "Address 1")
        oid2 = db.create_order(cid1, "2026-01-10", "2026-01-11", [{"cloth_type": "Pants", "quantity": 1, "price_per_unit": 30.0, "subtotal": 30.0}])

        aggregations = db.get_customer_aggregations()
        
        # Find group for test_phone
        cust = None
        for c in aggregations:
            if c["normalized_phone"] == "91" + test_phone or c["phone"] == test_phone:
                cust = c
                break

        self.assertIsNotNone(cust, f"Customer with phone {test_phone} should exist")
        self.assertEqual(cust["name"], "Kevin", "Display name should be the most recent name used")
        self.assertGreaterEqual(cust["total_orders"], 2)
        self.assertGreaterEqual(cust["total_spent"], 70.0)
        self.assertEqual(cust["first_visit"], "2026-01-01")
        self.assertEqual(cust["last_visit"], "2026-01-10")

        # Cleanup test orders
        db.delete_order(oid1)
        db.delete_order(oid2)

    def test_delete_customer(self):
        db.init_db()
        test_phone = "9876599999"
        cid = db.create_customer("Delete Me", test_phone, "Place", "Address")
        oid = db.create_order(cid, "2026-02-01", "2026-02-02", [{"cloth_type": "Shirt", "quantity": 1, "price_per_unit": 20.0, "subtotal": 20.0}])

        # Delete customer
        db.delete_customer_by_phone(test_phone)

        # Verify customer and order deleted
        self.assertIsNone(db.get_customer_by_phone(test_phone))
        self.assertIsNone(db.get_order_full(oid))


if __name__ == "__main__":
    unittest.main()

