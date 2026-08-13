"""
database.py — SQLite data layer for Victory Laundry Management System
"""
import sqlite3
import os
import re
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "laundry.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables and seed default price list."""
    conn = get_connection()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            phone       TEXT UNIQUE NOT NULL,
            place       TEXT DEFAULT '',
            address     TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS orders (
            order_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id   INTEGER NOT NULL,
            order_date    TEXT NOT NULL,
            delivery_date TEXT DEFAULT '',
            total_amount  REAL NOT NULL DEFAULT 0.0,
            status        TEXT DEFAULT 'Received',
            notes         TEXT DEFAULT '',
            payment_method    TEXT DEFAULT '',
            status_changed_at TEXT DEFAULT '',
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE IF NOT EXISTS order_items (
            item_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id       INTEGER NOT NULL,
            cloth_type     TEXT NOT NULL,
            quantity       INTEGER NOT NULL DEFAULT 1,
            price_per_unit REAL NOT NULL,
            subtotal       REAL NOT NULL,
            item_number    INTEGER NOT NULL DEFAULT 0,
            item_notes     TEXT DEFAULT '',
            item_returned  INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS order_item_units (
            unit_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id     INTEGER NOT NULL,
            unit_number INTEGER NOT NULL DEFAULT 1,
            returned    INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (item_id) REFERENCES order_items(item_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS price_list (
            cloth_type    TEXT PRIMARY KEY,
            default_price REAL NOT NULL DEFAULT 0.0
        );
    """)

    # ── Migration: add columns to existing databases ──
    _migrate_add_column(c, "orders", "payment_method", "TEXT DEFAULT ''")
    _migrate_add_column(c, "orders", "status_changed_at", "TEXT DEFAULT ''")
    _migrate_add_column(c, "order_items", "item_number", "INTEGER NOT NULL DEFAULT 0")
    _migrate_add_column(c, "order_items", "item_notes", "TEXT DEFAULT ''")
    _migrate_add_column(c, "order_items", "item_returned", "INTEGER NOT NULL DEFAULT 0")
    # Ensure order_item_units table exists (for databases predating this feature)
    c.executescript("""
        CREATE TABLE IF NOT EXISTS order_item_units (
            unit_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id     INTEGER NOT NULL,
            unit_number INTEGER NOT NULL DEFAULT 1,
            returned    INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (item_id) REFERENCES order_items(item_id) ON DELETE CASCADE
        );
    """)
    # Backfill units for existing items that have none yet
    _backfill_item_units(conn)

    defaults = [
        ("Shirt", 20.0), ("Pants", 30.0), ("Saree", 80.0),
        ("Bedsheet", 60.0), ("Towel", 15.0), ("Kurta", 25.0), ("Jacket", 50.0),
    ]
    for ct, pr in defaults:
        c.execute("INSERT OR IGNORE INTO price_list VALUES (?, ?)", (ct, pr))

    conn.commit()
    conn.close()


def _migrate_add_column(cursor, table, column, col_def):
    """Safely add a column if it doesn't exist yet."""
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
    except sqlite3.OperationalError:
        pass  # column already exists


def _backfill_item_units(conn):
    """For any order_items that have no units yet, create one unit per quantity."""
    rows = conn.execute(
        "SELECT oi.item_id, oi.quantity, oi.item_returned FROM order_items oi "
        "WHERE NOT EXISTS (SELECT 1 FROM order_item_units u WHERE u.item_id=oi.item_id)"
    ).fetchall()
    for row in rows:
        old_ret = row["item_returned"]
        # First unit: if whole item was marked returned, all units returned; else none
        for unit_num in range(1, row["quantity"] + 1):
            conn.execute(
                "INSERT INTO order_item_units (item_id, unit_number, returned) VALUES (?, ?, ?)",
                (row["item_id"], unit_num, old_ret)
            )
    conn.commit()


# ── Customers ─────────────────────────────────────────────────────────────────

def get_customer_by_phone(phone: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE phone = ?", (phone.strip(),)
        ).fetchone()
    return dict(row) if row else None


def get_customer_by_id(cid: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE customer_id = ?", (cid,)
        ).fetchone()
    return dict(row) if row else None


def create_customer(name, phone, place, address) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO customers (name, phone, place, address) VALUES (?, ?, ?, ?)",
            (name.strip(), phone.strip(), place.strip(), address.strip())
        )
        return cur.lastrowid


def update_customer(cid, name, phone, place, address):
    with get_connection() as conn:
        conn.execute(
            "UPDATE customers SET name=?, phone=?, place=?, address=? WHERE customer_id=?",
            (name.strip(), phone.strip(), place.strip(), address.strip(), cid)
        )


# ── Price List ─────────────────────────────────────────────────────────────────

def get_all_prices():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM price_list ORDER BY cloth_type"
        ).fetchall()
    return [dict(r) for r in rows]


def get_price(cloth_type: str) -> float:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT default_price FROM price_list WHERE cloth_type=?", (cloth_type,)
        ).fetchone()
    return row["default_price"] if row else 0.0


def set_price(cloth_type: str, price: float):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO price_list VALUES (?, ?)",
            (cloth_type.strip(), price)
        )


def delete_price(cloth_type: str):
    with get_connection() as conn:
        conn.execute("DELETE FROM price_list WHERE cloth_type=?", (cloth_type,))


def get_cloth_types():
    """Return sorted list of cloth type names."""
    return [p["cloth_type"] for p in get_all_prices()]


# ── Orders ─────────────────────────────────────────────────────────────────────

def create_order(customer_id, order_date, delivery_date, items, notes="", payment_method="") -> int:
    total = sum(i["subtotal"] for i in items)
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO orders (customer_id, order_date, delivery_date, total_amount, notes, payment_method) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (customer_id, order_date, delivery_date or "", total, notes, payment_method)
        )
        oid = cur.lastrowid
        for idx, it in enumerate(items, start=1):
            item_cur = conn.execute(
                "INSERT INTO order_items (order_id, cloth_type, quantity, price_per_unit, subtotal, item_number, item_notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (oid, it["cloth_type"], it["quantity"], it["price_per_unit"], it["subtotal"], idx, it.get("item_notes", ""))
            )
            item_id = item_cur.lastrowid
            for unit_num in range(1, it["quantity"] + 1):
                conn.execute(
                    "INSERT INTO order_item_units (item_id, unit_number, returned) VALUES (?, ?, 0)",
                    (item_id, unit_num)
                )
    return oid


def update_order(order_id, customer_id, order_date, delivery_date, items, notes, status, payment_method=""):
    total = sum(i["subtotal"] for i in items)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        # Preserve per-unit returned states keyed by (item_number, unit_number)
        existing_items = conn.execute(
            "SELECT item_id, item_number FROM order_items WHERE order_id=?", (order_id,)
        ).fetchall()
        unit_returned_map = {}  # (item_number, unit_number) -> returned
        for ei in existing_items:
            units = conn.execute(
                "SELECT unit_number, returned FROM order_item_units WHERE item_id=?",
                (ei["item_id"],)
            ).fetchall()
            for u in units:
                unit_returned_map[(ei["item_number"], u["unit_number"])] = u["returned"]

        conn.execute(
            "UPDATE orders SET customer_id=?, order_date=?, delivery_date=?, "
            "total_amount=?, notes=?, status=?, payment_method=?, "
            "status_changed_at=CASE WHEN status<>? THEN ? ELSE status_changed_at END "
            "WHERE order_id=?",
            (customer_id, order_date, delivery_date or "", total, notes, status,
             payment_method, status, now, order_id)
        )
        conn.execute("DELETE FROM order_items WHERE order_id=?", (order_id,))
        for idx, it in enumerate(items, start=1):
            item_cur = conn.execute(
                "INSERT INTO order_items (order_id, cloth_type, quantity, price_per_unit, subtotal, item_number, item_notes, item_returned) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                (order_id, it["cloth_type"], it["quantity"], it["price_per_unit"], it["subtotal"], idx, it.get("item_notes", ""))
            )
            new_item_id = item_cur.lastrowid
            for unit_num in range(1, it["quantity"] + 1):
                prev_ret = unit_returned_map.get((idx, unit_num), 0)
                conn.execute(
                    "INSERT INTO order_item_units (item_id, unit_number, returned) VALUES (?, ?, ?)",
                    (new_item_id, unit_num, prev_ret)
                )


def update_unit_returned(unit_id: int, returned: bool):
    """Toggle or set the returned flag for a single unit of an order item."""
    val = 1 if returned else 0
    with get_connection() as conn:
        conn.execute("UPDATE order_item_units SET returned=? WHERE unit_id=?", (val, unit_id))


def update_item_returned(item_id: int, returned: bool):
    """Toggle or set all unit flags for an order item (legacy/batch helper)."""
    val = 1 if returned else 0
    with get_connection() as conn:
        conn.execute("UPDATE order_item_units SET returned=? WHERE item_id=?", (val, item_id))


def are_all_items_returned(order_id: int) -> bool:
    """Return True if all individual units in the order are marked as returned."""
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM order_item_units u "
            "JOIN order_items oi ON u.item_id=oi.item_id "
            "WHERE oi.order_id=?", (order_id,)
        ).fetchone()[0]
        if total == 0:
            return True
        unreturned = conn.execute(
            "SELECT COUNT(*) FROM order_item_units u "
            "JOIN order_items oi ON u.item_id=oi.item_id "
            "WHERE oi.order_id=? AND u.returned=0", (order_id,)
        ).fetchone()[0]
        return unreturned == 0


def delete_order(order_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM orders WHERE order_id=?", (order_id,))


def update_order_status(order_id: int, status: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            "UPDATE orders SET status=?, status_changed_at=? WHERE order_id=?",
            (status, now, order_id)
        )


def get_order_full(order_id: int):
    """Return complete order dict including customer info, items, and per-unit data."""
    with get_connection() as conn:
        row = conn.execute("""
            SELECT o.*, c.name, c.phone, c.place, c.address
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            WHERE o.order_id = ?
        """, (order_id,)).fetchone()
        if not row:
            return None
        order = dict(row)
        item_rows = conn.execute(
            "SELECT * FROM order_items WHERE order_id=? ORDER BY item_number, item_id",
            (order_id,)
        ).fetchall()
        items = []
        for ir in item_rows:
            item_dict = dict(ir)
            units = conn.execute(
                "SELECT unit_id, unit_number, returned FROM order_item_units WHERE item_id=? ORDER BY unit_number",
                (ir["item_id"],)
            ).fetchall()
            item_dict["units"] = [dict(u) for u in units]
            items.append(item_dict)
        order["items"] = items
    return order


_ORDER_SELECT = """
    SELECT o.order_id, o.order_date, o.delivery_date, o.total_amount,
           o.status, o.payment_method, o.status_changed_at,
           c.name, c.phone
    FROM orders o JOIN customers c ON o.customer_id=c.customer_id
"""


def search_orders(query: str):
    """Search by order_id (if numeric) or customer name/phone."""
    with get_connection() as conn:
        try:
            oid = int(query.strip())
            rows = conn.execute(
                _ORDER_SELECT + " WHERE o.order_id=?", (oid,)
            ).fetchall()
        except ValueError:
            like = f"%{query.strip()}%"
            rows = conn.execute(
                _ORDER_SELECT + " WHERE c.name LIKE ? OR c.phone LIKE ? ORDER BY o.order_id DESC",
                (like, like)
            ).fetchall()
    return [dict(r) for r in rows]


def search_orders_by_status(status: str):
    """Return all orders matching the given status."""
    with get_connection() as conn:
        rows = conn.execute(
            _ORDER_SELECT + " WHERE o.status=? ORDER BY o.order_id DESC",
            (status,)
        ).fetchall()
    return [dict(r) for r in rows]


def search_orders_by_item_status(returned: bool):
    """Return all orders containing at least one unit with the given returned state."""
    val = 1 if returned else 0
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT DISTINCT o.order_id, o.order_date, o.delivery_date, o.total_amount,
                   o.status, o.payment_method, o.status_changed_at,
                   c.name, c.phone
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN order_item_units u ON oi.item_id = u.item_id
            WHERE u.returned = ?
            ORDER BY o.order_id DESC
        """, (val,)).fetchall()
    return [dict(r) for r in rows]


def get_orders_by_date_range(from_date: str, to_date: str):
    with get_connection() as conn:
        rows = conn.execute(
            _ORDER_SELECT + " WHERE o.order_date BETWEEN ? AND ? ORDER BY o.order_date DESC, o.order_id DESC",
            (from_date, to_date)
        ).fetchall()
    return [dict(r) for r in rows]


def get_recent_orders(limit=200):
    with get_connection() as conn:
        rows = conn.execute(
            _ORDER_SELECT + " ORDER BY o.order_id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_dashboard_stats() -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        def scalar(sql, *args):
            return conn.execute(sql, args).fetchone()[0]

        return {
            "today_orders":    scalar("SELECT COUNT(*) FROM orders WHERE order_date=?", today),
            "today_revenue":   scalar("SELECT COALESCE(SUM(total_amount),0) FROM orders WHERE order_date=?", today),
            "pending":         scalar("SELECT COUNT(*) FROM orders WHERE status IN ('Received','In Progress')"),
            "ready":           scalar("SELECT COUNT(*) FROM orders WHERE status='Ready'"),
            "total_customers": scalar("SELECT COUNT(*) FROM customers"),
            "total_orders":    scalar("SELECT COUNT(*) FROM orders"),
        }


# ── Progress / Stats helpers ──────────────────────────────────────────────────

def get_daily_stats(days=30):
    """Revenue + order count per day for the last N days."""
    start = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT order_date AS period,
                   COUNT(*) AS order_count,
                   COALESCE(SUM(total_amount), 0) AS revenue
            FROM orders
            WHERE order_date >= ?
            GROUP BY order_date
            ORDER BY order_date
        """, (start,)).fetchall()
    return [dict(r) for r in rows]


def get_weekly_stats(weeks=12):
    """Revenue + order count per week for the last N weeks."""
    start = (datetime.now() - timedelta(weeks=weeks)).strftime("%Y-%m-%d")
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT strftime('%Y-W%W', order_date) AS period,
                   COUNT(*) AS order_count,
                   COALESCE(SUM(total_amount), 0) AS revenue
            FROM orders
            WHERE order_date >= ?
            GROUP BY strftime('%Y-W%W', order_date)
            ORDER BY period
        """, (start,)).fetchall()
    return [dict(r) for r in rows]


def get_monthly_stats(months=12):
    """Revenue + order count per month for the last N months."""
    start_dt = datetime.now().replace(day=1)
    for _ in range(months - 1):
        start_dt = (start_dt - timedelta(days=1)).replace(day=1)
    start = start_dt.strftime("%Y-%m-%d")
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT strftime('%Y-%m', order_date) AS period,
                   COUNT(*) AS order_count,
                   COALESCE(SUM(total_amount), 0) AS revenue
            FROM orders
            WHERE order_date >= ?
            GROUP BY strftime('%Y-%m', order_date)
            ORDER BY period
        """, (start,)).fetchall()
    return [dict(r) for r in rows]


def get_yearly_stats():
    """Revenue + order count per year."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT strftime('%Y', order_date) AS period,
                   COUNT(*) AS order_count,
                   COALESCE(SUM(total_amount), 0) AS revenue
            FROM orders
            GROUP BY strftime('%Y', order_date)
            ORDER BY period
        """).fetchall()
    return [dict(r) for r in rows]


def clean_phone(phone_str: str) -> str:
    """Normalize phone number string for grouping."""
    raw = str(phone_str or "").strip()
    digits = "".join(re.findall(r"\d", raw))
    if raw.startswith("00"):
        digits = digits[2:]
    if len(digits) == 10:
        digits = "91" + digits
    return digits if digits else raw.lower()


def get_customer_aggregations():
    """Aggregate customer data grouped by phone number.
    Returns a list of customer dicts:
      - name: most recent name used
      - phone: phone number string
      - normalized_phone: cleaned phone string for key matching / WhatsApp
      - total_orders: count of orders
      - total_spent: total revenue from customer
      - first_visit: earliest order_date
      - last_visit: latest order_date
      - orders: list of order dicts sorted by order_id DESC
    """
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT o.order_id, o.order_date, o.delivery_date, o.total_amount,
                   o.status, o.payment_method, o.status_changed_at, o.notes,
                   c.customer_id, c.name, c.phone, c.place, c.address
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            ORDER BY o.order_id DESC
        """).fetchall()

        cust_rows = conn.execute("""
            SELECT c.customer_id, c.name, c.phone, c.place, c.address
            FROM customers c
            WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id)
        """).fetchall()

    grouped = {}

    for r in rows:
        order = dict(r)
        raw_phone = order.get("phone", "")
        norm_p = clean_phone(raw_phone)
        if norm_p not in grouped:
            grouped[norm_p] = {
                "name": order.get("name", "Customer"),
                "phone": raw_phone,
                "normalized_phone": norm_p,
                "place": order.get("place", ""),
                "address": order.get("address", ""),
                "total_orders": 0,
                "total_spent": 0.0,
                "first_visit": order.get("order_date", ""),
                "last_visit": order.get("order_date", ""),
                "orders": []
            }
        cust = grouped[norm_p]
        cust["total_orders"] += 1
        cust["total_spent"] += float(order.get("total_amount", 0.0))
        cust["orders"].append(order)

        o_date = order.get("order_date", "")
        if o_date:
            if not cust["first_visit"] or o_date < cust["first_visit"]:
                cust["first_visit"] = o_date
            if not cust["last_visit"] or o_date > cust["last_visit"]:
                cust["last_visit"] = o_date

    for cr in cust_rows:
        cdict = dict(cr)
        raw_phone = cdict.get("phone", "")
        norm_p = clean_phone(raw_phone)
        if norm_p not in grouped:
            grouped[norm_p] = {
                "name": cdict.get("name", "Customer"),
                "phone": raw_phone,
                "normalized_phone": norm_p,
                "place": cdict.get("place", ""),
                "address": cdict.get("address", ""),
                "total_orders": 0,
                "total_spent": 0.0,
                "first_visit": "—",
                "last_visit": "—",
                "orders": []
            }

    result = list(grouped.values())
    result.sort(key=lambda x: x["last_visit"], reverse=True)
    return result


def delete_customer_by_phone(phone_number: str):
    """Delete customer record(s) and all associated orders for a given phone number."""
    norm_target = clean_phone(phone_number)
    with get_connection() as conn:
        all_custs = conn.execute("SELECT customer_id, phone FROM customers").fetchall()
        matching_cids = [
            c["customer_id"] for c in all_custs
            if clean_phone(c["phone"]) == norm_target or c["phone"] == phone_number
        ]

        for cid in matching_cids:
            conn.execute("DELETE FROM orders WHERE customer_id=?", (cid,))
            conn.execute("DELETE FROM customers WHERE customer_id=?", (cid,))


