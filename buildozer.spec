
[app]

title = افهم قانون
package.name = afhamqanun
package.domain = org.elhapony
source.dir = .
source.include_exts = py,db,png,jpg,kv,ttf,json
version = 1.0

requirements = python3,kivy,arabic-reshaper,python-bidi

orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.api = 35
android.minapi = 23
android.archs = arm64-v8a, armeabi-v7a

android.accept_sdk_license = True

[buildozer]

log_level = 2
warn_on_root = 1
