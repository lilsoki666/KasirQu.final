KasirQU 2.0.4 - Cart & UI refinement

# KasirQU Android POS

Versi revisi startup-stability dan Android image picker.

## Perbaikan
- Startup tidak lagi mengembalikan `BoxLayout` kosong ketika UI gagal dimuat.
- Error startup ditulis ke `KasirQU_error.log` agar penyebab blank screen dapat dilacak.
- Ekspresi KV yang rawan parser error dirapikan menjadi ekspresi satu baris.
- Swipe antar halaman tetap menggunakan `SlideTransition`.
- Pemilih foto Android menggunakan `ACTION_OPEN_DOCUMENT`.
- Foto dari `content://` disalin ke penyimpanan internal aplikasi.
- Ekstensi foto mengikuti MIME asli (JPG/PNG/WebP).
- Database tetap berada di `App.user_data_dir`.
- Icon disiapkan dalam ukuran 512x512.
- Workflow GitHub Actions menyediakan `workflow_dispatch` dan pemeriksaan syntax Python.

## Build
GitHub → Actions → Build KasirQU APK → Run workflow.


## Versi 1.6.0 – Perbaikan UI & Fitur
- Toolbar memakai icon PNG dari `assets/icons/` (256x256).
- Popup dibuat lebih ringkas dan responsif terhadap ukuran layar.
- Form produk mendukung tambah dan edit produk.
- Foto produk disimpan ke folder internal aplikasi dan ditampilkan kembali.
- Riwayat transaksi dapat dibuka untuk melihat detail dan cetak ulang.
- Laporan menampilkan jumlah barang terjual selain omzet.
- Pengaturan ditambah input pajak dan refresh data.
- Database lama dimigrasikan otomatis untuk kolom produk, penjualan, dan item penjualan.
