import json
import os
import re
import threading
import time
import traceback

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

# مستويات خطة الرسالة
PLAN_LEVELS = {1: "الفصل", 2: "المبحث", 3: "المطلب"}
ORDINALS = [
    "الأول", "الثاني", "الثالث", "الرابع", "الخامس",
    "السادس", "السابع", "الثامن", "التاسع", "العاشر",
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
            "delete_harakat": T
