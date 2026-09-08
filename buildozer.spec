[app]

title = KasirQU
package.name = kasirqu
package.domain = com.kasirqu

source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,kv,atlas,json,txt,ttf,otf,csv
source.exclude_dirs = .git,.github,.buildozer,bin,__pycache__,docs

version = 1.6.4

orientation = portrait
fullscreen = 0

icon.filename = assets/icon.png
presplash.filename = assets/presplash.png

requirements = python3,kivy==2.3.1,pyjnius

android.api = 35
android.minapi = 24

android.ndk = 27c
android.ndk_api = 24

android.archs = arm64-v8a

android.debug_artifact = apk
android.release_artifact = apk

android.accept_sdk_license = True

android.permissions = INTERNET,BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN,READ_MEDIA_IMAGES

android.enable_androidx = True

p4a.bootstrap = sdl2
p4a.branch = develop

[buildozer]

log_level = 2
warn_on_root = 0
