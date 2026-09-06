[app]

title = KasirQU
package.name = kasirqu
package.domain = com.kasirqu

source.dir = .
source.main = main.py
source.include_exts = py,png,jpg,jpeg,webp,kv,atlas,json,txt,ttf,otf
source.exclude_dirs = .git,.github,.buildozer,bin,__pycache__,docs

version = 1.5.0

requirements = python3,kivy==2.3.1

orientation = portrait
fullscreen = 0

icon.filename = assets/icon.png
presplash.filename = assets/presplash.png

android.api = 34
android.minapi = 24
android.ndk = 25b
android.build_tools_version = 34.0.0
android.archs = arm64-v8a

android.debug_artifact = apk
android.release_artifact = apk

android.permissions = BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN,READ_MEDIA_IMAGES

android.accept_sdk_license = True

p4a.bootstrap = sdl2

[buildozer]

log_level = 2
warn_on_root = 1
