import sqlite3

conn = sqlite3.connect("inventory.db")
cur = conn.cursor()
cur.execute("DROP TABLE IF EXISTS bom;")
conn.commit()
conn.close()

print("BOM-tabel verwijderd.")
