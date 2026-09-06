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
