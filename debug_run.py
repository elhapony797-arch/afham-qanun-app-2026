import os
import sys
import traceback

LOG = "crash_log.txt"
lines = []


def log(msg):
    print(msg)
    lines.append(str(msg))


log("python: " + sys.version)
log("cwd: " + os.getcwd())
log("font exists: %s" % os.path.exists("font.ttf"))
if os.path.exists("font.ttf"):
    log("font size: %d" % os.path.getsize("font.ttf"))

for m in ["requests", "certifi", "arabic_reshaper", "bidi.algorithm", "kivy"]:
    try:
        __import__(m)
        log("OK    " + m)
    except BaseException:
        log("FAIL  " + m)
        log(traceback.format_exc())

try:
    import kivy
    log("kivy version: " + kivy.__version__)
    import main
    log("main imported")
    main.MushrifApp().run()
    log("app closed normally")
except BaseException:
    log("CRASH:")
    log(traceback.format_exc())
finally:
    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
