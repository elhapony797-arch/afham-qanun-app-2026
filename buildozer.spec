[app]

title = Alhabouni
package.name = alhabouni2
package.domain = org.elhapony

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,ttf,json

version = 1.0

requirements = python3,kivy==2.3.0,arabic-reshaper==3.0.1,python-bidi==0.4.2,openssl,requests,urllib3,chardet,idna,certifi

orientation = portrait
fullscreen = 0

android.permissions = INTERNET

android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = armeabi-v7a
android.enable_androidx = True
android.allow_backup = True

android.accept_sdk_license = True

p4a.branch = v2024.01.21

android.release_artifact = apk

[buildozer]

log_level = 2
warn_on_root = 1
