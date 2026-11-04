import os
import json
import textwrap

import certifi
import arabic_reshaper
from bidi.algorithm import get_display

from kivy.app import App
from kivy.core.window import Window
from kivy.network.urlrequest import UrlRequest
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-5-5"
FONT = "font.ttf"

MODES = {
    "بحث قانوني": (
        "أنت مساعد بحث قانوني للباحثين والمحامين. حلّل المسألة المطروحة، "
        "واذكر الإطار القانوني والمبادئ العامة والنصوص والمبادئ القضائية ذات الصلة "
        "إن كنت متأكدًا منها. لا تختلق أرقام مواد أو قضايا أو أحكامًا. "
        "إن لم تكن متأكدًا فاذكر ذلك صراحةً وأرشد الباحث إلى مصدر التحقق. "
        "اسأل عن الدولة والقانون المطبق إن لم يُحدَّدا."
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


def ar(text, width=32):
    lines = []
    for para in text.split("\n"):
        for line in textwrap.wrap(para, width) or [""]:
            lines.append(get_display(arabic_reshaper.reshape(line)))
    return "\n".join(lines)


class LegalApp(App):
    def build(self):
        self.title = "Alhabouni"
        Window.clearcolor = (0.07, 0.08, 0.11, 1)
        self.font = FONT if os.path.exists(FONT) else "Roboto"
        self.key_file = os.path.join(self.user_data_dir, "key.json")

        root = BoxLayout(orientation="vertical", padding=10, spacing=8)

        header = Label(
            text=ar("الحبوني - مساعد الباحث القانوني"),
            size_hint_y=None, height=100, font_size=34,
            font_name=self.font, color=(0.9, 0.75, 0.3, 1),
        )
        root.add_widget(header)

        self.key_input = TextInput(
            hint_text="API Key", password=True, multiline=False,
            size_hint_y=None, height=90, text=self.load_key(),
        )
        self.mode = Spinner(
            text=list(MODES)[0], values=list(MODES),
            size_hint_y=None, height=100, font_name=self.font, font_size=30,
        )
        self.country = TextInput(
            hint_text="Country / Law (ex: Libya)", multiline=False,
            size_hint_y=None, height=90, font_name=self.font,
        )
        self.q_input = TextInput(
            hint_text="Question / Text", size_hint_y=None, height=300,
            font_name=self.font,
        )
        self.btn = Button(
            text=ar("ابحث"), size_hint_y=None, height=110,
            font_size=34, font_name=self.font,
        )
        self.btn.bind(on_release=self.ask)

        self.answer = Label(
            text="", size_hint_y=None, halign="right", valign="top",
            font_size=28, font_name=self.font,
        )
        self.answer.bind(
            width=lambda *a: setattr(self.answer, "text_size", (self.answer.width, None)),
            texture_size=lambda *a: setattr(
                self.answer, "height", self.answer.texture_size[1] + 30),
        )
        scroll = ScrollView()
        scroll.add_widget(self.answer)

        for w in (self.key_input, self.mode, self.country,
                  self.q_input, self.btn, scroll):
            root.add_widget(w)
        return root

    def load_key(self):
        try:
            with open(self.key_file) as f:
                return json.load(f).get("key", "")
        except Exception:
            return ""

    def save_key(self, key):
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            with open(self.key_file, "w") as f:
                json.dump({"key": key}, f)
        except Exception:
            pass

    def show(self, text):
        self.answer.text = ar(text)

    def ask(self, *args):
        key = self.key_input.text.strip()
        question = self.q_input.text.strip()
        if not key:
            return self.show("أدخل مفتاح API أولًا")
        if not question:
            return self.show("اكتب سؤالك أو النص أولًا")
        self.save_key(key)

        system = MODES[self.mode.text]
        country = self.country.text.strip()
        if country:
            system += " النظام القانوني المعني: " + country + "."

        self.btn.disabled = True
        self.show("جارٍ البحث...")

        body = json.dumps({
            "model": MODEL,
            "max_tokens": 2000,
            "system": system,
            "messages": [{"role": "user", "content": question}],
        })
        headers = {
            "content-type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        }
        UrlRequest(
            API_URL, req_body=body, req_headers=headers,
            on_success=self.on_ok, on_failure=self.on_err,
            on_error=self.on_err, ca_file=certifi.where(), timeout=90,
        )

    def on_ok(self, req, result):
        self.btn.disabled = False
        try:
            self.show(result["content"][0]["text"] + FOOTER)
        except Exception:
            self.show("رد غير متوقع من الخادم")

    def on_err(self, req, error):
        self.btn.disabled = False
        msg = "تعذّر الاتصال. تحقق من الإنترنت."
        res = getattr(req, "result", None)
        if isinstance(res, dict):
            detail = res.get("error", {}).get("message", "")
            if detail:
                msg = "خطأ: " + detail
        self.show(msg)


LegalApp().run()
