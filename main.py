
import os
import csv
import shutil
import sqlite3
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from kivy.app import App
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.filechooser import FileChooserListView
from kivy.clock import Clock
from kivy.utils import platform

KV = r"""
#:import dp kivy.metrics.dp

<NavButton@Button>:
    background_normal: ""
    background_color: (0.08,0.09,0.11,1) if self.state == "normal" else (0.16,0.17,0.20,1)
    color: (0.92,0.94,0.98,1)
    font_size: "14sp"
    size_hint_y: None
    height: dp(48)

<PrimaryButton@Button>:
    background_normal: ""
    background_color: (0.12,0.12,0.14,1)
    color: 1,1,1,1
    bold: True
    size_hint_y: None
    height: dp(48)

<POSScreen>:
    BoxLayout:
        orientation: "vertical"
        padding: dp(12)
        spacing: dp(10)
        canvas.before:
            Color:
                rgba: 0.96,0.97,0.98,1
            Rectangle:
                pos: self.pos
                size: self.size

        BoxLayout:
            size_hint_y: None
            height: dp(50)
            Label:
                text: "KASIR"
                font_size: "22sp"
                bold: True
                color: 0.08,0.09,0.11,1
                halign: "left"
                text_size: self.size
                valign: "middle"
            TextInput:
                id: search
                hint_text: "Cari produk / SKU..."
                multiline: False
                size_hint_x: .65
                on_text: root.refresh_products(self.text)

        BoxLayout:
            spacing: dp(10)
            ScrollView:
                do_scroll_x: False
                GridLayout:
                    id: products
                    cols: 2
                    spacing: dp(8)
                    padding: dp(2)
                    size_hint_y: None
                    height: self.minimum_height

            BoxLayout:
                orientation: "vertical"
                size_hint_x: .40
                spacing: dp(8)
                Label:
                    text: "KERANJANG"
                    bold: True
                    font_size: "16sp"
                    size_hint_y: None
                    height: dp(35)
                    color: .1,.1,.12,1
                ScrollView:
                    do_scroll_x: False
                    GridLayout:
                        id: cart
                        cols: 1
                        spacing: dp(5)
                        size_hint_y: None
                        height: self.minimum_height
                BoxLayout:
                    size_hint_y: None
                    height: dp(42)
                    Label:
                        text: "Subtotal"
                        color: .1,.1,.12,1
                    Label:
                        id: subtotal
                        text: "Rp 0"
                        bold: True
                        color: .1,.1,.12,1
                BoxLayout:
                    size_hint_y: None
                    height: dp(42)
                    Label:
                        text: "Diskon"
                        color: .1,.1,.12,1
                    TextInput:
                        id: discount
                        text: "0"
                        input_filter: "float"
                        multiline: False
                        on_text: root.update_totals()
                BoxLayout:
                    size_hint_y: None
                    height: dp(42)
                    Label:
                        text: "Pajak %"
                        color: .1,.1,.12,1
                    TextInput:
                        id: tax
                        text: app.tax_percent
                        input_filter: "float"
                        multiline: False
                        on_text: root.update_totals()
                Label:
                    id: total
                    text: "TOTAL  Rp 0"
                    bold: True
                    font_size: "19sp"
                    color: .05,.05,.07,1
                    size_hint_y: None
                    height: dp(48)
                Spinner:
                    id: payment
                    text: "Tunai"
                    values: ["Tunai","QRIS","Debit","Kredit","Transfer","E-Wallet"]
                    size_hint_y: None
                    height: dp(46)
                TextInput:
                    id: paid
                    hint_text: "Jumlah dibayar (tunai)"
                    input_filter: "float"
                    multiline: False
                    size_hint_y: None
                    height: dp(46)
                    on_text: root.update_change()
                Label:
                    id: change
                    text: "Kembalian  Rp 0"
                    size_hint_y: None
                    height: dp(38)
                    color: .1,.1,.12,1
                Button:
                    text: "SELESAIKAN & CETAK"
                    background_normal: ""
                    background_color: (0.05,0.05,0.06,1)
                    color: 1,1,1,1
                    bold: True
                    size_hint_y: None
                    height: dp(52)
                    on_release: root.checkout()
                Button:
                    text: "Kosongkan"
                    size_hint_y: None
                    height: dp(40)
                    on_release: root.clear_cart()

<ProductScreen>:
    BoxLayout:
        orientation: "vertical"
        padding: dp(12)
        spacing: dp(10)
        canvas.before:
            Color:
                rgba: .96,.97,.98,1
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(48)
            Label:
                text: "PRODUK"
                font_size: "22sp"
                bold: True
                color: .08,.09,.11,1
            Button:
                text: "+ Produk"
                size_hint_x: .3
                on_release: root.open_editor()
        ScrollView:
            GridLayout:
                id: list
                cols: 1
                spacing: dp(7)
                padding: dp(2)
                size_hint_y: None
                height: self.minimum_height

<TransactionScreen>:
    BoxLayout:
        orientation: "vertical"
        padding: dp(12)
        spacing: dp(10)
        canvas.before:
            Color:
                rgba: .96,.97,.98,1
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "TRANSAKSI"
            font_size: "22sp"
            bold: True
            color: .08,.09,.11,1
            size_hint_y: None
            height: dp(48)
        ScrollView:
            GridLayout:
                id: list
                cols: 1
                spacing: dp(7)
                size_hint_y: None
                height: self.minimum_height

<ReportScreen>:
    BoxLayout:
        orientation: "vertical"
        padding: dp(12)
        spacing: dp(12)
        canvas.before:
            Color:
                rgba: .96,.97,.98,1
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "LAPORAN"
            font_size: "22sp"
            bold: True
            color: .08,.09,.11,1
            size_hint_y: None
            height: dp(48)
        Label:
            id: summary
            text: "Memuat..."
            color: .1,.1,.12,1
            font_size: "17sp"
            text_size: self.width, None
            halign: "left"
        Button:
            text: "Export CSV"
            size_hint_y: None
            height: dp(48)
            on_release: root.export_csv()

<SettingsScreen>:
    BoxLayout:
        orientation: "vertical"
        padding: dp(12)
        spacing: dp(9)
        canvas.before:
            Color:
                rgba: .96,.97,.98,1
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "PENGATURAN"
            font_size: "22sp"
            bold: True
            color: .08,.09,.11,1
            size_hint_y: None
            height: dp(48)
        TextInput:
            id: store
            hint_text: "Nama usaha"
            multiline: False
        TextInput:
            id: address
            hint_text: "Alamat / kontak"
            multiline: False
        TextInput:
            id: footer
            hint_text: "Footer struk"
            multiline: False
        Spinner:
            id: paper
            text: "58mm"
            values: ["58mm","80mm"]
            size_hint_y: None
            height: dp(46)
        Button:
            text: "Simpan Pengaturan"
            size_hint_y: None
            height: dp(48)
            on_release: root.save()
        Button:
            text: "Backup Database"
            size_hint_y: None
            height: dp(48)
            on_release: root.backup()
        Label:
            text: "Bluetooth: printer thermal harus sudah dipairing di Android. Dari kasir, pilih perangkat yang tersedia."
            color: .25,.25,.28,1
            text_size: self.width, None

BoxLayout:
    orientation: "vertical"
    ScreenManager:
        id: sm
        POSScreen:
            name: "pos"
        ProductScreen:
            name: "products"
        TransactionScreen:
            name: "transactions"
        ReportScreen:
            name: "reports"
        SettingsScreen:
            name: "settings"
    BoxLayout:
        size_hint_y: None
        height: dp(58)
        spacing: dp(3)
        padding: dp(3)
        NavButton:
            text: "Kasir"
            on_release: sm.current = "pos"
        NavButton:
            text: "Produk"
            on_release: sm.current = "products"
        NavButton:
            text: "Transaksi"
            on_release: sm.current = "transactions"
        NavButton:
            text: "Laporan"
            on_release: sm.current = "reports"
        NavButton:
            text: "Setting"
            on_release: sm.current = "settings"
"""

def money(v):
    try:
        q = Decimal(str(v)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return f"Rp {q:,}".replace(",", ".")
    except Exception:
        return "Rp 0"

class DB:
    def __init__(self, path):
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.setup()

    def setup(self):
        c = self.conn.cursor()
        c.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT DEFAULT '',
            category TEXT DEFAULT '',
            price REAL NOT NULL DEFAULT 0,
            cost REAL NOT NULL DEFAULT 0,
            stock REAL NOT NULL DEFAULT 0,
            image TEXT DEFAULT '',
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sales(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice TEXT UNIQUE NOT NULL,
            subtotal REAL NOT NULL,
            discount REAL NOT NULL,
            tax REAL NOT NULL,
            total REAL NOT NULL,
            payment_method TEXT NOT NULL,
            paid REAL NOT NULL,
            change_amount REAL NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sale_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            qty REAL NOT NULL,
            price REAL NOT NULL,
            line_total REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """)
        defaults = {
            "store_name": "UniversalPOS Store",
            "store_address": "Alamat / Kontak",
            "receipt_footer": "Terima kasih telah berbelanja",
            "paper": "58mm",
            "tax_percent": "0",
        }
        for k,v in defaults.items():
            c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",(k,v))
        self.conn.commit()

    def setting(self,k):
        row=self.conn.execute("SELECT value FROM settings WHERE key=?",(k,)).fetchone()
        return row["value"] if row else ""

    def set_setting(self,k,v):
        self.conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",(k,str(v)))
        self.conn.commit()

    def products(self, search=""):
        if search:
            q=f"%{search}%"
            return self.conn.execute("""SELECT * FROM products WHERE active=1 AND
                (name LIKE ? OR sku LIKE ? OR category LIKE ?) ORDER BY name""",(q,q,q)).fetchall()
        return self.conn.execute("SELECT * FROM products WHERE active=1 ORDER BY name").fetchall()

    def add_product(self, name, sku, category, price, cost, stock, image=""):
        self.conn.execute("""INSERT INTO products
            (name,sku,category,price,cost,stock,image,created_at)
            VALUES(?,?,?,?,?,?,?,?)""",
            (name,sku,category,float(price),float(cost),float(stock),image,datetime.now().isoformat(timespec="seconds")))
        self.conn.commit()

    def update_stock(self, pid, qty):
        self.conn.execute("UPDATE products SET stock=stock-? WHERE id=?",(qty,pid))
        self.conn.commit()

    def create_sale(self, cart, subtotal, discount, tax, total, method, paid, change):
        invoice="INV-"+datetime.now().strftime("%Y%m%d%H%M%S%f")[-14:]
        now=datetime.now().isoformat(timespec="seconds")
        c=self.conn.cursor()
        c.execute("""INSERT INTO sales(invoice,subtotal,discount,tax,total,payment_method,paid,change_amount,created_at)
                     VALUES(?,?,?,?,?,?,?,?,?)""",
                  (invoice,subtotal,discount,tax,total,method,paid,change,now))
        sid=c.lastrowid
        for item in cart:
            c.execute("""INSERT INTO sale_items(sale_id,product_id,name,qty,price,line_total)
                         VALUES(?,?,?,?,?,?)""",
                      (sid,item["id"],item["name"],item["qty"],item["price"],item["qty"]*item["price"]))
            c.execute("UPDATE products SET stock=stock-? WHERE id=?",(item["qty"],item["id"]))
        self.conn.commit()
        return invoice

    def sales(self, limit=100):
        return self.conn.execute("SELECT * FROM sales ORDER BY id DESC LIMIT ?",(limit,)).fetchall()

    def sale_items(self, invoice):
        return self.conn.execute("""SELECT si.* FROM sale_items si
          JOIN sales s ON s.id=si.sale_id WHERE s.invoice=? ORDER BY si.id""",(invoice,)).fetchall()

class POSScreen(Screen):
    def on_enter(self):
        self.app = App.get_running_app()
        self.cart_data = getattr(self, "cart_data", [])
        self.refresh_products()

    def refresh_products(self, text=""):
        box=self.ids.products
        box.clear_widgets()
        rows=self.app.db.products(text)
        for p in rows:
            b=BoxLayout(orientation="vertical", size_hint_y=None, height=dp(125), padding=dp(5))
            if p["image"] and os.path.exists(p["image"]):
                img=Image(source=p["image"], size_hint_y=.58)
                b.add_widget(img)
            else:
                b.add_widget(Label(text="📦", font_size="28sp", size_hint_y=.58, color=(.2,.2,.22,1)))
            name=Label(text=f'{p["name"]}\n{money(p["price"])} | stok {p["stock"]:g}',
                       color=(.08,.09,.11,1), halign="center")
            name.bind(size=lambda inst,val: setattr(inst,"text_size",val))
            b.add_widget(name)
            b.bind(on_touch_down=lambda inst,touch,p=p: self.add_product(p) if inst.collide_point(*touch.pos) and touch.is_double_tap else None)
            # Button overlay for reliable tapping
            btn=Button(text=f'{p["name"]}\n{money(p["price"])}',
                       background_normal="", background_color=(1,1,1,.04),
                       color=(.05,.05,.06,1), size_hint_y=1)
            btn.bind(on_release=lambda *_ ,p=p:self.add_product(p))
            box.add_widget(btn)

    def add_product(self,p):
        if float(p["stock"]) <= 0:
            self.app.notify("Stok produk habis.")
            return
        for item in self.cart_data:
            if item["id"]==p["id"]:
                if item["qty"]+1 > float(p["stock"]):
                    self.app.notify("Jumlah melebihi stok.")
                    return
                item["qty"]+=1
                self.render_cart()
                return
        self.cart_data.append({"id":p["id"],"name":p["name"],"price":float(p["price"]),"qty":1,"stock":float(p["stock"])})
        self.render_cart()

    def render_cart(self):
        box=self.ids.cart
        box.clear_widgets()
        for idx,item in enumerate(self.cart_data):
            row=BoxLayout(size_hint_y=None,height=dp(55),spacing=dp(4))
            lbl=Label(text=f'{item["name"]}\n{item["qty"]:g} × {money(item["price"])}',
                      color=(.08,.09,.11,1), halign="left")
            lbl.bind(size=lambda inst,val:setattr(inst,"text_size",val))
            row.add_widget(lbl)
            minus=Button(text="−",size_hint_x=.22)
            plus=Button(text="+",size_hint_x=.22)
            delete=Button(text="×",size_hint_x=.22)
            minus.bind(on_release=lambda *_ ,i=idx:self.change_qty(i,-1))
            plus.bind(on_release=lambda *_ ,i=idx:self.change_qty(i,1))
            delete.bind(on_release=lambda *_ ,i=idx:self.remove_item(i))
            row.add_widget(minus); row.add_widget(plus); row.add_widget(delete)
            box.add_widget(row)
        self.update_totals()

    def change_qty(self,i,delta):
        if not 0<=i<len(self.cart_data): return
        item=self.cart_data[i]
        item["qty"]+=delta
        if item["qty"]<=0: self.cart_data.pop(i)
        elif item["qty"]>item["stock"]: item["qty"]=item["stock"]
        self.render_cart()

    def remove_item(self,i):
        if 0<=i<len(self.cart_data):
            self.cart_data.pop(i)
            self.render_cart()

    def update_totals(self,*_):
        subtotal=sum(x["qty"]*x["price"] for x in self.cart_data)
        try: discount=max(0,float(self.ids.discount.text or 0))
        except: discount=0
        try: taxp=max(0,float(self.ids.tax.text or 0))
        except: taxp=0
        taxable=max(0,subtotal-discount)
        tax=taxable*taxp/100
        total=max(0,taxable+tax)
        self.ids.subtotal.text=money(subtotal)
        self.ids.total.text=f"TOTAL  {money(total)}"
        self.update_change()
        return subtotal,discount,tax,total

    def update_change(self,*_):
        try: total=self.update_totals_no_recurse()
        except: total=0
        try: paid=float(self.ids.paid.text or 0)
        except: paid=0
        method=self.ids.payment.text
        change=max(0,paid-total) if method=="Tunai" else 0
        self.ids.change.text=f"Kembalian  {money(change)}"

    def update_totals_no_recurse(self):
        subtotal=sum(x["qty"]*x["price"] for x in self.cart_data)
        try: discount=max(0,float(self.ids.discount.text or 0))
        except: discount=0
        try: taxp=max(0,float(self.ids.tax.text or 0))
        except: taxp=0
        return max(0,(subtotal-discount)*(1+taxp/100))

    def clear_cart(self):
        self.cart_data=[]
        self.render_cart()
        self.ids.discount.text="0"
        self.ids.paid.text=""

    def checkout(self):
        if not self.cart_data:
            self.app.notify("Keranjang masih kosong.")
            return
        subtotal,discount,tax,total=self.update_totals()
        method=self.ids.payment.text
        try: paid=float(self.ids.paid.text or 0)
        except: paid=0
        if method=="Tunai":
            if paid < total:
                self.app.notify(f"Uang kurang {money(total-paid)}")
                return
            change=paid-total
        else:
            paid=total
            change=0
        invoice=self.app.db.create_sale(self.cart_data,subtotal,discount,tax,total,method,paid,change)
        self.app.last_receipt=(invoice,subtotal,discount,tax,total,method,paid,change,list(self.cart_data))
        self.app.print_or_offer(invoice)
        self.clear_cart()
        self.app.root.ids.sm.current="transactions"

class ProductScreen(Screen):
    def on_enter(self):
        self.app=App.get_running_app()
        self.refresh()

    def refresh(self):
        box=self.ids.list; box.clear_widgets()
        for p in self.app.db.products():
            row=BoxLayout(size_hint_y=None,height=dp(70),spacing=dp(7))
            if p["image"] and os.path.exists(p["image"]):
                row.add_widget(Image(source=p["image"],size_hint_x=.16))
            info=Label(text=f'{p["name"]}  •  {p["sku"] or "-"}\n{money(p["price"])}  • stok {p["stock"]:g}\n{p["category"] or "Tanpa kategori"}',
                       color=(.08,.09,.11), halign="left")
            info.bind(size=lambda inst,val:setattr(inst,"text_size",val))
            row.add_widget(info)
            box.add_widget(row)

    def open_editor(self):
        content=BoxLayout(orientation="vertical",spacing=dp(7),padding=dp(10))
        fields={}
        for key,hint in [("name","Nama produk *"),("sku","SKU / Barcode"),("category","Kategori"),
                         ("price","Harga jual"),("cost","Harga modal"),("stock","Stok")]:
            ti=TextInput(hint_text=hint,multiline=False,size_hint_y=None,height=dp(42))
            fields[key]=ti; content.add_widget(ti)
        choose=Button(text="Pilih Foto Produk",size_hint_y=None,height=dp(42))
        content.add_widget(choose)
        selected={"path":""}
        save=Button(text="Simpan",size_hint_y=None,height=dp(46))
        content.add_widget(save)
        pop=Popup(title="Tambah Produk",content=content,size_hint=(.92,.85))
        choose.bind(on_release=lambda *_: self.pick_image(selected))
        def do_save(*_):
            if not fields["name"].text.strip():
                self.app.notify("Nama produk wajib diisi."); return
            try:
                price=float(fields["price"].text or 0); cost=float(fields["cost"].text or 0); stock=float(fields["stock"].text or 0)
            except:
                self.app.notify("Harga/stok tidak valid."); return
            img=""
            if selected["path"] and os.path.isfile(selected["path"]):
                dest=os.path.join(self.app.images_dir, datetime.now().strftime("%Y%m%d%H%M%S%f")+"."+selected["path"].split(".")[-1].lower())
                shutil.copy2(selected["path"],dest); img=dest
            self.app.db.add_product(fields["name"].text.strip(),fields["sku"].text.strip(),
                                    fields["category"].text.strip(),price,cost,stock,img)
            pop.dismiss(); self.refresh()
        save.bind(on_release=do_save)
        pop.open()

    def pick_image(self, selected):
        fc=FileChooserListView(path="/storage/emulated/0", filters=["*.png","*.jpg","*.jpeg","*.webp"])
        box=BoxLayout(orientation="vertical")
        box.add_widget(fc)
        row=BoxLayout(size_hint_y=None,height=dp(48))
        ok=Button(text="Pilih"); cancel=Button(text="Batal")
        row.add_widget(ok); row.add_widget(cancel); box.add_widget(row)
        pop=Popup(title="Pilih foto produk",content=box,size_hint=(.95,.9))
        ok.bind(on_release=lambda *_: (selected.update(path=fc.selection[0]) if fc.selection else None, pop.dismiss()))
        cancel.bind(on_release=pop.dismiss)
        pop.open()

class TransactionScreen(Screen):
    def on_enter(self):
        self.app=App.get_running_app()
        self.refresh()
    def refresh(self):
        box=self.ids.list; box.clear_widgets()
        for s in self.app.db.sales():
            box.add_widget(Label(text=f'{s["invoice"]}  •  {s["created_at"]}\n{money(s["total"])}  •  {s["payment_method"]}',
                                 color=(.08,.09,.11),halign="left",size_hint_y=None,height=dp(58)))

class ReportScreen(Screen):
    def on_enter(self):
        self.app=App.get_running_app()
        self.refresh()
    def refresh(self):
        rows=self.app.db.conn.execute("""SELECT
          COUNT(*) n, COALESCE(SUM(subtotal),0) subtotal,
          COALESCE(SUM(discount),0) discount, COALESCE(SUM(tax),0) tax,
          COALESCE(SUM(total),0) total FROM sales
          WHERE date(created_at)=date('now')""").fetchone()
        self.ids.summary.text=(f"HARI INI\n\n"
          f"Transaksi : {rows['n']}\n"
          f"Subtotal  : {money(rows['subtotal'])}\n"
          f"Diskon    : {money(rows['discount'])}\n"
          f"Pajak     : {money(rows['tax'])}\n"
          f"Penjualan : {money(rows['total'])}")

    def export_csv(self):
        path=os.path.join(self.app.user_data_dir,"sales_export.csv")
        with open(path,"w",newline="",encoding="utf-8-sig") as f:
            w=csv.writer(f)
            w.writerow(["Invoice","Tanggal","Subtotal","Diskon","Pajak","Total","Pembayaran","Dibayar","Kembalian"])
            for s in self.app.db.sales(10000):
                w.writerow([s["invoice"],s["created_at"],s["subtotal"],s["discount"],s["tax"],s["total"],s["payment_method"],s["paid"],s["change_amount"]])
        self.app.notify(f"CSV tersimpan di:\n{path}")

class SettingsScreen(Screen):
    def on_enter(self):
        self.app=App.get_running_app()
        self.ids.store.text=self.app.db.setting("store_name")
        self.ids.address.text=self.app.db.setting("store_address")
        self.ids.footer.text=self.app.db.setting("receipt_footer")
        self.ids.paper.text=self.app.db.setting("paper") or "58mm"
    def save(self):
        self.app.db.set_setting("store_name",self.ids.store.text)
        self.app.db.set_setting("store_address",self.ids.address.text)
        self.app.db.set_setting("receipt_footer",self.ids.footer.text)
        self.app.db.set_setting("paper",self.ids.paper.text)
        self.app.notify("Pengaturan disimpan.")
    def backup(self):
        target=os.path.join(self.app.user_data_dir,"UniversalPOS_backup.db")
        self.app.db.conn.commit()
        shutil.copy2(self.app.db.path,target)
        self.app.notify(f"Backup dibuat:\n{target}")

class UniversalPOS(App):
    tax_percent=StringProperty("0")
    last_receipt=None

    def build(self):
        self.title="UniversalPOS"
        self.user_data_dir=os.path.expanduser(self.user_data_dir)
        os.makedirs(self.user_data_dir,exist_ok=True)
        self.images_dir=os.path.join(self.user_data_dir,"products")
        os.makedirs(self.images_dir,exist_ok=True)
        self.db=DB(os.path.join(self.user_data_dir,"UniversalPOS.db"))
        self.tax_percent=self.db.setting("tax_percent") or "0"
        self.request_android_permissions()
        return Builder.load_string(KV)

    def on_start(self):
        Clock.schedule_once(lambda *_: self.root.ids.sm.get_screen("pos").refresh_products(), .2)

    def request_android_permissions(self):
        if platform != "android":
            return
        try:
            from android.permissions import request_permissions, Permission
            perms=[]
            for name in ("BLUETOOTH_SCAN","BLUETOOTH_CONNECT","READ_MEDIA_IMAGES","READ_EXTERNAL_STORAGE"):
                if hasattr(Permission,name):
                    perms.append(getattr(Permission,name))
            if perms: request_permissions(perms)
        except Exception as e:
            print("Permission request:",e)

    def notify(self,msg):
        Popup(title="UniversalPOS",content=Label(text=msg),size_hint=(.85,.35)).open()

    def print_or_offer(self, invoice):
        content=BoxLayout(orientation="vertical",spacing=dp(8),padding=dp(10))
        content.add_widget(Label(text=f"Transaksi {invoice} berhasil.\nCetak struk sekarang?"))
        row=BoxLayout(size_hint_y=None,height=dp(48),spacing=dp(7))
        bt=Button(text="Bluetooth")
        no=Button(text="Tidak")
        row.add_widget(bt); row.add_widget(no); content.add_widget(row)
        pop=Popup(title="Struk",content=content,size_hint=(.88,.4))
        bt.bind(on_release=lambda *_:(pop.dismiss(),self.bluetooth_printer_dialog()))
        no.bind(on_release=pop.dismiss)
        pop.open()

    def bluetooth_printer_dialog(self):
        devices=self.get_bonded_devices()
        if not devices:
            self.notify("Tidak ada printer/perangkat Bluetooth yang sudah dipairing.\nPair printer thermal terlebih dahulu di Android.")
            return
        box=BoxLayout(orientation="vertical",spacing=dp(6),padding=dp(8))
        for name,addr in devices:
            b=Button(text=f"{name}\n{addr}",size_hint_y=None,height=dp(58))
            b.bind(on_release=lambda *_ ,a=addr:self.print_bluetooth(a))
            box.add_widget(b)
        Popup(title="Pilih Printer Bluetooth",content=box,size_hint=(.92,.8)).open()

    def get_bonded_devices(self):
        if platform!="android": return []
        try:
            from jnius import autoclass
            BluetoothAdapter=autoclass("android.bluetooth.BluetoothAdapter")
            adapter=BluetoothAdapter.getDefaultAdapter()
            if adapter is None: return []
            return [(str(d.getName()),str(d.getAddress())) for d in adapter.getBondedDevices().toArray()]
        except Exception as e:
            print("Bluetooth list:",e); return []

    def print_bluetooth(self,address):
        if not self.last_receipt:
            return
        try:
            from jnius import autoclass
            BluetoothAdapter=autoclass("android.bluetooth.BluetoothAdapter")
            UUID=autoclass("java.util.UUID")
            adapter=BluetoothAdapter.getDefaultAdapter()
            device=adapter.getRemoteDevice(address)
            uuid=UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
            sock=device.createRfcommSocketToServiceRecord(uuid)
            adapter.cancelDiscovery()
            sock.connect()
            out=sock.getOutputStream()
            data=self.build_receipt_bytes()
            out.write(data)
            out.flush()
            sock.close()
            self.notify("Struk berhasil dikirim ke printer.")
        except Exception as e:
            self.notify(f"Gagal mencetak Bluetooth:\n{e}")

    def build_receipt_bytes(self):
        invoice,subtotal,discount,tax,total,method,paid,change,cart=self.last_receipt
        paper=self.db.setting("paper") or "58mm"
        width=32 if paper=="58mm" else 48
        lines=[]
        store=self.db.setting("store_name") or "UniversalPOS Store"
        addr=self.db.setting("store_address") or ""
        footer=self.db.setting("receipt_footer") or "Terima kasih"
        lines += [store.center(width),addr.center(width),"-"*width,
                  invoice,datetime.now().strftime("%d/%m/%Y %H:%M").center(width),"-"*width]
        for x in cart:
            name=str(x["name"])[:width]
            line=f'{name}\n  {x["qty"]:g} x {money(x["price"])} = {money(x["qty"]*x["price"])}'
            lines.append(line)
        lines += ["-"*width,
                  f"Subtotal : {money(subtotal)}",
                  f"Diskon   : {money(discount)}",
                  f"Pajak    : {money(tax)}",
                  f"TOTAL    : {money(total)}",
                  f"Bayar    : {money(paid)}",
                  f"Kembali  : {money(change)}",
                  f"Metode   : {method}",
                  "-"*width,footer.center(width),""]
        text="\n".join(lines)
        init=b"\x1b\x40"
        bold_on=b"\x1b\x45\x01"; bold_off=b"\x1b\x45\x00"
        cut=b"\x1d\x56\x00"
        return init+bold_on+text.encode("utf-8","replace")+bold_off+b"\n\n\n"+cut

if __name__=="__main__":
    UniversalPOS().run()
