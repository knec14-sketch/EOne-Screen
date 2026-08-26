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

import sys
import time

import prefs
import sistema
import yazyk

IS_WINDOWS = sys.platform.startswith("win")

# Что стоит в самой Windows. Читается из реестра и придерживается:
# спрашивать систему на каждый кадр незачем, а меняют эти настройки
# раз в жизни.
_sistema = None
_sistema_kogda = 0.0


def _iz_windows():
    """Единицы и форматы, выбранные в самой Windows.

    iMeasure    0 - метрическая система, 1 - американская
    sShortTime  строчная h - часы на двенадцать, прописная H - на 24
    sShortDate  порядок букв d, M и y и есть порядок чисел в дате
    """
    global _sistema, _sistema_kogda
    if _sistema is not None and time.time() - _sistema_kogda < 5.0:
        return _sistema
    itog = {"temp": "c", "wind": "kmh", "clock": "24", "date": "dmy"}
    ot_sistemy = sistema.edinicy_sistemy()      # не Windows - спросим там
    if ot_sistemy:
        itog.update(ot_sistemy)
    elif IS_WINDOWS:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Control Panel\International") as k:
                def spros(imya):
                    try:
                        return str(winreg.QueryValueEx(k, imya)[0])
                    except OSError:
                        return ""
                if spros("iMeasure") == "1":       # американская
                    itog["temp"] = "f"
                    itog["wind"] = "mph"
                vremya = spros("sShortTime") or spros("sTimeFormat")
                if "h" in vremya:                  # строчная - на двенадцать
                    itog["clock"] = "12"
                data = spros("sShortDate").lower()
                poryadok = [z for z in data if z in "dmy"]
                pervye = []
                for z in poryadok:
                    if z not in pervye:
                        pervye.append(z)
                itog["date"] = {"dmy": "dmy", "mdy": "mdy",
                                "ymd": "ymd"}.get("".join(pervye), "dmy")
        except Exception:
            pass
    _sistema, _sistema_kogda = itog, time.time()
    return itog


def _vybor(klyuch, svoy):
    """Что выбрано: своё или то, что стоит в Windows."""
    if str(svoy).lower() in ("system", "windows", ""):
        return _iz_windows()[klyuch]
    return svoy

# Что человек читает как температуру. Всё остальное - числа как числа.
GRADUSY_KLYUCHI = (
    "cpu_temp", "gpu_temp", "mb_temp",
    "weather_temp", "weather_feels", "weather_min", "weather_max",
)

# Скорость ветра. Внутри программа считает в километрах в час: так её
# отдаёт большинство служб, и так её понимают доли метели.
VETER_KLYUCHI = ("weather_wind",)

# Во что переводить километры в час и как это подписывать: множитель,
# обычная подпись и те языки, где она своя. Латиницей пишут одинаково -
# km/h и m/s международные, - а по-русски надо своими буквами.
VETER = {
    "kmh": (1.0, "km/h", {"ru": "км/ч"}),
    "ms": (1.0 / 3.6, "m/s", {"ru": "м/с"}),
    "mph": (1.0 / 1.609344, "mph", {"ru": "миль/ч"}),
}

# Подписи ветра, которые могут стоять в теме готовым текстом. Меняются
# так же, как «°C»: тему писали один раз, а шкалу выбирает человек.
VETER_PODPISI = ("км/ч", "km/h", "м/с", "m/s", "миль/ч", "mph")

# Порядок чисел в дате: полная, короткая, словами, без года.
# Без года нужна панели: «26.08» на весь экран читается издалека,
# а год на корпусе водянки никому не нужен.
PORYADKI = {
    "dmy": ("%d.%m.%Y", "%d.%m.%y", "%d %B", "%d.%m"),
    "mdy": ("%m/%d/%Y", "%m/%d/%y", "%B %d", "%m/%d"),
    "ymd": ("%Y-%m-%d", "%y-%m-%d", "%B %d", "%m-%d"),
}

# Дни и месяцы своими словами. Через strftime нельзя: он берёт язык
# у системы, и на португальской машине выходило «terça» рядом с русской
# погодой. Тема должна говорить на одном языке, своём.
DNI_NEDELI = {
    "ru": ("понедельник", "вторник", "среда", "четверг", "пятница",
           "суббота", "воскресенье"),
    "en": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
           "Saturday", "Sunday"),
    "es": ("lunes", "martes", "miércoles", "jueves", "viernes",
           "sábado", "domingo"),
    "de": ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag",
           "Samstag", "Sonntag"),
    "fr": ("lundi", "mardi", "mercredi", "jeudi", "vendredi",
           "samedi", "dimanche"),
    # Полные португальские названия - «segunda-feira» и далее. На панели
    # они вдвое длиннее прочих, поэтому берём короткую разговорную форму:
    # так говорят и так пишут в календарях.
    "pt": ("segunda", "terça", "quarta", "quinta", "sexta",
           "sábado", "domingo"),
    "it": ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì",
           "sabato", "domenica"),
}
# По-русски месяц при числе стоит в родительном: «26 августа».
MESYACY = {
    "ru": ("января", "февраля", "марта", "апреля", "мая", "июня", "июля",
           "августа", "сентября", "октября", "ноября", "декабря"),
    "en": ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"),
    "es": ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
           "agosto", "septiembre", "octubre", "noviembre", "diciembre"),
    "de": ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
           "August", "September", "Oktober", "November", "Dezember"),
    "fr": ("janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"),
    "pt": ("janeiro", "fevereiro", "março", "abril", "maio", "junho",
           "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"),
    "it": ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
           "luglio", "agosto", "settembre", "ottobre", "novembre",
           "dicembre"),
}

# Как в языке пишут число с месяцем. Порядок чисел человек выбирает
# в настройках, а предлог и точка - свойство языка, а не выбора.
DATA_SLOVAMI = {
    "ru": "{den} {mesyac}",
    "en": "{den} {mesyac}",
    "es": "{den} de {mesyac}",
    "de": "{den}. {mesyac}",
    "fr": "{den} {mesyac}",
    "pt": "{den} de {mesyac}",
    "it": "{den} {mesyac}",
}

# Языки, где месяц может встать перед числом, если так выбрано
# в настройках. В остальных порядок слов свой: «августа 26»
# и «de agosto 26» не говорят нигде.
MESYAC_MOZHET_VPERED = ("en",)


# Между временем и AM/PM ставится узкий неразрывный пробел, а не обычный.
# Причина не в правилах набора, хотя и по ним так: в рисованных шрифтах
# вроде Project Space обычный пробел втрое шире буквы, и «5:10   PM»
# разъезжается на полэкрана.
UZKIY_PROBEL = " "


def _yazyk_temy():
    """Код языка темы. Нет для него таблицы - берём английскую."""
    kod = yazyk.yazyk_temy()
    return kod if kod in DNI_NEDELI else "en"


def shkala():
    """Какая шкала выбрана: "c" или "f". По умолчанию - как в Windows."""
    vid = _vybor("temp", prefs.get("units.temp", "system"))
    return "f" if str(vid).lower().startswith("f") else "c"


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
    vid = str(_vybor("wind", prefs.get("units.wind", "system"))).lower()
    return vid if vid in VETER else "kmh"


def veter(v):
    """Ветер из километров в час - в выбранную меру."""
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return v
    return v * VETER[shkala_vetra()][0]


def znak_vetra():
    """Как подписывают ветер при выбранной мере и на выбранном языке."""
    kmh, obychno, osobye = VETER[shkala_vetra()]
    # Подпись уходит на панель, а не в окно, поэтому язык - темы.
    return osobye.get(_yazyk_temy(), obychno)


def dvenadcat():
    """Часы на двенадцать, с AM и PM."""
    return str(_vybor("clock", prefs.get("units.clock", "system"))
               ).startswith("12")


def chasy(dt, sekundy=False):
    """Время в выбранном виде.

    На двенадцати часах ведущий ноль снимаем: «4:46 PM», а не «04:46 PM» -
    так пишут везде, где так считают, и на экране это шире без нужды.
    """
    if dvenadcat():
        chas = dt.hour % 12 or 12
        hvost = dt.strftime(":%M:%S" if sekundy else ":%M")
        return "{}{}{}{}".format(chas, hvost, UZKIY_PROBEL, dt.strftime("%p"))
    return dt.strftime("%H:%M:%S" if sekundy else "%H:%M")


def data(dt, korotko=False, slovami=False, bez_goda=False):
    """Дата в выбранном порядке чисел.

    Месяц словами берём из своей таблицы, а не из strftime: тот пишет
    на языке системы, и получалось «26 agosto» под русской погодой.
    """
    dlinnaya, korotkaya, mesyacem, dm = PORYADKI.get(
        str(_vybor("date", prefs.get("units.date", "system"))).lower(),
        PORYADKI["dmy"])
    if slovami:
        yaz = _yazyk_temy()
        mesyac = MESYACY[yaz][dt.month - 1]
        # Месяц вперёд числа встаёт только там, где так говорят,
        # и только если так выбрано в настройках.
        if yaz in MESYAC_MOZHET_VPERED and not mesyacem.startswith("%d"):
            return "{} {}".format(mesyac, dt.day)
        return DATA_SLOVAMI[yaz].format(den=dt.day, mesyac=mesyac)
    if bez_goda:
        return dt.strftime(dm)
    return dt.strftime(korotkaya if korotko else dlinnaya)


def den_slovom(dt):
    """Название дня недели на языке темы."""
    return DNI_NEDELI[_yazyk_temy()][dt.weekday()]


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
    # Без года: панели он не нужен, а место занимает.
    snap["date_dm"] = data(now, bez_goda=True)
    snap["weekday"] = den_slovom(now)
    snap["day_index"] = den_nedeli(now)
    snap["deg"] = znak()
    snap["wind_unit"] = znak_vetra()
    # Слова погоды приходят из таблицы WMO сразу на двух языках. Какое
    # показать, решаем ЗДЕСЬ, а не при запросе прогноза: язык темы
    # переключается мгновенно, а следующего прогноза ждать четверть часа,
    # и без сети его можно не дождаться вовсе.
    yaz = yazyk.yazyk_temy()
    for klyuch in ("weather", "weather_full", "weather_fit"):
        gotovo = snap.get(klyuch + "_" + yaz) or snap.get(klyuch + "_en")
        if gotovo:
            snap[klyuch] = gotovo
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

    Ветер смотрим всегда, а не только при смене меры: подпись зависит
    ещё и от языка, и «км/ч» в английской теме держалось до тех пор,
    пока человек не переключит заодно и километры на мили.
    """
    if not isinstance(shablon, str):
        return shablon
    if shkala() != "c":
        shablon = shablon.replace("°C", "°F").replace("°c", "°f")
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
