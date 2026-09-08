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
from kivy.core.window import Window
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button, ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.filechooser import FileChooserListView
from kivy.graphics import Color, RoundedRectangle
from kivy.clock import Clock
from kivy.utils import platform


# ============================================================
# KASIRQU
# FINAL UI + IMAGE FIX
# ============================================================

APP_NAME = "KasirQU"
DB_NAME = "KasirQU.db"

PRIMARY = (0.12, 0.32, 0.78, 1)
PRIMARY_DARK = (0.08, 0.24, 0.62, 1)

BG = (0.95, 0.97, 0.99, 1)
WHITE = (1, 1, 1, 1)
TEXT = (0.08, 0.11, 0.16, 1)
MUTED = (0.40, 0.44, 0.51, 1)
BORDER = (0.88, 0.90, 0.94, 1)
SUCCESS = (0.08, 0.55, 0.30, 1)
DANGER = (0.78, 0.18, 0.18, 1)


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
        if value is None:
            return default

        value = str(value).strip()

        if not value:
            return default

        return float(value)

    except Exception:
        return default


def safe_text(value):
    try:
        return str(value or "")
    except Exception:
        return ""


# ============================================================
# CARD
# ============================================================

class Card(BoxLayout):

    radius = NumericProperty(dp(14))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(*WHITE)

            self._rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[self.radius]
            )

        self.bind(
            pos=self._update_rect,
            size=self._update_rect
        )

    def _update_rect(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


# ============================================================
# MODERN BUTTON
# ============================================================

class ModernButton(Button):

    def __init__(self, primary=False, **kwargs):

        self.primary = primary

        super().__init__(**kwargs)

        self.background_normal = ""
        self.background_down = ""

        self.background_color = (
            PRIMARY if primary else WHITE
        )

        self.color = (
            WHITE if primary else TEXT
        )

        self.bold = True

        self.size_hint_y = None

        if "height" not in kwargs:
            self.height = dp(44)


# ============================================================
# ICON NAVIGATION
# ============================================================

class IconNavButton(ButtonBehavior, BoxLayout):

    def __init__(self, name="", icon="", **kwargs):
        super().__init__(orientation="vertical", spacing=dp(2), **kwargs)
        self.nav_name = name
        self.icon_path = icon
        self.size_hint_y = None
        self.height = dp(72)
        self.padding = [dp(3), dp(4), dp(3), dp(3)]

        self.icon = Image(
            source=icon,
            size_hint_y=None,
            height=dp(42),
            allow_stretch=True,
            keep_ratio=True
        )
        self.label = Label(
            text=name,
            font_size="10sp",
            bold=True,
            color=MUTED,
            size_hint_y=None,
            height=dp(20),
            halign="center",
            valign="middle"
        )
        self.label.bind(size=lambda w, v: setattr(w, "text_size", v))
        self.add_widget(self.icon)
        self.add_widget(self.label)

        with self.canvas.before:
            Color(1, 1, 1, 1)
            self._nav_bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, *_):
        self._nav_bg.pos = self.pos
        self._nav_bg.size = self.size

    def on_release(self):
        App.get_running_app().navigate(self.nav_name)


# ============================================================
# SWIPE MANAGER
# ============================================================

class SwipeManager(ScreenManager):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._touch_start = None

    def on_touch_down(self, touch):

        self._touch_start = touch.pos

        return super().on_touch_down(touch)

    def on_touch_up(self, touch):

        start = self._touch_start

        result = super().on_touch_up(touch)

        if start is not None:

            dx = touch.x - start[0]
            dy = touch.y - start[1]

            if (
                abs(dx) > dp(70)
                and
                abs(dx) > abs(dy) * 1.3
            ):

                self.swipe(
                    -1 if dx > 0 else 1
                )

        self._touch_start = None

        return result

    def swipe(self, delta):

        names = list(self.screen_names)

        if self.current not in names:
            return

        index = names.index(self.current)

        target = index + delta

        if target < 0 or target >= len(names):
            return

        self.transition = SlideTransition(
            direction=(
                "right"
                if delta < 0
                else "left"
            ),
            duration=.20
        )

        self.current = names[target]


# ============================================================
# KV
# ============================================================

KV = r'''
#:import dp kivy.metrics.dp


<PrimaryButton@Button>:

    background_normal: ""

    background_down: ""

    background_color:
        (.08,.24,.62,1) if self.state == "down" else (.12,.32,.78,1)

    color: 1,1,1,1

    bold: True

    font_size: "14sp"

    size_hint_y: None

    height: dp(46)


<SoftButton@Button>:

    background_normal: ""

    background_down: ""

    background_color:
        (.88,.91,.96,1) if self.state == "down" else (1,1,1,1)

    color: (.08,.11,.16,1)

    bold: True

    font_size: "13sp"

    size_hint_y: None

    height: dp(44)


<ScreenTitle@Label>:

    color: (.07,.09,.13,1)

    font_size: "22sp"

    bold: True

    halign: "left"

    valign: "middle"

    text_size: self.size


<NavButton@Button>:

    background_normal: ""

    background_down: ""

    background_color:
        (.12,.32,.78,1) if self.state == "down" else (1,1,1,1)

    color:
        (1,1,1,1) if self.state == "down" else (.25,.29,.36,1)

    font_size: "11sp"

    bold: True

    halign: "center"

    valign: "middle"

    text_size: self.size


<POSScreen>:

    BoxLayout:

        orientation: "vertical"

        padding: dp(12)

        spacing: dp(10)


        canvas.before:

            Color:

                rgba: (.95,.97,.99,1)

            Rectangle:

                pos: self.pos

                size: self.size


        BoxLayout:

            size_hint_y: None

            height: dp(50)

            spacing: dp(8)


            Label:

                text: "KasirQU"

                color: (.07,.09,.13,1)

                font_size: "23sp"

                bold: True

                size_hint_x: .34

                halign: "left"

                valign: "middle"

                text_size: self.size


            TextInput:

                id: search

                hint_text: "Cari produk atau SKU..."

                multiline: False

                padding: [dp(12), dp(11)]

                background_normal: ""

                background_color: (1,1,1,1)

                foreground_color: (.08,.11,.16,1)

                cursor_color: (.12,.32,.78,1)

                on_text:

                    root.refresh_products(self.text)


        Label:

            text: "Pilih Produk"

            size_hint_y: None

            height: dp(27)

            color: (.40,.44,.51,1)

            font_size: "14sp"

            bold: True

            halign: "left"

            text_size: self.size


        ScrollView:

            do_scroll_x: False

            bar_width: dp(3)


            GridLayout:

                id: products

                cols: 2

                spacing: dp(10)

                padding: dp(2)

                size_hint_y: None

                height: self.minimum_height


        Card:

            orientation: "horizontal"

            size_hint_y: None

            height: dp(70)

            padding: dp(9)

            spacing: dp(8)


            Label:

                id: cart_count

                text: "0 item"

                color: (.08,.11,.16,1)

                bold: True

                size_hint_x: .25

                halign: "left"

                valign: "middle"

                text_size: self.size


            Label:

                id: cart_total

                text: "Rp 0"

                color: (.12,.32,.78,1)

                font_size: "18sp"

                bold: True

                size_hint_x: .42

                halign: "right"

                valign: "middle"

                text_size: self.size


            SoftButton:

                text: "KERANJANG"

                size_hint_x: .33

                on_release:

                    root.open_cart_popup()


<ProductScreen>:

    BoxLayout:

        orientation: "vertical"

        padding: dp(12)

        spacing: dp(10)


        canvas.before:

            Color:

                rgba: (.95,.97,.99,1)

            Rectangle:

                pos: self.pos

                size: self.size


        BoxLayout:

            size_hint_y: None

            height: dp(52)

            spacing: dp(10)


            ScreenTitle:

                text: "Produk"

                size_hint_x: .70


            PrimaryButton:

                text: "+ Produk"

                size_hint_x: .30

                on_release:

                    root.open_editor()


        TextInput:

            id: search

            hint_text: "Cari nama, SKU, kategori..."

            multiline: False

            size_hint_y: None

            height: dp(44)

            padding: [dp(12), dp(10)]

            background_normal: ""

            background_color: (1,1,1,1)

            foreground_color: (.08,.11,.16,1)

            on_text:

                root.refresh(self.text)


        ScrollView:

            do_scroll_x: False

            bar_width: dp(3)


            GridLayout:

                id: list

                cols: 1

                spacing: dp(8)

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

                rgba: (.95,.97,.99,1)

            Rectangle:

                pos: self.pos

                size: self.size


        ScreenTitle:

            text: "Riwayat Transaksi"

            size_hint_y: None

            height: dp(52)


        ScrollView:

            do_scroll_x: False

            bar_width: dp(3)


            GridLayout:

                id: list

                cols: 1

                spacing: dp(8)

                padding: dp(2)

                size_hint_y: None

                height: self.minimum_height


<ReportScreen>:

    BoxLayout:

        orientation: "vertical"

        padding: dp(12)

        spacing: dp(10)


        canvas.before:

            Color:

                rgba: (.95,.97,.99,1)

            Rectangle:

                pos: self.pos

                size: self.size


        ScreenTitle:

            text: "Laporan"

            size_hint_y: None

            height: dp(52)


        Card:

            orientation: "vertical"

            padding: dp(18)

            size_hint_y: None

            height: dp(205)


            Label:

                id: summary

                text: "Memuat..."

                color: (.08,.11,.16,1)

                font_size: "16sp"

                bold: True

                halign: "left"

                valign: "top"

                text_size: self.size


        PrimaryButton:

            text: "EXPORT CSV"

            on_release:

                root.export_csv()


        Widget:


<SettingsScreen>:

    BoxLayout:

        orientation: "vertical"

        padding: dp(12)

        spacing: dp(10)


        canvas.before:

            Color:

                rgba: (.95,.97,.99,1)

            Rectangle:

                pos: self.pos

                size: self.size


        ScreenTitle:

            text: "Pengaturan"

            size_hint_y: None

            height: dp(52)


        TextInput:

            id: store

            hint_text: "Nama usaha"

            multiline: False

            size_hint_y: None

            height: dp(44)

            padding: [dp(12),dp(10)]

            background_normal: ""

            background_color: (1,1,1,1)


        TextInput:

            id: address

            hint_text: "Alamat / kontak"

            multiline: False

            size_hint_y: None

            height: dp(44)

            padding: [dp(12),dp(10)]

            background_normal: ""

            background_color: (1,1,1,1)


        TextInput:

            id: footer

            hint_text: "Footer struk"

            multiline: False

            size_hint_y: None

            height: dp(44)

            padding: [dp(12),dp(10)]

            background_normal: ""

            background_color: (1,1,1,1)


        Spinner:

            id: paper

            text: "58mm"

            values: ["58mm","80mm"]

            size_hint_y: None

            height: dp(44)

        TextInput:

            id: tax

            hint_text: "Pajak (%) - contoh 11"

            input_filter: "float"

            multiline: False

            size_hint_y: None

            height: dp(44)

            padding: [dp(12), dp(10)]

            background_normal: ""

            background_color: (1,1,1,1)


        PrimaryButton:

            text: "SIMPAN PENGATURAN"

            on_release:

                root.save()


        SoftButton:

            text: "BACKUP DATABASE"

            on_release:

                root.backup()

        SoftButton:

            text: "REFRESH DATA"

            on_release:

                root.on_enter()


        Label:

            text: "Printer thermal Bluetooth harus sudah dipairing melalui Android."

            color: (.40,.44,.51,1)

            font_size: "13sp"

            halign: "left"

            valign: "top"

            text_size: self.width, None


        Widget:


BoxLayout:

    orientation: "vertical"


    SwipeManager:

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

        height: dp(72)

        padding: dp(5)

        spacing: dp(3)


        canvas.before:

            Color:

                rgba: (1,1,1,1)

            Rectangle:

                pos: self.pos

                size: self.size


        IconNavButton:

            name: "Kasir"

            icon: app.asset_path("assets/icons/kasir.png")

        IconNavButton:

            name: "Produk"

            icon: app.asset_path("assets/icons/produk.png")

        IconNavButton:

            name: "Riwayat"

            icon: app.asset_path("assets/icons/riwayat.png")

        IconNavButton:

            name: "Laporan"

            icon: app.asset_path("assets/icons/laporan.png")

        IconNavButton:

            name: "Pengaturan"

            icon: app.asset_path("assets/icons/pengaturan.png")
'''


# ============================================================
# DATABASE
# ============================================================

class DB:

    def __init__(self, path):

        self.path = path

        folder = os.path.dirname(path)

        if folder:
            os.makedirs(folder, exist_ok=True)

        self.conn = sqlite3.connect(
            path,
            check_same_thread=False,
            timeout=15
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
                active INTEGER NOT NULL DEFAULT 1,
                line_total REAL NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS sales(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice TEXT UNIQUE NOT NULL,
                subtotal REAL NOT NULL DEFAULT 0,
                discount REAL NOT NULL DEFAULT 0,
                tax REAL NOT NULL DEFAULT 0,
                total REAL NOT NULL DEFAULT 0,
                payment_method TEXT NOT NULL DEFAULT 'Tunai',
                paid REAL NOT NULL DEFAULT 0,
                change_amount REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sale_items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                product_id INTEGER,
                name TEXT NOT NULL,
                qty REAL NOT NULL DEFAULT 1,
                price REAL NOT NULL DEFAULT 0,
                line_total REAL NOT NULL DEFAULT 0,
                FOREIGN KEY(sale_id) REFERENCES sales(id)
            );

            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )

        # Migrate databases created by older KasirQU versions.
        columns = {row[1] for row in cursor.execute("PRAGMA table_info(products)").fetchall()}
        migrations = {
            "sku": "ALTER TABLE products ADD COLUMN sku TEXT DEFAULT ''",
            "category": "ALTER TABLE products ADD COLUMN category TEXT DEFAULT ''",
            "cost": "ALTER TABLE products ADD COLUMN cost REAL NOT NULL DEFAULT 0",
            "stock": "ALTER TABLE products ADD COLUMN stock REAL NOT NULL DEFAULT 0",
            "image": "ALTER TABLE products ADD COLUMN image TEXT DEFAULT ''",
            "active": "ALTER TABLE products ADD COLUMN active INTEGER NOT NULL DEFAULT 1",
            "created_at": "ALTER TABLE products ADD COLUMN created_at TEXT DEFAULT ''",
        }
        for name, sql in migrations.items():
            if name not in columns:
                cursor.execute(sql)

        defaults = {
            "store_name": "KasirQU",
            "store_address": "Alamat / Kontak",
            "receipt_footer": "Terima kasih telah berbelanja",
            "paper": "58mm",
            "tax_percent": "0"
        }

        for key, value in defaults.items():
            cursor.execute(
                "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
                (key, value)
            )

        self.conn.commit()

    def setting(self, key):

        row = self.conn.execute(
            """
            SELECT value
            FROM settings
            WHERE key=?
            """,
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

            q = "%" + search.strip() + "%"

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
                ORDER BY name COLLATE NOCASE
                """,
                (q, q, q)
            ).fetchall()

        return self.conn.execute(
            """
            SELECT *
            FROM products
            WHERE active=1
            ORDER BY name COLLATE NOCASE
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
            INSERT INTO products(
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
            "INV-"
            +
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
                INSERT INTO sales(
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
                    WHERE id=?
                    AND active=1
                    """,
                    (item["id"],)
                ).fetchone()

                if not product:
                    raise ValueError(
                        "Produk tidak ditemukan."
                    )

                stock = float(product["stock"])
                qty = float(item["qty"])

                if stock < qty:
                    raise ValueError(
                        "Stok produk tidak mencukupi."
                    )

                cursor.execute(
                    """
                    INSERT INTO sale_items(
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
                    (
                        qty,
                        item["id"]
                    )
                )

            self.conn.commit()

            return invoice

        except Exception:

            self.conn.rollback()

            raise

    def update_product(self, product_id, name, sku, category, price, cost, stock, image):
        self.conn.execute(
            """UPDATE products SET name=?, sku=?, category=?, price=?, cost=?, stock=?, image=? WHERE id=?""",
            (name, sku, category, float(price), float(cost), float(stock), image or "", product_id)
        )
        self.conn.commit()

    def sale(self, sale_id):
        return self.conn.execute("SELECT * FROM sales WHERE id=?", (sale_id,)).fetchone()

    def sale_items(self, sale_id):
        return self.conn.execute(
            "SELECT * FROM sale_items WHERE sale_id=? ORDER BY id", (sale_id,)
        ).fetchall()

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
# COMMON UI HELPERS
# ============================================================

def make_button(
    text,
    primary=False,
    height=44
):

    button = Button(
        text=text,
        size_hint_y=None,
        height=dp(height),
        background_normal="",
        background_down=""
    )

    button.background_color = (
        PRIMARY if primary else WHITE
    )

    button.color = (
        WHITE if primary else TEXT
    )

    button.bold = True

    return button


def text_label(
    text,
    size=14,
    color=TEXT,
    halign="left"
):

    label = Label(
        text=str(text),
        font_size=f"{size}sp",
        color=color,
        halign=halign,
        valign="middle"
    )

    label.bind(
        size=lambda widget, value:
        setattr(
            widget,
            "text_size",
            value
        )
    )

    return label


# ============================================================
# POS SCREEN
# ============================================================

class POSScreen(Screen):

    def on_enter(self):

        self.app = App.get_running_app()

        if not hasattr(self, "cart_data"):
            self.cart_data = []

        self.refresh_products()
        self.render_cart_summary()

    def refresh_products(self, text=""):

        try:

            box = self.ids.products

            box.clear_widgets()

            products = self.app.db.products(text)

            for product in products:

                card = Card(
                    orientation="vertical",
                    size_hint_y=None,
                    height=dp(205),
                    padding=dp(8),
                    spacing=dp(5)
                )

                image_path = self.app.resolve_image(
                    product["image"]
                )

                if image_path:

                    product_image = Image(
                        source=image_path,
                        size_hint_y=None,
                        height=dp(110),
                        allow_stretch=True,
                        keep_ratio=True
                    )
                    product_image.reload()

                    card.add_widget(product_image)

                else:

                    placeholder = Label(
                        text="FOTO",
                        size_hint_y=None,
                        height=dp(110),
                        color=MUTED,
                        font_size="14sp",
                        bold=True
                    )

                    card.add_widget(
                        placeholder
                    )

                info = Label(
                    text=(
                        f'{product["name"]}\n'
                        f'{money(product["price"])}'
                        f'  •  stok '
                        f'{float(product["stock"]):g}'
                    ),
                    color=TEXT,
                    font_size="13sp",
                    bold=True,
                    halign="center",
                    valign="middle"
                )

                info.bind(
                    size=lambda widget, value:
                    setattr(
                        widget,
                        "text_size",
                        value
                    )
                )

                card.add_widget(info)

                button = make_button(
                    "+ Tambah",
                    primary=True,
                    height=36
                )

                button.bind(
                    on_release=lambda *_,
                    product=product:
                    self.add_product(product)
                )

                card.add_widget(button)

                box.add_widget(card)

        except Exception as error:

            self.app.log_error(
                "POS_REFRESH_PRODUCTS",
                error
            )

    def add_product(self, product):

        stock = safe_float(
            product["stock"]
        )

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

                self.render_cart_summary()

                return

        self.cart_data.append(
            {
                "id": product["id"],
                "name": product["name"],
                "price": safe_float(
                    product["price"]
                ),
                "qty": 1,
                "stock": stock
            }
        )

        self.render_cart_summary()

    def calculate_total(
        self,
        discount=0,
        tax_percent=None
    ):

        subtotal = sum(
            item["qty"] * item["price"]
            for item in self.cart_data
        )

        discount = max(
            0,
            safe_float(discount)
        )

        if tax_percent is None:

            tax_percent = safe_float(
                self.app.tax_percent
            )

        tax_percent = max(
            0,
            safe_float(tax_percent)
        )

        taxable = max(
            0,
            subtotal - discount
        )

        tax = (
            taxable
            *
            tax_percent
            /
            100
        )

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

    def render_cart_summary(self):

        try:

            _, _, _, total = (
                self.calculate_total()
            )

            count = sum(
                item["qty"]
                for item in self.cart_data
            )

            self.ids.cart_count.text = (
                f"{count:g} item"
            )

            self.ids.cart_total.text = (
                money(total)
            )

        except Exception as error:

            self.app.log_error(
                "CART_SUMMARY",
                error
            )

    def open_cart_popup(self):

        if not self.cart_data:

            self.app.notify(
                "Keranjang masih kosong."
            )

            return

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=dp(10)
        )

        scroll = ScrollView(
            do_scroll_x=False
        )

        rows = GridLayout(
            cols=1,
            spacing=dp(6),
            size_hint_y=None
        )

        rows.bind(
            minimum_height=rows.setter(
                "height"
            )
        )

        discount = TextInput(
            hint_text="Diskon",
            text="0",
            input_filter="float",
            multiline=False,
            size_hint_y=None,
            height=dp(42)
        )

        tax = TextInput(
            hint_text="Pajak %",
            text=str(
                self.app.tax_percent
            ),
            input_filter="float",
            multiline=False,
            size_hint_y=None,
            height=dp(42)
        )

        total_label = Label(
            text="TOTAL  Rp 0",
            size_hint_y=None,
            height=dp(40),
            font_size="19sp",
            bold=True,
            color=PRIMARY
        )

        def redraw(*_):

            rows.clear_widgets()

            for index, item in enumerate(
                self.cart_data
            ):

                row = Card(
                    orientation="horizontal",
                    size_hint_y=None,
                    height=dp(58),
                    padding=dp(5),
                    spacing=dp(4)
                )

                name = Label(
                    text=(
                        f'{item["name"]}\n'
                        f'{item["qty"]:g} x '
                        f'{money(item["price"])}'
                    ),
                    color=TEXT,
                    halign="left",
                    valign="middle"
                )

                name.bind(
                    size=lambda widget, value:
                    setattr(
                        widget,
                        "text_size",
                        value
                    )
                )

                row.add_widget(name)

                minus = make_button(
                    "-",
                    height=42
                )

                plus = make_button(
                    "+",
                    primary=True,
                    height=42
                )

                delete = make_button(
                    "×",
                    height=42
                )

                minus.size_hint_x = None
                plus.size_hint_x = None
                delete.size_hint_x = None

                minus.width = dp(40)
                plus.width = dp(40)
                delete.width = dp(40)

                minus.bind(
                    on_release=lambda *_,
                    index=index:
                    self.change_qty(
                        index,
                        -1,
                        redraw
                    )
                )

                plus.bind(
                    on_release=lambda *_,
                    index=index:
                    self.change_qty(
                        index,
                        1,
                        redraw
                    )
                )

                delete.bind(
                    on_release=lambda *_,
                    index=index:
                    self.remove_item(
                        index,
                        redraw
                    )
                )

                row.add_widget(minus)
                row.add_widget(plus)
                row.add_widget(delete)

                rows.add_widget(row)

            _, _, _, total = (
                self.calculate_total(
                    discount.text,
                    tax.text
                )
            )

            total_label.text = (
                f"TOTAL  {money(total)}"
            )

        discount.bind(
            text=redraw
        )

        tax.bind(
            text=redraw
        )

        scroll.add_widget(rows)

        content.add_widget(scroll)
        content.add_widget(discount)
        content.add_widget(tax)
        content.add_widget(total_label)

        buttons = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(7)
        )

        clear = make_button(
            "Kosongkan"
        )

        pay = make_button(
            "BAYAR",
            primary=True
        )

        buttons.add_widget(clear)
        buttons.add_widget(pay)

        content.add_widget(buttons)

        popup = Popup(
            title="Keranjang Belanja",
            content=content,
            size_hint=(.94, None),
            size=(dp(430), min(dp(560), max(dp(360), Window.height - dp(100))))
        )

        clear.bind(
            on_release=lambda *_: (
                self.clear_cart(),
                popup.dismiss()
            )
        )

        def payment(*_):

            discount_value = discount.text
            tax_value = tax.text

            popup.dismiss()

            self.open_payment_popup(
                discount_value,
                tax_value
            )

        pay.bind(
            on_release=payment
        )

        popup.open()

        redraw()

    def change_qty(
        self,
        index,
        delta,
        callback=None
    ):

        if (
            0 <= index
            < len(self.cart_data)
        ):

            item = self.cart_data[index]

            item["qty"] += delta

            if item["qty"] <= 0:

                self.cart_data.pop(index)

            elif item["qty"] > item["stock"]:

                item["qty"] = item["stock"]

        self.render_cart_summary()

        if callback:
            callback()

    def remove_item(
        self,
        index,
        callback=None
    ):

        if (
            0 <= index
            < len(self.cart_data)
        ):

            self.cart_data.pop(index)

        self.render_cart_summary()

        if callback:
            callback()

    def open_payment_popup(
        self,
        discount="0",
        tax="0"
    ):

        if not self.cart_data:
            return

        (
            subtotal,
            discount_value,
            tax_value,
            total
        ) = self.calculate_total(
            discount,
            tax
        )

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(9),
            padding=dp(12)
        )

        total_card = Card(
            orientation="vertical",
            size_hint_y=None,
            height=dp(82),
            padding=dp(10)
        )

        total_card.add_widget(
            Label(
                text="TOTAL BELANJA",
                color=MUTED,
                font_size="12sp"
            )
        )

        total_card.add_widget(
            Label(
                text=money(total),
                color=PRIMARY,
                font_size="24sp",
                bold=True
            )
        )

        content.add_widget(total_card)

        method = Spinner(
            text="Tunai",
            values=[
                "Tunai",
                "QRIS",
                "Debit",
                "Kredit",
                "Transfer",
                "E-Wallet"
            ],
            size_hint_y=None,
            height=dp(44)
        )

        paid = TextInput(
            hint_text="Uang diterima",
            input_filter="float",
            multiline=False,
            size_hint_y=None,
            height=dp(44),
            padding=[dp(12), dp(10)]
        )

        change = Label(
            text="Kembalian  Rp 0",
            font_size="16sp",
            bold=True,
            size_hint_y=None,
            height=dp(40),
            color=SUCCESS
        )

        content.add_widget(method)
        content.add_widget(paid)
        content.add_widget(change)

        def update(*_):

            if method.text == "Tunai":

                paid.disabled = False

                paid_value = safe_float(
                    paid.text
                )

                change.text = (
                    "Kembalian  "
                    +
                    money(
                        max(
                            0,
                            paid_value - total
                        )
                    )
                )

            else:

                paid.text = ""
                paid.disabled = True

                change.text = (
                    "Pembayaran non-tunai"
                )

        paid.bind(
            text=update
        )

        method.bind(
            text=update
        )

        buttons = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(7)
        )

        cancel = make_button("Batal")
        done = make_button(
            "SELESAIKAN",
            primary=True
        )

        buttons.add_widget(cancel)
        buttons.add_widget(done)

        content.add_widget(buttons)

        popup = Popup(
            title="Pembayaran",
            content=content,
            size_hint=(.92, None),
            size=(dp(430), min(dp(410), max(dp(330), Window.height - dp(100))))
        )

        cancel.bind(
            on_release=popup.dismiss
        )

        def finish(*_):

            paid_value = safe_float(
                paid.text
            )

            if (
                method.text == "Tunai"
                and
                paid_value < total
            ):

                self.app.notify(
                    "Uang kurang "
                    +
                    money(
                        total - paid_value
                    )
                )

                return

            if method.text != "Tunai":
                paid_value = total

            change_value = (
                max(
                    0,
                    paid_value - total
                )
                if method.text == "Tunai"
                else 0
            )

            try:

                cart_snapshot = [
                    dict(item)
                    for item in self.cart_data
                ]

                invoice = (
                    self.app.db.create_sale(
                        cart_snapshot,
                        subtotal,
                        discount_value,
                        tax_value,
                        total,
                        method.text,
                        paid_value,
                        change_value
                    )
                )

                self.app.last_receipt = (
                    invoice,
                    subtotal,
                    discount_value,
                    tax_value,
                    total,
                    method.text,
                    paid_value,
                    change_value,
                    cart_snapshot
                )

                self.clear_cart()

                popup.dismiss()

                self.app.root.ids.sm.current = (
                    "transactions"
                )

                self.app.notify(
                    f"Transaksi {invoice} berhasil."
                )

                self.app.print_or_offer(
                    invoice
                )

            except Exception as error:

                self.app.log_error(
                    "CHECKOUT",
                    error
                )

                self.app.notify(
                    "Transaksi gagal:\n"
                    +
                    str(error)
                )

        done.bind(
            on_release=finish
        )

        popup.open()

        update()

    def clear_cart(self):

        self.cart_data = []

        self.render_cart_summary()


# ============================================================
# PRODUCT SCREEN
# ============================================================

class ProductScreen(Screen):

    def on_enter(self):

        self.app = App.get_running_app()

        self.refresh()

    def refresh(self, search=""):

        try:

            box = self.ids.list

            box.clear_widgets()

            products = self.app.db.products(search)

            for product in products:

                row = Card(
                    orientation="horizontal",
                    size_hint_y=None,
                    height=dp(92),
                    spacing=dp(9),
                    padding=dp(7)
                )

                image_path = (
                    self.app.resolve_image(
                        product["image"]
                    )
                )

                if image_path:

                    image = Image(
                        source=image_path,
                        size_hint_x=None,
                        width=dp(78),
                        allow_stretch=True,
                        keep_ratio=True
                    )
                    image.reload()

                    row.add_widget(image)

                else:

                    placeholder = Label(
                        text="FOTO",
                        size_hint_x=None,
                        width=dp(78),
                        color=MUTED,
                        bold=True
                    )

                    row.add_widget(
                        placeholder
                    )

                info = Label(
                    text=(
                        f'{product["name"]}\n'
                        f'{money(product["price"])}'
                        f'  •  stok '
                        f'{float(product["stock"]):g}\n'
                        f'{product["category"] or "Tanpa kategori"}'
                    ),
                    color=TEXT,
                    halign="left",
                    valign="middle"
                )

                info.bind(
                    size=lambda widget, value:
                    setattr(
                        widget,
                        "text_size",
                        value
                    )
                )

                row.add_widget(info)

                edit_button = make_button("EDIT", primary=True, height=40)
                edit_button.size_hint_x = None
                edit_button.width = dp(62)
                edit_button.bind(
                    on_release=lambda *_ , product=product: self.open_editor(product)
                )
                row.add_widget(edit_button)

                box.add_widget(row)

        except Exception as error:

            self.app.log_error(
                "PRODUCT_REFRESH",
                error
            )

    def open_editor(self, product=None):

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(7),
            padding=dp(10)
        )

        preview = Image(
            source="",
            size_hint_y=None,
            height=dp(145),
            allow_stretch=True,
            keep_ratio=True
        )

        content.add_widget(preview)

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
                height=dp(42),
                padding=[dp(10), dp(9)],
                background_normal="",
                background_color=WHITE
            )

            fields[key] = field

            content.add_widget(field)

        choose = make_button(
            "PILIH FOTO PRODUK",
            primary=False,
            height=42
        )

        content.add_widget(choose)

        selected = {
            "path": ""
        }

        if product:
            for key in ("name", "sku", "category", "price", "cost", "stock"):
                fields[key].text = str(product[key] if product[key] is not None else "")
            selected["path"] = self.app.resolve_image(product["image"])
            if selected["path"]:
                preview.source = selected["path"]
                preview.reload()

        buttons = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(7)
        )

        cancel = make_button("Batal")

        save = make_button(
            "Simpan",
            primary=True
        )

        buttons.add_widget(cancel)
        buttons.add_widget(save)

        content.add_widget(buttons)

        popup = Popup(
            title="Edit Produk" if product else "Tambah Produk",
            content=content,
            size_hint=(.94, None),
            size=(dp(430), dp(560)),
            auto_dismiss=True
        )

        choose.bind(
            on_release=lambda *_:
            self.pick_image(
                selected,
                preview
            )
        )

        cancel.bind(
            on_release=popup.dismiss
        )

        def save_product(*_):

            name = fields["name"].text.strip()

            if not name:

                self.app.notify(
                    "Nama produk wajib diisi."
                )

                return

            try:

                image_path = ""

                if selected["path"]:

                    image_path = (
                        self.app.save_selected_image(
                            selected["path"]
                        )
                    )

                    if not image_path:

                        self.app.notify(
                            "Foto tidak dapat disimpan."
                        )

                        return

                if product:
                    self.app.db.update_product(
                        product["id"], name,
                        fields["sku"].text.strip(),
                        fields["category"].text.strip(),
                        safe_float(fields["price"].text),
                        safe_float(fields["cost"].text),
                        safe_float(fields["stock"].text),
                        image_path or selected.get("path", "")
                    )
                    message = "Produk berhasil diperbarui."
                else:
                    self.app.db.add_product(
                        name,
                        fields["sku"].text.strip(),
                        fields["category"].text.strip(),
                        safe_float(fields["price"].text),
                        safe_float(fields["cost"].text),
                        safe_float(fields["stock"].text),
                        image_path
                    )
                    message = "Produk berhasil ditambahkan."

                popup.dismiss()
                self.refresh()
                self.app.root.ids.sm.get_screen("pos").refresh_products()
                self.app.notify(message)

            except Exception as error:

                self.app.log_error(
                    "SAVE_PRODUCT",
                    error
                )

                self.app.notify(
                    "Produk gagal disimpan:\n"
                    +
                    str(error)
                )

        save.bind(
            on_release=save_product
        )

        popup.open()

    def pick_image(
        self,
        selected,
        preview
    ):

        self.app.open_image_picker(
            selected,
            preview
        )


# ============================================================
# TRANSACTION SCREEN
# ============================================================

class TransactionScreen(Screen):

    def on_enter(self):

        self.app = App.get_running_app()

        self.refresh()

    def refresh(self):

        try:

            box = self.ids.list

            box.clear_widgets()

            for sale in self.app.db.sales():

                row = Card(
                    orientation="horizontal",
                    size_hint_y=None,
                    height=dp(82),
                    padding=dp(10),
                    spacing=dp(8)
                )

                info = Label(
                    text=(
                        f'{sale["invoice"]}\n'
                        f'{sale["created_at"]}\n'
                        f'{sale["payment_method"]}'
                    ),
                    color=TEXT,
                    halign="left",
                    valign="middle"
                )

                info.bind(
                    size=lambda widget, value:
                    setattr(
                        widget,
                        "text_size",
                        value
                    )
                )

                total = Label(
                    text=money(
                        sale["total"]
                    ),
                    color=PRIMARY,
                    bold=True,
                    font_size="15sp",
                    size_hint_x=.35,
                    halign="right",
                    valign="middle"
                )

                total.bind(
                    size=lambda widget, value:
                    setattr(
                        widget,
                        "text_size",
                        value
                    )
                )

                row.add_widget(info)
                row.add_widget(total)

                detail = make_button("DETAIL", primary=True, height=42)
                detail.size_hint_x = None
                detail.width = dp(72)
                detail.bind(on_release=lambda *_ , sale_id=sale["id"]: self.open_detail(sale_id))
                row.add_widget(detail)

                box.add_widget(row)

        except Exception as error:

            self.app.log_error(
                "TRANSACTION_REFRESH",
                error
            )

    def open_detail(self, sale_id):
        sale = self.app.db.sale(sale_id)
        items = self.app.db.sale_items(sale_id)
        if not sale:
            self.app.notify("Transaksi tidak ditemukan.")
            return

        content = BoxLayout(orientation="vertical", spacing=dp(7), padding=dp(12))
        details = [f"{sale['invoice']}", f"{sale['created_at']}", ""]
        for item in items:
            details.append(f"{item['name']}  x{item['qty']:g}  {money(item['line_total'])}")
        details += ["", f"Subtotal: {money(sale['subtotal'])}", f"Diskon: {money(sale['discount'])}", f"Pajak: {money(sale['tax'])}", f"TOTAL: {money(sale['total'])}", f"Pembayaran: {sale['payment_method']}"]
        if sale['payment_method'] == "Tunai":
            details += [f"Dibayar: {money(sale['paid'])}", f"Kembalian: {money(sale['change_amount'])}"]

        label = text_label("\n".join(details), size=13)
        content.add_widget(label)
        buttons = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(7))
        close = make_button("Tutup")
        print_btn = make_button("Cetak Ulang", primary=True)
        buttons.add_widget(close); buttons.add_widget(print_btn)
        content.add_widget(buttons)
        popup = Popup(title="Detail Transaksi", content=content, size_hint=(.92, None), size=(dp(430), dp(470)))
        close.bind(on_release=popup.dismiss)

        cart = [dict(item) for item in items]
        self.app.last_receipt = (sale['invoice'], sale['subtotal'], sale['discount'], sale['tax'], sale['total'], sale['payment_method'], sale['paid'], sale['change_amount'], cart)
        print_btn.bind(on_release=lambda *_: (popup.dismiss(), self.app.bluetooth_printer_dialog()))
        popup.open()


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
                    COALESCE(SUM(total),0) total,
                    COALESCE((SELECT SUM(qty) FROM sale_items si JOIN sales sx ON sx.id=si.sale_id WHERE date(sx.created_at)=date('now')),0) items_sold
                FROM sales
                WHERE date(created_at)=date('now')
                """
            ).fetchone()

            self.ids.summary.text = (
                "PENJUALAN HARI INI\n\n"
                f"Transaksi     : {rows['n']}\n"
                f"Subtotal      : {money(rows['subtotal'])}\n"
                f"Diskon        : {money(rows['discount'])}\n"
                f"Pajak         : {money(rows['tax'])}\n"
                f"Barang terjual: {float(rows['items_sold']):g} item\n\n"
                f"TOTAL         : {money(rows['total'])}"
            )

        except Exception as error:

            self.app.log_error(
                "REPORT_REFRESH",
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
                "CSV berhasil dibuat:\n"
                +
                path
            )

        except Exception as error:

            self.app.log_error(
                "EXPORT_CSV",
                error
            )

            self.app.notify(
                "Export CSV gagal."
            )


# ============================================================
# SETTINGS
# ============================================================

class SettingsScreen(Screen):

    def on_enter(self):

        self.app = App.get_running_app()

        try:

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
                self.app.db.setting("paper") or "58mm"
            )
            self.ids.tax.text = (
                self.app.db.setting("tax_percent") or "0"
            )

        except Exception as error:

            self.app.log_error(
                "SETTINGS_LOAD",
                error
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
                "paper", self.ids.paper.text
            )
            self.app.db.set_setting(
                "tax_percent", str(max(0, safe_float(self.ids.tax.text)))
            )

            self.app.tax_percent = (
                self.app.db.setting(
                    "tax_percent"
                )
                or
                "0"
            )

            self.app.notify(
                "Pengaturan berhasil disimpan."
            )

        except Exception as error:

            self.app.log_error(
                "SETTINGS_SAVE",
                error
            )

    def backup(self):

        try:

            self.app.db.conn.commit()

            target = os.path.join(
                self.app.user_data_dir,
                "KasirQU_backup.db"
            )

            shutil.copy2(
                self.app.db.path,
                target
            )

            self.app.notify(
                "Backup database berhasil:\n"
                +
                target
            )

        except Exception as error:

            self.app.log_error(
                "DATABASE_BACKUP",
                error
            )

            self.app.notify(
                "Backup gagal."
            )


# ============================================================
# MAIN APP
# ============================================================

class UniversalPOS(App):

    tax_percent = StringProperty("0")

    last_receipt = None

    pending_image = None

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.startup_error = None

        self.images_dir = ""

        self._activity_callback = None

    # --------------------------------------------------------
    # ERROR LOG
    # --------------------------------------------------------

    def log_error(
        self,
        location,
        error
    ):

        try:

            os.makedirs(
                self.user_data_dir,
                exist_ok=True
            )

            error_path = os.path.join(
                self.user_data_dir,
                "KasirQU_error.log"
            )

            with open(
                error_path,
                "a",
                encoding="utf-8"
            ) as file:

                file.write(
                    "\n\n"
                    +
                    "=" * 60
                    +
                    "\n"
                )

                file.write(
                    datetime.now().isoformat()
                    +
                    "\n"
                )

                file.write(
                    "LOCATION: "
                    +
                    str(location)
                    +
                    "\n"
                )

                file.write(
                    "ERROR: "
                    +
                    repr(error)
                    +
                    "\n"
                )

                file.write(
                    traceback.format_exc()
                )

        except Exception:
            pass

        print(
            "KASIRQU ERROR:",
            location,
            repr(error)
        )

    # --------------------------------------------------------
    # BUILD
    # --------------------------------------------------------

    def build(self):

        try:

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
                or
                "0"
            )

            root = Builder.load_string(KV)

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

            return self.build_error_screen(
                error
            )

    # --------------------------------------------------------
    # ERROR SCREEN
    # --------------------------------------------------------

    def build_error_screen(self, error):

        root = BoxLayout(
            orientation="vertical",
            padding=dp(24),
            spacing=dp(15)
        )

        with root.canvas.before:

            Color(*BG)

            from kivy.graphics import Rectangle

            root._bg = Rectangle(
                pos=root.pos,
                size=root.size
            )

        root.bind(
            pos=lambda obj, value:
            setattr(
                obj._bg,
                "pos",
                value
            ),
            size=lambda obj, value:
            setattr(
                obj._bg,
                "size",
                value
            )
        )

        root.add_widget(
            Label(
                text="KasirQU",
                color=PRIMARY,
                font_size="27sp",
                bold=True,
                size_hint_y=None,
                height=dp(55)
            )
        )

        detail = Label(
            text=(
                "Aplikasi gagal memuat UI.\n\n"
                +
                type(error).__name__
                +
                ": "
                +
                str(error)
                +
                "\n\n"
                "Detail tersimpan di:\n"
                +
                os.path.join(
                    self.user_data_dir,
                    "KasirQU_error.log"
                )
            ),
            color=TEXT,
            halign="center",
            valign="middle"
        )

        detail.bind(
            size=lambda widget, value:
            setattr(
                widget,
                "text_size",
                value
            )
        )

        root.add_widget(detail)

        return root

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    def on_start(self):

        Clock.schedule_once(
            self.finish_startup,
            .5
        )

    def finish_startup(self, *_):

        try:

            if self.startup_error is not None:
                return

            if not self.root:
                raise RuntimeError(
                    "Root aplikasi tidak tersedia."
                )

            if not hasattr(
                self.root,
                "ids"
            ):
                raise RuntimeError(
                    "Root tidak memiliki ids."
                )

            if "sm" not in self.root.ids:

                raise RuntimeError(
                    "ScreenManager id 'sm' tidak ditemukan."
                )

            sm = self.root.ids.sm

            sm.current = "pos"

            pos = sm.get_screen("pos")

            pos.refresh_products()

        except Exception as error:

            self.startup_error = error

            self.log_error(
                "FIRST_UI",
                error
            )

        finally:

            self.hide_android_loading_screen()

    # --------------------------------------------------------
    # ANDROID LOADING SCREEN
    # --------------------------------------------------------

    def hide_android_loading_screen(self):

        if platform != "android":
            return

        try:

            from android import loadingscreen

            loadingscreen.hide_loading_screen()

        except Exception:

            pass

    # --------------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------------

    def navigate(self, name):

        try:

            sm = self.root.ids.sm

            names = list(
                sm.screen_names
            )

            if name not in names:
                return

            current = names.index(
                sm.current
            )

            target = names.index(
                name
            )

            if current == target:
                return

            sm.transition = SlideTransition(
                direction=(
                    "left"
                    if target > current
                    else "right"
                ),
                duration=.20
            )

            sm.current = name

        except Exception as error:

            self.log_error(
                "NAVIGATION",
                error
            )

    # --------------------------------------------------------
    # NOTIFY
    # --------------------------------------------------------

    def notify(self, message):

        try:

            content = BoxLayout(
                orientation="vertical",
                padding=dp(12),
                spacing=dp(10)
            )

            label = Label(
                text=str(message),
                color=TEXT,
                halign="center",
                valign="middle"
            )

            label.bind(
                size=lambda widget, value:
                setattr(
                    widget,
                    "text_size",
                    value
                )
            )

            content.add_widget(label)

            close = make_button(
                "OK",
                primary=True
            )

            content.add_widget(close)

            line_count = max(1, str(message).count("\n") + 1)
            popup = Popup(
                title=APP_NAME,
                content=content,
                size_hint=(.88, None),
                size=(dp(400), min(dp(260), dp(112 + line_count * 20)))
            )

            close.bind(
                on_release=popup.dismiss
            )

            popup.open()

        except Exception as error:

            self.log_error(
                "NOTIFY",
                error
            )

    # ========================================================
    # IMAGE SYSTEM
    # ========================================================

    def asset_path(self, relative):
        try:
            base = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(base, relative)
        except Exception:
            return relative

    def resolve_image(self, path):

        if not path:
            return ""

        try:

            path = str(path).strip()

            if not path:
                return ""

            # Absolute path
            absolute = os.path.abspath(path)

            if os.path.isfile(absolute):
                return absolute

            # Filename only
            filename = os.path.basename(path)

            internal = os.path.join(
                self.images_dir,
                filename
            )

            if os.path.isfile(internal):
                return internal

            return ""

        except Exception as error:

            self.log_error(
                "RESOLVE_IMAGE",
                error
            )

            return ""

    # --------------------------------------------------------
    # ANDROID IMAGE PICKER
    # --------------------------------------------------------

    def open_image_picker(
        self,
        selected,
        preview
    ):

        if platform != "android":

            self.open_desktop_picker(
                selected,
                preview
            )

            return

        try:

            from jnius import autoclass

            from android.activity import (
                bind
            )

            Intent = autoclass(
                "android.content.Intent"
            )

            intent = Intent(
                Intent.ACTION_OPEN_DOCUMENT
            )

            intent.addCategory(
                Intent.CATEGORY_OPENABLE
            )

            intent.setType(
                "image/*"
            )

            # Sangat penting:
            # izin URI tetap dipertahankan jika Android mendukungnya.
            try:

                intent.addFlags(
                    Intent.FLAG_GRANT_READ_URI_PERMISSION
                    |
                    Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION
                )

            except Exception:
                pass

            self.pending_image = (
                selected,
                preview
            )

            self._activity_callback = (
                self.on_activity_result
            )

            bind(
                on_activity_result=
                self.on_activity_result
            )

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )

            PythonActivity.mActivity.startActivityForResult(
                intent,
                9001
            )

        except Exception as error:

            self.log_error(
                "ANDROID_IMAGE_PICKER",
                error
            )

            self.notify(
                "Pemilih foto Android gagal dibuka."
            )

    # --------------------------------------------------------
    # ACTIVITY RESULT
    # --------------------------------------------------------

    def on_activity_result(
        self,
        request_code,
        result_code,
        intent
    ):

        if request_code != 9001:
            return

        try:

            if intent is None:
                return

            uri = intent.getData()

            if uri is None:
                return

            # Pertahankan izin URI jika tersedia.
            try:

                from jnius import autoclass

                IntentClass = autoclass(
                    "android.content.Intent"
                )

                resolver = (
                    autoclass(
                        "org.kivy.android.PythonActivity"
                    )
                    .mActivity
                    .getContentResolver()
                )

                flags = (
                    IntentClass.FLAG_GRANT_READ_URI_PERMISSION
                )

                resolver.takePersistableUriPermission(
                    uri,
                    flags
                )

            except Exception:

                pass

            temp_path = (
                self.copy_content_uri(
                    uri
                )
            )

            if (
                temp_path
                and
                self.pending_image
            ):

                selected, preview = (
                    self.pending_image
                )

                selected["path"] = (
                    temp_path
                )

                preview.source = temp_path

                preview.reload()

        except Exception as error:

            self.log_error(
                "ACTIVITY_RESULT_IMAGE",
                error
            )

            self.notify(
                "Foto tidak dapat dibaca."
            )

        finally:

            try:

                from android.activity import (
                    unbind
                )

                unbind(
                    on_activity_result=
                    self.on_activity_result
                )

            except Exception:
                pass

            self.pending_image = None

    # --------------------------------------------------------
    # COPY CONTENT URI
    # --------------------------------------------------------

    def copy_content_uri(self, uri):

        input_stream = None
        output_stream = None

        try:

            from jnius import (
                autoclass,
                jarray
            )

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )

            resolver = (
                PythonActivity
                .mActivity
                .getContentResolver()
            )

            input_stream = (
                resolver.openInputStream(
                    uri
                )
            )

            if input_stream is None:

                raise RuntimeError(
                    "Content URI tidak dapat dibaca."
                )

            mime = None

            try:

                mime = resolver.getType(uri)

                if mime:
                    mime = str(mime)

            except Exception:

                mime = None

            extension_map = {
                "image/jpeg": ".jpg",
                "image/jpg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
                "image/gif": ".gif",
                "image/bmp": ".bmp"
            }

            extension = extension_map.get(
                mime,
                ".jpg"
            )

            FileOutputStream = autoclass(
                "java.io.FileOutputStream"
            )

            filename = (
                "product_"
                +
                datetime.now().strftime(
                    "%Y%m%d%H%M%S%f"
                )
                +
                extension
            )

            target = os.path.join(
                self.images_dir,
                filename
            )

            output_stream = FileOutputStream(
                target
            )

            buffer = jarray(
                "b",
                [0] * 8192
            )

            while True:

                count = (
                    input_stream.read(
                        buffer
                    )
                )

                if count <= 0:
                    break

                output_stream.write(
                    buffer,
                    0,
                    count
                )

            output_stream.flush()

            if not os.path.isfile(target):

                raise RuntimeError(
                    "File foto tidak berhasil dibuat."
                )

            return target

        except Exception as error:

            self.log_error(
                "COPY_CONTENT_URI",
                error
            )

            return ""

        finally:

            if output_stream is not None:

                try:
                    output_stream.close()
                except Exception:
                    pass

            if input_stream is not None:

                try:
                    input_stream.close()
                except Exception:
                    pass

    # --------------------------------------------------------
    # DESKTOP PICKER
    # --------------------------------------------------------

    def open_desktop_picker(
        self,
        selected,
        preview
    ):

        try:

            chooser = FileChooserListView(
                path=os.path.expanduser("~"),
                filters=[
                    "*.png",
                    "*.jpg",
                    "*.jpeg",
                    "*.webp",
                    "*.gif"
                ]
            )

            buttons = BoxLayout(
                size_hint_y=None,
                height=dp(46),
                spacing=dp(7)
            )

            select_btn = make_button(
                "Pilih",
                primary=True
            )

            cancel_btn = make_button(
                "Batal"
            )

            buttons.add_widget(
                select_btn
            )

            buttons.add_widget(
                cancel_btn
            )

            root = BoxLayout(
                orientation="vertical"
            )

            root.add_widget(
                chooser
            )

            root.add_widget(
                buttons
            )

            popup = Popup(
                title="Pilih Foto Produk",
                content=root,
                size_hint=(.94, None),
                size=(dp(430), min(dp(620), max(dp(420), Window.height - dp(100))))
            )

            def choose(*_):

                if not chooser.selection:

                    self.notify(
                        "Pilih foto terlebih dahulu."
                    )

                    return

                selected["path"] = (
                    chooser.selection[0]
                )

                preview.source = (
                    selected["path"]
                )

                preview.reload()

                popup.dismiss()

            select_btn.bind(
                on_release=choose
            )

            cancel_btn.bind(
                on_release=popup.dismiss
            )

            popup.open()

        except Exception as error:

            self.log_error(
                "DESKTOP_IMAGE_PICKER",
                error
            )

    # --------------------------------------------------------
    # SAVE SELECTED IMAGE
    # --------------------------------------------------------

    def save_selected_image(self, path):

        if not path:
            return ""

        try:

            source = os.path.abspath(
                str(path)
            )

            if not os.path.isfile(source):
                return ""

            images_dir = os.path.abspath(
                self.images_dir
            )

            os.makedirs(
                images_dir,
                exist_ok=True
            )

            # Sudah internal
            if (
                source == images_dir
                or
                source.startswith(
                    images_dir + os.sep
                )
            ):

                return source

            extension = (
                os.path.splitext(source)[1]
                .lower()
            )

            if extension not in (
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
                ".gif",
                ".bmp"
            ):

                extension = ".jpg"

            destination = os.path.join(
                images_dir,
                "product_"
                +
                datetime.now().strftime(
                    "%Y%m%d%H%M%S%f"
                )
                +
                extension
            )

            shutil.copy2(
                source,
                destination
            )

            if not os.path.isfile(
                destination
            ):

                return ""

            return destination

        except Exception as error:

            self.log_error(
                "SAVE_SELECTED_IMAGE",
                error
            )

            return ""

    # ========================================================
    # PRINT
    # ========================================================

    def print_or_offer(self, invoice):

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=dp(10)
        )

        content.add_widget(
            text_label(
                f"Transaksi {invoice} berhasil.\n"
                "Cetak struk sekarang?",
                size=15,
                halign="center"
            )
        )

        row = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(7)
        )

        bluetooth = make_button(
            "Bluetooth",
            primary=True
        )

        no_print = make_button(
            "Tidak"
        )

        row.add_widget(bluetooth)
        row.add_widget(no_print)

        content.add_widget(row)

        popup = Popup(
            title="Struk",
            content=content,
            size_hint=(.88, None),
            size=(dp(400), dp(190))
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

    # --------------------------------------------------------
    # BLUETOOTH DEVICES
    # --------------------------------------------------------

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
            size_hint=(.92, None),
            size=(dp(430), min(dp(500), max(dp(300), Window.height - dp(100))))
        )

        for name, address in devices:

            btn = make_button(
                f"{name}\n{address}",
                height=60
            )

            btn.bind(
                on_release=lambda *_,
                addr=address: (
                    popup.dismiss(),
                    self.print_bluetooth(addr)
                )
            )

            content.add_widget(btn)

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

            devices = (
                adapter
                .getBondedDevices()
                .toArray()
            )

            result = []

            for device in devices:

                try:

                    name = str(
                        device.getName()
                        or
                        "Bluetooth Device"
                    )

                    address = str(
                        device.getAddress()
                    )

                    result.append(
                        (
                            name,
                            address
                        )
                    )

                except Exception:
                    pass

            return result

        except Exception as error:

            self.log_error(
                "BLUETOOTH_DEVICES",
                error
            )

            return []

    # --------------------------------------------------------
    # BLUETOOTH PRINT
    # --------------------------------------------------------

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
                adapter.getRemoteDevice(
                    address
                )
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
                socket.getOutputStream()
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
                +
                str(error)
            )

        finally:

            if socket is not None:

                try:
                    socket.close()
                except Exception:
                    pass

    # ========================================================
    # RECEIPT
    # ========================================================

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
            or
            "58mm"
        )

        width = (
            32
            if paper == "58mm"
            else 48
        )

        store = (
            self.db.setting(
                "store_name"
            )
            or
            APP_NAME
        )

        address = (
            self.db.setting(
                "store_address"
            )
            or
            ""
        )

        footer = (
            self.db.setting(
                "receipt_footer"
            )
            or
            "Terima kasih"
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

            lines.append(name)

            lines.append(
                "  "
                +
                f'{item["qty"]:g}'
                +
                " x "
                +
                money(
                    item["price"]
                )
                +
                " = "
                +
                money(
                    item["qty"]
                    *
                    item["price"]
                )
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
                "",
                ""
            ]
        )

        raw = "\n".join(
            lines
        ).encode(
            "utf-8",
            "replace"
        )

        return (
            b"\x1b\x40"
            +
            b"\x1b\x45\x01"
            +
            raw
            +
            b"\x1b\x45\x00"
            +
            b"\n\n\n"
            +
            b"\x1d\x56\x00"
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        UniversalPOS().run()

    except Exception as error:

        try:

            app = UniversalPOS()

            app.log_error(
                "FATAL_ENTRY_POINT",
                error
            )

        except Exception:

            pass

        raise
