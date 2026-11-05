import json
import os
import re
import threading
import time

import arabic_reshaper
import certifi
import kivy
import requests
from bidi.algorithm import get_display

from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton


API_URL = "https://elhaponi-app.elhaponyabdo66.workers.dev/"
FONT = "font.ttf"
HISTORY_LIMIT = 30

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
}

FOOTER = (
    "\n\n⚠ للاستئناس البحثي فقط. تحقق من النصوص الرسمية والمراجع "
    "الأصلية قبل اعتماد أي معلومة في رسالتك."
)


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

_RESHAPER = arabic_reshaper.ArabicReshaper(configuration={
    # حذف الحركات يمنع ظهور مربعات إن لم يدعمها الخط
    "delete_harakat": True,
    "support_ligatures": True,
    # يستخدم الشكل الأصلي إن لم يوفر الخط الشكل المنفصل
    "use_unshaped_instead_of_isolated": True,
})

# محارف التحكم بالاتجاه التي تُفسد التقطيع عند اللصق من Word وغيره
_BIDI_CONTROLS = re.compile("[\u200e\u200f\u202a-\u202e\u2066-\u2069\ufeff]")

_measure_cache = {}
_font_name = {"value": "Roboto"}


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
    if not line:
        return ""
    return get_display(_RESHAPER.reshape(line), base_dir="R")


def _measure(text, font_size):
    key = (_font_name["value"], font_size)
    core = _measure_cache.get(key)
    if core is None:
        core = CoreLabel(font_name=_font_name["value"], font_size=font_size)
        _measure_cache[key] = core
    return core.get_extents(text)[0]


def wrap_logical(paragraph, max_px, font_size):
    """
    تقطيع فقرة على مستوى الكلمات حسب عرض الشاشة الفعلي بالبكسل.
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


def ar(text, font_size=16, wrap=True):
    """نص عربي جاهز للعرض في Label أو Button."""
    if not wrap:
        return "\n".join(shape(l) for l in str(text).split("\n"))
    max_px = Window.width - dp(40)
    lines = []
    for para in str(text).split("\n"):
        for line in wrap_logical(para, max_px, font_size):
            lines.append(shape(line))
    return "\n".join(lines)


# ===============================================================
# التطبيق
# ===============================================================
class MushrifApp(App):

    def build(self):
        self.title = "Mushrif"
        Window.clearcolor = (0.07, 0.08, 0.11, 1)
        Window.softinput_mode = "below_target"

        ok = os.path.exists(FONT) and os.path.getsize(FONT) > 50000
        self.font = FONT if ok else "Roboto"
        _font_name["value"] = self.font

        self.store_path = os.path.join(self.user_data_dir, "mushrif.json")
        self.data = self.load_data()
        self.mode_name = list(MODES)[0]
        self.last_answer = ""     # النص المنطقي (للنسخ)
        self.shown_raw = ""       # آخر نص معروض (لإعادة التقطيع عند التدوير)

        scroll = ScrollView(do_scroll_x=False)
        root = GridLayout(
            cols=1, size_hint_y=None,
            padding=dp(10), spacing=dp(8),
        )
        root.bind(minimum_height=root.setter("height"))
        scroll.add_widget(root)

        root.add_widget(self.label(
            "مشرف - رفيق الباحث القانوني",
            size=22, height=dp(60), color=(0.9, 0.75, 0.3, 1)
        ))

        root.add_widget(self.label(
            "مرحلة العمل", size=14, height=dp(28),
            color=(0.7, 0.7, 0.75, 1)
        ))
        grid = GridLayout(
            cols=2, size_hint_y=None,
            height=dp(52) * 3 + dp(6) * 2, spacing=dp(6)
        )
        for i, name in enumerate(MODES):
            b = ToggleButton(
                text=ar(name, 15, wrap=False),
                group="mode",
                allow_no_selection=False,
                state="down" if i == 0 else "normal",
                font_name=self.font,
                font_size=sp(15),
            )
            b.bind(on_release=lambda inst, n=name:
                   setattr(self, "mode_name", n))
            grid.add_widget(b)
        root.add_widget(grid)

        root.add_widget(self.label(
            "بيانات رسالتك (تُحفظ تلقائيًا)", size=14, height=dp(28),
            color=(0.7, 0.7, 0.75, 1)
        ))
        project = self.data.get("project", {})
        self.topic = self.field(
            "موضوع الرسالة", False, dp(48), project.get("topic", ""))
        self.method = self.field(
            "المنهج (تحليلي / مقارن / تأصيلي)", False, dp(48),
            project.get("method", ""))
        self.country = self.field(
            "الدولة أو النظام القانوني", False, dp(48),
            project.get("country", ""))
        for w in (self.topic, self.method, self.country):
            root.add_widget(w)

        self.q_input = self.field(
            "اكتب طلبك أو الصق النص المراد مراجعته", True, dp(150))
        root.add_widget(self.q_input)

        self.btn = Button(
            text=ar("أرسل إلى المشرف", 18, wrap=False),
            size_hint_y=None, height=dp(56),
            font_name=self.font, font_size=sp(18),
        )
        self.btn.bind(on_release=self.ask)
        root.add_widget(self.btn)

        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        copy_btn = Button(
            text=ar("نسخ الإجابة", 14, wrap=False),
            font_name=self.font, font_size=sp(14),
        )
        copy_btn.bind(on_release=self.copy_answer)
        hist_btn = Button(
            text=ar("السجل", 14, wrap=False),
            font_name=self.font, font_size=sp(14),
        )
        hist_btn.bind(on_release=self.show_history)
        row.add_widget(copy_btn)
        row.add_widget(hist_btn)
        root.add_widget(row)

        self.answer = Label(
            text="",
            size_hint_y=None,
            halign="right", valign="top",
            font_size=sp(16), font_name=self.font,
        )
        self.answer.bind
