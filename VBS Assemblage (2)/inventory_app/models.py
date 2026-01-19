from contextlib import closing
from db import get_conn

def create_bom(parent_product_id, components):
    """Maak een BOM(Bill of Materials) aan voor een samengesteld product.
    parent_product_id: id van het hoofdproduct (bundel)
    components = lijst van tuples (component_product_id, quantity)
    """
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        for comp_id, qty in components:
            cur.execute(
                "INSERT INTO bom (parent_product_id, component_product_id, quantity) VALUES (?,?,?)",
                (parent_product_id, comp_id, qty)
            )
        conn.commit()

def get_bom(parent_product_id):
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT p.sku, p.name, b.quantity
        FROM bom b
        JOIN products p ON b.component_product_id = p.id
        WHERE b.parent_product_id = ?
        """, (parent_product_id,))
        return cur.fetchall()


def add_product(sku, name, description="", quantity=0, min_stock=0, location=""):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products(sku, name, description, quantity, min_stock, location) VALUES (?,?,?,?,?,?)",
            (sku, name, description, quantity, min_stock, location)
        )
        conn.commit()
        return cur.lastrowid

def update_product(pid, **fields):
    if not fields:
        return
    keys = ", ".join(f"{k}=?" for k in fields.keys())
    vals = list(fields.values()) + [pid]
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE products SET {keys} WHERE id=?", vals)
        conn.commit()

def delete_product(pid):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id=?", (pid,))
        conn.commit()

def list_products(search=None):
    with get_conn() as conn:
        cur = conn.cursor()
        if search:
            q = f"%{search}%"
            cur.execute(
                "SELECT * FROM products WHERE sku LIKE ? OR name LIKE ? ORDER BY name",
                (q, q)
            )
        else:
            cur.execute("SELECT * FROM products ORDER BY name")
        return cur.fetchall()

def adjust_quantity(pid, change, typ="manual", note=""):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE products SET quantity = quantity + ? WHERE id=?", (change, pid))
        cur.execute(
            "INSERT INTO transactions (product_id, change, type, note) VALUES (?,?,?,?)",
            (pid, change, typ, note)
        )
        conn.commit()

# Orders en safe stock adjustment
def create_order(customer, items):
    """items: list van dicts:[{'product_id': id, 'quantity': q, 'price': p}]
    Retourneert order_id. Rollback on error (e.g., insufficient stock)"""
    with get_conn() as conn:
        cur = conn.cursor()
        try:
            # Controle voorraad
            for it in items:
                cur.execute("SELECT quantity, name FROM products WHERE id=?", (it['product_id'],))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Product id {it['product_id']} bestaat niet")
                available = row[0]
                if available < it['quantity']:
                    raise ValueError(
                        f"Onvoldoende voorraad voor {row[1]} (beschikbaar {available}, gevraagd {it['quantity']})"
                    )

            # Maak order
            total = sum((it.get('price', 0) * it['quantity']) for it in items)
            cur.execute(
                "INSERT INTO orders(customer, status, total) VALUES (?,?,?)",
                (customer, 'created', total)
            )
            order_id = cur.lastrowid

            # Voeg items in en update voorraad + transacties
            for it in items:
                cur.execute(
                    "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?,?,?,?)",
                    (order_id, it['product_id'], it['quantity'], it.get('price', 0))
                )
                cur.execute(
                    "UPDATE products SET quantity = quantity - ? WHERE id=?",
                    (it['quantity'], it['product_id'])
                )
                cur.execute(
                    "INSERT INTO transactions (product_id, change, type, note) VALUES (?,?,?,?)",
                    (it['product_id'], -it['quantity'], 'order', f'order_id:{order_id}')
                )

            conn.commit()
            return order_id
        except Exception:
            conn.rollback()
            raise

def list_orders(status=None):
    with get_conn() as conn:
        cur = conn.cursor()
        if status:
            cur.execute("SELECT * FROM orders WHERE status=? ORDER BY created_at DESC", (status,))
        else:
            cur.execute("SELECT * FROM orders ORDER BY created_at DESC")
        return cur.fetchall()

def get_order_items(order_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT oi.id, oi.product_id, p.sku, p.name, oi.quantity, oi.price
               FROM order_items oi
               JOIN products p ON oi.product_id = p.id
               WHERE oi.order_id=?""",
            (order_id,)
        )
        return cur.fetchall()

def cancel_order(order_id):
    """Optioneel: als order nog 'created' kan geannuleerd worden -> voorraad terugboeken."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT status FROM orders WHERE id=?", (order_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError("Order niet gevonden")
        status = row[0]
        if status != 'created':
            raise ValueError("Order kan niet geannuleerd worden (status != created)")

        items = get_order_items(order_id)
        for it in items:
            prod_id = it[1]
            qty = it[4]
            cur.execute("UPDATE products SET quantity = quantity + ? WHERE id=?", (qty, prod_id))
            cur.execute(
                "INSERT INTO transactions (product_id, change, type, note) VALUES (?,?,?,?)",
                (prod_id, qty, 'cancel', f'order_id:{order_id}')
            )

        cur.execute("UPDATE orders SET status='cancelled' WHERE id=?", (order_id,))
        conn.commit()
