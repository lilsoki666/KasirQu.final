# KasirQU 1.6.1 - UI startup fix

Perbaikan penting:
- `IconNavButton.__init__` menerima `name` dan `icon` sebagai keyword/default arguments sehingga tidak memicu `missing 2 required positional arguments` saat KV Builder membuat widget.
- Folder `assets/icons/` wajib ikut dalam APK dan berisi 5 icon PNG toolbar.
- Icon toolbar dinormalisasi ke 256x256 PNG.
