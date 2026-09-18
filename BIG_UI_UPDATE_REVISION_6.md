# KasirQU 2.0.4 - BIG UI UPDATE Revision 6

Basis: PAYMENT_UI_FIX_REVISION_5.

Target: supplied DESIGN_REFERENCE_REVISION_3 mockup.

## UI changes
- Consistent blue app bar on Kasir, Produk, Transaksi, Laporan, Pengaturan.
- Real KasirQU toolbar/bottom-navigation icons from `assets/icons/`.
- Kasir product tiles use the full tile as the add-to-cart target.
- Four-column product grid retained for phone POS density.
- Product management/search/category layout tightened.
- Transaction/history and report pages use the same visual system.
- Settings grouped into compact cards for Toko & Struk, Pembayaran, Operasional, Printer, and Data & Keamanan.
- Checkout popup redesigned to keep item rows, discount, total and payment button inside the viewport.
- Payment popup redesigned with four clearly separated payment cards and an always-visible cash/change area.
- Bank/E-Wallet account selection and confirmation cards use non-wrapping account fields.
- QRIS confirmation uses a bounded QR area and keeps confirmation controls visible.

## Preserved systems
- SQLite database and migrations
- Product photos/picker
- Stock/restock/void
- Sales history and reprint
- QRIS / bank / e-wallet accounts
- Bluetooth printer and ESC/POS receipt flow
- Automatic printing after checkout
- Backup/restore and CSV exports
- Existing role checks and error logging

`main.py` passes Python syntax compilation. Buildozer/Python-for-Android runtime must still be tested by building the APK on the target Android environment.
