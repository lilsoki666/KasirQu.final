# KasirQU 2.0.4 — Professional UI Final

Basis: KasirQU 2.0.4 UI Navigation Clean Crash Fixed / Professional UI payment-account implementation.

## Visual
- Pengaturan rebuilt with compact white cards, thin borders, consistent spacing and blue primary actions.
- QRIS and receipt-logo sections use + select and trash icon actions.
- Bank and e-wallet accounts render as compact cards with provider, number, owner, Edit and trash actions.
- Dynamic account lists avoid oversized empty areas.
- Payment account selection popup uses compact horizontal cards.
- Payment confirmation popup is large and readable; QRIS is shown at a large scanning size.

## Functional preservation
- SQLite products, sales, sale items, settings and payment accounts.
- Product image picker/storage.
- QRIS image storage and instruction text.
- Multiple bank/e-wallet accounts.
- Cash, QRIS, transfer and e-wallet checkout flow.
- Bluetooth printer selection, test print, automatic receipt printing and reprint.
- Transaction history, void, reports, CSV export, backup/restore and database integrity check.
- Bottom navigation: Kasir / Produk / Pengaturan.

## Important
This source was syntax-checked with Python. Kivy/Android runtime is not available in the build environment used for this preparation, so the final APK should still be tested on the target Android device. Existing database files are migrated by the app; do not delete the existing app data before testing.
