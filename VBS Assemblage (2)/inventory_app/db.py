import sqlite3
from contextlib import closing

DB = "inventory.db"

def init_db():
    with closing(sqlite3.connect(DB)) as conn:
        cur = conn.cursor()

        # Producten
        cur.execute("""
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE,
            name TEXT,
            description TEXT,
            quantity INTEGER DEFAULT 0,
            min_stock INTEGER DEFAULT 0,
            location TEXT
        )
        """)

        # Transacties
        cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            change INTEGER,
            type TEXT,
            note TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
        """)

        # Orders
        cur.execute("""
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer TEXT,
            status TEXT DEFAULT 'created',
            total REAL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Orderregels
        cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            price REAL DEFAULT 0,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
        """)

        # BOM (bill of materials)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bom(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_product_id INTEGER NOT NULL,
            component_product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(parent_product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY(component_product_id) REFERENCES products(id) ON DELETE CASCADE
        )
        """)
        conn.commit()


def get_conn():
    return sqlite3.connect(DB)
