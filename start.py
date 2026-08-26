#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Осмотр машины перед первым запуском.
#  Часть проекта EOne screen — открытой замены штатной программе
#  для экранов на контроллере TXW818.
#
#  Автор: EOne
#  Лицензия: CC BY-NC-SA 4.0 — использование в коммерческих целях
#  запрещено без письменного разрешения автора. См. файл LICENSE.
#
"""start.py - осмотр машины и подготовка к работе.

Запускать через start.bat: он поднимает права администратора (без них
температуру процессора не прочитать в принципе) и снимает с файлов
пометку «скачано из интернета», из-за которой Windows не даёт
загрузить библиотеку датчиков.

    start.bat                  обычный путь
    python start.py            то же самое, но без прав и разблокировки
    python start.py --tiho     ничего не спрашивать, только осмотреть

Что делает:
  * выбирает язык окна по языку Windows, если он ещё не выбран;
  * проверяет, что установлены нужные библиотеки, и говорит, чем ставить;
  * находит процессор и видеокарту и называет их по имени;
  * смотрит, какие датчики отвечают на самом деле, а не по бумаге;
  * ищет экран на COM-порту;
  * проверяет интернет и источник погоды;
  * записывает найденное в settings.json, чтобы программа не искала
    это заново при каждом запуске;
  * предлагает подставить в тему настоящие названия железа вместо
    вписанных руками.

Ничего не ломает: всё, что меняется, либо записывается в настройки
программы, либо делается только с согласия человека.
"""

import importlib.util
import json
import os
import sys
import time
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)
sys.path.insert(0, BASE)

IS_WINDOWS = sys.platform.startswith("win")
TIHO = "--tiho" in sys.argv or "--quiet" in sys.argv

import osmotr
import yazyk
from yazyk import t

# Четыре файла из архива LibreHardwareMonitor - ровно столько нужно,
# чтобы найти все датчики. Проверено перебором: с ними находится
# столько же датчиков, сколько со всеми двадцатью пятью.
DLL_NUZHNY = ("LibreHardwareMonitorLib.dll", "HidSharp.dll",
              "System.Memory.dll",
              "System.Runtime.CompilerServices.Unsafe.dll")

# Пятый файл нужен только тем, у кого видеокарта не Nvidia: без него
# библиотека не открывает раздел видеокарт. Тем, у кого Nvidia,
# показания и так идут из nvidia-smi, и файл не нужен.
DLL_DLYA_GPU = "System.Numerics.Vectors.dll"

# Что нужно программе. Обязательное - без него она не поднимется вовсе.
BIBLIOTEKI = [
    ("PIL", "Pillow", "сборка кадров и всё рисование", True),
    ("psutil", "psutil", "загрузка процессора, память, диски, сеть", True),
    ("serial", "pyserial", "разговор с экраном по COM-порту", True),
    ("tkinter", "", "само окно программы", True),
    ("clr", "pythonnet", "температура процессора, видеокарты AMD и Intel",
     False),
    ("numpy", "numpy", "переходы цвета и мягкие края", False),
    ("pystray", "pystray", "значок рядом с часами", False),
]

# Слова, по которым видно, что в теме название железа вписано руками
SLEDY_ZHELEZA = (
    ("gpu", ("nvidia", "geforce", "rtx ", "gtx ", "radeon", "rx ", "arc ")),
    ("cpu", ("ryzen", "threadripper", "core i", "core ultra", "xeon",
             "athlon", "pentium", "celeron")),
)

bedy = []          # (важно ли, что случилось, что делать)


# --- разговор с человеком ---------------------------------------------------

def zagolovok(text):
    print("")
    print("=== {} ===".format(t(text)))


def stroka(znak, chto, pojasnenie=""):
    print("  {:<3} {:<34} {}".format(znak, t(chto), t(pojasnenie)))


def horosho(chto, note=""):
    stroka("+", chto, note)


def ploho(chto, note="", vazhno=True, chinit=""):
    stroka("-" if vazhno else "!", chto, note)
    bedy.append((vazhno, t(chto) + (": " + t(note) if note else ""), t(chinit)))


def prosto(text=""):
    print("  " + t(text) if text else "")


def pokazat(nahodki):
    """Напечатать находки осмотра. Сами проверки лежат в osmotr.py."""
    for n in nahodki:
        if n.horosho is None:
            prosto(n.chto)
        elif n.horosho:
            horosho(n.chto, n.pojasnenie)
        else:
            ploho(n.chto, n.pojasnenie, n.vazhno, n.chinit)


def sprosit(vopros):
    """Да или нет. В тихом режиме всегда нет: молча ничего не меняем."""
    if TIHO:
        return False
    try:
        otvet = input("  " + t(vopros) + " " + t("[д/н] ")).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return otvet[:1] in ("д", "y", "1")


# --- язык -------------------------------------------------------------------

def yazyk_sistemy():
    """Какой язык окна подходит этой Windows.

    Русская система - русское окно, любая другая - английское.
    Спрашиваем именно язык оболочки, а не раскладку клавиатуры.
    """
    if IS_WINDOWS:
        try:
            import ctypes
            # младшие десять разрядов - сам язык, старшие - его вариант
            lang = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3ff
            if lang:
                return yazyk.RU if lang == 0x19 else yazyk.EN
        except Exception:
            pass
    code = ""
    try:
        import locale
        code = (locale.getdefaultlocale()[0] or "")
    except Exception:
        try:
            code = os.environ.get("LANG", "")
        except Exception:
            code = ""
    return yazyk.RU if code.lower().startswith("ru") else yazyk.EN


def vybrat_yazyk(prefs):
    """Выбрать язык окна, если его ещё никто не выбирал."""
    zagolovok("Язык")
    bylo = prefs.get("ui.lang")
    nado = yazyk_sistemy()
    if bylo:
        yazyk.vybrat(bylo)
        horosho("язык уже выбран", bylo)
        if bylo != nado:
            prosto(t("язык Windows подсказывал другой: {}").format(nado))
        return bylo
    yazyk.vybrat(nado)
    prefs.set("ui.lang", nado)
    horosho("язык выбран по языку Windows", nado)
    prosto("поменять можно в Настройках -> Оформление программы")
    return nado


# --- библиотеки -------------------------------------------------------------


# --- права и заблокированные файлы ------------------------------------------



# --- железо -----------------------------------------------------------------


# --- датчики ----------------------------------------------------------------

# Что показывает панель и откуда это берётся
VAZHNYE = [
    ("cpu_load", "загрузка процессора"),
    ("cpu_temp", "температура процессора"),
    ("cpu_ghz", "частота процессора"),
    ("ram_load", "загрузка памяти"),
    ("disk_load", "загрузка диска"),
    ("net_down_mbs", "приём из сети"),
    ("gpu_load", "загрузка видеокарты"),
    ("gpu_temp", "температура видеокарты"),
    ("gpu_mem_used_gb", "занято видеопамяти"),
    ("gpu_power_w", "потребление видеокарты"),
]

# Про эти показания ниже говорится отдельно: там видно не только «нет»,
# но и почему нет. В общий список бед их писать не надо.
OTDELNO = {"cpu_temp", "gpu_load", "gpu_temp", "gpu_mem_used_gb",
           "gpu_power_w"}



# --- экран ------------------------------------------------------------------


# --- погода -----------------------------------------------------------------


# --- темы -------------------------------------------------------------------

def nayti_zhelezo_v_teme(cfg):
    """Слои, в которых название железа вписано руками.

    Возвращает список (слой, что это - cpu или gpu).
    """
    nashli = []
    for layer in cfg.get("layers", []):
        if layer.get("type") != "text":
            continue
        text = str(layer.get("text", ""))
        if "{" in text:
            continue                    # там уже подстановка, трогать нечего
        low = text.lower()
        for chto, slova in SLEDY_ZHELEZA:
            if any(w in low for w in slova):
                nashli.append((layer, chto))
                break
    return nashli


def podstavit_v_temy(zhelezo):
    """Заменить вписанные руками названия железа на подстановку."""
    zagolovok("Темы")
    try:
        import themes as themes_mod
    except Exception as e:
        ploho("не смог просмотреть темы", str(e)[:60], False)
        return
    najdeno = []
    for put in themes_mod.find("."):
        if not put or not os.path.exists(put):
            continue
        try:
            with open(put, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            continue
        sloi = nayti_zhelezo_v_teme(cfg)
        if sloi:
            najdeno.append((put, cfg, sloi))

    if not najdeno:
        horosho("названия железа нигде не вписаны руками")
        return

    for put, cfg, sloi in najdeno:
        imya_temy = os.path.basename(os.path.dirname(put))
        prosto(t("«{}»: {} слоёв с вписанным названием").format(
            imya_temy, len(sloi)))
        for layer, chto in sloi:
            nado = "{cpu_name}" if chto == "cpu" else "{gpu_name}"
            teper = zhelezo.get(chto) or ""
            prosto("   «{}»  ->  {}  ({})".format(
                layer.get("text"), nado, teper or "?"))
        if not sprosit("Заменить, чтобы тема сама называла ваше железо?"):
            prosto("оставил как было")
            continue
        for layer, chto in sloi:
            layer["text"] = "{cpu_name}" if chto == "cpu" else "{gpu_name}"
        try:
            with open(put, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            horosho("тема поправлена", imya_temy)
        except Exception as e:
            ploho("не смог записать тему", str(e)[:60], True)


# --- запись найденного ------------------------------------------------------

def zapisat(prefs, zhelezo, s, est):
    """Сложить найденное в настройки, чтобы программа не искала заново."""
    zagolovok("Записываю в настройки")
    prefs.set("hardware.cpu", zhelezo.get("cpu", ""))
    prefs.set("hardware.gpu", zhelezo.get("gpu", ""))
    prefs.set("hardware.gpu_vendor", zhelezo.get("gpu_vendor", ""))
    prefs.set("hardware.disk", zhelezo.get("disk", ""))
    prefs.set("hardware.checked", datetime.now().strftime("%Y-%m-%d %H:%M"))
    horosho("железо записано")

    # nvidia-smi нужен только для Nvidia. У AMD и Intel показания идут
    # через ту же библиотеку, что и температуры, и отдельный поток
    # под nvidia-smi крутился бы впустую.
    nado_gpu = bool(s.has_nvidia)
    if bool(prefs.get("sensors.gpu.on", True)) != nado_gpu:
        prefs.set("sensors.gpu.on", nado_gpu)
        horosho("опрос nvidia-smi",
                "включён" if nado_gpu else "выключен, он тут не нужен")

    # Если температуру прочитать нечем, поток опроса каждые две секунды
    # дёргал бы PowerShell впустую.
    if not est.get("cpu_temp") and bool(prefs.get("sensors.temps.on", True)):
        if sprosit("Температуру прочитать нечем. Выключить её опрос?"):
            prefs.set("sensors.temps.on", False)
            horosho("опрос температур выключен")
    return True


# --- итог -------------------------------------------------------------------

def _bez_povtorov(spisok):
    """Убрать одинаковые строки, сохранив порядок."""
    bylo, out = set(), []
    for b in spisok:
        if b[1] not in bylo:
            bylo.add(b[1])
            out.append(b)
    return out


def itog():
    zagolovok("Итог")
    plohie = _bez_povtorov([b for b in bedy if b[0]])
    # Одну и ту же беду находят разные проверки: и права, и опрос
    # датчиков, и разбор источника температуры. В итоге «температура
    # процессора» стояла трижды, да ещё в двух степенях важности разом.
    # Оставляем её там, где она важнее.
    vazhnoe = {b[1].split(":")[0].strip() for b in plohie}
    melkie = _bez_povtorov([b for b in bedy if not b[0]
                            and b[1].split(":")[0].strip() not in vazhnoe])
    bedy_est = plohie or melkie
    if not bedy_est:
        prosto("Всё на месте. Запускай app.bat.")
        return 0
    if plohie:
        prosto("Без этого программа будет работать не полностью:")
        for _, chto, chinit in plohie:
            print("   * " + chto)
            if chinit:
                print("       " + chinit)
    if melkie:
        prosto("")
        prosto("Мелочи, жить можно:")
        for _, chto, chinit in melkie:
            print("   * " + chto)
            if chinit:
                print("       " + chinit)
    prosto("")
    prosto("Когда поправишь - запусти start.bat ещё раз.")
    return 1 if plohie else 0


def main():
    # Язык выбираем первым делом: всё, что печатается ниже, уже должно
    # выйти на нём. Поэтому и шапка идёт после него, а не до.
    import prefs
    yazyk.vybrat(prefs.get("ui.lang") or yazyk_sistemy())
    print("")
    print("  EOne screen — " + t("осмотр машины"))
    print("  " + BASE)
    vybrat_yazyk(prefs)

    zagolovok("Библиотеки")
    nahodki, _net = osmotr.biblioteki()
    pokazat(nahodki)
    if _net:
        prosto("")
        prosto("Поставить всё разом:")
        print("      pip install " + " ".join(_net))
    if not osmotr.est_li("psutil") or not osmotr.est_li("PIL"):
        prosto("")
        prosto("Без обязательных библиотек осматривать дальше нечего.")
        return itog()

    zagolovok("Права")
    pokazat(osmotr.prava()[0])
    if IS_WINDOWS:
        zagolovok("Библиотека датчиков")
        pokazat(osmotr.dll()[0])

    zagolovok("Железо")
    nahodki, zhelezo = osmotr.zhelezo()
    pokazat(nahodki)

    zagolovok("Датчики")
    prosto("опрашиваю железо, это занимает несколько секунд…")
    nahodki, s, est = osmotr.datchiki()
    pokazat(nahodki)

    zagolovok("Экран")
    pokazat(osmotr.ekran()[0])

    zagolovok("Погода")
    pokazat(osmotr.pogoda(s)[0])

    zapisat(prefs, zhelezo, s, est)
    podstavit_v_temy(zhelezo)
    s.stop()
    return itog()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n" + t("прервано"))
        sys.exit(1)
