# -*- coding: utf-8 -*-
import os,csv,shutil,sqlite3,traceback
from datetime import datetime
from decimal import Decimal,ROUND_HALF_UP
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color,RoundedRectangle
from kivy.metrics import dp,sp
from kivy.properties import StringProperty,NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen,ScreenManager,SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import platform

APP_NAME='KasirQU'; DB_NAME='KasirQU.db'; IMAGE_REQUEST_CODE=9001

def money(v):
    try:return 'Rp {:,}'.format(Decimal(str(v)).quantize(Decimal('1'),rounding=ROUND_HALF_UP)).replace(',','.')
    except:return 'Rp 0'
def num(v,d=0):
    try:return float(str(v).strip() or d)
    except:return d

class Panel(BoxLayout):
    radius=NumericProperty(dp(16))
    def __init__(self,**kw):
        bg=kw.pop('bg',(1,1,1,1));super().__init__(**kw)
        with self.canvas.before:
            self.c=Color(*bg);self.r=RoundedRectangle(pos=self.pos,size=self.size,radius=[self.radius])
        self.bind(pos=self._u,size=self._u,radius=self._u)
    def _u(self,*a):self.r.pos=self.pos;self.r.size=self.size;self.r.radius=[self.radius]

class Btn(Button):
    def __init__(self,text='',kind='primary',**kw):
        self.kind=kind;super().__init__(text=text,size_hint_y=None,height=dp(44),background_normal='',background_down='',border=(0,0,0,0),**kw)
        self.n=(.10,.31,.78,1) if kind=='primary' else ((.94,.95,.98,1) if kind=='soft' else (.95,.90,.90,1))
        self.d=(.07,.23,.61,1) if kind=='primary' else ((.86,.89,.94,1) if kind=='soft' else (.88,.82,.82,1))
        self.color=(1,1,1,1) if kind=='primary' else ((.09,.12,.18,1) if kind=='soft' else (.70,.12,.12,1));self.bold=True
        with self.canvas.after:self.bc=Color(*self.n);self.br=RoundedRectangle(pos=self.pos,size=self.size,radius=[dp(12)])
        self.bind(pos=self._u,size=self._u,state=self._s)
    def _u(self,*a):self.br.pos=self.pos;self.br.size=self.size
    def _s(self,*a):self.bc.rgba=self.d if self.state=='down' else self.n

class Nav(Btn):
    def __init__(self,icon,label,**kw):
        super().__init__(f'{icon}\n{label}',kind='soft',height=60,**kw);self.icon=icon;self.label=label;self.background_color=(1,1,1,0);self.font_size=sp(10)
    def active(self,x):self.color=(.10,.31,.78,1) if x else (.42,.46,.53,1)

class Swipe(ScreenManager):
    def __init__(self,**kw):super().__init__(**kw);self.s=None
    def on_touch_down(self,t):self.s=t.pos;return super().on_touch_down(t)
    def on_touch_up(self,t):
        s=self.s;r=super().on_touch_up(t)
        if s:
            dx=t.x-s[0];dy=t.y-s[1]
            if abs(dx)>dp(90) and abs(dx)>abs(dy)*1.4:self.go(-1 if dx>0 else 1)
        self.s=None;return r
    def go(self,d):
        ns=self.screen_names;i=ns.index(self.current);j=i+d
        if 0<=j<len(ns):self.transition=SlideTransition(direction='right' if d<0 else 'left',duration=.18);self.current=ns[j]

class DB:
    def __init__(self,p):
        self.path=p;os.makedirs(os.path.dirname(p),exist_ok=True);self.c=sqlite3.connect(p,check_same_thread=False,timeout=10);self.c.row_factory=sqlite3.Row;self.setup()
    def setup(self):
        self.c.executescript('''CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,sku TEXT DEFAULT '',category TEXT DEFAULT '',price REAL NOT NULL DEFAULT 0,cost REAL NOT NULL DEFAULT 0,stock REAL NOT NULL DEFAULT 0,image TEXT DEFAULT '',active INTEGER DEFAULT 1,created_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY AUTOINCREMENT,invoice TEXT UNIQUE NOT NULL,subtotal REAL NOT NULL,discount REAL NOT NULL,tax REAL NOT NULL,total REAL NOT NULL,payment_method TEXT NOT NULL,paid REAL NOT NULL,change_amount REAL NOT NULL,created_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS sale_items(id INTEGER PRIMARY KEY AUTOINCREMENT,sale_id INTEGER NOT NULL,product_id INTEGER NOT NULL,name TEXT NOT NULL,qty REAL NOT NULL,price REAL NOT NULL,line_total REAL NOT NULL);CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);''')
        for k,v in {'store_name':'KasirQU','store_address':'Alamat / Kontak','receipt_footer':'Terima kasih telah berbelanja','paper':'58mm','tax_percent':'0'}.items():self.c.execute('INSERT OR IGNORE INTO settings VALUES(?,?)',(k,v))
        self.c.commit()
    def setting(self,k):
        r=self.c.execute('SELECT value FROM settings WHERE key=?',(k,)).fetchone();return r['value'] if r else ''
    def set(self,k,v):self.c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(k,str(v)));self.c.commit()
    def products(self,q=''):
        q='%'+q.strip()+'%';return self.c.execute('SELECT * FROM products WHERE active=1 AND (name LIKE ? OR sku LIKE ? OR category LIKE ?) ORDER BY name',(q,q,q)).fetchall()
    def add(self,n,s,cat,p,cost,stock,img):
        self.c.execute('INSERT INTO products(name,sku,category,price,cost,stock,image,created_at) VALUES(?,?,?,?,?,?,?,?)',(n,s,cat,p,cost,stock,img,datetime.now().isoformat(timespec='seconds')));self.c.commit()
    def sales(self,limit=100):return self.c.execute('SELECT * FROM sales ORDER BY id DESC LIMIT ?',(limit,)).fetchall()
    def sale(self,cart,sub,disc,tax,total,method,paid,change):
        inv='INV-'+datetime.now().strftime('%Y%m%d%H%M%S%f');cur=self.c.cursor()
        try:
            self.c.execute('BEGIN');cur.execute('INSERT INTO sales(invoice,subtotal,discount,tax,total,payment_method,paid,change_amount,created_at) VALUES(?,?,?,?,?,?,?,?,?)',(inv,sub,disc,tax,total,method,paid,change,datetime.now().isoformat(timespec='seconds')));sid=cur.lastrowid
            for x in cart:
                r=cur.execute('SELECT stock FROM products WHERE id=? AND active=1',(x['id'],)).fetchone()
                if not r or r['stock']<x['qty']:raise ValueError('Stok tidak mencukupi: '+x['name'])
                cur.execute('INSERT INTO sale_items(sale_id,product_id,name,qty,price,line_total) VALUES(?,?,?,?,?,?)',(sid,x['id'],x['name'],x['qty'],x['price'],x['qty']*x['price']))
                cur.execute('UPDATE products SET stock=stock-? WHERE id=?',(x['qty'],x['id']))
            self.c.commit();return inv
        except Exception:self.c.rollback();raise

class Base(Screen):
    def __init__(self,**kw):
        super().__init__(**kw)
        with self.canvas.before:self.bc=Color(.96,.97,.985,1);self.br=RoundedRectangle(pos=self.pos,size=self.size)
        self.bind(pos=self._bg,size=self._bg)
    def _bg(self,*a):self.br.pos=self.pos;self.br.size=self.size
    def header(self,title,sub=''):
        b=BoxLayout(orientation='vertical',size_hint_y=None,height=dp(58));b.add_widget(Label(text=title,color=(.06,.08,.12,1),font_size=sp(21),bold=True,halign='left'));b.add_widget(Label(text=sub,color=(.44,.48,.54,1),font_size=sp(10),halign='left'));return b

class POS(Base):
    def __init__(self,**kw):
        super().__init__(**kw);self.cart=[];root=BoxLayout(orientation='vertical',padding=[dp(12),dp(10)],spacing=dp(8));root.add_widget(self.header('KasirQU','Penjualan cepat & mudah'))
        self.search=TextInput(hint_text='Cari produk atau SKU...',multiline=False,size_hint_y=None,height=dp(45),padding=[dp(13),dp(10)],background_normal='',background_color=(1,1,1,1));self.search.bind(text=self.refresh);root.add_widget(self.search)
        root.add_widget(Label(text='Pilih produk',color=(.25,.29,.35,1),size_hint_y=None,height=dp(25),halign='left'))
        sc=ScrollView(do_scroll_x=False);self.grid=GridLayout(cols=2,spacing=dp(9),padding=dp(2),size_hint_y=None);self.grid.bind(minimum_height=self.grid.setter('height'));sc.add_widget(self.grid);root.add_widget(sc)
        bar=Panel(orientation='horizontal',size_hint_y=None,height=dp(68),padding=dp(9),spacing=dp(7));self.count=Label(text='0 item',color=(.1,.13,.18,1),bold=True,size_hint_x=.25);self.total=Label(text='Rp 0',color=(.1,.31,.78,1),font_size=sp(17),bold=True,halign='right');bar.add_widget(self.count);bar.add_widget(self.total);b=Btn('LIHAT',kind='soft',size_hint_x=.25);b.bind(on_release=lambda *_:self.cart_popup());bar.add_widget(b);root.add_widget(bar);self.add_widget(root)
    def on_enter(self):self.app=App.get_running_app();self.refresh();self.summary()
    def refresh(self,*_):
        if not getattr(self,'app',None):return
        self.grid.clear_widgets();ps=self.app.db.products(self.search.text)
        if not ps:self.grid.cols=1;self.grid.add_widget(Label(text='Belum ada produk.',color=(.45,.49,.56,1),size_hint_y=None,height=dp(80)));return
        self.grid.cols=2
        for p in ps:self.grid.add_widget(self.card(p))
    def card(self,p):
        c=Panel(orientation='vertical',size_hint_y=None,height=dp(215),padding=dp(7),spacing=dp(4))
        path=self.app.image(p['image'])
        if path:c.add_widget(Image(source=path,size_hint_y=.58,allow_stretch=True,keep_ratio=True,nocache=True))
        else:c.add_widget(Label(text='▣',color=(.58,.62,.68,1),font_size=sp(30),size_hint_y=.58))
        c.add_widget(Label(text=f"{p['name']}\n{money(p['price'])}  •  stok {float(p['stock']):g}",color=(.09,.12,.18,1),font_size=sp(11),halign='center',valign='middle'))
        b=Btn('+ Tambah',height=34);b.bind(on_release=lambda *_:self.add(p));c.add_widget(b);return c
    def add(self,p):
        stock=float(p['stock'])
        if stock<=0:return self.app.notify('Stok produk habis.')
        for x in self.cart:
            if x['id']==p['id']:
                if x['qty']>=stock:return self.app.notify('Jumlah melebihi stok.')
                x['qty']+=1;self.summary();return
        self.cart.append({'id':p['id'],'name':p['name'],'price':float(p['price']),'qty':1,'stock':stock});self.summary()
    def calc(self,d=0,t=None):
        sub=sum(x['qty']*x['price'] for x in self.cart);d=max(0,num(d));t=num(self.app.tax if t is None else t);tax=max(0,sub-d)*max(0,t)/100;return sub,d,tax,max(0,sub-d+tax)
    def summary(self):
        if not getattr(self,'app',None):return
        _,_,_,tot=self.calc();self.count.text=f"{sum(x['qty'] for x in self.cart):g} item";self.total.text=money(tot)
    def cart_popup(self):
        if not self.cart:return self.app.notify('Keranjang masih kosong.')
        box=BoxLayout(orientation='vertical',padding=dp(9),spacing=dp(7));sc=ScrollView();rows=GridLayout(cols=1,spacing=dp(5),size_hint_y=None);rows.bind(minimum_height=rows.setter('height'));sc.add_widget(rows);box.add_widget(sc);disc=TextInput(text='0',hint_text='Diskon',input_filter='float',multiline=False,size_hint_y=None,height=dp(42));tax=TextInput(text=self.app.tax,hint_text='Pajak %',input_filter='float',multiline=False,size_hint_y=None,height=dp(42));tl=Label(color=(.1,.31,.78,1),bold=True,font_size=sp(17),size_hint_y=None,height=dp(35),halign='right');box.add_widget(disc);box.add_widget(tax);box.add_widget(tl);buttons=BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(6));clear=Btn('Kosongkan',kind='danger');pay=Btn('BAYAR');buttons.add_widget(clear);buttons.add_widget(pay);box.add_widget(buttons);pop=Popup(title='Keranjang',content=box,size_hint=(.94,.86))
        def draw(*_):
            rows.clear_widgets()
            for i,x in enumerate(self.cart):
                r=Panel(orientation='horizontal',size_hint_y=None,height=dp(52),padding=dp(4),spacing=dp(3),bg=(.97,.98,1,1));r.add_widget(Label(text=f"{x['name']}\n{x['qty']:g} × {money(x['price'])}",halign='left'));m=Btn('−',kind='soft',height=36,size_hint_x=None,width=dp(38));q=Btn('+',kind='soft',height=36,size_hint_x=None,width=dp(38));z=Btn('×',kind='danger',height=36,size_hint_x=None,width=dp(38));m.bind(on_release=lambda *_ ,i=i:self.qty(i,-1,draw));q.bind(on_release=lambda *_ ,i=i:self.qty(i,1,draw));z.bind(on_release=lambda *_ ,i=i:self.rem(i,draw));r.add_widget(m);r.add_widget(q);r.add_widget(z);rows.add_widget(r)
            tl.text='TOTAL  '+money(self.calc(disc.text,tax.text)[3])
        disc.bind(text=draw);tax.bind(text=draw);clear.bind(on_release=lambda *_:(self.cart.clear(),self.summary(),pop.dismiss()));pay.bind(on_release=lambda *_:(pop.dismiss(),self.payment(disc.text,tax.text)));pop.open();draw()
    def qty(self,i,d,cb):
        if 0<=i<len(self.cart):
            self.cart[i]['qty']+=d
            if self.cart[i]['qty']<=0:self.cart.pop(i)
            elif self.cart[i]['qty']>self.cart[i]['stock']:self.cart[i]['qty']=self.cart[i]['stock']
        self.summary();cb()
    def rem(self,i,cb):
        if 0<=i<len(self.cart):self.cart.pop(i)
        self.summary();cb()
    def payment(self,d,t):
        sub,d,tax,total=self.calc(d,t);box=BoxLayout(orientation='vertical',padding=dp(10),spacing=dp(7));box.add_widget(Label(text=f'TOTAL\n{money(total)}',font_size=sp(22),bold=True,color=(.1,.31,.78,1),size_hint_y=None,height=dp(70)));method=Spinner(text='Tunai',values=('Tunai','QRIS','Debit','Kredit','Transfer','E-Wallet'),size_hint_y=None,height=dp(44));paid=TextInput(hint_text='Uang diterima',input_filter='float',multiline=False,size_hint_y=None,height=dp(44));change=Label(text='Kembalian Rp 0',size_hint_y=None,height=dp(38),bold=True);box.add_widget(method);box.add_widget(paid);box.add_widget(change);row=BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(6));cancel=Btn('Batal',kind='soft');done=Btn('SELESAIKAN');row.add_widget(cancel);row.add_widget(done);box.add_widget(row);pop=Popup(title='Pembayaran',content=box,size_hint=(.92,.68))
        def upd(*_):
            if method.text=='Tunai':paid.disabled=False;change.text='Kembalian '+money(max(0,num(paid.text)-total))
            else:paid.text='';paid.disabled=True;change.text='Pembayaran non-tunai'
        def finish(*_):
            pv=num(paid.text)
            if method.text=='Tunai' and pv<total:return self.app.notify('Uang kurang '+money(total-pv))
            if method.text!='Tunai':pv=total
            try:
                inv=self.app.db.sale(self.cart,sub,d,tax,total,method.text,pv,max(0,pv-total));self.cart=[];self.summary();pop.dismiss();self.app.navigate('transactions');self.app.notify('Transaksi '+inv+' berhasil.')
            except Exception as e:self.app.log('CHECKOUT',e);self.app.notify('Transaksi gagal:\n'+str(e))
        paid.bind(text=upd);method.bind(text=upd);cancel.bind(on_release=pop.dismiss);done.bind(on_release=finish);pop.open();upd()

class Products(Base):
    def __init__(self,**kw):
        super().__init__(**kw);root=BoxLayout(orientation='vertical',padding=[dp(12),dp(10)],spacing=dp(8));add=Btn('+  Produk',size_hint_x=None,width=dp(110),height=42);add.bind(on_release=lambda *_:self.editor());h=BoxLayout(size_hint_y=None,height=dp(58));h.add_widget(self.header('Produk','Kelola produk, stok dan foto'));h.add_widget(add);root.add_widget(h);self.search=TextInput(hint_text='Cari nama, SKU atau kategori...',multiline=False,size_hint_y=None,height=dp(45),padding=[dp(13),dp(10)],background_normal='',background_color=(1,1,1,1));self.search.bind(text=self.refresh);root.add_widget(self.search);sc=ScrollView(do_scroll_x=False);self.grid=GridLayout(cols=1,spacing=dp(8),size_hint_y=None);self.grid.bind(minimum_height=self.grid.setter('height'));sc.add_widget(self.grid);root.add_widget(sc);self.add_widget(root)
    def on_enter(self):self.app=App.get_running_app();self.refresh()
    def refresh(self,*_):
        self.grid.clear_widgets()
        for p in self.app.db.products(self.search.text):
            r=Panel(orientation='horizontal',size_hint_y=None,height=dp(88),padding=dp(7),spacing=dp(8));path=self.app.image(p['image']);r.add_widget(Image(source=path,size_hint_x=None,width=dp(78),allow_stretch=True) if path else Label(text='▣',font_size=sp(28),size_hint_x=None,width=dp(78),color=(.58,.62,.68,1)));r.add_widget(Label(text=f"{p['name']}\n{money(p['price'])}  •  stok {float(p['stock']):g}\n{p['category'] or 'Tanpa kategori'}",color=(.09,.12,.18,1),halign='left'));self.grid.add_widget(r)
    def editor(self):
        box=BoxLayout(orientation='vertical',padding=dp(9),spacing=dp(6));sc=ScrollView();form=BoxLayout(orientation='vertical',spacing=dp(6),size_hint_y=None);form.bind(minimum_height=form.setter('height'));preview=Image(size_hint_y=None,height=dp(145),allow_stretch=True,keep_ratio=True);form.add_widget(preview);fields={}
        for k,h in [('name','Nama produk *'),('sku','SKU / Barcode'),('category','Kategori'),('price','Harga jual'),('cost','Harga modal'),('stock','Stok')]:fields[k]=TextInput(hint_text=h,multiline=False,size_hint_y=None,height=dp(42));form.add_widget(fields[k])
        choose=Btn('▣  Pilih Foto Produk',kind='soft');form.add_widget(choose);sc.add_widget(form);box.add_widget(sc);row=BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(6));cancel=Btn('Batal',kind='soft');save=Btn('Simpan Produk');row.add_widget(cancel);row.add_widget(save);box.add_widget(row);selected={'path':''};pop=Popup(title='Tambah Produk',content=box,size_hint=(.94,.90));choose.bind(on_release=lambda *_:self.app.pick(selected,preview));cancel.bind(on_release=pop.dismiss)
        def do(*_):
            n=fields['name'].text.strip()
            if not n:return self.app.notify('Nama produk wajib diisi.')
            img=self.app.save_image(selected['path']) if selected['path'] else ''
            if selected['path'] and not img:return self.app.notify('Foto gagal disimpan.')
            try:self.app.db.add(n,fields['sku'].text.strip(),fields['category'].text.strip(),num(fields['price'].text),num(fields['cost'].text),num(fields['stock'].text),img);pop.dismiss();self.refresh();self.app.pos.refresh();self.app.notify('Produk berhasil ditambahkan.')
            except Exception as e:self.app.log('SAVE_PRODUCT',e);self.app.notify(str(e))
        save.bind(on_release=do);pop.open()

class Transactions(Base):
    def __init__(self,**kw):
        super().__init__(**kw);root=BoxLayout(orientation='vertical',padding=[dp(12),dp(10)],spacing=dp(8));root.add_widget(self.header('Riwayat Transaksi','Transaksi terbaru'));sc=ScrollView(do_scroll_x=False);self.grid=GridLayout(cols=1,spacing=dp(8),size_hint_y=None);self.grid.bind(minimum_height=self.grid.setter('height'));sc.add_widget(self.grid);root.add_widget(sc);self.add_widget(root)
    def on_enter(self):self.app=App.get_running_app();self.refresh()
    def refresh(self):
        self.grid.clear_widgets();rows=self.app.db.sales()
        if not rows:self.grid.add_widget(Label(text='Belum ada transaksi.',color=(.45,.49,.56,1),size_hint_y=None,height=dp(80)));return
        for s in rows:
            r=Panel(orientation='horizontal',size_hint_y=None,height=dp(75),padding=dp(9));r.add_widget(Label(text=f"{s['invoice']}\n{s['created_at']} • {s['payment_method']}",halign='left',color=(.09,.12,.18,1)));r.add_widget(Label(text=money(s['total']),size_hint_x=.34,color=(.1,.31,.78,1),bold=True));self.grid.add_widget(r)

class Reports(Base):
    def __init__(self,**kw):
        super().__init__(**kw);root=BoxLayout(orientation='vertical',padding=[dp(12),dp(10)],spacing=dp(8));root.add_widget(self.header('Laporan','Ringkasan penjualan hari ini'));self.summary=Label(color=(.09,.12,.18,1),font_size=sp(15),halign='left',valign='top');root.add_widget(Panel(orientation='vertical',padding=dp(15),size_hint_y=None,height=dp(190),children=[]));root.children[0].add_widget(self.summary);b=Btn('⇩  Export CSV');b.bind(on_release=lambda *_:self.export());root.add_widget(b);root.add_widget(Widget());self.add_widget(root)
    def on_enter(self):self.app=App.get_running_app();self.refresh()
    def refresh(self):
        r=self.app.db.c.execute("SELECT COUNT(*) n,COALESCE(SUM(subtotal),0) sub,COALESCE(SUM(discount),0) dis,COALESCE(SUM(tax),0) tax,COALESCE(SUM(total),0) total FROM sales WHERE date(created_at)=date('now')").fetchone();self.summary.text=f"HARI INI\n\nTransaksi : {r['n']}\nSubtotal  : {money(r['sub'])}\nDiskon    : {money(r['dis'])}\nPajak     : {money(r['tax'])}\nPenjualan : {money(r['total'])}"
    def export(self):
        try:
            p=os.path.join(self.app.user_data_dir,'sales_export.csv');f=open(p,'w',newline='',encoding='utf-8-sig');w=csv.writer(f);w.writerow(['Invoice','Tanggal','Subtotal','Diskon','Pajak','Total','Pembayaran','Dibayar','Kembalian']);[w.writerow([s['invoice'],s['created_at'],s['subtotal'],s['discount'],s['tax'],s['total'],s['payment_method'],s['paid'],s['change_amount']]) for s in self.app.db.sales(10000)];f.close();self.app.notify('CSV tersimpan:\n'+p)
        except Exception as e:self.app.log('EXPORT',e)

class Settings(Base):
    def __init__(self,**kw):
        super().__init__(**kw);root=BoxLayout(orientation='vertical',padding=[dp(12),dp(10)],spacing=dp(8));root.add_widget(self.header('Pengaturan','Informasi toko dan struk'));self.store=TextInput(hint_text='Nama usaha',multiline=False,size_hint_y=None,height=dp(44));self.address=TextInput(hint_text='Alamat / kontak',multiline=False,size_hint_y=None,height=dp(44));self.footer=TextInput(hint_text='Footer struk',multiline=False,size_hint_y=None,height=dp(44));self.paper=Spinner(text='58mm',values=['58mm','80mm'],size_hint_y=None,height=dp(44));self.tax=TextInput(text='0',hint_text='Pajak %',input_filter='float',multiline=False,size_hint_y=None,height=dp(44));[root.add_widget(x) for x in (self.store,self.address,self.footer,self.paper,self.tax)];b=Btn('Simpan Pengaturan');b.bind(on_release=lambda *_:self.save());root.add_widget(b);bk=Btn('Backup Database',kind='soft');bk.bind(on_release=lambda *_:self.backup());root.add_widget(bk);root.add_widget(Widget());self.add_widget(root)
    def on_enter(self):
        self.app=App.get_running_app();self.store.text=self.app.db.setting('store_name');self.address.text=self.app.db.setting('store_address');self.footer.text=self.app.db.setting('receipt_footer');self.paper.text=self.app.db.setting('paper') or '58mm';self.tax.text=self.app.db.setting('tax_percent') or '0'
    def save(self):
        for k,v in [('store_name',self.store.text),('store_address',self.address.text),('receipt_footer',self.footer.text),('paper',self.paper.text),('tax_percent',self.tax.text or '0')]:self.app.db.set(k,v)
        self.app.tax=self.tax.text or '0';self.app.notify('Pengaturan disimpan.')
    def backup(self):
        try:p=os.path.join(self.app.user_data_dir,'KasirQU_backup.db');self.app.db.c.commit();shutil.copy2(self.app.db.path,p);self.app.notify('Backup dibuat:\n'+p)
        except Exception as e:self.app.log('BACKUP',e)

class KasirQU(App):
    tax=StringProperty('0')
    def __init__(self,**kw):super().__init__(**kw);self.startup_error=None;self.pending=None
    def log(self,where,e):
        try:
            p=os.path.join(self.user_data_dir,'KasirQU_error.log');os.makedirs(os.path.dirname(p),exist_ok=True)
            with open(p,'a',encoding='utf8') as f:f.write('\n\n'+datetime.now().isoformat()+'\n'+where+'\n'+repr(e)+'\n'+traceback.format_exc())
        except:pass
    def build(self):
        try:
            os.makedirs(self.user_data_dir,exist_ok=True);self.images_dir=os.path.join(self.user_data_dir,'products');os.makedirs(self.images_dir,exist_ok=True);self.db=DB(os.path.join(self.user_data_dir,DB_NAME));self.tax=self.db.setting('tax_percent') or '0';root=BoxLayout(orientation='vertical');self.sm=Swipe();self.pos=POS(name='pos');self.products=Products(name='products');self.transactions=Transactions(name='transactions');self.reports=Reports(name='reports');self.settings=Settings(name='settings');[self.sm.add_widget(x) for x in (self.pos,self.products,self.transactions,self.reports,self.settings)];root.add_widget(self.sm);bar=Panel(orientation='horizontal',size_hint_y=None,height=dp(67),padding=dp(4),spacing=dp(2));self.nav={};items=[('pos','⌂','Kasir'),('products','▣','Produk'),('transactions','↺','Riwayat'),('reports','▥','Laporan'),('settings','⚙','Pengaturan')]
            for n,i,l in items:
                b=Nav(i,l);b.bind(on_release=lambda *_ ,n=n:self.navigate(n));self.nav[n]=b;bar.add_widget(b)
            root.add_widget(bar);return root
        except Exception as e:self.startup_error=e;self.log('STARTUP',e);return Label(text='KasirQU\n\nGagal memuat UI.\n'+str(e),halign='center')
    def on_start(self):Clock.schedule_once(self.start,0.25)
    def start(self,*a):
        if not self.startup_error:self.pos.refresh();self.active('pos')
        if platform=='android':
            try:
                from android import loadingscreen;loadingscreen.hide_loading_screen()
            except Exception:pass
    def active(self,n):
        for k,b in self.nav.items():b.active(k==n)
    def navigate(self,n):
        names=list(self.sm.screen_names);cur=names.index(self.sm.current);tar=names.index(n);self.sm.transition=SlideTransition(direction='left' if tar>cur else 'right',duration=.18);self.sm.current=n;self.active(n)
    def notify(self,msg):Popup(title=APP_NAME,content=Label(text=str(msg),halign='center',valign='middle'),size_hint=(.86,.30)).open()
    def image(self,p):
        if not p:return ''
        for x in (p,os.path.join(self.user_data_dir,p),os.path.join(self.images_dir,os.path.basename(p))):
            try:
                x=os.path.abspath(x)
                if os.path.isfile(x):return x
            except:pass
        return ''
    def pick(self,selected,preview):
        if platform!='android':return self.desktop_pick(selected,preview)
        try:
            from jnius import autoclass
            from android.activity import bind
            I=autoclass('android.content.Intent');P=autoclass('org.kivy.android.PythonActivity');i=I(I.ACTION_OPEN_DOCUMENT);i.addCategory(I.CATEGORY_OPENABLE);i.setType('image/*');self.pending=(selected,preview);bind(on_activity_result=self.activity_result);P.mActivity.startActivityForResult(i,IMAGE_REQUEST_CODE)
        except Exception as e:self.log('PICKER',e);self.notify('Pemilih foto gagal dibuka.')
    def activity_result(self,request,result,intent):
        try:
            if request!=IMAGE_REQUEST_CODE or intent is None:return
            uri=intent.getData()
            if uri is None or not self.pending:return
            selected,preview=self.pending;p=self.copy_uri(uri)
            if not p:return self.notify('Foto tidak dapat dibaca.')
            selected['path']=p;preview.source=p;preview.reload()
        except Exception as e:self.log('IMAGE_RESULT',e)
        finally:self.pending=None
    def copy_uri(self,uri):
        inp=out=None
        try:
            from jnius import autoclass
            P=autoclass('org.kivy.android.PythonActivity');F=autoclass('java.io.FileOutputStream');r=P.mActivity.getContentResolver();inp=r.openInputStream(uri)
            if inp is None:raise RuntimeError('InputStream kosong')
            mime=str(r.getType(uri) or 'image/jpeg');ext={ 'image/png':'.png','image/webp':'.webp','image/gif':'.gif'}.get(mime,'.jpg');p=os.path.join(self.images_dir,'product_'+datetime.now().strftime('%Y%m%d%H%M%S%f')+ext);out=F(p);buf=bytearray(16384)
            while True:
                n=inp.read(buf)
                if n is None or int(n)<=0:break
                out.write(buf,0,int(n))
            out.flush()
            return p if os.path.isfile(p) and os.path.getsize(p)>0 else ''
        except Exception as e:self.log('COPY_URI',e);return ''
        finally:
            try:out.close()
            except:pass
            try:inp.close()
            except:pass
    def desktop_pick(self,selected,preview):
        ch=FileChooserListView(path=os.path.expanduser('~'),filters=['*.jpg','*.jpeg','*.png','*.webp']);box=BoxLayout(orientation='vertical');row=BoxLayout(size_hint_y=None,height=dp(44));ok=Btn('Pilih');no=Btn('Batal',kind='soft');row.add_widget(no);row.add_widget(ok);box.add_widget(ch);box.add_widget(row);pop=Popup(title='Pilih Foto',content=box,size_hint=(.92,.88))
        def choose(*a):
            if ch.selection:
                p=self.save_image(ch.selection[0]);selected['path']=p;preview.source=p;preview.reload();pop.dismiss()
        ok.bind(on_release=choose);no.bind(on_release=pop.dismiss);pop.open()
    def save_image(self,p):
        try:
            if not p or not os.path.isfile(p):return ''
            ext=os.path.splitext(p)[1].lower();ext=ext if ext in ('.jpg','.jpeg','.png','.webp','.gif') else '.jpg';d=os.path.join(self.images_dir,'product_'+datetime.now().strftime('%Y%m%d%H%M%S%f')+ext);shutil.copyfile(p,d);return d if os.path.getsize(d)>0 else ''
        except Exception as e:self.log('SAVE_IMAGE',e);return ''

if __name__=='__main__':KasirQU().run()
