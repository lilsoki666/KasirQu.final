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
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
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
# CONSTANT
# ============================================================

APP_NAME = "KasirQU"
DB_NAME = "KasirQU.db"


# ============================================================
# UTILITY
# ============================================================

def money(value):
    try:
        number = Decimal(str(value)).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )

        return "Rp {:,}".format(
            number
        ).replace(",", ".")

    except Exception:
        return "Rp 0"


def safe_float(value, default=0):
    try:
        if value is None:
            return default

        text = str(value).strip()

        if not text:
            return default

        return float(text)

    except Exception:
        return default


# ============================================================
# CARD
# ============================================================

class Card(BoxLayout):

    radius = NumericProperty(dp(14))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(
                1,
                1,
                1,
                1
            )

            self._background_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[self.radius]
            )

        self.bind(
            pos=self._update_background,
            size=self._update_background,
            radius=self._update_background
        )

    def _update_background(self, *_):
        self._background_rect.pos = self.pos
        self._background_rect.size = self.size
        self._background_rect.radius = [self.radius]


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
                abs(dx) > dp(60)
                and
                abs(dx) > abs(dy) * 1.2
            ):
                self.swipe(
                    -1 if dx > 0 else 1
                )

        self._touch_start = None

        return result

    def swipe(self, delta):

        names = list(self.screen_names)

        if not names:
            return

        if self.current not in names:
            return

        current_index = names.index(
            self.current
        )

        target_index = (
            current_index + delta
        )

        if target_index < 0:
            return

        if target_index >= len(names):
            return

        self.transition = SlideTransition(
            direction=(
                "right"
                if delta < 0
                else "left"
            ),
            duration=0.18
        )

        self.current = names[target_index]


# ============================================================
# KV
# ============================================================

KV = r'''
#:import dp kivy.metrics.dp


<PrimaryButton@Button>:

    background_normal: ""

    background_color:
        (.12,.32,.78,1) if self.state == "normal" else (.08,.25,.64,1)

    color:
        1,1,1,1

    bold: True

    size_hint_y: None

    height: dp(46)


<SoftButton@Button>:

    background_normal: ""

    background_color:
        (.93,.95,.98,1) if self.state == "normal" else (.86,.90,.96,1)

    color:
        (.10,.14,.20,1)

    bold: True

    size_hint_y: None

    height: dp(42)


<NavButton@Button>:

    background_normal: ""

    background_color:
        (.12,.32,.78,1) if self.state == "down" else (1,1,1,1)

    color:
        (1,1,1,1) if self.state == "down" else (.12,.32,.78,1)

    font_size: "10sp"

    bold: True


<ScreenTitle@Label>:

    color:
        (.07,.09,.13,1)

    font_size:
        "21sp"

    bold:
        True

    halign:
        "left"

    valign:
        "middle"


# ============================================================
# POS
# ============================================================

<POSScreen>:

    BoxLayout:

        orientation: "vertical"

        padding: dp(12)

        spacing: dp(10)


        canvas.before:

            Color:

                rgba:
                    (.96,.97,.99,1)

            Rectangle:

                pos:
                    self.pos

                size:
                    self.size


        BoxLayout:

            size_hint_y: None

            height: dp(48)

            spacing: dp(8)


            Label:

                text:
                    "KasirQU"

                color:
                    (.07,.09,.13,1)

                font_size:
                    "22sp"

                bold:
                    True

                size_hint_x:
                    .28


            TextInput:

                id: search

                hint_text:
                    "Cari produk / SKU..."

                multiline:
                    False

                padding:
                    [dp(12), dp(10)]

                background_color:
                    (1,1,1,1)

                on_text:
                    root.refresh_products(self.text)


        Label:

            text:
                "Pilih produk"

            size_hint_y:
                None

            height:
                dp(26)

            color:
                (.35,.39,.46,1)

            halign:
                "left"

            text_size:
                self.size


        ScrollView:

            do_scroll_x:
                False

            GridLayout:

                id: products

                cols:
                    2

                spacing:
                    dp(10)

                padding:
                    dp(2)

                size_hint_y:
                    None

                height:
                    self.minimum_height


        Card:

            size_hint_y:
                None

            height:
                dp(70)

            padding:
                dp(10)

            spacing:
                dp(8)

            orientation:
                "horizontal"


            Label:

                id: cart_count

                text:
                    "0 item"

                color:
                    (.10,.14,.20,1)

                bold:
                    True

                size_hint_x:
                    .30


            Label:

                id: cart_total

                text:
                    "Rp 0"

                color:
                    (.12,.32,.78,1)

                font_size:
                    "18sp"

                bold:
                    True

                halign:
                    "right"

                text_size:
                    self.size


            SoftButton:

                text:
                    "KERANJANG"

                size_hint_x:
                    .30

                on_release:
                    root.open_cart_popup()


# ============================================================
# PRODUCTS
# ============================================================

<ProductScreen>:

    BoxLayout:

        orientation:
            "vertical"

        padding:
            dp(12)

        spacing:
            dp(10)


        canvas.before:

            Color:

                rgba:
                    (.96,.97,.99,1)

            Rectangle:

                pos:
                    self.pos

                size:
                    self.size


        BoxLayout:

            size_hint_y:
                None

            height:
                dp(48)


            ScreenTitle:

                text:
                    "Produk"


            PrimaryButton:

                text:
                    "+ Produk"

                size_hint_x:
                    .30

                on_release:
                    root.open_editor()


        TextInput:

            id: search

            hint_text:
                "Cari nama, SKU, kategori..."

            multiline:
                False

            size_hint_y:
                None

            height:
                dp(44)

            on_text:
                root.refresh(self.text)


        ScrollView:

            do_scroll_x:
                False

            GridLayout:

                id: list

                cols:
                    1

                spacing:
                    dp(8)

                padding:
                    dp(2)

                size_hint_y:
                    None

                height:
                    self.minimum_height


# ============================================================
# TRANSACTIONS
# ============================================================

<TransactionScreen>:

    BoxLayout:

        orientation:
            "vertical"

        padding:
            dp(12)

        spacing:
            dp(10)


        canvas.before:

            Color:

                rgba:
                    (.96,.97,.99,1)

            Rectangle:

                pos:
                    self.pos

                size:
                    self.size


        ScreenTitle:

            text:
                "Riwayat Transaksi"

            size_hint_y:
                None

            height:
                dp(48)


        ScrollView:

            do_scroll_x:
                False

            GridLayout:

                id: list

                cols:
                    1

                spacing:
                    dp(8)

                padding:
                    dp(2)

                size_hint_y:
                    None

                height:
                    self.minimum_height


# ============================================================
# REPORT
# ============================================================

<ReportScreen>:

    BoxLayout:

        orientation:
            "vertical"

        padding:
            dp(12)

        spacing:
            dp(10)


        canvas.before:

            Color:

                rgba:
                    (.96,.97,.99,1)

            Rectangle:

                pos:
                    self.pos

                size:
                    self.size


        ScreenTitle:

            text:
                "Laporan"

            size_hint_y:
                None

            height:
                dp(48)


        Card:

            orientation:
                "vertical"

            padding:
                dp(16)

            size_hint_y:
                None

            height:
                dp(190)


            Label:

                id: summary

                text:
                    "Memuat..."

                color:
                    (.10,.14,.20,1)

                font_size:
                    "16sp"

                halign:
                    "left"

                valign:
                    "top"

                text_size:
                    self.size


        PrimaryButton:

            text:
                "Export CSV"

            on_release:
                root.export_csv()


        Widget:


# ============================================================
# SETTINGS
# ============================================================

<SettingsScreen>:

    BoxLayout:

        orientation:
            "vertical"

        padding:
            dp(12)

        spacing:
            dp(10)


        canvas.before:

            Color:

                rgba:
                    (.96,.97,.99,1)

            Rectangle:

                pos:
                    self.pos

                size:
                    self.size


        ScreenTitle:

            text:
                "Pengaturan"

            size_hint_y:
                None

            height:
                dp(48)


        TextInput:

            id: store

            hint_text:
                "Nama usaha"

            multiline:
                False


        TextInput:

            id: address

            hint_text:
                "Alamat / kontak"

            multiline:
                False


        TextInput:

            id: footer

            hint_text:
                "Footer struk"

            multiline:
                False


        Spinner:

            id: paper

            text:
                "58mm"

            values:
                ["58mm","80mm"]

            size_hint_y:
                None

            height:
                dp(44)


        PrimaryButton:

            text:
                "Simpan Pengaturan"

            on_release:
                root.save()


        SoftButton:

            text:
                "Backup Database"

            on_release:
                root.backup()


        Label:

            text:
                "Printer thermal Bluetooth harus sudah dipairing melalui Android."

            color:
                (.38,.42,.48,1)

            text_size:
                self.width, None

            halign:
                "left"


        Widget:


# ============================================================
# ROOT
# ============================================================

BoxLayout:

    orientation:
        "vertical"


    SwipeManager:

        id:
            sm


        POSScreen:

            name:
                "pos"


        ProductScreen:

            name:
                "products"


        TransactionScreen:

            name:
                "transactions"


        ReportScreen:

            name:
                "reports"


        SettingsScreen:

            name:
                "settings"


    BoxLayout:

        size_hint_y:
            None

        height:
            dp(68)

        padding:
            dp(5)

        spacing:
            dp(3)


        canvas.before:

            Color:

                rgba:
                    (1,1,1,1)

            Rectangle:

                pos:
                    self.pos

                size:
                    self.size


        NavButton:

            text:
                "▣\nKasir"

            on_release:
                app.navigate("pos")


        NavButton:

            text:
                "▤\nProduk"

            on_release:
                app.navigate("products")


        NavButton:

            text:
                "↻\nRiwayat"

            on_release:
                app.navigate("transactions")


        NavButton:

            text:
                "▥\nLaporan"

            on_release:
                app.navigate("reports")


        NavButton:

            text:
                "⚙\nPengaturan"

            on_release:
                app.navigate("settings")
'''


# ============================================================
# DATABASE
# ============================================================

class DB:

    def __init__(self, path):

        self.path = os.path.abspath(path)

        parent = os.path.dirname(self.path)

        if parent:
            os.makedirs(
                parent,
                exist_ok=True
            )

        self.conn = sqlite3.connect(
            self.path,
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
                INSERT OR IGNORE INTO settings(
                    key,
                    value
                )
                VALUES(?,?)
                """,
                (
                    key,
                    value
                )
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

        if row:
            return row["value"]

        return ""


    def set_setting(self, key, value):

        self.conn.execute(
            """
            INSERT OR REPLACE INTO settings(
                key,
                value
            )
            VALUES(?,?)
            """,
            (
                key,
                str(value)
            )
        )

        self.conn.commit()


    def products(self, search=""):

        if search:

            query = "%" + search.strip() + "%"

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
                (
                    query,
                    query,
                    query
                )
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
                str(name),
                str(sku),
                str(category),
                safe_float(price),
                safe_float(cost),
                safe_float(stock),
                str(image or ""),
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
                    safe_float(subtotal),
                    safe_float(discount),
                    safe_float(tax),
                    safe_float(total),
                    str(method),
                    safe_float(paid),
                    safe_float(change),
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
                    (
                        item["id"],
                    )
                ).fetchone()

                if product is None:

                    raise ValueError(
                        "Produk tidak ditemukan."
                    )

                stock = safe_float(
                    product["stock"]
                )

                qty = safe_float(
                    item["qty"]
                )

                if qty <= 0:

                    raise ValueError(
                        "Jumlah produk tidak valid."
                    )

                if stock < qty:

                    raise ValueError(
                        "Stok produk tidak mencukupi."
                    )

                price = safe_float(
                    item["price"]
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
                    VALUES(?,?,?,?,?,?,?)
                    """.replace(
                        "?,?,?,?,?,?,?",
                        "?,?,?,?,?,?"
                    ),
                    (
                        sale_id,
                        item["id"],
                        str(item["name"]),
                        qty,
                        price,
                        qty * price
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


    def sales(self, limit=100):

        return self.conn.execute(
            """
            SELECT *
            FROM sales
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                int(limit),
            )
        ).fetchall()


# ============================================================
# POS SCREEN
# ============================================================

class POSScreen(Screen):

    def on_enter(self):

        self.app = App.get_running_app()

        if not hasattr(self, "cart_data"):
            self.cart_data = []

        Clock.schedule_once(
            lambda *_: self.refresh_products(),
            0
        )

        Clock.schedule_once(
            lambda *_: self.render_cart_summary(),
            0
        )


    def refresh_products(self, text=""):

        try:

            box = self.ids.products

        except Exception as error:

            self.app.log_error(
                "POS_IDS",
                error
            )

            return

        box.clear_widgets()

        try:
            products = self.app.db.products(text)
        except Exception as error:

            self.app.log_error(
                "POS_PRODUCTS",
                error
            )

            return

        if not products:

            box.add_widget(
                Label(
                    text="Belum ada produk.",
                    color=(.45,.48,.54,1),
                    size_hint_y=None,
                    height=dp(80)
                )
            )

            return

        for product in products:

            card = Card(
                orientation="vertical",
                size_hint_y=None,
                height=dp(190),
                padding=dp(7),
                spacing=dp(4)
            )

            image_path = self.app.resolve_image(
                product["image"]
            )

            if image_path:

                image = Image(
                    source=image_path,
                    size_hint_y=.58,
                    allow_stretch=True,
                    keep_ratio=True
                )

                card.add_widget(image)

                Clock.schedule_once(
                    lambda *_,
                    widget=image:
                    widget.reload(),
                    0.05
                )

            else:

                card.add_widget(
                    Label(
                        text="▣",
                        font_size="32sp",
                        color=(.45,.48,.54,1),
                        size_hint_y=.58
                    )
                )

            info = Label(
                text=(
                    str(product["name"])
                    +
                    "\n"
                    +
                    money(product["price"])
                    +
                    " • stok "
                    +
                    "{:g}".format(
                        safe_float(product["stock"])
                    )
                ),
                color=(.10,.14,.20,1),
                font_size="13sp",
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

            button = Button(
                text="+ Tambah",
                background_normal="",
                background_color=(.12,.32,.78,1),
                color=(1,1,1,1),
                size_hint_y=None,
                height=dp(36),
                bold=True
            )

            button.bind(
                on_release=lambda instance,
                p=product:
                self.add_product(p)
            )

            card.add_widget(button)

            box.add_widget(card)


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
                "name": str(product["name"]),
                "price": safe_float(product["price"]),
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
            safe_float(item["qty"])
            *
            safe_float(item["price"])
            for item in self.cart_data
        )

        if tax_percent is None:

            tax_percent = safe_float(
                self.app.tax_percent
            )

        discount = max(
            0,
            safe_float(discount)
        )

        taxable = max(
            0,
            subtotal - discount
        )

        tax = (
            taxable
            *
            max(
                0,
                safe_float(tax_percent)
            )
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

        if not hasattr(self, "cart_data"):
            return

        try:

            _, _, _, total = self.calculate_total()

            count = sum(
                safe_float(item["qty"])
                for item in self.cart_data
            )

            self.ids.cart_count.text = (
                "{:g} item".format(count)
            )

            self.ids.cart_total.text = money(total)

        except Exception as error:

            if hasattr(self, "app"):
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
            spacing=dp(5),
            size_hint_y=None
        )

        rows.bind(
            minimum_height=rows.setter("height")
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
            text=str(self.app.tax_percent),
            input_filter="float",
            multiline=False,
            size_hint_y=None,
            height=dp(42)
        )

        total_label = Label(
            text="TOTAL Rp 0",
            size_hint_y=None,
            height=dp(36),
            font_size="18sp",
            bold=True,
            color=(.12,.32,.78,1)
        )


        def redraw(*_):

            rows.clear_widgets()

            for index, item in enumerate(
                list(self.cart_data)
            ):

                row = BoxLayout(
                    size_hint_y=None,
                    height=dp(54),
                    spacing=dp(4)
                )

                label = Label(
                    text=(
                        str(item["name"])
                        +
                        "\n"
                        +
                        "{:g}".format(
                            safe_float(item["qty"])
                        )
                        +
                        " x "
                        +
                        money(item["price"])
                    ),
                    halign="left",
                    valign="middle",
                    color=(.10,.14,.20,1)
                )

                label.bind(
                    size=lambda widget, value:
                    setattr(
                        widget,
                        "text_size",
                        value
                    )
                )

                row.add_widget(label)

                minus = Button(
                    text="-",
                    size_hint_x=None,
                    width=dp(40)
                )

                plus = Button(
                    text="+",
                    size_hint_x=None,
                    width=dp(40)
                )

                delete = Button(
                    text="×",
                    size_hint_x=None,
                    width=dp(40)
                )

                minus.bind(
                    on_release=lambda instance,
                    i=index:
                    self.change_qty(
                        i,
                        -1,
                        redraw
                    )
                )

                plus.bind(
                    on_release=lambda instance,
                    i=index:
                    self.change_qty(
                        i,
                        1,
                        redraw
                    )
                )

                delete.bind(
                    on_release=lambda instance,
                    i=index:
                    self.remove_item(
                        i,
                        redraw
                    )
                )

                row.add_widget(minus)
                row.add_widget(plus)
                row.add_widget(delete)

                rows.add_widget(row)

            _, _, _, total = self.calculate_total(
                discount.text,
                tax.text
            )

            total_label.text = (
                "TOTAL  "
                +
                money(total)
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

        clear = Button(
            text="Kosongkan"
        )

        pay = Button(
            text="BAYAR",
            background_normal="",
            background_color=(.12,.32,.78,1),
            color=(1,1,1,1),
            bold=True
        )

        buttons.add_widget(clear)
        buttons.add_widget(pay)

        content.add_widget(buttons)

        popup = Popup(
            title="Keranjang",
            content=content,
            size_hint=(.94,.86)
        )


        def clear_cart_action(*_):

            self.clear_cart()

            popup.dismiss()


        def payment_action(*_):

            current_discount = discount.text
            current_tax = tax.text

            popup.dismiss()

            Clock.schedule_once(
                lambda *_:
                self.open_payment_popup(
                    current_discount,
                    current_tax
                ),
                0.05
            )


        clear.bind(
            on_release=clear_cart_action
        )

        pay.bind(
            on_release=payment_action
        )

        popup.open()

        redraw()


    def change_qty(
        self,
        index,
        delta,
        callback=None
    ):

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

        self.render_cart_summary()

        if callback:
            callback()


    def remove_item(
        self,
        index,
        callback=None
    ):

        if (
            0 <= index < len(self.cart_data)
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
            spacing=dp(8),
            padding=dp(12)
        )

        content.add_widget(
            Label(
                text=(
                    "TOTAL\n"
                    +
                    money(total)
                ),
                font_size="22sp",
                bold=True,
                color=(.12,.32,.78,1),
                size_hint_y=None,
                height=dp(70)
            )
        )

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
            height=dp(44)
        )

        change = Label(
            text="Kembalian  Rp 0",
            font_size="16sp",
            bold=True,
            size_hint_y=None,
            height=dp(40),
            color=(.08,.55,.30,1)
        )

        content.add_widget(method)
        content.add_widget(paid)
        content.add_widget(change)


        def update_payment(*_):

            if method.text == "Tunai":

                paid.disabled = False

                value = max(
                    0,
                    safe_float(paid.text) - total
                )

                change.text = (
                    "Kembalian  "
                    +
                    money(value)
                )

            else:

                paid.text = ""

                paid.disabled = True

                change.text = (
                    "Pembayaran non-tunai"
                )


        paid.bind(
            text=update_payment
        )

        method.bind(
            text=update_payment
        )

        buttons = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(7)
        )

        cancel = Button(
            text="Batal"
        )

        done = Button(
            text="SELESAIKAN",
            background_normal="",
            background_color=(.12,.32,.78,1),
            color=(1,1,1,1),
            bold=True
        )

        buttons.add_widget(cancel)
        buttons.add_widget(done)

        content.add_widget(buttons)

        popup = Popup(
            title="Pembayaran",
            content=content,
            size_hint=(.92,.68)
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

            cart_snapshot = [
                dict(item)
                for item in self.cart_data
            ]

            try:

                invoice = self.app.db.create_sale(
                    cart_snapshot,
                    subtotal,
                    discount_value,
                    tax_value,
                    total,
                    method.text,
                    paid_value,
                    change_value
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

                self.app.navigate(
                    "transactions"
                )

                self.app.notify(
                    "Transaksi "
                    +
                    invoice
                    +
                    " berhasil."
                )

                Clock.schedule_once(
                    lambda *_:
                    self.app.print_or_offer(
                        invoice
                    ),
                    0.15
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

        update_payment()


    def clear_cart(self):

        self.cart_data = []

        self.render_cart_summary()


# ============================================================
# PRODUCT SCREEN
# ============================================================

class ProductScreen(Screen):

    def on_enter(self):

        self.app = App.get_running_app()

        Clock.schedule_once(
            lambda *_: self.refresh(),
            0
        )


    def refresh(self, search=""):

        try:
            box = self.ids.list
        except Exception as error:

            self.app.log_error(
                "PRODUCT_IDS",
                error
            )

            return

        box.clear_widgets()

        try:
            products = self.app.db.products(search)
        except Exception as error:

            self.app.log_error(
                "PRODUCT_LIST",
                error
            )

            return

        if not products:

            box.add_widget(
                Label(
                    text="Belum ada produk.",
                    color=(.45,.48,.54,1),
                    size_hint_y=None,
                    height=dp(80)
                )
            )

            return

        for product in products:

            row = Card(
                size_hint_y=None,
                height=dp(82),
                spacing=dp(8),
                padding=dp(6)
            )

            image_path = self.app.resolve_image(
                product["image"]
            )

            if image_path:

                image = Image(
                    source=image_path,
                    size_hint_x=.20,
                    allow_stretch=True,
                    keep_ratio=True
                )

                row.add_widget(image)

                Clock.schedule_once(
                    lambda *_,
                    widget=image:
                    widget.reload(),
                    0.05
                )

            else:

                row.add_widget(
                    Label(
                        text="▣",
                        size_hint_x=.20,
                        font_size="26sp",
                        color=(.45,.48,.54,1)
                    )
                )

            info = Label(
                text=(
                    str(product["name"])
                    +
                    "\n"
                    +
                    money(product["price"])
                    +
                    " • stok "
                    +
                    "{:g}".format(
                        safe_float(product["stock"])
                    )
                    +
                    "\n"
                    +
                    (
                        str(product["category"])
                        if product["category"]
                        else
                        "Tanpa kategori"
                    )
                ),
                color=(.10,.14,.20,1),
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

            box.add_widget(row)


    def open_editor(self):

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(7),
            padding=dp(10)
        )

        preview = Image(
            source="",
            size_hint_y=None,
            height=dp(150),
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

        buttons = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(7)
        )

        cancel = Button(
            text="Batal"
        )

        save = Button(
            text="Simpan",
            background_normal="",
            background_color=(.12,.32,.78,1),
            color=(1,1,1,1),
            bold=True
        )

        buttons.add_widget(cancel)
        buttons.add_widget(save)

        content.add_widget(buttons)

        popup = Popup(
            title="Tambah Produk",
            content=content,
            size_hint=(.94,.90)
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

                self.app.db.add_product(
                    name,
                    fields["sku"].text.strip(),
                    fields["category"].text.strip(),
                    safe_float(fields["price"].text),
                    safe_float(fields["cost"].text),
                    safe_float(fields["stock"].text),
                    image_path
                )

                popup.dismiss()

                self.refresh()

                self.app.notify(
                    "Produk berhasil ditambahkan."
                )

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

        Clock.schedule_once(
            lambda *_: self.refresh(),
            0
        )


    def refresh(self):

        try:
            box = self.ids.list
        except Exception as error:

            self.app.log_error(
                "TRANSACTION_IDS",
                error
            )

            return

        box.clear_widgets()

        try:
            sales = self.app.db.sales()
        except Exception as error:

            self.app.log_error(
                "TRANSACTION_LIST",
                error
            )

            return

        if not sales:

            box.add_widget(
                Label(
                    text="Belum ada transaksi.",
                    color=(.45,.48,.54,1),
                    size_hint_y=None,
                    height=dp(80)
                )
            )

            return

        for sale in sales:

            row = Card(
                size_hint_y=None,
                height=dp(76),
                padding=dp(10)
            )

            left = Label(
                text=(
                    str(sale["invoice"])
                    +
                    "\n"
                    +
                    str(sale["created_at"])
                    +
                    " • "
                    +
                    str(sale["payment_method"])
                ),
                color=(.10,.14,.20,1),
                halign="left",
                valign="middle"
            )

            left.bind(
                size=lambda widget, value:
                setattr(
                    widget,
                    "text_size",
                    value
                )
            )

            row.add_widget(left)

            row.add_widget(
                Label(
                    text=money(sale["total"]),
                    color=(.12,.32,.78,1),
                    bold=True,
                    size_hint_x=.32
                )
            )

            box.add_widget(row)


# ============================================================
# REPORT
# ============================================================

class ReportScreen(Screen):

    def on_enter(self):

        self.app = App.get_running_app()

        Clock.schedule_once(
            lambda *_: self.refresh(),
            0
        )


    def refresh(self):

        try:

            rows = self.app.db.conn.execute(
                """
                SELECT
                    COUNT(*) AS n,
                    COALESCE(SUM(subtotal),0) AS subtotal,
                    COALESCE(SUM(discount),0) AS discount,
                    COALESCE(SUM(tax),0) AS tax,
                    COALESCE(SUM(total),0) AS total
                FROM sales
                WHERE date(created_at)=date('now')
                """
            ).fetchone()

            self.ids.summary.text = (
                "HARI INI\n\n"
                +
                "Transaksi : "
                +
                str(rows["n"])
                +
                "\n"
                +
                "Subtotal  : "
                +
                money(rows["subtotal"])
                +
                "\n"
                +
                "Diskon    : "
                +
                money(rows["discount"])
                +
                "\n"
                +
                "Pajak     : "
                +
                money(rows["tax"])
                +
                "\n"
                +
                "Penjualan : "
                +
                money(rows["total"])
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

                for sale in self.app.db.sales(10000):

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
                "CSV tersimpan:\n"
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
                self.app.db.setting(
                    "paper"
                )
                or
                "58mm"
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
                "paper",
                self.ids.paper.text
            )

            self.app.tax_percent = (
                self.app.db.setting(
                    "tax_percent"
                )
                or
                "0"
            )

            self.app.notify(
                "Pengaturan disimpan."
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
                "Backup dibuat:\n"
                +
                target
            )

        except Exception as error:

            self.app.log_error(
                "DATABASE_BACKUP",
                error
            )


# ============================================================
# MAIN APP
# ============================================================

class UniversalPOS(App):

    tax_percent = StringProperty("0")

    last_receipt = None

    pending_image = None

    activity_callback_bound = False


    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.startup_error = None

        self.db = None

        self.images_dir = None


    # ========================================================
    # ERROR LOG
    # ========================================================

    def log_error(
        self,
        location,
        error
    ):

        try:

            data_dir = (
                getattr(
                    self,
                    "user_data_dir",
                    ""
                )
                or
                os.path.join(
                    os.path.expanduser("~"),
                    ".kasirqu"
                )
            )

            os.makedirs(
                data_dir,
                exist_ok=True
            )

            error_path = os.path.join(
                data_dir,
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
            "KASIRQU ERROR ["
            +
            str(location)
            +
            "]:",
            repr(error)
        )


    # ========================================================
    # BUILD
    # ========================================================

    def build(self):

        try:

            data_dir = (
                self.user_data_dir
                or
                os.path.join(
                    os.path.expanduser("~"),
                    ".kasirqu"
                )
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

            return self.build_error_screen(
                error
            )


    # ========================================================
    # ERROR SCREEN
    # ========================================================

    def build_error_screen(self, error):

        root = BoxLayout(
            orientation="vertical",
            padding=dp(24),
            spacing=dp(14)
        )

        with root.canvas.before:

            Color(
                .96,
                .97,
                .99,
                1
            )

            root._background = RoundedRectangle(
                pos=root.pos,
                size=root.size
            )

        root.bind(
            pos=lambda widget, value:
            setattr(
                widget._background,
                "pos",
                value
            ),
            size=lambda widget, value:
            setattr(
                widget._background,
                "size",
                value
            )
        )

        root.add_widget(
            Label(
                text="KasirQU",
                font_size="26sp",
                bold=True,
                size_hint_y=None,
                height=dp(54),
                color=(.07,.09,.13,1)
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
                "Detail error tersimpan di:\n"
                "KasirQU_error.log"
            ),
            halign="center",
            valign="middle",
            color=(.10,.14,.20,1)
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


    # ========================================================
    # START
    # ========================================================

    def on_start(self):

        Clock.schedule_once(
            self.finish_startup,
            0.5
        )


    def finish_startup(self, *_):

        try:

            if self.startup_error is not None:
                return

            if self.root is None:

                raise RuntimeError(
                    "Root aplikasi tidak tersedia."
                )

            try:

                screen_manager = (
                    self.root.ids.sm
                )

            except Exception:

                screen_manager = None

            if screen_manager is None:

                raise RuntimeError(
                    "ScreenManager tidak ditemukan."
                )

            pos = screen_manager.get_screen(
                "pos"
            )

            if hasattr(
                pos,
                "refresh_products"
            ):

                pos.refresh_products()

        except Exception as error:

            self.log_error(
                "FIRST_UI",
                error
            )

            self.startup_error = error

        finally:

            self.hide_android_loading_screen()


    def hide_android_loading_screen(self):

        if platform != "android":
            return

        try:

            from android import loadingscreen

            if hasattr(
                loadingscreen,
                "hide_loading_screen"
            ):

                loadingscreen.hide_loading_screen()

        except Exception as error:

            self.log_error(
                "LOADING_SCREEN",
                error
            )


    # ========================================================
    # NAVIGATION
    # ========================================================

    def navigate(self, name):

        try:

            if self.root is None:
                return

            screen_manager = (
                self.root.ids.sm
            )

            names = list(
                screen_manager.screen_names
            )

            if name not in names:
                return

            if screen_manager.current == name:
                return

            current_index = names.index(
                screen_manager.current
            )

            target_index = names.index(
                name
            )

            screen_manager.transition = (
                SlideTransition(
                    direction=(
                        "left"
                        if target_index > current_index
                        else "right"
                    ),
                    duration=0.18
                )
            )

            screen_manager.current = name

        except Exception as error:

            self.log_error(
                "NAVIGATION",
                error
            )


    # ========================================================
    # NOTIFICATION
    # ========================================================

    def notify(self, message):

        try:

            label = Label(
                text=str(message),
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

            popup = Popup(
                title=APP_NAME,
                content=label,
                size_hint=(.86,.32)
            )

            popup.open()

        except Exception as error:

            self.log_error(
                "NOTIFY",
                error
            )


    # ========================================================
    # IMAGE PATH
    # ========================================================

    def resolve_image(self, path):

        if not path:
            return ""

        try:

            path = str(path).strip()

            if not path:
                return ""

            if path.startswith(
                "file://"
            ):

                path = path[7:]

            path = os.path.abspath(path)

            if os.path.isfile(path):

                return path

            return ""

        except Exception as error:

            self.log_error(
                "RESOLVE_IMAGE",
                error
            )

            return ""


    # ========================================================
    # ANDROID IMAGE PICKER
    # ========================================================

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

            self.pending_image = (
                selected,
                preview
            )

            if not self.activity_callback_bound:

                bind(
                    on_activity_result=
                    self.on_activity_result
                )

                self.activity_callback_bound = True

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


    # ========================================================
    # ACTIVITY RESULT
    # ========================================================

    def on_activity_result(
        self,
        request_code,
        result_code,
        intent
    ):

        try:

            if request_code != 9001:
                return

            if intent is None:
                return

            uri = intent.getData()

            if uri is None:
                return

            copied = self.copy_content_uri(
                uri
            )

            if not copied:

                self.notify(
                    "Foto tidak dapat dibaca."
                )

                return

            if self.pending_image is None:
                return

            selected, preview = (
                self.pending_image
            )

            selected["path"] = copied

            preview.source = copied

            preview.reload()

            Clock.schedule_once(
                lambda *_:
                preview.reload(),
                0.2
            )

        except Exception as error:

            self.log_error(
                "ACTIVITY_RESULT_IMAGE",
                error
            )

            self.notify(
                "Gagal memuat foto."
            )

        finally:

            self.pending_image = None


    # ========================================================
    # COPY CONTENT URI
    # ========================================================

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
                PythonActivity.mActivity
                .getContentResolver()
            )

            input_stream = (
                resolver.openInputStream(uri)
            )

            if input_stream is None:

                raise RuntimeError(
                    "InputStream foto tidak tersedia."
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
                "image/gif": ".gif"
            }

            extension = (
                extension_map.get(
                    mime,
                    ".jpg"
                )
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

            FileOutputStream = autoclass(
                "java.io.FileOutputStream"
            )

            output_stream = (
                FileOutputStream(
                    target
                )
            )

            buffer = jarray(
                "b",
                [0] * 8192
            )

            while True:

                count = input_stream.read(
                    buffer
                )

                if count <= 0:
                    break

                output_stream.write(
                    buffer,
                    0,
                    count
                )

            output_stream.flush()

            try:
                output_stream.close()
            except Exception:
                pass

            output_stream = None

            try:
                input_stream.close()
            except Exception:
                pass

            input_stream = None

            if os.path.isfile(target):

                if os.path.getsize(target) > 0:

                    return os.path.abspath(
                        target
                    )

            raise RuntimeError(
                "File foto kosong."
            )

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


    # ========================================================
    # DESKTOP IMAGE PICKER
    # ========================================================

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
                    "*.webp"
                ]
            )

            buttons = BoxLayout(
                size_hint_y=None,
                height=dp(46)
            )

            select_button = Button(
                text="Pilih"
            )

            cancel_button = Button(
                text="Batal"
            )

            buttons.add_widget(
                cancel_button
            )

            buttons.add_widget(
                select_button
            )

            container = BoxLayout(
                orientation="vertical"
            )

            container.add_widget(chooser)
            container.add_widget(buttons)

            popup = Popup(
                title="Pilih Foto Produk",
                content=container,
                size_hint=(.92,.88)
            )


            def select_file(*_):

                if not chooser.selection:
                    return

                path = chooser.selection[0]

                if not os.path.isfile(path):
                    return

                selected["path"] = (
                    os.path.abspath(path)
                )

                preview.source = (
                    selected["path"]
                )

                preview.reload()

                popup.dismiss()


            select_button.bind(
                on_release=select_file
            )

            cancel_button.bind(
                on_release=popup.dismiss
            )

            popup.open()

        except Exception as error:

            self.log_error(
                "DESKTOP_IMAGE_PICKER",
                error
            )


    # ========================================================
    # SAVE IMAGE
    # ========================================================

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

            if source.startswith(
                images_dir + os.sep
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
                ".webp"
            ):

                extension = ".jpg"

            filename = (
                "product_"
                +
                datetime.now().strftime(
                    "%Y%m%d%H%M%S%f"
                )
                +
                extension
            )

            destination = os.path.join(
                images_dir,
                filename
            )

            shutil.copy2(
                source,
                destination
            )

            if not os.path.isfile(
                destination
            ):

                return ""

            if os.path.getsize(
                destination
            ) <= 0:

                return ""

            return os.path.abspath(
                destination
            )

        except Exception as error:

            self.log_error(
                "SAVE_SELECTED_IMAGE",
                error
            )

            return ""


    # ========================================================
    # PRINT OFFER
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
                    "Transaksi "
                    +
                    str(invoice)
                    +
                    " berhasil.\n"
                    "Cetak struk sekarang?"
                ),
                halign="center",
                valign="middle"
            )
        )

        buttons = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(7)
        )

        bluetooth = Button(
            text="Bluetooth"
        )

        no_print = Button(
            text="Tidak"
        )

        buttons.add_widget(bluetooth)
        buttons.add_widget(no_print)

        content.add_widget(buttons)

        popup = Popup(
            title="Struk",
            content=content,
            size_hint=(.88,.38)
        )


        bluetooth.bind(
            on_release=lambda *_:
            self.bluetooth_action(
                popup
            )
        )

        no_print.bind(
            on_release=popup.dismiss
        )

        popup.open()


    def bluetooth_action(self, popup):

        popup.dismiss()

        Clock.schedule_once(
            lambda *_:
            self.bluetooth_printer_dialog(),
            0.05
        )


    # ========================================================
    # BLUETOOTH
    # ========================================================

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
            size_hint=(.92,.80)
        )

        for name, address in devices:

            button = Button(
                text=(
                    str(name)
                    +
                    "\n"
                    +
                    str(address)
                ),
                size_hint_y=None,
                height=dp(58)
            )

            button.bind(
                on_release=lambda instance,
                addr=address:
                self.select_bluetooth_printer(
                    popup,
                    addr
                )
            )

            content.add_widget(button)

        popup.open()


    def select_bluetooth_printer(
        self,
        popup,
        address
    ):

        popup.dismiss()

        Clock.schedule_once(
            lambda *_:
            self.print_bluetooth(address),
            0.05
        )


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
                    continue

            return result

        except Exception as error:

            self.log_error(
                "BLUETOOTH_DEVICES",
                error
            )

            return []


    def print_bluetooth(self, address):

        if not self.last_receipt:

            self.notify(
                "Data struk tidak tersedia."
            )

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
                    str(address)
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

            output = socket.getOutputStream()

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
            else
            48
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
            str(store).center(width),
            str(address).center(width),
            "-" * width,
            str(invoice),
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
                "{:g}".format(
                    safe_float(item["qty"])
                )
                +
                " x "
                +
                money(item["price"])
                +
                " = "
                +
                money(
                    safe_float(item["qty"])
                    *
                    safe_float(item["price"])
                )
            )

        lines.extend(
            [
                "-" * width,
                "Subtotal : " + money(subtotal),
                "Diskon   : " + money(discount),
                "Pajak    : " + money(tax),
                "TOTAL    : " + money(total),
                "Bayar    : " + money(paid),
                "Kembali  : " + money(change),
                "Metode   : " + str(method),
                "-" * width,
                str(footer).center(width),
                ""
            ]
        )

        text = "\n".join(lines)

        init = b"\x1b\x40"

        bold_on = b"\x1b\x45\x01"

        bold_off = b"\x1b\x45\x00"

        cut = b"\x1d\x56\x00"

        return (
            init
            +
            bold_on
            +
            text.encode(
                "utf-8",
                "replace"
            )
            +
            bold_off
            +
            b"\n\n\n"
            +
            cut
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    UniversalPOS().run()
