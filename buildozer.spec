
[app]

title = افهم قانون
package.name = afhamqanun
package.domain = org.elhapony

source.dir = .
source.include_exts = py,db,png,jpg,jpeg,kv,ttf,json

version = 1.0

requirements = python3,kivy,arabic-reshaper,python-bidi

orientation = portrait
fullscreen = 0

android.permissions = INTERNET

android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a

android.accept_sdk_license = True

android.allow_backup = True

[buildozer]

log_level = 2
warn_on_root = 1
