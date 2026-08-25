#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Единая программа: экран, темы, редактор, настройки, датчики.
#  Часть проекта EOne screen.
#
#  Автор: EOne
#  Лицензия: CC BY-NC-SA 4.0 — использование в коммерческих целях
#  запрещено без письменного разрешения автора. См. файл LICENSE.
#
"""
app.py - окно программы.

    python app.py                открыть
    python app.py тема.json      сразу с этой темой

Страницы: Главная, Темы, Редактор, Настройки, Датчики.

Главная нарочно бедная: на ней видно, что уходит на экран, и три
регулятора, которые трогают каждый день. Всё, что настраивают раз
в жизни, живёт в «Настройках» и там расписано подробно.
"""

import json
import os
import sys
import threading
import time

import tkinter as tk
from tkinter import messagebox, ttk

import editor as editor_mod
import home as home_mod
import look as look_mod
import pages as pages_mod
import panel as panel_mod
import prefs
import sensors as sensors_mod
import sistema
import themes as themes_mod
import yazyk
from yazyk import t

AUTHOR = "EOne"
PROJECT = "EOne screen"
# Версия у программы одна и лежит в panel.py: её показывает и окно,
# и консоль. Второй, своей, здесь больше нет - две расходились.
VERSION = panel_mod.VERSION

# Что написано в полосе заголовка окна. Имя программы стоит в шапке,
# рядом с капелькой, и повторять его сверху незачем - там полезнее
# сказать, для чего программа.
ZAGOLOVOK = "Water-Cooler Screen"

# Имя контроллера экрана, к которому программа умеет обращаться.
# В названии программы его нет: оно про то, чем программа занимается,
# а не про то, к чему подключается.
KONTROLLER = "TXW818"

# Разделы наверху. Их намеренно три: редактор живёт внутри «Тем»,
# а датчики внутри «Настроек» - туда заходят из своего же раздела,
# а не ищут в общем ряду.
PAGES = [
    ("home", "Главная", "home"),
    ("themes", "Темы", "grid"),
    ("settings", "Настройки", "settings"),
]

# какой раздел подсвечивать наверху для страниц, которых в ряду нет
UNDER = {"editor": "themes"}


def _s_bolshoy(s):
    """Первую букву заглавной, остальные не трогать.

    Обычный capitalize() опускает всё остальное, и «как в Windows»
    превращается в «Как в windows».
    """
    return s[:1].upper() + s[1:]


class App:
    def __init__(self, root, start_theme=None):
        self.root = root
        root.title(ZAGOLOVOK)
        self._place_window(root)

        yazyk.vybrat(prefs.get("ui.lang", "ru"))
        # погоду можно было выключить в прошлый раз - помним это
        panel_mod.WEATHER_DAY = bool(prefs.get("view.weather_day", True))
        panel_mod.WEATHER_NIGHT = bool(prefs.get("view.weather_night", True))
        self.look = look_mod.Look(root, prefs.get("ui.theme", "system"))
        self.tip = look_mod.Tip(root, self.look)
        self.sensors = sensors_mod.Sensors()
        self.runner = None
        self.data = {}
        self.icon = None
        self._tray_title = None
        self.day_mode = "auto"
        self.path = start_theme or self._guess_theme()

        self._build()
        self._start_tray()
        self._tick()

        if prefs.get("start.minimized"):
            self.root.after(400, self.hide_window)
        if prefs.get("start.screen_on"):
            self.root.after(600, self.toggle_screen)
        # При первом запуске сразу показываем осмотр машины. Отдельным
        # обрядом перед делом его никто не делает, а потом удивляется
        # прочеркам вместо температуры. Свёрнутому в трей не мешаем.
        if not prefs.get("start.osmotr_byl") and not prefs.get("start.minimized"):
            self.root.after(900, self._pervyy_osmotr)

    def _pervyy_osmotr(self):
        """Открыть осмотр машины и запустить его. Один раз за жизнь."""
        prefs.set("start.osmotr_byl", True)
        try:
            self.show_page("settings")
            page = self.pages["settings"]
            page.side.set("osmotr")
            page.show_section("osmotr")
            page.after(300, page._osmotr_pusk)
        except Exception:
            pass

    def _place_window(self, root):
        """Размер окна по экрану, но с памятью о прошлом запуске.

        На большом мониторе жёсткие 1690 точек смотрятся огрызком, на
        маленьком - не влезают. Поэтому берём долю от рабочего стола,
        а если человек окно двигал или тянул, в следующий раз открываем
        как он оставил.
        """
        root.minsize(1080, 680)
        saved = prefs.get("ui.geometry", "")
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        if saved:
            try:
                w, h = (int(v) for v in saved.split("+")[0].split("x"))
                if 900 <= w <= sw and 600 <= h <= sh:
                    root.geometry(saved)
                    return
            except Exception:
                pass
        w = max(1180, min(int(sw * 0.82), sw - 80))
        h = max(760, min(int(sh * 0.86), sh - 90))
        root.geometry("{}x{}+{}+{}".format(w, h, (sw - w) // 2,
                                           max(0, (sh - h) // 2 - 20)))

    def _remember_window(self):
        """Запомнить, каким человек оставил окно."""
        try:
            if self.root.state() == "normal":
                prefs.set("ui.geometry", self.root.winfo_geometry())
        except Exception:
            pass

    def _guess_theme(self):
        """Что открыть при запуске.

        Если тем нет вовсе - заводим первую. Иначе окну нечего показывать,
        и оно не открывается совсем.
        """
        last = prefs.get("start.last_theme", "")
        if last and os.path.exists(last):
            return last
        if os.path.exists("layout.json"):
            return "layout.json"
        found = themes_mod.find(".")
        if found:
            return found[0]
        return themes_mod.create(".", "Моя тема", prefs.get("ui.author", ""))

    # --- каркас ---------------------------------------------------------

    def _build(self):
        lk = self.look

        bar = ttk.Frame(self.root, padding=(20, 14, 20, 10))
        bar.pack(fill="x")
        brand = ttk.Frame(bar)
        brand.pack(side="left")
        look_mod.icon_label(brand, lk, "water", 17, "Accent.TLabel").pack(
            side="left", padx=(0, 8))
        ttk.Label(brand, text=PROJECT, style="Title.TLabel").pack(
            side="left")

        self.nav = look_mod.Segmented(
            bar, lk, [(key, label, icon) for key, label, icon in PAGES],
            value="home", command=self.show_page, on_card=False,
            krupno=True)
        self.nav.pack(side="left", padx=24)

        self.head_state = ttk.Label(bar, text="", style="Dim.TLabel")
        self.head_state.pack(side="right")

        self.holder = ttk.Frame(self.root)
        self.holder.pack(fill="both", expand=True)

        # Редактор поднимаем первым: он держит открытую тему, а остальные
        # страницы спрашивают её у него.
        self.pages = {}
        edit_page = ttk.Frame(self.holder)
        self.pages["editor"] = edit_page
        self.editor = editor_mod.Editor(
            edit_page, self.path, toplevel=self.root, look=lk,
            sensors=self.sensors, on_change=self._editor_changed)
        self.editor.app_ref = self
        # свойства строились до того, как редактор узнал про окно,
        # поэтому подсказки к полям вешаем вторым заходом
        self.editor._refresh_props()

        self.pages["home"] = home_mod.Home(self.holder, lk, self)
        self.pages["themes"] = pages_mod.ThemesPage(self.holder, lk, self)
        self.pages["settings"] = pages_mod.SettingsPage(self.holder, lk, self)

        self.current = None
        self.show_page("home")

    def smenit_yazyk(self, code):
        """Сменить язык окна прямо сейчас, без перезапуска.

        Пересобираем окно, а не переводим надписи на месте: почти весь
        текст задаётся при создании виджета, а обратного перевода
        (с английского на русский) у нас нет и заводить его незачем.

        Процесс при этом остаётся тот же - и это важнее, чем кажется:
        собранная программа просит права администратора при запуске,
        и перезапуск заставил бы Windows спросить их заново. Вывод
        на экран водянки тоже не прерывается: он живёт в своём потоке
        и про окно ничего не знает.
        """
        if code == prefs.get("ui.lang", yazyk.RU):
            return
        prefs.set("ui.lang", code)
        yazyk.vybrat(code)

        # Несохранённые правки темы пережили бы пересборку только
        # на диске - спрашиваем, как с ними быть.
        if getattr(self, "editor", None) is not None and self.editor.dirty:
            otvet = messagebox.askyesnocancel(
                t("Смена языка"),
                t("В теме есть несохранённые правки. Сохранить их?"))
            if otvet is None:
                return
            if otvet:
                self.editor.save()

        bylo = self.current if self.current != "editor" else "themes"
        self._remember_window()
        for w in list(self.root.winfo_children()):
            w.destroy()
        self.tip = look_mod.Tip(self.root, self.look)
        self._build()
        self.show_page(bylo)
        # Меню значка рисует pystray, а не Tk: наш крючок перевода
        # до него не достаёт, поэтому значок заводим заново.
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:
                pass
            self.icon = None
            self._start_tray()

    def show_page(self, key):
        if key == self.current:
            return
        for name, page in self.pages.items():
            if name != key:
                page.pack_forget()
                if hasattr(page, "hide"):
                    page.hide()
        page = self.pages.get(key)
        if page is None:
            return
        page.pack(fill="both", expand=True)
        self.current = key
        self.nav.set(UNDER.get(key, key))
        self.editor.active = (key == "editor")
        if key == "editor":
            self.editor._render()
        if hasattr(page, "show"):
            page.show()

    # --- то, чем пользуются страницы -------------------------------------

    def cfg(self):
        return self.editor.cfg

    def theme_dir(self):
        return os.path.dirname(os.path.abspath(self.editor.path))

    def theme_title(self):
        """Как называется открытая тема. Считаем так же, как витрина."""
        try:
            return themes_mod.info(self.editor.path)["name"]
        except Exception:
            meta = (self.cfg().get("meta") or {}).get("name")
            return meta or os.path.splitext(
                os.path.basename(self.editor.path))[0]

    def running(self):
        return bool(self.runner and not self.runner.stop.is_set())

    def live_panel(self):
        """Панель, которая прямо сейчас рисует на экран. None - выключен."""
        return getattr(self.runner, "panel", None) if self.running() else None

    def hidden(self):
        try:
            return self.root.state() in ("withdrawn", "iconic")
        except Exception:
            return False

    # --- управление экраном ----------------------------------------------

    def toggle_screen(self):
        """Включить или выключить вывод.

        Настройку «сразу включать экран» здесь НЕ трогаем: она про то,
        чего человек хочет при запуске, а не про то, что он нажал сейчас.
        Иначе галочка в настройках переставлялась бы сама собой.
        """
        if self.running():
            self.runner.stop.set()
            self.runner = None
            return
        self._start_screen()

    def toggle_pause(self):
        if self.running():
            self.runner.paused = not self.runner.paused

    def restart_screen(self):
        """Перезапустить вывод: заново открыть порт и поздороваться с экраном.

        Выручает, когда экран сбился или порт подвис: пересоздавать
        программу целиком ради этого незачем.
        """
        was = self.running()
        if was:
            self.runner.stop.set()
            self.runner = None
            self.head_state.config(text="перезапускаю экран…")
            self.root.after(900, self._start_screen)
        else:
            self._start_screen()

    def _start_screen(self):
        self.runner = panel_mod.Runner(self.editor.path, cfg=self.cfg(),
                                       base_dir=self.theme_dir(),
                                       sensors=self.sensors)
        self.runner.forced_mode = self.day_mode
        self.runner.start()
        self.runner.set_brightness(int(self.pages["home"].bright.get()))

    def set_day_mode(self, mode):
        self.day_mode = mode
        self.cfg().setdefault("screen", {})["day_mode"] = mode
        if self.running():
            self.runner.set_day_mode(mode)
        if hasattr(self.editor, "sync_day_mode"):
            self.editor.sync_day_mode(mode)
        # Длительность перехода панель читает из описания сама, подсказывать
        # ей не надо — просто покажем, сколько это.
        if self.live_panel() is not None:
            self.head_state.config(text=t("переход {:.0f} с").format(
                panel_mod.transition_minutes(self.cfg()) * 60.0))

    def set_brightness(self, value):
        self.cfg().setdefault("screen", {})["brightness"] = int(value)
        if self.running():
            self.runner.set_brightness(value)

    def push_theme(self):
        """Отправить правки темы на работающий экран."""
        if self.running() and self.runner.apply_cfg(self.cfg(), self.theme_dir()):
            self.head_state.config(text="тема отправлена на экран")

    def load_theme(self, path):
        if self.editor.dirty and not messagebox.askyesno(
                "Темы", "Несохранённые правки пропадут. Продолжить?"):
            return False
        try:
            with open(path, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            messagebox.showerror("Темы", str(e))
            return False
        if "layers" not in cfg:
            messagebox.showwarning("Темы", "Это не похоже на тему: нет слоёв.")
            return False
        self.editor.adopt(path, cfg)
        panel_mod._PREPARED.clear()
        self.pages["home"]._mirror = None
        prefs.set("start.last_theme", os.path.abspath(path))
        self.push_theme()
        self.show_page("home")
        return True

    # --- обновление -------------------------------------------------------

    def _editor_changed(self, title, dirty):
        self.root.title("{} — {}".format(ZAGOLOVOK, title))
        self.pages["home"]._mirror = None      # тема изменилась, собрать заново

    def _tick(self):
        try:
            self.data = self.sensors.read()
            self.look.recheck()
            page = self.pages.get(self.current)
            if page is not None and hasattr(page, "tick") and not self.hidden():
                page.tick()
            if not self.hidden():
                self._head()
        except Exception as e:
            try:
                self.head_state.config(text=t("сбой обновления: {}")
                                       .format(str(e)[:60]))
            except Exception:
                pass
        if self.icon is not None and self._tray_title:
            try:
                self.icon.title = self._tray_title()
            except Exception:
                pass
        self.root.after(1000, self._tick)

    def _head(self):
        if self.running():
            r = self.runner
            self.head_state.config(
                text=t("экран: {} · {:.0f} кадр/с").format(t(r.status),
                                                          r.fps_real))
        else:
            self.head_state.config(text=t("экран выключен"))

    # --- значок возле часов ----------------------------------------------

    def _start_tray(self):
        # На Linux надо сперва выбрать, на чём значок рисовать: pystray
        # смотрит на PYSTRAY_BACKEND только при загрузке. Сам он идёт
        # по порядку appindicator - gtk - xorg, а нам надо перескочить
        # через gtk: его значок на Wayland просто не показывается.
        nazvali = sistema.podgotovit_trey()
        try:
            import pystray
        except ImportError:
            # Назвали подложку, а она не встала. Отступаем к его
            # собственному выбору: значок с переведённым заголовком
            # лучше, чем никакого.
            if not sistema.otstupit_s_treya(nazvali):
                self.icon = None
                return
            try:
                import pystray
            except ImportError:
                self.icon = None
                return
        # Что у него вышло на самом деле - от этого зависит, выдержит ли
        # заголовок русские буквы.
        podlozhka = sistema.podlozhka_treya(pystray)

        def title(_=None):
            if self.running():
                gotovo = t("{} — {} ({:.1f} кадр/с, {})").format(
                    PROJECT, t(self.runner.status), self.runner.fps_real,
                    t(panel_mod.DAY_MODE_NAMES.get(self.day_mode, "")))
            else:
                gotovo = t("{} — экран выключен").format(PROJECT)
            return sistema.bezopasnyy_zagolovok(gotovo, podlozhka)

        self._tray_title = title

        def later(fn):
            return lambda icon=None, item=None: self.root.after(0, fn)

        def set_mode(m):
            def do(icon, item):
                self.root.after(0, lambda: (self.set_day_mode(m),
                                            self.pages["home"].modes.set(m)))
                icon.update_menu()
            return do

        def quit_all(icon, item):
            icon.visible = False
            self.root.after(0, self.close)

        # Крючок перевода в look.py ловит только надписи tkinter, а меню
        # значка рисует pystray - здесь переводим руками.
        menu = pystray.Menu(
            pystray.MenuItem(title, later(self.show_window), default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("Включить или выключить экран"),
                             later(self.toggle_screen)),
            pystray.MenuItem(t("Пауза"), later(self.toggle_pause),
                             checked=lambda i: bool(self.runner
                                                    and self.runner.paused)),
            pystray.Menu.SEPARATOR,
            *[pystray.MenuItem(_s_bolshoy(t(panel_mod.DAY_MODE_NAMES[m])),
                               set_mode(m),
                               checked=lambda i, m=m: self.day_mode == m,
                               radio=True) for m in panel_mod.DAY_MODES],
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("Показать окно"), later(self.show_window)),
            pystray.MenuItem(t("Выход"), quit_all),
        )
        # Значок - удобство, а не условие работы. Раньше его беда роняла
        # весь запуск: ни окна, ни экрана. Теперь беду показываем
        # и живём дальше без значка - окно закрывается крестиком.
        def krutit():
            try:
                self.icon.run()
            except Exception as e:
                self.icon = None
                print("значок возле часов отвалился: {}".format(e))

        try:
            self.icon = pystray.Icon("eone_screen", panel_mod.make_icon(),
                                     title(), menu)
        except Exception as e:
            self.icon = None
            print("значок возле часов не завёлся: {}".format(e))
            return
        threading.Thread(target=krutit, daemon=True).start()

    def hide_window(self):
        if self.icon is None:
            self.root.iconify()
            return
        self.root.withdraw()

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        try:
            self.root.focus_force()
        except Exception:
            pass

    def on_x(self):
        if self.icon is not None and prefs.get("start.close_to_tray", True):
            self.hide_window()
        else:
            self.close()

    def close(self):
        self._remember_window()
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:
                pass
        if self.runner:
            self.runner.stop.set()
            time.sleep(0.3)
        self.editor.stream_stop.set()
        self.sensors.stop()
        if self.editor.dirty and messagebox.askyesno("Выход", "Сохранить правки?"):
            self.editor.save()
        prefs.save()
        self.root.destroy()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = tk.Tk()
    app = App(root, args[0] if args else None)
    root.protocol("WM_DELETE_WINDOW", app.on_x)
    root.mainloop()


if __name__ == "__main__":
    main()
