# KasirQU 2.0.4 - Final UI + Printer Update

Pembaruan final berdasarkan source KasirQU 2.0.4:

- Logo struk thermal diperkecil dan dibatasi tinggi agar tetap kecil di atas header.
- Koreksi rotasi logo 180 derajat pada raster ESC/POS ESC * mode 0.
- Teks struk dinormalisasi ke ASCII untuk mencegah karakter/simbol acak pada printer thermal.
- Pengiriman Bluetooth struk dikirim bertahap 512 byte dengan jeda agar buffer printer tidak overflow.
- Printer yang dipilih di Pengaturan dipakai otomatis setelah transaksi dan untuk cetak ulang.
- Highlight toolbar aktif menggunakan border biru.
- Swipe antar menu ikut memperbarui highlight toolbar.
- Grid produk kasir tetap 4 kolom dengan lebar kartu konsisten.
- Tombol + PRODUK tetap berada di samping pencarian produk.
- Tombol HAPUS produk tetap merah dan EDIT tetap biru.
- Pengaturan dikelompokkan; pajak dan batas stok dua kolom.
- Tombol SIMPAN PENGATURAN dipindahkan ke bawah TEST PRINT sesuai layout yang diminta.
- Logo struk disimpan ke storage aplikasi dengan nama stabil.
- Import CoreImage/FileChooser dibuat lazy untuk mengurangi risiko crash saat presplash/startup Android.
- Startup trace ditulis ke KasirQU_startup.log untuk diagnosis bila build membuka layar error.

Fitur transaksi, database, backup/restore, CSV, stok, void transaksi, foto produk, Bluetooth printer, cetak otomatis, dan cetak ulang dipertahankan.
