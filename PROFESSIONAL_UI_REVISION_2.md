# KasirQU 2.0.4 - Professional UI Revision 2

Basis: KasirQU 2.0.4 UI Navigation Clean Crash Fixed / current working project.

Focus of this revision:
- Settings layout uses compact professional cards and removes oversized empty spaces.
- QRIS, bank accounts and e-wallet accounts use compact bordered rows.
- Payment account rows show provider, number, owner, Edit and trash action.
- Account selection popup is larger and more compact.
- Payment confirmation popup is enlarged; QRIS preview is enlarged and centered.
- Existing database, checkout, printer, receipt, product, history and report logic is preserved.
- Spinner for 58mm/80mm paper is preserved.

Validation performed:
- Python syntax check passed with `python -m py_compile main.py`.
- Kivy/Android runtime is not available in the build environment, so APK runtime validation must be done by building the project.
