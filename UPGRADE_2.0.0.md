# KasirQU 2.0.1 – Professional POS Upgrade

Upgrade besar dari basis 1.6.7 dengan fokus pada kestabilan dan fitur POS nyata.

## Fitur baru
- Dashboard laporan: omzet, transaksi, barang terjual, laba kotor, produk terlaris, stok menipis.
- Stok pintar: restock, histori pergerakan stok di database, stok otomatis berkurang saat transaksi dan kembali saat void.
- Barcode: SKU berfungsi sebagai barcode; scanner USB/Bluetooth dapat langsung input + Enter. Tombol SCAN mencoba membuka scanner Android kompatibel (ZXing intent) dan memiliki fallback manual.
- Void transaksi: transaksi dapat dibatalkan dan stok otomatis dikembalikan.
- Backup: backup manual, backup otomatis setiap transaksi berhasil, menyimpan 10 backup timestamp terbaru, dan restore backup terakhir.
- Database safety: PRAGMA foreign_keys, WAL, integrity_check.
- Printer thermal: pemilihan printer disimpan di Pengaturan, status printer tampil, dan tersedia TEST PRINT.
- Pengaturan operasional: nama kasir, role Owner/Admin/Kasir, batas stok menipis.
- Role dasar: Kasir tidak dapat menghapus produk dan membuka laporan.
- Export laporan penjualan dan export stok ke CSV.
- Struk menampilkan nama kasir.
- UI Pengaturan kini scrollable agar aman pada layar Android pendek.

## Catatan barcode
Tombol SCAN menggunakan Android intent `com.google.zxing.client.android.SCAN`. Jika perangkat tidak memiliki aplikasi scanner yang menyediakan intent tersebut, KasirQU tetap mendukung barcode scanner USB/Bluetooth (keyboard mode) atau input kode manual lalu Enter.

## Migrasi
Database versi lama dimigrasikan otomatis dengan menambahkan kolom/tabel baru tanpa menghapus data produk maupun transaksi lama.
