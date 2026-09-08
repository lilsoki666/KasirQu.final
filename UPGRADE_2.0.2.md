# KasirQU 2.0.2

## Fix
- Fixed crash when opening the Keranjang popup.
- Reworked cart popup layout to use conservative Kivy sizing.
- Added guarded cart redraw and popup opening error handling.
- Payment opening is scheduled after popup dismissal to avoid layout/event collisions.
- Preserved existing product photos, toolbar, payment, stock, reporting, printer and barcode features.
