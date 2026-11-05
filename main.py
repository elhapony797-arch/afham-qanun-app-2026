
import os
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


API_URL = "https://elhaponi-app.elhaponyabdo66.workers.dev/"
FONT = "font.ttf"

MODES = {
    "بحث قانوني": (
        "قم بإجراء بحث قانوني منظم، وحدد المسألة القانونية "
        "والقواعد القانونية ذات الصلة، ولا تختلق مواد أو أحكامًا."
    ),
    "تحليل نص": (
        "حلل النص القانوني، واستخرج الأطراف والوقائع والالتزامات "
        "والشروط والحقوق والثغرات المحتملة."
    ),
    "صياغة مذكرة": (
        "اكتب مذكرة قانونية منظمة تشمل الوقائع والدفوع "
        "والأسانيد والطلبات، ولا تختلق وقائع غير مذكورة."
    ),
    "شرح مادة": (
        "اشرح الموضوع القانوني بأسلوب أكاديمي مبسط "
        "مع أمثلة تطبيقية واضحة."
    ),
}

FOOTER = (
    "\n\n⚠ للاستئناس البحثي فقط، وليس استشارة قانونية. "
    "راجع النصوص الرسمية قبل الاعتماد."
)


def ar(text, width=30):
    lines = []
    for para in str(text).split("\n"):
        for line in textwrap.wrap(para, width) or [""]:
            lines.append(
                get_display(arabic_reshaper.reshape(line))
            )
    return "\n".join(lines)


class LegalApp(App):

    def build(self):
        self.title = "Alhabouni"
        Window.clearcolor = (0.07, 0.08, 0.11, 1)

        ok = (
            os.path.exists(FONT)
            and os.path.getsize(FONT) > 50000
        )
        self.font = FONT if ok else "Roboto"
        self.mode_name = list(MODES)[0]

        root = BoxLayout(
            orientation="vertical",
            padding=10,
            spacing=8
        )

        root.add_widget(Label(
            text=ar("الحبوني - مساعد الباحث القانوني"),
            size_hint_y=None,
            height=100,
            font_size=32,
            font_name=self.font,
            color=(0.9, 0.75, 0.3, 1),
        ))

        grid = GridLayout(
            cols=2,
            size_hint_y=None,
            height=190,
            spacing=6
        )

        for i, name in enumerate(MODES):
            b = ToggleButton(
                text=ar(name),
                group="mode",
                allow_no_selection=False,
                state="down" if i == 0 else "normal",
                font_name=self.font,
                font_size=28,
            )
            b.bind(
                on_release=lambda inst, n=name:
                setattr(self, "mode_name", n)
            )
            grid.add_widget(b)

        root.add_widget(grid)

        self.country = TextInput(
            hint_text="Country / Law (ex: Libya)",
            multiline=False,
            size_hint_y=None,
            height=90,
            font_name=self.font,
        )
        root.add_widget(self.country)

        self.q_input = TextInput(
            hint_text="Question / Text",
            size_hint_y=None,
            height=280,
            font_name=self.font,
        )
        root.add_widget(self.q_input)

        self.btn = Button(
            text=ar("ابحث"),
            size_hint_y=None,
            height=110,
            font_size=34,
            font_name=self.font,
        )
        self.btn.bind(on_release=self.ask)
        root.add_widget(self.btn)

        self.answer = Label(
            text="",
            size_hint_y=None,
            halign="right",
            valign="top",
            font_size=28,
            font_name=self.font,
        )

        self.answer.bind(
            width=lambda *a: setattr(
                self.answer,
                "text_size",
                (self.answer.width, None)
            ),
            texture_size=lambda *a: setattr(
                self.answer,
                "height",
                self.answer.texture_size[1] + 30
            ),
        )

        scroll = ScrollView()
        scroll.add_widget(self.answer)
        root.add_widget(scroll)

        return root

    def show(self, text):
        self.answer.text = ar(text)

    def ask(self, *args):
        question = self.q_input.text.strip()

        if not question:
            return self.show("اكتب سؤالك أو النص أولًا")

        system = MODES[self.mode_name]
        country = self.country.text.strip()

        if not country:
            country = "حدد الدولة أو النظام القانوني قبل الإجابة"

        full_question = (
            "التعليمات: " + system
            + "\nالنظام القانوني المعني: " + country
            + "\n\nسؤال المستخدم أو النص المطلوب تحليله:\n"
            + question
        )

        self.btn.disabled = True
        self.show("جارٍ إرسال السؤال ومعالجته...")

        threading.Thread(
            target=self.worker,
            args=(full_question,),
            daemon=True
        ).start()

    def worker(self, question):
        try:
            r = requests.post(
                API_URL,
                headers={
                    "Content-Type": "application/json"
                },
                json={
                    "question": question
                },
                timeout=90,
                verify=certifi.where(),
            )

            try:
                data = r.json()
            except Exception:
                data = {}

            if r.status_code == 200:
                candidates = data.get("candidates", [])

                if candidates:
                    parts = (
                        candidates[0]
                        .get("content", {})
                        .get("parts", [])
                    )

                    answer = "\n".join(
                        p.get("text", "")
                        for p in parts
                        if p.get("text")
                    )

                    if answer:
                        result = answer + FOOTER
                    else:
                        result = "لم يصل رد نصي من Gemini."
                else:
                    result = data.get(
                        "error",
                        "لم يصل رد صالح من الخدمة."
                    )

            else:
                error = data.get("error", {})
                if isinstance(error, dict):
                    detail = error.get("message", str(error))
                else:
                    detail = str(error)

                result = "خطأ %d: %s" % (
                    r.status_code,
                    detail
                )

        except Exception as e:
            result = "تعذّر الاتصال بالخادم:\n" + repr(e)

        Clock.schedule_once(
            lambda dt: self.done(result)
        )

    def done(self, text):
        self.btn.disabled = False
        self.show(text)


LegalApp().run()
