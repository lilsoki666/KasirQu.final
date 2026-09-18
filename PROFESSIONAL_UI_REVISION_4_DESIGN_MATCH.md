# KasirQU 2.0.4 — Professional UI Revision 4

This revision is based directly on the working Revision 3 project and focuses on matching the supplied Revision 3 design reference more closely while preserving the existing POS/database/printer functionality.

## UI alignment
- Blue app bar with KasirQU branding.
- Four-column product grid on Kasir.
- Compact cart summary at the bottom of Kasir.
- Cart checkout popup redesigned with product thumbnails, quantity controls, discount and total.
- Payment popup redesigned from a spinner into selectable payment cards for QRIS, Transfer Bank, E-Wallet and Tunai.
- Existing account-selection and payment-confirmation flows are preserved.
- Product page retains search, category filter, stock badge, Edit and Hapus.
- Settings retains Toko & Struk, QRIS, Transfer Bank, E-Wallet, Operasional, Bluetooth Printer and Data & Keamanan.
- Bottom navigation remains Kasir, Produk, Pengaturan.
- Existing Transactions and Reports remain accessible from Settings.

## Preserved functionality
- SQLite database and existing schema.
- Product photos and Android picker.
- Stock management.
- Discount and tax calculation.
- Transaction creation and history.
- QRIS, bank and e-wallet accounts.
- Bluetooth printer selection and test print.
- Automatic receipt printing after sale.
- Receipt reprint from transaction history.
- Backup and CSV export.
- Existing error logging and startup handling.

## Validation
- `main.py` passes Python bytecode compilation (`python -m py_compile`).
- This is a UI-focused revision; no intentional removal of existing business logic was made.
