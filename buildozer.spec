[app]

Nama aplikasi

title = KasirQU

Package

package.name = kasirqu
package.domain = org.kasirqu

Versi aplikasi

version = 1.0.0

File utama

source.dir = .

File yang ikut dimasukkan ke APK

source.include_exts = py,png,jpg,jpeg,kv,json,atlas,ttf,otf,txt,csv,db

File yang tidak perlu dimasukkan

source.exclude_exts = spec,log,md

Orientasi aplikasi

orientation = portrait

Fullscreen

fullscreen = 0

Background presplash

presplash.filename = assets/presplash.png

Icon aplikasi

icon.filename = assets/icon.png

--------------------------------------------------PYTHON DEPENDENCIES--------------------------------------------------JANGAN tambahkan requests di sini.requests akan menarik charset-normalizer,urllib3, certifi, dan dependency lain yangmenyebabkan masalah pada Android build.

requirements = python3,kivy==2.3.1,pyjnius

--------------------------------------------------ANDROID--------------------------------------------------

android.api = 35
android.minapi = 24

android.ndk = 27c
android.ndk_api = 24

android.archs = arm64-v8a

android.accept_sdk_license = True

android.permissions = INTERNET,BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

android.private_storage = True

android.enable_androidx = True

android.gradle_dependencies = androidx.appcompat:appcompat:1.7.0

--------------------------------------------------JAVA / BUILD--------------------------------------------------

android.entrypoint = org.kivy.android.PythonActivity

android.add_src = android

android.add_aidl =

--------------------------------------------------APP BEHAVIOR--------------------------------------------------

android.allow_backup = True
android.debug_artifact = apk

--------------------------------------------------KIVY--------------------------------------------------

[buildozer]

log_level = 2

warn_on_root = 0

