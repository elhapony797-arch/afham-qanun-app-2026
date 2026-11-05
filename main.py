import json
import os
import re
import threading
import time
import traceback
from datetime import date, datetime

import kivy

from kivy.app import App
from kivy.base import ExceptionHandler, ExceptionManager
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import NoTransition, Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton

# ---------------------------------------------------------------
# استيراد المكتبات الخارجية بحماية: إن نقصت مكتبة يظهر تنبيه
# على الشاشة بدل أن ينهار التطبيق عند الإقلاع.
# ---------------------------------------------------------------
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_AR = True
except Exception:
    HAS_AR = False
    print(traceback.format_exc())

try:
    import requests
    HAS_REQUESTS = True
except Exception:
    HAS_REQUESTS = False
    print(traceback.format_exc())

try:
    import certifi
    HAS_CERTIFI = True
except Exception:
    HAS_CERTIFI = False


API_URL = "https://elhaponi-app.elhaponyabdo66.workers.dev/"
FONT = "font.ttf"
HISTORY_LIMIT = 30

GOLD = (0.9, 0.75, 0.3, 1)
MUTED = (0.7, 0.7, 0.75, 1)
GREEN = (0.5, 0.85, 0.5, 1)
RED = (0.95, 0.45, 0.45, 1)
WHITE = (1, 1, 1, 1)

# ---------------------------------------------------------------
# التعليمة الأساسية: المشرف يوجّه الطالب ولا يكتب الرسالة بدلًا عنه
# ---------------------------------------------------------------
SYSTEM_BASE = (
    "أنت مشرف أكاديمي متخصص في الدراسات القانونية العليا، "
    "تساعد طالبًا يعدّ رسالة ماجستير أو دكتوراه. "
    "وجّه الطالب وأرشده، ولا تكتب الرسالة أو فصولها بدلًا عنه. "
    "ميّز دائمًا بين ثلاثة مستويات: (نص قانوني مؤكد)، (رأي فقهي منسوب)، "
    "(اجتهاد مني يحتاج تحققًا). "
    "لا تختلق مواد قانونية أو أحكامًا قضائية أو مراجع أو أرقام صفحات، "
    "وإن لم تكن متأكدًا فقل صراحة: لا أعلم، وأرشد الطالب أين يتحقق. "
    "اكتب بالعربية الفصحى السليمة وبعلامات الترقيم العربية (، ؛ ؟). "
    "اكتب إحالات المواد هكذا: المادة (12) من القانون المدني. "
    "إذا ذكرت مصطلحًا أجنبيًا فاجعله بين قوسين مرة واحدة فقط بعد المقابل العربي. "
    "اجعل الرد منظمًا بعناوين قصيرة وفقرات واضحة، "
    "ولا تستخدم رموز التنسيق مثل ** أو # أو ` لأن الشاشة تعرض نصًا عاديًا."
)

# مراحل إعداد الرسالة
MODES = {
    "اقتراح إشكالية": (
        "اقترح ثلاث إشكاليات بحثية قابلة للدراسة في الموضوع المذكور، "
        "ولكل إشكالية: صياغتها، وأهميتها، والمنهج الأنسب لها، "
        "وأبرز صعوباتها المتوقعة."
    ),
    "فجوات بحثية": (
        "حدد الاتجاهات الدراسية المعروفة في هذا الموضوع، ثم بيّن "
        "الفجوات البحثية المحتملة التي لم تُعالج بعمق، وانبّه إلى ما "
        "يحتاج الطالب أن يتحقق من وجوده في الدراسات السابقة."
    ),
    "بناء خطة": (
        "اقترح هيكلًا للرسالة (فصول ومباحث ومطالب) وفق المنهج المذكور، "
        "وبيّن منطق الانتقال بين الأجزاء، ونبّه إلى أي خلل في التوازن "
        "أو تكرار محتمل."
    ),
    "مراجعة نص": (
        "راجع النص المرفق كمشرف أكاديمي: قيّم وضوح الفكرة، وسلامة "
        "الاستدلال القانوني، والتماسك، والصياغة، وحدد مواضع تحتاج "
        "توثيقًا، دون إعادة كتابة النص كاملًا."
    ),
    "أسئلة المناقشة": (
        "اطرح الأسئلة التي قد تسألها لجنة المناقشة على الطالب بخصوص "
        "المحتوى المذكور، مرتبة من الأسهل إلى الأصعب، مع إشارة مختصرة "
        "إلى محاور الإجابة الجيدة دون تقديم إجابة جاهزة."
    ),
    "شرح مفهوم": (
        "اشرح المفهوم أو القاعدة القانونية بأسلوب أكاديمي مبسط "
        "مع مثال تطبيقي، وبيّن ما هو متفق عليه وما هو محل خلاف."
    ),
    "مقارنة قانونية": (
        "قارن بين النظامين القانونيين المذكورين في المسألة المطروحة: "
        "أوجه الاتفاق والاختلاف والعلة من كل حكم. لا تنسب نصًا برقم "
        "مادة إلا إن كنت متأكدًا، وإلا فاذكر المبدأ العام ونبّه الطالب "
        "إلى ضرورة التحقق من النص الرسمي. إن لم يُحدد نظام المقارنة "
        "فاطلب من الطالب تحديده."
    ),
    "تدقيق المنهج": (
        "قيّم سلامة المنهج المذكور وتناسبه مع الإشكالية والخطة، وحدد "
        "نقاط الضعف المنهجية في الإشكالية والفرضيات وأدوات البحث، "
        "واقترح كيف يعالجها الطالب بنفسه."
    ),
}

FOOTER = (
    "\n\nتنبيه: للاستئناس البحثي فقط. تحقق من النصوص الرسمية والمراجع "
    "الأصلية قبل اعتماد أي معلومة في رسالتك."
)

# مستويات خطة الرسالة
PLAN_LEVELS = {1: "الفصل", 2: "المبحث", 3: "المطلب"}
ORDINALS = [
    "الأول", "الثاني", "الثالث", "الرابع", "الخامس",
    "السادس", "السابع", "الثامن", "التاسع", "العاشر",
]

# أنواع المراجع وتلميحات حقولها
REF_TYPES = [
    ("book", "كتاب"),
    ("article", "مقال أو بحث"),
    ("law", "تشريع"),
    ("case", "حكم قضائي"),
    ("thesis", "رسالة جامعية"),
]
REF_HINTS = {
    "book": ["المؤلف", "عنوان الكتاب", "الناشر", "مكان النشر",
             "سنة النشر", "الصفحات (للهامش)"],
    "article": ["المؤلف", "عنوان المقال", "اسم المجلة",
                "مكان النشر أو العدد", "السنة", "الصفحات"],
    "law": ["الجهة المصدرة (اختياري)", "اسم القانون ورقمه",
            "الجريدة الرسمية", "المكان", "سنة الإصدار", "رقم المادة"],
    "case": ["(اختياري)", "رقم الطعن أو عنوان القضية", "المحكمة",
             "المكان", "السنة", "الصفحة أو رقم المبدأ"],
    "thesis": ["الباحث", "عنوان الرسالة",
               "الجامعة والدرجة (ماجستير أو دكتوراه)",
               "الكلية أو المكان", "السنة", "الصفحات"],
}

DEFAULT_TASKS = [
    "تحديد الموضوع وصياغة الإشكالية",
    "جمع الدراسات السابقة ومراجعتها",
    "إعداد خطة الرسالة واعتمادها من المشرف",
    "كتابة المقدمة",
    "كتابة الفصل الأول",
    "كتابة الفصل الثاني",
    "كتابة الفصل الثالث",
    "كتابة الخاتمة والنتائج والتوصيات",
    "ضبط التوثيق وقائمة المراجع",
    "المراجعة اللغوية والشكلية",
    "التسليم والاستعداد للمناقشة",
]


# ===============================================================
# معالجة النص العربي
# ---------------------------------------------------------------
# القاعدة الذهبية:
#   * النص "المنطقي" (الأصلي) هو الذي يُخزَّن ويُنسخ ويُرسل للخادم.
#   * النص "البصري" (بعد التشكيل وقلب الاتجاه) للعرض فقط، ولا يُحفظ.
# ===============================================================

def _version_tuple():
    nums = re.findall(r"\d+", kivy.__version__)[:3]
    return tuple(int(n) for n in nums) + (0,) * (3 - len(nums))


# من Kivy 2.2 يدعم TextInput الاتجاه من اليمين لليسار أصليًا
NATIVE_RTL_INPUT = _version_tuple() >= (2, 2, 0)

_RESHAPER = None
if HAS_AR:
    try:
        _RESHAPER = arabic_reshaper.ArabicReshaper(configuration={
            "delete_harakat": True,
            "support_ligatures": True,
            "use_unshaped_instead_of_isolated": True,
        })
    except Exception:
        _RESHAPER = None

# محارف التحكم بالاتجاه التي تُفسد التقطيع عند اللصق من Word وغيره
_BIDI_CONTROLS = re.compile("[\u200e\u200f\u202a-\u202e\u2066-\u2069\ufeff]")
_DIGITS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

_measure_cache = {}
_font_name = {"value": "Roboto"}


def norm_digits(text):
    return str(text).translate(_DIGITS)


def sanitize_input(text):
    """تنظيف النص الذي يكتبه الطالب قبل إرساله."""
    text = _BIDI_CONTROLS.sub("", str(text))
    text = text.replace("\u0640", "")  # حذف التطويل (ـ)
    return text.strip()


def clean_markdown(text):
    """تحويل رموز Markdown إلى نص عادي مناسب للشاشة."""
    out = []
    for line in str(text).split("\n"):
        s = line.strip()
        s = re.sub(r"^#{1,6}\s*", "", s)
        s = re.sub(r"^[\*\-]\s+", "• ", s)
        s = s.replace("**", "").replace("__", "").replace("`", "")
        s = s.replace("*", "")
        out.append(s)
    return "\n".join(out)


def shape(line):
    """سطر واحد: تشكيل الحروف ثم ترتيبها بصريًا مع اتجاه أساسي RTL."""
    if not line or not HAS_AR:
        return line
    try:
        if _RESHAPER is not None:
            reshaped = _RESHAPER.reshape(line)
        else:
            reshaped = arabic_reshaper.reshape(line)
        return get_display(reshaped, base_dir="R")
    except Exception:
        return line


def _measure(text, font_size):
    try:
        key = (_font_name["value"], font_size)
        core = _measure_cache.get(key)
        if core is None:
            core = CoreLabel(
                font_name=_font_name["value"], font_size=font_size)
            _measure_cache[key] = core
        return core.get_extents(text)[0]
    except Exception:
        return len(text) * font_size * 0.5


def wrap_logical(paragraph, max_px, font_size):
    """
    تقطيع فقرة على مستوى الكلمات حسب العرض الفعلي بالبكسل.
    التقطيع يتم على النص المنطقي، ثم يُشكَّل كل سطر على حدة،
    فلا تنكسر الكلمات ولا يختل ترتيب الأسطر.
    """
    words = paragraph.split()
    if not words:
        return [""]
    px = sp(font_size)
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if not cur or _measure(shape(test), px) <= max_px:
            cur = test
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def ar(text, font_size=16, wrap=True, width=None):
    """نص عربي جاهز للعرض في Label أو Button."""
    if not wrap:
        return "\n".join(shape(l) for l in str(text).split("\n"))
    max_px = width if width else Window.width - dp(40)
    lines = []
    for para in str(text).split("\n"):
        for line in wrap_logical(para, max_px, font_size):
            lines.append(shape(line))
    return "\n".join(lines)


# ===============================================================
# خطة الرسالة: الترقيم التلقائي
# ===============================================================
def ordinal(n):
    return ORDINALS[n - 1] if 1 <= n <= len(ORDINALS) else str(n)


def number_plan(plan):
    """يعيد قائمة (المستوى، البادئة المرقمة، العنوان)."""
    counters = [0, 0, 0]
    result = []
    for item in plan:
        lvl = item.get("level", 1)
        if lvl not in PLAN_LEVELS:
            lvl = 1
        counters[lvl - 1] += 1
        for j in range(lvl, 3):
            counters[j] = 0
        prefix = "%s %s" % (PLAN_LEVELS[lvl], ordinal(counters[lvl - 1]))
        result.append((lvl, prefix, item.get("title", "")))
    return result


def plan_text(plan):
    """الخطة كنص منطقي عادي (للنسخ وللإرسال إلى المشرف)."""
    lines = []
    for lvl, prefix, title in number_plan(plan):
        lines.append("  " * (lvl - 1) + prefix + ": " + title)
    return "\n".join(lines)


# ===============================================================
# المراجع: التنسيق
# ===============================================================
def _j(parts, sep="، "):
    return sep.join(p for p in parts if p)


def _end(s):
    return s + "." if s and not s.endswith(".") else s


def fmt_arabic(r, foot=False):
    """النمط العربي الجامعي. foot=True يعطي صيغة الهامش."""
    t = r.get("type", "book")
    a = r.get("author", "")
    ti = r.get("title", "")
    so = r.get("source", "")
    pl = r.get("place", "")
    yr = r.get("year", "")
    pg = r.get("pages", "")
    pgs = ("ص " + pg) if pg else ""
    quoted = ("«%s»" % ti) if ti else ""

    if t == "article":
        parts = [a, quoted, so, pl, yr, pgs]
    elif t == "law":
        parts = [ti, so, pl, yr]
        if foot and pg:
            parts.append("المادة (%s)" % pg)
    elif t == "case":
        parts = [so, ti, pl, yr]
        if foot and pgs:
            parts.append(pgs)
    elif t == "thesis":
        parts = [a, quoted, ("رسالة " + so) if so else "", pl, yr]
        if foot and pgs:
            parts.append(pgs)
    else:
        parts = [a, ti, so, pl, yr]
        if foot and pgs:
            parts.append(pgs)
    return _end(_j(parts))


def fmt_apa(r, foot=False):
    """نمط APA تقريبي (المؤلف، السنة)."""
    t = r.get("type", "book")
    a = r.get("author", "") or r.get("source", "")
    ti = r.get("title", "")
    so = r.get("source", "")
    pl = r.get("place", "")
    yr = r.get("year", "")
    pg = r.get("pages", "")
    if foot:
        parts = [a or ti, yr, ("ص " + pg) if pg else ""]
        return "(" + _j(parts) + ")"
    head = ((a + " ") if a else "") + (("(" + yr + ").") if yr else "")
    tail = [so if so != a else "", pl]
    if t == "article" and pg:
        tail.append("ص " + pg)
    pieces = [head, _end(ti), _end(_j(tail))]
    return " ".join(p for p in pieces if p)


# ===============================================================
# مدقق الاتساق (آلي محلي، لا يستخدم الذكاء الاصطناعي)
# ===============================================================
def check_text(text, refs_count):
    t = text
    n = norm_digits(t)
    issues = []

    c = len(re.findall(r"[\u0600-\u06FF]\s*,", t))
    if c:
        issues.append(
            "تنبيه: فاصلة لاتينية (,) بعد كلمات عربية في %d موضع. "
            "استخدم الفاصلة العربية (،)." % c)
    c = len(re.findall(r"[\u0600-\u06FF]\s*\?", t))
    if c:
        issues.append(
            "تنبيه: علامة استفهام لاتينية (?) في %d موضع. "
            "استخدم (؟)." % c)
    c = len(re.findall(r"[\u0600-\u06FF]\s*;", t))
    if c:
        issues.append(
            "تنبيه: فاصلة منقوطة لاتينية (;) في %d موضع. "
            "استخدم (؛)." % c)

    if re.search("[٠-٩۰-۹]", t) and re.search("[0-9]", t):
        issues.append(
            "تنبيه: النص يخلط بين الأرقام الهندية والغربية. وحّد الأسلوب.")

    f_paren = len(re.findall(r"المادة\s*\(\s*\d+\s*\)", n))
    f_plain = len(re.findall(r"المادة\s+\d+", n))
    if f_paren and f_plain:
        issues.append(
            "تنبيه: إحالات المواد بصيغتين مختلفتين: المادة (12) "
            "وهي %d، والمادة 12 وهي %d. اعتمد صيغة واحدة."
            % (f_paren, f_plain))

    markers = sorted(set(int(x) for x in re.findall(r"\[(\d{1,3})\]", n)))
    if markers:
        bad = [m for m in markers if m < 1 or m > refs_count]
        if bad:
            issues.append(
                "تنبيه: إحالات لا يقابلها مرجع في قائمتك (عدد مراجعك %d): %s"
                % (refs_count, "، ".join(str(b) for b in bad)))
        if refs_count:
            unused = [i for i in range(1, refs_count + 1)
                      if i not in markers]
            if unused:
                issues.append(
                    "• مراجع في قائمتك لم يُستشهد بها في هذا النص: "
                    + "، ".join(str(u) for u in unused))
    elif refs_count:
        issues.append(
            "• لا توجد إحالات بصيغة [1] في النص رغم وجود مراجع محفوظة.")

    reps = re.findall(r"(?<!\S)([\u0600-\u06FF]{2,})\s+\1(?!\S)", t)
    if reps:
        uniq = []
        for r in reps:
            if r not in uniq:
                uniq.append(r)
        issues.append(
            "تنبيه: كلمات مكررة متتالية: " + "، ".join(uniq[:5]))

    long_s = [s for s in re.split(r"[.؟?!\n]+", t) if len(s.split()) > 60]
    if long_s:
        issues.append(
            "• %d جملة أطول من 60 كلمة. فكّر في تقسيمها." % len(long_s))

    if re.search(r" {2,}", t):
        issues.append("• توجد مسافات مزدوجة.")
    if t.count("(") != t.count(")"):
        issues.append("تنبيه: الأقواس غير متوازنة.")
    if t.count("«") != t.count("»"):
        issues.append("تنبيه: علامات الاقتباس « » غير متوازنة.")

    out = ["عدد الكلمات: %d" % len(t.split()), ""]
    if issues:
        out.extend(issues)
    else:
        out.append("لم تظهر ملاحظات آلية.")
    out.append("")
    out.append(
        "هذا فحص شكلي آلي، ولا يغني عن المراجعة البشرية "
        "ولا عن التحقق من المصادر.")
    return out


def parse_date(s):
    s = norm_digits(s).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None


# ===============================================================
# معالج الأخطاء أثناء التشغيل: يعرض الخطأ بدل إغلاق التطبيق
# ===============================================================
class _Handler(ExceptionHandler):
    def handle_exception(self, inst):
        try:
            tb = traceback.format_exc()
            print(tb)
            app = App.get_running_app()
            if app is not None and hasattr(app, "answer"):
                Clock.schedule_once(lambda dt: app.show_error(tb))
        except Exception:
            pass
        return ExceptionManager.PASS


# ===============================================================
# التطبيق
# ===============================================================
class MushrifApp(App):

    TABS = [
        ("chat", "المشرف"),
        ("plan", "الخطة"),
        ("refs", "المراجع"),
        ("track", "المتابعة"),
        ("check", "التدقيق"),
    ]

    def build(self):
        try:
            return self._build()
        except Exception:
            tb = traceback.format_exc()
            print(tb)
            box = ScrollView()
            lb = Label(
                text="Startup error - send this text to the developer:\n\n"
                     + tb,
                size_hint_y=None, halign="left", valign="top",
                font_size=sp(13),
            )
            lb.bind(
                width=lambda *a: setattr(lb, "text_size", (lb.width, None)),
                texture_size=lambda *a: setattr(
                    lb, "height", lb.texture_size[1] + dp(30)),
            )
            box.add_widget(lb)
            return box

    def _build(self):
        self.title = "Mushrif"
        Window.clearcolor = (0.07, 0.08, 0.11, 1)
        try:
            Window.softinput_mode = "below_target"
        except Exception:
            pass

        warnings = []
        ok = os.path.exists(FONT) and os.path.getsize(FONT) > 50000
        self.font = FONT if ok else "Roboto"
        _font_name["value"] = self.font
        if not ok:
            warnings.append(
                "Missing font.ttf next to main.py\n"
                "تنبيه: ملف font.ttf غير موجود بجانب main.py "
                "فقد تظهر الحروف العربية مربعات."
            )
        if not HAS_AR:
            warnings.append(
                "Missing libs: arabic-reshaper, python-bidi\n"
                "تنبيه: مكتبتا arabic-reshaper وpython-bidi غير مثبتتين "
                "فلن تتصل الحروف العربية."
            )
        if not HAS_REQUESTS:
            warnings.append(
                "Missing lib: requests\n"
                "تنبيه: مكتبة requests غير مثبتة فلن يعمل الاتصال."
            )

        self.store_path = os.path.join(self.user_data_dir, "mushrif.json")
        self.data = self.load_data()
        self.mode_name = list(MODES)[0]
        self.last_answer = ""
        self.shown_raw = ""
        self.check_raw = ""
        self.mode_buttons = {}
        self.level_buttons = {}
        self.tab_buttons = {}
        self.type_buttons = {}
        self.style_buttons = {}
        self.level = 1
        self.edit_index = None
        self.ref_type = "book"
        self.current_mode = self.mode_name
        self.current_question = ""

        root = BoxLayout(orientation="vertical")

        tabs = BoxLayout(
            size_hint_y=None, height=dp(46), spacing=dp(2),
            padding=[dp(4), dp(4), dp(4), 0],
        )
        for key, name in self.TABS:
            tb = ToggleButton(
                text=ar(name, 13, wrap=False),
                group="tab",
                allow_no_selection=False,
                state="down" if key == "chat" else "normal",
                font_name=self.font, font_size=sp(13),
            )
            tb.bind(on_release=lambda inst, k=key: self.go_tab(k))
            self.tab_buttons[key] = tb
            tabs.add_widget(tb)
        root.add_widget(tabs)

        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(self.build_chat_screen())
        self.sm.add_widget(self.build_plan_screen())
        self.sm.add_widget(self.build_refs_screen())
        self.sm.add_widget(self.build_track_screen())
        self.sm.add_widget(self.build_check_screen())
        root.add_widget(self.sm)

        self.refresh_plan()
        self.refresh_refs()
        self.refresh_tasks()
        Window.bind(on_resize=self.on_win_resize)

        if warnings:
            for w in warnings:
                print(w)
            self.show("\n\n".join(warnings))

        return root

    # -----------------------------------------------------------
    # أدوات بناء الواجهة
    # -----------------------------------------------------------
    def new_screen(self, name):
        screen = Screen(name=name)
        scroll = ScrollView(do_scroll_x=False)
        grid = GridLayout(
            cols=1, size_hint_y=None,
            padding=dp(10), spacing=dp(8),
        )
        grid.bind(minimum_height=grid.setter("height"))
        scroll.add_widget(grid)
        screen.add_widget(scroll)
        return screen, grid

    def label(self, text, size=16, height=None, color=WHITE):
        return Label(
            text=ar(text, size) if text else "",
            size_hint_y=None, height=height or dp(40),
            font_size=sp(size), font_name=self.font,
            color=color,
        )

    def hint(self, text):
        return text if NATIVE_RTL_INPUT else ar(text, 16, wrap=False)

    def field(self, hint, multiline, height, text=""):
        base = dict(
            text=text,
            multiline=multiline,
            size_hint_y=None,
            height=height,
            font_name=self.font,
            font_size=sp(16),
            halign="right",
        )
        if NATIVE_RTL_INPUT:
            try:
                return TextInput(
                    hint_text=hint,
                    base_direction="rtl",
                    text_language="ar",
                    **base
                )
            except Exception:
                pass
        return TextInput(hint_text=ar(hint, 16, wrap=False), **base)

    def button(self, text, fn, size=16, height=None):
        b = Button(
            text=ar(text, size, wrap=False),
            size_hint_y=None, height=height or dp(52),
            font_name=self.font, font_size=sp(size),
        )
        b.bind(on_release=fn)
        return b

    def out_label(self):
        lb = Label(
            text="",
            size_hint_y=None,
            halign="right", valign="top",
            font_size=sp(16), font_name=self.font,
        )
        lb.bind(
            width=lambda *a: setattr(lb, "text_size", (lb.width, None)),
            texture_size=lambda *a: setattr(
                lb, "height", lb.texture_size[1] + dp(30)),
        )
        return lb

    def list_row(self, text, color, on_main, buttons, indent=0, size=15):
        """صف قائمة: أزرار صغيرة على اليسار وزر رئيسي يحمل النص."""
        btn_w = dp(50)
        avail = (Window.width - dp(20) - indent
                 - len(buttons) * (btn_w + dp(4)) - dp(24))
        avail = max(avail, dp(80))
        shown = ar(text, size, width=avail)
        n_lines = shown.count("\n") + 1
        h = max(dp(48), n_lines * sp(size) * 1.35 + dp(20))

        row = BoxLayout(
            size_hint_y=None, height=h, spacing=dp(4),
            padding=[0, 0, indent, 0],
        )
        for label, fn in buttons:
            b = Button(
                text=ar(label, 12, wrap=False),
                size_hint_x=None, width=btn_w,
                font_name=self.font, font_size=sp(12),
            )
            b.bind(on_release=fn)
            row.add_widget(b)

        main = Button(
            text=shown,
            halign="right", valign="middle",
            background_normal="", background_down="",
            background_color=(0.13, 0.15, 0.22, 1),
            color=color,
            font_name=self.font, font_size=sp(size),
        )
        main.bind(size=lambda inst, v: setattr(
            inst, "text_size", (inst.width - dp(12), inst.height)))
        main.bind(on_release=on_main)
        row.add_widget(main)
        return row

    def show(self, text):
        """عرض نص منطقي في منطقة الإجابة (يُشكَّل هنا فقط)."""
        self.shown_raw = text
        self.answer.text = ar(text, 16)

    def show_check(self, text):
        self.check_raw = text
        self.check_out.text = ar(text, 16)

    def show_error(self, tb):
        try:
            self.btn.disabled = False
        except Exception:
            pass
        self.show("حدث خطأ غير متوقع (أرسل هذا النص للمطور):\n" + tb[-900:])

    def on_win_resize(self, *args):
        def redo(dt):
            if self.shown_raw:
                self.show(self.shown_raw)
            if self.check_raw:
                self.show_check(self.check_raw)
            self.refresh_plan()
            self.refresh_refs()
            self.refresh_tasks()
        Clock.schedule_once(redo, 0.1)

    def go_tab(self, key):
        self.sm.current = key
        for k, b in self.tab_buttons.items():
            b.state = "down" if k == key else "normal"

    # -----------------------------------------------------------
    # شاشة المشرف
    # -----------------------------------------------------------
    def build_chat_screen(self):
        screen, root = self.new_screen("chat")

        root.add_widget(self.label(
            "مشرف - رفيق الباحث القانوني",
            size=22, height=dp(60), color=GOLD))
        root.add_widget(self.label(
            "مرحلة العمل", size=14, height=dp(28), color=MUTED))

        rows = (len(MODES) + 1) // 2
        grid = GridLayout(
            cols=2, size_hint_y=None,
            height=dp(52) * rows + dp(6) * (rows - 1), spacing=dp(6)
        )
        for i, name in enumerate(MODES):
            b = ToggleButton(
                text=ar(name, 15, wrap=False),
                group="mode",
                allow_no_selection=False,
                state="down" if i == 0 else "normal",
                font_name=self.font, font_size=sp(15),
            )
            b.bind(on_release=lambda inst, n=name: self.select_mode(n))
            self.mode_buttons[name] = b
            grid.add_widget(b)
        root.add_widget(grid)

        root.add_widget(self.label(
            "بيانات رسالتك (تُحفظ تلقائيًا)", size=14, height=dp(28),
            color=MUTED))
        project = self.data.get("project", {})
        self.topic = self.field(
            "موضوع الرسالة", False, dp(48), project.get("topic", ""))
        self.method = self.field(
            "المنهج (تحليلي / مقارن / تأصيلي)", False, dp(48),
            project.get("method", ""))
        self.country = self.field(
            "الدولة أو النظام القانوني", False, dp(48),
            project.get("country", ""))
        self.compare = self.field(
            "نظام للمقارنة (اختياري)", False, dp(48),
            project.get("compare", ""))
        for w in (self.topic, self.method, self.country, self.compare):
            root.add_widget(w)

        self.q_input = self.field(
            "اكتب طلبك أو الصق النص المراد مراجعته", True, dp(150))
        root.add_widget(self.q_input)

        self.btn = self.button("أرسل إلى المشرف", self.ask, 18, dp(56))
        root.add_widget(self.btn)

        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        row.add_widget(self.button(
            "نسخ الإجابة", self.copy_answer, 14, dp(48)))
        row.add_widget(self.button(
            "السجل", self.show_history, 14, dp(48)))
        root.add_widget(row)

        self.answer = self.out_label()
        root.add_widget(self.answer)
        return screen

    # -----------------------------------------------------------
    # شاشة خطة الرسالة
    # -----------------------------------------------------------
    def build_plan_screen(self):
        screen, root = self.new_screen("plan")

        root.add_widget(self.label(
            "خطة الرسالة", size=22, height=dp(50), color=GOLD))
        root.add_widget(self.label(
            "اختر المستوى، اكتب العنوان، ثم أضف. "
            "اضغط على أي عنصر لتعديله.",
            size=13, height=dp(50), color=MUTED))

        lvl_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        for lvl, name in PLAN_LEVELS.items():
            b = ToggleButton(
                text=ar(name, 15, wrap=False),
                group="level",
                allow_no_selection=False,
                state="down" if lvl == 1 else "normal",
                font_name=self.font, font_size=sp(15),
            )
            b.bind(on_release=lambda inst, l=lvl: self.set_level(l))
            self.level_buttons[lvl] = b
            lvl_row.add_widget(b)
        root.add_widget(lvl_row)

        self.plan_input = self.field("عنوان العنصر", False, dp(48))
        root.add_widget(self.plan_input)

        self.plan_add_btn = self.button("إضافة", self.add_or_save_item)
        root.add_widget(self.plan_add_btn)

        self.plan_status = self.label(
            "", size=13, height=dp(28), color=GREEN)
        root.add_widget(self.plan_status)

        self.plan_list = GridLayout(
            cols=1, size_hint_y=None, spacing=dp(4))
        self.plan_list.bind(
            minimum_height=self.plan_list.setter("height"))
        root.add_widget(self.plan_list)

        row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6))
        row.add_widget(self.button("نسخ الخطة", self.copy_plan, 14))
        row.add_widget(self.button("مراجعة الخطة", self.review_plan, 14))
        root.add_widget(row)
        return screen

    # -----------------------------------------------------------
    # شاشة المراجع
    # -----------------------------------------------------------
    def build_refs_screen(self):
        screen, root = self.new_screen("refs")

        root.add_widget(self.label(
            "المراجع والتوثيق", size=22, height=dp(50), color=GOLD))
        root.add_widget(self.label(
            "أضف مصادرك مرة واحدة، ويُنسَّق لك الهامش وقائمة المراجع. "
            "رقم كل مرجع هو رقم الإحالة [1] في نصك.",
            size=13, height=dp(70), color=MUTED))

        style_row = BoxLayout(
            size_hint_y=None, height=dp(44), spacing=dp(6))
        cur_style = self.data.get("style", "arabic")
        for key, name in (("arabic", "النمط العربي"), ("apa", "نمط APA")):
            b = ToggleButton(
                text=ar(name, 14, wrap=False),
                group="style",
                allow_no_selection=False,
                state="down" if key == cur_style else "normal",
                font_name=self.font, font_size=sp(14),
            )
            b.bind(on_release=lambda inst, k=key: self.set_style(k))
            self.style_buttons[key] = b
            style_row.add_widget(b)
        root.add_widget(style_row)

        tgrid = GridLayout(
            cols=3, size_hint_y=None,
            height=dp(44) * 2 + dp(6), spacing=dp(6))
        for key, name in REF_TYPES:
            b = ToggleButton(
                text=ar(name, 13, wrap=False),
                group="reftype",
                allow_no_selection=False,
                state="down" if key == "book" else "normal",
                font_name=self.font, font_size=sp(13),
            )
            b.bind(on_release=lambda inst, k=key: self.set_ref_type(k))
            self.type_buttons[key] = b
            tgrid.add_widget(b)
        root.add_widget(tgrid)

        self.ref_fields = []
        for h in REF_HINTS["book"]:
            f = self.field(h, False, dp(46))
            self.ref_fields.append(f)
            root.add_widget(f)

        root.add_widget(self.button("إضافة المرجع", self.add_ref))
        self.ref_status = self.label(
            "", size=13, height=dp(28), color=GREEN)
        root.add_widget(self.ref_status)

        root.add_widget(self.label(
            "اضغط على أي مرجع لنسخ صيغة الهامش.",
            size=13, height=dp(30), color=MUTED))
        self.ref_list = GridLayout(
            cols=1, size_hint_y=None, spacing=dp(4))
        self.ref_list.bind(minimum_height=self.ref_list.setter("height"))
        root.add_widget(self.ref_list)

        root.add_widget(self.button(
            "نسخ قائمة المراجع كاملة", self.copy_bibliography, 14))
        return screen

    # -----------------------------------------------------------
    # شاشة المتابعة
    # -----------------------------------------------------------
    def build_track_screen(self):
        screen, root = self.new_screen("track")

        root.add_widget(self.label(
            "متابعة التقدم", size=22, height=dp(50), color=GOLD))

        project = self.data.get("project", {})
        self.deadline = self.field(
            "موعد التسليم (مثال: 2027-06-30)", False, dp(48),
            project.get("deadline", ""))
        root.add_widget(self.deadline)
        root.add_widget(self.button("حفظ الموعد", self.save_deadline, 15))

        self.countdown = self.label("", size=15, height=dp(36), color=GOLD)
        root.add_widget(self.countdown)

        self.progress = ProgressBar(
            max=100, value=0, size_hint_y=None, height=dp(14))
        root.add_widget(self.progress)
        self.progress_label = self.label(
            "", size=14, height=dp(32), color=MUTED)
        root.add_widget(self.progress_label)

        root.add_widget(self.label(
            "المهام", size=16, height=dp(32), color=WHITE))
        self.task_input = self.field("عنوان المهمة", False, dp(48))
        root.add_widget(self.task_input)
        self.task_due = self.field(
            "موعدها (اختياري، مثال: 2027-01-15)", False, dp(48))
        root.add_widget(self.task_due)
        root.add_widget(self.button("إضافة المهمة", self.add_task, 15))
        root.add_widget(self.button(
            "إضافة مهام مقترحة للرسالة", self.add_template_tasks, 14))
        root.add_widget(self.label(
            "اضغط على المهمة لتحديدها منجزة أو لإلغاء ذلك.",
            size=13, height=dp(30), color=MUTED))

        self.task_list = GridLayout(
            cols=1, size_hint_y=None, spacing=dp(4))
        self.task_list.bind(minimum_height=self.task_list.setter("height"))
        root.add_widget(self.task_list)
        return screen

    # -----------------------------------------------------------
    # شاشة التدقيق
    # -----------------------------------------------------------
    def build_check_screen(self):
        screen, root = self.new_screen("check")

        root.add_widget(self.label(
            "مدقق الاتساق", size=22, height=dp(50), color=GOLD))
        root.add_widget(self.label(
            "فحص آلي محلي لنصك: علامات الترقيم، وصيغ المواد، والإحالات "
            "مقابل قائمة مراجعك، والتكرار، والأقواس.",
            size=13, height=dp(70), color=MUTED))

        self.check_input = self.field(
            "الصق هنا فقرة أو فصلًا من رسالتك", True, dp(220))
        root.add_widget(self.check_input)
        root.add_widget(self.button("دقّق النص", self.run_check))

        self.check_out = self.out_label()
        root.add_widget(self.check_out)
        return screen

    # -----------------------------------------------------------
    # التخزين المحلي (نصوص منطقية فقط)
    # -----------------------------------------------------------
    def load_data(self):
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data.setdefault("project", {})
                data.setdefault("history", [])
                data.setdefault("plan", [])
                data.setdefault("refs", [])
                data.setdefault("tasks", [])
                data.setdefault("style", "arabic")
                return data
        except Exception:
            pass
        return {"project": {}, "history": [], "plan": [],
                "refs": [], "tasks": [], "style": "arabic"}

    def save_data(self):
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            with open(self.store_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def save_project(self):
        self.data["project"] = {
            "topic": sanitize_input(self.topic.text),
            "method": sanitize_input(self.method.text),
            "country": sanitize_input(self.country.text),
            "compare": sanitize_input(self.compare.text),
            "deadline": sanitize_input(self.deadline.text),
        }
        self.save_data()

    # -----------------------------------------------------------
    # المشرف: الأزرار
    # -----------------------------------------------------------
    def select_mode(self, name):
        self.mode_name = name
        for n, b in self.mode_buttons.items():
            b.state = "down" if n == name else "normal"

    def copy_answer(self, *args):
        if self.last_answer:
            Clipboard.copy(self.last_answer)
            self.show("تم نسخ الإجابة.\n\n" + self.last_answer)
        else:
            self.show("لا توجد إجابة لنسخها بعد.")

    def show_history(self, *args):
        history = self.data.get("history", [])
        if not history:
            return self.show("السجل فارغ.")
        parts = []
        for item in reversed(history[-10:]):
            parts.append("%s  (%s)\n%s\n%s" % (
                item.get("mode", ""),
                item.get("time", ""),
                item.get("question", "")[:80],
                "--------------",
            ))
        self.show("آخر الطلبات:\n\n" + "\n".join(parts))

    def ask(self, *args):
        if not HAS_REQUESTS:
            return self.show("مكتبة requests غير مثبتة، لا يمكن الاتصال.")

        question = sanitize_input(self.q_input.text)
        topic = sanitize_input(self.topic.text)

        if not question and not topic:
            return self.show("اكتب موضوع رسالتك أو طلبك أولًا.")

        self.save_project()

        method = sanitize_input(self.method.text) or "غير محدد"
        country = sanitize_input(self.country.text) or "غير محدد"
        compare = sanitize_input(self.compare.text) or "غير محدد"

        plan = plan_text(self.data.get("plan", []))
        plan_block = ""
        if plan:
            plan_block = "\n\nخطة الرسالة الحالية للطالب:\n" + plan
            if self.mode_name == "بناء خطة":
                plan_block += (
                    "\n(للطالب خطة قائمة، فراجعها وطوّرها بدل أن تقترح "
                    "خطة جديدة كليًا.)"
                )

        compare_block = ""
        if self.mode_name == "مقارنة قانونية":
            compare_block = "\nنظام المقارنة: " + compare

        refs_block = ""
        refs = self.data.get("refs", [])
        if refs and self.mode_name == "مراجعة نص":
            lines = []
            for i, r in enumerate(refs):
                lines.append("[%d] %s" % (i + 1, self.fmt(r)))
            refs_block = (
                "\n\nقائمة مراجع الطالب (للتحقق من إحالات النص إليها):\n"
                + "\n".join(lines)
            )

        full_question = (
            "التعليمات العامة: " + SYSTEM_BASE
            + "\n\nالمرحلة المطلوبة: " + self.mode_name
            + "\nمهمتك في هذه المرحلة: " + MODES[self.mode_name]
            + "\n\nموضوع الرسالة: " + (topic or "غير محدد")
            + "\nالمنهج: " + method
            + "\nالنظام القانوني: " + country
            + compare_block
            + plan_block
            + refs_block
            + "\n\nطلب الطالب أو نصه:\n" + (question or "(لا يوجد)")
        )

        self.current_mode = self.mode_name
        self.current_question = question or topic
        self.btn.disabled = True
        self.show("جارٍ إرسال الطلب ومعالجته...")

        threading.Thread(
            target=self.worker, args=(full_question,), daemon=True
        ).start()

    # -----------------------------------------------------------
    # الاتصال بالخادم
    # -----------------------------------------------------------
    def worker(self, question):
        ok = False
        try:
            r = requests.post(
                API_URL,
                headers={"Content-Type": "application/json"},
                json={"question": question},
                timeout=90,
                verify=certifi.where() if HAS_CERTIFI else True,
            )
            r.encoding = "utf-8"

            try:
                data = r.json()
            except Exception:
                data = {}

            if r.status_code == 200:
                candidates = data.get("candidates", [])
                if candidates:
                    parts = (
                        candidates[0].get("content", {}).get("parts", [])
                    )
                    answer = "\n".join(
                        p.get("text", "") for p in parts if p.get("text")
                    )
                    if answer:
                        result = answer
                        ok = True
                    else:
                        result = "لم يصل رد نصي من الخدمة."
                else:
                    result = str(
                        data.get("error", "لم يصل رد صالح من الخدمة."))
            else:
                error = data.get("error", {})
                if isinstance(error, dict):
                    detail = error.get("message", str(error))
                else:
                    detail = str(error)
                result = "خطأ %d: %s" % (r.status_code, detail)

        except Exception as e:
            result = "تعذّر الاتصال بالخادم:\n" + repr(e)

        Clock.schedule_once(lambda dt: self.done(result, ok))

    def done(self, text, ok):
        self.btn.disabled = False
        if ok:
            text = clean_markdown(text)
            self.last_answer = text
            history = self.data.setdefault("history", [])
            history.append({
                "mode": self.current_mode,
                "question": self.current_question,
                "answer": text,
                "time": time.strftime("%Y-%m-%d %H:%M"),
            })
            self.data["history"] = history[-HISTORY_LIMIT:]
            self.save_data()
            self.show(text + FOOTER)
        else:
            self.show(text)

    # -----------------------------------------------------------
    # خطة الرسالة: العمليات
    # -----------------------------------------------------------
    def set_level(self, lvl):
        self.level = lvl
        for k, b in self.level_buttons.items():
            b.state = "down" if k == lvl else "normal"

    def refresh_plan(self):
        if not hasattr(self, "plan_list"):
            return
        self.plan_list.clear_widgets()
        plan = self.data.get("plan", [])
        if not plan:
            self.plan_list.add_widget(self.label(
                "لا توجد عناصر بعد. أضف أول فصل لرسالتك.",
                size=14, height=dp(40), color=MUTED))
            return
        colors = {1: GOLD, 2: WHITE, 3: (0.75, 0.8, 0.9, 1)}
        for i, (lvl, prefix, title) in enumerate(number_plan(plan)):
            self.plan_list.add_widget(self.list_row(
                prefix + ": " + title,
                colors.get(lvl, WHITE),
                lambda inst, idx=i: self.edit_item(idx),
                [
                    ("حذف", lambda inst, idx=i: self.delete_item(idx)),
                    ("أعلى", lambda inst, idx=i: self.move_up(idx)),
                    ("أسفل", lambda inst, idx=i: self.move_down(idx)),
                ],
                indent=dp(18) * (lvl - 1),
            ))

    def reset_plan_form(self):
        self.edit_index = None
        self.plan_input.text = ""
        self.plan_add_btn.text = ar("إضافة", 16, wrap=False)

    def add_or_save_item(self, *args):
        title = sanitize_input(self.plan_input.text)
        if not title:
            return
        plan = self.data.setdefault("plan", [])
        item = {"level": self.level, "title": title}
        if (self.edit_index is not None
                and 0 <= self.edit_index < len(plan)):
            plan[self.edit_index] = item
        else:
            plan.append(item)
        self.reset_plan_form()
        self.plan_status.text = ""
        self.save_data()
        self.refresh_plan()

    def edit_item(self, i):
        plan = self.data.get("plan", [])
        if not (0 <= i < len(plan)):
            return
        item = plan[i]
        self.edit_index = i
        self.plan_input.text = item.get("title", "")
        self.set_level(item.get("level", 1))
        self.plan_add_btn.text = ar("حفظ التعديل", 16, wrap=False)

    def delete_item(self, i):
        plan = self.data.get("plan", [])
        if 0 <= i < len(plan):
            plan.pop(i)
            if self.edit_index is not None:
                self.reset_plan_form()
            self.save_data()
            self.refresh_plan()

    def move_up(self, i):
        plan = self.data.get("plan", [])
        if 0 < i < len(plan):
            plan[i - 1], plan[i] = plan[i], plan[i - 1]
            self.reset_plan_form()
            self.save_data()
            self.refresh_plan()

    def move_down(self, i):
        plan = self.data.get("plan", [])
        if 0 <= i < len(plan) - 1:
            plan[i + 1], plan[i] = plan[i], plan[i + 1]
            self.reset_plan_form()
            self.save_data()
            self.refresh_plan()

    def copy_plan(self, *args):
        text = plan_text(self.data.get("plan", []))
        if text:
            Clipboard.copy(text)
            self.plan_status.text = ar("تم نسخ الخطة", 13, wrap=False)
        else:
            self.plan_status.text = ar("الخطة فارغة", 13, wrap=False)

    def review_plan(self, *args):
        if not self.data.get("plan"):
            self.plan_status.text = ar(
                "أضف عناصر للخطة أولًا", 13, wrap=False)
            return
        self.q_input.text = (
            "راجع خطة رسالتي الحالية، وبيّن مواضع الخلل في التوازن "
            "والتكرار وترتيب الأفكار."
        )
        self.select_mode("بناء خطة")
        self.go_tab("chat")

    # -----------------------------------------------------------
    # المراجع: العمليات
    # -----------------------------------------------------------
    def fmt(self, ref, foot=False):
        if self.data.get("style", "arabic") == "apa":
            return fmt_apa(ref, foot)
        return fmt_arabic(ref, foot)

    def set_style(self, key):
        self.data["style"] = key
        for k, b in self.style_buttons.items():
            b.state = "down" if k == key else "normal"
        self.save_data()
        self.refresh_refs()

    def set_ref_type(self, key):
        self.ref_type = key
        for k, b in self.type_buttons.items():
            b.state = "down" if k == key else "normal"
        for f, h in zip(self.ref_fields, REF_HINTS[key]):
            f.hint_text = self.hint(h)

    def add_ref(self, *args):
        vals = [sanitize_input(f.text) for f in self.ref_fields]
        author, title, source, place, year, pages = vals
        if not title:
            self.ref_status.text = ar(
                "اكتب عنوان المرجع على الأقل", 13, wrap=False)
            return
        self.data.setdefault("refs", []).append({
            "type": self.ref_type,
            "author": author, "title": title, "source": source,
            "place": place, "year": norm_digits(year),
            "pages": norm_digits(pages),
        })
        for f in self.ref_fields:
            f.text = ""
        self.ref_status.text = ar("تمت إضافة المرجع", 13, wrap=False)
        self.save_data()
        self.refresh_refs()

    def refresh_refs(self):
        if not hasattr(self, "ref_list"):
            return
        self.ref_list.clear_widgets()
        refs = self.data.get("refs", [])
        if not refs:
            self.ref_list.add_widget(self.label(
                "لا توجد مراجع بعد.", size=14, height=dp(40), color=MUTED))
            return
        for i, r in enumerate(refs):
            self.ref_list.add_widget(self.list_row(
                "%d. %s" % (i + 1, self.fmt(r)),
                WHITE,
                lambda inst, idx=i: self.copy_footnote(idx),
                [("حذف", lambda inst, idx=i: self.delete_ref(idx))],
                size=14,
            ))

    def copy_footnote(self, i):
        refs = self.data.get("refs", [])
        if 0 <= i < len(refs):
            Clipboard.copy(self.fmt(refs[i], foot=True))
            self.ref_status.text = ar(
                "تم نسخ صيغة الهامش", 13, wrap=False)

    def delete_ref(self, i):
        refs = self.data.get("refs", [])
        if 0 <= i < len(refs):
            refs.pop(i)
            self.save_data()
            self.refresh_refs()
            self.ref_status.text = ar(
                "حُذف المرجع، وتغيّرت أرقام ما بعده", 13, wrap=False)

    def copy_bibliography(self, *args):
        refs = self.data.get("refs", [])
        if not refs:
            self.ref_status.text = ar("لا توجد مراجع", 13, wrap=False)
            return
        ordered = sorted(
            refs, key=lambda r: (r.get("author") or r.get("title") or ""))
        Clipboard.copy("\n".join(self.fmt(r) for r in ordered))
        self.ref_status.text = ar(
            "تم نسخ قائمة المراجع مرتبة هجائيًا", 13, wrap=False)

    # -----------------------------------------------------------
    # المتابعة: العمليات
    # -----------------------------------------------------------
    def save_deadline(self, *args):
        self.save_project()
        self.refresh_tasks()

    def add_task(self, *args):
        title = sanitize_input(self.task_input.text)
        if not title:
            return
        due = sanitize_input(self.task_due.text)
        if due and parse_date(due) is None:
            self.countdown.text = ar(
                "صيغة موعد المهمة: 2027-01-15", 14, wrap=False)
            return
        self.data.setdefault("tasks", []).append(
            {"title": title, "due": norm_digits(due), "done": False})
        self.task_input.text = ""
        self.task_due.text = ""
        self.save_data()
        self.refresh_tasks()

    def add_template_tasks(self, *args):
        tasks = self.data.setdefault("tasks", [])
        existing = set(t.get("title") for t in tasks)
        for title in DEFAULT_TASKS:
            if title not in existing:
                tasks.append({"title": title, "due": "", "done": False})
        self.save_data()
        self.refresh_tasks()

    def toggle_task(self, i):
        tasks = self.data.get("tasks", [])
        if 0 <= i < len(tasks):
            tasks[i]["done"] = not tasks[i].get("done", False)
            self.save_data()
            self.refresh_tasks()

    def delete_task(self, i):
        tasks = self.data.get("tasks", [])
        if 0 <= i < len(tasks):
            tasks.pop(i)
            self.save_data()
            self.refresh_tasks()

    def refresh_tasks(self):
        if not hasattr(self, "task_list"):
            return
        # العد التنازلي
        dl = parse_date(self.deadline.text)
        if dl:
            days = (dl - date.today()).days
            if days > 0:
                msg = "المتبقي حتى التسليم: %d يومًا" % days
            elif days == 0:
                msg = "موعد التسليم اليوم"
            else:
                msg = "تجاوزت الموعد بـ %d يومًا" % (-days)
        else:
            msg = "أدخل موعد التسليم بصيغة 2027-06-30"
        self.countdown.text = ar(msg, 15, wrap=False)

        tasks = self.data.get("tasks", [])
        done = sum(1 for t in tasks if t.get("done"))
        total = len(tasks)
        pct = int(done * 100 / total) if total else 0
        self.progress.value = pct
        self.progress_label.text = ar(
            "المنجز: %d من %d (%d%%)" % (done, total, pct), 14, wrap=False)

        self.task_list.clear_widgets()
        if not tasks:
            self.task_list.add_widget(self.label(
                "لا توجد مهام بعد.", size=14, height=dp(40), color=MUTED))
            return
        today = date.today()
        for i, t in enumerate(tasks):
            due = t.get("due", "")
            d = parse_date(due) if due else None
            text = t.get("title", "")
            color = WHITE
            if t.get("done"):
                text = "تم - " + text
                color = GREEN
            elif d and d < today:
                text = "متأخرة - " + text
                color = RED
            if due:
                text += " (" + due + ")"
            self.task_list.add_widget(self.list_row(
                text, color,
                lambda inst, idx=i: self.toggle_task(idx),
                [("حذف", lambda inst, idx=i: self.delete_task(idx))],
            ))

    # -----------------------------------------------------------
    # التدقيق
    # -----------------------------------------------------------
    def run_check(self, *args):
        text = sanitize_input(self.check_input.text)
        if not text:
            return self.show_check("الصق نصًا للتدقيق أولًا.")
        lines = check_text(text, len(self.data.get("refs", [])))
        self.show_check("\n".join(lines))


if __name__ == "__main__":
    try:
        ExceptionManager.add_handler(_Handler())
    except Exception:
        pass
    MushrifApp().run()
