import os

import arabic_reshaper
from bidi.algorithm import get_display
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

# خطوط عربية موجودة عادة في أندرويد (يُستخدم أول خط يوجد)
FONT_CANDIDATES = [
    "/system/fonts/NotoNaskhArabic-Regular.ttf",
    "/system/fonts/NotoNaskhArabicUI-Regular.ttf",
    "/system/fonts/DroidSansArabic.ttf",
]
FONT = next((f for f in FONT_CANDIDATES if os.path.exists(f)), None)


def ar(text):
    """تجهيز النص العربي للعرض الصحيح (ربط الحروف + اتجاه اليمين لليسار)."""
    return get_display(arabic_reshaper.reshape(text))


def explain(question):
    """مكان منطق الشرح. حاليًا نص تجريبي فقط."""
    question = question.strip()
    if not question:
        return "اكتب سؤالك القانوني أولًا."
    return "سؤالك: " + question + "\n\n(سيُضاف هنا شرح القانون بلغة بسيطة.)"


class MainScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=16, spacing=12, **kwargs)
        font = {"font_name": FONT} if FONT else {}

        self.add_widget(Label(text=ar("افهم قانون"), font_size=28,
                              size_hint_y=None, height=60, **font))

        self.question = TextInput(hint_text=ar("اكتب سؤالك هنا"), multiline=True,
                                  size_hint_y=None, height=140, font_size=20,
                                  halign="right", **font)
        self.add_widget(self.question)

        button = Button(text=ar("اشرح"), size_hint_y=None, height=56,
                        font_size=22, **font)
        button.bind(on_release=self.on_explain)
        self.add_widget(button)

        scroll = ScrollView()
        self.answer = Label(text="", font_size=20, halign="right", valign="top",
                            size_hint_y=None, **font)
        self.answer.bind(width=self.update_text_size,
                         texture_size=self.update_height)
        scroll.add_widget(self.answer)
        self.add_widget(scroll)

    def update_text_size(self, label, width):
        label.text_size = (width, None)

    def update_height(self, label, size):
        label.height = size[1]

    def on_explain(self, *args):
        self.answer.text = ar(explain(self.question.text))


class AfhamQanunApp(App):
    def build(self):
        Window.clearcolor = (0.08, 0.1, 0.14, 1)
        return MainScreen()


if __name__ == "__main__":
    AfhamQanunApp().run()
