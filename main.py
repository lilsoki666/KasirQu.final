import os
import csv
import shutil
import sqlite3
import traceback
import unicodedata

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from kivy.app import App
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
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
from kivy.uix.anchorlayout import AnchorLayout
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.clock import Clock
from kivy.utils import platform


# ============================================================
# KASIRQU
# 2.0 PROFESSIONAL POS UPGRADE
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
    """Normalisasi teks struk ke ASCII agar printer ESC/POS tidak mencetak mojibake."""
    try:
        s = safe_text(value)
        replacements = {"×":"x", "•":"-", "·":"-", "–":"-", "—":"-", "…":"...", "“":'"', "”":'"', "‘":"'", "’":"'"}
        for src, dst in replacements.items():
            s = s.replace(src, dst)
        s = unicodedata.normalize("NFKD", s)
        return s.encode("ascii", "ignore").decode("ascii")
    except Exception:
        return ""


def printer_bytes(value):
    return printer_text(value).encode("ascii", "replace")


# ============================================================
# CARD
# ============================================================

class Card(BoxLayout):

    radius = NumericProperty(dp(14))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            self._fill_color = Color(*WHITE)
            self._rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[self.radius]
            )
            self._border_color = Color(*BORDER)
            from kivy.graphics import Line
            self._border = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, self.radius),
                width=0.8
            )

        self.bind(
            pos=self._update_rect,
            size=self._update_rect
        )

    def _update_rect(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._border.rounded_rectangle = (self.x, self.y, self.width, self.height, self.radius)


class OutlinedInput(TextInput):
    """Text input clean dengan border tipis dan indikator fokus."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_active = ""
        self.background_color = WHITE
        self.foreground_color = TEXT
        self.cursor_color = PRIMARY
        with self.canvas.after:
            self._border_color = Color(*BORDER)
            self._border = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(6)),
                width=1.0
            )
        self.bind(pos=self._update_border, size=self._update_border, focus=self._update_border_color)

    def _update_border(self, *_):
        self._border.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(6))

    def _update_border_color(self, *_):
        self._border_color.rgba = PRIMARY if self.focus else BORDER


class IconActionButton(Button):
    """Tombol ikon kecil untuk aksi + dan hapus tanpa ketergantungan font emoji."""
    icon_type = StringProperty("plus")
    danger = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.size_hint_y = None
        self.height = dp(38)
        self.size_hint_x = None
        self.width = dp(44)
        with self.canvas.before:
            self._bg_color = Color(*PRIMARY)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        with self.canvas.after:
            self._icon_color = Color(*WHITE)
            from kivy.graphics import Line
            self._icon_a = Line(points=[], width=1.7)
            self._icon_b = Line(points=[], width=1.7)
            self._icon_c = Line(points=[], width=1.7)
        self.bind(pos=self._update_icon, size=self._update_icon, icon_type=self._update_icon,
                  danger=self._update_icon, state=self._update_icon)
        self._update_icon()

    def _update_icon(self, *_):
        pressed = self.state == "down"
        base = DANGER if self.danger else PRIMARY
        if pressed:
            base = (max(0, base[0]-0.04), max(0, base[1]-0.04), max(0, base[2]-0.04), 1)
        self._bg_color.rgba = base
        self._bg.pos = self.pos
        self._bg.size = self.size
        cx, cy = self.center
        if self.icon_type == "trash":
            self._icon_a.points = [cx-dp(8), cy+dp(7), cx+dp(8), cy+dp(7)]
            self._icon_b.points = [cx-dp(6), cy+dp(5), cx-dp(5), cy-dp(7), cx+dp(5), cy-dp(7), cx+dp(6), cy+dp(5)]
            self._icon_c.points = [cx-dp(3), cy+dp(10), cx+dp(3), cy+dp(10)]
        else:
            self._icon_a.points = [cx-dp(8), cy, cx+dp(8), cy]
            self._icon_b.points = [cx, cy-dp(8), cx, cy+dp(8)]
            self._icon_c.points = []


class PillLabel(Label):
    """Label kecil berbentuk badge untuk status/stok."""
    bg_color = StringProperty("success")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(28)
        self.padding = [dp(8), 0]
        with self.canvas.before:
            self._bg_color = Color(*SUCCESS)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._update_bg, size=self._update_bg)
        self.bind(bg_color=self._update_color)
        self._update_color()

    def _update_bg(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _update_color(self, *_):
        self._bg_color.rgba = DANGER if self.bg_color == "danger" else SUCCESS


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

class IconNavButton(BoxLayout):
    """Navigasi bawah minimalis tanpa ikon.

    Nama class dipertahankan agar tidak mengganggu referensi KV lama,
    tetapi toolbar sekarang hanya menampilkan teks dan garis indikator
    tipis di bagian atas item aktif.
    """

    nav_name = StringProperty("")
    label_text = StringProperty("")
    icon_path = StringProperty("")
    is_active = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.spacing = 0
        self.size_hint_y = None
        self.height = dp(58)
        self.padding = [dp(4), 0, dp(4), 0]
        self.size_hint_x = 1
        self._touch_start = None

        self.label = Label(
            text="",
            font_size="12sp",
            bold=True,
            color=MUTED,
            size_hint=(1, 1),
            halign="center",
            valign="middle"
        )
        self.label.bind(size=lambda w, v: setattr(w, "text_size", v))
        self.add_widget(self.label)

        with self.canvas.before:
            self._active_color = Color(0.12, 0.32, 0.78, 0)
            from kivy.graphics import Rectangle
            self._active_line = Rectangle(
                pos=(self.x, self.top - dp(3)),
                size=(self.width, dp(3))
            )

        self.bind(pos=self._update_line, size=self._update_line)
        self.bind(label_text=self._sync_label_text, is_active=self._sync_active)
        Clock.schedule_once(self._sync_widgets, 0)

    def _sync_label_text(self, *_):
        self.label.text = self.label_text

    def _sync_widgets(self, *_):
        self._sync_label_text()
        self._update_line()
        self._sync_active()

    def _update_line(self, *_):
        self._active_line.pos = (self.x, self.top - dp(3))
        self._active_line.size = (self.width, dp(3))

    def _sync_active(self, *_):
        self._active_line.pos = (self.x, self.top - dp(3))
        self._active_line.size = (self.width, dp(3))
        self._active_color.a = 1 if self.is_active else 0
        self.label.color = PRIMARY if self.is_active else MUTED

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._touch_start = touch.pos
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self._touch_start is not None:
            start = self._touch_start
            self._touch_start = None
            dx = touch.x - start[0]
            dy = touch.y - start[1]
            if abs(dx) < dp(20) and abs(dy) < dp(20) and self.collide_point(*touch.pos):
                try:
                    App.get_running_app().navigate(self.nav_name)
                except Exception as error:
                    try:
                        App.get_running_app().log_error("NAV_TOUCH", error)
                    except Exception:
                        pass
            return True
        return super().on_touch_up(touch)


# ============================================================
# SWIPE MANAGER
# ============================================================

class SwipeManager(ScreenManager):
    """Screen manager dengan swipe hanya untuk 3 halaman utama."""

    MAIN_SCREENS = ["pos", "products", "settings"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._touch_start = None

    def on_touch_down(self, touch):
        self._touch_start = touch.pos
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        start = self._touch_start
        result = super().on_touch_up(touch)

        if start is not None and self.current in self.MAIN_SCREENS:
            dx = touch.x - start[0]
            dy = touch.y - start[1]
            if abs(dx) > dp(70) and abs(dx) > abs(dy) * 1.3:
                self.swipe(-1 if dx > 0 else 1)

        self._touch_start = None
        return result

    def swipe(self, delta):
        names = self.MAIN_SCREENS
        if self.current not in names:
            return
        index = names.index(self.current)
        target = index + delta
        if target < 0 or target >= len(names):
            return
        self.transition = SlideTransition(
            direction="right" if delta < 0 else "left", duration=.20
        )
        self.current = names[target]
        try:
            App.get_running_app().refresh_nav_highlight()
        except Exception:
            pass


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


<OutlineButton@Button>:
    background_normal: ""
    background_down: ""
    background_color: (0,0,0,0)
    color: (.12,.32,.78,1)
    bold: True
    font_size: "12sp"
    size_hint_y: None
    height: dp(44)
    canvas.before:
        Color:
            rgba: (.12,.32,.78,1) if self.state != "down" else (.08,.24,.62,1)
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, dp(8))
            width: 1.0


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
        spacing: 0
        canvas.before:
            Color:
                rgba: (.95,.97,.99,1)
            Rectangle:
                pos: self.pos
                size: self.size

        BoxLayout:
            size_hint_y: None
            height: dp(60)
            padding: [dp(16), 0, dp(12), 0]
            canvas.before:
                Color:
                    rgba: (.10,.31,.76,1)
                Rectangle:
                    pos: self.pos
                    size: self.size
            Label:
                text: app.db.setting("store_name") or "KasirQU"
                color: 1,1,1,1
                font_size: "18sp"
                bold: True
                halign: "left"
                valign: "middle"
                text_size: self.size
            Label:
                text: "KASIR"
                color: (1,1,1,.82)
                font_size: "11sp"
                bold: True
                size_hint_x: None
                width: dp(60)
                halign: "right"
                valign: "middle"
                text_size: self.size

        BoxLayout:
            orientation: "vertical"
            padding: [dp(12), dp(10), dp(12), dp(8)]
            spacing: dp(8)

            BoxLayout:
                size_hint_y: None
                height: dp(42)
                Label:
                    text: "Kasir"
                    color: (.08,.11,.16,1)
                    font_size: "22sp"
                    bold: True
                    halign: "left"
                    valign: "middle"
                    text_size: self.size
                Label:
                    text: ""

            BoxLayout:
                size_hint_y: None
                height: dp(46)
                spacing: dp(7)
                TextInput:
                    id: search
                    hint_text: "Cari produk / scan barcode..."
                    multiline: False
                    padding: [dp(12), dp(10)]
                    background_normal: ""
                    background_color: 1,1,1,1
                    foreground_color: (.08,.11,.16,1)
                    cursor_color: (.12,.32,.78,1)
                    on_text: root.refresh_products(self.text)
                    on_text_validate: root.quick_add_by_code(self.text)
                PrimaryButton:
                    text: "+"
                    size_hint_x: None
                    width: dp(46)
                    on_release: root.open_cart_popup()

            Label:
                text: "Pilih Produk"
                color: (.40,.44,.51,1)
                font_size: "13sp"
                bold: True
                size_hint_y: None
                height: dp(22)
                halign: "left"
                text_size: self.size

            ScrollView:
                do_scroll_x: False
                bar_width: dp(3)
                GridLayout:
                    id: products
                    cols: 4
                    spacing: dp(8)
                    padding: dp(1)
                    size_hint_y: None
                    height: self.minimum_height

            Card:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(64)
                padding: dp(8)
                spacing: dp(8)
                Label:
                    id: cart_count
                    text: "0 item"
                    color: (.08,.11,.16,1)
                    bold: True
                    size_hint_x: .30
                    halign: "left"
                    valign: "middle"
                    text_size: self.size
                Label:
                    id: cart_total
                    text: "Rp 0"
                    color: (.12,.32,.78,1)
                    font_size: "18sp"
                    bold: True
                    size_hint_x: .40
                    halign: "right"
                    valign: "middle"
                    text_size: self.size
                PrimaryButton:
                    text: "KERANJANG"
                    size_hint_x: .30
                    on_release: root.open_cart_popup()


<ProductScreen>:
    BoxLayout:
        orientation: "vertical"
        spacing: 0
        canvas.before:
            Color:
                rgba: (.95,.97,.99,1)
            Rectangle:
                pos: self.pos
                size: self.size

        BoxLayout:
            size_hint_y: None
            height: dp(60)
            padding: [dp(16), 0, dp(12), 0]
            canvas.before:
                Color:
                    rgba: (.10,.31,.76,1)
                Rectangle:
                    pos: self.pos
                    size: self.size
            Label:
                text: app.db.setting("store_name") or "KasirQU"
                color: 1,1,1,1
                font_size: "18sp"
                bold: True
                halign: "left"
                valign: "middle"
                text_size: self.size
            Label:
                text: "PRODUK"
                color: (1,1,1,.82)
                font_size: "11sp"
                bold: True
                size_hint_x: None
                width: dp(64)
                halign: "right"
                valign: "middle"
                text_size: self.size

        BoxLayout:
            orientation: "vertical"
            padding: [dp(12), dp(9), dp(12), dp(8)]
            spacing: dp(8)

            BoxLayout:
                size_hint_y: None
                height: dp(42)
                Label:
                    id: count
                    text: "Produk (0 Item)"
                    color: (.08,.11,.16,1)
                    font_size: "21sp"
                    bold: True
                    halign: "left"
                    valign: "middle"
                    text_size: self.size
                PrimaryButton:
                    text: "Tambah +"
                    size_hint_x: None
                    width: dp(112)
                    on_release: root.open_editor()

            BoxLayout:
                size_hint_y: None
                height: dp(44)
                spacing: dp(7)
                TextInput:
                    id: search
                    hint_text: "Cari produk, SKU, kategori..."
                    multiline: False
                    padding: [dp(12), dp(9)]
                    background_normal: ""
                    background_color: (1,1,1,1)
                    foreground_color: (.08,.11,.16,1)
                    cursor_color: (.12,.32,.78,1)
                    on_text: root.refresh(self.text, root.category_filter)
                SoftButton:
                    text: "FILTER"
                    size_hint_x: None
                    width: dp(82)
                    on_release: root.toggle_categories()

            ScrollView:
                size_hint_y: None
                height: dp(38)
                do_scroll_y: False
                bar_width: 0
                GridLayout:
                    id: categories
                    rows: 1
                    spacing: dp(6)
                    size_hint_x: None
                    width: self.minimum_width
                    size_hint_y: None
                    height: dp(34)

            ScrollView:
                do_scroll_x: False
                bar_width: dp(3)
                GridLayout:
                    id: list
                    cols: 1
                    spacing: dp(8)
                    padding: dp(1)
                    size_hint_y: None
                    height: self.minimum_height


<TransactionScreen>:
    BoxLayout:
        orientation: "vertical"
        spacing: 0
        canvas.before:
            Color:
                rgba: (.95,.97,.99,1)
            Rectangle:
                pos: self.pos
                size: self.size

        BoxLayout:
            size_hint_y: None
            height: dp(60)
            padding: [dp(16), 0, dp(12), 0]
            canvas.before:
                Color:
                    rgba: (.10,.31,.76,1)
                Rectangle:
                    pos: self.pos
                    size: self.size
            Label:
                text: app.db.setting("store_name") or "KasirQU"
                color: 1,1,1,1
                font_size: "18sp"
                bold: True
                halign: "left"
                valign: "middle"
                text_size: self.size
            Label:
                text: "TRANSAKSI"
                color: (1,1,1,.82)
                font_size: "11sp"
                bold: True
                size_hint_x: None
                width: dp(82)
                halign: "right"
                valign: "middle"
                text_size: self.size

        BoxLayout:
            orientation: "vertical"
            padding: [dp(12), dp(9), dp(12), dp(8)]
            spacing: dp(8)

            BoxLayout:
                size_hint_y: None
                height: dp(42)
                Label:
                    id: count
                    text: "Transaksi (0)"
                    color: (.08,.11,.16,1)
                    font_size: "21sp"
                    bold: True
                    halign: "left"
                    valign: "middle"
                    text_size: self.size
                PrimaryButton:
                    text: "+ Buat Transaksi"
                    size_hint_x: None
                    width: dp(142)
                    on_release: app.navigate("pos")

            BoxLayout:
                size_hint_y: None
                height: dp(44)
                spacing: dp(7)
                TextInput:
                    id: search
                    hint_text: "Cari invoice / pembayaran..."
                    multiline: False
                    padding: [dp(12), dp(9)]
                    background_normal: ""
                    background_color: (1,1,1,1)
                    foreground_color: (.08,.11,.16,1)
                    cursor_color: (.12,.32,.78,1)
                    on_text: root.refresh(self.text)
                SoftButton:
                    text: "FILTER"
                    size_hint_x: None
                    width: dp(82)
                    on_release: root.refresh(self.ids.search.text)

            ScrollView:
                do_scroll_x: False
                bar_width: dp(3)
                GridLayout:
                    id: list
                    cols: 1
                    spacing: dp(8)
                    padding: dp(1)
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
        canvas.before:
            Color:
                rgba: (.95,.97,.99,1)
            Rectangle:
                pos: self.pos
                size: self.size

        # PROFESSIONAL APP BAR
        BoxLayout:
            size_hint_y: None
            height: dp(60)
            padding: [dp(14), 0, dp(14), 0]
            spacing: dp(8)
            canvas.before:
                Color:
                    rgba: (.10,.31,.76,1)
                Rectangle:
                    pos: self.pos
                    size: self.size
            Label:
                text: app.db.setting("store_name") or "KasirQU"
                color: 1,1,1,1
                font_size: "17sp"
                bold: True
                halign: "left"
                valign: "middle"
                text_size: self.size
            Label:
                text: "PENGATURAN"
                color: 1,1,1,1
                font_size: "15sp"
                bold: True
                halign: "center"
                valign: "middle"
                text_size: self.size
            Widget:
                size_hint_x: .45

        ScrollView:
            do_scroll_x: False
            bar_width: dp(3)
            BoxLayout:
                orientation: "vertical"
                spacing: dp(10)
                padding: [dp(10), dp(10), dp(10), dp(14)]
                size_hint_y: None
                height: self.minimum_height

                # MENU LAINNYA
                Card:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(112)
                    padding: dp(12)
                    spacing: dp(8)
                    Label:
                        text: "MENU LAINNYA"
                        color: (.40,.44,.51,1)
                        bold: True
                        font_size: "12sp"
                        size_hint_y: None
                        height: dp(20)
                        halign: "left"
                        text_size: self.size
                    BoxLayout:
                        size_hint_y: None
                        height: dp(48)
                        spacing: dp(8)
                        OutlineButton:
                            text: "RIWAYAT TRANSAKSI   ›"
                            on_release: root.open_transactions()
                        OutlineButton:
                            text: "LAPORAN   ›"
                            on_release: root.open_reports()

                # TOKO & STRUK
                Card:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(270)
                    padding: dp(12)
                    spacing: dp(7)
                    Label:
                        text: "TOKO & STRUK"
                        color: (.40,.44,.51,1)
                        bold: True
                        font_size: "12sp"
                        size_hint_y: None
                        height: dp(20)
                        halign: "left"
                        text_size: self.size
                    OutlinedInput:
                        id: store
                        hint_text: "Nama toko"
                        multiline: False
                        size_hint_y: None
                        height: dp(42)
                        padding: [dp(12),dp(9)]
                    OutlinedInput:
                        id: address
                        hint_text: "Alamat / kontak"
                        multiline: False
                        size_hint_y: None
                        height: dp(42)
                        padding: [dp(12),dp(9)]
                    OutlinedInput:
                        id: footer
                        hint_text: "Footer struk"
                        multiline: False
                        size_hint_y: None
                        height: dp(42)
                        padding: [dp(12),dp(9)]
                    BoxLayout:
                        size_hint_y: None
                        height: dp(92)
                        spacing: dp(9)
                        Card:
                            size_hint_x: None
                            width: dp(82)
                            padding: dp(5)
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
                                color: (.40,.44,.51,1)
                                font_size: "10sp"
                                halign: "left"
                                valign: "middle"
                                text_size: self.size
                            BoxLayout:
                                size_hint_y: None
                                height: dp(38)
                                spacing: dp(7)
                                PrimaryButton:
                                    text: "+ PILIH LOGO"
                                    on_release: root.choose_receipt_logo()
                                IconActionButton:
                                    icon_type: "trash"
                                    danger: True
                                    on_release: root.remove_receipt_logo()

                # PEMBAYARAN
                Card:
                    orientation: "vertical"
                    size_hint_y: None
                    height: self.minimum_height
                    padding: dp(12)
                    spacing: dp(8)
                    Label:
                        text: "PEMBAYARAN"
                        color: (.40,.44,.51,1)
                        bold: True
                        font_size: "12sp"
                        size_hint_y: None
                        height: dp(20)
                        halign: "left"
                        text_size: self.size

                    # QRIS CARD
                    Card:
                        orientation: "vertical"
                        size_hint_y: None
                        height: dp(205)
                        padding: dp(10)
                        spacing: dp(7)
                        Label:
                            text: "QRIS"
                            color: (.08,.11,.16,1)
                            bold: True
                            font_size: "12sp"
                            size_hint_y: None
                            height: dp(18)
                            halign: "left"
                            text_size: self.size
                        BoxLayout:
                            size_hint_y: None
                            height: dp(112)
                            spacing: dp(10)
                            Card:
                                size_hint_x: None
                                width: dp(112)
                                padding: dp(5)
                                Image:
                                    id: qris_preview
                                    source: ""
                                    allow_stretch: True
                                    keep_ratio: True
                            BoxLayout:
                                orientation: "vertical"
                                spacing: dp(4)
                                Label:
                                    id: qris_status
                                    text: "QRIS: belum dipasang"
                                    color: (.08,.55,.30,1)
                                    bold: True
                                    font_size: "11sp"
                                    size_hint_y: None
                                    height: dp(20)
                                    halign: "left"
                                    text_size: self.size
                                Label:
                                    text: "QRIS digunakan pada pembayaran dan konfirmasi pesanan."
                                    color: (.40,.44,.51,1)
                                    font_size: "10sp"
                                    size_hint_y: None
                                    height: dp(32)
                                    halign: "left"
                                    valign: "middle"
                                    text_size: self.size
                                BoxLayout:
                                    size_hint_y: None
                                    height: dp(38)
                                    spacing: dp(7)
                                    PrimaryButton:
                                        text: "+ PILIH QRIS"
                                        on_release: root.choose_qris()
                                    IconActionButton:
                                        icon_type: "trash"
                                        danger: True
                                        on_release: root.remove_qris()
                        OutlinedInput:
                            id: qris_instruction
                            hint_text: "Instruksi QRIS"
                            multiline: False
                            size_hint_y: None
                            height: dp(40)
                            padding: [dp(10),dp(8)]

                    # BANK
                    BoxLayout:
                        size_hint_y: None
                        height: dp(38)
                        spacing: dp(8)
                        Label:
                            text: "TRANSFER BANK"
                            color: (.08,.11,.16,1)
                            bold: True
                            font_size: "12sp"
                            halign: "left"
                            valign: "middle"
                            text_size: self.size
                        PrimaryButton:
                            text: "+ TAMBAH REKENING"
                            size_hint_x: None
                            width: dp(164)
                            height: dp(36)
                            on_release: root.add_bank_account()
                    GridLayout:
                        id: bank_accounts
                        cols: 1
                        spacing: dp(5)
                        size_hint_y: None
                        height: self.minimum_height

                    # E-WALLET
                    BoxLayout:
                        size_hint_y: None
                        height: dp(38)
                        spacing: dp(8)
                        Label:
                            text: "E-WALLET"
                            color: (.08,.11,.16,1)
                            bold: True
                            font_size: "12sp"
                            halign: "left"
                            valign: "middle"
                            text_size: self.size
                        PrimaryButton:
                            text: "+ TAMBAH E-WALLET"
                            size_hint_x: None
                            width: dp(164)
                            height: dp(36)
                            on_release: root.add_wallet_account()
                    GridLayout:
                        id: wallet_accounts
                        cols: 1
                        spacing: dp(5)
                        size_hint_y: None
                        height: self.minimum_height

                # OPERASIONAL
                Card:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(212)
                    padding: dp(12)
                    spacing: dp(7)
                    Label:
                        text: "OPERASIONAL"
                        color: (.40,.44,.51,1)
                        bold: True
                        font_size: "12sp"
                        size_hint_y: None
                        height: dp(20)
                        halign: "left"
                        text_size: self.size
                    BoxLayout:
                        size_hint_y: None
                        height: dp(42)
                        spacing: dp(8)
                        OutlinedInput:
                            id: cashier
                            hint_text: "Nama kasir"
                            multiline: False
                            padding: [dp(12),dp(9)]
                        Spinner:
                            id: role
                            text: "Owner"
                            values: ["Owner","Admin","Kasir"]
                            size_hint_x: None
                            width: dp(120)
                    BoxLayout:
                        size_hint_y: None
                        height: dp(42)
                        spacing: dp(8)
                        OutlinedInput:
                            id: tax
                            hint_text: "Pajak (%)"
                            input_filter: "float"
                            multiline: False
                            padding: [dp(10),dp(9)]
                        OutlinedInput:
                            id: low_stock
                            hint_text: "Batas stok menipis"
                            input_filter: "float"
                            multiline: False
                            padding: [dp(10),dp(9)]
                    BoxLayout:
                        size_hint_y: None
                        height: dp(42)
                        spacing: dp(8)
                        Spinner:
                            id: paper
                            text: "58mm"
                            values: ["58mm", "80mm"]
                            size_hint_x: None
                            width: dp(120)
                        PrimaryButton:
                            text: "SIMPAN PENGATURAN"
                            on_release: root.save()
                        SoftButton:
                            text: "REFRESH"
                            on_release: root.on_enter()

                # PRINTER
                Card:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(174)
                    padding: dp(12)
                    spacing: dp(7)
                    Label:
                        text: "PRINTER BLUETOOTH"
                        color: (.40,.44,.51,1)
                        bold: True
                        font_size: "12sp"
                        size_hint_y: None
                        height: dp(20)
                        halign: "left"
                        text_size: self.size
                    Label:
                        id: printer_status
                        text: "Printer: belum dipilih"
                        color: (.08,.11,.16,1)
                        size_hint_y: None
                        height: dp(28)
                        halign: "left"
                        valign: "middle"
                        text_size: self.size
                    BoxLayout:
                        size_hint_y: None
                        height: dp(42)
                        spacing: dp(8)
                        PrimaryButton:
                            text: "PILIH PRINTER"
                            on_release: root.open_printer()
                        SoftButton:
                            text: "TEST PRINT"
                            on_release: root.test_printer()
                    Label:
                        text: "Printer dipilih sekali untuk transaksi dan cetak ulang."
                        color: (.40,.44,.51,1)
                        font_size: "10sp"
                        size_hint_y: None
                        height: dp(28)
                        halign: "left"
                        valign: "middle"
                        text_size: self.size

                # DATA
                Card:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(132)
                    padding: dp(12)
                    spacing: dp(7)
                    Label:
                        text: "DATA & KEAMANAN"
                        color: (.40,.44,.51,1)
                        bold: True
                        font_size: "12sp"
                        size_hint_y: None
                        height: dp(20)
                        halign: "left"
                        text_size: self.size
                    BoxLayout:
                        size_hint_y: None
                        height: dp(42)
                        spacing: dp(8)
                        SoftButton:
                            text: "BACKUP DATABASE"
                            on_release: root.backup()
                        SoftButton:
                            text: "CEK DATABASE"
                            on_release: root.check_database()

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

        height: dp(60)

        padding: [dp(8), 0, dp(8), 0]

        spacing: dp(4)

        canvas.before:

            Color:

                rgba: (1,1,1,1)

            Rectangle:

                pos: self.pos

                size: self.size


        IconNavButton:

            nav_name: "pos"

            label_text: "Kasir"

        IconNavButton:

            nav_name: "products"

            label_text: "Produk"

        IconNavButton:

            nav_name: "settings"

            label_text: "Pengaturan"
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

            CREATE TABLE IF NOT EXISTS payment_accounts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_type TEXT NOT NULL DEFAULT 'bank',
                provider TEXT NOT NULL DEFAULT '',
                account_number TEXT NOT NULL DEFAULT '',
                account_name TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT ''
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
            "receipt_logo": "",
            "qris_image": "",
            "qris_instruction": "Scan QRIS lalu lakukan pembayaran sesuai total."
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
                    created_at,
                    cashier,
                    role
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
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
                    now,
                    self.setting("cashier_name") or "Kasir",
                    self.setting("user_role") or "Owner"
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
                    (qty, item["id"])
                )
                cursor.execute(
                    "INSERT INTO stock_movements(product_id,qty,movement_type,note,created_at) VALUES(?,?,?,?,?)",
                    (item["id"], -qty, "SALE", invoice, now)
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

    def delete_product(self, product_id):
        self.conn.execute(
            "UPDATE products SET active=0 WHERE id=?",
            (product_id,)
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

    def product_by_code(self, code):
        code = safe_text(code).strip()
        if not code:
            return None
        return self.conn.execute(
            "SELECT * FROM products WHERE active=1 AND (sku=? OR name=?) LIMIT 1",
            (code, code)
        ).fetchone()

    def low_stock_products(self):
        threshold = safe_float(self.setting("low_stock_threshold"), 5)
        return self.conn.execute(
            "SELECT * FROM products WHERE active=1 AND stock<=? ORDER BY stock ASC, name COLLATE NOCASE",
            (threshold,)
        ).fetchall()

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
            cur.execute(
                "INSERT INTO stock_movements(product_id,qty,movement_type,note,created_at) VALUES(?,?,?,?,?)",
                (product_id, qty, "RESTOCK", note, now)
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback(); raise

    def stock_history(self, product_id, limit=50):
        return self.conn.execute(
            "SELECT * FROM stock_movements WHERE product_id=? ORDER BY id DESC LIMIT ?",
            (product_id, limit)
        ).fetchall()

    def void_sale(self, sale_id, reason="Dibatalkan"):
        sale = self.sale(sale_id)
        if not sale:
            raise ValueError("Transaksi tidak ditemukan.")
        try:
            if "voided" in sale.keys() and int(sale["voided"] or 0):
                raise ValueError("Transaksi sudah dibatalkan.")
        except Exception:
            pass
        cur = self.conn.cursor()
        try:
            self.conn.execute("BEGIN")
            items = cur.execute("SELECT * FROM sale_items WHERE sale_id=?", (sale_id,)).fetchall()
            for item in items:
                if item["product_id"]:
                    cur.execute("UPDATE products SET stock=stock+? WHERE id=?", (float(item["qty"]), item["product_id"]))
                    cur.execute(
                        "INSERT INTO stock_movements(product_id,qty,movement_type,note,created_at) VALUES(?,?,?,?,?)",
                        (item["product_id"], float(item["qty"]), "VOID", f"Void {sale['invoice']}", datetime.now().isoformat(timespec="seconds"))
                    )
            cur.execute("UPDATE sales SET voided=1, void_reason=? WHERE id=?", (reason, sale_id))
            self.conn.commit()
        except Exception:
            self.conn.rollback(); raise

    def dashboard(self):
        today = self.conn.execute(
            """SELECT COUNT(*) n, COALESCE(SUM(total),0) total, COALESCE(SUM(discount),0) discount
               FROM sales WHERE date(created_at)=date('now') AND COALESCE(voided,0)=0"""
        ).fetchone()
        items = self.conn.execute(
            """SELECT COALESCE(SUM(si.qty),0) qty, COALESCE(SUM((si.price-COALESCE(p.cost,0))*si.qty),0) profit
               FROM sale_items si JOIN sales s ON s.id=si.sale_id
               LEFT JOIN products p ON p.id=si.product_id
               WHERE date(s.created_at)=date('now') AND COALESCE(s.voided,0)=0"""
        ).fetchone()
        top = self.conn.execute(
            """SELECT si.name, SUM(si.qty) qty FROM sale_items si JOIN sales s ON s.id=si.sale_id
               WHERE COALESCE(s.voided,0)=0 GROUP BY si.name ORDER BY qty DESC LIMIT 5"""
        ).fetchall()
        return today, items, top

    # --------------------------------------------------------
    # PAYMENT ACCOUNTS
    # --------------------------------------------------------

    def payment_accounts(self, account_type=""):
        if account_type:
            return self.conn.execute(
                "SELECT * FROM payment_accounts WHERE active=1 AND account_type=? ORDER BY provider COLLATE NOCASE, id",
                (account_type,)
            ).fetchall()
        return self.conn.execute(
            "SELECT * FROM payment_accounts WHERE active=1 ORDER BY account_type, provider COLLATE NOCASE, id"
        ).fetchall()

    def add_payment_account(self, account_type, provider, account_number, account_name):
        self.conn.execute(
            "INSERT INTO payment_accounts(account_type,provider,account_number,account_name,active,created_at) VALUES(?,?,?,?,1,?)",
            (account_type, provider.strip(), account_number.strip(), account_name.strip(), datetime.now().isoformat(timespec="seconds"))
        )
        self.conn.commit()

    def update_payment_account(self, account_id, account_type, provider, account_number, account_name):
        self.conn.execute(
            "UPDATE payment_accounts SET account_type=?, provider=?, account_number=?, account_name=? WHERE id=?",
            (account_type, provider.strip(), account_number.strip(), account_name.strip(), account_id)
        )
        self.conn.commit()

    def delete_payment_account(self, account_id):
        self.conn.execute("UPDATE payment_accounts SET active=0 WHERE id=?", (account_id,))
        self.conn.commit()

    def integrity_check(self):
        row = self.conn.execute("PRAGMA integrity_check").fetchone()
        return bool(row and str(row[0]).lower() == "ok")


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


def style_popup(popup, compact=True):
    """Apply a clean light dialog style instead of Kivy's dark default."""
    popup.background = ""
    popup.background_color = WHITE
    popup.separator_color = BORDER
    popup.title_color = TEXT
    popup.title_size = "17sp"
    popup.title_align = "left"
    return popup


def fit_popup(popup, content, min_width=dp(300), max_width=dp(460),
              min_height=dp(150), max_height_ratio=0.88, extra_height=dp(58)):
    """Size dialogs from their actual content, capped to the screen."""
    def _fit(_dt):
        try:
            width = min(max_width, max(min_width, Window.width * 0.92))
            # BoxLayout.minimum_height is reliable after its first layout pass.
            wanted = content.minimum_height + extra_height
            height = min(
                max_height_ratio * Window.height,
                max(min_height, wanted)
            )
            popup.size_hint = (None, None)
            popup.size = (width, height)
        except Exception:
            pass
    Clock.schedule_once(_fit, 0)
    Clock.schedule_once(_fit, 0.08)
    return popup


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

            # Always use four equal columns. Empty slots remain empty so a
            # single/two/three-product result never stretches the card.
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
                    size_hint_x=None,
                    size_hint_y=None,
                    width=dp(110),
                    height=dp(194),
                    padding=[dp(6), dp(6), dp(6), dp(6)],
                    spacing=dp(4),
                )

                image_path = self.app.resolve_image(product["image"])
                if image_path:
                    product_image = Image(
                        source=image_path,
                        size_hint_y=None,
                        height=dp(92),
                        allow_stretch=True,
                        keep_ratio=True,
                    )
                    product_image.reload()
                    card.add_widget(product_image)
                else:
                    placeholder = Label(
                        text="FOTO",
                        size_hint_y=None,
                        height=dp(92),
                        color=MUTED,
                        font_size="11sp",
                        bold=True,
                        halign="center",
                        valign="middle",
                    )
                    placeholder.text_size = placeholder.size
                    card.add_widget(placeholder)

                info = Label(
                    text=(
                        f'{safe_text(product["name"])}\n'
                        f'{money(product["price"])}\n'
                        f'| stok {float(product["stock"]):g}'
                    ),
                    color=TEXT,
                    font_size="10sp",
                    bold=True,
                    halign="center",
                    valign="middle",
                    size_hint_y=None,
                    height=dp(55),
                )
                info.bind(
                    size=lambda widget, value: setattr(widget, "text_size", value)
                )
                card.add_widget(info)

                button = make_button("+ Tambah", primary=True, height=32)
                button.size_hint_y = None
                button.height = dp(32)
                button.bind(
                    on_release=lambda *_args, product=product:
                    self.add_product(product)
                )
                card.add_widget(button)

                box.add_widget(card)

            box.bind(width=set_card_widths)
            Clock.schedule_once(set_card_widths, 0)
            Clock.schedule_once(set_card_widths, 0.05)

        except Exception as error:
            self.app.log_error("POS_REFRESH_PRODUCTS", error)

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
            self.app.notify("Scanner tidak tersedia. Anda tetap bisa memakai scanner Bluetooth/USB atau mengetik barcode lalu Enter.")

    def open_cart_popup(self):
        """Open the shopping cart using conservative Kivy layouts.

        This method intentionally avoids dynamic size_hint/height combinations
        that can trigger Android/Kivy layout exceptions while a Popup is opening.
        """
        try:
            if not self.cart_data:
                self.app.notify("Keranjang masih kosong.")
                return

            content = BoxLayout(
                orientation="vertical",
                spacing=dp(8),
                padding=dp(10),
            )

            scroll = ScrollView(
                do_scroll_x=False,
                size_hint_y=1,
            )
            rows = GridLayout(
                cols=1,
                spacing=dp(6),
                size_hint_y=None,
            )
            rows.bind(minimum_height=rows.setter("height"))
            scroll.add_widget(rows)
            content.add_widget(scroll)

            discount = TextInput(
                hint_text="Rp 0",
                text="0",
                input_filter="float",
                multiline=False,
                size_hint=(1, None),
                height=dp(36),
                padding=[dp(8), dp(7)],
                background_normal="",
                background_color=(0.97, 0.98, 1, 1),
                foreground_color=TEXT,
                cursor_color=PRIMARY,
            )

            discount_row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(42),
                spacing=dp(8),
            )
            discount_label = Label(
                text="Diskon Toko",
                color=MUTED,
                font_size="12sp",
                size_hint_x=None,
                width=dp(58),
                halign="left",
                valign="middle",
            )
            discount_row.add_widget(discount_label)
            discount_row.add_widget(discount)

            total_label = Label(
                text="TOTAL  Rp 0",
                color=PRIMARY,
                font_size="18sp",
                bold=True,
                size_hint_x=1,
                halign="center",
                valign="middle",
            )

            summary = GridLayout(
                cols=2,
                size_hint_y=None,
                height=dp(46),
                spacing=dp(8),
            )
            summary.add_widget(discount_row)
            total_box = BoxLayout(
                orientation="vertical",
                size_hint_x=1,
                padding=[0, dp(2), 0, dp(2)],
            )
            total_box.add_widget(total_label)
            summary.add_widget(total_box)
            content.add_widget(summary)

            pay = make_button("PILIH PEMBAYARAN  >", primary=True, height=46)
            content.add_widget(pay)

            def redraw(*_):
                try:
                    rows.clear_widgets()
                    for index, item in enumerate(list(self.cart_data)):
                        row = Card(
                            orientation="horizontal",
                            size_hint_y=None,
                            height=dp(58),
                            padding=dp(5),
                            spacing=dp(4),
                        )
                        name = Label(
                            text=f'{safe_text(item.get("name", "Produk"))}\n{item.get("qty", 0):g} x {money(item.get("price", 0))}',
                            color=TEXT,
                            halign="left",
                            valign="middle",
                        )
                        name.bind(size=lambda w, v: setattr(w, "text_size", v))
                        row.add_widget(name)

                        for symbol, delta, primary in (("-", -1, False), ("+", 1, True), ("x", 0, False)):
                            btn = make_button(symbol, primary=primary, height=42)
                            btn.size_hint_x = None
                            btn.width = dp(40)
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
                    self.app.notify("Gagal menampilkan isi keranjang.")

            def payment(*_):
                try:
                    discount_value = discount.text or "0"
                    popup.dismiss()
                    Clock.schedule_once(lambda *_dt: self.open_payment_popup(discount_value), 0.05)
                except Exception as error:
                    self.app.log_error("OPEN_PAYMENT", error)
                    self.app.notify("Gagal membuka pembayaran.")

            discount.bind(text=redraw)
            pay.bind(on_release=payment)

            popup = style_popup(Popup(
                title="Checkout Transaksi",
                content=content,
                size_hint=(None, None),
                size=(min(dp(520), Window.width * 0.94), min(dp(560), Window.height * 0.82)),
                auto_dismiss=True,
            ))

            def size_popup(*_):
                try:
                    width = min(dp(520), max(dp(320), Window.width * 0.94))
                    rows_h = min(dp(390), max(dp(150), rows.minimum_height + dp(8)))
                    desired = rows_h + dp(46) + dp(42) + dp(46) + dp(58)
                    height = min(Window.height * 0.82, max(dp(340), desired))
                    popup.size = (width, height)
                except Exception as error:
                    self.app.log_error("CART_POPUP_SIZE", error)

            redraw()
            popup.open()
            Clock.schedule_once(size_popup, 0.05)
            Clock.schedule_once(size_popup, 0.15)

        except Exception as error:
            self.app.log_error("OPEN_CART", error)
            self.app.notify("Keranjang gagal dibuka. Silakan coba lagi.")

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
        tax=None
    ):
        if not self.cart_data:
            self.app.notify("Keranjang masih kosong.")
            return

        subtotal, discount_value, tax_value, total = self.calculate_total(
            discount, self.app.tax_percent if tax is None else tax
        )

        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(14))

        total_card = Card(orientation="vertical", size_hint_y=None, height=dp(92), padding=dp(10), spacing=dp(2))
        total_card.add_widget(Label(text="TOTAL PEMBAYARAN", color=MUTED, font_size="12sp", size_hint_y=None, height=dp(24)))
        total_card.add_widget(Label(text=money(total), color=PRIMARY, font_size="25sp", bold=True))
        content.add_widget(total_card)

        method = Spinner(
            text="Tunai",
            values=["Tunai", "QRIS", "Debit", "Kredit", "Transfer", "E-Wallet"],
            size_hint_y=None, height=dp(46)
        )
        content.add_widget(method)

        paid = OutlinedInput(
            hint_text="Uang diterima", input_filter="float", multiline=False,
            size_hint_y=None, height=dp(46), padding=[dp(12), dp(10)]
        )
        content.add_widget(paid)

        change = Label(text="Kembalian  Rp 0", font_size="15sp", bold=True,
                       size_hint_y=None, height=dp(38), color=SUCCESS)
        content.add_widget(change)

        selected = {"account": None}
        account_status = Label(text="", color=MUTED, font_size="11sp",
                               size_hint_y=None, height=dp(38), halign="center", valign="middle")
        account_status.bind(size=lambda w, v: setattr(w, "text_size", v))
        content.add_widget(account_status)

        def update(*_):
            m = method.text
            if m == "Tunai":
                paid.disabled = False
                change.text = "Kembalian  " + money(max(0, safe_float(paid.text) - total))
                account_status.text = "Masukkan uang yang diterima."
            elif m in ("Transfer", "E-Wallet"):
                paid.text = ""
                paid.disabled = True
                kind = "bank" if m == "Transfer" else "wallet"
                accounts = self.app.db.payment_accounts(kind)
                selected["account"] = None
                if accounts:
                    account_status.text = f"{len(accounts)} akun tersedia. Pilih rekening/nomor pada langkah berikutnya."
                else:
                    account_status.text = "Belum ada akun pembayaran. Tambahkan di Pengaturan."
                change.text = "Pembayaran non-tunai"
            else:
                paid.text = ""
                paid.disabled = True
                selected["account"] = None
                change.text = "Pembayaran non-tunai"
                account_status.text = "Siap dikonfirmasi setelah pembayaran diterima."

        paid.bind(text=update)
        method.bind(text=update)

        buttons = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        cancel = make_button("BATAL")
        done = make_button("SELESAIKAN PESANAN", primary=True, height=48)
        buttons.add_widget(cancel); buttons.add_widget(done); content.add_widget(buttons)

        popup = style_popup(Popup(
            title="Pilih Pembayaran", content=content, size_hint=(None, None),
            size=(dp(420), dp(430)), auto_dismiss=True
        ))
        fit_popup(popup, content, min_width=dp(340), max_width=dp(540),
                  min_height=dp(390), max_height_ratio=.86, extra_height=dp(64))
        cancel.bind(on_release=popup.dismiss)

        def complete_sale(account=None):
            paid_value = safe_float(paid.text)
            m = method.text
            if m == "Tunai" and paid_value < total:
                self.app.notify("Uang kurang " + money(total - paid_value))
                return
            if m != "Tunai":
                paid_value = total
            change_value = max(0, paid_value - total) if m == "Tunai" else 0
            try:
                cart_snapshot = [dict(item) for item in self.cart_data]
                invoice = self.app.db.create_sale(
                    cart_snapshot, subtotal, discount_value, tax_value, total,
                    m, paid_value, change_value
                )
                self.app.last_receipt = (
                    invoice, subtotal, discount_value, tax_value, total,
                    m, paid_value, change_value, cart_snapshot
                )
                popup.dismiss()
                self.clear_cart()
                # Setelah transaksi, tetap di Kasir agar navigasi utama selalu 3 halaman.
                self.app.root.ids.sm.current = "pos"
                self.app.refresh_nav_highlight()
                self.app.notify(f"Transaksi {invoice} berhasil.")
                self.app.auto_backup()
                Clock.schedule_once(lambda *_dt: self.app.auto_print_saved_receipt(), 0.15)
            except Exception as error:
                self.app.log_error("CHECKOUT", error)
                self.app.notify("Transaksi gagal:\n" + str(error))

        def continue_payment(*_):
            m = method.text
            if m == "Tunai":
                complete_sale()
                return
            if m in ("Transfer", "E-Wallet"):
                kind = "bank" if m == "Transfer" else "wallet"
                accounts = self.app.db.payment_accounts(kind)
                if not accounts:
                    self.app.notify("Belum ada akun pembayaran. Tambahkan rekening/e-wallet di Pengaturan.")
                    return
                self.open_account_selection_popup(
                    m, total, accounts,
                    lambda account: self.open_payment_confirmation(
                        m, total, account, complete_sale
                    )
                )
                return
            self.open_payment_confirmation(m, total, None, complete_sale)

        done.bind(on_release=continue_payment)
        popup.open()
        update()

    def open_account_selection_popup(self, method, total, accounts, on_selected):
        kind_text = "rekening bank" if method == "Transfer" else "nomor e-wallet"
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        intro = text_label(f"Total pembayaran\n{money(total)}\n\nPilih {kind_text} tujuan.", size=15, halign="center")
        intro.size_hint_y = None
        intro.height = dp(92)
        content.add_widget(intro)

        scroll = ScrollView(do_scroll_x=False, size_hint_y=1, bar_width=dp(3))
        rows = GridLayout(cols=1, spacing=dp(6), size_hint_y=None, padding=[0,dp(2),0,dp(2)])
        rows.bind(minimum_height=rows.setter("height"))
        scroll.add_widget(rows)
        content.add_widget(scroll)

        close = make_button("BATAL", height=44)
        content.add_widget(close)
        popup = style_popup(Popup(title="Pilih Akun Pembayaran", content=content, size_hint=(None,None),
                                  size=(dp(470), dp(610)), auto_dismiss=True))
        fit_popup(popup, content, min_width=dp(370), max_width=dp(620),
                  min_height=dp(480), max_height_ratio=.93, extra_height=dp(62))
        close.bind(on_release=popup.dismiss)

        for account in accounts:
            card = Card(orientation="horizontal", size_hint_y=None, height=dp(76), padding=dp(8), spacing=dp(8), radius=dp(10))
            badge = Card(orientation="vertical", size_hint_x=None, width=dp(56), padding=dp(4), radius=dp(10))
            badge_label = text_label(safe_text(account["provider"])[:6].upper(), size=9, color=PRIMARY, halign="center")
            badge_label.bold = True
            badge_label.valign = "middle"
            badge_label.text_size = badge_label.size
            badge.add_widget(badge_label)
            card.add_widget(badge)

            info = BoxLayout(orientation="vertical", spacing=0)
            p = text_label(safe_text(account["provider"]), size=11, color=PRIMARY, halign="left"); p.bold=True
            num = text_label(safe_text(account["account_number"]), size=13, color=TEXT, halign="left")
            holder = text_label("a.n. " + safe_text(account["account_name"]), size=9, color=MUTED, halign="left")
            for lbl,h in ((p,19),(num,23),(holder,18)):
                lbl.size_hint_y=None; lbl.height=dp(h); lbl.valign="middle"; lbl.text_size=lbl.size; info.add_widget(lbl)
            card.add_widget(info)
            choose = make_button("PILIH", primary=True, height=38)
            choose.size_hint_x=None; choose.width=dp(78)
            card.add_widget(choose)
            choose.bind(on_release=lambda *_a, a=account: (popup.dismiss(), on_selected(a)))
            rows.add_widget(card)
        popup.open()

    def open_payment_confirmation(self, method, total, account, complete_sale):
        content = BoxLayout(orientation="vertical", spacing=dp(9), padding=dp(14))

        title = Label(text="KONFIRMASI PEMBAYARAN", color=TEXT, font_size="18sp", bold=True,
                      size_hint_y=None, height=dp(32), halign="center", valign="middle")
        title.bind(size=lambda w,v: setattr(w,"text_size",v))
        content.add_widget(title)

        total_lbl = Label(text="Total Pembayaran\n" + money(total), color=PRIMARY, font_size="22sp", bold=True,
                          size_hint_y=None, height=dp(68), halign="center", valign="middle")
        total_lbl.bind(size=lambda w,v: setattr(w,"text_size",v))
        content.add_widget(total_lbl)

        if method == "QRIS":
            qr_card = Card(orientation="vertical", size_hint_y=None, height=dp(430), padding=dp(10), spacing=dp(8), radius=dp(12))
            image_path = self.app.resolve_image(self.app.db.setting("qris_image"))
            if image_path:
                qr_holder = AnchorLayout(size_hint_y=None, height=dp(355), anchor_x="center", anchor_y="center")
                qr = Image(source=image_path, size_hint=(None,None), width=dp(335), height=dp(335), allow_stretch=True, keep_ratio=True)
                qr.reload()
                qr_holder.add_widget(qr)
                qr_card.add_widget(qr_holder)
            else:
                qr_card.add_widget(Label(text="QRIS belum dipasang di Pengaturan.", color=DANGER, font_size="14sp",
                                         size_hint_y=None, height=dp(250), halign="center", valign="middle"))
            instruction = self.app.db.setting("qris_instruction") or "Scan QRIS lalu lakukan pembayaran sesuai total."
            ins = Label(text=instruction, color=TEXT, font_size="12sp", size_hint_y=None, height=dp(42), halign="center", valign="middle")
            ins.bind(size=lambda w,v: setattr(w,"text_size",v))
            qr_card.add_widget(ins)
            content.add_widget(qr_card)
        elif method in ("Transfer", "E-Wallet") and account is not None:
            box = Card(orientation="vertical", size_hint_y=None, height=dp(155), padding=dp(14), spacing=dp(3), radius=dp(12))
            provider_label = "BANK / TUJUAN" if method == "Transfer" else "E-WALLET / TUJUAN"
            small = Label(text=provider_label, color=MUTED, font_size="10sp", bold=True, size_hint_y=None, height=dp(20), halign="center")
            p = Label(text=safe_text(account["provider"]), color=PRIMARY, font_size="18sp", bold=True, size_hint_y=None, height=dp(28), halign="center")
            n = Label(text=safe_text(account["account_number"]), color=TEXT, font_size="20sp", bold=True, size_hint_y=None, height=dp(32), halign="center")
            h = Label(text="a.n. " + safe_text(account["account_name"]), color=MUTED, font_size="12sp", size_hint_y=None, height=dp(24), halign="center")
            for w in (small,p,n,h): w.text_size=w.size
            box.add_widget(small); box.add_widget(p); box.add_widget(n); box.add_widget(h)
            content.add_widget(box)
            action = "transfer" if method == "Transfer" else "pembayaran"
            info = Label(text=f"Setelah {action} diterima, tekan KONFIRMASI PEMBAYARAN.", color=TEXT,
                         font_size="12sp", size_hint_y=None, height=dp(54), halign="center", valign="middle")
            info.bind(size=lambda w,v: setattr(w,"text_size",v))
            content.add_widget(info)
        else:
            info = Label(text="Pastikan pembayaran sudah diterima sebelum melanjutkan.", color=TEXT,
                         font_size="13sp", size_hint_y=None, height=dp(86), halign="center", valign="middle")
            info.bind(size=lambda w,v: setattr(w,"text_size",v))
            content.add_widget(info)

        buttons = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        cancel = make_button("BATAL", height=52)
        confirm = make_button("KONFIRMASI PEMBAYARAN", primary=True, height=52)
        buttons.add_widget(cancel); buttons.add_widget(confirm); content.add_widget(buttons)

        popup = style_popup(Popup(title="Pembayaran", content=content, size_hint=(None,None),
                                  size=(dp(600), dp(790)), auto_dismiss=False))
        fit_popup(popup, content, min_width=dp(420), max_width=dp(700),
                  min_height=dp(570), max_height_ratio=.97, extra_height=dp(70))
        cancel.bind(on_release=popup.dismiss)
        confirm.bind(on_release=lambda *_: (popup.dismiss(), complete_sale(account)))
        popup.open()


    def clear_cart(self):

        self.cart_data = []

        self.render_cart_summary()


# ============================================================
# PRODUCT SCREEN
# ============================================================

class ProductScreen(Screen):

    category_filter = StringProperty("Semua")

    def on_enter(self):

        self.app = App.get_running_app()

        self.refresh()

    def toggle_categories(self):
        try:
            box = self.ids.categories
            box.clear_widgets()
            categories = ["Semua"]
            seen = set()
            for p in self.app.db.products():
                c = safe_text(p["category"]).strip()
                if c and c.lower() not in seen:
                    seen.add(c.lower()); categories.append(c)
            for category in categories:
                b = make_button(category, primary=(category == self.category_filter), height=34)
                b.size_hint_x = None
                b.width = max(dp(72), dp(18) + len(category) * dp(7))
                b.bind(on_release=lambda *_a, c=category: self.set_category(c))
                box.add_widget(b)
        except Exception as error:
            self.app.log_error("PRODUCT_CATEGORIES", error)

    def set_category(self, category):
        self.category_filter = category
        self.toggle_categories()
        self.refresh(self.ids.search.text, category)

    def refresh(self, search="", category="Semua"):
        try:
            box = self.ids.list
            box.clear_widgets()
            products = self.app.db.products(search)
            if category and category != "Semua":
                products = [p for p in products if safe_text(p["category"]).strip().lower() == category.strip().lower()]

            self.ids.count.text = f"Produk ({len(products)} Item)"
            self.toggle_categories()

            for product in products:
                row = Card(
                    orientation="horizontal",
                    size_hint_y=None,
                    height=dp(86),
                    spacing=dp(9),
                    padding=dp(7),
                )

                image_path = self.app.resolve_image(product["image"])
                if image_path:
                    image = Image(
                        source=image_path,
                        size_hint_x=None,
                        width=dp(68),
                        allow_stretch=True,
                        keep_ratio=True,
                    )
                    image.reload()
                    row.add_widget(image)
                else:
                    row.add_widget(Label(text="FOTO", size_hint_x=None, width=dp(68), color=MUTED, bold=True))

                info_box = BoxLayout(orientation="vertical", spacing=dp(3))
                info = Label(
                    text=f'{safe_text(product["name"])}\n{money(product["price"])}\n{safe_text(product["category"]) or "Tanpa kategori"}',
                    color=TEXT, font_size="11sp", halign="left", valign="middle"
                )
                info.bind(size=lambda widget, value: setattr(widget, "text_size", value))
                info_box.add_widget(info)

                stock_text = ("STOK HABIS" if safe_float(product["stock"]) <= 0 else f'STOK {float(product["stock"]):g}')
                stock = PillLabel(
                    text=stock_text,
                    bg_color=("danger" if safe_float(product["stock"]) <= 0 else "success"),
                    color=WHITE, bold=True, font_size="9sp",
                    size_hint_x=None, width=max(dp(62), dp(16) + len(stock_text) * dp(5.6)),
                    halign="center", valign="middle"
                )
                stock.text_size = stock.size
                info_box.add_widget(stock)
                row.add_widget(info_box)

                edit_button = make_button("EDIT", primary=True, height=36)
                edit_button.size_hint_x = None; edit_button.width = dp(56)
                edit_button.bind(on_release=lambda *_args, product=product: self.open_editor(product))
                row.add_widget(edit_button)

                delete_button = make_button("HAPUS", primary=False, height=36)
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
        content.add_widget(text_label(
            f"Hapus produk \"{product['name']}\"?\nProduk tidak akan tampil lagi di kasir.",
            size=14, halign="center"
        ))
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        cancel = make_button("Batal")
        remove = make_button("HAPUS", primary=False)
        remove.background_color = (0.78, 0.12, 0.12, 1)
        remove.color = (1, 1, 1, 1)
        row.add_widget(cancel); row.add_widget(remove)
        content.add_widget(row)
        popup = style_popup(Popup(title="Hapus Produk", content=content, size_hint=(None, None), size=(dp(360), dp(190))))
        fit_popup(popup, content, min_width=dp(320), max_width=dp(460), min_height=dp(175), max_height_ratio=.55, extra_height=dp(52))
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
                self.app.notify("Produk gagal dihapus.")
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
        popup = style_popup(Popup(title="Restock Produk", content=content, size_hint=(None,None), size=(dp(370),dp(260))))
        fit_popup(popup, content, min_width=dp(330), max_width=dp(460), min_height=dp(240), max_height_ratio=.65, extra_height=dp(56))
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

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(7),
            padding=dp(10)
        )

        preview = Image(
            source="",
            size_hint_y=None,
            height=dp(105),
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

        popup = style_popup(Popup(
            title="Edit Produk" if product else "Tambah Produk",
            content=content,
            size_hint=(None, None),
            size=(dp(400), dp(500)),
            auto_dismiss=True
        ))
        fit_popup(popup, content, min_width=dp(320), max_width=dp(470),
                  min_height=dp(390), max_height_ratio=0.90, extra_height=dp(58))

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

    def refresh(self, search=""):

        try:

            box = self.ids.list

            box.clear_widgets()

            sales = self.app.db.sales()
            q = safe_text(search).strip().lower()
            if q:
                sales = [sale for sale in sales if q in safe_text(sale["invoice"]).lower() or q in safe_text(sale["payment_method"]).lower() or q in safe_text(sale["created_at"]).lower()]
            self.ids.count.text = f"Transaksi ({len(sales)})"

            for sale in sales:

                row = Card(
                    orientation="horizontal", size_hint_y=None, height=dp(82),
                    padding=dp(9), spacing=dp(8)
                )
                voided = bool(int(sale["voided"] or 0)) if "voided" in sale.keys() else False
                info = Label(
                    text=f'{sale["invoice"]}\n{sale["created_at"]}  |  {sale["payment_method"]}',
                    color=TEXT, halign="left", valign="middle", font_size="11sp"
                )
                info.bind(size=lambda w, v: setattr(w, "text_size", v))
                row.add_widget(info)

                status = PillLabel(
                    text=("DIBATALKAN" if voided else "DIBAYAR"),
                    bg_color=("danger" if voided else "success"),
                    color=WHITE, bold=True, font_size="9sp",
                    size_hint_x=None, width=dp(78), halign="center", valign="middle"
                )
                status.text_size = status.size
                row.add_widget(status)

                total = Label(
                    text=money(sale["total"]), color=PRIMARY, bold=True, font_size="14sp",
                    size_hint_x=None, width=dp(92), halign="right", valign="middle"
                )
                total.bind(size=lambda w, v: setattr(w, "text_size", v))
                row.add_widget(total)

                detail = make_button("DETAIL", primary=True, height=36)
                detail.size_hint_x = None; detail.width = dp(64)
                detail.bind(on_release=lambda *_a, sale_id=sale["id"]: self.open_detail(sale_id))
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
        if not sale:
            return
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        content.add_widget(text_label(f"Batalkan transaksi {sale['invoice']}?\nStok produk akan dikembalikan.", size=14, halign="center"))
        reason = TextInput(hint_text="Alasan pembatalan", multiline=False, size_hint_y=None, height=dp(44))
        content.add_widget(reason)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        cancel=make_button("Batal"); yes=make_button("VOID", primary=False); yes.background_color=DANGER; yes.color=WHITE
        row.add_widget(cancel); row.add_widget(yes); content.add_widget(row)
        popup=style_popup(Popup(title="Void Transaksi", content=content, size_hint=(None,None), size=(dp(380),dp(250))))
        fit_popup(popup, content, min_width=dp(330), max_width=dp(460), min_height=dp(230), max_height_ratio=.65, extra_height=dp(58))
        cancel.bind(on_release=popup.dismiss)
        def run(*_):
            try:
                self.app.db.void_sale(sale_id, reason.text.strip() or "Dibatalkan")
                popup.dismiss(); self.refresh(); self.app.root.ids.sm.get_screen("products").refresh(); self.app.root.ids.sm.get_screen("pos").refresh_products()
                self.app.notify("Transaksi dibatalkan dan stok dikembalikan.")
            except Exception as error:
                self.app.log_error("VOID_SALE", error); self.app.notify(str(error))
        yes.bind(on_release=run); popup.open()


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
                    COALESCE((SELECT SUM(qty) FROM sale_items si JOIN sales sx ON sx.id=si.sale_id WHERE date(sx.created_at)=date('now') AND COALESCE(sx.voided,0)=0),0) items_sold
                FROM sales
                WHERE date(created_at)=date('now') AND COALESCE(voided,0)=0
                """
            ).fetchone()

            box = self.ids.summary
            box.clear_widgets()
            header = text_label("PENJUALAN HARI INI", size=16, halign="center")
            header.bold = True
            header.size_hint_y = None
            header.height = dp(30)
            box.add_widget(header)
            grid = GridLayout(cols=2, spacing=dp(2), size_hint_y=None)
            grid.bind(minimum_height=grid.setter("height"))
            report_rows = [
                ("Transaksi", str(rows['n'])),
                ("Subtotal", money(rows['subtotal'])),
                ("Diskon", money(rows['discount'])),
                ("Pajak", money(rows['tax'])),
                ("Barang terjual", f"{float(rows['items_sold']):g} item"),
                ("TOTAL", money(rows['total'])),
            ]
            for label_text, value_text in report_rows:
                l = text_label(label_text + "  :", size=14, halign="left")
                r = text_label(value_text, size=14, halign="right")
                l.size_hint_y = None; l.height = dp(25)
                r.size_hint_y = None; r.height = dp(25)
                if label_text == "TOTAL":
                    l.bold = True; r.bold = True; r.color = PRIMARY
                grid.add_widget(l); grid.add_widget(r)
            box.add_widget(grid)

            try:
                today, items, top = self.app.db.dashboard()
                profit = money(items["profit"])
                extra_label = text_label(f"Laba kotor hari ini  :  {profit}", size=14, halign="left")
                extra_label.size_hint_y=None; extra_label.height=dp(28); extra_label.bold=True
                box.add_widget(extra_label)
                low = self.app.db.low_stock_products()
                low_text = ", ".join([f"{p['name']} ({float(p['stock']):g})" for p in low[:4]]) if low else "Tidak ada"
                low_label = text_label("Stok menipis  :  " + low_text, size=12, halign="left")
                low_label.size_hint_y=None; low_label.height=dp(42); box.add_widget(low_label)
                top_text = ", ".join([f"{r['name']} ({float(r['qty']):g})" for r in top[:3]]) if top else "Belum ada"
                top_label = text_label("Produk terlaris  :  " + top_text, size=12, halign="left")
                top_label.size_hint_y=None; top_label.height=dp(42); box.add_widget(top_label)
            except Exception as dashboard_error:
                self.app.log_error("DASHBOARD", dashboard_error)

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

    def export_stock_csv(self):
        try:
            path = os.path.join(self.app.user_data_dir, "stock_export.csv")
            with open(path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerow(["Nama","SKU/Barcode","Kategori","Harga Jual","Modal","Stok"])
                for p in self.app.db.products():
                    writer.writerow([p["name"],p["sku"],p["category"],p["price"],p["cost"],p["stock"]])
            self.app.notify("CSV stok berhasil dibuat:\n" + path)
        except Exception as error:
            self.app.log_error("EXPORT_STOCK", error); self.app.notify("Export stok gagal.")


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

            logo = self.app.resolve_image(self.app.db.setting("receipt_logo"))
            self.ids.receipt_logo_preview.source = logo if logo else ""
            if logo:
                self.ids.receipt_logo_preview.reload()
            self.ids.logo_status.text = "Logo struk: terpasang" if logo else "Logo struk: belum dipilih"

            self.ids.paper.text = (
                self.app.db.setting("paper") or "58mm"
            )
            self.ids.tax.text = (self.app.db.setting("tax_percent") or "0")
            self.ids.cashier.text = (self.app.db.setting("cashier_name") or "Kasir")
            self.ids.role.text = (self.app.db.setting("user_role") or "Owner")
            self.ids.low_stock.text = (self.app.db.setting("low_stock_threshold") or "5")
            address = self.app.db.setting("printer_address")
            self.ids.printer_status.text = "Printer: " + (address if address else "belum dipilih")

            qris = self.app.resolve_image(self.app.db.setting("qris_image"))
            self.ids.qris_preview.source = qris if qris else ""
            if qris:
                self.ids.qris_preview.reload()
            self.ids.qris_status.text = "QRIS: terpasang" if qris else "QRIS: belum dipasang"
            self.ids.qris_instruction.text = self.app.db.setting("qris_instruction") or "Scan QRIS lalu lakukan pembayaran sesuai total."
            Clock.schedule_once(lambda *_dt: self.refresh_payment_accounts(), 0)

        except Exception as error:

            self.app.log_error(
                "SETTINGS_LOAD",
                error
            )

    def open_transactions(self):
        try:
            self.app.navigate("transactions")
        except Exception as error:
            self.app.log_error("SETTINGS_OPEN_TRANSACTIONS", error)

    def open_reports(self):
        try:
            self.app.navigate("reports")
        except Exception as error:
            self.app.log_error("SETTINGS_OPEN_REPORTS", error)

    def open_printer(self):
        try:
            self.app.bluetooth_printer_dialog()
        except Exception as error:
            self.app.log_error("SETTINGS_PRINTER", error)
            self.app.notify("Pengaturan printer gagal dibuka.")

    def test_printer(self):
        try:
            self.app.test_saved_printer()
        except Exception as error:
            self.app.log_error("TEST_PRINTER", error); self.app.notify("Test printer gagal.")

    def refresh_payment_accounts(self):
        try:
            for widget_id, kind in (("bank_accounts", "bank"), ("wallet_accounts", "wallet")):
                box = self.ids[widget_id]
                box.clear_widgets()
                accounts = self.app.db.payment_accounts(kind)
                if not accounts:
                    empty = Card(orientation="horizontal", size_hint_y=None, height=dp(44), padding=dp(8))
                    empty.add_widget(text_label("Belum ada akun pembayaran.", size=10, color=MUTED, halign="left"))
                    box.add_widget(empty)
                    continue

                for account in accounts:
                    row = Card(orientation="horizontal", size_hint_y=None, height=dp(66), padding=dp(6), spacing=dp(6), radius=dp(10))
                    badge = Card(orientation="vertical", size_hint_x=None, width=dp(48), padding=dp(3), radius=dp(9))
                    badge_label = text_label(safe_text(account["provider"])[:5].upper(), size=8, color=PRIMARY, halign="center")
                    badge_label.bold = True
                    badge_label.valign = "middle"
                    badge_label.text_size = badge_label.size
                    badge.add_widget(badge_label)
                    row.add_widget(badge)

                    info = BoxLayout(orientation="vertical", spacing=0)
                    provider = text_label(safe_text(account["provider"]), size=10, color=PRIMARY, halign="left")
                    provider.bold = True
                    number = text_label(safe_text(account["account_number"]), size=10, color=TEXT, halign="left")
                    holder = text_label("a.n. " + safe_text(account["account_name"]), size=8, color=MUTED, halign="left")
                    for lbl, h in ((provider, 18), (number, 20), (holder, 17)):
                        lbl.size_hint_y = None
                        lbl.height = dp(h)
                        lbl.valign = "middle"
                        lbl.text_size = lbl.size
                        info.add_widget(lbl)
                    row.add_widget(info)

                    edit = OutlineButton(text="EDIT", size_hint_x=None, width=dp(58), height=dp(34))
                    remove = IconActionButton(icon_type="trash", danger=True)
                    remove.width = dp(40)
                    remove.height = dp(34)
                    edit.bind(on_release=lambda *_a, a=account: self.edit_payment_account(a))
                    remove.bind(on_release=lambda *_a, a=account: self.delete_payment_account(a))
                    row.add_widget(edit)
                    row.add_widget(remove)
                    box.add_widget(row)
        except Exception as error:
            self.app.log_error("PAYMENT_ACCOUNTS_REFRESH", error)

    def payment_account_editor(self, account_type, account=None):
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        provider_hint = "Nama bank (contoh: BCA)" if account_type == "bank" else "Jenis e-wallet (contoh: DANA)"
        number_hint = "Nomor rekening" if account_type == "bank" else "Nomor HP / akun e-wallet"
        provider = OutlinedInput(hint_text=provider_hint, multiline=False, size_hint_y=None, height=dp(44), padding=[dp(10),dp(9)])
        number = OutlinedInput(hint_text=number_hint, multiline=False, size_hint_y=None, height=dp(44), padding=[dp(10),dp(9)])
        owner = OutlinedInput(hint_text="Nama pemilik", multiline=False, size_hint_y=None, height=dp(44), padding=[dp(10),dp(9)])
        if account:
            provider.text = safe_text(account["provider"]); number.text = safe_text(account["account_number"]); owner.text = safe_text(account["account_name"])
        content.add_widget(provider); content.add_widget(number); content.add_widget(owner)
        buttons = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        cancel=make_button("BATAL"); save=make_button("SIMPAN", primary=True)
        buttons.add_widget(cancel); buttons.add_widget(save); content.add_widget(buttons)
        title = ("Edit " if account else "Tambah ") + ("Rekening Bank" if account_type == "bank" else "E-Wallet")
        popup=style_popup(Popup(title=title, content=content, size_hint=(None,None), size=(dp(390),dp(300)), auto_dismiss=True))
        fit_popup(popup, content, min_width=dp(330), max_width=dp(500), min_height=dp(250), max_height_ratio=.65, extra_height=dp(58))
        cancel.bind(on_release=popup.dismiss)
        def do_save(*_):
            if not provider.text.strip() or not number.text.strip() or not owner.text.strip():
                self.app.notify("Semua data pembayaran wajib diisi."); return
            try:
                if account:
                    self.app.db.update_payment_account(account["id"], account_type, provider.text, number.text, owner.text)
                else:
                    self.app.db.add_payment_account(account_type, provider.text, number.text, owner.text)
                popup.dismiss(); self.refresh_payment_accounts(); self.app.notify("Data pembayaran berhasil disimpan.")
            except Exception as error:
                self.app.log_error("PAYMENT_ACCOUNT_SAVE", error); self.app.notify("Data pembayaran gagal disimpan.")
        save.bind(on_release=do_save); popup.open()

    def add_bank_account(self): self.payment_account_editor("bank")
    def add_wallet_account(self): self.payment_account_editor("wallet")
    def edit_payment_account(self, account): self.payment_account_editor(account["account_type"], account)
    def delete_payment_account(self, account):
        content=BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        content.add_widget(text_label(f'Hapus {account["provider"]}\n{account["account_number"]}?', size=14, halign="center"))
        row=BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8)); cancel=make_button("BATAL"); yes=make_button("HAPUS", primary=False); yes.background_color=DANGER; yes.color=WHITE
        row.add_widget(cancel); row.add_widget(yes); content.add_widget(row)
        popup=style_popup(Popup(title="Hapus Akun", content=content, size_hint=(None,None), size=(dp(350),dp(190))))
        cancel.bind(on_release=popup.dismiss)
        def run(*_):
            try:
                self.app.db.delete_payment_account(account["id"]); popup.dismiss(); self.refresh_payment_accounts(); self.app.notify("Akun pembayaran dihapus.")
            except Exception as error:
                self.app.log_error("PAYMENT_ACCOUNT_DELETE", error)
        yes.bind(on_release=run); popup.open()

    def choose_qris(self):
        try:
            selected={"path": self.ids.qris_preview.source or ""}
            self.app.open_image_picker(selected, self.ids.qris_preview)
            self._qris_selection=selected
            self.app._settings_qris_selected=selected
        except Exception as error:
            self.app.log_error("QRIS_PICKER", error); self.app.notify("Pemilih QRIS gagal dibuka.")

    def remove_qris(self):
        try:
            old=self.app.resolve_image(self.app.db.setting("qris_image"))
            self.app.db.set_setting("qris_image", ""); self.ids.qris_preview.source=""; self.ids.qris_status.text="QRIS: belum dipasang"
            if old and os.path.isfile(old) and old.startswith(os.path.abspath(self.app.images_dir)+os.sep):
                try: os.remove(old)
                except Exception: pass
            self.app.notify("QRIS dihapus.")
        except Exception as error: self.app.log_error("QRIS_REMOVE", error)

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

            logo_source = self.ids.receipt_logo_preview.source or self.app.db.setting("receipt_logo") or ""
            logo_path = self.app.save_receipt_logo(logo_source) if logo_source else ""
            self.app.db.set_setting("receipt_logo", logo_path)

            qris_source = self.ids.qris_preview.source or self.app.db.setting("qris_image") or ""
            qris_path = self.app.save_named_image(qris_source, "qris.png") if qris_source else ""
            self.app.db.set_setting("qris_image", qris_path)
            self.app.db.set_setting("qris_instruction", self.ids.qris_instruction.text.strip() or "Scan QRIS lalu lakukan pembayaran sesuai total.")

            self.app.db.set_setting(
                "paper", self.ids.paper.text
            )
            self.app.db.set_setting("tax_percent", str(max(0, safe_float(self.ids.tax.text))))
            self.app.db.set_setting("cashier_name", self.ids.cashier.text.strip() or "Kasir")
            self.app.db.set_setting("user_role", self.ids.role.text or "Owner")
            self.app.db.set_setting("low_stock_threshold", str(max(0, safe_float(self.ids.low_stock.text, 5))))

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

    def choose_receipt_logo(self):
        try:
            selected = {"path": self.ids.receipt_logo_preview.source or ""}
            self.app.open_image_picker(selected, self.ids.receipt_logo_preview)
            self._logo_selection = selected
            self.app._settings_logo_selected = selected
        except Exception as error:
            self.app.log_error("RECEIPT_LOGO_PICKER", error)
            self.app.notify("Pemilih logo struk gagal dibuka.")

    def remove_receipt_logo(self):
        try:
            old = self.app.resolve_image(self.app.db.setting("receipt_logo"))
            self.app.db.set_setting("receipt_logo", "")
            self.ids.receipt_logo_preview.source = ""
            self.ids.logo_status.text = "Logo struk: belum dipilih"
            if old and os.path.isfile(old) and old.startswith(os.path.abspath(self.app.images_dir) + os.sep):
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
            self.app.log_error("DATABASE_BACKUP", error); self.app.notify("Backup gagal.")

    def restore_backup(self):
        try:
            self.app.restore_latest_backup()
            self.app.notify("Restore berhasil. Tutup lalu buka kembali aplikasi agar seluruh tampilan memuat data terbaru.")
        except Exception as error:
            self.app.log_error("DATABASE_RESTORE", error); self.app.notify("Restore gagal:\n" + str(error))

    def check_database(self):
        try:
            ok = self.app.db.integrity_check()
            self.app.notify("Database sehat (integrity_check: OK)." if ok else "Database terdeteksi bermasalah.")
        except Exception as error:
            self.app.log_error("DATABASE_CHECK", error); self.app.notify("Pengecekan database gagal.")


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
    # STARTUP TRACE
    # --------------------------------------------------------

    def log_startup(self, stage):
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            path = os.path.join(self.user_data_dir, "KasirQU_startup.log")
            with open(path, "a", encoding="utf-8") as file:
                file.write(datetime.now().isoformat() + " | " + str(stage) + "\n")
        except Exception:
            pass

    # --------------------------------------------------------
    # BUILD
    # --------------------------------------------------------

    def build(self):

        self.log_startup("BUILD_ENTER")
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
            self.log_startup("DATABASE_READY")

            self.tax_percent = (
                self.db.setting(
                    "tax_percent"
                )
                or
                "0"
            )

            self.log_startup("LOADING_KV")
            root = Builder.load_string(KV)
            self.log_startup("KV_READY")

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

        self.log_startup("ON_START")
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
            self.log_startup("SCREEN_POS_READY")

            pos.refresh_products()
            self.log_startup("PRODUCTS_READY")
            self.refresh_nav_highlight()

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

            if name == "reports" and (self.db.setting("user_role") or "Owner") == "Kasir":
                self.notify("Laporan hanya dapat dibuka oleh Owner/Admin.")
                return

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
                self.refresh_nav_highlight()
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
            self.refresh_nav_highlight()

        except Exception as error:

            self.log_error(
                "NAVIGATION",
                error
            )

    def refresh_nav_highlight(self):
        try:
            current = self.root.ids.sm.current
            def walk(widget):
                yield widget
                for child in getattr(widget, "children", []):
                    yield from walk(child)
            nav_current = current if current in ("pos", "products", "settings") else "settings"
            for widget in walk(self.root):
                if isinstance(widget, IconNavButton):
                    widget.is_active = (widget.nav_name == nav_current)
        except Exception as error:
            self.log_error("NAV_HIGHLIGHT", error)

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
            popup = style_popup(Popup(
                title=APP_NAME,
                content=content,
                size_hint=(.88, None),
                size=(dp(400), min(dp(220), max(dp(150), dp(105 + line_count * 22))))
            ))

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

        if request_code == 9002:
            try:
                if intent is not None:
                    code = safe_text(intent.getStringExtra("SCAN_RESULT")).strip()
                    if code and getattr(self, "_barcode_screen", None):
                        self._barcode_screen.quick_add_by_code(code)
                return
            except Exception as error:
                self.log_error("BARCODE_RESULT", error); return

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
        """Copy Android content:// image into app-private storage as a PNG.

        Using BitmapFactory avoids provider/format issues that can leave a valid
        gallery selection but an unreadable Kivy image path.
        """
        input_stream = None
        output_stream = None
        bitmap = None
        target = ""
        try:
            from jnius import autoclass

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            resolver = PythonActivity.mActivity.getContentResolver()
            input_stream = resolver.openInputStream(uri)
            if input_stream is None:
                raise RuntimeError("Content URI tidak dapat dibaca.")

            BitmapFactory = autoclass("android.graphics.BitmapFactory")
            bitmap = BitmapFactory.decodeStream(input_stream)
            if bitmap is None:
                raise RuntimeError("Android tidak dapat mendekode gambar yang dipilih.")

            filename = "product_" + datetime.now().strftime("%Y%m%d%H%M%S%f") + ".png"
            target = os.path.join(self.images_dir, filename)

            FileOutputStream = autoclass("java.io.FileOutputStream")
            output_stream = FileOutputStream(target)
            CompressFormat = autoclass("android.graphics.Bitmap$CompressFormat")
            if not bitmap.compress(CompressFormat.PNG, 100, output_stream):
                raise RuntimeError("Gambar gagal dikonversi ke PNG.")
            output_stream.flush()

            if not os.path.isfile(target) or os.path.getsize(target) <= 0:
                raise RuntimeError("File foto tidak berhasil dibuat.")
            return target
        except Exception as error:
            self.log_error("COPY_CONTENT_URI", error)
            return ""
        finally:
            if output_stream is not None:
                try: output_stream.close()
                except Exception: pass
            if input_stream is not None:
                try: input_stream.close()
                except Exception: pass
            if bitmap is not None:
                try: bitmap.recycle()
                except Exception: pass

    # --------------------------------------------------------
    # DESKTOP PICKER
    # --------------------------------------------------------

    def open_desktop_picker(
        self,
        selected,
        preview
    ):

        try:

            from kivy.uix.filechooser import FileChooserListView
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

            popup = style_popup(Popup(
                title="Pilih Foto Produk",
                content=root,
                size_hint=(.94, None),
                size=(dp(430), min(dp(560), max(dp(360), Window.height * .82)))
            ))

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
    # SAVE RECEIPT LOGO
    # --------------------------------------------------------

    def save_receipt_logo(self, path):
        """Simpan logo struk ke nama tetap agar path stabil di Android."""
        if not path:
            return ""
        try:
            source = self.resolve_image(path) or os.path.abspath(str(path))
            if not os.path.isfile(source):
                return ""
            os.makedirs(self.images_dir, exist_ok=True)
            destination = os.path.join(self.images_dir, "receipt_logo.png")
            shutil.copy2(source, destination)
            return destination if os.path.isfile(destination) and os.path.getsize(destination) > 0 else ""
        except Exception as error:
            self.log_error("SAVE_RECEIPT_LOGO", error)
            return ""

    def save_named_image(self, path, filename):
        if not path:
            return ""
        try:
            source = self.resolve_image(path) or os.path.abspath(str(path))
            if not os.path.isfile(source):
                return ""
            os.makedirs(self.images_dir, exist_ok=True)
            destination = os.path.join(self.images_dir, filename)
            shutil.copy2(source, destination)
            return destination if os.path.isfile(destination) and os.path.getsize(destination) > 0 else ""
        except Exception as error:
            self.log_error("SAVE_NAMED_IMAGE", error)
            return ""

    # --------------------------------------------------------
    # SAVE SELECTED IMAGE
    # --------------------------------------------------------

    def save_selected_image(self, path):
        if not path:
            return ""
        try:
            source = os.path.abspath(str(path))
            if not os.path.isfile(source):
                return ""
            images_dir = os.path.abspath(self.images_dir)
            os.makedirs(images_dir, exist_ok=True)
            if source.startswith(images_dir + os.sep):
                return source

            destination = os.path.join(
                images_dir,
                "product_" + datetime.now().strftime("%Y%m%d%H%M%S%f") + ".png"
            )
            # Normalize to PNG when Pillow is present. This also strips problematic
            # CMYK/EXIF combinations and gives Kivy one consistent image format.
            try:
                from PIL import Image as PILImage
                with PILImage.open(source) as im:
                    if im.mode not in ("RGB", "RGBA"):
                        im = im.convert("RGBA")
                    im.save(destination, "PNG", optimize=True)
            except Exception:
                shutil.copy2(source, destination)

            return destination if os.path.isfile(destination) and os.path.getsize(destination) > 0 else ""
        except Exception as error:
            self.log_error("SAVE_SELECTED_IMAGE", error)
            return ""


    def open_barcode_scanner(self, pos_screen=None):
        self._barcode_screen = pos_screen
        if platform != "android":
            self.notify("Di desktop, klik kolom pencarian lalu scan dengan barcode scanner USB/Bluetooth atau ketik kode dan Enter.")
            return
        try:
            from jnius import autoclass
            from android.activity import bind
            Intent = autoclass("android.content.Intent")
            intent = Intent("com.google.zxing.client.android.SCAN")
            intent.putExtra("SCAN_MODE", "PRODUCT_MODE")
            bind(on_activity_result=self.on_activity_result)
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            PythonActivity.mActivity.startActivityForResult(intent, 9002)
        except Exception:
            self.notify("Aplikasi scanner kompatibel belum tersedia. Anda bisa memakai scanner Bluetooth/USB atau ketik barcode lalu Enter.")

    def create_backup(self, manual=False):
        self.db.conn.commit()
        backup_dir = os.path.join(self.user_data_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = os.path.join(backup_dir, f"KasirQU_{stamp}.db")
        shutil.copy2(self.db.path, target)
        latest = os.path.join(self.user_data_dir, "KasirQU_backup.db")
        shutil.copy2(self.db.path, latest)
        # Keep last 10 timestamped backups
        files = sorted([os.path.join(backup_dir,f) for f in os.listdir(backup_dir) if f.endswith('.db')], reverse=True)
        for old in files[10:]:
            try: os.remove(old)
            except Exception: pass
        return target

    def restore_latest_backup(self):
        latest = os.path.join(self.user_data_dir, "KasirQU_backup.db")
        if not os.path.isfile(latest):
            raise FileNotFoundError("Backup belum tersedia.")
        self.db.conn.commit(); self.db.conn.close()
        safety = self.db.path + ".before_restore"
        if os.path.isfile(self.db.path): shutil.copy2(self.db.path, safety)
        shutil.copy2(latest, self.db.path)
        self.db = DB(self.db.path)

    def auto_backup(self):
        try:
            if self.db.setting("auto_backup") != "0": self.create_backup(manual=False)
        except Exception as error:
            self.log_error("AUTO_BACKUP", error)

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

        popup = style_popup(Popup(
            title="Struk",
            content=content,
            size_hint=(.88, None),
            size=(dp(400), dp(170))
        ))

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

    def auto_print_saved_receipt(self):
        """Cetak otomatis memakai printer yang sudah dipilih di Pengaturan."""
        address = self.db.setting("printer_address")
        if not address:
            self.notify("Transaksi tersimpan. Printer Bluetooth belum dipilih di Pengaturan.")
            return
        self.print_bluetooth(address, silent=False)

    def print_saved_receipt(self):
        """Cetak ulang transaksi terakhir dengan printer tersimpan."""
        address = self.db.setting("printer_address")
        if not address:
            self.notify("Pilih printer Bluetooth sekali di Pengaturan terlebih dahulu.")
            return
        self.print_bluetooth(address, silent=False)

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

        popup = style_popup(Popup(
            title="Pilih Printer Bluetooth",
            content=content,
            size_hint=(.92, None),
            size=(dp(430), min(dp(460), max(dp(300), Window.height * .72)))
        ))

        for name, address in devices:

            row = Card(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(66),
                padding=[dp(10), dp(7)],
                spacing=dp(8)
            )

            info = BoxLayout(
                orientation="vertical",
                spacing=dp(1)
            )
            name_label = Label(
                text=name or "Printer Bluetooth",
                color=TEXT,
                bold=True,
                font_size="13sp",
                halign="left",
                valign="middle",
                shorten=True,
                shorten_from="right"
            )
            name_label.bind(size=lambda w, v: setattr(w, "text_size", v))
            addr_label = Label(
                text=address,
                color=MUTED,
                font_size="10sp",
                halign="left",
                valign="middle",
                shorten=True,
                shorten_from="right"
            )
            addr_label.bind(size=lambda w, v: setattr(w, "text_size", v))
            info.add_widget(name_label)
            info.add_widget(addr_label)

            connect = make_button(
                "PILIH",
                primary=True,
                height=40
            )
            connect.size_hint_x = None
            connect.width = dp(72)
            connect.bind(
                on_release=lambda *_,
                addr=address: (
                    popup.dismiss(),
                    self.select_printer(addr)
                )
            )

            row.add_widget(info)
            row.add_widget(connect)
            content.add_widget(row)

        fit_popup(
            popup, content,
            min_width=dp(330),
            max_width=dp(500),
            min_height=dp(210),
            max_height_ratio=0.82,
            extra_height=dp(70)
        )

        popup.open()

    def select_printer(self, address):
        try:
            self.db.set_setting("printer_address", address)
            try:
                settings = self.root.ids.sm.get_screen("settings")
                settings.ids.printer_status.text = "Printer: " + address
            except Exception:
                pass
            self.notify("Printer Bluetooth dipilih:\n" + address)
        except Exception as error:
            self.log_error("SELECT_PRINTER", error); self.notify("Printer gagal disimpan.")

    def test_saved_printer(self):
        address = self.db.setting("printer_address")
        if not address:
            self.notify("Pilih printer Bluetooth terlebih dahulu.")
            return
        self.print_raw_bluetooth(address, b"\x1b@KasirQU - TEST PRINT\nPrinter terhubung.\n\n\n")

    def print_raw_bluetooth(self, address, payload):
        if platform != "android":
            self.notify("Test printer Bluetooth hanya tersedia pada Android.")
            return
        socket = None
        try:
            from jnius import autoclass
            BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
            UUID = autoclass("java.util.UUID")
            adapter = BluetoothAdapter.getDefaultAdapter()
            if adapter is None: raise RuntimeError("Bluetooth tidak tersedia.")
            device = adapter.getRemoteDevice(address)
            uuid = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
            socket = device.createRfcommSocketToServiceRecord(uuid)
            try: adapter.cancelDiscovery()
            except Exception: pass
            socket.connect(); output = socket.getOutputStream(); output.write(payload); output.flush()
            self.notify("Test print berhasil dikirim.")
        except Exception as error:
            self.log_error("RAW_BLUETOOTH_PRINT", error); self.notify("Gagal terhubung ke printer:\n" + str(error))
        finally:
            if socket is not None:
                try: socket.close()
                except Exception: pass

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

    def print_bluetooth(self, address=None, silent=False):

        if not address:
            address = self.db.setting("printer_address")
        if not address:
            self.notify("Printer Bluetooth belum dipilih di Pengaturan.")
            return

        if not self.last_receipt:
            self.notify("Belum ada struk yang bisa dicetak. Gunakan TEST PRINT di Pengaturan untuk mengetes koneksi.")
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

            payload = self.build_receipt_bytes()
            # Kirim bertahap supaya buffer printer Bluetooth tidak overflow.
            chunk_size = 512
            for start in range(0, len(payload), chunk_size):
                output.write(payload[start:start + chunk_size])
                try:
                    import time
                    time.sleep(0.015)
                except Exception:
                    pass
            output.flush()
            try:
                import time
                time.sleep(0.20)
            except Exception:
                pass

            if not silent:
                self.notify("Struk berhasil dikirim.")

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

    def _receipt_logo_raster(self, path, max_width):
        """Konversi logo ke ESC/POS ESC * mode 0 dengan rotasi 180 derajat."""
        if not path:
            return b""
        try:
            path = self.resolve_image(path) or os.path.abspath(str(path))
            if not os.path.isfile(path):
                self.log_error("RECEIPT_LOGO_PATH", FileNotFoundError(path))
                return b""
            from kivy.core.image import Image as CoreImage
            ci = CoreImage(path)
            texture = ci.texture
            if texture is None:
                return b""
            w, h = int(texture.width), int(texture.height)
            pixels = texture.pixels
            if not pixels or w < 1 or h < 1:
                return b""

            paper = self.db.setting("paper") or "58mm"
            target_width = 64 if paper == "58mm" else 96
            target_height = 48 if paper == "58mm" else 64
            if max_width:
                target_width = min(target_width, int(max_width))
            scale = min(1.0, float(target_width) / float(w), float(target_height) / float(h))
            nw = max(1, int(w * scale))
            nh = max(1, int(h * scale))
            out = bytearray()

            # ESC * mode 0 = 8 vertical dots per column.
            # X dan Y source dibalik untuk koreksi rotasi 180 derajat.
            for band_top in range(0, nh, 8):
                out += bytes([0x1B, 0x2A, 0x00, nw & 0xFF, (nw >> 8) & 0xFF])
                for x in range(nw):
                    byte = 0
                    sx = min(w - 1, int((nw - 1 - x) / scale))
                    for bit in range(8):
                        y_out = band_top + bit
                        if y_out >= nh:
                            continue
                        sy = min(h - 1, int(y_out / scale))
                        idx = (sy * w + sx) * 4
                        if idx + 3 >= len(pixels):
                            continue
                        r = pixels[idx]
                        g = pixels[idx + 1]
                        b = pixels[idx + 2]
                        a = pixels[idx + 3]
                        if a < 60:
                            continue
                        lum = (0.299 * r) + (0.587 * g) + (0.114 * b)
                        if lum < 205:
                            byte |= (0x80 >> bit)
                    out.append(byte)
                out += b"\n"
            return bytes(out)
        except Exception as error:
            self.log_error("RECEIPT_LOGO_RASTER", error)
            return b""

    def _receipt_columns(self, left, right, width):
        left = printer_text(left).replace("\n", " ")
        right = printer_text(right).replace("\n", " ")
        if len(right) >= width:
            return right[:width]
        max_left = max(1, width - len(right) - 1)
        if len(left) > max_left:
            left = left[:max_left - 1] + "..."
        return left + (" " * (width - len(left) - len(right))) + right

    def _receipt_item_line(self, name, qty, price, line_total, width):
        # Nama di kiri, total di kanan; detail qty x harga di bawahnya.
        return [
            printer_text(name)[:width],
            self._receipt_columns(
                f"{qty:g} x {money(price)}",
                money(line_total),
                width
            )
        ]

    def build_receipt_bytes(self):
        (
            invoice, subtotal, discount, tax, total,
            method, paid, change, cart
        ) = self.last_receipt

        paper = self.db.setting("paper") or "58mm"
        width = 32 if paper == "58mm" else 48
        logo_width = 64 if paper == "58mm" else 96

        store = self.db.setting("store_name") or APP_NAME
        address = self.db.setting("store_address") or ""
        footer = self.db.setting("receipt_footer") or "Terima kasih"
        cashier = self.db.setting("cashier_name") or "Kasir"
        logo_setting = self.db.setting("receipt_logo") or ""
        logo_path = self.resolve_image(logo_setting)
        if logo_setting and not logo_path:
            self.log_error("RECEIPT_LOGO_NOT_FOUND", FileNotFoundError(str(logo_setting)))

        out = bytearray(b"\x1b\x40")
        out += b"\x1b\x74\x00"  # ESC t 0
        out += b"\x1b\x52\x00"  # ESC R 0
        out += b"\x1b\x7b\x00"  # ESC { 0
        out += b"\x1b\x4d\x00"  # ESC M 0
        out += b"\x1b\x32"       # ESC 2

        # Logo: center, raster image, lalu kembali ke kiri.
        logo = self._receipt_logo_raster(logo_path, logo_width)
        if logo:
            out += b"\x1b\x61\x01" + logo + b"\x1b\x61\x00"

        # Header tetap rapi/center.
        out += b"\x1b\x45\x01"
        header = [store.center(width)]
        if address.strip():
            header.append(address.center(width))
        out += ("\n".join(header) + "\n").encode("ascii", "replace")
        out += b"\x1b\x45\x00"
        out += ("-" * width + "\n").encode("ascii")

        out += (invoice + "\n").encode("ascii", "replace")
        out += (self._receipt_columns("Tanggal", datetime.now().strftime("%d/%m/%Y %H:%M"), width) + "\n").encode("ascii", "replace")
        out += (self._receipt_columns("Kasir", cashier, width) + "\n").encode("ascii", "replace")
        out += ("-" * width + "\n").encode("ascii")

        for item in cart:
            for line in self._receipt_item_line(
                item["name"], item["qty"], item["price"],
                item["qty"] * item["price"], width
            ):
                out += (line + "\n").encode("ascii", "replace")

        out += ("-" * width + "\n").encode("ascii")
        totals = [
            ("Subtotal", money(subtotal)),
            ("Diskon", money(discount)),
            ("Pajak", money(tax)),
            ("TOTAL", money(total)),
            ("Bayar", money(paid)),
            ("Kembali", money(change)),
            ("Metode", method),
        ]
        for label, value in totals:
            line = self._receipt_columns(label, value, width)
            if label == "TOTAL":
                out += b"\x1b\x45\x01"
                out += (line + "\n").encode("ascii", "replace")
                out += b"\x1b\x45\x00"
            else:
                out += (line + "\n").encode("ascii", "replace")

        out += ("-" * width + "\n").encode("ascii")
        out += footer.center(width).encode("ascii", "replace") + b"\n\n\n"
        out += b"\x1d\x56\x00"
        return bytes(out)


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
