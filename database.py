"""
database.py — SQLite data layer for Victory Laundry Management System
"""
import sqlite3
import os
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
            FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
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
            conn.execute(
                "INSERT INTO order_items (order_id, cloth_type, quantity, price_per_unit, subtotal, item_number) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (oid, it["cloth_type"], it["quantity"], it["price_per_unit"], it["subtotal"], idx)
            )
    return oid


def update_order(order_id, customer_id, order_date, delivery_date, items, notes, status, payment_method=""):
    total = sum(i["subtotal"] for i in items)
    with get_connection() as conn:
        conn.execute(
            "UPDATE orders SET customer_id=?, order_date=?, delivery_date=?, "
            "total_amount=?, notes=?, status=?, payment_method=? WHERE order_id=?",
            (customer_id, order_date, delivery_date or "", total, notes, status, payment_method, order_id)
        )
        conn.execute("DELETE FROM order_items WHERE order_id=?", (order_id,))
        for idx, it in enumerate(items, start=1):
            conn.execute(
                "INSERT INTO order_items (order_id, cloth_type, quantity, price_per_unit, subtotal, item_number) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (order_id, it["cloth_type"], it["quantity"], it["price_per_unit"], it["subtotal"], idx)
            )


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
    """Return complete order dict including customer info and items list."""
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
        order["items"] = [
            dict(r) for r in conn.execute(
                "SELECT * FROM order_items WHERE order_id=? ORDER BY item_number, item_id",
                (order_id,)
            ).fetchall()
        ]
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
