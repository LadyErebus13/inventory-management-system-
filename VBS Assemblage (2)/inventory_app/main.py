from db import init_db
from ui import InventoryApp
import services

if __name__ == "__main__":
    init_db()
    app = InventoryApp()
    app.mainloop()