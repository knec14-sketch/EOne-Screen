#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Осмотр машины: что установлено, что отвечает, чего не хватает.
#  Часть проекта EOne screen.
#
#  Автор: EOne
#  Лицензия: CC BY-NC-SA 4.0 — использование в коммерческих целях
#  запрещено без письменного разрешения автора. См. файл LICENSE.
#
"""osmotr.py - проверки машины, общие для консоли и для окна.

Раньше эти проверки жили внутри start.py и сразу печатали в консоль.
Окну такое не переиспользовать: ему нужны не строчки, а находки, чтобы
рядом с каждой поставить кнопку.

Поэтому здесь проверки только СМОТРЯТ и возвращают список находок,
а как их показать - решает тот, кто спросил: start.py печатает,
окно раскладывает по карточкам.

    import osmotr
    nahodki, net = osmotr.biblioteki()
    for n in nahodki:
        print(n.chto, "-", n.pojasnenie)
"""

import os
import sys
import time

import edinicy
import papka

IS_WINDOWS = sys.platform.startswith("win")
BASE = papka.programma()

# Четыре файла из архива LibreHardwareMonitor - ровно столько нужно,
# чтобы найти все датчики.
DLL_NUZHNY = ("LibreHardwareMonitorLib.dll", "HidSharp.dll",
              "System.Memory.dll",
              "System.Runtime.CompilerServices.Unsafe.dll")

# Пятый файл нужен только тем, у кого видеокарта не Nvidia.
DLL_DLYA_GPU = "System.Numerics.Vectors.dll"

# Что нужно программе. Последнее поле - обязательна ли она.
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

# Про эти показания говорится отдельно и по существу: там видно не только
# «нет», но и почему. В общий список бед их писать не надо.
OTDELNO = {"cpu_temp", "gpu_load", "gpu_temp", "gpu_mem_used_gb",
           "gpu_power_w"}


class Nahodka:
    """Одна строчка осмотра.

    horosho - True всё в порядке, False беда, None просто сведение.
    chinit  - что человеку сделать, если беда. Пусто - делать нечего.
    vazhno  - без этого программа работает не полностью.
    """

    __slots__ = ("horosho", "chto", "pojasnenie", "chinit", "vazhno")

    def __init__(self, horosho, chto, pojasnenie="", chinit="", vazhno=True):
        self.horosho = horosho
        self.chto = chto
        self.pojasnenie = pojasnenie
        self.chinit = chinit
        self.vazhno = vazhno

    def __repr__(self):
        znak = {True: "+", False: "-", None: " "}[self.horosho]
        return "{} {} {}".format(znak, self.chto, self.pojasnenie)


def bedy(nahodki):
    """Только то, что не в порядке."""
    return [n for n in nahodki if n.horosho is False]


# --- библиотеки -------------------------------------------------------------

def est_li(imya):
    """Установлена ли библиотека.

    Сначала смотрим в уже загруженные: у pythonnet модуль clr после
    загрузки остаётся без __spec__, и find_spec на нём спотыкается -
    в окне, где датчики его уже подняли, библиотека выглядела бы
    отсутствующей.
    """
    if imya in sys.modules:
        return True
    import importlib.util
    try:
        return importlib.util.find_spec(imya) is not None
    except (ImportError, ValueError):
        return False


def biblioteki():
    """Что установлено, чего не хватает и чем ставить."""
    nahodki = [Nahodka(None, "Python {}.{}.{}".format(*sys.version_info[:3]))]
    net = []
    for imya, stavit, zachem, nuzhna in BIBLIOTEKI:
        if est_li(imya):
            nahodki.append(Nahodka(True, stavit or imya, zachem))
            continue
        if not stavit:                  # tkinter ставится вместе с Python
            nahodki.append(Nahodka(
                False, imya, zachem,
                "переустанови Python, отметив «tcl/tk and IDLE»", True))
            continue
        net.append(stavit)
        nahodki.append(Nahodka(False, stavit, zachem,
                               "pip install {}".format(stavit), nuzhna))
    return nahodki, net


# --- права и файлы библиотеки ------------------------------------------------

def zablokirovan(put):
    """Помечен ли файл как скачанный из интернета.

    Windows держит пометку отдельным потоком NTFS. Пока она на месте,
    .NET отказывается загружать сборку и жалуется невнятно.
    """
    if not IS_WINDOWS:
        return False
    try:
        with open(put + ":Zone.Identifier", "r", encoding="utf-8") as f:
            return "ZoneId=3" in f.read() or "ZoneId=4" in f.read()
    except OSError:
        return False


def razblokirovat(put):
    """Снять пометку. Файл при этом не меняется."""
    try:
        os.remove(put + ":Zone.Identifier")
        return True
    except OSError:
        return False


def prava():
    import sensors as sensors_mod
    admin = sensors_mod._check_admin()
    if admin:
        return [Nahodka(True, "права администратора есть")], True
    return [Nahodka(False, "прав администратора нет",
                    "без них температуры процессора не будет вовсе",
                    "запусти программу через app.bat", True)], False


def dll(snimat_pometki=True):
    """Файлы библиотеки датчиков: на месте ли и не заблокированы ли."""
    nahodki, net, zablokirovany = [], [], []
    for imya in DLL_NUZHNY:
        put = os.path.join(BASE, imya)
        if not os.path.exists(put):
            net.append(imya)
        elif IS_WINDOWS and zablokirovan(put):
            zablokirovany.append(put)
    for imya in net:
        nahodki.append(Nahodka(
            False, imya, "нет рядом с программой",
            "возьми из архива LibreHardwareMonitor и положи сюда", True))
    if not net:
        nahodki.append(Nahodka(True, "все четыре файла на месте"))
    for put in zablokirovany:
        if snimat_pometki and razblokirovat(put):
            nahodki.append(Nahodka(True, os.path.basename(put),
                                   "снял пометку «из интернета»"))
        else:
            nahodki.append(Nahodka(
                False, os.path.basename(put),
                "помечен как скачанный из интернета",
                "Свойства файла -> галочка «Разблокировать»", True))
    if not zablokirovany and not net:
        nahodki.append(Nahodka(True, "пометки «из интернета» ни на одном нет"))

    # Пятый файл спрашиваем только с тех, кому он действительно нужен
    import sensors as sensors_mod
    if not sensors_mod.gpu_vendor().startswith("nvidia"):
        if os.path.exists(os.path.join(BASE, DLL_DLYA_GPU)):
            nahodki.append(Nahodka(True, DLL_DLYA_GPU,
                                   "нужен для видеокарт не Nvidia — на месте"))
        else:
            nahodki.append(Nahodka(
                False, DLL_DLYA_GPU,
                "нужен, чтобы читать видеокарту не Nvidia",
                "возьми из архива LibreHardwareMonitor и положи сюда", True))
    return nahodki, not net


# --- железо -----------------------------------------------------------------

def zhelezo():
    """Как называется процессор и видеокарта, сколько ядер и памяти."""
    import sensors as sensors_mod
    svedeniya = {}
    nahodki = []
    cpu = sensors_mod.cpu_name()
    gpu = sensors_mod.gpu_name()
    svedeniya["cpu"] = cpu
    svedeniya["gpu"] = gpu
    svedeniya["gpu_vendor"] = sensors_mod.gpu_vendor(gpu)
    nahodki.append(Nahodka(bool(cpu), "процессор",
                           cpu or "название выяснить не удалось",
                           "", False))
    nahodki.append(Nahodka(bool(gpu), "видеокарта",
                           gpu or "название выяснить не удалось",
                           "", False))
    try:
        import psutil
        svedeniya["cores"] = psutil.cpu_count(logical=False)
        svedeniya["threads"] = psutil.cpu_count(logical=True)
        svedeniya["ram_gb"] = psutil.virtual_memory().total / 1073741824.0
        nahodki.append(Nahodka(None, "ядер {}, потоков {}".format(
            svedeniya["cores"], svedeniya["threads"])))
        nahodki.append(Nahodka(None, "оперативной памяти {:.0f} ГБ".format(
            svedeniya["ram_gb"])))
    except Exception:
        pass
    disk = (os.environ.get("SystemDrive", "C:") + "\\") if IS_WINDOWS else "/"
    svedeniya["disk"] = disk
    nahodki.append(Nahodka(None, "системный диск {}".format(disk)))
    return nahodki, svedeniya


# --- датчики ----------------------------------------------------------------

def datchiki(zhdat=8.0, s=None):
    """Поднять сбор показаний и посмотреть, что отвечает на самом деле.

    Возвращает и сам сбор: окну он нужен, чтобы не поднимать второй.
    """
    import sensors as sensors_mod
    svoy = s is None
    if svoy:
        s = sensors_mod.Sensors()
    # Скорость сети считается по разнице между двумя замерами, поэтому
    # раньше двух опросов её не будет, как бы быстро ни ответило всё
    # остальное. Ждём именно её, а не просто «хоть что-нибудь».
    kraj = time.time() + zhdat
    while time.time() < kraj:
        time.sleep(0.5)
        snap = s.read()
        gotovo = all(k in snap for k in ("cpu_load", "ram_load",
                                         "net_down_mbs"))
        if gotovo and (s.has_lhm or not s.plan["temps"][0]):
            if s.has_weather or not s.plan["weather"][0]:
                break
    snap = s.read()

    nahodki, est = [], {}
    for key, imya in VAZHNYE:
        znach = snap.get(key)
        chitaetsya = znach is not None and not isinstance(
            znach, sensors_mod.Missing)
        # Ровный ноль на градуснике - это не ноль градусов, а молчание:
        # без прав администратора библиотека отдаёт нули по всем ядрам.
        if chitaetsya and key.endswith("_temp") and float(znach) <= 0:
            chitaetsya = False
        est[key] = bool(chitaetsya)
        if chitaetsya:
            try:
                # Температуру показываем в той шкале, которую человек
                # выбрал: увидеть Цельсии там, где всюду Фаренгейт,
                # он не ожидает.
                if key.endswith("_temp"):
                    pojasnenie = "{:.1f} {}".format(
                        edinicy.gradusy(float(znach)), edinicy.znak())
                else:
                    pojasnenie = "{:.1f}".format(float(znach))
            except (TypeError, ValueError):
                pojasnenie = str(znach)
            nahodki.append(Nahodka(True, imya, pojasnenie))
        else:
            nahodki.append(Nahodka(False, imya, "не читается", "",
                                   key not in OTDELNO))

    if s.temp_source and est.get("cpu_temp"):
        nahodki.append(Nahodka(True, "температура читается", s.temp_source))
        if s.temp_sensor:
            nahodki.append(Nahodka(None, "выбран датчик: " + s.temp_sensor))
    elif s.temp_source:
        nahodki.append(Nahodka(
            False, "температура процессора",
            "источник открылся, но отдаёт нули",
            "так бывает без прав администратора: запусти start.bat", True))
    else:
        nahodki.append(Nahodka(
            False, "температура процессора",
            s.temp_note or "источник не найден",
            "нужны права администратора и четыре .dll рядом", True))
    if s.gpu_source:
        nahodki.append(Nahodka(True, "видеокарта читается", s.gpu_source))
    elif s.gpu_note:
        nahodki.append(Nahodka(
            False, "видеокарта", s.gpu_note,
            "положи System.Numerics.Vectors.dll рядом с программой", True))
    else:
        nahodki.append(Nahodka(
            False, "видеокарта", "нет источника показаний",
            "для Nvidia хватит драйвера, для AMD и Intel нужна "
            "библиотека датчиков и права", True))
    if svoy:
        s.stop()
    return nahodki, s, est


# --- экран ------------------------------------------------------------------

def ekran():
    """Виден ли экран на COM-порту, и что на портах есть вообще."""
    try:
        import txw818
        port = txw818.find_port()
    except Exception as e:
        return [Nahodka(False, "не смог заглянуть в порты", str(e)[:60],
                        "pip install pyserial", True)], None
    if port:
        return [Nahodka(True, "экран найден", port)], port
    nahodki = [Nahodka(False, "экран не найден", "ни на одном COM-порту",
                       "проверь кабель от помпы к разъёму USB на плате",
                       True)]
    try:
        from serial.tools import list_ports
        vse = list(list_ports.comports())
        if vse:
            nahodki.append(Nahodka(None, "а вот что на портах есть:"))
            for p in vse:
                nahodki.append(Nahodka(None, "   {:<8} {}".format(
                    p.device, p.description)))
        else:
            nahodki.append(Nahodka(None, "COM-портов не найдено вообще"))
    except Exception:
        pass
    return nahodki, None


# --- погода -----------------------------------------------------------------

def pogoda(s):
    """Отвечает ли служба прогноза и что она сказала."""
    if not s.plan["weather"][0]:
        return [Nahodka(False, "погода выключена в настройках", "", "",
                        False)], False
    if s.has_weather:
        nahodki = [Nahodka(True, "прогноз получен", "{}, {}".format(
            s.weather_source or "?", s.weather_city or "?"))]
        if s.sunrise and s.sunset:
            nahodki.append(Nahodka(None, "восход {}   закат {}".format(
                s.sunrise.strftime("%H:%M"), s.sunset.strftime("%H:%M"))))
        return nahodki, True
    return [Nahodka(False, "прогноза нет",
                    s.weather_note or "источник не ответил",
                    "проверь интернет и место в Настройках -> Погода и адрес",
                    False)], False


if __name__ == "__main__":
    for imya, fn in (("библиотеки", biblioteki), ("права", prava),
                     ("библиотека датчиков", dll), ("железо", zhelezo),
                     ("экран", ekran)):
        print("\n=== {} ===".format(imya))
        for n in fn()[0]:
            print("  ", n)
