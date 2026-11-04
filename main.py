import os
import json
import textwrap
import threading

import certifi
import requests
import arabic_reshaper
from bidi.algorithm import get_display

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-5-5"
FONT = "font.ttf"

MODES = {
    "بحث قانوني": (
        "أنت مساعد بحث قانوني للباحثين والمحامين. حلّل المسألة المطروحة، "
        "واذكر الإطار القانوني والمبادئ العامة والنصوص والمبادئ القضائية ذات الصلة "
        "إن كنت متأكدًا منها. لا تختلق أرقام مواد أو قضايا أو أحكامًا. "
        "إن لم تكن متأكدًا فاذكر ذلك صراحةً وأرشد الباحث إلى مصدر التحقق."
    ),
    "تحليل نص": (
        "أنت محلل نصوص قانونية. لخّص النص المعطى، واستخرج عناصره "
        "(الأطراف، الوقائع، الالتزامات، الشروط، الثغرات المحتملة) في نقاط مرتبة."
    ),
    "صياغة مذكرة": (
        "أنت محامٍ محترف في الصياغة القانونية. اكتب مذكرة أو مسودة قانونية منظمة "
        "(الوقائع، الدفوع، الأسانيد، الطلبات) بلغة قانونية رصينة، "
        "واترك الأماكن غير المعلومة بين أقواس مربعة [ ] ولا تختلق وقائع أو مواد."
    ),
    "شرح مادة": (
        "أنت أستاذ قانون. اشرح الموضوع القانوني بأسلوب أكاديمي مبسّط "
        "مع أمثلة تطبيقية، وبنفس لغة السؤال."
    ),
}

FOOTER = "\n\n⚠ للاستئناس البحثي فقط، وليس استشارة قانونية. راجع النصوص الرسمية قبل الاعتماد."


def ar(text, width=30):
    lines = []
    for para in text.split("\n"):
        for line in textwrap.wrap(para, width) or [""]:
            lines.append(get_display(arabic_reshaper.reshape(line)))
    return "\n".join(lines)


class LegalApp(App):
    def build(self):
        self.title = "Alhabouni"
        Window.clearcolor = (0.07, 0.08, 0.11, 1)
        ok = os.path.exists(FONT) and os.path.getsize(FONT) > 50000
        self.font = FONT if ok else "Roboto"
        self.key_file = os.path.join(self.user_data_dir, "key.json")
        self.mode_name = list(MODES)[0]

        root = BoxLayout(orientation="vertical", padding=10, spacing=8)

        root.add_widget(Label(
            text=ar("الحبوني - مساعد الباحث القانوني"),
            size_hint_y=None, height=100, font_size=32,
            font_name=self.font, color=(0.9, 0.75, 0.3, 1),
        ))

        self.key_input = TextInput(
            hint_text="API Key", password=True, multiline=False,
            size_hint_y=None, height=90, text=self.load_key(),
        )
        root.add_widget(self.key_input)

        grid = GridLayout(cols=2, size_hint_y=None, height=190, spacing=6)
        for i, name in enumerate(MODES):
            b = ToggleButton(
                text=ar(name), group="mode", allow_no_selection=Fals
