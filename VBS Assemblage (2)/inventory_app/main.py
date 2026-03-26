from db import init_db
from ui import InventoryApp
#from migrations import run_migrations
#from master_sync import MasterDatabaseSync
 #Designed By Petra Molegraaf ©

MASTER_DB = "inventory.db"
READONLY_DB = "readonly/inventory_readonly.db"
BACKUP_DIR = "backups"

if __name__ == "__main__":
    # 1. Database initialiseren
    init_db()

    # 2. Migraties uitvoeren
   # run_migrations()

    # 3. Master sync initialiseren
    #sync = MasterDatabaseSync(MASTER_DB, READONLY_DB, BACKUP_DIR)

    # 4. DIRECT een readonly kopie maken (belangrijk!)
    #sync.update_readonly_copy()
    #InventoryApp.last_sync_time = sync.last_sync_time

    # 5. Sync-thread starten voor elke 4 uur
    #sync.start_sync_thread()

    #print("Master gestart en synchronisatie actief.")

    # 6. UI starten
    app = InventoryApp()
    app.mainloop()