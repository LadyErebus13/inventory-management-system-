import sqlite3
from contextlib import closing
import db

def TestSQL():
    with closing(db.get_conn()) as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT * --p.id, p.sku, p.name, b.quantity
        --FROM products p
        FROM bom as b
        --JOIN products p ON b.component_product_id = p.id
        --WHERE p.sku LIKE ?
        WHERE b.component_product_id=76
        """, ())
        #""", ("SPS-GVP%",))
        return cur.fetchall()


#print(sqlite3.connect("readonly/inventory_readonly.db").execute("SELECT * FROM orders").fetchall())


res = TestSQL()
print(res)
