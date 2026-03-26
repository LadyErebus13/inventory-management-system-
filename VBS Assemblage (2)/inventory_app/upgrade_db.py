import sqlite3
#Designed By Petra Molegraaf ©

conn = sqlite3.connect("inventory.db")
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE products ADD COLUMN is_finished INTEGER DEFAULT 0;")
    print("Kolom 'is_finished' toegevoegd")
except Exception as e:
    print("Kon kolom niet toevoegen:", e)

conn.commit()
conn.close()