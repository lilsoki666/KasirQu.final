import os
import csv
import shutil
import sqlite3
import traceback
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import StringProperty
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
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import platform


APP_NAME = "KasirQU"
DB_NAME = "KasirQU.db"


# ============================================================
# HELPERS
# ============================================================

def money(value):
    try:
        value = Decimal(str(value)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        return "Rp {:,}".format(value).replace(",", ".")
    except Exception:
        return "Rp 0"


def number(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def text_label(text="", size=14, color=(0.08, 0.09, 0.12, 1),
               bold=False, halign="left", valign="middle", **kwargs):
    label = Label(
        text=str(text),
        font_size=f"{size}sp",
        color=color,
        bold=bold,
        halign=halign,
        valign=valign,
        **kwargs
    )
    label.bind(size=lambda w, s: setattr(w, "text_size", s))
    return label


def make_button(text, primary=False, height=46, **kwargs):
    btn = Button(
        text=text,
        size_hint_y=None,
        height=dp(height),
        background_normal="",
        background_down="",
        background_color=(
            (0.10, 0.36, 0.86, 1)
            if primary else
            (0.92, 0.94, 0.97, 1)
        ),
        color=(1, 1, 1, 1) if primary else (0.10, 0.13, 0.18, 1),
        bold=True,
        **kwargs
    )
    return btn


class Card(BoxLayout):
    """Kartu UI sederhana. Tidak memakai ButtonBehavior."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(14)]
            )
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *_):
        self.rect.pos = self.pos
        self.rect.size = self.size


class SwipeManager(ScreenManager):
    """Swipe horizontal tanpa ButtonBehavior."""

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
            if abs(dx) > dp(70) and abs(dx) > abs(dy) * 1.25:
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
            direction="right" if delta < 0 else "left",
            duration=0.18
        )
        self.current = names[target]


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
        cur = self.conn.cursor()
        cur.executescript("""
        PRAGMA foreign_keys=ON;

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
            "store_name": "KasirQU",
            "store_address": "Alamat / Kontak",
            "receipt_footer": "Terima kasih telah berbelanja",
            "paper": "58mm",
            "tax_percent": "0"
        }

        for key, value in defaults.items():
            cur.execute(
                "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
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
            "INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
            (key, str(value))
        )
        self.conn.commit()

    def products(self, search=""):
        if search:
            q = f"%{search.strip()}%"
            return self.conn.execute(
                """
                SELECT * FROM products
                WHERE active=1
                AND (name LIKE ? OR sku LIKE ? OR category LIKE ?)
                ORDER BY name COLLATE NOCASE
                """,
                (q, q, q)
            ).fetchall()

        return self.conn.execute(
            """
            SELECT * FROM products
            WHERE active=1
            ORDER BY name COLLATE NOCASE
            """
        ).fetchall()

    def add_product(
        self, name, sku, category, price, cost, stock, image=""
    ):
        self.conn.execute(
            """
            INSERT INTO products
            (name,sku,category,price,cost,stock,image,created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                name, sku, category,
                float(price), float(cost), float(stock),
                image,
                datetime.now().isoformat(timespec="seconds")
            )
        )
        self.conn.commit()

    def create_sale(
        self, cart, subtotal, discount, tax, total,
        method, paid, change
    ):
        now = datetime.now()
        invoice = "INV-" + now.strftime("%Y%m%d%H%M%S%f")
        created = now.isoformat(timespec="seconds")
        cur = self.conn.cursor()

        try:
            self.conn.execute("BEGIN")

            cur.execute(
                """
                INSERT INTO sales
                (invoice,subtotal,discount,tax,total,payment_method,
                 paid,change_amount,created_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    invoice, subtotal, discount, tax, total,
                    method, paid, change, created
                )
            )

            sale_id = cur.lastrowid

            for item in cart:
                row = cur.execute(
                    """
                    SELECT stock FROM products
                    WHERE id=? AND active=1
                    """,
                    (item["id"],)
                ).fetchone()

                if not row:
                    raise ValueError(
                        f'Produk "{item["name"]}" tidak ditemukan.'
                    )

                stock = float(row["stock"])
                qty = float(item["qty"])

                if stock < qty:
                    raise ValueError(
                        f'Stok "{item["name"]}" tidak mencukupi.'
                    )

                cur.execute(
                    """
                    INSERT INTO sale_items
                    (sale_id,product_id,name,qty,price,line_total)
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

                cur.execute(
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
            "SELECT * FROM sales ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()


# ============================================================
# POS SCREEN
# ============================================================

class POSScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = None
        self.cart_data = []
        self._built = False

    def on_kv_post(self, *_):
        # Nama method dipertahankan sebagai no-op agar aman jika project
        # lama pernah memanggilnya. UI sebenarnya dibuat di build_ui().
        pass

    def on_pre_enter(self, *_):
        if not self._built:
            self.build_ui()
        self.app = App.get_running_app()
        self.refresh_products()
        self.update_summary()

    def build_ui(self):
        self._built = True
        root = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(10)
        )

        # Header
        header = BoxLayout(
            size_hint_y=None,
            height=dp(52),
            spacing=dp(8)
        )
        header.add_widget(text_label(
            "KasirQU",
            size=23,
            bold=True,
            color=(0.06, 0.10, 0.16, 1),
            size_hint_x=0.35
        ))

        self.search = TextInput(
            hint_text="Cari produk / SKU...",
            multiline=False,
            size_hint_x=0.65,
            padding=[dp(12), dp(10)]
        )
        self.search.bind(text=lambda *_: self.refresh_products())
        header.add_widget(self.search)
        root.add_widget(header)

        # Produk
        root.add_widget(text_label(
            "Pilih produk",
            size=14,
            color=(0.38, 0.42, 0.49, 1),
            size_hint_y=None,
            height=dp(25)
        ))

        scroll = ScrollView(do_scroll_x=False)
        self.products_grid = GridLayout(
            cols=2,
            spacing=dp(9),
            padding=dp(2),
            size_hint_y=None
        )
        self.products_grid.bind(
            minimum_height=self.products_grid.setter("height")
        )
        scroll.add_widget(self.products_grid)
        root.add_widget(scroll)

        # Summary bawah - ringkas
        summary = Card(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(70),
            padding=dp(10),
            spacing=dp(8)
        )
        self.cart_count_label = text_label(
            "0 item",
            size=14,
            bold=True,
            size_hint_x=0.30
        )
        self.cart_total_label = text_label(
            "Rp 0",
            size=19,
            bold=True,
            halign="right",
            color=(0.08, 0.32, 0.78, 1),
            size_hint_x=0.42
        )
        cart_btn = make_button(
            "KERANJANG",
            primary=True,
            height=44,
            size_hint_x=0.28
        )
        cart_btn.bind(on_release=lambda *_: self.open_cart_popup())

        summary.add_widget(self.cart_count_label)
        summary.add_widget(self.cart_total_label)
        summary.add_widget(cart_btn)
        root.add_widget(summary)

        self.add_widget(root)

    def refresh_products(self, *_):
        if not self._built or self.app is None:
            return

        self.products_grid.clear_widgets()
        query = self.search.text if hasattr(self, "search") else ""

        for product in self.app.db.products(query):
            self.products_grid.add_widget(
                self.make_product_card(product)
            )

    def make_product_card(self, product):
        card = Card(
            orientation="vertical",
            size_hint_y=None,
            height=dp(190),
            padding=dp(7),
            spacing=dp(5)
        )

        image = self.app.product_image_widget(
            product["image"],
            size_hint_y=0.56
        )
        card.add_widget(image)

        info = text_label(
            f'{product["name"]}\n'
            f'{money(product["price"])}  â€¢  stok {float(product["stock"]):g}',
            size=13,
            bold=True,
            halign="center",
            size_hint_y=0.25
        )
        card.add_widget(info)

        btn = make_button(
            "+ Tambah",
            primary=True,
            height=36,
            size_hint_y=0.19
        )
        btn.bind(
            on_release=lambda *_,
            p=product: self.add_product(p)
        )
        card.add_widget(btn)

        return card

    def add_product(self, product):
        stock = float(product["stock"])

        if stock <= 0:
            self.app.notify("Stok produk habis.")
            return

        for item in self.cart_data:
            if item["id"] == product["id"]:
                if item["qty"] + 1 > stock:
                    self.app.notify("Jumlah melebihi stok.")
                    return
                item["qty"] += 1
                self.update_summary()
                return

        self.cart_data.append({
            "id": product["id"],
            "name": product["name"],
            "price": float(product["price"]),
            "qty": 1.0,
            "stock": stock
        })
        self.update_summary()

    def calculate_total(self, discount=0, tax_percent=None):
        subtotal = sum(
            float(x["qty"]) * float(x["price"])
            for x in self.cart_data
        )
        discount = max(0, number(discount))

        if tax_percent is None:
            tax_percent = number(self.app.tax_percent)

        taxable = max(0, subtotal - discount)
        tax = taxable * max(0, number(tax_percent)) / 100
        total = max(0, taxable + tax)
        return subtotal, discount, tax, total

    def update_summary(self):
        if not self._built:
            return

        _, _, _, total = self.calculate_total()
        count = sum(float(x["qty"]) for x in self.cart_data)

        self.cart_count_label.text = f"{count:g} item"
        self.cart_total_label.text = money(total)

    def open_cart_popup(self):
        if not self.cart_data:
            self.app.notify("Keranjang masih kosong.")
            return

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=dp(10)
        )

        scroll = ScrollView(do_scroll_x=False)
        rows = GridLayout(
            cols=1,
            spacing=dp(6),
            size_hint_y=None
        )
        rows.bind(minimum_height=rows.setter("height"))
        scroll.add_widget(rows)
        content.add_widget(scroll)

        discount = TextInput(
            hint_text="Diskon",
            text="0",
            input_filter="float",
            multiline=False,
            size_hint_y=None,
            height=dp(44)
        )
        tax = TextInput(
            hint_text="Pajak %",
            text=self.app.tax_percent,
            input_filter="float",
            multiline=False,
            size_hint_y=None,
            height=dp(44)
        )
        total_label = text_label(
            "TOTAL  Rp 0",
            size=19,
            bold=True,
            color=(0.08, 0.32, 0.78, 1),
            size_hint_y=None,
            height=dp(40)
        )

        content.add_widget(discount)
        content.add_widget(tax)
        content.add_widget(total_label)

        actions = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(7)
        )
        clear = make_button("Kosongkan", height=46)
        pay = make_button("BAYAR", primary=True, height=46)
        actions.add_widget(clear)
        actions.add_widget(pay)
        content.add_widget(actions)

        popup = Popup(
            title="Keranjang",
            content=content,
            size_hint=(0.94, 0.88)
        )

        def redraw(*_):
            rows.clear_widgets()

            for index, item in enumerate(self.cart_data):
                row = BoxLayout(
                    size_hint_y=None,
                    height=dp(54),
                    spacing=dp(4)
                )

                label = text_label(
                    f'{item["name"]}\n'
                    f'{item["qty"]:g} Ã— {money(item["price"])}',
                    size=12,
                    size_hint_x=0.58
                )
                row.add_widget(label)

                minus = make_button("âˆ’", height=42, size_hint_x=None, width=dp(42))
                plus = make_button("+", height=42, size_hint_x=None, width=dp(42))
                delete = make_button("Ã—", height=42, size_hint_x=None, width=dp(42))

                minus.bind(
                    on_release=lambda *_,
                    i=index: self.change_qty(i, -1, redraw)
                )
                plus.bind(
                    on_release=lambda *_,
                    i=index: self.change_qty(i, 1, redraw)
                )
                delete.bind(
                    on_release=lambda *_,
                    i=index: self.remove_item(i, redraw)
                )

                row.add_widget(minus)
                row.add_widget(plus)
                row.add_widget(delete)
                rows.add_widget(row)

            _, _, _, total = self.calculate_total(
                discount.text, tax.text
            )
            total_label.text = f"TOTAL  {money(total)}"

        discount.bind(text=redraw)
        tax.bind(text=redraw)

        clear.bind(
            on_release=lambda *_: (
                self.clear_cart(),
                popup.dismiss()
            )
        )
        pay.bind(
            on_release=lambda *_: (
                popup.dismiss(),
                self.open_payment_popup(
                    discount.text,
                    tax.text
                )
            )
        )

        popup.open()
        redraw()

    def change_qty(self, index, delta, callback=None):
        if not 0 <= index < len(self.cart_data):
            return

        item = self.cart_data[index]
        item["qty"] += delta

        if item["qty"] <= 0:
            self.cart_data.pop(index)
        elif item["qty"] > item["stock"]:
            item["qty"] = item["stock"]

        self.update_summary()
        if callback:
            callback()

    def remove_item(self, index, callback=None):
        if 0 <= index < len(self.cart_data):
            self.cart_data.pop(index)

        self.update_summary()
        if callback:
            callback()

    def clear_cart(self):
        self.cart_data = []
        self.update_summary()

    def open_payment_popup(self, discount="0", tax="0"):
        if not self.cart_data:
            return

        subtotal, discount_value, tax_value, total = self.calculate_total(
            discount, tax
        )

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=dp(12)
        )

        content.add_widget(text_label(
            f"TOTAL\n{money(total)}",
            size=22,
            bold=True,
            halign="center",
            color=(0.08, 0.32, 0.78, 1),
            size_hint_y=None,
            height=dp(72)
        ))

        method = Spinner(
            text="Tunai",
            values=[
                "Tunai", "QRIS", "Debit",
                "Kredit", "Transfer", "E-Wallet"
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
        change = text_label(
            "Kembalian  Rp 0",
            size=16,
            bold=True,
            color=(0.06, 0.55, 0.30, 1),
            size_hint_y=None,
            height=dp(40)
        )

        content.add_widget(method)
        content.add_widget(paid)
        content.add_widget(change)

        actions = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(7)
        )
        cancel = make_button("Batal", height=46)
        done = make_button("SELESAIKAN", primary=True, height=46)
        actions.add_widget(cancel)
        actions.add_widget(done)
        content.add_widget(actions)

        popup = Popup(
            title="Pembayaran",
            content=content,
            size_hint=(0.92, 0.70)
        )

        def update(*_):
            if method.text == "Tunai":
                paid.disabled = False
                value = max(0, number(paid.text) - total)
                change.text = f"Kembalian  {money(value)}"
            else:
                paid.disabled = True
                paid.text = ""
                change.text = "Pembayaran non-tunai"

        paid.bind(text=update)
        method.bind(text=update)

        cancel.bind(on_release=popup.dismiss)

        def finish(*_):
            paid_value = number(paid.text)

            if method.text == "Tunai":
                if paid_value < total:
                    self.app.notify(
                        "Uang kurang " + money(total - paid_value)
                    )
                    return
                change_value = paid_value - total
            else:
                paid_value = total
                change_value = 0

            try:
                invoice = self.app.db.create_sale(
                    self.cart_data,
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
                    list(self.cart_data)
                )

                self.clear_cart()
                popup.dismiss()
                self.app.navigate("transactions")

                self.app.notify(
                    f"Transaksi {invoice} berhasil."
                )

                self.app.print_or_offer(invoice)

            except Exception as error:
                self.app.log_error("checkout", error)
                self.app.notify(
                    "Transaksi gagal:\n" + str(error)
                )

        done.bind(on_release=finish)

        popup.open()
        update()


# ============================================================
# PRODUCT SCREEN
# ============================================================

class ProductScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = None
        self._built = False

    def on_pre_enter(self, *_):
        self.app = App.get_running_app()
        if not self._built:
            self.build_ui()
        self.refresh()

    def build_ui(self):
        self._built = True

        root = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(10)
        )

        header = BoxLayout(
            size_hint_y=None,
            height=dp(52),
            spacing=dp(8)
        )
        header.add_widget(text_label(
            "Produk",
            size=23,
            bold=True,
            size_hint_x=0.68
        ))

        add_btn = make_button(
            "+ Produk",
            primary=True,
            height=44,
            size_hint_x=0.32
        )
        add_btn.bind(on_release=lambda *_: self.open_editor())
        header.add_widget(add_btn)

        root.add_widget(header)

        self.search = TextInput(
            hint_text="Cari nama, SKU, kategori...",
            multiline=False,
            size_hint_y=None,
            height=dp(44),
            padding=[dp(12), dp(10)]
        )
        self.search.bind(text=lambda *_: self.refresh())
        root.add_widget(self.search)

        scroll = ScrollView(do_scroll_x=False)
        self.list_grid = GridLayout(
            cols=1,
            spacing=dp(8),
            padding=dp(2),
            size_hint_y=None
        )
        self.list_grid.bind(
            minimum_height=self.list_grid.setter("height")
        )
        scroll.add_widget(self.list_grid)
        root.add_widget(scroll)

        self.add_widget(root)

    def refresh(self, *_):
        if not self._built or self.app is None:
            return

        self.list_grid.clear_widgets()
        query = self.search.text if hasattr(self, "search") else ""

        for product in self.app.db.products(query):
            row = Card(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(86),
                padding=dp(7),
                spacing=dp(8)
            )

            row.add_widget(
                self.app.product_image_widget(
                    product["image"],
                    size_hint_x=0.22
                )
            )

            info = text_label(
                f'{product["name"]}\n'
                f'{money(product["price"])}  â€¢  stok {float(product["stock"]):g}\n'
                f'{product["category"] or "Tanpa kategori"}'
                + (
                    f'  â€¢  {product["sku"]}'
                    if product["sku"] else ""
                ),
                size=13,
                size_hint_x=0.78
            )
            row.add_widget(info)
            self.list_grid.add_widget(row)

    def open_editor(self):
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
                padding=[dp(10), dp(9)]
            )
            fields[key] = field
            content.add_widget(field)

        choose = make_button(
            "Pilih Foto Produk",
            height=44
        )
        content.add_widget(choose)

        selected = {"path": ""}

        actions = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(7)
        )
        cancel = make_button("Batal", height=46)
        save = make_button("Simpan", primary=True, height=46)
        actions.add_widget(cancel)
        actions.add_widget(save)
        content.add_widget(actions)

        popup = Popup(
            title="Tambah Produk",
            content=content,
            size_hint=(0.94, 0.92)
        )

        choose.bind(
            on_release=lambda *_:
            self.app.open_image_picker(selected, preview)
        )
        cancel.bind(on_release=popup.dismiss)

        def save_product(*_):
            name = fields["name"].text.strip()

            if not name:
                self.app.notify("Nama produk wajib diisi.")
                return

            price = number(fields["price"].text)
            cost = number(fields["cost"].text)
            stock = number(fields["stock"].text)

            if price < 0 or cost < 0 or stock < 0:
                self.app.notify(
                    "Harga dan stok tidak boleh negatif."
                )
                return

            try:
                image_path = ""

                if selected["path"]:
                    image_path = self.app.save_selected_image(
                        selected["path"]
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
                    price,
                    cost,
                    stock,
                    image_path
                )

                popup.dismiss()
                self.refresh()
                self.app.notify("Produk berhasil ditambahkan.")

            except Exception as error:
                self.app.log_error("save_product", error)
                self.app.notify(
                    "Produk gagal disimpan:\n" + str(error)
                )

        save.bind(on_release=save_product)

        popup.open()


# ============================================================
# TRANSACTION SCREEN
# ============================================================

class TransactionScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = None
        self._built = False

    def on_pre_enter(self, *_):
        self.app = App.get_running_app()
        if not self._built:
            self.build_ui()
        self.refresh()

    def build_ui(self):
        self._built = True

        root = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(10)
        )

        root.add_widget(text_label(
            "Riwayat Transaksi",
            size=23,
            bold=True,
            size_hint_y=None,
            height=dp(52)
        ))

        scroll = ScrollView(do_scroll_x=False)
        self.list_grid = GridLayout(
            cols=1,
            spacing=dp(8),
            size_hint_y=None
        )
        self.list_grid.bind(
            minimum_height=self.list_grid.setter("height")
        )
        scroll.add_widget(self.list_grid)
        root.add_widget(scroll)

        self.add_widget(root)

    def refresh(self, *_):
        if not self._built or self.app is None:
            return

        self.list_grid.clear_widgets()

        for sale in self.app.db.sales():
            row = Card(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(78),
                padding=dp(10)
            )

            info = text_label(
                f'{sale["invoice"]}\n'
                f'{sale["created_at"]}  â€¢  {sale["payment_method"]}',
                size=12,
                size_hint_x=0.68
            )
            total = text_label(
                money(sale["total"]),
                size=15,
                bold=True,
                halign="right",
                color=(0.08, 0.32, 0.78, 1),
                size_hint_x=0.32
            )

            row.add_widget(info)
            row.add_widget(total)
            self.list_grid.add_widget(row)


# ============================================================
# REPORT SCREEN
# ============================================================

class ReportScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = None
        self._built = False

    def on_pre_enter(self, *_):
        self.app = App.get_running_app()
        if not self._built:
            self.build_ui()
        self.refresh()

    def build_ui(self):
        self._built = True

        root = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(12)
        )

        root.add_widget(text_label(
            "Laporan",
            size=23,
            bold=True,
            size_hint_y=None,
            height=dp(52)
        ))

        card = Card(
            orientation="vertical",
            padding=dp(16),
            size_hint_y=None,
            height=dp(210)
        )
        self.summary = text_label(
            "Memuat...",
            size=16,
            valign="top"
        )
        card.add_widget(self.summary)
        root.add_widget(card)

        export = make_button(
            "Export CSV",
            primary=True,
            height=48
        )
        export.bind(on_release=lambda *_: self.export_csv())
        root.add_widget(export)

        root.add_widget(Widget())
        self.add_widget(root)

    def refresh(self, *_):
        if not self._built or self.app is None:
            return

        try:
            row = self.app.db.conn.execute(
                """
                SELECT
                    COUNT(*) n,
                    COALESCE(SUM(subtotal),0) subtotal,
                    COALESCE(SUM(discount),0) discount,
                    COALESCE(SUM(tax),0) tax,
                    COALESCE(SUM(total),0) total
                FROM sales
                WHERE date(created_at)=date('now','localtime')
                """
            ).fetchone()

            self.summary.text = (
                "HARI INI\n\n"
                f"Transaksi : {row['n']}\n"
                f"Subtotal  : {money(row['subtotal'])}\n"
                f"Diskon    : {money(row['discount'])}\n"
                f"Pajak     : {money(row['tax'])}\n"
                f"Penjualan : {money(row['total'])}"
            )
        except Exception as error:
            self.app.log_error("report_refresh", error)
            self.summary.text = "Laporan gagal dimuat."

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
                writer.writerow([
                    "Invoice", "Tanggal", "Subtotal",
                    "Diskon", "Pajak", "Total",
                    "Pembayaran", "Dibayar", "Kembalian"
                ])

                for sale in self.app.db.sales(10000):
                    writer.writerow([
                        sale["invoice"],
                        sale["created_at"],
                        sale["subtotal"],
                        sale["discount"],
                        sale["tax"],
                        sale["total"],
                        sale["payment_method"],
                        sale["paid"],
                        sale["change_amount"]
                    ])

            self.app.notify(
                f"CSV tersimpan:\n{path}"
            )

        except Exception as error:
            self.app.log_error("export_csv", error)
            self.app.notify("Export CSV gagal.")


# ============================================================
# SETTINGS SCREEN
# ============================================================

class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = None
        self._built = False

    def on_pre_enter(self, *_):
        self.app = App.get_running_app()
        if not self._built:
            self.build_ui()
        self.load_settings()

    def build_ui(self):
        self._built = True

        root = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(9)
        )

        root.add_widget(text_label(
            "Pengaturan",
            size=23,
            bold=True,
            size_hint_y=None,
            height=dp(52)
        ))

        self.store = TextInput(
            hint_text="Nama usaha",
            multiline=False,
            size_hint_y=None,
            height=dp(44)
        )
        self.address = TextInput(
            hint_text="Alamat / kontak",
            multiline=False,
            size_hint_y=None,
            height=dp(44)
        )
        self.footer = TextInput(
            hint_text="Footer struk",
            multiline=False,
            size_hint_y=None,
            height=dp(44)
        )

        root.add_widget(self.store)
        root.add_widget(self.address)
        root.add_widget(self.footer)

        self.paper = Spinner(
            text="58mm",
            values=("58mm", "80mm"),
            size_hint_y=None,
            height=dp(44)
        )
        root.add_widget(self.paper)

        save = make_button(
            "Simpan Pengaturan",
            primary=True,
            height=46
        )
        save.bind(on_release=lambda *_: self.save())
        root.add_widget(save)

        backup = make_button(
            "Backup Database",
            height=46
        )
        backup.bind(on_release=lambda *_: self.backup())
        root.add_widget(backup)

        root.add_widget(text_label(
            "Printer thermal Bluetooth harus sudah dipairing "
            "melalui pengaturan Android.",
            size=13,
            color=(0.38, 0.42, 0.48, 1),
            size_hint_y=None,
            height=dp(55)
        ))

        root.add_widget(Widget())
        self.add_widget(root)

    def load_settings(self):
        self.store.text = self.app.db.setting("store_name")
        self.address.text = self.app.db.setting("store_address")
        self.footer.text = self.app.db.setting("receipt_footer")
        self.paper.text = self.app.db.setting("paper") or "58mm"

    def save(self):
        try:
            self.app.db.set_setting("store_name", self.store.text)
            self.app.db.set_setting("store_address", self.address.text)
            self.app.db.set_setting("receipt_footer", self.footer.text)
            self.app.db.set_setting("paper", self.paper.text)

            self.app.tax_percent = (
                self.app.db.setting("tax_percent") or "0"
            )
            self.app.notify("Pengaturan disimpan.")
        except Exception as error:
            self.app.log_error("settings_save", error)

    def backup(self):
        try:
            self.app.db.conn.commit()
            target = os.path.join(
                self.app.user_data_dir,
                "KasirQU_backup.db"
            )
            shutil.copy2(self.app.db.path, target)
            self.app.notify(
                f"Backup dibuat:\n{target}"
            )
        except Exception as error:
            self.app.log_error("database_backup", error)
            self.app.notify("Backup database gagal.")


# ============================================================
# MAIN APP
# ============================================================

class UniversalPOS(App):
    tax_percent = StringProperty("0")
    last_receipt = None
    pending_image = None
    _activity_callback = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.startup_error = None

    def build(self):
        try:
            self.title = APP_NAME

            data_dir = os.path.abspath(
                self.user_data_dir or
                os.path.join(
                    os.path.expanduser("~"),
                    ".kasirqu"
                )
            )
            os.makedirs(data_dir, exist_ok=True)

            self.images_dir = os.path.join(
                data_dir,
                "products"
            )
            os.makedirs(self.images_dir, exist_ok=True)

            self.db = DB(
                os.path.join(data_dir, DB_NAME)
            )

            self.tax_percent = (
                self.db.setting("tax_percent") or "0"
            )

            root = self.build_root_ui()

            if root is None:
                raise RuntimeError(
                    "Root aplikasi gagal dibuat."
                )

            return root

        except Exception as error:
            self.startup_error = error
            self.log_error(
                "APPLICATION_STARTUP",
                error
            )
            return self.build_error_screen(error)

    def build_root_ui(self):
        root = BoxLayout(
            orientation="vertical"
        )

        self.sm = SwipeManager(
            size_hint_y=1
        )

        self.pos_screen = POSScreen(name="pos")
        self.products_screen = ProductScreen(name="products")
        self.transactions_screen = TransactionScreen(name="transactions")
        self.reports_screen = ReportScreen(name="reports")
        self.settings_screen = SettingsScreen(name="settings")

        self.sm.add_widget(self.pos_screen)
        self.sm.add_widget(self.products_screen)
        self.sm.add_widget(self.transactions_screen)
        self.sm.add_widget(self.reports_screen)
        self.sm.add_widget(self.settings_screen)

        root.add_widget(self.sm)
        root.add_widget(self.build_toolbar())

        return root

    def build_toolbar(self):
        bar = BoxLayout(
            size_hint_y=None,
            height=dp(70),
            padding=[dp(5), dp(5)],
            spacing=dp(3)
        )

        self.nav_buttons = {}

        items = [
            ("pos", "â–£", "Kasir"),
            ("products", "â–¤", "Produk"),
            ("transactions", "â†»", "Riwayat"),
            ("reports", "â–¥", "Laporan"),
            ("settings", "âš™", "Pengaturan")
        ]

        for name, icon, label in items:
            btn = Button(
                text=f"{icon}\n{label}",
                font_size="12sp",
                bold=True,
                background_normal="",
                background_down="",
                background_color=(1, 1, 1, 1),
                color=(0.28, 0.32, 0.39, 1),
                border=(0, 0, 0, 0)
            )
            btn.bind(
                on_release=lambda *_,
                target=name: self.navigate(target)
            )
            self.nav_buttons[name] = btn
            bar.add_widget(btn)

        Clock.schedule_once(
            lambda *_: self.update_nav_style("pos"),
            0
        )

        return bar

    def update_nav_style(self, active):
        for name, btn in self.nav_buttons.items():
            if name == active:
                btn.background_color = (
                    0.10, 0.36, 0.86, 1
                )
                btn.color = (1, 1, 1, 1)
            else:
                btn.background_color = (
                    1, 1, 1, 1
                )
                btn.color = (
                    0.28, 0.32, 0.39, 1
                )

    def navigate(self, name):
        if not hasattr(self, "sm"):
            return

        names = list(self.sm.screen_names)

        if name not in names:
            return

        current = self.sm.current
        if current == name:
            return

        old_index = names.index(current)
        new_index = names.index(name)

        self.sm.transition = SlideTransition(
            direction="left" if new_index > old_index else "right",
            duration=0.18
        )
        self.sm.current = name
        self.update_nav_style(name)

    def on_start(self):
        Clock.schedule_once(
            self.finish_startup,
            0.35
        )

    def finish_startup(self, *_):
        try:
            if self.startup_error is not None:
                return

            if not self.root:
                raise RuntimeError("Root aplikasi tidak tersedia.")

            self.pos_screen.app = self
            self.pos_screen.refresh_products()
            self.pos_screen.update_summary()

        except Exception as error:
            self.startup_error = error
            self.log_error("FIRST_UI", error)

        finally:
            self.hide_android_loading_screen()

    # --------------------------------------------------------
    # ERROR
    # --------------------------------------------------------

    def log_error(self, location, error):
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            path = os.path.join(
                self.user_data_dir,
                "KasirQU_error.log"
            )

            with open(path, "a", encoding="utf-8") as file:
                file.write(
                    "\n\n==============================\n"
                )
                file.write(datetime.now().isoformat())
                file.write(f"\nLOCATION: {location}\n")
                file.write(f"ERROR: {repr(error)}\n")
                file.write(traceback.format_exc())

        except Exception:
            pass

        print(
            f"KASIRQU ERROR [{location}]:",
            repr(error)
        )

    def build_error_screen(self, error):
        root = BoxLayout(
            orientation="vertical",
            padding=dp(24),
            spacing=dp(15)
        )
        root.add_widget(text_label(
            APP_NAME,
            size=27,
            bold=True,
            halign="center",
            size_hint_y=None,
            height=dp(55)
        ))
        root.add_widget(text_label(
            "Gagal memuat aplikasi.\n\n"
            f"{type(error).__name__}: {error}\n\n"
            "Detail tersimpan di KasirQU_error.log",
            size=15,
            halign="center"
        ))
        return root

    def notify(self, message):
        try:
            Popup(
                title=APP_NAME,
                content=text_label(
                    str(message),
                    size=14,
                    halign="center"
                ),
                size_hint=(0.88, 0.34)
            ).open()
        except Exception as error:
            self.log_error("NOTIFY", error)

    # --------------------------------------------------------
    # IMAGE
    # --------------------------------------------------------

    def product_image_widget(self, stored_path, **kwargs):
        path = self.resolve_image(stored_path)

        if path:
            img = Image(
                source=path,
                allow_stretch=True,
                keep_ratio=True,
                **kwargs
            )
            # Memaksa reload setelah source ditetapkan.
            Clock.schedule_once(
                lambda *_: img.reload(),
                0
            )
            return img

        return text_label(
            "â–£",
            size=28,
            halign="center",
            color=(0.55, 0.58, 0.64, 1),
            **kwargs
        )

    def resolve_image(self, path):
        if not path:
            return ""

        try:
            # Path lama mungkin relatif. Coba beberapa lokasi.
            candidates = []

            if os.path.isabs(path):
                candidates.append(path)
            else:
                candidates.append(
                    os.path.join(self.user_data_dir, path)
                )
                candidates.append(path)

            for candidate in candidates:
                candidate = os.path.abspath(candidate)
                if os.path.isfile(candidate):
                    return candidate

        except Exception as error:
            self.log_error("RESOLVE_IMAGE", error)

        return ""

    def open_image_picker(self, selected, preview):
        if platform != "android":
            self.open_desktop_picker(selected, preview)
            return

        try:
            from jnius import autoclass
            from android.activity import bind

            Intent = autoclass("android.content.Intent")
            intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType("image/*")

            # Ambil URI yang bisa dipakai lebih lama jika Android mengizinkan.
            try:
                intent.addFlags(
                    Intent.FLAG_GRANT_READ_URI_PERMISSION |
                    Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION
                )
            except Exception:
                pass

            self.pending_image = (selected, preview)

            # Hindari bind berkali-kali.
            try:
                from android.activity import unbind
                if self._activity_callback is not None:
                    unbind(
                        on_activity_result=self._activity_callback
                    )
            except Exception:
                pass

            def callback(request_code, result_code, data):
                self.on_activity_result(
                    request_code, result_code, data
                )

            self._activity_callback = callback
            bind(on_activity_result=callback)

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
            self.pending_image = None
            self.notify(
                "Pemilih foto Android gagal dibuka."
            )

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

            temp_path = self.copy_content_uri(uri)

            if not temp_path:
                self.notify(
                    "Foto dipilih, tetapi tidak dapat dibaca."
                )
                return

            if self.pending_image:
                selected, preview = self.pending_image
                selected["path"] = temp_path
                preview.source = temp_path
                preview.reload()

        except Exception as error:
            self.log_error(
                "ACTIVITY_RESULT_IMAGE",
                error
            )
        finally:
            self.pending_image = None

            try:
                from android.activity import unbind
                if self._activity_callback is not None:
                    unbind(
                        on_activity_result=self._activity_callback
                    )
            except Exception:
                pass

            self._activity_callback = None

    def copy_content_uri(self, uri):
        input_stream = None
        output_stream = None

        try:
            from jnius import autoclass, jarray

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )
            resolver = (
                PythonActivity.mActivity
                .getContentResolver()
            )

            input_stream = resolver.openInputStream(uri)
            if input_stream is None:
                raise RuntimeError(
                    "Content URI tidak dapat dibaca."
                )

            mime = None
            try:
                mime_value = resolver.getType(uri)
                if mime_value:
                    mime = str(mime_value)
            except Exception:
                pass

            extensions = {
                "image/jpeg": ".jpg",
                "image/jpg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
                "image/gif": ".gif"
            }
            extension = extensions.get(mime, ".jpg")

            filename = (
                "product_" +
                datetime.now().strftime("%Y%m%d%H%M%S%f") +
                extension
            )
            target = os.path.join(
                self.images_dir,
                filename
            )

            FileOutputStream = autoclass(
                "java.io.FileOutputStream"
            )
            output_stream = FileOutputStream(target)

            buffer = jarray("b", [0] * 8192)

            while True:
                count = input_stream.read(buffer)
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

    def open_desktop_picker(self, selected, preview):
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

            root = BoxLayout(
                orientation="vertical"
            )
            root.add_widget(chooser)

            row = BoxLayout(
                size_hint_y=None,
                height=dp(46)
            )
            select_btn = make_button(
                "Pilih",
                primary=True,
                height=46
            )
            cancel_btn = make_button(
                "Batal",
                height=46
            )
            row.add_widget(select_btn)
            row.add_widget(cancel_btn)
            root.add_widget(row)

            popup = Popup(
                title="Pilih Foto Produk",
                content=root,
                size_hint=(0.94, 0.88)
            )

            def choose(*_):
                if not chooser.selection:
                    self.notify("Pilih foto terlebih dahulu.")
                    return

                selected["path"] = chooser.selection[0]
                preview.source = selected["path"]
                preview.reload()
                popup.dismiss()

            select_btn.bind(on_release=choose)
            cancel_btn.bind(on_release=popup.dismiss)
            popup.open()

        except Exception as error:
            self.log_error(
                "DESKTOP_IMAGE_PICKER",
                error
            )

    def save_selected_image(self, path):
        if not path:
            return ""

        try:
            source = os.path.abspath(path)

            if not os.path.isfile(source):
                return ""

            images_dir = os.path.abspath(self.images_dir)

            # Jika sudah berada di folder internal aplikasi,
            # jangan copy ulang.
            if source == images_dir or source.startswith(
                images_dir + os.sep
            ):
                return source

            extension = os.path.splitext(source)[1].lower()
            if extension not in (
                ".jpg", ".jpeg", ".png", ".webp", ".gif"
            ):
                extension = ".jpg"

            destination = os.path.join(
                images_dir,
                "product_" +
                datetime.now().strftime("%Y%m%d%H%M%S%f") +
                extension
            )

            shutil.copy2(source, destination)

            if not os.path.isfile(destination):
                return ""

            return destination

        except Exception as error:
            self.log_error(
                "SAVE_SELECTED_IMAGE",
                error
            )
            return ""

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
            # Tidak dianggap fatal. Beberapa versi python-for-android
            # tidak menyediakan API ini.
            pass

    # --------------------------------------------------------
    # PRINT
    # --------------------------------------------------------

    def print_or_offer(self, invoice):
        content = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=dp(10)
        )

        content.add_widget(text_label(
            f"Transaksi {invoice} berhasil.\n"
            "Cetak struk sekarang?",
            size=15,
            halign="center"
        ))

        row = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(7)
        )
        bluetooth = make_button(
            "Bluetooth",
            primary=True,
            height=46
        )
        no_print = make_button(
            "Tidak",
            height=46
        )
        row.add_widget(bluetooth)
        row.add_widget(no_print)
        content.add_widget(row)

        popup = Popup(
            title="Struk",
            content=content,
            size_hint=(0.88, 0.40)
        )

        bluetooth.bind(
            on_release=lambda *_: (
                popup.dismiss(),
                self.bluetooth_printer_dialog()
            )
        )
        no_print.bind(on_release=popup.dismiss)
        popup.open()

    def bluetooth_printer_dialog(self):
        devices = self.get_bonded_devices()

        if not devices:
            self.notify(
                "Tidak ada printer Bluetooth yang sudah dipairing."
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
            size_hint=(0.92, 0.80)
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
            adapter = BluetoothAdapter.getDefaultAdapter()

            if adapter is None:
                return []

            result = []
            devices = adapter.getBondedDevices().toArray()

            for device in devices:
                try:
                    result.append((
                        str(device.getName() or "Bluetooth Device"),
                        str(device.getAddress())
                    ))
                except Exception:
                    pass

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

            adapter = BluetoothAdapter.getDefaultAdapter()
            if adapter is None:
                raise RuntimeError(
                    "Bluetooth tidak tersedia."
                )

            device = adapter.getRemoteDevice(address)

            uuid = UUID.fromString(
                "00001101-0000-1000-8000-00805F9B34FB"
            )

            socket = device.createRfcommSocketToServiceRecord(
                uuid
            )

            try:
                adapter.cancelDiscovery()
            except Exception:
                pass

            socket.connect()

            output = socket.getOutputStream()
            output.write(self.build_receipt_bytes())
            output.flush()

            self.notify("Struk berhasil dikirim.")

        except Exception as error:
            self.log_error(
                "BLUETOOTH_PRINT",
                error
            )
            self.notify(
                "Gagal mencetak:\n" + str(error)
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

        paper = self.db.setting("paper") or "58mm"
        width = 32 if paper == "58mm" else 48

        store = self.db.setting("store_name") or APP_NAME
        address = self.db.setting("store_address") or ""
        footer = self.db.setting("receipt_footer") or "Terima kasih"

        lines = [
            store.center(width),
            address.center(width),
            "-" * width,
            invoice,
            datetime.now().strftime("%d/%m/%Y %H:%M").center(width),
            "-" * width
        ]

        for item in cart:
            name = str(item["name"])[:width]
            lines.append(name)
            lines.append(
                "  "
                f'{item["qty"]:g} x {money(item["price"])}'
                " = "
                f'{money(item["qty"] * item["price"])}'
            )

        lines.extend([
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
        ])

        raw = "\n".join(lines).encode(
            "utf-8", "replace"
        )

        return (
            b"\x1b\x40" +
            b"\x1b\x45\x01" +
            raw +
            b"\x1b\x45\x00" +
            b"\n\n\n" +
            b"\x1d\x56\x00"
        )


if __name__ == "__main__":
    UniversalPOS().run()
