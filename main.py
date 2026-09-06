# ============================================================
# KASIRQU ANDROID POS
# Startup Safe Edition
# ============================================================

import os
import csv
import shutil
import sqlite3
import traceback
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from kivy.app import App
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.filechooser import FileChooserListView
from kivy.clock import Clock
from kivy.utils import platform


APP_NAME = "KasirQU"
DB_NAME = "KasirQU.db"


# ============================================================
# UTILITIES
# ============================================================

def money(value):
    try:
        number = Decimal(str(value)).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
        return "Rp {:,}".format(number).replace(",", ".")
    except Exception:
        return "Rp 0"


def safe_float(value, default=0):
    try:
        return float(value)
    except Exception:
        return default


# ============================================================
# KV UI
# ============================================================

KV = r"""

#:import dp kivy.metrics.dp

<NavButton@Button>:
    background_normal: ""
    background_color: (0.08,0.09,0.11,1) if self.state == "normal" else (0.16,0.17,0.20,1)
    color: (0.92,0.94,0.98,1)
    font_size: "13sp"
    size_hint_y: None
    height: dp(48)

<PrimaryButton@Button>:
    background_normal: ""
    background_color: (0.06,0.07,0.08,1)
    color: 1,1,1,1
    bold: True
    size_hint_y: None
    height: dp(48)


<POSScreen>:

    BoxLayout:
        orientation: "vertical"
        padding: dp(10)
        spacing: dp(8)

        canvas.before:
            Color:
                rgba: .96,.97,.98,1
            Rectangle:
                pos: self.pos
                size: self.size

        BoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: dp(8)

            Label:
                text: "KASIRQU"
                font_size: "21sp"
                bold: True
                color: .08,.09,.11,1
                size_hint_x: .35

            TextInput:
                id: search
                hint_text: "Cari produk / SKU..."
                multiline: False
                size_hint_x: .65
                on_text: root.refresh_products(self.text)

        BoxLayout:
            spacing: dp(8)

            ScrollView:
                do_scroll_x: False
                size_hint_x: .60

                GridLayout:
                    id: products
                    cols: 2
                    spacing: dp(7)
                    padding: dp(2)
                    size_hint_y: None
                    height: self.minimum_height

            BoxLayout:
                orientation: "vertical"
                size_hint_x: .40
                spacing: dp(6)

                Label:
                    text: "KERANJANG"
                    bold: True
                    font_size: "15sp"
                    size_hint_y: None
                    height: dp(32)
                    color: .1,.1,.12,1

                ScrollView:
                    do_scroll_x: False

                    GridLayout:
                        id: cart
                        cols: 1
                        spacing: dp(4)
                        size_hint_y: None
                        height: self.minimum_height

                BoxLayout:
                    size_hint_y: None
                    height: dp(35)

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
                    height: dp(35)

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
                    height: dp(35)

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
                    font_size: "18sp"
                    color: .05,.05,.07,1
                    size_hint_y: None
                    height: dp(40)

                Spinner:
                    id: payment
                    text: "Tunai"
                    values:
                        ["Tunai",
                        "QRIS",
                        "Debit",
                        "Kredit",
                        "Transfer",
                        "E-Wallet"]
                    size_hint_y: None
                    height: dp(42)

                TextInput:
                    id: paid
                    hint_text: "Jumlah dibayar"
                    input_filter: "float"
                    multiline: False
                    size_hint_y: None
                    height: dp(42)
                    on_text: root.update_change()

                Label:
                    id: change
                    text: "Kembalian  Rp 0"
                    size_hint_y: None
                    height: dp(32)
                    color: .1,.1,.12,1

                Button:
                    text: "SELESAIKAN"
                    background_normal: ""
                    background_color: (.05,.05,.06,1)
                    color: 1,1,1,1
                    bold: True
                    size_hint_y: None
                    height: dp(46)
                    on_release: root.checkout()

                Button:
                    text: "Kosongkan"
                    size_hint_y: None
                    height: dp(38)
                    on_release: root.clear_cart()


<ProductScreen>:

    BoxLayout:
        orientation: "vertical"
        padding: dp(10)
        spacing: dp(8)

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
                font_size: "21sp"
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
        padding: dp(10)
        spacing: dp(8)

        canvas.before:
            Color:
                rgba: .96,.97,.98,1
            Rectangle:
                pos: self.pos
                size: self.size

        Label:
            text: "TRANSAKSI"
            font_size: "21sp"
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
        padding: dp(10)
        spacing: dp(10)

        canvas.before:
            Color:
                rgba: .96,.97,.98,1
            Rectangle:
                pos: self.pos
                size: self.size

        Label:
            text: "LAPORAN"
            font_size: "21sp"
            bold: True
            color: .08,.09,.11,1
            size_hint_y: None
            height: dp(48)

        Label:
            id: summary
            text: "Memuat..."
            color: .1,.1,.12,1
            font_size: "16sp"
            text_size: self.width, None
            halign: "left"

        Button:
            text: "Export CSV"
            size_hint_y: None
            height: dp(46)
            on_release: root.export_csv()


<SettingsScreen>:

    BoxLayout:
        orientation: "vertical"
        padding: dp(10)
        spacing: dp(8)

        canvas.before:
            Color:
                rgba: .96,.97,.98,1
            Rectangle:
                pos: self.pos
                size: self.size

        Label:
            text: "PENGATURAN"
            font_size: "21sp"
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
            height: dp(42)

        Button:
            text: "Simpan Pengaturan"
            size_hint_y: None
            height: dp(46)
            on_release: root.save()

        Button:
            text: "Backup Database"
            size_hint_y: None
            height: dp(46)
            on_release: root.backup()

        Label:
            text: "Printer thermal Bluetooth harus sudah dipairing melalui Android."
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
        height: dp(56)
        spacing: dp(2)
        padding: dp(2)

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


# ============================================================
# DATABASE
# ============================================================

class DB:

    def __init__(self, path):

        self.path = path

        os.makedirs(
            os.path.dirname(path),
            exist_ok=True
        )

        self.conn = sqlite3.connect(
            path,
            check_same_thread=False,
            timeout=10
        )

        self.conn.row_factory = sqlite3.Row

        self.setup()

    def setup(self):

        cursor = self.conn.cursor()

        cursor.executescript(
            """
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
            """
        )

        defaults = {
            "store_name": "KasirQU",
            "store_address": "Alamat / Kontak",
            "receipt_footer": "Terima kasih telah berbelanja",
            "paper": "58mm",
            "tax_percent": "0"
        }

        for key, value in defaults.items():

            cursor.execute(
                """
                INSERT OR IGNORE INTO settings(key,value)
                VALUES(?,?)
                """,
                (key, value)
            )

        self.conn.commit()

    def setting(self, key):

        row = self.conn.execute(
            "SELECT value FROM settings WHERE key=?",
            (key,)
        ).fetchone()

        return row["value"] if row else ""

    def set_setting(self, key, value):

        self.conn.execute(
            """
            INSERT OR REPLACE INTO settings(key,value)
            VALUES(?,?)
            """,
            (key, str(value))
        )

        self.conn.commit()

    def products(self, search=""):

        if search:

            q = f"%{search.strip()}%"

            return self.conn.execute(
                """
                SELECT *
                FROM products
                WHERE active=1
                AND (
                    name LIKE ?
                    OR sku LIKE ?
                    OR category LIKE ?
                )
                ORDER BY name
                """,
                (q, q, q)
            ).fetchall()

        return self.conn.execute(
            """
            SELECT *
            FROM products
            WHERE active=1
            ORDER BY name
            """
        ).fetchall()

    def add_product(
        self,
        name,
        sku,
        category,
        price,
        cost,
        stock,
        image=""
    ):

        self.conn.execute(
            """
            INSERT INTO products
            (
                name,
                sku,
                category,
                price,
                cost,
                stock,
                image,
                created_at
            )
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                name,
                sku,
                category,
                float(price),
                float(cost),
                float(stock),
                image,
                datetime.now().isoformat(
                    timespec="seconds"
                )
            )
        )

        self.conn.commit()

    def create_sale(
        self,
        cart,
        subtotal,
        discount,
        tax,
        total,
        method,
        paid,
        change
    ):

        invoice = (
            "INV-" +
            datetime.now().strftime(
                "%Y%m%d%H%M%S%f"
            )
        )

        now = datetime.now().isoformat(
            timespec="seconds"
        )

        cursor = self.conn.cursor()

        try:

            self.conn.execute("BEGIN")

            cursor.execute(
                """
                INSERT INTO sales
                (
                    invoice,
                    subtotal,
                    discount,
                    tax,
                    total,
                    payment_method,
                    paid,
                    change_amount,
                    created_at
                )
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    invoice,
                    subtotal,
                    discount,
                    tax,
                    total,
                    method,
                    paid,
                    change,
                    now
                )
            )

            sale_id = cursor.lastrowid

            for item in cart:

                product = cursor.execute(
                    """
                    SELECT stock
                    FROM products
                    WHERE id=? AND active=1
                    """,
                    (item["id"],)
                ).fetchone()

                if not product:
                    raise ValueError(
                        "Produk tidak ditemukan."
                    )

                current_stock = float(
                    product["stock"]
                )

                qty = float(item["qty"])

                if current_stock < qty:
                    raise ValueError(
                        "Stok produk tidak mencukupi."
                    )

                cursor.execute(
                    """
                    INSERT INTO sale_items
                    (
                        sale_id,
                        product_id,
                        name,
                        qty,
                        price,
                        line_total
                    )
                    VALUES(?,?,?,?,?,?)
                    """,
                    (
                        sale_id,
                        item["id"],
                        item["name"],
                        qty,
                        item["price"],
                        qty * item["price"]
                    )
                )

                cursor.execute(
                    """
                    UPDATE products
                    SET stock=stock-?
                    WHERE id=?
                    """,
                    (qty, item["id"])
                )

            self.conn.commit()

            return invoice

        except Exception:

            self.conn.rollback()

            raise

    def sales(self, limit=100):

        return self.conn.execute(
            """
            SELECT *
            FROM sales
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()


# ============================================================
# POS SCREEN
# ============================================================

class POSScreen(Screen):

    def on_enter(self):

        self.app = App.get_running_app()

        if not hasattr(self, "cart_data"):
            self.cart_data = []

        self.refresh_products()

    def refresh_products(self, text=""):

        try:

            box = self.ids.products

            box.clear_widgets()

            rows = self.app.db.products(text)

            for product in rows:

                card = BoxLayout(
                    orientation="vertical",
                    size_hint_y=None,
                    height=dp(125),
                    padding=dp(4)
                )

                image_path = product["image"]

                if (
                    image_path
                    and os.path.isfile(image_path)
                ):

                    card.add_widget(
                        Image(
                            source=image_path,
                            size_hint_y=.58
                        )
                    )

                else:

                    card.add_widget(
                        Label(
                            text="📦",
                            font_size="28sp",
                            size_hint_y=.58,
                            color=(.2,.2,.22,1)
                        )
                    )

                label = Label(
                    text=(
                        f'{product["name"]}\n'
                        f'{money(product["price"])} | '
                        f'stok {product["stock"]:g}'
                    ),
                    color=(.08,.09,.11,1),
                    halign="center"
                )

                label.bind(
                    size=lambda instance, value:
                    setattr(
                        instance,
                        "text_size",
                        value
                    )
                )

                card.add_widget(label)

                button = Button(
                    text="Tambah",
                    size_hint_y=None,
                    height=dp(30),
                    background_normal="",
                    background_color=(.08,.09,.11,.95)
                )

                button.bind(
                    on_release=lambda *_,
                    p=product:
                    self.add_product(p)
                )

                card.add_widget(button)

                box.add_widget(card)

        except Exception as error:

            self.app.log_error(
                "refresh_products",
                error
            )

    def add_product(self, product):

        try:

            stock = float(product["stock"])

            if stock <= 0:

                self.app.notify(
                    "Stok produk habis."
                )

                return

            for item in self.cart_data:

                if item["id"] == product["id"]:

                    if item["qty"] + 1 > stock:

                        self.app.notify(
                            "Jumlah melebihi stok."
                        )

                        return

                    item["qty"] += 1

                    self.render_cart()

                    return

            self.cart_data.append(
                {
                    "id": product["id"],
                    "name": product["name"],
                    "price": float(
                        product["price"]
                    ),
                    "qty": 1,
                    "stock": stock
                }
            )

            self.render_cart()

        except Exception as error:

            self.app.log_error(
                "add_product",
                error
            )

    def render_cart(self):

        box = self.ids.cart

        box.clear_widgets()

        for index, item in enumerate(
            self.cart_data
        ):

            row = BoxLayout(
                size_hint_y=None,
                height=dp(52),
                spacing=dp(3)
            )

            label = Label(
                text=(
                    f'{item["name"]}\n'
                    f'{item["qty"]:g} × '
                    f'{money(item["price"])}'
                ),
                color=(.08,.09,.11,1),
                halign="left"
            )

            label.bind(
                size=lambda instance, value:
                setattr(
                    instance,
                    "text_size",
                    value
                )
            )

            row.add_widget(label)

            minus = Button(
                text="-",
                size_hint_x=.20
            )

            plus = Button(
                text="+",
                size_hint_x=.20
            )

            delete = Button(
                text="×",
                size_hint_x=.20
            )

            minus.bind(
                on_release=lambda *_,
                i=index:
                self.change_qty(i, -1)
            )

            plus.bind(
                on_release=lambda *_,
                i=index:
                self.change_qty(i, 1)
            )

            delete.bind(
                on_release=lambda *_,
                i=index:
                self.remove_item(i)
            )

            row.add_widget(minus)
            row.add_widget(plus)
            row.add_widget(delete)

            box.add_widget(row)

        self.update_totals()

    def change_qty(self, index, delta):

        if not (
            0 <= index < len(self.cart_data)
        ):
            return

        item = self.cart_data[index]

        item["qty"] += delta

        if item["qty"] <= 0:

            self.cart_data.pop(index)

        elif item["qty"] > item["stock"]:

            item["qty"] = item["stock"]

        self.render_cart()

    def remove_item(self, index):

        if 0 <= index < len(self.cart_data):

            self.cart_data.pop(index)

            self.render_cart()

    def calculate_total(self):

        subtotal = sum(
            item["qty"] * item["price"]
            for item in self.cart_data
        )

        discount = max(
            0,
            safe_float(
                self.ids.discount.text
            )
        )

        tax_percent = max(
            0,
            safe_float(
                self.ids.tax.text
            )
        )

        taxable = max(
            0,
            subtotal - discount
        )

        tax = taxable * tax_percent / 100

        total = max(
            0,
            taxable + tax
        )

        return (
            subtotal,
            discount,
            tax,
            total
        )

    def update_totals(self, *_):

        try:

            subtotal, discount, tax, total = (
                self.calculate_total()
            )

            self.ids.subtotal.text = money(
                subtotal
            )

            self.ids.total.text = (
                f"TOTAL  {money(total)}"
            )

            self.update_change()

        except Exception:

            pass

    def update_change(self, *_):

        try:

            total = self.calculate_total()[3]

            paid = max(
                0,
                safe_float(
                    self.ids.paid.text
                )
            )

            method = self.ids.payment.text

            change = (
                max(0, paid - total)
                if method == "Tunai"
                else 0
            )

            self.ids.change.text = (
                f"Kembalian  {money(change)}"
            )

        except Exception:

            self.ids.change.text = (
                "Kembalian  Rp 0"
            )

    def clear_cart(self):

        self.cart_data = []

        self.ids.discount.text = "0"

        self.ids.paid.text = ""

        self.render_cart()

    def checkout(self):

        if not self.cart_data:

            self.app.notify(
                "Keranjang masih kosong."
            )

            return

        try:

            (
                subtotal,
                discount,
                tax,
                total
            ) = self.calculate_total()

            method = self.ids.payment.text

            paid = safe_float(
                self.ids.paid.text
            )

            if method == "Tunai":

                if paid < total:

                    self.app.notify(
                        f"Uang kurang "
                        f"{money(total - paid)}"
                    )

                    return

                change = paid - total

            else:

                paid = total
                change = 0

            invoice = self.app.db.create_sale(
                self.cart_data,
                subtotal,
                discount,
                tax,
                total,
                method,
                paid,
                change
            )

            self.app.last_receipt = (
                invoice,
                subtotal,
                discount,
                tax,
                total,
                method,
                paid,
                change,
                list(self.cart_data)
            )

            self.app.print_or_offer(
                invoice
            )

            self.clear_cart()

            self.app.root.ids.sm.current = (
                "transactions"
            )

        except Exception as error:

            self.app.log_error(
                "checkout",
                error
            )

            self.app.notify(
                "Transaksi gagal:\n"
                + str(error)
            )


# ============================================================
# PRODUCT SCREEN
# ============================================================

class ProductScreen(Screen):

    def on_enter(self):

        self.app = App.get_running_app()

        self.refresh()

    def refresh(self):

        try:

            box = self.ids.list

            box.clear_widgets()

            for product in self.app.db.products():

                row = BoxLayout(
                    size_hint_y=None,
                    height=dp(82),
                    spacing=dp(7)
                )

                image_path = product["image"]

                if (
                    image_path
                    and os.path.isfile(image_path)
                ):

                    row.add_widget(
                        Image(
                            source=image_path,
                            size_hint_x=.18
                        )
                    )

                info = Label(
                    text=(
                        f'{product["name"]}  •  '
                        f'{product["sku"] or "-"}\n'
                        f'{money(product["price"])}  • '
                        f'stok {product["stock"]:g}\n'
                        f'{product["category"] or "Tanpa kategori"}'
                    ),
                    color=(.08,.09,.11,1),
                    halign="left"
                )

                info.bind(
                    size=lambda instance, value:
                    setattr(
                        instance,
                        "text_size",
                        value
                    )
                )

                row.add_widget(info)

                box.add_widget(row)

        except Exception as error:

            self.app.log_error(
                "product_refresh",
                error
            )

    def open_editor(self):

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(7),
            padding=dp(10)
        )

        fields = {}

        definitions = [
            ("name", "Nama produk *"),
            ("sku", "SKU / Barcode"),
            ("category", "Kategori"),
            ("price", "Harga jual"),
            ("cost", "Harga modal"),
            ("stock", "Stok")
        ]

        for key, hint in definitions:

            field = TextInput(
                hint_text=hint,
                multiline=False,
                size_hint_y=None,
                height=dp(42)
            )

            fields[key] = field

            content.add_widget(field)

        choose = Button(
            text="Pilih Foto Produk",
            size_hint_y=None,
            height=dp(42)
        )

        content.add_widget(choose)

        selected = {
            "path": ""
        }

        save = Button(
            text="Simpan",
            size_hint_y=None,
            height=dp(46)
        )

        content.add_widget(save)

        popup = Popup(
            title="Tambah Produk",
            content=content,
            size_hint=(.92,.85)
        )

        choose.bind(
            on_release=lambda *_:
            self.pick_image(selected)
        )

        def save_product(*_):

            name = fields["name"].text.strip()

            if not name:

                self.app.notify(
                    "Nama produk wajib diisi."
                )

                return

            price = safe_float(
                fields["price"].text
            )

            cost = safe_float(
                fields["cost"].text
            )

            stock = safe_float(
                fields["stock"].text
            )

            image_path = ""

            source = selected["path"]

            if (
                source
                and os.path.isfile(source)
            ):

                try:

                    extension = (
                        os.path.splitext(source)[1]
                        .lower()
                    )

                    if extension not in (
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".webp"
                    ):

                        self.app.notify(
                            "Format gambar tidak didukung."
                        )

                        return

                    filename = (
                        datetime.now().strftime(
                            "%Y%m%d%H%M%S%f"
                        )
                        + extension
                    )

                    destination = os.path.join(
                        self.app.images_dir,
                        filename
                    )

                    shutil.copy2(
                        source,
                        destination
                    )

                    image_path = destination

                except Exception as error:

                    self.app.log_error(
                        "copy_product_image",
                        error
                    )

                    self.app.notify(
                        "Foto tidak dapat disimpan."
                    )

                    return

            try:

                self.app.db.add_product(
                    name,
                    fields["sku"].text.strip(),
                    fields["category"].text.strip(),
                    price,
                    cost,
                    stock,
                    image_path
                )

                popup.dismiss()

                self.refresh()

            except Exception as error:

                self.app.log_error(
                    "save_product",
                    error
                )

                self.app.notify(
                    "Produk gagal disimpan."
                )

        save.bind(
            on_release=save_product
        )

        popup.open()

    def pick_image(self, selected):

        try:

            start_path = (
                "/storage/emulated/0"
                if platform == "android"
                else os.path.expanduser("~")
            )

            if not os.path.exists(start_path):

                start_path = (
                    self.app.user_data_dir
                )

            chooser = FileChooserListView(
                path=start_path,
                filters=[
                    "*.png",
                    "*.jpg",
                    "*.jpeg",
                    "*.webp"
                ]
            )

            container = BoxLayout(
                orientation="vertical"
            )

            container.add_widget(
                chooser
            )

            buttons = BoxLayout(
                size_hint_y=None,
                height=dp(48)
            )

            select_button = Button(
                text="Pilih"
            )

            cancel_button = Button(
                text="Batal"
            )

            buttons.add_widget(
                select_button
            )

            buttons.add_widget(
                cancel_button
            )

            container.add_widget(
                buttons
            )

            popup = Popup(
                title="Pilih Foto Produk",
                content=container,
                size_hint=(.95,.90)
            )

            def select_file(*_):

                if not chooser.selection:

                    return

                selected["path"] = (
                    chooser.selection[0]
                )

                popup.dismiss()

            select_button.bind(
                on_release=select_file
            )

            cancel_button.bind(
                on_release=popup.dismiss
            )

            popup.open()

        except Exception as error:

            self.app.log_error(
                "image_picker",
                error
            )

            self.app.notify(
                "Pemilih foto tidak dapat dibuka."
            )


# ============================================================
# TRANSACTION SCREEN
# ============================================================

class TransactionScreen(Screen):

    def on_enter(self):

        self.app = App.get_running_app()

        self.refresh()

    def refresh(self):

        box = self.ids.list

        box.clear_widgets()

        try:

            rows = self.app.db.sales()

            for sale in rows:

                label = Label(
                    text=(
                        f'{sale["invoice"]} • '
                        f'{sale["created_at"]}\n'
                        f'{money(sale["total"])} • '
                        f'{sale["payment_method"]}'
                    ),
                    color=(.08,.09,.11,1),
                    halign="left",
                    size_hint_y=None,
                    height=dp(60)
                )

                box.add_widget(label)

        except Exception as error:

            self.app.log_error(
                "transaction_refresh",
                error
            )


# ============================================================
# REPORT SCREEN
# ============================================================

class ReportScreen(Screen):

    def on_enter(self):

        self.app = App.get_running_app()

        self.refresh()

    def refresh(self):

        try:

            rows = self.app.db.conn.execute(
                """
                SELECT
                    COUNT(*) n,
                    COALESCE(SUM(subtotal),0) subtotal,
                    COALESCE(SUM(discount),0) discount,
                    COALESCE(SUM(tax),0) tax,
                    COALESCE(SUM(total),0) total
                FROM sales
                WHERE date(created_at)=date('now')
                """
            ).fetchone()

            self.ids.summary.text = (
                "HARI INI\n\n"
                f"Transaksi : {rows['n']}\n"
                f"Subtotal  : {money(rows['subtotal'])}\n"
                f"Diskon    : {money(rows['discount'])}\n"
                f"Pajak     : {money(rows['tax'])}\n"
                f"Penjualan : {money(rows['total'])}"
            )

        except Exception as error:

            self.app.log_error(
                "report_refresh",
                error
            )

    def export_csv(self):

        try:

            path = os.path.join(
                self.app.user_data_dir,
                "sales_export.csv"
            )

            with open(
                path,
                "w",
                newline="",
                encoding="utf-8-sig"
            ) as file:

                writer = csv.writer(file)

                writer.writerow(
                    [
                        "Invoice",
                        "Tanggal",
                        "Subtotal",
                        "Diskon",
                        "Pajak",
                        "Total",
                        "Pembayaran",
                        "Dibayar",
                        "Kembalian"
                    ]
                )

                for sale in self.app.db.sales(
                    10000
                ):

                    writer.writerow(
                        [
                            sale["invoice"],
                            sale["created_at"],
                            sale["subtotal"],
                            sale["discount"],
                            sale["tax"],
                            sale["total"],
                            sale["payment_method"],
                            sale["paid"],
                            sale["change_amount"]
                        ]
                    )

            self.app.notify(
                f"CSV tersimpan:\n{path}"
            )

        except Exception as error:

            self.app.log_error(
                "export_csv",
                error
            )


# ============================================================
# SETTINGS
# ============================================================

class SettingsScreen(Screen):

    def on_enter(self):

        self.app = App.get_running_app()

        self.ids.store.text = (
            self.app.db.setting(
                "store_name"
            )
        )

        self.ids.address.text = (
            self.app.db.setting(
                "store_address"
            )
        )

        self.ids.footer.text = (
            self.app.db.setting(
                "receipt_footer"
            )
        )

        self.ids.paper.text = (
            self.app.db.setting(
                "paper"
            )
            or "58mm"
        )

    def save(self):

        try:

            self.app.db.set_setting(
                "store_name",
                self.ids.store.text
            )

            self.app.db.set_setting(
                "store_address",
                self.ids.address.text
            )

            self.app.db.set_setting(
                "receipt_footer",
                self.ids.footer.text
            )

            self.app.db.set_setting(
                "paper",
                self.ids.paper.text
            )

            self.app.notify(
                "Pengaturan disimpan."
            )

        except Exception as error:

            self.app.log_error(
                "settings_save",
                error
            )

    def backup(self):

        try:

            target = os.path.join(
                self.app.user_data_dir,
                "KasirQU_backup.db"
            )

            self.app.db.conn.commit()

            shutil.copy2(
                self.app.db.path,
                target
            )

            self.app.notify(
                f"Backup dibuat:\n{target}"
            )

        except Exception as error:

            self.app.log_error(
                "database_backup",
                error
            )


# ============================================================
# MAIN APPLICATION
# ============================================================

class UniversalPOS(App):

    tax_percent = StringProperty("0")

    last_receipt = None

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.startup_error = None

    def log_error(self, location, error):

        try:

            error_path = os.path.join(
                self.user_data_dir,
                "KasirQU_error.log"
            )

            os.makedirs(
                self.user_data_dir,
                exist_ok=True
            )

            with open(
                error_path,
                "a",
                encoding="utf-8"
            ) as file:

                file.write(
                    "\n\n==============================\n"
                )

                file.write(
                    datetime.now().isoformat()
                )

                file.write(
                    f"\nLOCATION: {location}\n"
                )

                file.write(
                    f"ERROR: {repr(error)}\n"
                )

                file.write(
                    traceback.format_exc()
                )

        except Exception:

            pass

        print(
            f"KASIRQU ERROR [{location}]:",
            repr(error)
        )

    def build(self):

        try:

            self.title = APP_NAME

            data_dir = self.user_data_dir

            if not data_dir:

                data_dir = os.path.join(
                    os.path.expanduser("~"),
                    ".kasirqu"
                )

            data_dir = os.path.abspath(
                data_dir
            )

            os.makedirs(
                data_dir,
                exist_ok=True
            )

            self.images_dir = os.path.join(
                data_dir,
                "products"
            )

            os.makedirs(
                self.images_dir,
                exist_ok=True
            )

            database_path = os.path.join(
                data_dir,
                DB_NAME
            )

            self.db = DB(
                database_path
            )

            self.tax_percent = (
                self.db.setting(
                    "tax_percent"
                )
                or "0"
            )

            root = Builder.load_string(
                KV
            )

            if root is None:

                raise RuntimeError(
                    "Kivy root gagal dibuat."
                )

            return root

        except Exception as error:

            self.startup_error = error

            self.log_error(
                "APPLICATION_STARTUP",
                error
            )

            return self.build_safe_screen(
                error
            )

    def build_safe_screen(self, error):

        root = BoxLayout(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(15)
        )

        root.add_widget(
            Label(
                text="KasirQU",
                font_size="28sp",
                bold=True
            )
        )

        root.add_widget(
            Label(
                text=(
                    "Aplikasi mengalami "
                    "masalah saat startup.\n\n"
                    "Silakan restart aplikasi."
                ),
                halign="center"
            )
        )

        return root

    def on_start(self):

        Clock.schedule_once(
            self.finish_startup,
            0.5
        )

    def finish_startup(self, *_):

        try:

            if self.startup_error is None:

                pos = (
                    self.root
                    .ids
                    .sm
                    .get_screen("pos")
                )

                pos.refresh_products()

        except Exception as error:

            self.log_error(
                "FIRST_UI",
                error
            )

        self.hide_android_loading_screen()

    def hide_android_loading_screen(self):

        if platform != "android":

            return

        try:

            from android import loadingscreen

            loadingscreen.hide_loading_screen()

        except Exception as error:

            self.log_error(
                "LOADING_SCREEN",
                error
            )

    def notify(self, message):

        try:

            Popup(
                title=APP_NAME,
                content=Label(
                    text=str(message)
                ),
                size_hint=(.85,.35)
            ).open()

        except Exception as error:

            self.log_error(
                "NOTIFY",
                error
            )

    # ========================================================
    # RECEIPT
    # ========================================================

    def print_or_offer(self, invoice):

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=dp(10)
        )

        content.add_widget(
            Label(
                text=(
                    f"Transaksi {invoice} berhasil.\n"
                    "Cetak struk sekarang?"
                )
            )
        )

        buttons = BoxLayout(
            size_hint_y=None,
            height=dp(48),
            spacing=dp(7)
        )

        bluetooth = Button(
            text="Bluetooth"
        )

        no_print = Button(
            text="Tidak"
        )

        buttons.add_widget(
            bluetooth
        )

        buttons.add_widget(
            no_print
        )

        content.add_widget(
            buttons
        )

        popup = Popup(
            title="Struk",
            content=content,
            size_hint=(.88,.4)
        )

        bluetooth.bind(
            on_release=lambda *_: (
                popup.dismiss(),
                self.bluetooth_printer_dialog()
            )
        )

        no_print.bind(
            on_release=popup.dismiss
        )

        popup.open()

    def bluetooth_printer_dialog(self):

        devices = self.get_bonded_devices()

        if not devices:

            self.notify(
                "Tidak ada printer Bluetooth "
                "yang sudah dipairing."
            )

            return

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(6),
            padding=dp(8)
        )

        popup = Popup(
            title="Pilih Printer Bluetooth",
            content=content,
            size_hint=(.92,.8)
        )

        for name, address in devices:

            button = Button(
                text=f"{name}\n{address}",
                size_hint_y=None,
                height=dp(58)
            )

            button.bind(
                on_release=lambda *_,
                addr=address: (
                    popup.dismiss(),
                    self.print_bluetooth(addr)
                )
            )

            content.add_widget(
                button
            )

        popup.open()

    def get_bonded_devices(self):

        if platform != "android":

            return []

        try:

            from jnius import autoclass

            BluetoothAdapter = autoclass(
                "android.bluetooth.BluetoothAdapter"
            )

            adapter = (
                BluetoothAdapter
                .getDefaultAdapter()
            )

            if adapter is None:

                return []

            bonded = (
                adapter
                .getBondedDevices()
                .toArray()
            )

            result = []

            for device in bonded:

                try:

                    name = str(
                        device.getName()
                    )

                except Exception:

                    name = "Bluetooth Device"

                try:

                    address = str(
                        device.getAddress()
                    )

                except Exception:

                    continue

                result.append(
                    (name, address)
                )

            return result

        except Exception as error:

            self.log_error(
                "BLUETOOTH_DEVICES",
                error
            )

            return []

    def print_bluetooth(self, address):

        if not self.last_receipt:

            return

        socket = None

        try:

            from jnius import autoclass

            BluetoothAdapter = autoclass(
                "android.bluetooth.BluetoothAdapter"
            )

            UUID = autoclass(
                "java.util.UUID"
            )

            adapter = (
                BluetoothAdapter
                .getDefaultAdapter()
            )

            if adapter is None:

                raise RuntimeError(
                    "Bluetooth tidak tersedia."
                )

            device = (
                adapter
                .getRemoteDevice(address)
            )

            uuid = UUID.fromString(
                "00001101-0000-1000-8000-00805F9B34FB"
            )

            socket = (
                device
                .createRfcommSocketToServiceRecord(
                    uuid
                )
            )

            try:

                adapter.cancelDiscovery()

            except Exception:

                pass

            socket.connect()

            output = (
                socket
                .getOutputStream()
            )

            output.write(
                self.build_receipt_bytes()
            )

            output.flush()

            self.notify(
                "Struk berhasil dikirim."
            )

        except Exception as error:

            self.log_error(
                "BLUETOOTH_PRINT",
                error
            )

            self.notify(
                "Gagal mencetak:\n"
                + str(error)
            )

        finally:

            if socket is not None:

                try:

                    socket.close()

                except Exception:

                    pass

    def build_receipt_bytes(self):

        (
            invoice,
            subtotal,
            discount,
            tax,
            total,
            method,
            paid,
            change,
            cart
        ) = self.last_receipt

        paper = (
            self.db.setting("paper")
            or "58mm"
        )

        width = (
            32
            if paper == "58mm"
            else 48
        )

        store = (
            self.db.setting("store_name")
            or APP_NAME
        )

        address = (
            self.db.setting("store_address")
            or ""
        )

        footer = (
            self.db.setting("receipt_footer")
            or "Terima kasih"
        )

        lines = [
            store.center(width),
            address.center(width),
            "-" * width,
            invoice,
            datetime.now().strftime(
                "%d/%m/%Y %H:%M"
            ).center(width),
            "-" * width
        ]

        for item in cart:

            name = str(
                item["name"]
            )[:width]

            lines.append(
                name
            )

            lines.append(
                "  "
                f'{item["qty"]:g} x '
                f'{money(item["price"])}'
                " = "
                f'{money(item["qty"] * item["price"])}'
            )

        lines.extend(
            [
                "-" * width,
                f"Subtotal : {money(subtotal)}",
                f"Diskon   : {money(discount)}",
                f"Pajak    : {money(tax)}",
                f"TOTAL    : {money(total)}",
                f"Bayar    : {money(paid)}",
                f"Kembali  : {money(change)}",
                f"Metode   : {method}",
                "-" * width,
                footer.center(width),
                ""
            ]
        )

        text = "\n".join(
            lines
        )

        init = b"\x1b\x40"

        bold_on = b"\x1b\x45\x01"

        bold_off = b"\x1b\x45\x00"

        cut = b"\x1d\x56\x00"

        return (
            init
            + bold_on
            + text.encode(
                "utf-8",
                "replace"
            )
            + bold_off
            + b"\n\n\n"
            + cut
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    UniversalPOS().run()
