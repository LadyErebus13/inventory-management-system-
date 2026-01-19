import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import csv
import models
from services import process_bom_transaction

class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Voorraadbeheer Assemblage")
        self.geometry("900x600")
        self.create_widgets()
        self.refresh_list()

    def handle_process_order(self):
        order_id = 1 
        process_bom_transaction(order_id)
        print(f"Order {order_id} verwerkt met BOM-transacties.")

    def create_widgets(self):
        # MENUBALK
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # PRODUCTEN MENU
        product_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Producten", menu=product_menu)
        product_menu.add_command(label="Nieuw product", command=self.add_product)
        product_menu.add_command(label="Bewerken", command=self.edit_selected)
        product_menu.add_command(label="Verwijderen", command=self.delete_selected)
        product_menu.add_separator()
        product_menu.add_command(label="Import CSV", command=self.import_csv)
        product_menu.add_command(label="Export CSV", command=self.export_csv)

        # VOORRAAD MENU
        stock_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Voorraad", menu=stock_menu)
        stock_menu.add_command(label="Inboeken (+)", command=lambda: self.adjust_selected(+1))
        stock_menu.add_command(label="Uitboeken (-)", command=lambda: self.adjust_selected(-1))
        stock_menu.add_separator()
        stock_menu.add_command(label="Rapport lage voorraad", command=self.low_stock_report)

        # BOM MENU
        bom_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="BOM / Assemblage", menu=bom_menu)
        bom_menu.add_command(label="Toon BOM", command=self.show_bom)
        bom_menu.add_command(label="BOM Editor", command=self.open_bom_editor)
        bom_menu.add_command(label="Nieuw eindproduct", command=self.create_end_product)

        # ORDERS MENU
        order_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Orders", menu=order_menu)
        order_menu.add_command(label="Nieuwe order", command=self.new_order)
        order_menu.add_command(label="Toon orders", command=self.show_orders)
        order_menu.add_command(label="Verwerk order", command=self.handle_process_order)

        # ZOEKBALK
        
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=4)

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(top, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True)
        search_entry.bind("<KeyRelease>", lambda e: self.refresh_list())

        ttk.Button(top, text="Zoek", command=self.refresh_list).pack(side="left", padx=4)

        # HOOFDPANEEL (PRODUCTLIJST + DETAILS)
        main = ttk.PanedWindow(self, orient="horizontal")
        main.pack(fill="both", expand=True, padx=8, pady=4)
        main.config(height=260)   # lager hoofdscherm

        # LINKERPANEEL – PRODUCTLIJST
        left = ttk.Frame(main)
        main.add(left, weight=1)

        cols = ("sku", "name", "qty", "min_stock", "location")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=10)

        headings = [
            ("sku", "SKU"),
            ("name", "Naam"),
            ("qty", "Aantal"),
            ("min_stock", "Min"),
            ("location", "Locatie")
        ]

        for col, txt in headings:
            self.tree.heading(col, text=txt, command=lambda c=col: self.sort_by(c, False))
            self.tree.column(col, width=90)  # SMALLER COLUMNS

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.edit_selected())
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # RECHTERPANEEL – DETAILS
        right = ttk.Frame(main, width=300)
        main.add(right, weight=0)

        self.detail = tk.Text(right, width=40, height=12, state="disabled", wrap="word")
        self.detail.pack(fill="both", expand=True, padx=4, pady=4)

        # BOM + COMPONENTEN PANEL

        bom_panel = ttk.PanedWindow(self, orient="horizontal")
        bom_panel.pack(fill="both", expand=True, padx=8, pady=4)
        bom_panel.config(height=340)   # HOGER BOM PANEEL

        # BOM TREEVIEW
        bom_frame = ttk.LabelFrame(bom_panel, text="BOM-structuur")
        bom_panel.add(bom_frame, weight=1)

        self.bom_tree = ttk.Treeview(bom_frame, columns=("qty",), show="tree headings", height=12)
        self.bom_tree.heading("#0", text="Product / Component")
        self.bom_tree.heading("qty", text="Aantal")
        self.bom_tree.column("qty", width=80)
        self.bom_tree.pack(fill="both", expand=True, padx=4, pady=4)

        # COMPONENTEN TREEVIEW
        comp_frame = ttk.LabelFrame(bom_panel, text="Alle componenten")
        bom_panel.add(comp_frame, weight=1)

        self.comp_tree = ttk.Treeview(comp_frame, columns=("sku", "qty"), show="headings", height=12)
        self.comp_tree.heading("sku", text="SKU")
        self.comp_tree.heading("qty", text="Voorraad")
        self.comp_tree.column("sku", width=100)
        self.comp_tree.column("qty", width=60)
        self.comp_tree.pack(fill="both", expand=True, padx=4, pady=4)

        # STATUSBALK
  
        self.status = ttk.Label(self, text="Klaar", anchor="w")
        self.status.pack(fill="x", side="bottom", padx=4, pady=4)

        # SORTERING
        self._search_after_id = None
        self._sort_col = None
        self._sort_desc = False


    def show_bom(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Selectie", "Selecteer eerst een product")
            return
        parent_id = int(sel[0])
        bom_items = models.get_bom(parent_id)
        if not bom_items:
            messagebox.showinfo("BOM", "Geen BOM gevonden voor dit product")
            return
        txt = "\n".join(f"{name} (SKU:{sku}) x{qty}" for sku, name, qty in bom_items)
        messagebox.showinfo("BOM", txt)

    def open_bom_editor(self):
        item= self.tree.focus()
        if not item:
            messagebox.showinfo("Selectie", "Selecteer eerst een hoofdproduct")
            return

        parent_id = int(item)
        parent_prod = next((p for p in models.list_products() if p[0] == parent_id), None)

        if not parent_prod:
            messagebox.showerror("Fout", "Product niet gevonden")
            return

        BOMEditor(self, parent_id, parent_prod)

    def create_end_product(self):
    # Vraag basisgegevens
        name = simpledialog.askstring("Eindproduct", "Naam van het eindproduct:")
        if not name:
            return

        sku = simpledialog.askstring("Eindproduct", "SKU voor het eindproduct:")
        if not sku:
            return

        # Check of SKU al bestaat
        existing = [p for p in models.list_products() if p[1] == sku]
        if existing:
            messagebox.showerror("Fout", f"SKU '{sku}' bestaat al. Kies een andere SKU.")
            return

        # Maak product aan met voorraad 0
        pid = models.add_product(
            sku=sku,
            name=name,
            description="Samengesteld product",
            quantity=0,
            min_stock=0,
            location="BOM"
        )

        # Lijst verversen
        self.refresh_list()

        # Open direct de BOM-editor
        parent_prod = next((p for p in models.list_products() if p[0] == pid), None)
        BOMEditor(self, pid, parent_prod)

    def debounce_search(self, delay=300):
        if self._search_after_id:
            self.after_cancel(self._search_after_id)
            self._search_after_id = self.after(delay, self.refresh_list)

    def refresh_list(self):
    # Maak de Treeview leeg
        for i in self.tree.get_children():
            self.tree.delete(i)

    # Haal producten op uit de database (met zoekterm)
        items = models.list_products(self.search_var.get())

    # Optioneel sorteren
        if self._sort_col:
            idx = {"sku": 1, "name": 2, "qty": 4, "min_stock": 5, "location": 6}[self._sort_col]
            items.sort(key=lambda r: r[idx], reverse=self._sort_desc)

    # Altijd vullen met resultaten
        for row in items:
            pid, sku, name, desc, qty, min_stock, loc = row
            self.tree.insert("", "end", iid=str(pid), values=(sku, name, qty, min_stock, loc))

    # Pas kolombreedtes aan en update status
        self.adjust_column_widths()
        self.status.config(text=f"Totaal producten: {len(items)}")

        
    def adjust_column_widths(self):
            # Eenvoudige auto-width op basis van content
            for col in self.tree["columns"]:
                values = [str(self.tree.set(k, col)) for k in self.tree.get_children()]
                max_w = max((len(v) for v in values), default=10)
                self.tree.column(col, width=min(max_w*8+20, 300))

    def on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            self.set_detail_text("")
            return
        pid = int(sel[0])
        prod = next((r for r in models.list_products() if r[0]==pid), None)
        if not prod:
            self.set_detail_text("")
            return 
        _, sku, name, desc, qty, min_stock, loc = prod
        txt = f"SKU: {sku}\nNaam: {name}\nAantal: {qty}\nMin voorraad: {min_stock}\nLocatie: {loc}\n\nBeschrijving: {desc}"
        self.set_detail_text(txt)
        self.load_bom_tree(pid)
        self.load_component_tree()

    def load_bom_tree(self, parent_id):
    # Maak leeg
        for i in self.bom_tree.get_children():
            self.bom_tree.delete(i)

    # Haal BOM op
        bom_items = models.get_bom(parent_id)
        if not bom_items:
            return

    # Voeg toe
        for sku, name, qty in bom_items:
            self.bom_tree.insert("", "end", text=f"{name} (SKU:{sku})", values=(qty,))

    def load_component_tree(self):
        for i in self.comp_tree.get_children():
            self.comp_tree.delete(i)

        prods = models.list_products()
        for pid, sku, name, desc, qty, min_stock, loc in prods:
            self.comp_tree.insert("", "end", values=(sku, qty))

    def set_detail_text(self, text):
        self.detail.config(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("end", text)
        self.detail.config(state="disabled")

    def add_product(self):
        print("add_product aangeroepen")   #Debug
        dlg = ProductDialog(self, "Nieuw product")
        self.wait_window(dlg)
        if dlg.result:
            try:
                models.add_product(**dlg.result)
                self.refresh_list()
                self.status.config(text="Product toegevoegd")
            except Exception as e: 
                messagebox.showerror("Fout", str(e))

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel: return
        pid = int(sel[0])
        prod = next((r for r in models.list_products() if r[0]==pid), None)
        if not prod: return 
        dlg = ProductDialog(self, "Bewerk product", product=prod)
        self.wait_window(dlg)
        if dlg.result:
            models.update_product(pid, **dlg.result)
            self.refresh_list()
            self.status.config(text="Product bijgewerkt")

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel: return
        pid = int(sel[0])
        if messagebox.askyesno("Verwijderen", "weet je het zeker?"):
            models.delete_product(pid)
            self.refresh_list()
            self.status.config(text="Product verwijderd")

    def adjust_selected(self, delta):
        sel = self.tree.selection()
        if not sel: return
        pid = int(sel[0])
        amt = simpledialog.askinteger("Aanpassen", "Aantal:", initialvalue=abs(delta))
        if amt is None: return
        change = amt if delta>0 else -amt
        note = simpledialog.askstring("Notitie", "Optionele notitie:")
        models.adjust_quantity(pid, change, typ="in" if change>0 else "out", note=note or "")
        self.refresh_list()
        self.status.config(text=f"Voorraad aangepast({change})")

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not path: return
        count = 0
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    models.add_product(row.get("sku", ""), row.get("name", ""), row.get("description", ""), int(row.get("quantity", "") or 0), int(row.get("min_stock", "") or 0), 
                                       row.get("location", ""))
                    count += 1
                except Exception: 
                    continue 
                self.refresh_list()
                self.status.config(text=f"Import voltooid({count} rijen)")

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path: return
        items = models.list_products(self.search_var.get())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "sku", "name", "description", "quantity", "min_stock", "location"])
            for r in items:
                writer.writerow(r)
                self.status.config(text="Export Voltooid")
                #messagebox.showinfo("Export", "Export voltooid.")

    def low_stock_report(self):
        rows = models.list_products()
        low = [r for r in rows if r[4] <= r[5]]
        text = "\n".join(f"{r[2]} (SKU: {r[1]}) Aantal: {r[4]} Min: {r[5]}" for r in low) or "Geen lage voorraad."
        messagebox.showinfo("Lage voorraad", text)

    # Orders UI
    def new_order(self):
        # Eenvoudige dialog: selecteer producten en aantallen
        dlg = OrderDialog(self, "Nieuwe order")
        self.wait_window(dlg)
        if not dlg.result:
            return
        customer = dlg.result['customer']
        items = dlg.result['items']
        #[{'product_id':..., 'quantity':..., 'price':...}, ...]
        try: 
            order_id = models.create_order(customer, items)
            self.refresh_list()
            self.status.config(text=f"Order{order_id} aangemaakt")
        except Exception as e:
            messagebox.showerror("Fout bij order", str(e))

    def show_orders(self):
        rows = models.list_orders()
        txt = ""
        for r in rows:
            #r: (id, customer, status, total, created_at)
            txt += f"#{r[0]} klant:{r[1]} status:{r[2]} totaal:{r[3]} ({r[4]})\n"
            if not txt:
                txt = "Geen orders"
        messagebox.showinfo("Orders", txt)

    def sort_by(self, col, desc):
        if self._sort_col == col:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_col = col
            self._sort_desc = False
        self.refresh_list()

class ProductDialog(tk.Toplevel):
    def __init__(self, parent, title, product=None):
        super().__init__(parent)
        self.title(title)
        self.result = None
        labels = ["sku", "name", "description", "quantity", "min_stock", "location"]
        self.vars = {}

        for i, label in enumerate(labels):
            ttk.Label(self, text=label.capitalize()).grid(row=i, column=0, sticky="w", padx=8, pady=4)
            val = str(product[i+1]) if product else ""
            v = tk.StringVar(value=val)
            self.vars[label] = v
            ttk.Entry(self, textvariable=v, width=40).grid(row=i, column=1, padx=8, pady=4)

        # Knoppen buiten de lus
        ttk.Button(self, text="OK", command=self.on_ok).grid(row=len(labels), column=0, padx=8, pady=8)
        ttk.Button(self, text="Annuleer", command=self.destroy).grid(row=len(labels), column=1, padx=8, pady=8)
    
    def on_ok(self):
        try: 
            qty = int(self.vars["quantity"].get() or 0)
            min_stock = int(self.vars["min_stock"].get() or 0)
        except ValueError:
            messagebox.showerror("Fout", "Aantal en Min voorraad moeten getallen zijn.")
            return 
        self.result = {"sku": self.vars["sku"].get().strip(),
                       "name": self.vars["name"].get().strip(),
                       "description": self.vars["description"].get().strip(),
                       "quantity": qty, "min_stock": min_stock, "location": self.vars["location"].get().strip(),}
        self.destroy()

class OrderDialog(tk.Toplevel):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.title(title)
        self.result = None
        self.geometry("700x400")
        self.resizable(True, True)

        ttk.Label(self, text="Klant:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.customer_v = tk.StringVar()
        ttk.Entry(self, textvariable=self.customer_v, width=40).grid(row=0, column=1, padx=8, pady=4, columnspan=2, sticky="w")

        # Product zoeken en toevoegen
        ttk.Label(self, text="Product zoeken:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.prod_search_v = tk.StringVar()
        prod_entry = ttk.Entry(self, textvariable=self.prod_search_v, width=40)
        prod_entry.grid(row=1, column=2, padx=4, pady=4, sticky="w")

        #resultaten listbox
        self.search_list = tk.Listbox(self, height=6)
        self.search_list.grid(row=2, column=0, columnspan=2, padx=8, sticky="nsew")
        self.search_list.bind("<Double-1>", lambda e: self.add_selected_products())
        ttk.Button(self, text="Voeg toe", command=self.add_selected_products).grid(row=2, column=2, padx=4)

        #Order lines treeview
        cols = ("product_id", "sku", "name", "qty", "price", "line_total")
        self.lines = ttk.Treeview(self, columns=cols, show="headings", height=8)
        headings = [("sku", "SKU"), ("name", "Naam"), ("qty", "Aantal"), ("price", "Prijs"), ("line_total", "Totaal")]
        for col, txt in headings:
            self.lines.heading(col, text=txt)
            self.lines.column(col, width=100)
            self.lines.grid(row=3, column=0, columnspan=3, padx=8, pady=8, sticky="nsew")
            self.lines.bind("<Delete>", lambda e: self.remove_selected_line())

        #Totals and buttons
        self.total_label = ttk.Label(self, text="Totaal: 0")
        self.total_label.grid(row=4, column=0, sticky="w", padx=8)
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=4, column=1, columnspan=2, sticky="e", padx=8)
        ttk.Button(btn_frame, text="OK", command=self.on_ok).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Annuleer", command=self.destroy).pack(side="left", padx=4)

        #layout weight
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(1, weight=1)

        #Cache
        self._search_results = []
        #list of product tuples
        self._lines = {} #iid -> dict
        #Preload empty search
        self.search_products()
    
    def search_products(self):
        q = self.prod_search_v.get().strip()
        prods = models.list_products(q)
        self.search_list.delete(0, "end")
        self._search_results = prods
        for p in prods:
            pid, sku, name, desc, qty, min_stock, loc = p
            self.search_list.insert("end", f"{name} (SKU:{sku}) - voorraad:{qty}")

    def add_selected_products(self):
        sel = self.search_list.curselection()
        if not sel:
            messagebox.showinfo("Selectie", "Selecteer eerst een product in de zoekresultaten")
            return
        
        idx = sel[0]
        p = self._search_results[idx]
        pid, sku, name, desc, avail, min_stock, loc = p

        #Vraag hoeveelheid en prijs
        qty = simpledialog.askinteger("Aantal", f"Aantal voor {name}:", initialvalue=1, minvalue=1)
        if qty is None:
            return
        price = simpledialog.askfloat("Prijs", f"Prijs per eenheid voor {name} (optioneel):", initialvalue=0.0)
        if price is None:
            price = 0.0

    # Check of dit al in de regels staat -> verhoog hoeveelheid
        for iid in self.lines.get_children():
            vals = self.lines.item(iid, "values")
            if int(vals[0]) == pid:
                new_qty = int(vals[3]) + qty 
                line_total = new_qty * float(vals[4])
                self.lines.item(iid, values=(vals[0], vals[1], vals[2], new_qty, f"{float(price):.2f}", f"{line_total:.2f}"))
                self.update_total()
                return
        # Als product nog niet bestaat -> nieuw toevoegen
        line_total = qty * price
        iid = self.lines.insert("", "end", values=(pid, sku, name, qty, f"{price:.2f}", f"{line_total:.2f}"))
        self._lines[iid] = {"product_id":pid, "quantity":qty, "price":price}
        self.update_total()

    def remove_selected_line(self):
        sel = self.lines.selection()
        if not sel:
            return
        for iid in sel:
            self.lines.delete(iid)
            self._lines.pop(iid, None)
            self.update_total()

    def update_total(self):
        total = 0.0
        for iid in self.lines.get_children():
            vals = self.lines.item(iid, "values")
            total += float(vals[5])
        self.total_label.config(text=f"Totaal: {total:.2f}")
    
    def on_ok(self):
        items = []
        # Verzamel alle orderregels uit de Treeview
        for iid in self.lines.get_children():
            vals = self.lines.item(iid, "values")
            pid = int(vals[0])
            qty = int(vals[3])
            price = float(vals[4])

            if qty <= 0:
                messagebox.showerror("Fout", f"Aantal voor {vals[2]} moet groter dan 0 zijn.")
                return

            items.append({"product_id": pid, "quantity": qty, "price": price})

        # Controleer of er überhaupt regels zijn
        if not items:
            messagebox.showerror("Fout", "Geen orderregels toegevoegd")
            return

        # Klantnaam ophalen
        customer = self.customer_v.get().strip() or "Klant"

        # Voorraadcontrole
        shortages = []
        for it in items:
            pid = it['product_id']
            cur = next((p for p in models.list_products() if p[0] == pid), None)
            if cur and cur[4] < it['quantity']:
                shortages.append((cur[2], cur[4], it['quantity']))

        if shortages:
            msg = "Onvoldoende voorraad voor:\n" + "\n".join(
                f"{n} (beschikbaar {a}, gevraagd {q})" for n, a, q in shortages
            )
            if not messagebox.askyesno(
                "Onvoldoende voorraad",
                msg + "\n\nWil je de order toch plaatsen (voorraad kan negatief worden)?"
            ):
                return

        # Resultaat opslaan en dialoog sluiten
        self.result = {"customer": customer, "items": items}
        self.destroy()

class BOMEditor(tk.Toplevel):
    def __init__(self, parent, parent_id, parent_prod):
        super().__init__(parent)
        self.title(f"BOM voor {parent_prod[2]} (SKU: {parent_prod[1]})")
        self.geometry("900x600")
        self.parent_id = parent_id

        # Layout: 2 kolommen
        main = ttk.PanedWindow(self, orient="horizontal")
        main.pack(fill="both", expand=True)

        # -----------------------------
        # LINKERZIJDE: BOM TREEVIEW
        # -----------------------------
        left = ttk.Frame(main)
        main.add(left, weight=1)

        ttk.Label(left, text="BOM-structuur", font=("Arial", 12, "bold")).pack(anchor="w", padx=6, pady=6)

        self.tree = ttk.Treeview(left, columns=("qty",), show="tree headings")
        self.tree.heading("#0", text="Product / Component")
        self.tree.heading("qty", text="Aantal")
        self.tree.column("qty", width=80)
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)

        self.tree.bind("<Double-1>", self.edit_quantity)

        # -----------------------------
        # RECHTERZIJDE: COMPONENT SELECTIE
        # -----------------------------
        right = ttk.Frame(main)
        main.add(right, weight=1)

        ttk.Label(right, text="Componenten zoeken", font=("Arial", 12, "bold")).pack(anchor="w", padx=6, pady=6)

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(right, textvariable=self.search_var)
        search_entry.pack(fill="x", padx=6)
        search_entry.bind("<KeyRelease>", lambda e: self.update_component_list())

        self.comp_list = tk.Listbox(right, height=20)
        self.comp_list.pack(fill="both", expand=True, padx=6, pady=6)
        self.comp_list.bind("<Double-1>", self.add_selected_component)

        # Knoppen
        btn_frame = ttk.Frame(right)
        btn_frame.pack(fill="x", pady=6)

        ttk.Button(btn_frame, text="Verwijder geselecteerde", command=self.remove_component).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Sluiten", command=self.destroy).pack(side="right", padx=4)

        # Data laden
        self.refresh_bom()
        self.update_component_list()

    # -----------------------------
    # BOM LADEN (RECURSIEF)
    # -----------------------------
    def refresh_bom(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        self.build_bom_tree(self.parent_id, "")

    def build_bom_tree(self, parent_id, parent_node):
        items = models.get_bom(parent_id)
        for sku, name, qty in items:
            comp = next((p for p in models.list_products() if p[1] == sku), None)
            comp_id = comp[0] if comp else None

            node = self.tree.insert(parent_node, "end", text=f"{name} (SKU:{sku})", values=(qty,))

            # Als dit component zelf ook een BOM heeft → recursief
            if models.get_bom(comp_id):
                self.build_bom_tree(comp_id, node)

    # -----------------------------
    # COMPONENT SELECTIE
    # -----------------------------
    def update_component_list(self):
        q = self.search_var.get().lower()
        prods = models.list_products()

        self.comp_list.delete(0, "end")

        for p in prods:
            pid, sku, name, desc, qty, min_stock, loc = p
            if q in name.lower() or q in sku.lower():
                self.comp_list.insert("end", f"{name} (SKU:{sku})")

    def add_selected_component(self, event=None):
        sel = self.comp_list.curselection()
        if not sel:
            return

        text = self.comp_list.get(sel[0])
        sku = text.split("SKU:")[1].replace(")", "").strip()

        comp = next((p for p in models.list_products() if p[1] == sku), None)
        if not comp:
            return

        comp_id = comp[0]

        qty = simpledialog.askinteger("Aantal", f"Aantal voor {comp[2]}:", initialvalue=1)
        if not qty:
            return

        models.create_bom(self.parent_id, [(comp_id, qty)])
        self.refresh_bom()

    # -----------------------------
    # HOEVEELHEID AANPASSEN
    # -----------------------------
    def edit_quantity(self, event=None):
        item = self.tree.focus()
        if not item:
            return

        text = self.tree.item(item, "text")
        sku = text.split("SKU:")[1].replace(")", "").strip()

        comp = next((p for p in models.list_products() if p[1] == sku), None)
        if not comp:
            return

        comp_id = comp[0]
        old_qty = int(self.tree.item(item, "values")[0])

        new_qty = simpledialog.askinteger("Aantal aanpassen", f"Nieuw aantal voor {comp[2]}:", initialvalue=old_qty)
        if new_qty is None:
            return

        with models.get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE bom SET quantity=? 
                WHERE parent_product_id=? AND component_product_id=?
            """, (new_qty, self.parent_id, comp_id))
            conn.commit()

        self.refresh_bom()

    # -----------------------------
    # COMPONENT VERWIJDEREN
    # -----------------------------
    def remove_component(self):
        item = self.tree.focus()
        if not item:
            messagebox.showinfo("Selectie", "Selecteer een component om te verwijderen")
            return

        text = self.tree.item(item, "text")
        sku = text.split("SKU:")[1].replace(")", "").strip()

        comp = next((p for p in models.list_products() if p[1] == sku), None)
        if not comp:
            return

        comp_id = comp[0]

        with models.get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM bom WHERE parent_product_id=? AND component_product_id=?",
                        (self.parent_id, comp_id))
            conn.commit()

        self.refresh_bom()
