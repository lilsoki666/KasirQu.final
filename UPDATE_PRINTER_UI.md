# KasirQU 2.0.4 - Printer & UI Revision

Perubahan utama pada revisi ini:

1. Printer Bluetooth dipilih dan dihubungkan dari menu Pengaturan.
2. Koneksi RFCOMM disimpan selama aplikasi berjalan, sehingga checkout dan cetak ulang tidak lagi membuka pemilih printer atau melakukan koneksi ulang.
3. Setelah transaksi berhasil, struk langsung dikirim ke printer yang sedang terhubung.
4. Cetak ulang dari Riwayat Transaksi langsung menggunakan printer yang sedang terhubung.
5. Jika koneksi printer terputus, aplikasi menutup koneksi yang rusak dan meminta pengguna menghubungkan ulang dari Pengaturan.
6. Test Print menggunakan koneksi printer yang sama.
7. Ukuran kertas (58mm/80mm) dipindahkan ke atas pilihan printer di Pengaturan.
8. Tombol `+ Produk` dipindahkan ke samping kolom pencarian pada menu Produk.
9. Header utama setiap menu dibuat rata tengah.
10. Icon toolbar PNG tetap menggunakan file di `assets/icons/`.

## Alur printer

- Buka **Pengaturan**.
- Pilih **ukuran kertas**.
- Tekan **PILIH & HUBUNGKAN PRINTER BLUETOOTH**.
- Pilih printer yang sudah dipairing Android.
- Tunggu status berubah menjadi **TERHUBUNG**.
- Tekan **TEST PRINT** jika ingin mengetes.
- Setelah itu transaksi dapat dicetak langsung tanpa memilih printer lagi.

Catatan: koneksi Bluetooth adalah koneksi runtime Android. Jika aplikasi benar-benar ditutup atau proses Android dihentikan, koneksi socket tidak dapat dipertahankan; pada sesi aplikasi berikutnya printer perlu dihubungkan kembali dari Pengaturan.
