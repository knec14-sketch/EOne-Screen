#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Главная страница: что сейчас на экране и три главных регулятора.
#  Часть проекта EOne screen.
#
#  Автор: EOne
#  Лицензия: CC BY-NC-SA 4.0 — использование в коммерческих целях
#  запрещено без письменного разрешения автора. См. файл LICENSE.
#
"""
home.py - главная страница окна.

Здесь намеренно мало всего. Ровно то, за чем сюда заходят:

    видно, что именно уходит на экран прямо сейчас
    включить и выключить
    выбрать дневной или ночной вид
    подкрутить яркость

Всё остальное - в «Настройках». Тут не место частоте кадров и качеству
сжатия: их трогают раз в жизни, а мешать они будут каждый день.

Зеркало намеренно не анимировано: датчики в нём живые и обновляются
раз в секунду, а кадры фона не листаются. Иначе окно тратило бы столько
же, сколько сам вывод на экран, и вдобавок вхолостую.
"""

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

import edinicy
import look as L
import panel as panel_mod
import prefs
from yazyk import t


class Home(ttk.Frame):
    """Главная страница внутри прокрутки.

    Прокрутка тут - страховка на маленькое окно. Обычно её не видно:
    кадр подстраивается под то, сколько места осталось, и всё помещается.
    Но если человек сожмёт окно до предела, нижняя строчка должна
    оставаться доступной, а не прятаться за краем.
    """

    def __init__(self, parent, look, app):
        super().__init__(parent, style="TFrame")
        self.look = look
        self.app = app
        self.polotno = tk.Canvas(self, highlightthickness=0, bd=0,
                                 bg=look.c["bg"])
        self.polosa = ttk.Scrollbar(self, orient="vertical",
                                    command=self.polotno.yview)
        self.polotno.configure(yscrollcommand=self.polosa.set)
        self.polotno.pack(side="left", fill="both", expand=True)
        self._polosa_vidna = False
        # Содержимое страницы кладётся сюда, а не прямо на страницу.
        self.holst = ttk.Frame(self.polotno, style="TFrame", padding=(22, 18))
        self._okno = self.polotno.create_window((0, 0), window=self.holst,
                                                anchor="nw")
        self.holst.bind("<Configure>", self._pod_soderzhimoe)
        self.polotno.bind("<Configure>", self._po_shirine)
        self.polotno.bind_all("<MouseWheel>", self._koleso, add="+")
        look.on_change(lambda lk: self.polotno.configure(bg=lk.c["bg"]))
        self._mirror = None          # отдельная панель только для предпросмотра
        self.photo = None
        self.active = False
        self._last_size = None
        self._build()
        look.on_change(self._restyle)

    # --- прокрутка -------------------------------------------------------

    def _pod_soderzhimoe(self, _e=None):
        """Появление и исчезновение полосы. Состояние помним сами:
        winfo_ismapped у скрытого окна равен нулю у всего подряд."""
        self.polotno.configure(scrollregion=self.polotno.bbox("all"))
        nado = self.holst.winfo_reqheight() > self.polotno.winfo_height() + 2
        if nado and not self._polosa_vidna:
            self.polosa.pack(side="right", fill="y")
            self._polosa_vidna = True
        elif not nado and self._polosa_vidna:
            self.polosa.pack_forget()
            self._polosa_vidna = False

    def _po_shirine(self, e):
        self.polotno.itemconfigure(self._okno, width=e.width)
        self._pod_soderzhimoe()

    def _koleso(self, e):
        if self.winfo_ismapped() and self._polosa_vidna:
            self.polotno.yview_scroll(-int(e.delta / 120), "units")

    # --- сборка ---------------------------------------------------------

    def _build(self):
        lk = self.look

        # --- зеркало экрана, справа от него яркость ---
        # Ряд не растягиваем: иначе он забирает всю высоту окна, а нижние
        # блоки уезжают за край. Размер кадра считается отдельно, по тому,
        # сколько места осталось - см. _draw_mirror.
        row = ttk.Frame(self.holst)
        row.pack(fill="x")

        self.frame_card = L.Card(row, lk, radius=16, padding=12)
        self.frame_card.pack(side="left", fill="both", expand=True)
        top = ttk.Frame(self.frame_card.body, style="Card.TFrame")
        top.pack(fill="x", pady=(0, 10))
        L.icon_label(top, lk, "screen", 15).pack(side="left", padx=(2, 8))
        ttk.Label(top, text="Сейчас на экране",
                  style="Card.Sub.TLabel").pack(side="left")
        self.state_lbl = ttk.Label(top, text="выключен",
                                   style="Card.Dim.TLabel")
        self.state_lbl.pack(side="right", padx=2)

        self.mirror = tk.Canvas(self.frame_card.body, width=960, height=480,
                                highlightthickness=0, bd=0, bg=lk.c["bg"])
        self.mirror.pack()
        self.hint = ttk.Label(self.frame_card.body, text="",
                              style="Card.Faint.TLabel")
        self.hint.pack(anchor="w", pady=(8, 0))

        # Яркость стоит вплотную к картинке и тянется вертикально: так
        # видно, что крутишь именно её, а не что-то в программе.
        bcard = L.Card(row, lk, radius=16, padding=12, width=92)
        bcard.pack(side="left", fill="y", padx=(14, 0))
        bb = bcard.body
        L.icon_label(bb, lk, "brightness", 18, "Card.Accent.TLabel").pack(
            pady=(2, 8))
        try:
            start_v = int(self.app.cfg().get("screen", {}).get("brightness", 90))
        except Exception:
            start_v = 90
        self._bright_ready = False   # пока раскладываемся, не писать
        self.bright = tk.IntVar(value=start_v)
        # Длина скромная: ползунок стоит в своей карточке, а та тянет
        # за собой высоту всего ряда - от длинного оставалась пустота
        # под кадром.
        self.bright_scale = ttk.Scale(bb, from_=100, to=0, orient="vertical",
                                      variable=self.bright, length=170,
                                      command=lambda _v: self._bright_moved())
        self.bright_scale.pack(fill="y", expand=True)
        self.bright_lbl = ttk.Label(bb, text="{} %".format(start_v),
                                    style="Card.Dim.TLabel")
        self.bright_lbl.pack(pady=(8, 2))
        self.app.tip.add(self.bright_scale,
                         "Яркость подсветки экрана водянки. Уходит на экран, "
                         "когда отпустишь ползунок.")

        # --- крупные кнопки: включить, пауза, перезапустить ---
        big = ttk.Frame(self.holst)
        big.pack(fill="x", pady=(16, 0))
        self._nizhnie = [big]
        self.power = self._big(big, "power", "Включить экран",
                               self.app.toggle_screen, accent=True,
                               tip="Начать или прекратить вывод картинки "
                                   "на экран водянки.")
        self.pause_btn = self._big(big, "pause", "Пауза",
                                   self.app.toggle_pause,
                                   tip="Придержать вывод, не закрывая порт. "
                                       "Экран замрёт на последнем кадре.")
        self.restart_btn = self._big(big, "refresh", "Перезапустить",
                                     self.app.restart_screen,
                                     tip="Заново открыть порт и поздороваться "
                                         "с экраном. Выручает, если картинка "
                                         "сбилась или порт подвис.")

        # --- выбор отображения ---
        card = L.Card(self.holst, lk, radius=14, padding=14)
        card.pack(fill="x", pady=(14, 0))
        self._nizhnie.append(card)
        b = card.body
        line = ttk.Frame(b, style="Card.TFrame")
        line.pack(fill="x")
        ttk.Label(line, text="Что показывать",
                  style="Card.Sub.TLabel").pack(side="left")
        self.sun_lbl = ttk.Label(line, text="", style="Card.Faint.TLabel")
        self.sun_lbl.pack(side="right")

        # Две разные вещи, и подписаны они порознь: слева выбирают, когда
        # на экране день, а когда ночь; справа - какую погоду показывать.
        # Без подписей эти два ряда читались как один длинный список,
        # и было непонятно, что с чем связано.
        # Друг под другом, а не слева и справа: рядом им не хватало
        # ширины, и последняя кнопка погоды уезжала за край окна.
        levo = ttk.Frame(b, style="Card.TFrame")
        levo.pack(fill="x", pady=(10, 0))
        pravo = ttk.Frame(b, style="Card.TFrame")
        pravo.pack(fill="x", pady=(12, 0))
        # Держим ссылки: то, чего тема не умеет, с главной убирается.
        self.card_vybor, self.gruppa_den, self.gruppa_pogoda = card, levo, pravo
        ttk.Label(levo, text="День и ночь",
                  style="Card.Faint.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(pravo, text="Погода на экране",
                  style="Card.Faint.TLabel").pack(anchor="w", pady=(0, 4))

        self.modes = L.Segmented(
            levo, lk,
            [("auto", "По солнцу", "sunrise"),
             ("system", "Как в Windows", "windows"),
             ("night", "Ночь", "moon"),
             ("day", "День", "sun")],
            value="auto", command=self.app.set_day_mode)
        self.modes.pack(anchor="w")
        self._pogoda(pravo, lk)
        for key, tip in (
                ("auto", "Светлеет на рассвете и темнеет на закате, "
                         "по времени восхода и заката в твоём городе."),
                ("system", "Следит за оформлением Windows: светлая тема — "
                           "дневной вид, тёмная — ночной."),
                ("night", "Всегда ночной вид, независимо от времени."),
                ("day", "Всегда дневной вид, независимо от времени.")):
            if key in self.modes.buttons:
                self.app.tip.add(self.modes.buttons[key], tip)

        # --- строчка про открытую тему ---
        self.pogoda_lbl = ttk.Label(b, text="", style="Card.Faint.TLabel",
                                    justify="left")
        self.pogoda_lbl.pack(anchor="w", pady=(8, 0))

        foot = ttk.Frame(self.holst)
        foot.pack(fill="x", pady=(12, 0))
        self._nizhnie.append(foot)
        self.foot = foot
        self.theme_lbl = ttk.Label(foot, text="", style="Dim.TLabel")
        self.theme_lbl.pack(side="left")
        ttk.Button(foot, text=lk.icon("edit") + "  " + t("Открыть в редакторе"),
                   style="Quiet.TButton",
                   command=lambda: self.app.show_page("editor")).pack(
            side="right")

    def _big(self, parent, icon, label, command, accent=False, tip=""):
        """Крупная кнопка: значок сверху, подпись снизу.

        Не обычная кнопка, а рамка с двумя подписями: значок берётся из
        набора Windows и требует своего шрифта, а Tk одной кнопке двух
        шрифтов не даёт.
        """
        lk = self.look
        box = tk.Frame(parent, bd=0, highlightthickness=0, cursor="hand2")
        box.pack(side="left", padx=(0, 12))
        ic = tk.Label(box, text=lk.icon(icon), bd=0,
                      font=lk.icon_font(26))
        ic.pack(padx=34, pady=(14, 2))
        tx = tk.Label(box, text=label, bd=0, font=lk.font("subtitle"))
        tx.pack(padx=34, pady=(0, 14))
        for w in (box, ic, tx):
            w.bind("<Button-1>", lambda e, fn=command: fn())
            w.bind("<Enter>", lambda e, b=box: self._hover_big(b, True))
            w.bind("<Leave>", lambda e, b=box: self._hover_big(b, False))
        box._parts = (ic, tx)
        box._icon = icon
        box._accent = accent
        box._hot = False
        self._paint_big(box)
        if tip:
            for w in (box, ic, tx):
                self.app.tip.add(w, tip)
        return box

    def _hover_big(self, box, on):
        box._hot = on
        self._paint_big(box)

    def _paint_big(self, box, label=None, icon=None):
        c = self.look.c
        ic, tx = box._parts
        if icon:
            box._icon = icon
            ic.configure(text=self.look.icon(icon))
        if label is not None:
            tx.configure(text=label)
        if box._accent:
            bg = c["accent"]
            fg = c["on_accent"]
        else:
            bg = c["raised"] if box._hot else c["surface"]
            fg = c["text"]
        for w in (box, ic, tx):
            w.configure(bg=bg)
        ic.configure(fg=fg, font=self.look.icon_font(26))
        tx.configure(fg=fg, font=self.look.font("subtitle"))

    def _restyle(self, lk):
        self.mirror.configure(bg=lk.c["bg"])
        for b in (self.power, self.pause_btn, self.restart_btn):
            self._paint_big(b)

    # --- живые значения --------------------------------------------------

    def _bright_moved(self):
        if not self._bright_ready:
            return          # это ещё раскладка окна, а не рука человека
        v = int(self.bright.get())
        self.bright_lbl.config(text="{} %".format(v))
        self.app.set_brightness(v)

    def show(self):
        self.active = True
        self.po_teme()
        self.tick()
        # первое движение мыши по ползунку теперь настоящее
        self.after(400, lambda: setattr(self, "_bright_ready", True))

    def po_teme(self):
        """Убрать с главной то, чего открытая тема не умеет.

        Тему в одном-единственном исполнении незачем спрашивать, день
        сейчас или ночь, а тему без погоды - какую погоду показывать.
        Если тема не умеет ни того, ни другого, вся карточка уходит.
        """
        import themes as themes_mod
        cfg = self.app.cfg()
        den = themes_mod.umeet_den(cfg)
        pogoda = themes_mod.umeet_pogodu(cfg)
        # Возвращаем блок на его место, а не в конец: pack после
        # pack_forget кладёт виджет последним, и погода оказалась бы
        # ниже строчки про то, что за окном.
        for est, blok, kak in (
                (den, self.gruppa_den,
                 dict(fill="x", pady=(10, 0), before=self.gruppa_pogoda)),
                (pogoda, self.gruppa_pogoda,
                 dict(fill="x", pady=(12, 0), before=self.pogoda_lbl))):
            if est and not blok.winfo_ismapped():
                blok.pack(**kak)
            elif not est:
                blok.pack_forget()
        if den or pogoda:
            if not self.card_vybor.winfo_ismapped():
                self.card_vybor.pack(fill="x", pady=(14, 0),
                                     before=self.foot)
        else:
            self.card_vybor.pack_forget()
        self.sun_lbl.configure(text="" if not den else self.sun_lbl.cget("text"))

    def hide(self):
        self.active = False

    def tick(self):
        """Раз в секунду: обновить надписи и перерисовать зеркало."""
        if not self.active or self.app.hidden():
            return
        r = self.app.runner
        on = self.app.running()
        self.power._accent = not on         # выключен - зовём включить
        self._paint_big(self.power,
                        "Выключить экран" if on else "Включить экран")
        if on:
            self.state_lbl.configure(
                text=r.status if r.status != "работает"
                else t("работает · {:.0f} кадр/с").format(r.fps_real),
                style="Card.Ok.TLabel" if r.status == "работает"
                else "Card.Warn.TLabel")
            self._paint_big(self.pause_btn,
                            "Продолжить" if r.paused else "Пауза",
                            icon="play" if r.paused else "pause")
        else:
            self.state_lbl.configure(text="выключен", style="Card.Dim.TLabel")

        d = self.app.data
        have_sun = getattr(self.app.sensors, "sunrise", None) is not None
        self.sun_lbl.configure(text=t("восход {}   закат {}   сейчас {:.0f} % дня")
                               .format(d.get("sunrise", "07:00"),
                                       d.get("sunset", "20:00"),
                                       float(d.get("day_factor", 0) or 0) * 100)
                               + ("" if have_sun
                                  else "   " + t("(прогноз не пришёл)")))
        self.theme_lbl.configure(text=t("тема: ") + self.app.theme_title())
        self._show_pogodu()
        self._draw_mirror()

    # --- погода ----------------------------------------------------------

    # Что показать вместо настоящей погоды: код по стандарту ВМО,
    # температура и ветер. Ветер решает, метёт снег или падает отвесно.
    # имя, значок, код погоды по стандарту ВМО, градусы, ветер.
    # Код None - настоящий прогноз, "off" - погоды нет вовсе.
    POGODY = [
        ("По прогнозу", "water", None, None, None),
        ("Ясно", "sun", 0, 22, 4),
        ("Пасмурно", "windows", 3, 12, 10),
        ("Дождь", "sliders", 63, 9, 12),
        ("Гроза", "power", 95, 24, 26),
        ("Снег", "moon", 73, -6, 6),
        ("Метель", "sensors", 75, -12, 34),
        ("Туман", "screen", 45, 6, 3),
        ("Мороз", "thermo", 0, -24, 8),
        ("Жара", "brightness", 0, 38, 5),
    ]

    def _pogoda(self, parent, lk):
        """Погоду можно вызвать руками — иначе грозу ждать неделями."""
        self.pogody = L.Segmented(
            parent, lk, [(name, name, icon)
                         for name, icon, _c, _t, _w in self.POGODY],
            value="По прогнозу", command=self._set_pogodu, v_ryadu=5)
        self.pogody.pack(anchor="w")
        for name, _i, code, temp, wind in self.POGODY:
            btn = self.pogody.buttons.get(name)
            if btn is None:
                continue
            self.app.tip.add(btn, "Показывать настоящий прогноз."
                             if code is None else
                             t("Показать «{}» так, будто оно за окном: "
                               "{:+.0f} {}, ветер {:.0f} {}. Прогноз никуда "
                               "не девается.").format(
                                   t(name), edinicy.gradusy(temp),
                                   edinicy.znak(), edinicy.veter(wind),
                                   t(edinicy.znak_vetra())))

        # Погоду можно убрать порознь с дневной и ночной темы.
        galki = ttk.Frame(parent, style="Card.TFrame")
        galki.pack(anchor="w", pady=(8, 0))
        self.pog_vars = {}
        for key, podpis, tip in (
                ("day", "днём", "Показывать дождь, снег, туман и грозу "
                                "на дневной теме."),
                ("night", "ночью", "То же на ночной. Звёзды и метеоры "
                                   "останутся в любом случае.")):
            var = tk.BooleanVar(value=bool(prefs.get("view.weather_" + key,
                                                     True)))
            cb = ttk.Checkbutton(galki, text=t("погода") + " " + t(podpis), variable=var,
                                 style="Card.TCheckbutton",
                                 command=self._set_vidimost)
            cb.pack(side="left", padx=(12, 0))
            self.app.tip.add(cb, tip)
            self.pog_vars[key] = var
        self._set_vidimost()

    def _set_vidimost(self):
        """Показывать ли погоду днём и ночью."""
        for key, flag in (("day", "WEATHER_DAY"), ("night", "WEATHER_NIGHT")):
            on = bool(self.pog_vars[key].get())
            setattr(panel_mod, flag, on)
            prefs.set("view.weather_" + key, on)
        self._mirror = None

    def _set_pogodu(self, value):
        for name, _i, code, temp, wind in self.POGODY:
            if name != value:
                continue
            self.app.sensors.pretend(code, temp, wind)
            self.app.data = self.app.sensors.read()
            self._mirror = None          # доли изменились, собрать заново
            break

    def _show_pogodu(self):
        d = self.app.data
        doli = [(n, float(d.get(k, 0) or 0)) for n, k in (
            ("ясно", "sky_clear"), ("облака", "sky_clouds"),
            ("серость", "sky_grey"), ("дождь", "sky_rain"),
            ("снег", "sky_snow"), ("гроза", "sky_storm"),
            ("туман", "sky_fog"))]
        vidno = ", ".join("{} {:.0f} %".format(t(n), v * 100)
                          for n, v in doli if v > 0.01) or t("ничего")
        self.pogoda_lbl.configure(
            text=t("{}: {}, {:.0f} {}, ветер {:.0f} {}   ·   небо — {}").format(
                t("выдумано") if self.app.sensors.fake else t("за окном"),
                d.get("weather_full", t("нет данных")),
                edinicy.gradusy(float(d.get("weather_temp", 0) or 0)),
                edinicy.znak(),
                edinicy.veter(float(d.get("weather_wind", 0) or 0)),
                t(edinicy.znak_vetra()), vidno))

    # --- зеркало ---------------------------------------------------------

    def _draw_mirror(self):
        """Собрать кадр так же, как он уходит на экран, но без анимации."""
        try:
            cfg = self.app.cfg()
            if self._mirror is None or self._mirror.cfg is not cfg:
                self._mirror = panel_mod.Panel(
                    cfg=cfg, static=True, base_dir=self.app.theme_dir())
                self._mirror.instant = True
            m = self._mirror
            m.static = True
            m.instant = True

            live = self.app.live_panel()
            if live is not None:
                # экран работает - показываем ровно то же, что на нём:
                # ту же долю дня, вплоть до середины перехода
                m.day_mode = live.day_mode
                m._f_now = live._f_now
            else:
                m.day_mode = self.app.day_mode
                m._f_now = None

            img = m.render(self.app.data, 0, 0.0)
            self.look.screen_is_day = (m._f_now or 0) >= 0.5

            # Вписываем кадр в то место, что осталось от окна. Сколько
            # занято нижними блоками - спрашиваем у них самих, а не берём
            # готовым числом: по-английски подписи длиннее, шрифт можно
            # укрупнить, и от жёсткого числа нижняя строка уезжала за край.
            zanyato = 0
            for w in getattr(self, "_nizhnie", ()):
                try:
                    zanyato += w.winfo_reqheight() + 16
                except Exception:
                    zanyato += 90
            zanyato += 96          # заголовок карточки и строчка под кадром
            avail_w = max(320, self.polotno.winfo_width() - 200)
            # Потолок в долях от окна, помимо вычитания занятого: размер
            # кадра влияет на раскладку, а раскладка - обратно на него,
            # и без потолка эти двое сходятся не с первого раза, оставляя
            # нижнюю строку за краем.
            vysota = self.polotno.winfo_height() or 800
            avail_h = max(180, min(vysota - zanyato, int(vysota * 0.46)))
            k = min(avail_w / img.width, avail_h / img.height, 2.0)
            if k < 0.99 or k > 1.01:
                img = img.resize((max(1, int(img.width * k)),
                                  max(1, int(img.height * k))),
                                 Image.LANCZOS if k < 1 else Image.NEAREST)
            box = (img.width, img.height)
            if box != self._last_size:
                self.mirror.configure(width=img.width, height=img.height)
                self._last_size = box
            self.photo = ImageTk.PhotoImage(img)
            self.mirror.delete("all")
            self.mirror.create_image(0, 0, anchor="nw", image=self.photo)
            self.hint.configure(text=self._facts(img))
        except Exception as e:
            self.hint.configure(text=t("не удалось собрать кадр: {}")
                                .format(str(e)[:70]))

    def _facts(self, img):
        cfg = self.app.cfg().get("screen", {})
        bits = ["{}x{}".format(cfg.get("width", 960), cfg.get("height", 480)),
                t("{:g} кадр/с").format(float(cfg.get("fps", 1) or 1))]
        r = self.app.runner
        if self.app.running() and r.sent:
            bits.append(t("отправлено кадров {}").format(r.sent))
            if r.errors:
                bits.append(t("сбоев {}").format(r.errors))
        bits.append(t("кадры фона не листаются, чтобы окно не тратило лишнего"))
        return "   ·   ".join(bits)
