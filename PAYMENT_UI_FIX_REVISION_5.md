# KasirQU 2.0.4 - Payment UI Fix Revision 5

Perbaikan berdasarkan screenshot aktual pengguna.

## Perbaikan
- Popup Pembayaran dibuat responsif terhadap lebar layar.
- Kartu Transfer Bank / E-Wallet pada konfirmasi dibuat lebih tinggi dan lebar.
- Nomor rekening/akun dan nama pemilik tidak lagi dipaksa wrap secara vertikal.
- Metode pembayaran memakai teks yang lebih pendek agar tidak terpotong.
- Bagian Tunai selalu menampilkan field Uang Diterima dan KEMBALIAN sebagai area terpisah di bawah metode pembayaran.
- Popup Keranjang dibuat lebih compact untuk 1-2 item dan scroll untuk banyak item.
- Baris Diskon + TOTAL dibuat dengan lebar tetap yang aman agar total tidak keluar layar.
- Tombol PILIH PEMBAYARAN dibuat berada penuh di dalam popup.
- QRIS confirmation dipadatkan agar tombol konfirmasi tetap terlihat.
- Flow konfirmasi tetap: simpan transaksi -> kosongkan keranjang -> kembali Kasir -> backup -> auto print.

## Validasi
- main.py lolos `python -m py_compile`.
- Tidak mengubah database schema atau printer implementation.
