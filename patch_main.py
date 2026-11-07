import sys

P = "main.py"
s = open(P, encoding="utf-8").read()

if "class ShareIcon" in s:
    print("main.py already patched")
    sys.exit(0)

PAIRS = []

PAIRS.append((
    "from kivy.uix.gridlayout import GridLayout\n",
    "from kivy.graphics import Color, Ellipse, Line\n"
    "from kivy.uix.gridlayout import GridLayout\n"
    "from kivy.uix.image import Image\n"
    "from kivy.uix.modalview import ModalView\n"
    "from kivy.uix.widget import Widget\n"))

PAIRS.append((
    "MIN_GAP = 5",
    '''LOGO = "logo.png"

# SHARE_URL: put the app download link here (optional)
SHARE_URL = ""
SHARE_TEXT = (
    "مشرف - رفيق الباحث القانوني: مشرف أكاديمي في جيبك يوجّهك في رسالة "
    "الماجستير والدكتوراه: إشكالية وخطة ومراجع وأسئلة مناقشة ومتابعة "
    "لموعد التسليم. جرّبه."
)
WELCOME_INTRO = (
    "أوجّهك خطوة بخطوة في رسالتك، وأرشدك ولا أكتب عنك. "
    "وإن لم أتأكد من معلومة قلت لك صراحة وأرشدتك أين تتحقق."
)
WELCOME_POINTS = [
    "اقتراح إشكالية وكشف الفجوات البحثية",
    "بناء خطة الرسالة ومراجعتها",
    "توثيق المراجع والهوامش",
    "أسئلة لجنة المناقشة",
    "متابعة المهام وموعد التسليم",
]

MIN_GAP = 5'''))

PAIRS.append((
    "class ArabicTextInput(TextInput):",
    '''class ShareIcon(Widget):
    def __init__(self, color=(1, 1, 1, 1), **kw):
        super().__init__(**kw)
        self.icon_color = color
        self.bind(pos=self.redraw, size=self.redraw)

    def redraw(self, *a):
        self.canvas.clear()
        with self.canvas:
            Color(*self.icon_color)
            s = min(self.width, self.height) * 0.5
            cx, cy = self.center_x, self.center_y
            r = s * 0.2
            p1 = (cx + s * 0.5, cy + s * 0.55)
            p2 = (cx - s * 0.5, cy)
            p3 = (cx + s * 0.5, cy - s * 0.55)
            Line(points=[p1[0], p1[1], p2[0], p2[1], p3[0], p3[1]],
                 width=dp(1.6))
            for p in (p1, p2, p3):
                Ellipse(pos=(p[0] - r, p[1] - r), size=(2 * r, 2 * r))


class ArabicTextInput(TextInput):'''))

PAIRS.append((
    '            self.show("\\n\\n".join(warnings))\n\n        return root',
    '            self.show("\\n\\n".join(warnings))\n\n'
    '        Clock.schedule_once(self.maybe_welcome, 0.6)\n'
    '        return root'))

PAIRS.append((
    '''        root.add_widget(self.label(
            "مشرف - رفيق الباحث القانوني",
            size=22, height=dp(60), color=GOLD))
        root.add_widget(self.label(
            "مرحلة العمل"''',
    '''        head = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(6))
        head.add_widget(self.share_button(dp(52)))
        title = self.label(
            "مشرف - رفيق الباحث القانوني", size=20, height=dp(60),
            color=GOLD)
        title.size_hint_y = 1
        head.add_widget(title)
        about = self.button("عن التطبيق", self.open_welcome, 12, dp(52))
        about.size_hint = (None, 1)
        about.width = dp(84)
        head.add_widget(about)
        root.add_widget(head)
        root.add_widget(self.label(
            "مرحلة العمل"'''))

PAIRS.append((
    "    def select_mode(self, name):",
    '''    def para(self, text, size=16, color=WHITE):
        lb = Label(
            text=ar(text, size), size_hint_y=None,
            halign="center", valign="top",
            font_size=sp(size), font_name=self.font, color=color,
        )
        lb.bind(
            width=lambda *a: setattr(lb, "text_size", (lb.width, None)),
            texture_size=lambda *a: setattr(
                lb, "height", lb.texture_size[1] + dp(10)),
        )
        return lb

    def share_button(self, side):
        b = Button(size_hint=(None, None), size=(side, side),
                   background_normal="", background_down="",
                   background_color=(0.16, 0.18, 0.27, 1))
        icon = ShareIcon(color=GOLD)
        b.add_widget(icon)
        b.bind(pos=lambda inst, v: setattr(icon, "pos", v),
               size=lambda inst, v: setattr(icon, "size", v))
        b.bind(on_release=self.share_app)
        return b

    def maybe_welcome(self, *args):
        if not self.data.get("welcomed"):
            self.open_welcome()

    def open_welcome(self, *args):
        view = ModalView(
            size_hint=(1, 1), auto_dismiss=False,
            background="", background_color=(0.07, 0.08, 0.11, 1))
        scroll = ScrollView(do_scroll_x=False)
        box = GridLayout(
            cols=1, size_hint_y=None, padding=dp(20), spacing=dp(14))
        box.bind(minimum_height=box.setter("height"))

        if os.path.exists(LOGO):
            box.add_widget(Image(
                source=LOGO, size_hint_y=None, height=dp(150)))
        box.add_widget(self.para("مرحبًا بك أيها الباحث", 26, GOLD))
        box.add_widget(self.para(
            "أنا «مشرف»، رفيقك الأكاديمي في الدراسات القانونية العليا.", 17))
        box.add_widget(self.para(WELCOME_INTRO, 15, MUTED))
        box.add_widget(self.para("ماذا أقدّم لك؟", 17, GOLD))
        for t in WELCOME_POINTS:
            box.add_widget(self.para("• " + t, 15))

        def close(*a):
            self.data["welcomed"] = True
            self.save_data()
            view.dismiss()

        start = self.button("ابدأ رحلتك البحثية", close, 18, dp(58))
        start.background_normal = ""
        start.background_down = ""
        start.background_color = (0.9, 0.75, 0.3, 1)
        start.color = (0.07, 0.08, 0.11, 1)
        box.add_widget(start)

        row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6))
        row.add_widget(self.share_button(dp(52)))
        row.add_widget(self.button(
            "شارك التطبيق مع زملائك", self.share_app, 15, dp(52)))
        box.add_widget(row)

        scroll.add_widget(box)
        view.add_widget(scroll)
        view.open()

    def share_app(self, *args):
        text = SHARE_TEXT + (("\\n" + SHARE_URL) if SHARE_URL else "")
        try:
            from jnius import autoclass, cast
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            String = autoclass("java.lang.String")
            intent = Intent()
            intent.setAction(Intent.ACTION_SEND)
            intent.putExtra(
                Intent.EXTRA_TEXT,
                cast("java.lang.CharSequence", String(text)))
            intent.setType("text/plain")
            chooser = Intent.createChooser(
                intent,
                cast("java.lang.CharSequence", String("مشاركة التطبيق")))
            PythonActivity.mActivity.startActivity(chooser)
        except Exception:
            Clipboard.copy(text)
            self.show("تعذّر فتح قائمة المشاركة، فنُسخ نص الدعوة. "
                      "الصقه في أي محادثة.")

    def select_mode(self, name):'''))

for old, new in PAIRS:
    if s.count(old) != 1:
        print("ERROR: anchor not found exactly once:")
        print(old[:70])
        sys.exit(1)
    s = s.replace(old, new)

open(P, "w", encoding="utf-8").write(s)
print("main.py patched OK")
