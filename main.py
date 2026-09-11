import os
import unicodedata
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
# KASIRQU 2.0 - PROFESSIONAL POS
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


def printer_text(value):
    """Normalisasi teks untuk printer ESC/POS."""
    try:
        text = safe_text(value)
        replacements = {
            "×": "x",
            "•": "-",
            "…": "...",
            "–": "-",
            "—": "-",
            "“": '"',
            "”": '"',
            "‘": "'",
            "’": "'",
            "Rp.": "Rp",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = unicodedata.normalize("NFKD", text)
        text = text.encode("ascii", "ignore").decode("ascii")
        return text
    except Exception:
        return ""


# ============================================================
# CARD & CUSTOM UI COMPONENTS
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
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


class ModernButton(Button):
    def __init__(self, primary=False, **kwargs):
        self.primary = primary
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = PRIMARY if primary else WHITE
        self.color = WHITE if primary else TEXT
        self.bold = True
        self.size_hint_y = None
        if "height" not in kwargs:
            self.height = dp(44)


class IconNavButton(ButtonBehavior, BoxLayout):
    nav_name = StringProperty("")
    label_text = StringProperty("")
    icon_path = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(2), **kwargs)
        self.size_hint_y = None
        self.height = dp(78)
        self.padding = [dp(3), dp(3), dp(3), dp(3)]
        self.size_hint_x = 1

        self.icon = Image(
            source=self.icon_path,
            size_hint=(1, None),
            height=dp(46),
            allow_stretch=True,
            keep_ratio=True
        )

        self.label = Label(
            text=self.label_text,
            font_size="10sp",
            bold=True,
            color=MUTED,
            size_hint=(1, None),
            height=dp(22),
            halign="center",
            valign="middle"
        )
        self.label.bind(size=lambda w, v: setattr(w, "text_size", v))

        self.add_widget(self.icon)
        self.add_widget(self.label)

        with self.canvas.before:
            Color(1, 1, 1, 1)
            self._nav_bg = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(10)]
            )

        self.bind(pos=self._update_bg, size=self._update_bg)
        self.bind(label_text=self._sync_label_text, icon_path=self._sync_icon)
        Clock.schedule_once(self._sync_widgets, 0)

    def _sync_label_text(self, *_):
        if hasattr(self, "label"):
            self.label.text = self.label_text

    def _sync_icon(self, *_):
        if hasattr(self, "icon"):
            self.icon.source = self.icon_path
            self.icon.reload()

    def _sync_widgets(self, *_):
        self._sync_label_text()
        self._sync_icon()
        self._update_bg()

    def _update_bg(self, *_):
        self._nav_bg.pos = self.pos
        self._nav_bg.size = self.size

    def on_release(self):
        App.get_running_app().navigate(self.nav_name)


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
            if abs(dx) > dp(70) and abs(dx) > abs(dy) * 1.3:
                self.swipe(-1 if dx > 0 else 1)
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
            direction=("right" if delta < 0 else "left"),
            duration=.20
        )
        self.current = names[target]


# ============================================================
# KV LANGUAGE SCHEME
# ============================================================

KV = r'''
#:import dp kivy.metrics.dp

<PrimaryButton@Button>:
    background_normal: ""
    background_down: ""
    background_color: (.08,.24,.62,1) if self.state == "down" else (.12,.32,.78,1)
    color: 1,1,1,1
    bold: True
    font_size: "14sp"
    size_hint_y: None
    height: dp(46)

<SoftButton@Button>:
    background_normal: ""
    background_down: ""
    background_color: (.88,.91,.96,1) if self.state == "down" else (1,1,1,1)
    color: (.08,.11,.16,1)
    bold: True
    font_size: "13sp"
    size_hint_y: None
    height: dp(44)

<ScreenTitle@Label>:
    color: (.07,.09,.13,1)
    font_size: "22sp"
    bold: True
    halign: "center"
    valign: "middle"
    text_size: self.size

<NavButton@Button>:
    background_normal: ""
    background_down: ""
    background_color: (.12,.32,.78,1) if self.state == "down" else (1,1,1,1)
    color: (1,1,1,1) if self.state == "down" else (.25,.29,.36,1)
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

        Label:
            text: "KasirQU"
            color: (.07,.09,.13,1)
            font_size: "24sp"
            bold: True
            size_hint_y: None
            height: dp(42)
            halign: "center"
            valign: "middle"
            text_size: self.size

        BoxLayout:
            size_hint_y: None
            height: dp(48)
            padding: [dp(24), 0, dp(24), 0]
            BoxLayout:
                spacing: dp(7)
                TextInput:
                    id: search
                    hint_text: "Cari produk / scan barcode..."
                    multiline: False
                    padding: [dp(12), dp(11)]
                    background_normal: ""
                    background_color: (1,1,1,1)
                    foreground_color: (.08,.11,.16,1)
                    cursor_color: (.12,.32,.78,1)
                    on_text: root.refresh_products(self.text)
                    on_text_validate: root.quick_add_by_code(self.text)
                PrimaryButton:
                    text: "SCAN"
                    size_hint_x: None
                    width: dp(72)
                    on_release: root.open_scanner()

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
                cols: 4
                spacing: dp(8)
                padding: dp(2)
                size_hint_x: 1
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
            PrimaryButton:
                text: "KERANJANG"
                size_hint_x: .33
                on_release: root.open_cart_popup()

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
        ScreenTitle:
            text: "Produk"
            size_hint_y: None
            height: dp(48)
        BoxLayout:
            size_hint_y: None
            height: dp(46)
            spacing: dp(8)
            TextInput:
                id: search
                hint_text: "Cari nama, SKU, kategori..."
                multiline: False
                size_hint_x: 1
                padding: [dp(12), dp(10)]
                background_normal: ""
                background_color: (1,1,1,1)
                foreground_color: (.08,.11,.16,1)
                cursor_color: (.12,.32,.78,1)
                on_text: root.refresh(self.text)
            PrimaryButton:
                text: "+ PRODUK"
                size_hint_x: None
                width: dp(112)
                on_release: root.open_editor()
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
            height: dp(370)
            BoxLayout:
                id: summary
                orientation: "vertical"
                spacing: dp(3)
                size_hint_y: 1
        BoxLayout:
            size_hint_y: None
            height: dp(46)
            spacing: dp(8)
            PrimaryButton:
                text: "EXPORT PENJUALAN"
                on_release: root.export_csv()
            SoftButton:
                text: "EXPORT STOK"
                on_release: root.export_stock_csv()
        Widget:

<SettingsScreen>:
    BoxLayout:
        orientation: "vertical"
        padding: dp(12)
        spacing: dp(8)
        canvas.before:
            Color:
                rgba: (.95,.97,.99,1)
            Rectangle:
                pos: self.pos
                size: self.size
        ScreenTitle:
            text: "Pengaturan"
            size_hint_y: None
            height: dp(48)
        ScrollView:
            do_scroll_x: False
            bar_width: dp(3)
            BoxLayout:
                orientation: "vertical"
                spacing: dp(10)
                padding: [dp(2), 0, dp(5), dp(12)]
                size_hint_y: None
                height: self.minimum_height

                Card:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(360)
                    padding: dp(12)
                    spacing: dp(8)
                    Label:
                        text: "TOKO & STRUK"
                        color: (.40,.44,.51,1)
                        bold: True
                        font_size: "13sp"
                        size_hint_y: None
                        height: dp(24)
                        halign: "left"
                        text_size: self.size
                    TextInput:
                        id: store
                        hint_text: "Nama usaha"
                        multiline: False
                        size_hint_y: None
                        height: dp(44)
                        padding: [dp(12),dp(10)]
                        background_normal: ""
                        background_color: (1,1,1,1)
                        foreground_color: (.08,.11,.16,1)
                    TextInput:
                        id: address
                        hint_text: "Alamat / kontak"
                        multiline: False
                        size_hint_y: None
                        height: dp(44)
                        padding: [dp(12),dp(10)]
                        background_normal: ""
                        background_color: (1,1,1,1)
                        foreground_color: (.08,.11,.16,1)
                    TextInput:
                        id: footer
                        hint_text: "Footer struk"
                        multiline: False
                        size_hint_y: None
                        height: dp(44)
                        padding: [dp(12),dp(10)]
                        background_normal: ""
                        background_color: (1,1,1,1)
                        foreground_color: (.08,.11,.16,1)
                    BoxLayout:
                        size_hint_y: None
                        height: dp(104)
                        spacing: dp(10)
                        Card:
                            size_hint_x: None
                            width: dp(94)
                            padding: dp(6)
                            Image:
                                id: receipt_logo_preview
                                source: ""
                                allow_stretch: True
                                keep_ratio: True
                        BoxLayout:
                            orientation: "vertical"
                            spacing: dp(5)
                            Label:
                                id: logo_status
                                text: "Logo struk: belum dipilih"
                                color: (.25,.29,.36,1)
                                font_size: "11sp"
                                halign: "left"
                                valign: "middle"
                                text_size: self.size
                            BoxLayout:
                                size_hint_y: None
                                height: dp(40)
                                spacing: dp(6)
                                SoftButton:
                                    text: "PILIH LOGO"
                                    on_release: root.choose_receipt_logo()
                                SoftButton:
                                    text: "HAPUS"
                                    on_release: root.remove_receipt_logo()

                Card:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(310)
                    padding: dp(12)
                    spacing: dp(8)
                    Label:
                        text: "OPERASIONAL"
                        color: (.40,.44,.51,1)
                        bold: True
                        font_size: "13sp"
                        size_hint_y: None
                        height: dp(24)
                        halign: "left"
                        text_size: self.size
                    TextInput:
                        id: cashier
                        hint_text: "Nama kasir"
                        multiline: False
                        size_hint_y: None
                        height: dp(44)
                        padding: [dp(12),dp(10)]
                        background_normal: ""
                        background_color: (1,1,1,1)
                    Spinner:
                        id: role
                        text: "Owner"
                        values: ["Owner","Admin","Kasir"]
                        size_hint_y: None
                        height: dp(44)
                    BoxLayout:
                        size_hint_y: None
                        height: dp(44)
                        spacing: dp(8)
                        TextInput:
                            id: tax
                            hint_text: "Pajak (%)"
                            input_filter: "float"
                            multiline: False
                            padding: [dp(12),dp(10)]
                            background_normal: ""
                            background_color: (1,1,1,1)
                        TextInput:
                            id: low_stock
                            hint_text: "Batas stok menipis"
                            input_filter: "float"
                            multiline: False
                            padding: [dp(12),dp(10)]
                            background_normal: ""
                            background_color: (1,1,1,1)
                    BoxLayout:
                        size_hint_y: None
                        height: dp(44)
                        spacing: dp(8)
                        Label:
                            text: "Ukuran kertas"
                            color: (.25,.29,.36,1)
                            halign: "left"
                            valign: "middle"
                            text_size: self.size
                        Spinner:
                            id: paper
                            text: "58mm"
                            values: ["58mm","80mm"]
                            size_hint_x: None
                            width: dp(130)
                    PrimaryButton:
                        text: "SIMPAN PENGATURAN"
                        on_release: root.save()

                Card:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(238)
                    padding: dp(12)
                    spacing: dp(8)
                    Label:
                        text: "PRINTER THERMAL"
                        color: (.40,.44,.51,1)
                        bold: True
                        font_size: "13sp"
                        size_hint_y: None
                        height: dp(24)
                        halign: "left"
                        text_size: self.size
                    Label:
                        id: printer_status
                        text: "Printer: belum dipilih"
                        color: (.08,.11,.16,1)
                        size_hint_y: None
                        height: dp(40)
                        halign: "center"
                        valign: "middle"
                        text_size: self.size
                    PrimaryButton:
                        text: "PILIH PRINTER BLUETOOTH"
                        on_release: root.open_printer()
                    SoftButton:
                        text: "TEST PRINT"
                        on_release: root.test_printer()
                    Label:
                        text: "Printer dipilih satu kali di sini dan digunakan kembali untuk transaksi serta cetak ulang."
                        color: (.40,.44,.51,1)
                        font_size: "11sp"
                        size_hint_y: None
                        height: dp(42)
                        halign: "center"
                        valign: "middle"
                        text_size: self.width, None

                Card:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(250)
                    padding: dp(12)
                    spacing: dp(7)
                    Label:
                        text: "DATA & KEAMANAN"
                        color: (.40,.44,.51,1)
                        bold: True
                        font_size: "13sp"
                        size_hint_y: None
                        height: dp(24)
                        halign: "left"
                        text_size: self.size
                    SoftButton:
                        text: "BACKUP DATABASE"
                        on_release: root.backup()
                    SoftButton:
                        text: "RESTORE BACKUP TERAKHIR"
                        on_release: root.restore_backup()
                    SoftButton:
                        text: "CEK DATABASE"
                        on_release: root.check_database()
                    SoftButton:
                        text: "REFRESH DATA"
                        on_release: root.on_enter()

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
        height: dp(88)
        padding: dp(5)
        spacing: dp(3)
        canvas.before:
            Color:
                rgba: (1,1,1,1)
            Rectangle:
                pos: self.pos
                size: self.size
        IconNavButton:
            nav_name: "pos"
            label_text: "Kasir"
            icon_path: app.asset_path("assets/icons/kasir.png")
        IconNavButton:
            nav_name: "products"
            label_text: "Produk"
            icon_path: app.asset_path("assets/icons/produk.png")
        IconNavButton:
            nav_name: "transactions"
            label_text: "Riwayat"
            icon_path: app.asset_path("assets/icons/riwayat.png")
        IconNavButton:
            nav_name: "reports"
            label_text: "Laporan"
            icon_path: app.asset_path("assets/icons/laporan.png")
        IconNavButton:
            nav_name: "settings"
            label_text: "Pengaturan"
            icon_path: app.asset_path("assets/icons/pengaturan.png")
'''


# ============================================================
# DATABASE ENGINE
# ============================================================

class DB:
    def __init__(self, path):
        self.path = path
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False, timeout=15)
        self.conn.row_factory = sqlite3.Row
        try:
            self.conn.execute("PRAGMA foreign_keys=ON")
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
        except Exception:
            pass
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

            CREATE TABLE IF NOT EXISTS stock_movements(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                qty REAL NOT NULL DEFAULT 0,
                movement_type TEXT NOT NULL DEFAULT 'ADJUSTMENT',
                note TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS app_users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'Kasir',
                pin TEXT DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1
            );
            """
        )

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

        sales_columns = {row[1] for row in cursor.execute("PRAGMA table_info(sales)").fetchall()}
        sales_migrations = {
            "voided": "ALTER TABLE sales ADD COLUMN voided INTEGER NOT NULL DEFAULT 0",
            "void_reason": "ALTER TABLE sales ADD COLUMN void_reason TEXT DEFAULT ''",
            "cashier": "ALTER TABLE sales ADD COLUMN cashier TEXT DEFAULT ''",
            "role": "ALTER TABLE sales ADD COLUMN role TEXT DEFAULT ''",
        }
        for name, sql in sales_migrations.items():
            if name not in sales_columns:
                cursor.execute(sql)

        defaults = {
            "store_name": "KasirQU",
            "store_address": "Alamat / Kontak",
            "receipt_footer": "Terima kasih telah berbelanja",
            "paper": "58mm",
            "tax_percent": "0",
            "low_stock_threshold": "5",
            "cashier_name": "Kasir",
            "user_role": "Owner",
            "receipt_header": "",
            "auto_backup": "1",
            "product_columns": "4",
            "printer_address": "",
            "receipt_logo": ""
        }

        for key, value in defaults.items():
            cursor.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (key, value))

        self.conn.commit()

    def setting(self, key):
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else ""

    def set_setting(self, key, value):
        self.conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, str(value)))
        self.conn.commit()

    def products(self, search=""):
        if search:
            q = "%" + search.strip() + "%"
            return self.conn.execute(
                "SELECT * FROM products WHERE active=1 AND (name LIKE ? OR sku LIKE ? OR category LIKE ?) ORDER BY name COLLATE NOCASE",
                (q, q, q)
            ).fetchall()
        return self.conn.execute("SELECT * FROM products WHERE active=1 ORDER BY name COLLATE NOCASE").fetchall()

    def add_product(self, name, sku, category, price, cost, stock, image=""):
        self.conn.execute(
            """INSERT INTO products(name, sku, category, price, cost, stock, image, created_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            (name, sku, category, float(price), float(cost), float(stock), image, datetime.now().isoformat(timespec="seconds"))
        )
        self.conn.commit()

    def create_sale(self, cart, subtotal, discount, tax, total, method, paid, change):
        invoice = "INV-" + datetime.now().strftime("%Y%m%d%H%M%S%f")
        now = datetime.now().isoformat(timespec="seconds")
        cursor = self.conn.cursor()

        try:
            self.conn.execute("BEGIN")
            cursor.execute(
                """INSERT INTO sales(invoice, subtotal, discount, tax, total, payment_method, paid, change_amount, created_at, cashier, role)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (invoice, subtotal, discount, tax, total, method, paid, change, now, self.setting("cashier_name") or "Kasir", self.setting("user_role") or "Owner")
            )
            sale_id = cursor.lastrowid

            for item in cart:
                product = cursor.execute("SELECT stock FROM products WHERE id=? AND active=1", (item["id"],)).fetchone()
                if not product:
                    raise ValueError("Produk tidak ditemukan.")
                stock = float(product["stock"])
                qty = float(item["qty"])
                if stock < qty:
                    raise ValueError("Stok produk tidak mencukupi.")

                cursor.execute(
                    "INSERT INTO sale_items(sale_id, product_id, name, qty, price, line_total) VALUES(?,?,?,?,?,?)",
                    (sale_id, item["id"], item["name"], qty, item["price"], qty * item["price"])
                )
                cursor.execute("UPDATE products SET stock=stock-? WHERE id=?", (qty, item["id"]))
                cursor.execute(
                    "INSERT INTO stock_movements(product_id, qty, movement_type, note, created_at) VALUES(?,?,?,?,?)",
                    (item["id"], -qty, "SALE", invoice, now)
                )

            self.conn.commit()
            return invoice
        except Exception:
            self.conn.rollback()
            raise

    def update_product(self, product_id, name, sku, category, price, cost, stock, image):
        self.conn.execute(
            "UPDATE products SET name=?, sku=?, category=?, price=?, cost=?, stock=?, image=? WHERE id=?",
            (name, sku, category, float(price), float(cost), float(stock), image or "", product_id)
        )
        self.conn.commit()

    def delete_product(self, product_id):
        self.conn.execute("UPDATE products SET active=0 WHERE id=?", (product_id,))
        self.conn.commit()

    def sale(self, sale_id):
        return self.conn.execute("SELECT * FROM sales WHERE id=?", (sale_id,)).fetchone()

    def sale_items(self, sale_id):
        return self.conn.execute("SELECT * FROM sale_items WHERE sale_id=? ORDER BY id", (sale_id,)).fetchall()

    def sales(self, limit=100):
        return self.conn.execute("SELECT * FROM sales ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def product_by_code(self, code):
        code = safe_text(code).strip()
        if not code:
            return None
        return self.conn.execute("SELECT * FROM products WHERE active=1 AND (sku=? OR name=?) LIMIT 1", (code, code)).fetchone()

    def low_stock_products(self):
        threshold = safe_float(self.setting("low_stock_threshold"), 5)
        return self.conn.execute("SELECT * FROM products WHERE active=1 AND stock<=? ORDER BY stock ASC, name COLLATE NOCASE", (threshold,)).fetchall()

    def restock_product(self, product_id, qty, note="Restock"):
        qty = safe_float(qty)
        if qty <= 0:
            raise ValueError("Jumlah restock harus lebih dari 0.")
        now = datetime.now().isoformat(timespec="seconds")
        cur = self.conn.cursor()
        try:
            self.conn.execute("BEGIN")
            cur.execute("UPDATE products SET stock=stock+? WHERE id=? AND active=1", (qty, product_id))
            if cur.rowcount <= 0:
                raise ValueError("Produk tidak ditemukan.")
            cur.execute("INSERT INTO stock_movements(product_id,qty,movement_type,note,created_at) VALUES(?,?,?,?,?)", (product_id, qty, "RESTOCK", note, now))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def void_sale(self, sale_id, reason="Dibatalkan"):
        sale = self.sale(sale_id)
        if not sale:
            raise ValueError("Transaksi tidak ditemukan.")
        cur = self.conn.cursor()
        try:
            self.conn.execute("BEGIN")
            items = cur.execute("SELECT * FROM sale_items WHERE sale_id=?", (sale_id,)).fetchall()
            for item in items:
                if item["product_id"]:
                    cur.execute("UPDATE products SET stock=stock+? WHERE id=?", (float(item["qty"]), item["product_id"]))
                    cur.execute("INSERT INTO stock_movements(product_id,qty,movement_type,note,created_at) VALUES(?,?,?,?,?)",
                                (item["product_id"], float(item["qty"]), "VOID", f"Void {sale['invoice']}", datetime.now().isoformat(timespec="seconds")))
            cur.execute("UPDATE sales SET voided=1, void_reason=? WHERE id=?", (reason, sale_id))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def dashboard(self):
        today = self.conn.execute("SELECT COUNT(*) n, COALESCE(SUM(total),0) total, COALESCE(SUM(discount),0) discount FROM sales WHERE date(created_at)=date('now') AND COALESCE(voided,0)=0").fetchone()
        items = self.conn.execute("""SELECT COALESCE(SUM(si.qty),0) qty, COALESCE(SUM((si.price-COALESCE(p.cost,0))*si.qty),0) profit
                                     FROM sale_items si JOIN sales s ON s.id=si.sale_id
                                     LEFT JOIN products p ON p.id=si.product_id
                                     WHERE date(s.created_at)=date('now') AND COALESCE(s.voided,0)=0""").fetchone()
        top = self.conn.execute("SELECT si.name, SUM(si.qty) qty FROM sale_items si JOIN sales s ON s.id=si.sale_id WHERE COALESCE(s.voided,0)=0 GROUP BY si.name ORDER BY qty DESC LIMIT 5").fetchall()
        return today, items, top

    def integrity_check(self):
        row = self.conn.execute("PRAGMA integrity_check").fetchone()
        return bool(row and str(row[0]).lower() == "ok")


# ============================================================
# UI HELPERS
# ============================================================

def make_button(text, primary=False, height=44):
    button = Button(text=text, size_hint_y=None, height=dp(height), background_normal="", background_down="")
    button.background_color = PRIMARY if primary else WHITE
    button.color = WHITE if primary else TEXT
    button.bold = True
    return button


def text_label(text, size=14, color=TEXT, halign="left"):
    label = Label(text=str(text), font_size=f"{size}sp", color=color, halign=halign, valign="middle")
    label.bind(size=lambda widget, value: setattr(widget, "text_size", value))
    return label


def style_popup(popup, compact=True):
    popup.background = ""
    popup.background_color = WHITE
    popup.separator_color = BORDER
    popup.title_color = TEXT
    popup.title_size = "17sp"
    popup.title_align = "left"
    return popup


def fit_popup(popup, content, min_width=dp(300), max_width=dp(460), min_height=dp(150), max_height_ratio=0.88, extra_height=dp(58)):
    def _fit(_dt):
        try:
            width = min(max_width, max(min_width, Window.width * 0.92))
            wanted = content.minimum_height + extra_height
            height = min(max_height_ratio * Window.height, max(min_height, wanted))
            popup.size_hint = (None, None)
            popup.size = (width, height)
        except Exception:
            pass
    Clock.schedule_once(_fit, 0)
    Clock.schedule_once(_fit, 0.08)
    return popup


# ============================================================
# POS SCREEN IMPLEMENTATION
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
            box.cols = 4

            def set_card_widths(*_):
                try:
                    available = box.width - dp(4) - (dp(8) * 3)
                    card_width = max(dp(1), available / 4.0)
                    for child in box.children:
                        child.width = card_width
                except Exception:
                    pass

            for product in products:
                card = Card(
                    orientation="vertical",
                    size_hint_x=None, size_hint_y=None,
                    width=dp(110), height=dp(194),
                    padding=[dp(6), dp(6), dp(6), dp(6)], spacing=dp(4)
                )

                image_path = self.app.resolve_image(product["image"])
                if image_path:
                    product_image = Image(source=image_path, size_hint_y=None, height=dp(92), allow_stretch=True, keep_ratio=True)
                    product_image.reload()
                    card.add_widget(product_image)
                else:
                    placeholder = Label(text="FOTO", size_hint_y=None, height=dp(92), color=MUTED, font_size="11sp", bold=True, halign="center", valign="middle")
                    placeholder.text_size = placeholder.size
                    card.add_widget(placeholder)

                info = Label(
                    text=f'{safe_text(product["name"])}\n{money(product["price"])}\n| stok {float(product["stock"]):g}',
                    color=TEXT, font_size="10sp", bold=True, halign="center", valign="middle", size_hint_y=None, height=dp(55)
                )
                info.bind(size=lambda widget, value: setattr(widget, "text_size", value))
                card.add_widget(info)

                button = make_button("+ Tambah", primary=True, height=32)
                button.size_hint_y = None; button.height = dp(32)
                button.bind(on_release=lambda *_args, product=product: self.add_product(product))
                card.add_widget(button)
                box.add_widget(card)

            box.bind(width=set_card_widths)
            Clock.schedule_once(set_card_widths, 0)
        except Exception as error:
            self.app.log_error("POS_REFRESH_PRODUCTS", error)

    def add_product(self, product):
        stock = safe_float(product["stock"])
        if stock <= 0:
            self.app.notify("Stok produk habis.")
            return

        for item in self.cart_data:
            if item["id"] == product["id"]:
                if item["qty"] + 1 > stock:
                    self.app.notify("Jumlah melebihi stok.")
                    return
                item["qty"] += 1
                self.render_cart_summary()
                return

        self.cart_data.append({
            "id": product["id"],
            "name": product["name"],
            "price": safe_float(product["price"]),
            "qty": 1,
            "stock": stock
        })
        self.render_cart_summary()

    def calculate_total(self, discount=0, tax_percent=None):
        subtotal = sum(item["qty"] * item["price"] for item in self.cart_data)
        discount = max(0, safe_float(discount))
        if tax_percent is None:
            tax_percent = safe_float(self.app.tax_percent)
        tax_percent = max(0, safe_float(tax_percent))
        taxable = max(0, subtotal - discount)
        tax = taxable * tax_percent / 100
        total = max(0, taxable + tax)
        return subtotal, discount, tax, total

    def render_cart_summary(self):
        try:
            _, _, _, total = self.calculate_total()
            count = sum(item["qty"] for item in self.cart_data)
            self.ids.cart_count.text = f"{count:g} item"
            self.ids.cart_total.text = money(total)
        except Exception as error:
            self.app.log_error("CART_SUMMARY", error)

    def quick_add_by_code(self, code):
        try:
            product = self.app.db.product_by_code(code)
            if product:
                self.add_product(product)
                self.ids.search.text = ""
        except Exception as error:
            self.app.log_error("BARCODE_ADD", error)

    def open_scanner(self):
        try:
            self.app.open_barcode_scanner(self)
        except Exception as error:
            self.app.log_error("BARCODE_SCAN", error)
            self.app.notify("Scanner tidak tersedia. Gunakan scanner fisik USB/Bluetooth.")

    def open_cart_popup(self):
        try:
            if not self.cart_data:
                self.app.notify("Keranjang masih kosong.")
                return

            content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
            scroll = ScrollView(do_scroll_x=False, size_hint_y=1)
            rows = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
            rows.bind(minimum_height=rows.setter("height"))
            scroll.add_widget(rows)
            content.add_widget(scroll)

            discount = TextInput(hint_text="Rp 0", text="0", input_filter="float", multiline=False, size_hint=(1, None), height=dp(36), padding=[dp(8), dp(7)])
            discount_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(42), spacing=dp(8))
            discount_row.add_widget(Label(text="Diskon", color=MUTED, font_size="12sp", size_hint_x=None, width=dp(58), halign="left", valign="middle"))
            discount_row.add_widget(discount)

            total_label = Label(text="TOTAL  Rp 0", color=PRIMARY, font_size="18sp", bold=True, size_hint_x=1, halign="center", valign="middle")
            summary = GridLayout(cols=2, size_hint_y=None, height=dp(46), spacing=dp(8))
            summary.add_widget(discount_row)
            total_box = BoxLayout(orientation="vertical", size_hint_x=1, padding=[0, dp(2), 0, dp(2)])
            total_box.add_widget(total_label)
            summary.add_widget(total_box)
            content.add_widget(summary)

            pay = make_button("BAYAR", primary=True, height=46)
            content.add_widget(pay)

            def redraw(*_):
                try:
                    rows.clear_widgets()
                    for index, item in enumerate(list(self.cart_data)):
                        row = Card(orientation="horizontal", size_hint_y=None, height=dp(58), padding=dp(5), spacing=dp(4))
                        name = Label(text=f'{safe_text(item.get("name", "Produk"))}\n{item.get("qty", 0):g} x {money(item.get("price", 0))}', color=TEXT, halign="left", valign="middle")
                        name.bind(size=lambda w, v: setattr(w, "text_size", v))
                        row.add_widget(name)

                        for symbol, delta, primary in (("-", -1, False), ("+", 1, True), ("x", 0, False)):
                            btn = make_button(symbol, primary=primary, height=42)
                            btn.size_hint_x = None; btn.width = dp(40)
                            if delta:
                                btn.bind(on_release=lambda *_a, i=index, d=delta: self.change_qty(i, d, redraw))
                            else:
                                btn.bind(on_release=lambda *_a, i=index: self.remove_item(i, redraw))
                            row.add_widget(btn)
                        rows.add_widget(row)

                    total = self.calculate_total(discount.text or "0")[3]
                    total_label.text = f"TOTAL  {money(total)}"
                except Exception as error:
                    self.app.log_error("CART_REDRAW", error)

            def payment(*_):
                try:
                    discount_value = discount.text or "0"
                    popup.dismiss()
                    Clock.schedule_once(lambda *_dt: self.open_payment_popup(discount_value), 0.05)
                except Exception as error:
                    self.app.log_error("OPEN_PAYMENT", error)

            discount.bind(text=redraw)
            pay.bind(on_release=payment)

            popup = style_popup(Popup(title="Keranjang Belanja", content=content, size_hint=(None, None), size=(min(dp(520), Window.width * 0.94), min(dp(560), Window.height * 0.82))))
            redraw()
            popup.open()
        except Exception as error:
            self.app.log_error("OPEN_CART", error)

    def change_qty(self, index, delta, callback=None):
        if 0 <= index < len(self.cart_data):
            item = self.cart_data[index]
            item["qty"] += delta
            if item["qty"] <= 0:
                self.cart_data.pop(index)
            elif item["qty"] > item["stock"]:
                item["qty"] = item["stock"]
        self.render_cart_summary()
        if callback:
            callback()

    def remove_item(self, index, callback=None):
        if 0 <= index < len(self.cart_data):
            self.cart_data.pop(index)
        self.render_cart_summary()
        if callback:
            callback()

    def open_payment_popup(self, discount="0", tax=None):
        if not self.cart_data:
            return

        subtotal, discount_value, tax_value, total = self.calculate_total(
            discount, self.app.tax_percent if tax is None else tax
        )

        content = BoxLayout(orientation="vertical", spacing=dp(9), padding=dp(12))
        total_card = Card(orientation="vertical", size_hint_y=None, height=dp(82), padding=dp(10))
        total_card.add_widget(Label(text="TOTAL BELANJA", color=MUTED, font_size="12sp"))
        total_card.add_widget(Label(text=money(total), color=PRIMARY, font_size="24sp", bold=True))
        content.add_widget(total_card)

        method = Spinner(text="Tunai", values=["Tunai", "QRIS", "Debit", "Kredit", "Transfer", "E-Wallet"], size_hint_y=None, height=dp(44))
        paid = TextInput(hint_text="Uang diterima", input_filter="float", multiline=False, size_hint_y=None, height=dp(44), padding=[dp(12), dp(10)])
        change = Label(text="Kembalian  Rp 0", font_size="16sp", bold=True, size_hint_y=None, height=dp(40), color=SUCCESS)

        content.add_widget(method)
        content.add_widget(paid)
        content.add_widget(change)

        def update(*_):
            if method.text == "Tunai":
                paid.disabled = False
                paid_value = safe_float(paid.text)
                change.text = "Kembalian  " + money(max(0, paid_value - total))
            else:
                paid.text = ""
                paid.disabled = True
                change.text = "Pembayaran non-tunai"

        paid.bind(text=update)
        method.bind(text=update)

        buttons = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(7))
        cancel = make_button("Batal")
        done = make_button("SELESAIKAN", primary=True)
        buttons.add_widget(cancel)
        buttons.add_widget(done)
        content.add_widget(buttons)

        popup = style_popup(Popup(title="Pembayaran", content=content, size_hint=(None, None), size=(dp(380), dp(330))))
        cancel.bind(on_release=popup.dismiss)

        def finish(*_):
            paid_value = safe_float(paid.text)
            if method.text == "Tunai" and paid_value < total:
                self.app.notify("Uang kurang " + money(total - paid_value))
                return

            if method.text != "Tunai":
                paid_value = total

            change_value = max(0, paid_value - total) if method.text == "Tunai" else 0

            try:
                cart_snapshot = [dict(item) for item in self.cart_data]
                invoice = self.app.db.create_sale(
                    cart_snapshot, subtotal, discount_value, tax_value, total, method.text, paid_value, change_value
                )
                self.app.last_receipt = (
                    invoice, subtotal, discount_value, tax_value, total, method.text, paid_value, change_value, cart_snapshot
                )
                self.clear_cart()
                popup.dismiss()
                self.app.root.ids.sm.current = "transactions"
                self.app.notify(f"Transaksi {invoice} berhasil.")
                self.app.auto_backup()
                Clock.schedule_once(lambda *_: self.app.auto_print_saved_receipt(), 0.15)
            except Exception as error:
                self.app.log_error("CHECKOUT", error)
                self.app.notify("Transaksi gagal:\n" + str(error))

        done.bind(on_release=finish)
        popup.open()
        update()

    def clear_cart(self):
        self.cart_data = []
        self.render_cart_summary()


# ============================================================
# MANAGEMENT SCREENS
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
                row = Card(orientation="horizontal", size_hint_y=None, height=dp(88), spacing=dp(9), padding=dp(7))
                image_path = self.app.resolve_image(product["image"])
                if image_path:
                    image = Image(source=image_path, size_hint_x=None, width=dp(72), allow_stretch=True, keep_ratio=True)
                    image.reload()
                    row.add_widget(image)
                else:
                    row.add_widget(Label(text="FOTO", size_hint_x=None, width=dp(72), color=MUTED, bold=True))

                info = Label(
                    text=f'{safe_text(product["name"])}\n{money(product["price"])}  |  stok {float(product["stock"]):g}\n{safe_text(product["category"]) or "Tanpa kategori"}',
                    color=TEXT, font_size="11sp", halign="left", valign="middle"
                )
                info.bind(size=lambda widget, value: setattr(widget, "text_size", value))
                row.add_widget(info)

                restock_button = make_button("STOK +", primary=False, height=38)
                restock_button.size_hint_x = None; restock_button.width = dp(62)
                restock_button.bind(on_release=lambda *_args, product=product: self.open_restock(product))
                row.add_widget(restock_button)

                edit_button = make_button("EDIT", primary=True, height=38)
                edit_button.size_hint_x = None; edit_button.width = dp(58)
                edit_button.bind(on_release=lambda *_args, product=product: self.open_editor(product))
                row.add_widget(edit_button)

                delete_button = make_button("HAPUS", primary=False, height=38)
                delete_button.size_hint_x = None; delete_button.width = dp(62)
                delete_button.background_color = DANGER; delete_button.color = WHITE
                delete_button.bind(on_release=lambda *_args, product=product: self.confirm_delete(product))
                row.add_widget(delete_button)

                box.add_widget(row)
        except Exception as error:
            self.app.log_error("PRODUCT_REFRESH", error)

    def confirm_delete(self, product):
        if (self.app.db.setting("user_role") or "Owner") == "Kasir":
            self.app.notify("Akses ditolak. Role Kasir tidak dapat menghapus produk.")
            return
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))
        content.add_widget(text_label(f"Hapus produk \"{product['name']}\"?\nProduk tidak akan tampil lagi di kasir.", size=14, halign="center"))
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        cancel = make_button("Batal")
        remove = make_button("HAPUS", primary=False)
        remove.background_color = DANGER; remove.color = WHITE
        row.add_widget(cancel); row.add_widget(remove); content.add_widget(row)
        popup = style_popup(Popup(title="Hapus Produk", content=content, size_hint=(None, None), size=(dp(360), dp(190))))
        cancel.bind(on_release=popup.dismiss)

        def do_delete(*_):
            try:
                self.app.db.delete_product(product["id"])
                popup.dismiss()
                self.refresh()
                self.app.root.ids.sm.get_screen("pos").refresh_products()
                self.app.notify("Produk berhasil dihapus.")
            except Exception as error:
                self.app.log_error("DELETE_PRODUCT", error)

        remove.bind(on_release=do_delete)
        popup.open()

    def open_restock(self, product):
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        content.add_widget(text_label(f"{product['name']}\nStok saat ini: {float(product['stock']):g}", size=14, halign="center"))
        qty = TextInput(hint_text="Jumlah stok masuk", input_filter="float", multiline=False, size_hint_y=None, height=dp(44))
        note = TextInput(hint_text="Catatan (opsional)", multiline=False, size_hint_y=None, height=dp(44))
        content.add_widget(qty); content.add_widget(note)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        cancel = make_button("Batal"); save = make_button("TAMBAH STOK", primary=True)
        row.add_widget(cancel); row.add_widget(save); content.add_widget(row)
        popup = style_popup(Popup(title="Restock Produk", content=content, size_hint=(None, None), size=(dp(370), dp(260))))
        cancel.bind(on_release=popup.dismiss)

        def do_save(*_):
            try:
                self.app.db.restock_product(product["id"], qty.text, note.text.strip() or "Restock manual")
                popup.dismiss(); self.refresh(); self.app.root.ids.sm.get_screen("pos").refresh_products()
                self.app.notify("Stok berhasil ditambahkan.")
            except Exception as error:
                self.app.log_error("RESTOCK", error); self.app.notify(str(error))

        save.bind(on_release=do_save); popup.open()

    def open_editor(self, product=None):
        content = BoxLayout(orientation="vertical", spacing=dp(7), padding=dp(10))
        preview = Image(source="", size_hint_y=None, height=dp(105), allow_stretch=True, keep_ratio=True)
        content.add_widget(preview)

        fields = {}
        definitions = [
            ("name", "Nama produk *"), ("sku", "SKU / Barcode"), ("category", "Kategori"),
            ("price", "Harga jual"), ("cost", "Harga modal"), ("stock", "Stok")
        ]

        for key, hint in definitions:
            field = TextInput(hint_text=hint, multiline=False, size_hint_y=None, height=dp(42), padding=[dp(10), dp(9)])
            fields[key] = field
            content.add_widget(field)

        choose = make_button("PILIH FOTO PRODUK", primary=False, height=42)
        content.add_widget(choose)
        selected = {"path": ""}

        if product:
            for key in ("name", "sku", "category", "price", "cost", "stock"):
                fields[key].text = str(product[key] if product[key] is not None else "")
            selected["path"] = self.app.resolve_image(product["image"])
            if selected["path"]:
                preview.source = selected["path"]
                preview.reload()

        buttons = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(7))
        cancel = make_button("Batal"); save = make_button("Simpan", primary=True)
        buttons.add_widget(cancel); buttons.add_widget(save); content.add_widget(buttons)

        popup = style_popup(Popup(
            title="Edit Produk" if product else "Tambah Produk",
            content=content, size_hint=(None, None), size=(dp(400), dp(500))
        ))

        choose.bind(on_release=lambda *_: self.app.open_image_picker(selected, preview))
        cancel.bind(on_release=popup.dismiss)

        def save_product(*_):
            name = fields["name"].text.strip()
            if not name:
                self.app.notify("Nama produk wajib diisi.")
                return
            try:
                image_path = self.app.save_selected_image(selected["path"]) if selected["path"] else ""
                if product:
                    self.app.db.update_product(
                        product["id"], name, fields["sku"].text.strip(), fields["category"].text.strip(),
                        safe_float(fields["price"].text), safe_float(fields["cost"].text), safe_float(fields["stock"].text),
                        image_path or selected.get("path", "")
                    )
                else:
                    self.app.db.add_product(
                        name, fields["sku"].text.strip(), fields["category"].text.strip(),
                        safe_float(fields["price"].text), safe_float(fields["cost"].text), safe_float(fields["stock"].text),
                        image_path
                    )
                popup.dismiss(); self.refresh(); self.app.root.ids.sm.get_screen("pos").refresh_products()
                self.app.notify("Data produk berhasil disimpan.")
            except Exception as error:
                self.app.log_error("SAVE_PRODUCT", error)

        save.bind(on_release=save_product)
        popup.open()


class TransactionScreen(Screen):
    def on_enter(self):
        self.app = App.get_running_app()
        self.refresh()

    def refresh(self):
        try:
            box = self.ids.list
            box.clear_widgets()

            for sale in self.app.db.sales():
                row = Card(orientation="horizontal", size_hint_y=None, height=dp(82), padding=dp(10), spacing=dp(8))
                info = Label(
                    text=f'{sale["invoice"]}\n{sale["created_at"]}\n{sale["payment_method"]}' + ("  |  VOID" if ("voided" in sale.keys() and int(sale["voided"] or 0)) else ""),
                    color=TEXT, halign="left", valign="middle"
                )
                info.bind(size=lambda widget, value: setattr(widget, "text_size", value))
                total = Label(text=money(sale["total"]), color=PRIMARY, bold=True, font_size="15sp", size_hint_x=.35, halign="right", valign="middle")
                total.bind(size=lambda widget, value: setattr(widget, "text_size", value))

                row.add_widget(info); row.add_widget(total)
                detail = make_button("DETAIL", primary=True, height=42)
                detail.size_hint_x = None; detail.width = dp(72)
                detail.bind(on_release=lambda *_, sale_id=sale["id"]: self.open_detail(sale_id))
                row.add_widget(detail)
                box.add_widget(row)
        except Exception as error:
            self.app.log_error("TRANSACTION_REFRESH", error)

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
        close = make_button("Tutup"); print_btn = make_button("Cetak Ulang", primary=True)
        buttons.add_widget(close); buttons.add_widget(print_btn)
        content.add_widget(buttons)

        popup = style_popup(Popup(title="Detail Transaksi", content=content, size_hint=(.92, None), size=(dp(430), min(dp(440), max(dp(320), Window.height * .68)))))
        close.bind(on_release=popup.dismiss)

        cart = [dict(item) for item in items]
        self.app.last_receipt = (sale['invoice'], sale['subtotal'], sale['discount'], sale['tax'], sale['total'], sale['payment_method'], sale['paid'], sale['change_amount'], cart)
        print_btn.bind(on_release=lambda *_: (popup.dismiss(), self.app.print_saved_receipt()))

        try:
            if not int(sale["voided"] or 0):
                void_btn = make_button("VOID TRANSAKSI", primary=False, height=42)
                void_btn.background_color = DANGER; void_btn.color = WHITE
                void_btn.bind(on_release=lambda *_: (popup.dismiss(), self.confirm_void(sale_id)))
                content.add_widget(void_btn)
        except Exception:
            pass

        popup.open()

    def confirm_void(self, sale_id):
        sale = self.app.db.sale(sale_id)
        if not sale: return
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        content.add_widget(text_label(f"Batalkan transaksi {sale['invoice']}?\nStok produk akan dikembalikan.", size=14, halign="center"))
        reason = TextInput(hint_text="Alasan pembatalan", multiline=False, size_hint_y=None, height=dp(44))
        content.add_widget(reason)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        cancel = make_button("Batal"); yes = make_button("VOID", primary=False); yes.background_color = DANGER; yes.color = WHITE
        row.add_widget(cancel); row.add_widget(yes); content.add_widget(row)
        popup = style_popup(Popup(title="Void Transaksi", content=content, size_hint=(None, None), size=(dp(380), dp(250))))
        cancel.bind(on_release=popup.dismiss)

        def run(*_):
            try:
                self.app.db.void_sale(sale_id, reason.text.strip() or "Dibatalkan")
                popup.dismiss(); self.refresh(); self.app.root.ids.sm.get_screen("products").refresh(); self.app.root.ids.sm.get_screen("pos").refresh_products()
                self.app.notify("Transaksi dibatalkan dan stok dikembalikan.")
            except Exception as error:
                self.app.log_error("VOID_SALE", error); self.app.notify(str(error))

        yes.bind(on_release=run); popup.open()


class ReportScreen(Screen):
    def on_enter(self):
        self.app = App.get_running_app()
        self.refresh()

    def refresh(self):
        try:
            rows = self.app.db.conn.execute(
                """SELECT COUNT(*) n, COALESCE(SUM(subtotal),0) subtotal, COALESCE(SUM(discount),0) discount,
                          COALESCE(SUM(tax),0) tax, COALESCE(SUM(total),0) total,
                          COALESCE((SELECT SUM(qty) FROM sale_items si JOIN sales sx ON sx.id=si.sale_id WHERE date(sx.created_at)=date('now') AND COALESCE(sx.voided,0)=0),0) items_sold
                   FROM sales WHERE date(created_at)=date('now') AND COALESCE(voided,0)=0"""
            ).fetchone()

            box = self.ids.summary
            box.clear_widgets()
            header = text_label("PENJUALAN HARI INI", size=16, halign="center")
            header.bold = True; header.size_hint_y = None; header.height = dp(30)
            box.add_widget(header)

            grid = GridLayout(cols=2, spacing=dp(2), size_hint_y=None)
            grid.bind(minimum_height=grid.setter("height"))
            report_rows = [
                ("Transaksi", str(rows['n'])), ("Subtotal", money(rows['subtotal'])),
                ("Diskon", money(rows['discount'])), ("Pajak", money(rows['tax'])),
                ("Barang terjual", f"{float(rows['items_sold']):g} item"), ("TOTAL", money(rows['total'])),
            ]
            for label_text, value_text in report_rows:
                l = text_label(label_text + "  :", size=14, halign="left")
                r = text_label(value_text, size=14, halign="right")
                l.size_hint_y = None; l.height = dp(25); r.size_hint_y = None; r.height = dp(25)
                if label_text == "TOTAL": l.bold = True; r.bold = True; r.color = PRIMARY
                grid.add_widget(l); grid.add_widget(r)
            box.add_widget(grid)
        except Exception as error:
            self.app.log_error("REPORT_REFRESH", error)

    def export_csv(self):
        try:
            path = os.path.join(self.app.user_data_dir, "sales_export.csv")
            with open(path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerow(["Invoice", "Tanggal", "Subtotal", "Diskon", "Pajak", "Total", "Pembayaran", "Dibayar", "Kembalian"])
                for sale in self.app.db.sales(10000):
                    writer.writerow([sale["invoice"], sale["created_at"], sale["subtotal"], sale["discount"], sale["tax"], sale["total"], sale["payment_method"], sale["paid"], sale["change_amount"]])
            self.app.notify("CSV berhasil dibuat:\n" + path)
        except Exception as error:
            self.app.log_error("EXPORT_CSV", error)

    def export_stock_csv(self):
        try:
            path = os.path.join(self.app.user_data_dir, "stock_export.csv")
            with open(path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerow(["Nama", "SKU/Barcode", "Kategori", "Harga Jual", "Modal", "Stok"])
                for p in self.app.db.products():
                    writer.writerow([p["name"], p["sku"], p["category"], p["price"], p["cost"], p["stock"]])
            self.app.notify("CSV stok berhasil dibuat:\n" + path)
        except Exception as error:
            self.app.log_error("EXPORT_STOCK", error)


class SettingsScreen(Screen):
    def on_enter(self):
        self.app = App.get_running_app()
        try:
            self.ids.store.text = self.app.db.setting("store_name")
            self.ids.address.text = self.app.db.setting("store_address")
            self.ids.footer.text = self.app.db.setting("receipt_footer")
            logo = self.app.resolve_image(self.app.db.setting("receipt_logo"))
            self.ids.receipt_logo_preview.source = logo if logo else ""
            if logo: self.ids.receipt_logo_preview.reload()
            self.ids.logo_status.text = "Logo struk: terpasang" if logo else "Logo struk: belum dipilih"
            self.ids.paper.text = self.app.db.setting("paper") or "58mm"
            self.ids.tax.text = self.app.db.setting("tax_percent") or "0"
            self.ids.cashier.text = self.app.db.setting("cashier_name") or "Kasir"
            self.ids.role.text = self.app.db.setting("user_role") or "Owner"
            self.ids.low_stock.text = self.app.db.setting("low_stock_threshold") or "5"
            address = self.app.db.setting("printer_address")
            self.ids.printer_status.text = "Printer: " + (address if address else "belum dipilih")
        except Exception as error:
            self.app.log_error("SETTINGS_LOAD", error)

    def open_printer(self):
        try:
            self.app.bluetooth_printer_dialog()
        except Exception as error:
            self.app.log_error("SETTINGS_PRINTER", error)

    def test_printer(self):
        try:
            self.app.test_saved_printer()
        except Exception as error:
            self.app.log_error("TEST_PRINTER", error)

    def save(self):
        try:
            self.app.db.set_setting("store_name", self.ids.store.text)
            self.app.db.set_setting("store_address", self.ids.address.text)
            self.app.db.set_setting("receipt_footer", self.ids.footer.text)
            logo_path = self.app.save_selected_image(self.ids.receipt_logo_preview.source)
            self.app.db.set_setting("receipt_logo", logo_path)
            self.app.db.set_setting("paper", self.ids.paper.text)
            self.app.db.set_setting("tax_percent", str(max(0, safe_float(self.ids.tax.text))))
            self.app.db.set_setting("cashier_name", self.ids.cashier.text.strip() or "Kasir")
            self.app.db.set_setting("user_role", self.ids.role.text or "Owner")
            self.app.db.set_setting("low_stock_threshold", str(max(0, safe_float(self.ids.low_stock.text, 5))))
            self.app.tax_percent = self.app.db.setting("tax_percent") or "0"
            self.app.notify("Pengaturan berhasil disimpan.")
        except Exception as error:
            self.app.log_error("SETTINGS_SAVE", error)

    def choose_receipt_logo(self):
        try:
            selected = {"path": self.ids.receipt_logo_preview.source or ""}
            self.app.open_image_picker(selected, self.ids.receipt_logo_preview)
        except Exception as error:
            self.app.log_error("RECEIPT_LOGO_PICKER", error)

    def remove_receipt_logo(self):
        try:
            old = self.app.resolve_image(self.app.db.setting("receipt_logo"))
            self.app.db.set_setting("receipt_logo", "")
            self.ids.receipt_logo_preview.source = ""
            self.ids.logo_status.text = "Logo struk: belum dipilih"
            if old and os.path.isfile(old):
                try: os.remove(old)
                except Exception: pass
            self.app.notify("Logo struk dihapus.")
        except Exception as error:
            self.app.log_error("RECEIPT_LOGO_REMOVE", error)

    def backup(self):
        try:
            target = self.app.create_backup(manual=True)
            self.app.notify("Backup database berhasil:\n" + target)
        except Exception as error:
            self.app.log_error("DATABASE_BACKUP", error)

    def restore_backup(self):
        try:
            self.app.restore_latest_backup()
            self.app.notify("Restore berhasil.")
        except Exception as error:
            self.app.log_error("DATABASE_RESTORE", error)

    def check_database(self):
        try:
            ok = self.app.db.integrity_check()
            self.app.notify("Database sehat (integrity_check: OK)." if ok else "Database terdeteksi bermasalah.")
        except Exception as error:
            self.app.log_error("DATABASE_CHECK", error)


# ============================================================
# MAIN APPLICATION & ESC/POS ENGINE (FIXED FULL)
# ============================================================

class UniversalPOS(App):
    tax_percent = StringProperty("0")
    last_receipt = None
    pending_image = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.startup_error = None
        self.images_dir = ""

    def log_error(self, location, error):
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            error_path = os.path.join(self.user_data_dir, "KasirQU_error.log")
            with open(error_path, "a", encoding="utf-8") as file:
                file.write(f"\n\n{'='*60}\n{datetime.now().isoformat()}\nLOCATION: {location}\nERROR: {repr(error)}\n{traceback.format_exc()}")
        except Exception:
            pass
        print("KASIRQU ERROR:", location, repr(error))

    def build(self):
        try:
            data_dir = self.user_data_dir or os.path.join(os.path.expanduser("~"), ".kasirqu")
            os.makedirs(data_dir, exist_ok=True)
            self.images_dir = os.path.join(data_dir, "products")
            os.makedirs(self.images_dir, exist_ok=True)

            self.db = DB(os.path.join(data_dir, DB_NAME))
            self.tax_percent = self.db.setting("tax_percent") or "0"

            root = Builder.load_string(KV)
            return root
        except Exception as error:
            self.startup_error = error
            self.log_error("APPLICATION_STARTUP", error)
            return self.build_error_screen(error)

    def build_error_screen(self, error):
        root = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(15))
        root.add_widget(Label(text="KasirQU", color=PRIMARY, font_size="27sp", bold=True, size_hint_y=None, height=dp(55)))
        detail = Label(text=f"Aplikasi gagal memuat UI.\n\n{type(error).__name__}: {str(error)}", color=TEXT, halign="center", valign="middle")
        root.add_widget(detail)
        return root

    def on_start(self):
        Clock.schedule_once(self.finish_startup, .5)

    def finish_startup(self, *_):
        try:
            if self.startup_error or not self.root: return
            sm = self.root.ids.sm
            sm.current = "pos"
            sm.get_screen("pos").refresh_products()
        except Exception as error:
            self.log_error("FIRST_UI", error)

    def navigate(self, name):
        try:
            sm = self.root.ids.sm
            if name == "reports" and (self.db.setting("user_role") or "Owner") == "Kasir":
                self.notify("Laporan hanya dapat dibuka oleh Owner/Admin.")
                return
            sm.current = name
        except Exception as error:
            self.log_error("NAVIGATION", error)

    def notify(self, message):
        try:
            content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
            label = Label(text=str(message), color=TEXT, halign="center", valign="middle")
            label.bind(size=lambda widget, value: setattr(widget, "text_size", value))
            content.add_widget(label)
            close = make_button("OK", primary=True)
            content.add_widget(close)
            popup = style_popup(Popup(title=APP_NAME, content=content, size_hint=(.88, None), size=(dp(400), dp(200))))
            close.bind(on_release=popup.dismiss)
            popup.open()
        except Exception as error:
            self.log_error("NOTIFY", error)

    def asset_path(self, relative):
        try:
            base = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(base, relative)
        except Exception:
            return relative

    def resolve_image(self, path):
        if not path: return ""
        try:
            path = str(path).strip()
            if os.path.isfile(os.path.abspath(path)): return os.path.abspath(path)
            internal = os.path.join(self.images_dir, os.path.basename(path))
            if os.path.isfile(internal): return internal
            return ""
        except Exception:
            return ""

    def open_image_picker(self, selected, preview):
        self.open_desktop_picker(selected, preview)

    def open_desktop_picker(self, selected, preview):
        try:
            chooser = FileChooserListView(path=os.path.expanduser("~"), filters=["*.png", "*.jpg", "*.jpeg"])
            buttons = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(7))
            select_btn = make_button("Pilih", primary=True); cancel_btn = make_button("Batal")
            buttons.add_widget(select_btn); buttons.add_widget(cancel_btn)
            root = BoxLayout(orientation="vertical")
            root.add_widget(chooser); root.add_widget(buttons)

            popup = style_popup(Popup(title="Pilih Foto", content=root, size_hint=(.94, .88)))

            def choose(*_):
                if chooser.selection:
                    selected["path"] = chooser.selection[0]
                    preview.source = selected["path"]
                    preview.reload()
                popup.dismiss()

            select_btn.bind(on_release=choose); cancel_btn.bind(on_release=popup.dismiss)
            popup.open()
        except Exception as error:
            self.log_error("DESKTOP_IMAGE_PICKER", error)

    def save_selected_image(self, path):
        if not path: return ""
        try:
            source = os.path.abspath(str(path))
            if not os.path.isfile(source): return ""
            destination = os.path.join(self.images_dir, f"product_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.png")
            shutil.copy2(source, destination)
            return destination
        except Exception as error:
            self.log_error("SAVE_SELECTED_IMAGE", error)
            return ""

    def open_barcode_scanner(self, pos_screen=None):
        self.notify("Scanner aktif. Ketik / Scan kode di bar pencarian.")

    def create_backup(self, manual=False):
        backup_dir = os.path.join(self.user_data_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        target = os.path.join(backup_dir, f"KasirQU_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        shutil.copy2(self.db.path, target)
        return target

    def restore_latest_backup(self):
        latest = os.path.join(self.user_data_dir, "KasirQU_backup.db")
        if os.path.isfile(latest):
            shutil.copy2(latest, self.db.path)
            self.db = DB(self.db.path)

    def auto_backup(self):
        try:
            if self.db.setting("auto_backup") != "0": self.create_backup()
        except Exception as error:
            self.log_error("AUTO_BACKUP", error)

    # --------------------------------------------------------
    # PRINT ENGINE PERBAIKAN DUA FILE (LOGO + TEKS STRUK INTEGRATED)
    # --------------------------------------------------------

    def _convert_logo_to_escpos(self, logo_path, max_width=384):
        """Konversi gambar logo ke format ESC/POS Raster (GS v 0) - DIPERBAIKI SIKLUS BINARI NYA."""
        if not logo_path or not os.path.isfile(logo_path):
            return b""
        try:
            from PIL import Image as PILImage
            with PILImage.open(logo_path) as img:
                img = img.convert("L")
                if img.width > max_width:
                    wpercent = max_width / float(img.width)
                    hsize = int(float(img.height) * float(wpercent))
                    img = img.resize((max_width, hsize), PILImage.Resampling.LANCZOS)

                width = (img.width + 7) // 8 * 8
                height = img.height
                if img.width != width:
                    new_img = PILImage.new("L", (width, height), 255)
                    new_img.paste(img, (0, 0))
                    img = new_img

                bw_img = img.point(lambda x: 0 if x < 128 else 1, '1')
                raw_bytes = bw_img.tobytes()

                xL = (width // 8) % 256
                xH = (width // 8) // 256
                yL = height % 256
                yH = height // 256

                # Mode Rata Tengah (ESC a 1) + GS v 0 (Raster bit image)
                header = bytes([0x1B, 0x61, 0x01, 0x1D, 0x76, 0x30, 0x00, xL, xH, yL, yH])
                return header + raw_bytes + b"\x0a\x1b\x61\x00"
        except Exception as error:
            self.log_error("CONVERT_LOGO_ESCPOS", error)
            return b""

    def generate_receipt_bytes(self, receipt_data=None):
        """Membentuk Byte Stream ESC/POS lengkap (Logo + Teks Struk)."""
        data = receipt_data or self.last_receipt
        if not data:
            return b""

        invoice, subtotal, discount, tax, total, method, paid, change, cart = data
        paper_size = self.db.setting("paper") or "58mm"
        line_width = 48 if paper_size == "80mm" else 32

        # Reset Printer + Inisialisasi
        out = bytearray(b"\x1b\x40")

        # 1. Cetak Logo jika ada
        logo_file = self.resolve_image(self.db.setting("receipt_logo"))
        if logo_file:
            out.extend(self._convert_logo_to_escpos(logo_file, max_width=384 if paper_size == "80mm" else 384))

        # 2. Header Toko (Rata Tengah)
        out.extend(b"\x1b\x61\x01")  # Rata Tengah
        store_name = printer_text(self.db.setting("store_name") or "KasirQU")
        store_address = printer_text(self.db.setting("store_address"))
        
        out.extend(b"\x1b\x45\x01")  # Bold ON
        out.extend(f"{store_name}\n".encode("ascii", "ignore"))
        out.extend(b"\x1b\x45\x00")  # Bold OFF
        
        if store_address:
            out.extend(f"{store_address}\n".encode("ascii", "ignore"))

        out.extend(f"{'-'*line_width}\n".encode("ascii"))

        # 3. Transaksi Info (Rata Kiri)
        out.extend(b"\x1b\x61\x00")  # Rata Kiri
        out.extend(f"No  : {printer_text(invoice)}\n".encode("ascii"))
        out.extend(f"Tgl : {datetime.now().strftime('%d/%m/%Y %H:%M')}\n".encode("ascii"))
        out.extend(f"Ksr : {printer_text(self.db.setting('cashier_name') or 'Kasir')}\n".encode("ascii"))
        out.extend(f"{'-'*line_width}\n".encode("ascii"))

        # 4. Item Produk
        for item in cart:
            name_str = printer_text(item.get("name", "Produk"))
            out.extend(f"{name_str}\n".encode("ascii"))
            qty_str = f"  {item.get('qty', 1):g} x {money(item.get('price', 0))}"
            total_str = money(item.get('qty', 1) * item.get('price', 0))
            space_len = line_width - len(qty_str) - len(total_str)
            space_str = " " * max(1, space_len)
            out.extend(f"{qty_str}{space_str}{total_str}\n".encode("ascii"))

        out.extend(f"{'-'*line_width}\n".encode("ascii"))

        # 5. Rincian Total
        def format_line(lbl, val_str):
            l = printer_text(lbl)
            v = printer_text(val_str)
            s = " " * max(1, line_width - len(l) - len(v))
            return f"{l}{s}{v}\n".encode("ascii")

        out.extend(format_line("Subtotal", money(subtotal)))
        if discount > 0:
            out.extend(format_line("Diskon", f"-{money(discount)}"))
        if tax > 0:
            out.extend(format_line("Pajak", money(tax)))

        out.extend(b"\x1b\x45\x01")  # Bold Total
        out.extend(format_line("TOTAL", money(total)))
        out.extend(b"\x1b\x45\x00")

        out.extend(format_line("Bayar (" + printer_text(method) + ")", money(paid)))
        out.extend(format_line("Kembali", money(change)))
        out.extend(f"{'='*line_width}\n".encode("ascii"))

        # 6. Footer Struk (Rata Tengah)
        out.extend(b"\x1b\x61\x01")
        footer = printer_text(self.db.setting("receipt_footer") or "Terima Kasih")
        out.extend(f"{footer}\n\n\n\n".encode("ascii"))
        out.extend(b"\x1d\x56\x41\x00")  # Paper Cut Command

        return bytes(out)

    def print_saved_receipt(self):
        address = self.db.setting("printer_address")
        if not address:
            self.notify("Printer belum diatur di Pengaturan.")
            return

        raw_data = self.generate_receipt_bytes()
        if not raw_data:
            self.notify("Data struk tidak ditemukan.")
            return

        try:
            # Mengirimkan Stream Byte Gabungan Logo + Teks via Soket/Bluetooth Standard
            import socket
            sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            sock.connect((address, 1))
            sock.sendall(raw_data)
            sock.close()
            self.notify("Struk berhasil dicetak.")
        except Exception as error:
            self.log_error("PRINT_SAVED_RECEIPT", error)
            self.notify("Gagal mencetak ke printer Bluetooth.")

    def auto_print_saved_receipt(self):
        if self.db.setting("printer_address"):
            self.print_saved_receipt()

    def bluetooth_printer_dialog(self):
        self.notify("Fitur Pencarian Bluetooth Aktif (Pilih via menu Pengaturan sistem/Isi MAC Address).")

    def test_saved_printer(self):
        if not self.last_receipt:
            self.last_receipt = ("INV-TEST", 10000, 0, 0, 10000, "Tunai", 10000, 0, [{"name": "Item Uji Coba", "qty": 1, "price": 10000}])
        self.print_saved_receipt()


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":
    UniversalPOS().run()
