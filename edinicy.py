#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Единицы и форматы: градусы, часы, дата, начало недели.
#  Часть проекта EOne screen — открытой замены штатной программе
#  для экранов на контроллере TXW818.
#
#  Автор: EOne
#  Лицензия: CC BY-NC-SA 4.0 — использование в коммерческих целях
#  запрещено без письменного разрешения автора. См. файл LICENSE.
#
"""edinicy.py - в чём показывать числа: градусы, часы, дата, неделя.

Настройка одна на программу и лежит в settings.json, раздел units.
Действует и в окне, и на экране водянки: тема пишет «{cpu_temp:.0f} °C»,
а увидит человек то, что выбрал.

    import edinicy
    edinicy.gradusy(67.0)   ->  67.0  или  152.6
    edinicy.znak()          ->  "°C"  или  "°F"
    edinicy.chasy(now)      ->  "14:30"  или  "02:30 PM"
    edinicy.data(now)       ->  "13.08.2026"  или  "08/13/2026"

ВАЖНО: в градусы переводится только то, что человек ЧИТАЕТ. Значения,
которыми тема правит картинку - доля кольца, react по температуре, -
остаются в Цельсиях всегда. Иначе выбор шкалы сдвинул бы все пороги
в теме, и кольцо, настроенное на 40..90, при Фаренгейте залилось бы
целиком и навсегда.
"""

import prefs

# Что человек читает как температуру. Всё остальное - числа как числа.
GRADUSY_KLYUCHI = (
    "cpu_temp", "gpu_temp", "mb_temp",
    "weather_temp", "weather_feels", "weather_min", "weather_max",
)

# Скорость ветра. Внутри программа считает в километрах в час: так её
# отдаёт большинство служб, и так её понимают доли метели.
VETER_KLYUCHI = ("weather_wind",)

# Во что переводить километры в час и как это подписывать.
VETER = {
    "kmh": (1.0, "км/ч"),
    "ms": (1.0 / 3.6, "м/с"),
    "mph": (1.0 / 1.609344, "миль/ч"),
}

# Подписи ветра, которые могут стоять в теме готовым текстом. Меняются
# так же, как «°C»: тему писали один раз, а шкалу выбирает человек.
VETER_PODPISI = ("км/ч", "km/h", "м/с", "m/s", "миль/ч", "mph")

# Порядок чисел в дате: как записывают день, месяц и год.
PORYADKI = {
    "dmy": ("%d.%m.%Y", "%d.%m.%y", "%d %B"),
    "mdy": ("%m/%d/%Y", "%m/%d/%y", "%B %d"),
    "ymd": ("%Y-%m-%d", "%y-%m-%d", "%B %d"),
}


def shkala():
    """Какая шкала выбрана: "c" или "f"."""
    return "f" if str(prefs.get("units.temp", "c")).lower().startswith("f") \
        else "c"


def znak():
    """Как подписывают градусы при выбранной шкале."""
    return "°F" if shkala() == "f" else "°C"


def gradusy(c):
    """Температуру из Цельсия - в выбранную шкалу."""
    if not isinstance(c, (int, float)) or isinstance(c, bool):
        return c
    return c * 9.0 / 5.0 + 32.0 if shkala() == "f" else c


def shkala_vetra():
    """В чём показывать ветер: "kmh", "ms" или "mph"."""
    vid = str(prefs.get("units.wind", "kmh")).lower()
    return vid if vid in VETER else "kmh"


def veter(v):
    """Ветер из километров в час - в выбранную меру."""
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return v
    return v * VETER[shkala_vetra()][0]


def znak_vetra():
    """Как подписывают ветер при выбранной мере."""
    return VETER[shkala_vetra()][1]


def dvenadcat():
    """Часы на двенадцать, с AM и PM."""
    return str(prefs.get("units.clock", "24")).startswith("12")


def chasy(dt, sekundy=False):
    """Время в выбранном виде."""
    if dvenadcat():
        return dt.strftime("%I:%M:%S %p" if sekundy else "%I:%M %p")
    return dt.strftime("%H:%M:%S" if sekundy else "%H:%M")


def data(dt, korotko=False, slovami=False):
    """Дата в выбранном порядке чисел."""
    dlinnaya, korotkaya, mesyacem = PORYADKI.get(
        str(prefs.get("units.date", "dmy")).lower(), PORYADKI["dmy"])
    if slovami:
        return dt.strftime(mesyacem)
    return dt.strftime(korotkaya if korotko else dlinnaya)


def s_voskresenya():
    """Неделя начинается с воскресенья, а не с понедельника."""
    return str(prefs.get("units.week_start", "mon")).lower().startswith("sun")


def den_nedeli(dt):
    """Номер дня недели с учётом того, с какого дня она начинается.

    Считаем от единицы: при начале с понедельника понедельник - первый,
    при начале с воскресенья первым становится воскресенье. Тема может
    зажигать по этому числу нужный из семи блоков.
    """
    pn = dt.weekday()                      # 0 - понедельник, 6 - воскресенье
    return (pn + 1) % 7 + 1 if s_voskresenya() else pn + 1


def dobavit(snap):
    """Дописать в снимок готовые надписи времени и даты.

    Сырое время тоже остаётся: тема, которой нужен свой вид, пишет
    «{now:%H:%M}» и получает ровно его, мимо всяких настроек.
    """
    now = snap.get("now")
    if now is None or not hasattr(now, "strftime"):
        return snap
    snap["time"] = chasy(now)
    snap["time_sec"] = chasy(now, sekundy=True)
    snap["date"] = data(now)
    snap["date_short"] = data(now, korotko=True)
    snap["date_words"] = data(now, slovami=True)
    snap["weekday"] = now.strftime("%A")
    snap["day_index"] = den_nedeli(now)
    snap["deg"] = znak()
    snap["wind_unit"] = znak_vetra()
    return snap


def dlya_teksta(data_dict):
    """Снимок для НАДПИСЕЙ: температуры переведены в выбранную шкалу.

    Отдельная копия, а не правка на месте: исходный снимок нужен целым
    для react и для долей кольца - см. пояснение в шапке файла.
    """
    gradusy_nado = shkala() != "c"
    veter_nado = shkala_vetra() != "kmh"
    if not gradusy_nado and not veter_nado:
        return data_dict
    out = dict(data_dict)
    if gradusy_nado:
        for k in GRADUSY_KLYUCHI:
            if k in out:
                out[k] = gradusy(out[k])
    if veter_nado:
        for k in VETER_KLYUCHI:
            if k in out:
                out[k] = veter(out[k])
    return out


def podpis(shablon):
    """Подписи единиц в теме - на те, что выбраны.

    Тему пишут один раз, в Цельсиях и километрах в час. Чтобы она
    не врала при других единицах, подпись меняем прямо в шаблоне:
    числа к этому времени уже переведены.
    """
    if not isinstance(shablon, str):
        return shablon
    if shkala() != "c":
        shablon = shablon.replace("°C", "°F").replace("°c", "°f")
    if shkala_vetra() != "kmh":
        nado = znak_vetra()
        for bylo in VETER_PODPISI:
            if bylo != nado and bylo in shablon:
                shablon = shablon.replace(bylo, nado)
    return shablon


if __name__ == "__main__":
    from datetime import datetime
    now = datetime.now()
    print("шкала:        {}  ({})".format(shkala(), znak()))
    print("67 °C:        {:.1f}".format(gradusy(67.0)))
    print("время:        {}".format(chasy(now)))
    print("время с сек.: {}".format(chasy(now, True)))
    print("дата:         {}".format(data(now)))
    print("дата коротко: {}".format(data(now, korotko=True)))
    print("день недели:  {} (номер {})".format(now.strftime("%A"),
                                               den_nedeli(now)))
