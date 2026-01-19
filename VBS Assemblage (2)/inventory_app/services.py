from contextlib import closing
from db import get_conn

def process_bom_transaction(order_id):
    """
    Verwerk een order en boekt automatisch voorraadmutaties 
    voor alle componenten voor de stukslijst (BOM) van de samengestelde producten.
    """
    with closing(get_conn()) as conn:
        cur = conn.cursor()

        # Haal alle orderregels op voor de gegeven order_id
        cur.execute("""
        SELECT product_id, qty FROM order_items WHERE order_id = ? """, (order_id,))
        order_items = cur.fetchall()

        for product_id, qty in order_items:
            #Boek voorraad mutaties voor het hoofdproduct.
            cur.execute("""
            Update products SET quantity = quantity - ? WHERE id = ?""", (qty, product_id))
            
            cur.execute("""INSERT INTO transactions(product_id, change, type, note) 
                        VALUES(?, ?, 'order', ?)""", (product_id, -qty, f'Order ID: {order_id}'))
            
            #Check of dit product een BOM heeft
            cur.execute("""SELECT component_product_id, quantity FROM bom WHERE parent_product_id = ?""", (product_id,))
            bom_items = cur.fetchall()

            for comp_id, comp_qty in bom_items:
                total_comp_qty = comp_qty * qty
                
                #Boek voorraad mutaties voor de componenten
                cur.execute("""
                Update products SET quantity = quantity - ? WHERE id = ?""", (total_comp_qty, comp_id))
                
                cur.execute("""INSERT INTO transactions(product_id, change, type, note) 
                            VALUES(?, ?, 'out', ?)""", (comp_id, -total_comp_qty, f"Order {order_id} (BOM)"))
    conn.commit()