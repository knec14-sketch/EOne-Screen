#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Разговор с операционной системой: температуры, единицы, ярлык.
#  Часть проекта EOne screen.
#
#  Автор: EOne
#  Лицензия: CC BY-NC-SA 4.0 — использование в коммерческих целях
#  запрещено без письменного разрешения автора. См. файл LICENSE.
#
"""sistema.py - всё, что зависит от операционной системы.

Программа спрашивает отсюда: «какие есть температуры», «в чём тут меряют
градусы», «сделай ярлык». И не знает, на чём работает.

Так сделано намеренно. Разложить по коду развилки «если Windows / если
Linux» - самый быстрый способ испортить обе версии сразу: каждая правка
задевает чужую систему, а проверить её негде. Здесь же всё в одном месте
и видно целиком.

Windows-часть уже написана и проверена, поэтому она осталась там, где
была: этот модуль её просто зовёт. А всё, что нужно Linux, живёт здесь.

    import sistema
    sistema.LINUX                 -> True на Linux
    sistema.temperatury()         -> {"процессор": 57.0, ...} или None
    sistema.edinicy_sistemy()     -> {"temp": "c", "clock": "24", ...}

ЧЕГО ЗДЕСЬ НЕТ. Всё, что и так работает везде: psutil, Pillow, разговор
с экраном по последовательному порту. Их трогать незачем - они одинаковы
на обеих системах.

ПРОВЕРЕНО НА WINDOWS. Linux-ветки написаны по описаниям ядра и проверены
на поддельных файлах /sys, но на живой машине с Linux не запускались ни
разу. Это надо знать тому, кто возьмётся: первое, что стоит сделать, -
запустить и прислать, что сломалось.
"""

import os
import subprocess
import sys

WINDOWS = sys.platform.startswith("win")
LINUX = sys.platform.startswith("linux")

# Чтобы вызовы не мигали чёрными окошками на Windows
_TIHO = dict(creationflags=0x08000000) if WINDOWS else {}


def _sprosit(komanda, timeout=4):
    """Выполнить команду и вернуть её вывод. Не вышло - пустая строка."""
    try:
        got = subprocess.run(komanda, capture_output=True, text=True,
                             timeout=timeout, encoding="utf-8",
                             errors="replace", **_TIHO)
        return (got.stdout or "").strip()
    except Exception:
        return ""


def _prochest(put):
    """Содержимое файла из /sys или /proc. Нет файла - пустая строка."""
    try:
        with open(put, encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return ""


# --- температуры -------------------------------------------------------------

# Как ядро Linux называет датчики и что это на самом деле. Имя лежит
# в hwmonN/name, а сами градусы - в tempN_input, в тысячных долях.
HWMON_PROCESSOR = ("k10temp", "coretemp", "zenpower", "cpu_thermal",
                   "cpu-thermal", "acpitz")
HWMON_VIDEOKARTA = ("amdgpu", "radeon", "nouveau", "i915", "xe")


def temperatury(koren="/sys/class/hwmon"):
    """Температуры железа на Linux. На Windows - None.

    None означает «спроси у того, кто это умеет»: на Windows температуры
    читает библиотека LibreHardwareMonitor, и она уже написана.

    На Linux всё проще: ядро само выкладывает показания в /sys/class/hwmon,
    и прав администратора для чтения не нужно. Это тот редкий случай,
    когда на Linux работать легче, чем на Windows.

    koren задаётся, чтобы разбор можно было проверить на подложенных
    файлах, не имея Linux под рукой.
    """
    if not LINUX:
        return None
    itog = {}
    try:
        papki = sorted(os.listdir(koren))
    except OSError:
        return itog
    for papka in papki:
        put = os.path.join(koren, papka)
        imya = _prochest(os.path.join(put, "name")).lower()
        if not imya:
            continue
        kto = None
        if any(k in imya for k in HWMON_PROCESSOR):
            kto = "процессор"
        elif any(k in imya for k in HWMON_VIDEOKARTA):
            kto = "видеокарта"
        if kto is None:
            continue
        for fayl in sorted(os.listdir(put)):
            if not (fayl.startswith("temp") and fayl.endswith("_input")):
                continue
            syroe = _prochest(os.path.join(put, fayl))
            if not syroe:
                continue
            try:
                gradusy = float(syroe) / 1000.0      # ядро отдаёт тысячные
            except ValueError:
                continue
            if not (-50.0 < gradusy < 150.0):        # явная чепуха
                continue
            podpis = _prochest(os.path.join(
                put, fayl.replace("_input", "_label"))) or fayl
            itog.setdefault(kto, []).append((podpis, gradusy))
    # Из нескольких датчиков берём тот, что похож на общий: у Ryzen это
    # Tctl, у Intel - Package. Остальные скачут сильнее и в панели
    # выглядят дёргаными.
    gotovo = {}
    for kto, spisok in itog.items():
        obshy = next((z for p, z in spisok
                      if any(k in p.lower() for k in
                             ("tctl", "tdie", "package", "edge"))), None)
        gotovo[kto] = obshy if obshy is not None else max(z for _p, z in spisok)
    return gotovo


# --- как называется железо ---------------------------------------------------

def imya_processora():
    """Название процессора на Linux. На Windows - None."""
    if not LINUX:
        return None
    for stroka in _prochest("/proc/cpuinfo").splitlines():
        if stroka.lower().startswith("model name"):
            return stroka.split(":", 1)[-1].strip()
    return ""


def imya_videokarty():
    """Название видеокарты на Linux. На Windows - None.

    Сначала спрашиваем драйвер Nvidia - он отвечает точнее всех.
    Нет его - смотрим, что вообще висит на шине.
    """
    if not LINUX:
        return None
    got = _sprosit(["nvidia-smi", "--query-gpu=name",
                    "--format=csv,noheader"])
    if got:
        return got.splitlines()[0].strip()
    for stroka in _sprosit(["lspci"]).splitlines():
        nizhe = stroka.lower()
        if "vga compatible controller" in nizhe or "3d controller" in nizhe:
            return stroka.split(":", 2)[-1].strip()
    return ""


# --- единицы и форматы -------------------------------------------------------

def edinicy_sistemy():
    """В чём меряет сама система. На Windows - None, там своё чтение.

    На Linux смотрим переменные окружения локали. Единственная страна,
    где температуру меряют Фаренгейтом в быту, - США, поэтому решаем
    по коду страны, а не гадаем.
    """
    if not LINUX:
        return None
    itog = {"temp": "c", "wind": "kmh", "clock": "24", "date": "dmy"}
    lok = (os.environ.get("LC_MEASUREMENT") or os.environ.get("LC_ALL")
           or os.environ.get("LANG") or "")
    strana = lok.split(".")[0].split("_")[-1].upper()
    if strana in ("US", "LR", "MM"):          # там же и мили с фунтами
        itog.update({"temp": "f", "wind": "mph", "clock": "12", "date": "mdy"})
    elif strana in ("GB", "IE", "AU", "NZ", "CA", "IN", "PH", "ZA"):
        itog["clock"] = "12"
        if strana in ("GB", "IE", "AU", "NZ", "IN", "ZA"):
            itog["date"] = "dmy"
        else:
            itog["date"] = "mdy"
    return itog


def temnoe_oformlenie():
    """Тёмное ли оформление у рабочего стола. Не выяснили - None.

    Спрашиваем у GNOME и его родни. У KDE и прочих ответ другой, и если
    его нет - лучше честно сказать «не знаю», чем угадывать.
    """
    if not LINUX:
        return None
    got = _sprosit(["gsettings", "get", "org.gnome.desktop.interface",
                    "color-scheme"]).strip("'\" ").lower()
    if got:
        return "dark" in got
    got = _sprosit(["gsettings", "get", "org.gnome.desktop.interface",
                    "gtk-theme"]).strip("'\" ").lower()
    if got:
        return "dark" in got
    return None


# --- ярлык и автозапуск ------------------------------------------------------

# На Linux и то и другое - один и тот же текстовый файл, положенный
# в разные папки. Никакого реестра.
YARLYK_TEKST = """[Desktop Entry]
Type=Application
Name=EOne screen
Comment=Water-cooler screen
Exec={komanda}
Icon={znachok}
Terminal=false
Categories=Utility;System;
"""


def _papka_yarlykov(avtozapusk=False):
    dom = os.path.expanduser("~")
    if avtozapusk:
        return os.path.join(os.environ.get("XDG_CONFIG_HOME",
                                           os.path.join(dom, ".config")),
                            "autostart")
    return os.path.join(os.environ.get("XDG_DATA_HOME",
                                       os.path.join(dom, ".local", "share")),
                        "applications")


def yarlyk_put(avtozapusk=False):
    """Где лежит файл ярлыка. На Windows - None."""
    if not LINUX:
        return None
    return os.path.join(_papka_yarlykov(avtozapusk), "eone-screen.desktop")


def sdelat_yarlyk(on, komanda, znachok="", avtozapusk=False):
    """Создать или убрать ярлык на Linux. На Windows - None."""
    if not LINUX:
        return None
    put = yarlyk_put(avtozapusk)
    if not on:
        try:
            if os.path.exists(put):
                os.remove(put)
            return True
        except OSError:
            return False
    try:
        os.makedirs(os.path.dirname(put), exist_ok=True)
        with open(put, "w", encoding="utf-8") as f:
            f.write(YARLYK_TEKST.format(komanda=komanda, znachok=znachok))
        os.chmod(put, 0o755)          # рабочий стол требует права на запуск
        return True
    except OSError:
        return False


# --- мелочи, которых на Linux просто нет -------------------------------------

def nuzhna_biblioteka_datchikov():
    """Нужны ли четыре .dll рядом с программой.

    На Linux температуры читает ядро, и никакой чужой библиотеки
    не требуется. Спрашивать про неё в осмотре машины там незачем.
    """
    return WINDOWS


def pometka_iz_interneta(put):
    """Помечен ли файл как скачанный из интернета. На Linux - никогда.

    Такой пометки в Linux не существует вовсе: там права на запуск
    снимаются иначе и .dll никто не грузит.
    """
    if not WINDOWS:
        return False
    try:
        with open(put + ":Zone.Identifier", "r", encoding="utf-8") as f:
            soderzhimoe = f.read()
        return "ZoneId=3" in soderzhimoe or "ZoneId=4" in soderzhimoe
    except OSError:
        return False


def snyat_pometku(put):
    """Снять пометку «скачано из интернета». На Linux нечего снимать."""
    if not WINDOWS:
        return True
    try:
        os.remove(put + ":Zone.Identifier")
        return True
    except OSError:
        return False


def imya_sistemy():
    """Как назвать систему человеку."""
    if WINDOWS:
        return "Windows"
    if LINUX:
        return "Linux"
    return sys.platform


if __name__ == "__main__":
    print("система:            {}".format(imya_sistemy()))
    print("температуры:        {}".format(temperatury()))
    print("процессор:          {}".format(imya_processora()))
    print("видеокарта:         {}".format(imya_videokarty()))
    print("единицы системы:    {}".format(edinicy_sistemy()))
    print("тёмное оформление:  {}".format(temnoe_oformlenie()))
    print("нужна библиотека:   {}".format(nuzhna_biblioteka_datchikov()))
    print("ярлык лёг бы в:     {}".format(yarlyk_put()))
