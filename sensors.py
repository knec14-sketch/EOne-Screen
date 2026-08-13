#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Сбор показаний железа и погоды.
#  Часть проекта EOne screen — открытой замены штатной программе
#  для экранов на контроллере TXW818.
#
#  Автор: EOne
#  Лицензия: CC BY-NC-SA 4.0 — использование в коммерческих целях
#  запрещено без письменного разрешения автора. См. файл LICENSE.
#
"""
sensors.py - сбор данных о железе для панели.

Источники и что от них берётся:

  psutil          загрузка процессора, память, диски, сеть, время работы
  nvidia-smi      всё по видеокарте Nvidia (идёт в комплекте с драйвером)
  LibreHardware   температура процессора (нужна запущенная LibreHardwareMonitor
    Monitor       с включённым в её настройках WMI)

Если источник недоступен, значение становится "нет данных" и на панели
рисуется прочерк. Программа при этом продолжает работать.
"""

import atexit
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

try:
    import psutil
except ImportError:
    psutil = None

# Датчики молчат на любом языке, кроме одного места: describe() пишет
# для человека, и её показывают в окне и при осмотре машины.
from yazyk import t

import edinicy


IS_WINDOWS = sys.platform.startswith("win")

# чтобы вызовы nvidia-smi и powershell не мигали чёрными окошками
_NO_WINDOW = {}
if IS_WINDOWS:
    _NO_WINDOW = dict(creationflags=0x08000000)  # CREATE_NO_WINDOW


class Missing:
    """Заглушка для значения, которого нет.

    Умеет подставляться в строку с любым форматом, выдавая прочерк,
    поэтому шаблон вида {cpu_temp:.0f} не ломается, когда датчик молчит.
    """
    text = "--"

    def __format__(self, spec):
        return self.text

    def __str__(self):
        return self.text

    def __float__(self):
        return 0.0

    def __bool__(self):
        return False


MISSING = Missing()


def temp_priority(name):
    """Насколько датчик подходит на роль общей температуры процессора.

    Меньше - лучше. Имена у AMD и Intel разные, поэтому здесь оба ряда.

    У Ryzen рядом живут несколько похожих датчиков: Core (Tctl/Tdie) -
    усреднённый по кристаллу, именно его показывает штатная программа;
    CCD1 (Tdie) - отдельный кристалл, скачет сильнее; Core #1..#16 -
    отдельные ядра, скачут ещё сильнее.

    У Intel общий датчик называется CPU Package, рядом лежат Core Max,
    Core Average и отдельные ядра. Ещё есть Distance to TjMax - это
    не температура вовсе, а запас до предела, и брать его нельзя.
    """
    low = (name or "").lower()
    if "tjmax" in low or "distance" in low:
        return 99                       # запас до предела, а не температура
    if "tctl" in low and "tdie" in low:
        return 0
    if "tctl" in low or "tdie" in low:
        return 1
    if "package" in low:
        return 2                        # так называется общий датчик у Intel
    if "ccd" in low:
        return 4
    if "core" in low and ("max" in low or "average" in low or "avg" in low):
        return 5
    if "core" in low:
        return 6
    return 9


def windows_light_theme():
    """Светлое ли оформление выбрано в самой Windows.

    True - светлое, False - тёмное, None - выяснить не удалось.
    Чтение стоит около сотой доли миллисекунды, так что спрашивать
    можно хоть каждую секунду.
    """
    if not IS_WINDOWS:
        return None
    try:
        import winreg
        key = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            return bool(winreg.QueryValueEx(k, "AppsUseLightTheme")[0])
    except Exception:
        return None


# Код погоды - это номер состояния, а не шкала: между «ясно» и «гроза»
# нет середины, по нему нельзя плавно тянуть. Поэтому раскладываем его
# на несколько долей от 0 до 1: сколько сейчас облаков, сколько солнца,
# идёт ли гроза. По таким долям тема уже может плавно меняться.
SKY = {
    #  код: (ясно, облака, серость, дождь, снег, гроза, туман)
    0:  (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    1:  (0.8, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0),
    2:  (0.4, 0.6, 0.1, 0.0, 0.0, 0.0, 0.0),
    3:  (0.0, 1.0, 0.6, 0.0, 0.0, 0.0, 0.15),
    45: (0.0, 0.7, 1.0, 0.0, 0.0, 0.0, 1.0),
    48: (0.0, 0.7, 1.0, 0.0, 0.0, 0.0, 1.0),
    51: (0.1, 0.8, 0.5, 0.3, 0.0, 0.0, 0.2),
    53: (0.0, 0.9, 0.6, 0.5, 0.0, 0.0, 0.25),
    55: (0.0, 1.0, 0.7, 0.7, 0.0, 0.0, 0.3),
    56: (0.0, 0.9, 0.7, 0.6, 0.2, 0.0, 0.0),
    57: (0.0, 1.0, 0.8, 0.8, 0.3, 0.0, 0.0),
    61: (0.1, 0.9, 0.6, 0.6, 0.0, 0.0, 0.0),
    63: (0.0, 1.0, 0.7, 0.8, 0.0, 0.0, 0.0),
    65: (0.0, 1.0, 0.9, 1.0, 0.0, 0.0, 0.0),
    66: (0.0, 1.0, 0.8, 0.8, 0.3, 0.0, 0.0),
    67: (0.0, 1.0, 0.9, 1.0, 0.4, 0.0, 0.0),
    71: (0.1, 0.9, 0.6, 0.0, 0.6, 0.0, 0.2),
    73: (0.0, 1.0, 0.7, 0.0, 0.8, 0.0, 0.3),
    75: (0.0, 1.0, 0.9, 0.0, 1.0, 0.0, 0.4),
    77: (0.0, 0.9, 0.7, 0.0, 0.7, 0.0, 0.25),
    80: (0.3, 0.8, 0.4, 0.6, 0.0, 0.0, 0.0),
    81: (0.1, 0.9, 0.6, 0.8, 0.0, 0.0, 0.0),
    82: (0.0, 1.0, 0.8, 1.0, 0.0, 0.0, 0.0),
    85: (0.1, 0.9, 0.6, 0.0, 0.8, 0.0, 0.0),
    86: (0.0, 1.0, 0.8, 0.0, 1.0, 0.0, 0.0),
    95: (0.0, 1.0, 0.9, 0.8, 0.0, 1.0, 0.0),
    96: (0.0, 1.0, 1.0, 0.9, 0.2, 1.0, 0.0),
    99: (0.0, 1.0, 1.0, 1.0, 0.3, 1.0, 0.0),
}
SKY_KEYS = ("sky_clear", "sky_clouds", "sky_grey", "sky_rain", "sky_snow",
            "sky_storm", "sky_fog")


def sky_parts(code):
    """Разложить код погоды на доли от 0 до 1."""
    try:
        vals = SKY[int(code)]
    except (KeyError, TypeError, ValueError):
        vals = (0.5, 0.5, 0.3, 0.0, 0.0, 0.0, 0.0)  # не знаем - берём среднее
    return dict(zip(SKY_KEYS, vals))


def _check_admin():
    """Запущены ли мы с правами администратора."""
    if not IS_WINDOWS:
        return os.geteuid() == 0 if hasattr(os, "geteuid") else False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _run(cmd, timeout=4):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=timeout, **_NO_WINDOW)
        if out.returncode == 0:
            return out.stdout
    except Exception:
        pass
    return None


def _powershell(script, timeout=10):
    return _run(["powershell", "-NoProfile", "-NonInteractive",
                 "-Command", script], timeout=timeout)


# --- как называется железо ---------------------------------------------------

# Производители пишут в название всё подряд: значки правообладателя,
# число ядер, частоту. На панели это не нужно - там важно само имя.
_MUSOR = (
    "(R)", "(r)", "(TM)", "(tm)", "(C)", "(c)",
    " CPU", " Processor", " processor", " with Radeon Graphics",
)


def tidy_name(name):
    """Убрать из названия железа канцелярию производителя."""
    s = " ".join(str(name or "").split())
    if not s:
        return ""
    # «... 16-Core Processor» и «... @ 3.60GHz» - подробности, не имя
    for razdel in (" 4-Core", " 6-Core", " 8-Core", " 10-Core", " 12-Core",
                   " 16-Core", " 24-Core", " 32-Core", " 64-Core", " @ "):
        i = s.find(razdel)
        if i > 0:
            s = s[:i]
    for m in _MUSOR:
        s = s.replace(m, "")
    return " ".join(s.split())


_names = {}


def cpu_name():
    """Название процессора. Спрашиваем один раз: оно не меняется."""
    if "cpu" in _names:
        return _names["cpu"]
    got = ""
    if IS_WINDOWS:
        # В реестре имя лежит готовым, и читается оно мгновенно -
        # ни PowerShell, ни сторонних библиотек не нужно.
        try:
            import winreg
            key = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as k:
                got = winreg.QueryValueEx(k, "ProcessorNameString")[0]
        except Exception:
            got = ""
    if not got:
        try:
            import platform
            got = platform.processor() or ""
        except Exception:
            got = ""
    _names["cpu"] = tidy_name(got)
    return _names["cpu"]


def gpu_name():
    """Название видеокарты. Сначала спрашиваем Nvidia, потом саму Windows."""
    if "gpu" in _names:
        return _names["gpu"]
    got = _run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
    if got and got.strip():
        got = got.strip().splitlines()[0]
    elif IS_WINDOWS:
        # У ноутбуков карт бывает две; берём ту, у которой больше памяти -
        # это и есть игровая, а не встроенная в процессор
        out = _powershell(
            "Get-CimInstance Win32_VideoController | "
            "Sort-Object AdapterRAM -Descending | "
            "Select-Object -First 1 -ExpandProperty Name")
        got = (out or "").strip().splitlines()[0] if (out or "").strip() else ""
    else:
        got = ""
    _names["gpu"] = tidy_name(got)
    return _names["gpu"]


def gpu_vendor(name=None):
    """Кто сделал видеокарту: nvidia, amd, intel или пусто."""
    low = (name if name is not None else gpu_name()).lower()
    if "nvidia" in low or "geforce" in low or "rtx" in low or "gtx" in low \
            or "quadro" in low:
        return "nvidia"
    if "radeon" in low or "amd" in low:
        return "amd"
    if "intel" in low or "arc" in low:
        return "intel"
    return ""


# --- погода -----------------------------------------------------------------

# Коды погоды по стандарту ВМО, которые отдаёт Open-Meteo.
# Для каждого - краткое и подробное описание.
WMO = {
    0:  ("Ясно", "Ясно"),
    1:  ("Ясно", "В основном ясно"),
    2:  ("Облачно", "Переменная облачность"),
    3:  ("Пасмурно", "Пасмурно"),
    45: ("Туман", "Туман"),
    48: ("Туман", "Изморозь"),
    51: ("Морось", "Слабая морось"),
    53: ("Морось", "Морось"),
    55: ("Морось", "Сильная морось"),
    56: ("Гололёд", "Ледяная морось"),
    57: ("Гололёд", "Сильная ледяная морось"),
    61: ("Дождь", "Небольшой дождь"),
    63: ("Дождь", "Дождь"),
    65: ("Ливень", "Сильный дождь"),
    66: ("Гололёд", "Ледяной дождь"),
    67: ("Гололёд", "Сильный ледяной дождь"),
    71: ("Снег", "Небольшой снег"),
    73: ("Снег", "Снег"),
    75: ("Снегопад", "Сильный снег"),
    77: ("Снег", "Снежная крупа"),
    80: ("Ливень", "Небольшой ливень"),
    81: ("Ливень", "Ливень"),
    82: ("Ливень", "Сильный ливень"),
    85: ("Снег", "Снежный заряд"),
    86: ("Снегопад", "Сильный снежный заряд"),
    95: ("Гроза", "Гроза"),
    96: ("Гроза", "Гроза с градом"),
    99: ("Гроза", "Сильная гроза с градом"),
}


# Те же коды по-английски.
WMO_EN = {
    0:  ("Clear", "Clear sky"),
    1:  ("Clear", "Mainly clear"),
    2:  ("Cloudy", "Partly cloudy"),
    3:  ("Overcast", "Overcast"),
    45: ("Fog", "Fog"),
    48: ("Fog", "Rime fog"),
    51: ("Drizzle", "Light drizzle"),
    53: ("Drizzle", "Drizzle"),
    55: ("Drizzle", "Heavy drizzle"),
    56: ("Freezing", "Freezing drizzle"),
    57: ("Freezing", "Heavy freezing drizzle"),
    61: ("Rain", "Light rain"),
    63: ("Rain", "Rain"),
    65: ("Heavy rain", "Heavy rain"),
    66: ("Freezing", "Freezing rain"),
    67: ("Freezing", "Heavy freezing rain"),
    71: ("Snow", "Light snow"),
    73: ("Snow", "Snow"),
    75: ("Snowfall", "Heavy snow"),
    77: ("Snow", "Snow grains"),
    80: ("Showers", "Light showers"),
    81: ("Showers", "Showers"),
    82: ("Showers", "Heavy showers"),
    85: ("Snow", "Snow showers"),
    86: ("Snowfall", "Heavy snow showers"),
    95: ("Storm", "Thunderstorm"),
    96: ("Storm", "Thunderstorm with hail"),
    99: ("Storm", "Severe thunderstorm with hail"),
}

WEATHER_CONF = "weather.json"

# Откуда берётся прогноз. Open-Meteo не требует ни ключа, ни регистрации.
ISTOCHNIK = "https://api.open-meteo.com/v1/forecast"

# Кто спрашивает. Норвежская служба без этого отвечает отказом, и это
# не каприз: они просят называться, чтобы было кому написать, если
# программа начнёт долбить их сервер.
AGENT = "EOne screen (open source, github)"


# --- переходники к чужим источникам погоды -----------------------------------
#
# Внутри программы погода живёт кодами ВМО: по ним разложены доли неба,
# по ним темы решают, идёт дождь или метёт снег. Чужие службы отдают свои
# номера состояний и свои имена полей, поэтому между ними и панелью стоит
# переходник - табличка, где написано:
#
#   zapros  что приписать к ссылке; {lat}, {lon} и {key} подставляются
#   polya   где в ответе лежит каждое значение, путь через точку
#   veter   в чём меряется ветер: km/h, m/s или mph
#   vremya  в каком виде восход и закат: iso, unix, 12h или нет вовсе
#   kody    по какой таблице переводить номер состояния в код ВМО
#
# Тот же вид описания можно положить в weather.json под именем "своё" -
# тогда новую службу подключают без единой строчки кода.

# OpenWeatherMap: номера состояний идут рядами, разбираем по началу.
KODY_OPENWEATHER = (
    (200, 232, 95),      # гроза
    (300, 321, 53),      # морось
    (500, 501, 61),      # небольшой дождь
    (502, 504, 65),      # сильный дождь
    (511, 511, 66),      # ледяной дождь
    (520, 521, 80),      # ливень
    (522, 531, 82),      # сильный ливень
    (600, 600, 71),      # небольшой снег
    (601, 601, 73),
    (602, 602, 75),
    (611, 616, 66),      # мокрый снег
    (620, 622, 85),      # снежные заряды
    (701, 741, 45),      # дымка, туман
    (751, 771, 3),       # песок, пыль, шквал
    (781, 781, 99),      # смерч
    (800, 800, 0),       # ясно
    (801, 801, 1),
    (802, 802, 2),
    (803, 804, 3),
)

# WeatherAPI: у каждого состояния свой номер, рядов нет
KODY_WEATHERAPI = {
    1000: 0, 1003: 2, 1006: 3, 1009: 3,
    1030: 45, 1135: 45, 1147: 45,
    1063: 61, 1150: 51, 1153: 53, 1180: 61, 1183: 61, 1186: 63, 1189: 63,
    1192: 65, 1195: 65, 1240: 80, 1243: 81, 1246: 82,
    1066: 71, 1114: 75, 1117: 75, 1210: 71, 1213: 71, 1216: 73, 1219: 73,
    1222: 75, 1225: 75, 1255: 85, 1258: 86,
    1069: 66, 1072: 56, 1168: 56, 1171: 57, 1198: 66, 1201: 67,
    1204: 66, 1207: 67, 1237: 77, 1249: 66, 1252: 67, 1261: 77, 1264: 77,
    1087: 95, 1273: 95, 1276: 96, 1279: 95, 1282: 96,
}

# met.no: состояние приходит словом. Хвосты _day, _night и _polartwilight
# отрезаются при разборе - для панели важно, что идёт с неба, а день
# или ночь она знает и сама.
KODY_METNO = {
    "clearsky": 0, "fair": 1, "partlycloudy": 2, "cloudy": 3,
    "fog": 45,
    "lightrain": 61, "rain": 63, "heavyrain": 65,
    "lightrainshowers": 80, "rainshowers": 81, "heavyrainshowers": 82,
    "lightsleet": 66, "sleet": 66, "heavysleet": 67,
    "lightsleetshowers": 66, "sleetshowers": 66, "heavysleetshowers": 67,
    "lightsnow": 71, "snow": 73, "heavysnow": 75,
    "lightsnowshowers": 85, "snowshowers": 85, "heavysnowshowers": 86,
    "lightrainandthunder": 95, "rainandthunder": 95,
    "heavyrainandthunder": 96, "thunderstorm": 95,
    "lightrainshowersandthunder": 95, "rainshowersandthunder": 95,
    "heavyrainshowersandthunder": 96,
    "lightsnowandthunder": 95, "snowandthunder": 95,
    "heavysnowandthunder": 96, "lightsleetandthunder": 95,
    "sleetandthunder": 95, "heavysleetandthunder": 96,
    "lightssleetshowersandthunder": 95, "sleetshowersandthunder": 95,
    "heavysleetshowersandthunder": 96,
    "lightssnowshowersandthunder": 95, "snowshowersandthunder": 95,
    "heavysnowshowersandthunder": 96,
}

# wttr.in отдаёт коды World Weather Online - свой ряд, ни на что
# не похожий.
KODY_WWO = {
    113: 0, 116: 2, 119: 3, 122: 3,
    143: 45, 248: 45, 260: 45,
    176: 80, 293: 61, 296: 61, 299: 63, 302: 63, 305: 65, 308: 65,
    311: 66, 314: 67, 317: 66, 320: 71, 323: 71, 326: 71,
    329: 73, 332: 73, 335: 75, 338: 75,
    350: 77, 353: 80, 356: 81, 359: 82,
    362: 66, 365: 66, 368: 85, 371: 86, 374: 66, 377: 67,
    179: 71, 182: 66, 185: 66,
    200: 95, 386: 95, 389: 96, 392: 95, 395: 96,
    227: 73, 230: 75, 264: 51, 266: 51, 281: 56, 284: 57,
}

PEREHODNIKI = {
    "open-meteo": {
        "imya": "Open-Meteo",
        "base": ISTOCHNIK,
        "klyuch": False,
        "zapros": ("latitude={lat:.4f}&longitude={lon:.4f}"
                   "&current=temperature_2m,apparent_temperature,"
                   "relative_humidity_2m,wind_speed_10m,weather_code"
                   "&daily=temperature_2m_max,temperature_2m_min,"
                   "sunrise,sunset&timezone=auto&forecast_days=1"),
        "polya": {
            "temp": "current.temperature_2m",
            "feels": "current.apparent_temperature",
            "humidity": "current.relative_humidity_2m",
            "wind": "current.wind_speed_10m",
            "code": "current.weather_code",
            "max": "daily.temperature_2m_max.0",
            "min": "daily.temperature_2m_min.0",
            "sunrise": "daily.sunrise.0",
            "sunset": "daily.sunset.0",
        },
        "veter": "km/h",
        "vremya": "iso",
        "kody": None,                 # уже коды ВМО, переводить нечего
    },
    "openweather": {
        "imya": "OpenWeatherMap",
        "base": "https://api.openweathermap.org/data/2.5/weather",
        "klyuch": True,
        "zapros": "lat={lat:.4f}&lon={lon:.4f}&units=metric&appid={key}",
        "polya": {
            "temp": "main.temp",
            "feels": "main.feels_like",
            "humidity": "main.humidity",
            "wind": "wind.speed",
            "code": "weather.0.id",
            "max": "main.temp_max",
            "min": "main.temp_min",
            "sunrise": "sys.sunrise",
            "sunset": "sys.sunset",
        },
        "veter": "m/s",
        "vremya": "unix",
        "kody": "openweather",
    },
    "weatherapi": {
        "imya": "WeatherAPI",
        "base": "https://api.weatherapi.com/v1/forecast.json",
        "klyuch": True,
        "zapros": "q={lat:.4f},{lon:.4f}&days=1&aqi=no&alerts=no&key={key}",
        "polya": {
            "temp": "current.temp_c",
            "feels": "current.feelslike_c",
            "humidity": "current.humidity",
            "wind": "current.wind_kph",
            "code": "current.condition.code",
            "max": "forecast.forecastday.0.day.maxtemp_c",
            "min": "forecast.forecastday.0.day.mintemp_c",
            "sunrise": "forecast.forecastday.0.astro.sunrise",
            "sunset": "forecast.forecastday.0.astro.sunset",
        },
        "veter": "km/h",
        "vremya": "12h",
        "kody": "weatherapi",
    },
    # Норвежский метеорологический институт. Ключа не просит, но просит
    # назваться - см. AGENT. Восхода и заката не даёт вовсе: панель
    # считает их сама по координатам.
    "metno": {
        "imya": "met.no",
        "base": "https://api.met.no/weatherapi/locationforecast/2.0/compact",
        "klyuch": False,
        "zapros": "lat={lat:.4f}&lon={lon:.4f}",
        "polya": {
            "temp": "properties.timeseries.0.data.instant.details."
                    "air_temperature",
            "humidity": "properties.timeseries.0.data.instant.details."
                        "relative_humidity",
            "wind": "properties.timeseries.0.data.instant.details."
                    "wind_speed",
            "code": "properties.timeseries.0.data.next_1_hours.summary."
                    "symbol_code",
        },
        "veter": "m/s",
        "vremya": "iso",
        "kody": "metno",
    },
    # wttr.in: ключа не просит, отвечает коротко и понятно.
    "wttr": {
        "imya": "wttr.in",
        "base": "https://wttr.in/{lat:.4f},{lon:.4f}",
        "klyuch": False,
        "zapros": "format=j1",
        "polya": {
            "temp": "current_condition.0.temp_C",
            "feels": "current_condition.0.FeelsLikeC",
            "humidity": "current_condition.0.humidity",
            "wind": "current_condition.0.windspeedKmph",
            "code": "current_condition.0.weatherCode",
            "max": "weather.0.maxtempC",
            "min": "weather.0.mintempC",
            "sunrise": "weather.0.astronomy.0.sunrise",
            "sunset": "weather.0.astronomy.0.sunset",
        },
        "veter": "km/h",
        "vremya": "12h",
        "kody": "wwo",
    },
    # Чужая служба, описанная человеком. Пустое описание - заготовка:
    # всё, что здесь стоит, перебивается source_map из weather.json.
    "svoy": {
        "imya": "свой источник",
        "base": "",
        "klyuch": False,
        "zapros": "",
        "polya": {},
        "veter": "km/h",
        "vremya": "iso",
        "kody": None,
    },
}

VETER_V_KMH = {"km/h": 1.0, "kmh": 1.0, "kph": 1.0,
               "m/s": 3.6, "ms": 3.6,
               "mph": 1.609344}


def perehodnik(conf):
    """Описание источника, который выбран в настройках.

    Своё описание в weather.json перебивает готовое: так новую службу
    можно подключить, не трогая код.
    """
    vid = str((conf or {}).get("source_kind") or "open-meteo").lower()
    svoyo = (conf or {}).get("source_map")
    if isinstance(svoyo, dict) and svoyo.get("polya"):
        gotovo = dict(PEREHODNIKI.get(vid, PEREHODNIKI["open-meteo"]))
        gotovo.update(svoyo)
        return gotovo
    return dict(PEREHODNIKI.get(vid, PEREHODNIKI["open-meteo"]))


def dostat(dannye, put):
    """Значение по пути через точку: «current.temp», «weather.0.id»."""
    uzel = dannye
    for shag in str(put or "").split("."):
        if uzel is None:
            return None
        if isinstance(uzel, list):
            try:
                uzel = uzel[int(shag)]
            except (ValueError, IndexError):
                return None
        elif isinstance(uzel, dict):
            if shag not in uzel:
                return None
            uzel = uzel[shag]
        else:
            return None
    return uzel


def sprosit(url, timeout=12):
    """Спросить службу и вернуть разобранный ответ.

    Одно место на все запросы, потому что двум вещам надо угодить сразу:

      * met.no отказывает без подписи - кто спрашивает. Правило у них
        прямое: назовись, иначе 403;
      * у части служб цепочка сертификатов не лежит в хранилище Windows,
        и Python отказывается им верить. Тогда берём список из certifi,
        если он рядом есть.
    """
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            raise
        import ssl
        try:
            import certifi
        except ImportError:
            raise
        ctx = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return json.loads(r.read().decode("utf-8"))


def puti(dannye, koren="", glubina=6):
    """Все пути к простым значениям в ответе службы.

    Нужны, чтобы человеку не пришлось изучать чужой JSON: программа
    спрашивает службу один раз, раскладывает ответ на пути вроде
    «current.temp_c», и в окне остаётся выбрать из списка, где что
    лежит. Списки берём только с начала - у прогноза на неделю это
    сегодняшний день, а остальные семьсот путей лишь мешают.

    Глубина шесть, а не меньше: восход у wttr.in лежит на пятом уровне,
    «weather.0.astronomy.0.sunrise», и на четырёх его не видно.
    """
    out = []
    if glubina <= 0:
        return out
    if isinstance(dannye, dict):
        for k, v in dannye.items():
            out += puti(v, "{}.{}".format(koren, k) if koren else str(k),
                        glubina - 1)
    elif isinstance(dannye, list):
        for i, v in enumerate(dannye[:2]):
            out += puti(v, "{}.{}".format(koren, i), glubina - 1)
    elif isinstance(dannye, (int, float, str)) and koren:
        out.append(koren)
    return out


def syroy_otvet(url, latitude, longitude, kind=None, key=None, karta=None):
    """Спросить службу и вернуть её ответ как есть, не разбирая."""
    conf = {"source": url, "source_kind": kind or "svoy",
            "source_key": key or "", "source_map": karta or {}}
    return sprosit(weather_url(conf, latitude, longitude))


def v_wmo(code, tablica):
    """Состояние погоды чужой службы - в код ВМО.

    Состояние приходит не только числом: норвежцы шлют слово вроде
    «partlycloudy_day». Поэтому сначала ищем по слову, и только потом
    разбираем число.
    """
    if isinstance(tablica, dict):
        klyuch = str(code).strip().lower()
        if klyuch in tablica:
            return int(tablica[klyuch])
    if tablica == "metno":
        slovo = str(code).strip().lower()
        for hvost in ("_day", "_night", "_polartwilight"):
            if slovo.endswith(hvost):
                slovo = slovo[:-len(hvost)]
                break
        return KODY_METNO.get(slovo, -1)
    try:
        code = int(code)
    except (TypeError, ValueError):
        return -1
    if not tablica:
        return code
    if tablica == "wwo":
        return KODY_WWO.get(code, -1)
    if tablica == "openweather":
        for ot, do, wmo in KODY_OPENWEATHER:
            if ot <= code <= do:
                return wmo
        return -1
    if tablica == "weatherapi":
        return KODY_WEATHERAPI.get(code, -1)
    if isinstance(tablica, dict):
        # своя таблица из weather.json: ключи там строками
        return int(tablica.get(str(code), tablica.get(code, -1)))
    return -1


def _chas(znachenie, vid, kogda=None):
    """Восход или закат в datetime. Не разобрали - None."""
    if znachenie is None:
        return None
    kogda = kogda or datetime.now()
    try:
        if vid == "unix":
            return datetime.fromtimestamp(float(znachenie))
        s = str(znachenie).strip()
        if vid == "iso":
            return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")
        if vid == "12h":
            chas = datetime.strptime(s.upper().replace(".", ""), "%I:%M %p")
            return kogda.replace(hour=chas.hour, minute=chas.minute,
                                 second=0, microsecond=0)
        if vid == "24h":
            chas = datetime.strptime(s[:5], "%H:%M")
            return kogda.replace(hour=chas.hour, minute=chas.minute,
                                 second=0, microsecond=0)
    except (ValueError, TypeError, OSError, OverflowError):
        return None
    return None


def solnce(latitude, longitude, kogda=None):
    """Свои восход и закат, по широте и долготе.

    Нужны, когда служба погоды их не отдаёт: без восхода и заката панель
    не знает, когда переключаться с ночного вида на дневной. Считаем
    сами - обычная астрономическая формула, точность около минуты,
    для смены вида этого более чем достаточно.
    """
    import math
    kogda = kogda or datetime.now()
    den = kogda.timetuple().tm_yday
    shirota = math.radians(float(latitude))

    # склонение солнца и уравнение времени
    g = 2 * math.pi / 365.0 * (den - 1 + (kogda.hour - 12) / 24.0)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g)
                       - 0.032077 * math.sin(g)
                       - 0.014615 * math.cos(2 * g)
                       - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
            - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))

    # часовой угол на высоте -0.833 градуса: край солнца у горизонта
    cos_ha = ((math.cos(math.radians(90.833)) / (math.cos(shirota)
                                                 * math.cos(decl)))
              - math.tan(shirota) * math.tan(decl))
    if cos_ha > 1:
        return None, None            # полярная ночь: солнце не встаёт
    if cos_ha < -1:
        return None, None            # полярный день: солнце не садится
    ha = math.degrees(math.acos(cos_ha))

    # Часовой пояс берём у самой машины: время на панели местное,
    # и восход должен быть в тех же часах, что и часы в углу.
    smeshenie = -time.timezone / 60.0
    if time.daylight and time.localtime().tm_isdst > 0:
        smeshenie = -time.altzone / 60.0

    def v_chas(minuty):
        minuty = minuty % 1440
        return kogda.replace(hour=int(minuty // 60), minute=int(minuty % 60),
                             second=0, microsecond=0)

    voshod = 720 - 4 * (float(longitude) + ha) - eqtime + smeshenie
    zakat = 720 - 4 * (float(longitude) - ha) - eqtime + smeshenie
    return v_chas(voshod), v_chas(zakat)


def weather_url(conf, latitude, longitude):
    """Полная ссылка на прогноз для этого места."""
    import urllib.parse
    vid = perehodnik(conf)
    base = str((conf or {}).get("source") or vid.get("base")
               or ISTOCHNIK).strip() or ISTOCHNIK
    # Ключ пришёл от человека и попадает прямо в адрес. Пробел или
    # русская буква, случайно в нём оказавшиеся, роняли бы запрос
    # непонятной жалобой на кодировку - поэтому экранируем.
    klyuch = urllib.parse.quote(str((conf or {}).get("source_key", "")),
                                safe="")
    # Свой адрес человек пишет целиком и сам расставляет в нём {lat},
    # {lon} и {key}. Чужие адреса фигурных скобок не содержат, поэтому
    # подставляем только когда они есть, и молча оставляем как есть,
    # если в скобках оказалось что-то незнакомое.
    if "{" in base:
        try:
            base = base.format(lat=float(latitude), lon=float(longitude),
                               key=klyuch)
        except (KeyError, IndexError, ValueError):
            pass
    zapros = str(vid.get("zapros", "")).format(
        lat=float(latitude), lon=float(longitude), key=klyuch)
    if not zapros:
        return base
    znak = "&" if "?" in base else "?"
    return base + znak + zapros


def razobrat_pogodu(dannye, vid, kogda=None):
    """Вытащить из ответа службы то, что нужно панели.

    Возвращает готовый набор значений. Чего в ответе нет - того нет
    и в наборе: пусть лучше на панели будет прочерк, чем выдуманный ноль.
    """
    polya = vid.get("polya") or {}
    k = VETER_V_KMH.get(str(vid.get("veter", "km/h")).lower(), 1.0)
    out = {}

    syroy = dostat(dannye, polya.get("code"))
    if syroy is None:
        raise ValueError("в ответе нет состояния погоды ({})"
                         .format(polya.get("code")))
    code = v_wmo(syroy, vid.get("kody"))
    if code < 0:
        raise ValueError("состояние {} этой службе известно, а нам нет"
                         .format(syroy))
    out["weather_code"] = code

    for imya, klyuch, mera in (("weather_temp", "temp", 1.0),
                               ("weather_feels", "feels", 1.0),
                               ("weather_humidity", "humidity", 1.0),
                               ("weather_wind", "wind", k),
                               ("weather_max", "max", 1.0),
                               ("weather_min", "min", 1.0)):
        znach = dostat(dannye, polya.get(klyuch))
        if znach is None:
            continue
        try:
            out[imya] = float(znach) * mera
        except (TypeError, ValueError):
            continue
    if "weather_temp" not in out:
        raise ValueError("в ответе нет температуры ({})"
                         .format(polya.get("temp")))
    if "weather_feels" not in out:
        out["weather_feels"] = out["weather_temp"]

    chasy = str(vid.get("vremya", "iso")).lower()
    voshod = _chas(dostat(dannye, polya.get("sunrise")), chasy, kogda)
    zakat = _chas(dostat(dannye, polya.get("sunset")), chasy, kogda)
    return out, voshod, zakat


def save_source(url, kind=None, key=None, karta=None):
    """Записать источник погоды. Пусто - вернуть обычный Open-Meteo.

    karta - своё описание чужого ответа: где в нём лежит температура,
    ветер и всё остальное. Пустое описание убирается, чтобы вернуться
    к готовому переходнику было одной кнопкой.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, WEATHER_CONF)
    try:
        with open(path, encoding="utf-8") as f:
            conf = json.load(f)
    except Exception:
        conf = {}
    url = (url or "").strip()
    if url:
        conf["source"] = url
    else:
        conf.pop("source", None)
    if kind:
        conf["source_kind"] = kind
    if key is not None:
        if str(key).strip():
            conf["source_key"] = str(key).strip()
        else:
            conf.pop("source_key", None)
    if karta is not None:
        if isinstance(karta, dict) and karta.get("polya"):
            conf["source_map"] = karta
        else:
            conf.pop("source_map", None)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(conf, f, ensure_ascii=False, indent=2)
    return conf


def try_source(url, latitude, longitude, kind=None, key=None, karta=None):
    """Спросить источник один раз и рассказать, что он ответил."""
    import urllib.request
    conf = {"source": url, "source_kind": kind or "open-meteo",
            "source_key": key or "", "source_map": karta or {}}
    vid = perehodnik(conf)
    if vid.get("klyuch") and not str(key or "").strip():
        raise ValueError("этой службе нужен ключ, а он не задан")
    dannye = sprosit(weather_url(conf, latitude, longitude))
    vals, voshod, zakat = razobrat_pogodu(dannye, vid)
    code = vals["weather_code"]
    return {"temp": vals["weather_temp"],
            "wind": vals.get("weather_wind", 0.0),
            "code": code,
            "sunrise": voshod,
            "source": vid.get("imya", ""),
            "text": WMO.get(code, ("—", "нет данных"))[1]}


def _weather_config():
    """Координаты для прогноза. Если их нет - определяем по адресу в сети."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, WEATHER_CONF)
    conf = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                conf = json.load(f)
        except Exception:
            conf = {}

    if conf.get("latitude") is None or conf.get("longitude") is None:
        try:
            import urllib.request
            with urllib.request.urlopen(
                    "http://ip-api.com/json/?fields=lat,lon,city", timeout=6) as r:
                d = json.loads(r.read().decode("utf-8"))
            conf["latitude"] = d.get("lat")
            conf["longitude"] = d.get("lon")
            conf.setdefault("city", d.get("city", ""))
        except Exception:
            pass

    conf.setdefault("latitude", None)
    conf.setdefault("longitude", None)
    conf.setdefault("city", "")
    conf.setdefault("language", "ru")   # ru или en
    conf.setdefault("update_minutes", 15)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(conf, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return conf


def find_places(name, limit=6, language="ru"):
    """Найти город по названию. Ключ не нужен, сервис тот же, что и погода."""
    import urllib.parse, urllib.request
    url = ("https://geocoding-api.open-meteo.com/v1/search?name={}"
           "&count={}&language={}&format=json").format(
               urllib.parse.quote(name), int(limit), language)
    with urllib.request.urlopen(url, timeout=8) as r:
        data = json.loads(r.read().decode("utf-8"))
    out = []
    for p in data.get("results") or []:
        where = ", ".join(x for x in (p.get("admin1"), p.get("country")) if x)
        out.append({"city": p.get("name", ""), "where": where,
                    "latitude": p.get("latitude"),
                    "longitude": p.get("longitude")})
    return out


def save_location(latitude, longitude, city="", language=None,
                  update_minutes=None):
    """Записать координаты в weather.json рядом с программой."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, WEATHER_CONF)
    conf = {}
    try:
        with open(path, encoding="utf-8") as f:
            conf = json.load(f)
    except Exception:
        conf = {}
    conf["latitude"] = float(latitude)
    conf["longitude"] = float(longitude)
    conf["city"] = city or conf.get("city", "")
    if language:
        conf["language"] = language
    if update_minutes:
        conf["update_minutes"] = int(update_minutes)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(conf, f, ensure_ascii=False, indent=2)
    return conf


class Sensors:
    """Опрашивает железо в фоновых потоках и отдаёт готовый набор значений."""

    def __init__(self, net_interface=None):
        self.lock = threading.Lock()
        self.data = {}
        self.net_interface = net_interface
        self._stop = threading.Event()
        self._last_net = None
        self._last_net_t = None

        self.has_nvidia = _run(["nvidia-smi", "--version"]) is not None
        # чем читаем видеокарту: nvidia-smi, LibreHardwareMonitor или ничем
        self.gpu_source = "nvidia-smi" if self.has_nvidia else None
        self.gpu_note = None          # что мешает читать видеокарту
        self.has_lhm = False
        self.temp_source = None       # каким способом читаем температуру
        self.temp_extra = 0           # сколько вспомогательных сборок нашлось
        self.temp_sensor = None       # имя выбранного датчика
        self.temp_note = None         # что пошло не так, если не читаем
        self.all_temps = {}           # все найденные датчики температуры
        self.has_weather = False
        self.weather_note = None
        self.weather_source = ""      # как называется служба погоды
        self.sun_source = ""          # откуда восход и закат
        self.weather_city = ""
        self.sunrise = None
        self.sunset = None
        self.twilight_min = 45   # длина плавного перехода
        self.is_admin = _check_admin()
        self._gpu_proc = None
        self._weather_kick = threading.Event()
        self.fake = {}                # выдуманная погода на время проверки

        if psutil:
            psutil.cpu_percent(interval=None)  # первый вызов всегда 0, съедаем его
            # число ядер не меняется, спрашивать его каждую секунду незачем
            self._cores = psutil.cpu_count(logical=False) or MISSING
            self._threads_n = psutil.cpu_count(logical=True) or MISSING

        # Что опрашивать и как часто - из настроек программы. Выключенный
        # источник не опрашивается вовсе: поток под него даже не поднимается.
        self.plan = {"system": (True, 1.0), "gpu": (True, 1.0),
                     "temps": (True, 2.0), "weather": (True, 15.0)}
        # Какой диск показывать. На чужой машине системным может быть
        # не C:, поэтому спрашиваем саму Windows, а start.py может
        # записать в настройки любой другой.
        self.disk = os.environ.get("SystemDrive", "C:") + "\\" \
            if IS_WINDOWS else "/"
        try:
            import prefs
            for key, (on, every) in list(self.plan.items()):
                self.plan[key] = (bool(prefs.get("sensors.%s.on" % key, on)),
                                  max(0.2, float(prefs.get("sensors.%s.every" % key,
                                                           every) or every)))
            self.disk = str(prefs.get("hardware.disk", "") or self.disk)
        except Exception:
            pass

        self._threads = []
        for key, fn in (("system", self._loop_fast), ("gpu", self._loop_gpu),
                        ("temps", self._loop_temps),
                        ("weather", self._loop_weather)):
            if not self.plan[key][0]:
                continue          # выключен - поток даже не поднимаем
            pot = threading.Thread(target=fn, daemon=True)
            self._threads.append(pot)
            pot.start()
        atexit.register(self.stop)

    def stop(self):
        self._stop.set()
        self._kill_gpu()
        # Даём потокам заметить остановку. Поток температуры сидит внутри
        # вызова к .NET, и если оборвать его на полуслове выходом из
        # программы, среда ругается в консоль уже после закрытия окна.
        for pot in self._threads:
            if pot.is_alive():
                pot.join(timeout=0.4)

    def _kill_gpu(self):
        """Прибить nvidia-smi, если он запущен в потоковом режиме."""
        p, self._gpu_proc = self._gpu_proc, None
        if p is None:
            return
        try:
            p.terminate()
        except Exception:
            pass

    # --- фоновые опросы -----------------------------------------------------

    def _set(self, **kw):
        with self.lock:
            self.data.update(kw)

    def _loop_fast(self):
        """Процессор, память, диски, сеть. Дёшево, опрашиваем часто."""
        # Названия железа не меняются, но узнавать их бывает долго
        # (у видеокарты - через PowerShell). Поэтому спрашиваем один раз
        # и здесь, в фоне, а не при запуске программы.
        self._set(cpu_name=cpu_name() or MISSING,
                  gpu_name=gpu_name() or MISSING)
        while not self._stop.is_set():
            light = windows_light_theme()
            if light is not None:
                self._set(system_light=light)
            if psutil:
                try:
                    self._set(cpu_load=psutil.cpu_percent(interval=None))
                    freq = psutil.cpu_freq()
                    if freq:
                        self._set(cpu_mhz=freq.current, cpu_ghz=freq.current / 1000.0)
                    self._set(cpu_cores=self._cores, cpu_threads=self._threads_n)

                    vm = psutil.virtual_memory()
                    self._set(ram_load=vm.percent,
                              ram_used_gb=vm.used / 1073741824.0,
                              ram_total_gb=vm.total / 1073741824.0,
                              ram_free_gb=vm.available / 1073741824.0)

                    du = psutil.disk_usage(self.disk)
                    self._set(disk_load=du.percent,
                              disk_used_gb=du.used / 1073741824.0,
                              disk_total_gb=du.total / 1073741824.0,
                              disk_free_gb=du.free / 1073741824.0)

                    self._poll_net()

                    up = time.time() - psutil.boot_time()
                    self._set(uptime_sec=up,
                              uptime_h=int(up // 3600),
                              uptime_m=int((up % 3600) // 60),
                              uptime=self._fmt_uptime(up))
                except Exception:
                    pass
            self._stop.wait(self.plan["system"][1])

    def _poll_net(self):
        try:
            counters = psutil.net_io_counters(pernic=bool(self.net_interface))
            if self.net_interface:
                c = counters.get(self.net_interface)
                if c is None:
                    return
            else:
                c = counters
            now = time.time()
            if self._last_net is not None:
                dt = now - self._last_net_t
                if dt > 0:
                    down = (c.bytes_recv - self._last_net.bytes_recv) / dt
                    up = (c.bytes_sent - self._last_net.bytes_sent) / dt
                    self._set(net_down_kbs=down / 1024.0, net_up_kbs=up / 1024.0,
                              net_down_mbs=down / 1048576.0, net_up_mbs=up / 1048576.0)
            self._last_net, self._last_net_t = c, now
        except Exception:
            pass

    @staticmethod
    def _fmt_uptime(sec):
        d, rem = divmod(int(sec), 86400)
        h, rem = divmod(rem, 3600)
        m = rem // 60
        if d:
            return "{}д {}ч {}м".format(d, h, m)
        return "{}ч {}м".format(h, m)

    GPU_QUERY = ("utilization.gpu,temperature.gpu,memory.used,memory.total,"
                 "power.draw,clocks.current.graphics,fan.speed,"
                 "utilization.memory")
    GPU_KEYS = ["gpu_load", "gpu_temp", "gpu_mem_used_mb", "gpu_mem_total_mb",
                "gpu_power_w", "gpu_mhz", "gpu_fan", "gpu_mem_load"]

    def _loop_gpu(self):
        """Видеокарта Nvidia через nvidia-smi.

        Сначала пробуем держать один запущенный nvidia-smi с ключом -l:
        он сам выдаёт строку раз в секунду. Поднимать процесс заново
        каждую секунду вышло бы куда дороже - только на запуск уходит
        около 50 мс, то есть двадцатая часть ядра впустую и круглые сутки.

        Если потоковый режим почему-то не пошёл, возвращаемся к прежнему
        способу: запускать nvidia-smi по одному разу.
        """
        if not self.has_nvidia:
            return
        args = ["nvidia-smi", "--query-gpu=" + self.GPU_QUERY,
                "--format=csv,noheader,nounits"]
        if self._stream_gpu(args + ["-l", "1"]):
            return
        while not self._stop.is_set():
            out = _run(args)
            if out:
                self._take_gpu(out.strip().splitlines()[0])
            self._stop.wait(self.plan["gpu"][1])

    def _stream_gpu(self, cmd):
        """Читать показания из непрерывно работающего nvidia-smi.

        True - режим отработал до самой остановки программы.
        False - не запустился или оборвался, дальше нужен обычный опрос.
        """
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL,
                                 text=True, bufsize=1, **_NO_WINDOW)
        except Exception:
            return False
        self._gpu_proc = p
        try:
            for line in p.stdout:
                if self._stop.is_set():
                    break
                line = line.strip()
                if line:
                    self._take_gpu(line)
        except Exception:
            pass
        self._kill_gpu()
        # если поток оборвался сам, а нас никто не останавливал, вернём
        # False: без обычного опроса показания видеокарты просто замрут
        return self._stop.is_set()

    def _take_gpu(self, line):
        """Разобрать строку вида «41, 51, 2450, 16303, 42.4, 1267, 0, 4»."""
        vals = {}
        for k, part in zip(self.GPU_KEYS, line.split(",")):
            try:
                vals[k] = float(part.strip())
            except ValueError:
                vals[k] = MISSING
        if isinstance(vals.get("gpu_mem_used_mb"), float) and \
           isinstance(vals.get("gpu_mem_total_mb"), float):
            vals["gpu_mem_used_gb"] = vals["gpu_mem_used_mb"] / 1024.0
            vals["gpu_mem_total_gb"] = vals["gpu_mem_total_mb"] / 1024.0
        if vals:
            self._set(**vals)

    def _loop_temps(self):
        """Температура процессора (только Windows).

        Два способа, по убыванию предпочтительности:

        1. Напрямую через LibreHardwareMonitorLib.dll, положенную рядом.
           Нужен запуск от имени администратора, зато никаких сторонних
           программ и почти нулевая нагрузка.
        2. Через WMI, если запущена сама LibreHardwareMonitor или
           OpenHardwareMonitor. Дороже, потому что дёргает PowerShell.
        """
        if not IS_WINDOWS:
            return
        if self._try_direct_lhm():
            return
        self._loop_temps_wmi()

    # --- способ 1: библиотека напрямую ---------------------------------

    def _try_direct_lhm(self):
        here = os.path.dirname(os.path.abspath(__file__))
        places = [
            "LibreHardwareMonitorLib.dll",
            os.path.join("lhm", "LibreHardwareMonitorLib.dll"),
            os.path.join(here, "LibreHardwareMonitorLib.dll"),
            os.path.join(here, "lhm", "LibreHardwareMonitorLib.dll"),
        ]
        dll = None
        for name in places:
            if os.path.exists(name):
                dll = os.path.abspath(name)
                break
        if not dll:
            self.temp_note = ("рядом нет LibreHardwareMonitorLib.dll "
                              "(положи её в папку с программой)")
            return False

        try:
            import clr
        except ImportError:
            self.temp_note = ("библиотека есть, но нет pythonnet. "
                              "Выполни: pip install pythonnet")
            return False

        dll_dir = os.path.dirname(dll)

        # .NET ищет вспомогательные сборки рядом с python.exe, а не рядом
        # с нашей библиотекой. Поэтому подсказываем ему, где смотреть.
        try:
            from System import AppDomain, ResolveEventHandler
            from System.Reflection import Assembly

            def _resolve(sender, args):
                short = str(args.Name).split(",")[0]
                cand = os.path.join(dll_dir, short + ".dll")
                if os.path.exists(cand):
                    try:
                        return Assembly.LoadFrom(cand)
                    except Exception:
                        return None
                return None

            # ссылку держим у себя, иначе обработчик соберёт сборщик мусора
            self._asm_resolver = ResolveEventHandler(_resolve)
            AppDomain.CurrentDomain.AssemblyResolve += self._asm_resolver
        except Exception:
            pass

        # Сначала пробуем поднять одну только библиотеку: вспомогательные
        # сборки .NET подтянет сам через обработчик выше, и в память их
        # попадёт заметно меньше. Не выйдет - подгрузим всё подряд.
        loaded = []

        def preload():
            try:
                for name in sorted(os.listdir(dll_dir)):
                    if not name.lower().endswith(".dll"):
                        continue
                    if name.lower() == "librehardwaremonitorlib.dll":
                        continue
                    try:
                        clr.AddReference(os.path.join(dll_dir, name))
                        loaded.append(name)
                    except Exception:
                        pass
            except Exception:
                pass

        try:
            clr.AddReference(dll)
            from LibreHardwareMonitor import Hardware
        except Exception:
            preload()
        try:
            clr.AddReference(dll)
            from LibreHardwareMonitor import Hardware
        except Exception as e:
            msg = str(e)
            if "0x80131515" in msg:
                self.temp_note = ("библиотека заблокирована Windows как "
                                  "скачанная из интернета. Свойства файла -> "
                                  "галочка «Разблокировать»")
            elif "load file or assembly" in msg or "загрузить файл или сборку" in msg:
                self.temp_note = ("не хватает вспомогательных библиотек. "
                                  "Скопируй в папку ВСЕ .dll из архива "
                                  "LibreHardwareMonitor. Не хватает: "
                                  + msg.split('"')[1].split(",")[0]
                                  if '"' in msg else msg[:100])
            else:
                self.temp_note = "библиотека не загрузилась: {}".format(msg[:120])
            return False

        # При Nvidia видеокарту здесь не открываем - её читает nvidia-smi,
        # а опрос отсюда стоит три десятка мегабайт памяти. У AMD и Intel
        # это единственный источник, поэтому открываем.
        #
        # Пробуем дважды: с видеокартой нужен System.Numerics.Vectors.dll,
        # и без него не открывается вообще ничего, даже температура
        # процессора. Лучше панель без видеокарты, чем без датчиков вовсе.
        comp = None
        for s_gpu in ((True, False) if not self.has_nvidia else (False,)):
            try:
                comp = Hardware.Computer()
                comp.IsCpuEnabled = True
                comp.IsGpuEnabled = s_gpu
                comp.IsMotherboardEnabled = True
                comp.IsControllerEnabled = True
                comp.Open()
                break
            except Exception as e:
                comp = None
                msg = str(e)
                if s_gpu:
                    self.gpu_note = ("библиотеке не хватает файла "
                                     "System.Numerics.Vectors.dll — без него "
                                     "показаний видеокарты не будет. Возьми "
                                     "его из архива LibreHardwareMonitor")
                    continue          # пробуем ещё раз, уже без видеокарты
                if "load file or assembly" in msg or \
                        "загрузить файл или сборку" in msg:
                    missing = msg.split('"')[1].split(",")[0] \
                        if '"' in msg else "?"
                    self.temp_note = ("не хватает вспомогательной библиотеки "
                                      "{}.dll. Скопируй в папку ВСЕ .dll "
                                      "из архива LibreHardwareMonitor "
                                      "и разблокируй их".format(missing))
                else:
                    self.temp_note = ("не удалось открыть датчики: {}"
                                      .format(msg[:120]))
        if comp is None:
            return False

        # Способ храним отдельно от числа: иначе получится не ключ словаря,
        # а готовая строка, и перевести её будет уже нечем.
        self.temp_source = "библиотека напрямую"
        self.temp_extra = len(loaded)
        pot = threading.Thread(target=self._loop_lhm_direct,
                               args=(comp, Hardware), daemon=True)
        pot.start()
        self._threads.append(pot)
        return True

    @staticmethod
    def _gpu_from_lhm(s, low, ST, found):
        """Разложить один датчик видеокарты по нашим ключам.

        Имена у Nvidia, AMD и Intel Arc разные, а вид датчика - один
        и тот же, поэтому опираемся на вид, а имя используем только
        чтобы отличить ядро от памяти.
        """
        val = float(s.Value)
        vid = s.SensorType
        if vid == ST.Temperature:
            if "hot" in low or "junction" in low or "memory" in low:
                return                     # это отдельные точки, не общая
            found.setdefault("gpu_temp", val)
        elif vid == ST.Load:
            if "memory" in low:
                found.setdefault("gpu_mem_load", val)
            elif "core" in low or low == "gpu":
                found.setdefault("gpu_load", val)
        elif vid == ST.Power:
            found.setdefault("gpu_power_w", val)
        elif vid == ST.Clock:
            if "core" in low or "graphics" in low:
                found.setdefault("gpu_mhz", val)
        elif vid == ST.Control and "fan" in low:
            found.setdefault("gpu_fan", val)   # в процентах
        elif vid == ST.Fan:
            found.setdefault("gpu_fan_rpm", val)
        elif vid == ST.SmallData:
            # объём памяти LHM отдаёт мегабайтами
            if "memory used" in low and "shared" not in low:
                found.setdefault("gpu_mem_used_mb", val)
            elif "memory total" in low and "shared" not in low:
                found.setdefault("gpu_mem_total_mb", val)

    def _loop_lhm_direct(self, comp, Hardware):
        HW, ST = Hardware.HardwareType, Hardware.SensorType
        # какие узлы считать видеокартой: у разных производителей свои
        gpu_types = tuple(getattr(HW, name) for name in
                          ("GpuNvidia", "GpuAmd", "GpuAti", "GpuIntel")
                          if hasattr(HW, name))
        while not self._stop.is_set():
            found = {}
            temps = {}
            try:
                for hw in comp.Hardware:
                    hw.Update()
                    for sub in hw.SubHardware:
                        sub.Update()
                    is_cpu = (hw.HardwareType == HW.Cpu)
                    is_gpu = hw.HardwareType in gpu_types
                    is_mb = hw.HardwareType in (HW.Motherboard, HW.SuperIO)
                    sensors_list = list(hw.Sensors)
                    for sub in hw.SubHardware:
                        sensors_list += list(sub.Sensors)
                    for s in sensors_list:
                        if s.Value is None:
                            continue
                        val = float(s.Value)
                        low = (s.Name or "").lower()
                        if is_gpu:
                            self._gpu_from_lhm(s, low, ST, found)
                        elif is_cpu and s.SensorType == ST.Temperature:
                            temps[s.Name] = val
                        elif is_cpu and s.SensorType == ST.Power and "package" in low:
                            found["cpu_power_w"] = val
                        elif s.SensorType == ST.Fan:
                            if "cpu" in low:
                                found["cpu_fan_rpm"] = val
                            found.setdefault("fan_rpm", val)
                        elif is_mb and s.SensorType == ST.Temperature:
                            found.setdefault("mb_temp", val)
            except Exception:
                pass
            if temps:
                self.all_temps = dict(temps)
                best = min(temps, key=lambda n: (temp_priority(n), n))
                found["cpu_temp"] = temps[best]
                self.temp_sensor = best
            if "gpu_mem_used_mb" in found and "gpu_mem_total_mb" in found:
                found["gpu_mem_used_gb"] = found["gpu_mem_used_mb"] / 1024.0
                found["gpu_mem_total_gb"] = found["gpu_mem_total_mb"] / 1024.0
            if found:
                self.has_lhm = True
                if not self.has_nvidia and "gpu_load" in found:
                    self.gpu_source = "LibreHardwareMonitor"
                self._set(**found)
            self._stop.wait(self.plan["temps"][1])

    # --- способ 2: через WMI -------------------------------------------

    def _loop_temps_wmi(self):
        namespaces = ["root/LibreHardwareMonitor", "root/OpenHardwareMonitor"]
        working = None
        while not self._stop.is_set():
            for ns in ([working] if working else namespaces):
                ps = ("Get-CimInstance -Namespace {} -ClassName Sensor "
                      "-ErrorAction Stop | Where-Object {{$_.SensorType -eq "
                      "'Temperature'}} | Select-Object Name,Value | "
                      "ConvertTo-Csv -NoTypeInformation").format(ns)
                out = _run(["powershell", "-NoProfile", "-NonInteractive",
                            "-Command", ps], timeout=10)
                if not out:
                    continue
                temps = {}
                for line in out.splitlines()[1:]:
                    parts = line.strip().strip('"').split('","')
                    if len(parts) != 2:
                        continue
                    name, val = parts[0], parts[1]
                    try:
                        temps[name] = float(val.replace(",", "."))
                    except ValueError:
                        continue
                best = None
                if temps:
                    self.all_temps = dict(temps)
                    pick = min(temps, key=lambda n: (temp_priority(n), n))
                    if temp_priority(pick) <= 6:
                        best = temps[pick]
                        self.temp_sensor = pick
                if best is not None:
                    working = ns
                    self.has_lhm = True
                    self.temp_source = "через WMI"
                    self._set(cpu_temp=best)
                    break
            # PowerShell дорого запускать, поэтому реже
            self._stop.wait(4.0)

    # --- выдача -------------------------------------------------------------


    def refresh_weather(self):
        """Забрать погоду заново, не дожидаясь очередного часа."""
        self._weather_kick.set()

    def pretend(self, code=None, temp=None, wind=None):
        """Показать выдуманную погоду вместо настоящей.

        Нужно, чтобы посмотреть, как тема ведёт себя в грозу или метель,
        не дожидаясь их. code=None возвращает всё как есть.
        """
        if code is None:
            self.fake = {}
            return
        lang = "ru"
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(here, WEATHER_CONF), encoding="utf-8") as f:
                lang = str(json.load(f).get("language", "ru")).lower()
        except Exception:
            pass
        table = WMO_EN if lang.startswith("en") else WMO
        short, full = table.get(int(code), ("—", "нет данных"))
        out = {"weather_code": int(code), "weather": short,
               "weather_full": full}
        out.update(sky_parts(code))
        if temp is not None:
            out["weather_temp"] = float(temp)
            out["weather_feels"] = float(temp)
        if wind is not None:
            out["weather_wind"] = float(wind)
        self.fake = out

    def _loop_weather(self):
        """Погода через Open-Meteo. Ключ API не нужен, регистрация тоже."""
        import urllib.request
        conf = _weather_config()

        while not self._stop.is_set():
            # Настройки перечитываем каждый заход: сменил город в окне -
            # и ждать перезапуска программы не нужно.
            try:
                here = os.path.dirname(os.path.abspath(__file__))
                with open(os.path.join(here, WEATHER_CONF), encoding="utf-8") as f:
                    conf = json.load(f)
            except Exception:
                pass
            self.weather_city = conf.get("city", "")
            wait = max(5, int(conf.get("update_minutes", 15))) * 60
            if conf.get("latitude") is None:
                self.weather_note = ("не выбрано место — укажи город "
                                     "в настройках, раздел «Погода»")
                self._weather_kick.wait(60)
                self._weather_kick.clear()
                continue
            vid = perehodnik(conf)
            self.weather_source = vid.get("imya", "")
            url = weather_url(conf, conf["latitude"], conf["longitude"])
            try:
                d = sprosit(url)
                vals, voshod, zakat = razobrat_pogodu(d, vid)
                code = vals["weather_code"]
                short_ru, full_ru = WMO.get(code, ("—", "нет данных"))
                short_en, full_en = WMO_EN.get(code, ("—", "no data"))
                lang = str(conf.get("language", "ru")).lower()
                short, full = ((short_en, full_en) if lang.startswith("en")
                               else (short_ru, full_ru))
                vals.update({
                    "weather": short,
                    "weather_full": full,
                    "weather_ru": short_ru,
                    "weather_full_ru": full_ru,
                    "weather_en": short_en,
                    "weather_full_en": full_en,
                    "weather_city": self.weather_city,
                })
                vals.update(sky_parts(code))
                # Восход и закат отдают не все службы. Без них панель
                # не знает, когда менять ночной вид на дневной, поэтому
                # считаем их сами по широте и долготе.
                if voshod is None or zakat is None:
                    voshod, zakat = solnce(conf["latitude"],
                                           conf["longitude"])
                    self.sun_source = "свой расчёт"
                else:
                    self.sun_source = vid.get("imya", "")
                if voshod and zakat:
                    self.sunrise, self.sunset = voshod, zakat
                    vals["sunrise"] = edinicy.chasy(voshod)
                    vals["sunset"] = edinicy.chasy(zakat)
                self.has_weather = True
                self.weather_note = None
                self._set(**vals)
            except Exception as e:
                self.weather_note = "нет связи с сервисом погоды: {}".format(
                    str(e)[:60])
            self._weather_kick.wait(wait)
            self._weather_kick.clear()


    def day_factor(self, now=None):
        """Насколько сейчас день: 0 - ночь, 1 - день, между - переход.

        Переход растянут вокруг восхода и заката, по умолчанию на 45 минут,
        и идёт по сглаженной кривой, без рывков на краях.
        """
        now = now or datetime.now()
        rise, sett = self.sunrise, self.sunset
        if rise is None or sett is None:
            # запасной вариант, пока прогноз не пришёл
            rise = now.replace(hour=7, minute=0, second=0, microsecond=0)
            sett = now.replace(hour=20, minute=0, second=0, microsecond=0)
        else:
            rise = now.replace(hour=rise.hour, minute=rise.minute,
                               second=0, microsecond=0)
            sett = now.replace(hour=sett.hour, minute=sett.minute,
                               second=0, microsecond=0)

        half = self.twilight_min * 30.0   # половина перехода в секундах

        def smooth(dolya):
            dolya = max(0.0, min(1.0, dolya))
            return dolya * dolya * (3 - 2 * dolya)

        sec = (now - rise).total_seconds()
        if sec < -half:
            return 0.0
        if sec <= half:
            return smooth((sec + half) / (2 * half))
        sec = (now - sett).total_seconds()
        if sec < -half:
            return 1.0
        if sec <= half:
            return 1.0 - smooth((sec + half) / (2 * half))
        return 0.0

    def read(self):
        """Снимок всех значений плюс текущее время."""
        with self.lock:
            snap = dict(self.data)
        if self.fake:
            snap.update(self.fake)
        now = datetime.now()
        snap["now"] = now
        snap["day_factor"] = round(self.day_factor(now), 3)
        snap["is_day"] = snap["day_factor"] >= 0.5
        # Метёт снег или падает отвесно - решает ветер. Снегопад задаёт,
        # сколько его вообще, ветер - куда он летит. Перемножаем, чтобы
        # тема могла спросить одним значением: react умеет только одно.
        snow = float(snap.get("sky_snow", 0) or 0)
        wind = snap.get("weather_wind")
        w = 0.0 if not isinstance(wind, (int, float)) else \
            max(0.0, min(1.0, (float(wind) - 10.0) / 28.0))
        snap["snow_calm"] = round(snow * (1.0 - w), 3)
        snap["snow_windy"] = round(snow * w, 3)
        # Доли отдаются как есть, без привязки ко дню: этим занимается
        # панель - она одна знает, какую долю дня рисует прямо сейчас.
        # См. Panel._sky_by_day.
        snap["sky_sun"] = round(float(snap.get("sky_clear", 0) or 0)
                                * snap["day_factor"], 3)
        snap["sky_day"] = snap["day_factor"]
        snap["sky_night"] = round(1.0 - snap["day_factor"], 3)
        # Готовые время и дата в том виде, какой выбран в настройках.
        # Сырое {now:...} остаётся рядом для тех тем, которым нужен свой.
        return edinicy.dobavit(snap)

    def describe(self):
        """Что доступно и что мешает. Для запуска и диагностики."""
        rows = []
        rows.append(t("psutil (процессор, память, диски, сеть): ")
                    + (t("есть") if psutil else t("НЕ УСТАНОВЛЕН")))
        if cpu_name():
            rows.append(t("процессор: ") + cpu_name())
        if gpu_name():
            rows.append(t("видеокарта: ") + gpu_name())
        if self.gpu_source:
            rows.append(t("показания видеокарты: ") + self.gpu_source)
        elif self.gpu_note:
            rows.append(t("показания видеокарты: НЕТ — ") + t(self.gpu_note))
        else:
            rows.append(t("показания видеокарты: НЕТ — нет ни nvidia-smi, "
                          "ни LibreHardwareMonitorLib.dll"))
        if IS_WINDOWS:
            if self.has_lhm:
                kak = t(self.temp_source or "способ не указан")
                if self.temp_extra:
                    kak += t(", вспомогательных сборок: {}").format(
                        self.temp_extra)
                rows.append(t("температура процессора: читается ({})")
                            .format(kak))
                if self.temp_sensor:
                    rows.append(t("  выбран датчик: ") + self.temp_sensor)
                if self.all_temps:
                    rows.append(t("  все найденные датчики процессора:"))
                    for n in sorted(self.all_temps,
                                    key=lambda x: (temp_priority(x), x)):
                        rows.append("     {:32s} {:5.1f} {}".format(
                            n[:32], edinicy.gradusy(self.all_temps[n]),
                            edinicy.znak()))
            else:
                why = self.temp_note or "источник не найден"
                rows.append(t("температура процессора: НЕТ — ") + t(why))
                if not self.is_admin:
                    rows.append(t("  ВНИМАНИЕ: программа запущена без прав "
                                  "администратора."))
                    rows.append(t("  Температуру процессора без них прочитать "
                                  "невозможно в принципе:"))
                    rows.append(t("  Windows не даёт доступ к регистрам "
                                  "процессора обычным программам."))
                else:
                    rows.append(t("  Права администратора есть. Положи рядом "
                                  "LibreHardwareMonitorLib.dll"))
                    rows.append(t("  и HidSharp.dll, либо запусти саму "
                                  "LibreHardwareMonitor в фоне."))
        if self.has_weather:
            rows.append(t("погода: получена{}{}").format(
                t(" от ") + self.weather_source if self.weather_source else "",
                t(" для ") + self.weather_city if self.weather_city else ""))
            if self.sun_source:
                rows.append(t("  восход и закат: ") + self.sun_source)
        else:
            rows.append(t("погода: НЕТ — ")
                        + t(self.weather_note or "ещё не загружена"))
        return "\n".join("  " + r for r in rows)


ALL_KEYS = """
  Процессор:  cpu_load  cpu_temp  cpu_mhz  cpu_ghz  cpu_cores  cpu_threads
              cpu_power_w  cpu_fan_rpm
  Память:     ram_load  ram_used_gb  ram_total_gb  ram_free_gb
  Диск C:     disk_load  disk_used_gb  disk_total_gb  disk_free_gb
  Видеокарта: gpu_load  gpu_temp  gpu_mem_load  gpu_mem_used_gb
              gpu_mem_total_gb  gpu_power_w  gpu_mhz  gpu_fan
  Сеть:       net_down_kbs  net_up_kbs  net_down_mbs  net_up_mbs
  Система:    uptime  uptime_h  uptime_m  now  mb_temp  fan_rpm
  Погода:     weather  weather_full  weather_temp  weather_feels
              weather_ru  weather_full_ru  weather_en  weather_full_en
  Солнце:     sunrise  sunset  day_factor (0 ночь .. 1 день)  is_day
              weather_humidity  weather_wind  weather_min
              weather_max  weather_city
"""


if __name__ == "__main__":
    s = Sensors()
    print("Источники данных:")
    print(s.describe())
    print("\nЖду 3 секунды, чтобы датчики успели опроситься...\n")
    time.sleep(3)
    print(s.describe())
    print()
    data = s.read()
    for k in sorted(data):
        v = data[k]
        if isinstance(v, float):
            print("  {:20s} {:.2f}".format(k, v))
        else:
            print("  {:20s} {}".format(k, v))
    s.stop()
