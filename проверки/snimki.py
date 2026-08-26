#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Снимки для README: окно и кадры панели.

Снимки в репозитории быстро отстают от программы, а человек по ним
судит, что она умеет. Поэтому не делаем их руками: скрипт поднимает
настоящее окно, проходит по разделам и снимает каждый, а кадры панели
рисует движком.

Окно снимается ПО-АНГЛИЙСКИ: снимки одни на оба README, и английский
здесь общий знаменатель. Настоящие настройки не трогаются - язык
возвращается на место, что бы ни случилось.

    python проверки/snimki.py            в snimki/ рядом с программой
    python проверки/snimki.py --kuda X   в другую папку
"""

import ctypes
import os
import sys
import time
from ctypes import wintypes

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)
sys.path.insert(0, BASE)

KUDA = os.path.join(BASE, "snimki")
if "--kuda" in sys.argv:
    KUDA = sys.argv[sys.argv.index("--kuda") + 1]
os.makedirs(KUDA, exist_ok=True)

import tkinter as tk                                        # noqa: E402
from PIL import Image, ImageGrab                            # noqa: E402

import app as app_mod                                       # noqa: E402
import panel as panel_mod                                   # noqa: E402
import prefs                                                # noqa: E402
import sensors as sensors_mod                               # noqa: E402
import yazyk                                                # noqa: E402

# Окно ставим одного размера всегда: иначе снимки разной ширины,
# и в README они прыгают.
SHIRINA, VYSOTA = 1340, 820

# Снимки уходят в открытый репозиторий, поэтому на них не должно быть
# ничего про хозяина машины. Своё железо узнаётся по названию, а город
# с координатами и временем восхода - это уже адрес. Подставляем
# выдуманное: большой город и другое, но правдоподобное железо.
DEMO_PROCESSOR = "AMD Ryzen 7 7800X3D"
DEMO_VIDEOKARTA = "NVIDIA GeForce RTX 4070 Ti"
DEMO_GOROD = {"city": "Saint Petersburg", "latitude": 59.9386,
              "longitude": 30.3141, "update_minutes": 15, "language": "en"}
# Отдельный файл рядом с программой: настоящий weather.json не трогаем
DEMO_POGODA_FAYL = "snimki-pogoda.json"


def podstavit_demo():
    """Подменить всё, что выдаёт хозяина машины. Возвращает уборщика."""
    import json

    import papka
    bylo_fayl = sensors_mod.WEATHER_CONF
    bylo_imena = dict(sensors_mod._names)
    put = os.path.join(papka.programma(), DEMO_POGODA_FAYL)
    with open(put, "w", encoding="utf-8") as f:
        json.dump(DEMO_GOROD, f, ensure_ascii=False, indent=2)
    sensors_mod.WEATHER_CONF = DEMO_POGODA_FAYL
    sensors_mod._names["cpu"] = DEMO_PROCESSOR
    sensors_mod._names["gpu"] = DEMO_VIDEOKARTA

    def ubrat():
        sensors_mod.WEATHER_CONF = bylo_fayl
        sensors_mod._names.clear()
        sensors_mod._names.update(bylo_imena)
        try:
            os.remove(put)
        except OSError:
            pass

    return ubrat


def zhdat(root, sekund):
    """Дать окну дорисоваться, не замораживая его."""
    konec = time.time() + sekund
    while time.time() < konec:
        root.update()
        time.sleep(0.03)


def _hwnd_okna(root):
    """Настоящее окно Windows, а не внутреннее окошко Tk."""
    hwnd = root.winfo_id()
    roditel = ctypes.windll.user32.GetParent(hwnd)
    return roditel or hwnd


def _sam_sebya(root):
    """Попросить окно нарисовать себя в память.

    Снимать область экрана нельзя: если человек в это время работает,
    в кадр попадёт его рабочий стол и чужие окна поверх. PrintWindow
    берёт у окна его собственную картинку, что бы ни лежало сверху.
    """
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    hwnd = _hwnd_okna(root)
    ramka = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(ramka))
    w, h = ramka.right - ramka.left, ramka.bottom - ramka.top
    if w <= 0 or h <= 0:
        return None

    okno_dc = user32.GetWindowDC(hwnd)
    nash_dc = gdi32.CreateCompatibleDC(okno_dc)
    kartinka = gdi32.CreateCompatibleBitmap(okno_dc, w, h)
    byla = gdi32.SelectObject(nash_dc, kartinka)
    # 2 - PW_RENDERFULLCONTENT: без него окна со слоями выходят пустыми
    vyshlo = user32.PrintWindow(hwnd, nash_dc, 2)
    if not vyshlo:
        vyshlo = user32.PrintWindow(hwnd, nash_dc, 0)
    # Отцепить картинку от контекста ОБЯЗАТЕЛЬНО до чтения точек:
    # пока она выбрана, GetDIBits отдаёт чёрное поле.
    gdi32.SelectObject(nash_dc, byla)

    class ZAGOLOVOK(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                    ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD),
                    ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD),
                    ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG),
                    ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)]

    zag = ZAGOLOVOK()
    zag.biSize = ctypes.sizeof(ZAGOLOVOK)
    zag.biWidth, zag.biHeight = w, -h        # минус - строки сверху вниз
    zag.biPlanes, zag.biBitCount = 1, 32
    baytov = w * h * 4
    bufer = ctypes.create_string_buffer(baytov)
    gdi32.GetDIBits(nash_dc, kartinka, 0, h, bufer, ctypes.byref(zag), 0)

    gdi32.DeleteObject(kartinka)
    gdi32.DeleteDC(nash_dc)
    user32.ReleaseDC(hwnd, okno_dc)
    if not vyshlo:
        return None
    return Image.frombuffer("RGB", (w, h), bufer, "raw", "BGRX", 0, 1)


def _pusto(kadr):
    """Кадр одноцветный - значит ничего не сняли."""
    ottenki = kadr.convert("L").getcolors(400000)
    return not ottenki or len(ottenki) < 8


def _s_ekrana(root):
    """Снять область экрана по рамке, которую называет сама Windows.

    winfo_rootx у Tk бывает несвежим сразу после переключения страницы,
    и кадр уезжал мимо окна. GetWindowRect отвечает про то окно,
    которое видно прямо сейчас.
    """
    ramka = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(_hwnd_okna(root), ctypes.byref(ramka))
    return ImageGrab.grab(bbox=(ramka.left, ramka.top,
                                ramka.right, ramka.bottom),
                          all_screens=True)


def snyat(root, imya):
    """Снять окно целиком, вместе с рамкой."""
    zhdat(root, 0.9)
    kadr = _sam_sebya(root)
    if kadr is None or _pusto(kadr):
        # Tk не отвечает на просьбу нарисовать себя, и PrintWindow отдаёт
        # чёрное поле. Тогда снимаем с экрана - для этого окно и держим
        # поверх всех.
        kadr = _s_ekrana(root)
        if _pusto(kadr):                     # не успело дорисоваться
            zhdat(root, 1.5)
            kadr = _s_ekrana(root)
    put = os.path.join(KUDA, imya + ".png")
    kadr.save(put)
    print("  {:24s} {}x{}{}".format(imya, kadr.size[0], kadr.size[1],
                                    "   ПУСТО" if _pusto(kadr) else ""))
    return put


def okno():
    """Снимки живого окна."""
    # Что временно меняем в настройках и обязаны вернуть.
    #   minimized  - иначе программа прячется в трей через 400 мс,
    #                и снимался бы пустой рабочий стол;
    #   screen_on  - иначе снимки включали бы настоящий экран водянки.
    bylo = {k: prefs.get(k) for k in ("ui.lang", "start.minimized",
                                      "start.screen_on")}
    root = tk.Tk()
    try:
        prefs.set("ui.lang", yazyk.EN)
        prefs.set("start.minimized", False)
        prefs.set("start.screen_on", False)
        a = app_mod.App(root)
        # Размер задаём ПОСЛЕ App: он восстанавливает своё прошлое окно,
        # и снимки выходили бы каждый раз разной величины.
        root.geometry("{}x{}+80+60".format(SHIRINA, VYSOTA))
        # Программа могла успеть спрятаться сама - показываем обратно
        a.show_window()
        root.deiconify()
        root.update_idletasks()
        root.lift()
        # Поверх всех: снимаем область экрана, и чужое окно сверху
        # попало бы в кадр.
        root.attributes("-topmost", True)
        zhdat(root, 3.5)

        a.show_page("home")
        a.set_day_mode("night")
        snyat(root, "home-night")
        a.set_day_mode("day")
        snyat(root, "home-day")
        a.set_day_mode("auto")

        a.show_page("themes")
        zhdat(root, 1.2)
        snyat(root, "themes")

        a.show_page("settings")
        nastroyki = a.pages["settings"]
        for razdel, imya in (("units", "units"),
                             ("weather", "weather-settings"),
                             ("look", "look")):
            nastroyki.show_section(razdel)
            zhdat(root, 0.8)
            snyat(root, imya)

        # Осмотр машины: он сам опрашивает железо, это несколько секунд
        nastroyki.show_section("osmotr")
        zhdat(root, 0.6)
        try:
            nastroyki._osmotr_pusk()
        except Exception as e:
            print("  осмотр не запустился:", e)
        zhdat(root, 12.0)
        snyat(root, "checkup")

        a.show_page("editor")
        zhdat(root, 2.0)
        snyat(root, "editor")
    finally:
        # Возвращаем настройки, что бы ни случилось: это настоящий
        # settings.json человека, а не наша песочница.
        for klyuch, znachenie in bylo.items():
            prefs.set(klyuch, znachenie)
        try:
            root.destroy()
        except Exception:
            pass


def panel():
    """Кадры самой панели: их рисуем движком, а не снимаем с экрана."""
    tema = os.path.join("themes", "Skywatch", "tema.json")
    p = panel_mod.Panel(tema)
    p.instant = True
    p.day_mode = "auto"
    s = sensors_mod.Sensors()
    time.sleep(8)
    bylo_tema = prefs.get("ui.theme_lang", yazyk.KAK_V_OKNE)
    yazyk.vybrat_temu(yazyk.EN)
    for imya, kod, dolya, temp in (("weather-rain", 63, 0.0, 12.0),
                                   ("weather-blizzard", 75, 0.0, -14.0),
                                   ("weather-storm", 95, 0.0, 17.0),
                                   ("panel-day", 2, 1.0, 21.0)):
        s.pretend(code=kod)
        d = dict(s.read())
        d["day_factor"] = float(dolya)
        d["is_day"] = dolya >= 0.5
        d["weather_temp"] = temp
        p._f_now = None
        put = os.path.join(KUDA, imya + ".png")
        p.render(d, 0).save(put)
        print("  {:24s} 960x480".format(imya))
    s.pretend(None)
    yazyk.vybrat_temu(bylo_tema)
    s.stop()


if __name__ == "__main__":
    ubrat = podstavit_demo()
    print("вместо настоящего подставлено: {} · {} · {}".format(
        DEMO_PROCESSOR, DEMO_VIDEOKARTA, DEMO_GOROD["city"]))
    try:
        print("\nкадры панели:")
        panel()
        print("\nокно (не трогай мышь, пока идёт):")
        okno()
    finally:
        ubrat()
    print("\nготово, снимки в: {}".format(KUDA))
