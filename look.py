#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Оформление окна: цвета, шрифты, значки, карточки.
#  Часть проекта EOne screen.
#
#  Автор: EOne
#  Лицензия: CC BY-NC-SA 4.0 — использование в коммерческих целях
#  запрещено без письменного разрешения автора. См. файл LICENSE.
#
"""
look.py - как выглядит само окно программы.

Одно место, где заданы цвета, шрифты и значки. Светлое и тёмное
оформление переключается на ходу: виджеты подписываются на смену
и перекрашиваются.

    look = Look(root)
    look.set_mode("light")      светлое
    look.set_mode("system")     как в Windows
    look.set_mode("screen")     как сейчас на экране водянки

Скруглённые карточки рисуются через PIL: Tk сам такого не умеет,
а движок отрисовки у нас и так под рукой.
"""

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageDraw, ImageTk

import sensors as sensors_mod
import yazyk

# --- цвета -------------------------------------------------------------------

# Роли, а не названия цветов: так оформление можно менять целиком,
# не разыскивая по всей программе, где какой оттенок был вписан.
# Два вида окна. Ночь - тёмно-синяя, с голубо-зелёным свечением, как
# северное сияние. День - тёплый белый, с голубыми переливами.
#
# Ключи grad1 и grad2 - концы градиента, gradsoft - его тихий вариант
# для крупных карточек: на всю карточку яркий перелив кричит, а под
# заголовком с цифрами он нужен еле заметным.
PALETTES = {
    "dark": {
        "bg":        "#0a1020",   # фон окна: глубокий синий, не чёрный
        "surface":   "#101a30",   # карточка
        "raised":    "#16233d",   # карточка под курсором, поля ввода
        "border":    "#1e2f4d",
        "text":      "#e8edf6",
        "dim":       "#8fa0bd",   # приглушённая подпись
        "faint":     "#5d6f90",   # совсем тихая
        "accent":    "#3ddbc0",   # бирюза сияния
        "on_accent": "#04201c",
        "ok":        "#3ddbc0",
        "warn":      "#f4c05a",
        "bad":       "#ff7a85",
        "shadow":    "#03060e",
        "grad1":     "#1a7fb8",   # голубой
        "grad2":     "#33d6a6",   # зелёный - вместе даёт сияние
        "gradsoft1": "#122340",
        "gradsoft2": "#143550",
    },
    "light": {
        "bg":        "#f7f4ef",   # тёплый белый, с уходом в бумагу
        "surface":   "#fffdfa",
        "raised":    "#f0eee9",
        "border":    "#e2ded6",
        "text":      "#15202e",
        "dim":       "#5a677a",
        "faint":     "#8b95a4",
        "accent":    "#2f6fd0",   # синий
        "on_accent": "#ffffff",
        "ok":        "#1f9d68",
        "warn":      "#c2740a",
        "bad":       "#d64550",
        "shadow":    "#c9c2b6",
        "grad1":     "#5aa9f0",   # голубой
        "grad2":     "#2f6fd0",   # синий
        "gradsoft1": "#eef4fd",
        "gradsoft2": "#e3edfb",
    },
}

def _v_chisla(cvet):
    """Цвет «#1a7fb8» в три числа. Не разобрали - берём серый."""
    s = str(cvet or "").strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except (ValueError, IndexError):
        return (128, 128, 128)


# --- шрифты ------------------------------------------------------------------

# Windows 11 ставит Segoe UI Variable, он заметно опрятнее обычного Segoe UI.
# Если его нет, спускаемся по списку до чего-нибудь рабочего.
FACES = {
    "display": ["Segoe UI Variable Display", "Segoe UI Semibold", "Segoe UI",
                "Arial"],
    "text":    ["Segoe UI Variable Text", "Segoe UI", "Arial"],
    "mono":    ["Cascadia Code", "Consolas", "Courier New"],
    "icons":   ["Segoe Fluent Icons", "Segoe MDL2 Assets", "Segoe UI Symbol"],
}

# размер и насыщенность для каждой роли
ROLES = {
    "display": ("display", 20, "bold"),
    "title":   ("display", 13, "bold"),
    "subtitle": ("text", 11, "bold"),
    "body":    ("text", 10, "normal"),
    "small":   ("text", 9, "normal"),
    "mono":    ("mono", 9, "normal"),
    "big":     ("display", 30, "bold"),
}

# Значки из системного набора Windows 11. Имена наши, понятные.
ICONS = {
    "power":        "\ue7e8",    # PowerButton
    "home":         "\ue80f",    # Home
    "themes":       "\ueca5",    # Personalize
    "edit":         "\ue70f",    # Edit
    "settings":     "\ue713",    # Settings
    "sensors":      "\ue9d9",    # Diagnostic
    "about":        "\ue946",    # Info
    "sun":          "\ue706",    # солнце — дневной вид
    "moon":         "\ue708",    # луна — ночной вид
    "sunrise":      "\ued39",    # солнце над горизонтом — по восходу и закату
    "windows":      "\ue793",    # солнце с контрастом — как оформлена Windows
    "clock":        "\ue823",    # часы
    "brightness":   "\ue706",    # яркость подсветки
    "layers":       "\ue81e",    # стопка — слои темы
    "grid":         "\ueca5",    # плитка — список тем
    "chip":         "\ue950",    # процессор
    "thermo":       "\ue9ca",    # градусник
    "water":        "\ueb42",    # капля — водянка
    "sliders":      "\ue9e9",    # ползунки — оптимизация
    "help":         "\ue9ce",    # знак вопроса
    "pause":        "\ue769",    # Pause
    "play":         "\ue768",    # Play
    "refresh":      "\ue72c",    # Refresh
    "add":          "\ue710",    # Add
    "delete":       "\ue74d",    # Delete
    "copy":         "\ue8c8",    # Copy
    "save":         "\ue74e",    # Save
    "folder":       "\ue8b7",    # FolderHorizontal
    "open":         "\ue8e5",    # OpenFile
    "export":       "\uede1",    # Share
    "import":       "\ue896",    # Download
    "up":           "\ue74a",    # ChevronUp
    "down":         "\ue74b",    # ChevronDown
    "hide":         "\ued1a",    # Hide
    "show":         "\ue7b3",    # View
    "warning":      "\ue7ba",    # Warning
    "ok":           "\ue73e",    # Accept
    "tray":         "\ue921",    # Dock
    "screen":       "\ue7f4",    # Devices
    "undo":         "\ue7a7",    # Undo
}


# Запасные значки — обычные знаки Unicode, какие есть в шрифтах любой
# системы. Нужны там, где нет набора Windows: на Linux, на урезанной
# сборке, на машине без Segoe Fluent Icons. Красивее было бы рисовать
# их самим, но эти хотя бы читаются, а квадраты не читаются никак.
ICONS_ZAPAS = {
    "power": "⏻", "home": "⌂", "themes": "❖", "edit": "✎",
    "settings": "⚙", "sensors": "📈", "about": "ⓘ",
    "sun": "☀", "moon": "☾", "sunrise": "🌅", "windows": "◐",
    "clock": "🕐", "brightness": "☀", "layers": "≡", "grid": "▦",
    "chip": "▣", "thermo": "🌡", "water": "💧", "sliders": "⚌",
    "help": "?", "pause": "❚❚", "play": "▶", "refresh": "↻",
    "add": "＋", "delete": "🗑", "copy": "⧉", "save": "💾",
    "folder": "🗀", "open": "🗁", "export": "↗", "import": "↓",
    "up": "⌃", "down": "⌄", "hide": "◌", "show": "◉",
    "warning": "⚠", "ok": "✓", "tray": "▭", "screen": "🖵",
    "undo": "↺",
}


class Look:
    """Текущее оформление окна. Один объект на всю программу."""

    def __init__(self, root, mode=None):
        self.root = root
        self.style = ttk.Style(root)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass
        self._listeners = []
        self._images = {}          # кэш нарисованных карточек
        self._fonts = {}
        self.scale = 1.0
        self.wish = mode or "system"
        self.mode = None              # ещё не применено, первый раз применим
        self.c = dict(PALETTES["dark"])
        self.screen_is_day = False    # чему следовать в режиме «как на экране»
        self.set_mode(self.wish)

    # --- переключение ---------------------------------------------------

    def resolve(self, wish=None):
        """Во что превращается пожелание: «dark» или «light»."""
        wish = wish or self.wish
        if wish == "light":
            return "light"
        if wish == "dark":
            return "dark"
        if wish == "screen":
            return "light" if self.screen_is_day else "dark"
        light = sensors_mod.windows_light_theme()   # system
        return "light" if light else "dark"

    def set_mode(self, wish, force=False):
        """Сменить оформление. Возвращает True, если картинка изменилась."""
        self.wish = wish or "system"
        want = self.resolve()
        if want == self.mode and not force:
            return False
        self.mode = want
        self.c = dict(PALETTES[want])
        self._images.clear()
        self._apply()
        for fn in list(self._listeners):
            try:
                fn(self)
            except Exception:
                pass
        return True

    def recheck(self):
        """Перепроверить внешние условия: оформление Windows или время суток.

        Зовётся раз в секунду из общего такта, стоит доли миллисекунды.
        """
        if self.wish in ("system", "screen"):
            return self.set_mode(self.wish)
        return False

    def on_change(self, fn):
        """Позвать fn(look) при каждой смене оформления."""
        self._listeners.append(fn)
        return fn

    # --- шрифты и значки ------------------------------------------------

    def font(self, role="body", size=None, weight=None):
        face_key, base, base_weight = ROLES.get(role, ROLES["body"])
        size = int(round((size or base) * self.scale))
        weight = weight or base_weight
        key = (face_key, size, weight)
        if key not in self._fonts:
            self._fonts[key] = (self._face(face_key), size, weight)
        return self._fonts[key]

    def icon_font(self, size=12):
        return (self._face("icons"), int(round(size * self.scale)))

    def _face(self, key):
        """Первое семейство из списка, которое есть в системе."""
        attr = "_face_" + key
        got = getattr(self, attr, None)
        if got is None:
            try:
                import tkinter.font as tkf
                have = set(tkf.families())
            except Exception:
                have = set()
            got = next((f for f in FACES[key] if f in have), FACES[key][-1])
            setattr(self, attr, got)
        return got

    def est_shrift_znachkov(self):
        """Есть ли в системе набор значков Windows.

        Проверяем один раз: список семейств у Tk спрашивать недёшево.
        """
        got = getattr(self, "_znachki_est", None)
        if got is None:
            got = self._face("icons") in FACES["icons"][:-1]
            self._znachki_est = got
        return got

    def icon(self, name):
        """Знак значка. Нет набора Windows - берём обычный Unicode."""
        if self.est_shrift_znachkov():
            return ICONS.get(name, "")
        return ICONS_ZAPAS.get(name, "•")

    # --- ttk -------------------------------------------------------------

    def _apply(self):
        c, st = self.c, self.style
        self.root.configure(bg=c["bg"])

        st.configure(".", background=c["bg"], foreground=c["text"],
                     fieldbackground=c["raised"], bordercolor=c["border"],
                     lightcolor=c["border"], darkcolor=c["border"],
                     troughcolor=c["raised"], focuscolor=c["accent"],
                     insertcolor=c["text"])

        st.configure("TFrame", background=c["bg"])
        st.configure("Card.TFrame", background=c["surface"])
        st.configure("Raised.TFrame", background=c["raised"])

        for name, role, colour in (
                ("TLabel", "body", "text"),
                ("Dim.TLabel", "body", "dim"),
                ("Faint.TLabel", "small", "faint"),
                ("Small.TLabel", "small", "dim"),
                ("Title.TLabel", "title", "text"),
                ("Sub.TLabel", "subtitle", "text"),
                ("Display.TLabel", "display", "text"),
                ("Big.TLabel", "big", "text"),
                ("Ok.TLabel", "body", "ok"),
                ("Warn.TLabel", "body", "warn"),
                ("Bad.TLabel", "body", "bad"),
                ("Accent.TLabel", "body", "accent")):
            st.configure(name, background=c["bg"], foreground=c[colour],
                         font=self.font(role))
        # те же подписи, но на карточке
        for name in ("TLabel", "Dim.TLabel", "Faint.TLabel", "Small.TLabel",
                     "Title.TLabel", "Sub.TLabel", "Display.TLabel",
                     "Big.TLabel", "Ok.TLabel", "Warn.TLabel", "Bad.TLabel",
                     "Accent.TLabel"):
            st.configure("Card." + name, background=c["surface"],
                         foreground=st.lookup(name, "foreground"),
                         font=st.lookup(name, "font"))

        st.configure("TButton", background=c["raised"], foreground=c["text"],
                     borderwidth=0, focusthickness=0, padding=(14, 8),
                     font=self.font("body"))
        st.map("TButton",
               background=[("pressed", c["border"]), ("active", c["border"]),
                           ("disabled", c["surface"])],
               foreground=[("disabled", c["faint"])])

        st.configure("Accent.TButton", background=c["accent"],
                     foreground=c["on_accent"], font=self.font("body", weight="bold"))
        st.map("Accent.TButton",
               background=[("pressed", c["accent"]), ("active", c["accent"]),
                           ("disabled", c["raised"])],
               foreground=[("disabled", c["faint"])])

        # Тихие кнопки обведены цветом накала. Без обводки они читались
        # как обычные надписи, и было не понять, что нажимается, а что
        # просто написано.
        st.configure("Quiet.TButton", background=c["surface"],
                     foreground=c["accent"], padding=(10, 6),
                     borderwidth=1, relief="solid",
                     bordercolor=c["accent"], lightcolor=c["surface"],
                     darkcolor=c["surface"])
        st.map("Quiet.TButton",
               background=[("active", c["raised"])],
               foreground=[("active", c["text"])],
               bordercolor=[("active", c["accent"])],
               lightcolor=[("active", c["raised"])],
               darkcolor=[("active", c["raised"])])

        st.configure("Icon.TButton", background=c["surface"],
                     foreground=c["accent"], padding=(6, 4),
                     borderwidth=1, relief="solid",
                     bordercolor=c["accent"], lightcolor=c["surface"],
                     darkcolor=c["surface"],
                     font=self.icon_font(13))
        st.map("Icon.TButton",
               background=[("active", c["raised"])],
               foreground=[("active", c["text"])],
               bordercolor=[("active", c["accent"])],
               lightcolor=[("active", c["raised"])],
               darkcolor=[("active", c["raised"])])

        st.configure("TEntry", fieldbackground=c["raised"], foreground=c["text"],
                     bordercolor=c["border"], insertcolor=c["text"],
                     padding=(6, 5))
        st.configure("TCombobox", fieldbackground=c["raised"],
                     background=c["raised"], foreground=c["text"],
                     arrowcolor=c["dim"], padding=(4, 4))
        st.map("TCombobox", fieldbackground=[("readonly", c["raised"])],
               foreground=[("readonly", c["text"])])

        for name in ("TCheckbutton", "TRadiobutton"):
            st.configure(name, background=c["bg"], foreground=c["text"],
                         font=self.font("body"), focuscolor=c["bg"],
                         indicatorcolor=c["raised"], bordercolor=c["border"])
            st.map(name, background=[("active", c["bg"])],
                   indicatorcolor=[("selected", c["accent"])])
            st.configure("Card." + name, background=c["surface"],
                         foreground=c["text"], font=self.font("body"),
                         focuscolor=c["surface"], indicatorcolor=c["raised"],
                         bordercolor=c["border"])
            st.map("Card." + name, background=[("active", c["surface"])],
                   indicatorcolor=[("selected", c["accent"])])

        st.configure("TScale", background=c["surface"], troughcolor=c["raised"],
                     bordercolor=c["border"], lightcolor=c["accent"],
                     darkcolor=c["accent"])
        st.configure("Vertical.TScrollbar", background=c["border"],
                     troughcolor=c["bg"], arrowcolor=c["dim"],
                     bordercolor=c["bg"], relief="flat")
        st.map("Vertical.TScrollbar", background=[("active", c["dim"])])
        st.configure("Horizontal.TScrollbar", background=c["border"],
                     troughcolor=c["bg"], arrowcolor=c["dim"],
                     bordercolor=c["bg"], relief="flat")

        st.configure("TSeparator", background=c["border"])
        st.configure("TLabelframe", background=c["bg"], bordercolor=c["border"])
        st.configure("TLabelframe.Label", background=c["bg"], foreground=c["dim"],
                     font=self.font("small"))

        # обычные виджеты Tk: ttk-стили на них не действуют
        self.root.option_add("*Listbox.background", c["surface"])
        self.root.option_add("*Listbox.foreground", c["text"])
        self.root.option_add("*Listbox.selectBackground", c["accent"])
        self.root.option_add("*Listbox.selectForeground", c["on_accent"])
        self.root.option_add("*Listbox.highlightThickness", 0)
        self.root.option_add("*Listbox.borderWidth", 0)
        self.root.option_add("*Text.background", c["surface"])
        self.root.option_add("*Text.foreground", c["text"])
        self.root.option_add("*Text.insertBackground", c["text"])
        self.root.option_add("*Canvas.highlightThickness", 0)

    # --- рисование -------------------------------------------------------

    def rounded(self, w, h, radius=12, fill=None, border=None, width=1,
                under=None, fill2=None):
        """Скруглённый прямоугольник как картинка.

        Tk не умеет скруглять углы, поэтому рисуем их сами и подкладываем
        под содержимое. Прозрачности в Tk тоже нет, так что сразу
        накладываем на цвет того, что окажется снизу.

        fill2 - второй цвет: тогда заливка не ровная, а перелив сверху
        вниз. Готовая картинка придерживается по размеру и цветам, так
        что перелив считается один раз, а не на каждую перерисовку.
        """
        w, h = max(1, int(w)), max(1, int(h))
        key = (w, h, radius, fill, border, width, under, fill2)
        got = self._images.get(key)
        if got is not None:
            return got
        base = under or self.c["bg"]
        img = Image.new("RGB", (w, h), base)
        d = ImageDraw.Draw(img)
        box = [0, 0, w - 1, h - 1]
        if fill2:
            # Перелив рисуем во весь прямоугольник, а углы срезаем маской:
            # так не надо ни считать скругление вручную, ни городить
            # прозрачность, которой в Tk нет.
            sverhu = _v_chisla(fill or self.c["surface"])
            snizu = _v_chisla(fill2)
            polosa = Image.new("RGB", (1, max(2, h)))
            for y in range(polosa.height):
                dolya = y / (polosa.height - 1)
                polosa.putpixel((0, y), tuple(
                    int(round(a + (b - a) * dolya))
                    for a, b in zip(sverhu, snizu)))
            maska = Image.new("L", (w, h), 0)
            ImageDraw.Draw(maska).rounded_rectangle(box, radius=radius,
                                                    fill=255)
            img.paste(polosa.resize((w, h), Image.BILINEAR), (0, 0), maska)
            if border:
                d.rounded_rectangle(box, radius=radius, outline=border,
                                    width=width)
        else:
            d.rounded_rectangle(box, radius=radius,
                                fill=fill or self.c["surface"],
                                outline=border, width=width if border else 0)
        photo = ImageTk.PhotoImage(img)
        self._images[key] = photo       # ссылку держим, иначе картинку уберут
        return photo


class Card(tk.Canvas):
    """Карточка со скруглёнными углами. Содержимое кладётся в .body."""

    def __init__(self, parent, look, radius=14, padding=16, fill=None,
                 border=True, under=None, grad=None, stroke=None, **kw):
        super().__init__(parent, highlightthickness=0, bd=0,
                         bg=under or look.c["bg"], **kw)
        self.look = look
        self.radius = radius
        self.padding = padding
        self.fill_key = fill
        self.border = border
        self.under = under
        # grad="soft" - тихий перелив вместо ровной заливки,
        # grad="accent" - яркий, для одной-двух главных карточек.
        self.grad = grad
        # Цвет обводки: ключ палитры. Обычным карточкам хватает тихой
        # рамки, а те, по которым щёлкают, обводятся цветом накала.
        self.stroke = stroke
        # Содержимое кладём с отступом от края: рамка внутри - обычная,
        # прямоугольная, и положенная вплотную она закрыла бы собой
        # скруглённые углы. Отступ оставляет их на виду.
        self.otstup = max(3, radius // 3)
        self.body = ttk.Frame(self, style="Card.TFrame", padding=padding)
        self._win = self.create_window(self.otstup, self.otstup, anchor="nw",
                                       window=self.body)
        self._bg = None
        self.bind("<Configure>", self._relayout)
        self.body.bind("<Configure>", self._fit)
        look.on_change(self._restyle)

    def _restyle(self, look):
        self.configure(bg=self.under or look.c["bg"])
        self._redraw(self.winfo_width(), self.winfo_height())

    def _fit(self, _=None):
        """Высота карточки идёт за содержимым."""
        need = self.body.winfo_reqheight()
        if need and abs(need - int(self["height"] or 0)) > 1:
            self.configure(height=need)

    def _relayout(self, e=None):
        w = e.width if e else self.winfo_width()
        h = e.height if e else self.winfo_height()
        self.itemconfigure(self._win, width=w)
        self._redraw(w, h)

    def _redraw(self, w, h):
        if w < 2 or h < 2:
            return
        c = self.look.c
        zalivka = c.get(self.fill_key or "surface", self.fill_key)
        vtoroy = None
        if self.grad == "soft":
            zalivka, vtoroy = c["gradsoft1"], c["gradsoft2"]
        elif self.grad == "accent":
            zalivka, vtoroy = c["grad1"], c["grad2"]
        ramka = None
        if self.stroke:
            ramka = c.get(self.stroke, self.stroke)
        elif self.border:
            ramka = c["border"]
        photo = self.look.rounded(
            w, h, self.radius, zalivka, ramka,
            2 if self.stroke else 1, self.under or c["bg"], vtoroy)
        if self._bg is None:
            self._bg = self.create_image(0, 0, anchor="nw", image=photo)
            self.tag_lower(self._bg)
        else:
            self.itemconfigure(self._bg, image=photo)


class Banner(tk.Canvas):
    """Заголовок страницы: название, пояснение и черта с переливом.

    Плита во всю ширину под заголовок оказалась тяжёлой: справа от
    короткого слова остаётся пустое цветное поле, и оно перетягивает
    внимание на себя. Поэтому цвет остался только в черте под названием -
    её видно, а спорить с содержимым страницы ей нечем.

    Рисуем на холсте, а не виджетами, потому что у Tk нет прозрачности
    и перелив под обычной надписью закрасился бы её фоном.
    """

    VYSOTA = 92            # название, пояснение и черта
    CHERTA = 46            # длина черты

    def __init__(self, parent, look, title, subtitle="", height=None, **kw):
        super().__init__(parent, highlightthickness=0, bd=0,
                         height=height or self.VYSOTA, bg=look.c["bg"], **kw)
        self.look = look
        self.title = title
        self.subtitle = subtitle
        self.bind("<Configure>", lambda e: self._redraw(e.width, e.height))
        look.on_change(lambda _l: self._redraw(self.winfo_width(),
                                               self.winfo_height()))

    def set_subtitle(self, text):
        self.subtitle = text
        self._redraw(self.winfo_width(), self.winfo_height())

    def _redraw(self, w, h):
        if w < 2 or h < 2:
            return
        c = self.look.c
        self.configure(bg=c["bg"])
        self.delete("all")
        self.create_text(0, 2, anchor="nw", text=yazyk.t(self.title),
                         fill=c["text"], font=self.look.font("display"))
        # Черта: короткие куски разного цвета, вместе - перелив.
        # Целой картинкой ради полоски в четыре точки заводить незачем.
        y = h - 26
        kusok = max(1, self.CHERTA // 12)
        a, b = _v_chisla(c["grad1"]), _v_chisla(c["grad2"])
        for i in range(12):
            dolya = i / 11.0
            cvet = "#%02x%02x%02x" % tuple(
                int(round(p + (q - p) * dolya)) for p, q in zip(a, b))
            self.create_rectangle(i * kusok, y, (i + 1) * kusok + 1, y + 4,
                                  fill=cvet, outline=cvet)
        if self.subtitle:
            self.create_text(self.CHERTA + 14, y + 2, anchor="w",
                             text=yazyk.t(self.subtitle), fill=c["dim"],
                             font=self.look.font("small"))


class Segmented(ttk.Frame):
    """Ряд кнопок, из которых нажата одна. Вместо кучки радиокнопок.

    options - список пар (значение, подпись) или троек со значком.
    """

    def __init__(self, parent, look, options, value=None, command=None,
                 on_card=True, v_ryadu=0, krupno=False, **kw):
        """v_ryadu - сколько кнопок помещать в строку, 0 - все в одну.

        Десять кнопок погоды в одну строку не влезали и уезжали за край
        окна вместе с последней. Переносим их на вторую строку.
        """
        super().__init__(parent, style="Card.TFrame" if on_card else "TFrame",
                         **kw)
        self.look = look
        self.command = command
        self.value = value
        self.on_card = on_card
        self.buttons = {}
        self.krupno = krupno
        stil = "Card.TFrame" if on_card else "TFrame"
        ryad = None
        for n, opt in enumerate(options):
            if ryad is None or (v_ryadu and n % v_ryadu == 0):
                ryad = ttk.Frame(self, style=stil)
                ryad.pack(anchor="w", pady=(0 if n == 0 else 4, 0))
            val, label = opt[0], yazyk.t(opt[1])
            icon = opt[2] if len(opt) > 2 else None
            b = tk.Button(ryad, text=(look.icon(icon) + "  " + label) if icon
                          else label, bd=0, relief="flat", takefocus=0,
                          padx=22 if krupno else 10,
                          pady=13 if krupno else 6, cursor="hand2",
                          command=lambda v=val: self.pick(v))
            b.pack(side="left", padx=(0, 4))
            self.buttons[val] = b
        look.on_change(lambda _l: self.repaint())
        self.repaint()

    def pick(self, val, quiet=False):
        self.value = val
        self.repaint()
        if self.command and not quiet:
            self.command(val)

    def set(self, val):
        self.pick(val, quiet=True)

    def repaint(self):
        c = self.look.c
        base = c["surface"] if self.on_card else c["bg"]
        self.configure(style="Card.TFrame" if self.on_card else "TFrame")
        for val, b in self.buttons.items():
            on = (val == self.value)
            b.configure(
                bg=c["accent"] if on else c["raised"],
                fg=c["on_accent"] if on else c["dim"],
                activebackground=c["accent"] if on else c["border"],
                activeforeground=c["on_accent"] if on else c["text"],
                font=self.look.font("subtitle" if self.krupno else "body",
                                    weight="bold" if on else "normal"),
                highlightbackground=base)


class SideList(ttk.Frame):
    """Стопка блоков слева: нажал — подсветился, справа развернулось нужное.

    options - список троек (ключ, подпись, значок).
    """

    def __init__(self, parent, look, options, value=None, command=None,
                 width=250, **kw):
        super().__init__(parent, style="TFrame", width=width, **kw)
        self.pack_propagate(False)
        self.look = look
        self.command = command
        self.value = value or (options[0][0] if options else None)
        self.rows = {}
        for key, label, icon in options:
            row = tk.Frame(self, bd=0, highlightthickness=0, cursor="hand2")
            row.pack(fill="x", pady=(0, 8))
            ic = tk.Label(row, text=look.icon(icon), bd=0,
                          font=look.icon_font(16))
            ic.pack(side="left", padx=(16, 12), pady=13)
            tx = tk.Label(row, text=label, bd=0, anchor="w",
                          font=look.font("subtitle"))
            tx.pack(side="left", fill="x", expand=True, pady=13)
            for w in (row, ic, tx):
                w.bind("<Button-1>", lambda e, k=key: self.pick(k))
            self.rows[key] = (row, ic, tx)
        look.on_change(lambda _l: self.repaint())
        self.repaint()

    def pick(self, key, quiet=False):
        self.value = key
        self.repaint()
        if self.command and not quiet:
            self.command(key)

    def set(self, key):
        self.pick(key, quiet=True)

    def repaint(self):
        c = self.look.c
        for key, (row, ic, tx) in self.rows.items():
            on = (key == self.value)
            bg = c["accent"] if on else c["surface"]
            fg = c["on_accent"] if on else c["text"]
            row.configure(bg=bg)
            ic.configure(bg=bg, fg=fg if on else c["accent"])
            tx.configure(bg=bg, fg=fg)


class Tip:
    """Подсказка, всплывающая при задержке мыши.

    Одна на всю программу: окошко создаётся один раз и переезжает
    к тому виджету, над которым замерла мышь. Так не плодятся окна
    и не мигает при быстром проходе по панели.
    """

    DELAY = 700          # сколько держать мышь, миллисекунд

    def __init__(self, root, look):
        self.root = root
        self.look = look
        self.win = None
        self.label = None
        self.job = None
        self.texts = {}

    def add(self, widget, text):
        """Привязать подсказку к виджету.

        Перевод здесь, а не по месту вызова: подсказка не проходит через
        text=, и общий крючок _perevod_nadpisey её не видит.
        """
        if not text:
            return widget
        self.texts[str(widget)] = yazyk.t(text)
        widget.bind("<Enter>", lambda e, w=widget: self._enter(w), add="+")
        widget.bind("<Leave>", lambda e: self._leave(), add="+")
        widget.bind("<ButtonPress>", lambda e: self._leave(), add="+")
        return widget

    def _enter(self, widget):
        self._cancel()
        self.job = self.root.after(self.DELAY, lambda: self._show(widget))

    def _leave(self):
        self._cancel()
        if self.win is not None:
            self.win.withdraw()

    def _cancel(self):
        if self.job is not None:
            try:
                self.root.after_cancel(self.job)
            except Exception:
                pass
            self.job = None

    def _show(self, widget):
        text = self.texts.get(str(widget))
        if not text:
            return
        try:
            if not widget.winfo_ismapped():
                return
        except Exception:
            return
        c = self.look.c
        if self.win is None:
            self.win = tk.Toplevel(self.root)
            self.win.wm_overrideredirect(True)     # без рамки и заголовка
            self.win.attributes("-topmost", True)
            self.label = tk.Label(self.win, justify="left", anchor="w",
                                  padx=10, pady=7, bd=0, wraplength=360)
            self.label.pack()
        self.label.configure(text=text, bg=c["raised"], fg=c["text"],
                             font=self.look.font("small"))
        self.win.configure(bg=c["border"])
        self.label.pack_configure(padx=1, pady=1)
        self.win.update_idletasks()
        x = widget.winfo_rootx() + 12
        y = widget.winfo_rooty() + widget.winfo_height() + 8
        # не вылезаем за край экрана
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        x = min(x, self.root.winfo_screenwidth() - w - 8)
        if y + h > self.root.winfo_screenheight() - 8:
            y = widget.winfo_rooty() - h - 8
        self.win.wm_geometry("+{}+{}".format(int(x), int(y)))
        self.win.deiconify()


def _perevod_nadpisey():
    """Пропустить все надписи окна через перевод.

    Один крючок на весь ttk вместо тысячи обёрток по коду: любая надпись,
    заданная через text=, переводится сама. Строки, собранные из кусков
    через format, надо переводить руками - шаблон до подстановки.
    """
    def obernut(cls):
        init, conf = cls.__init__, cls.configure

        def _init(self, *a, **kw):
            if "text" in kw:
                kw["text"] = yazyk.t(kw["text"])
            init(self, *a, **kw)

        def _conf(self, cnf=None, **kw):
            if "text" in kw:
                kw["text"] = yazyk.t(kw["text"])
            return conf(self, cnf, **kw)

        cls.__init__, cls.configure, cls.config = _init, _conf, _conf

    for cls in (ttk.Label, ttk.Button, ttk.Checkbutton, ttk.Radiobutton,
                ttk.LabelFrame, tk.Label, tk.Button, tk.Checkbutton):
        obernut(cls)


_perevod_nadpisey()


def icon_label(parent, look, name, size=14, style="Card.Dim.TLabel"):
    """Отдельный значок как подпись."""
    lab = ttk.Label(parent, text=look.icon(name), style=style)
    lab.configure(font=look.icon_font(size))
    return lab
