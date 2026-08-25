#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Визуальный редактор панели.
#  Часть проекта EOne screen — открытой замены штатной программе
#  для экранов на контроллере TXW818.
#
#  Автор: EOne
#  Лицензия: CC BY-NC-SA 4.0 — использование в коммерческих целях
#  запрещено без письменного разрешения автора. См. файл LICENSE.
#
"""
editor.py - визуальный редактор панели.

    python editor.py              открыть layout.json
    python editor.py другой.json  открыть другое описание

Слева список блоков, в центре точный предпросмотр того, что уйдёт
на экран водянки, справа свойства выбранного блока.

Двигается только выбранный блок - мышкой, стрелками или полями X и Y.
При перетаскивании появляются зелёные линии привязки к краям и центрам
других блоков.
"""

import copy
import json
import os
import sys
import threading
import time

import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from PIL import Image, ImageTk

import panel as panel_mod
import sensors as sensors_mod
import yazyk
from yazyk import t

AUTHOR = "EOne"
PROJECT = "EOne screen"
LICENSE = "CC BY-NC-SA 4.0, некоммерческое использование"
# Версия у программы одна и лежит в panel.py. Своя, отдельная, здесь
# была - и разошлась с настоящей на полтора года правок.
VERSION = panel_mod.VERSION

SNAP = 6      # на сколько пикселей притягивать к линиям привязки
PROPS_W = 300  # ширина колонки свойств справа


# --- списки для выпадающих меню ---------------------------------------------

SENSORS = [
    ("Загрузка процессора, %", "cpu_load"),
    ("Температура процессора", "cpu_temp"),
    ("Частота процессора, ГГц", "cpu_ghz"),
    ("Потребление процессора, Вт", "cpu_power_w"),
    ("Обороты вентилятора ЦП", "cpu_fan_rpm"),
    ("Загрузка видеокарты, %", "gpu_load"),
    ("Температура видеокарты", "gpu_temp"),
    ("Потребление видеокарты, Вт", "gpu_power_w"),
    ("Загрузка видеопамяти, %", "gpu_mem_load"),
    ("Занято видеопамяти, ГБ", "gpu_mem_used_gb"),
    ("Частота видеокарты, МГц", "gpu_mhz"),
    ("Вентилятор видеокарты, %", "gpu_fan"),
    ("Загрузка ОЗУ, %", "ram_load"),
    ("Занято ОЗУ, ГБ", "ram_used_gb"),
    ("Свободно ОЗУ, ГБ", "ram_free_gb"),
    ("Загрузка диска, %", "disk_load"),
    ("Свободно на диске, ГБ", "disk_free_gb"),
    ("Приём из сети, МБ/с", "net_down_mbs"),
    ("Отдача в сеть, МБ/с", "net_up_mbs"),
    ("Температура платы", "mb_temp"),
    ("Погода: температура", "weather_temp"),
    ("Погода: ощущается как", "weather_feels"),
    ("Погода: влажность, %", "weather_humidity"),
    ("Погода: ветер, км/ч", "weather_wind"),
]

TEXT_PRESETS = [
    ("— свой текст —", None),
    ("Загрузка процессора  23%", "{cpu_load:.0f}%"),
    ("Температура процессора  67 °C", "{cpu_temp:.0f} °C"),
    ("Частота процессора  4.85 ГГц", "{cpu_ghz:.2f} ГГц"),
    ("Потребление процессора  142 Вт", "{cpu_power_w:.0f} Вт"),
    ("Загрузка видеокарты  41%", "{gpu_load:.0f}%"),
    ("Температура видеокарты  51 °C", "{gpu_temp:.0f} °C"),
    ("Потребление видеокарты  186 Вт", "{gpu_power_w:.0f} Вт"),
    ("Видеопамять  9.9 ГБ", "{gpu_mem_used_gb:.1f} ГБ"),
    ("Видеопамять  9.9 / 16 ГБ", "{gpu_mem_used_gb:.1f} / {gpu_mem_total_gb:.0f} ГБ"),
    ("Загрузка ОЗУ  28%", "{ram_load:.0f}%"),
    ("ОЗУ  17.0 / 64 ГБ", "{ram_used_gb:.1f} / {ram_total_gb:.0f} ГБ"),
    ("Свободно на диске  231 ГБ", "{disk_free_gb:.0f} ГБ"),
    ("Приём из сети  11.4 МБ/с", "{net_down_mbs:.1f} МБ/с"),
    ("Отдача в сеть  2.3 МБ/с", "{net_up_mbs:.1f} МБ/с"),
    ("Время работы  5ч 49м", "{uptime}"),
    ("Часы  как выбрано в настройках", "{time}"),
    ("Часы с секундами  как выбрано в настройках", "{time_sec}"),
    ("Дата  как выбрано в настройках", "{date}"),
    ("Дата коротко  как выбрано в настройках", "{date_short}"),
    ("Часы  14:30", "{now:%H:%M}"),
    ("Часы с секундами  14:30:45", "{now:%H:%M:%S}"),
    ("Часы 12-часовые  02:30 PM", "{now:%I:%M %p}"),
    ("Часы 12-часовые с секундами  02:30:45 PM", "{now:%I:%M:%S %p}"),
    ("Дата  03.08.2026", "{now:%d.%m.%Y}"),
    ("Дата  03.08.26", "{now:%d.%m.%y}"),
    ("Дата  2026-08-03", "{now:%Y-%m-%d}"),
    ("Дата  03 August", "{now:%d %B}"),
    ("День недели  Monday", "{now:%A}"),
    ("Погода кратко  Дождь", "{weather}"),
    ("Погода подробно  Небольшой дождь", "{weather_full}"),
    ("Погода и температура  Дождь  12 °C", "{weather}   {weather_temp:.0f} °C"),
    ("Погода подробно и температура", "{weather_full}   {weather_temp:.0f} °C"),
    ("Погода: температура со знаком настройки  12 °C",
     "{weather_temp:.0f} {deg}"),
    ("Погода: только температура  12 °C", "{weather_temp:.0f} °C"),
    ("Погода: ощущается как  10 °C", "ощущается как {weather_feels:.0f} °C"),
    ("Погода: минимум и максимум  8…15 °C",
     "{weather_min:.0f}…{weather_max:.0f} °C"),
    ("Погода: ветер  4 км/ч", "ветер {weather_wind:.0f} км/ч"),
    ("Погода: влажность  78 %", "влажность {weather_humidity:.0f} %"),
    ("Погода: город и температура", "{weather_city}  {weather_temp:.0f} °C"),
    ("Погода: всё вместе", "{weather_city}  {weather_full}  {weather_temp:.0f} °C"),
    ("Weather short  Rain", "{weather_en}"),
    ("Weather full  Light rain", "{weather_full_en}"),
    ("Weather and temperature  Rain  12 °C",
     "{weather_en}   {weather_temp:.0f} °C"),
    ("Weather full and temperature",
     "{weather_full_en}   {weather_temp:.0f} °C"),
    ("Weather: feels like  10 °C", "feels like {weather_feels:.0f} °C"),
    ("Weather: low and high  8…15 °C", "{weather_min:.0f}…{weather_max:.0f} °C"),
    ("Weather: wind  4 km/h", "wind {weather_wind:.0f} km/h"),
    ("Weather: humidity  78 %", "humidity {weather_humidity:.0f} %"),
    ("Weather: everything", "{weather_city}  {weather_full_en}  {weather_temp:.0f} °C"),
]

ANCHORS = [
    ("по центру", "mm"),
    ("слева, по середине", "lm"),
    ("справа, по середине", "rm"),
    ("слева сверху", "la"),
    ("по центру сверху", "ma"),
    ("справа сверху", "ra"),
    ("слева снизу", "ld"),
    ("по центру снизу", "md"),
    ("справа снизу", "rd"),
]

DIRECTIONS = [("слева направо", "h"), ("справа налево", "rl"),
              ("снизу вверх", "v"), ("сверху вниз", "tb")]

GAPS = [("сверху", "top"), ("снизу", "bottom"),
        ("слева", "left"), ("справа", "right")]

FITS = [("заполнить с обрезкой", "cover"), ("вписать целиком", "contain"),
        ("растянуть", "stretch"), ("как есть", "none")]

TYPES = [("текст", "text"), ("прямоугольник", "rect"), ("овал", "ellipse"),
         ("линия", "line"), ("стрелка", "arrow"), ("звезда", "star"),
         ("полоса", "bar"), ("кольцо", "ring"), ("картинка", "image")]

# в списке добавления есть квадрат - это тот же прямоугольник,
# просто с одинаковыми сторонами
ADD_LIST = [("текст", "text"), ("прямоугольник", "rect"), ("квадрат", "square"),
            ("овал", "ellipse"), ("круг", "circle"), ("линия", "line"),
            ("стрелка", "arrow"), ("звезда", "star"), ("полоса", "bar"),
            ("кольцо", "ring"), ("картинка", "image")]

SPEEDS = [("резко", "резко"), ("средне", "средне"), ("плавно", "плавно")]

# как крутится повтор: туда-обратно или всё время в одну сторону
LOOP_MODES = [("туда-обратно", "pingpong"), ("по кругу", "forward")]

# что именно меняется у блока к дню: набор полей, которые попадут в раздел day
ANIM_PARTS = {
    "затухание": ["opacity"],
    "движение": ["x", "y"],
    "поворот": ["angle"],
    "цвет": ["fill", "color", "back", "fill2", "outline"],
    "размер": ["w", "h", "r", "size", "thickness", "stretch_x", "stretch_y"],
}

GRADIENTS = [("нет", ""), ("сверху вниз", "v"), ("снизу вверх", "bt"),
             ("слева направо", "h"), ("справа налево", "rl"), ("по диагонали", "diag")]

FRIENDLY_FONTS = [
    ("Arial обычный", "arial.ttf"), ("Arial жирный", "arialbd.ttf"),
    ("Segoe UI обычный", "segoeui.ttf"), ("Segoe UI жирный", "segoeuib.ttf"),
    ("Consolas обычный", "consola.ttf"), ("Consolas жирный", "consolab.ttf"),
    ("Tahoma обычный", "tahoma.ttf"), ("Tahoma жирный", "tahomabd.ttf"),
    ("Verdana обычный", "verdana.ttf"), ("Verdana жирный", "verdanab.ttf"),
    ("Times New Roman", "times.ttf"), ("Impact", "impact.ttf"),
    ("Calibri обычный", "calibri.ttf"), ("Calibri жирный", "calibrib.ttf"),
]


def all_fonts():
    """Понятные названия сверху, дальше всё, что нашлось в системе."""
    found = set()
    dirs = [r"C:\Windows\Fonts", "fonts", ".",
            # шрифты, установленные только для текущего пользователя
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts")]
    for d in dirs:
        try:
            for n in os.listdir(d):
                if n.lower().endswith((".ttf", ".otf", ".ttc")):
                    found.add(n)
        except Exception:
            pass
    pairs = [(label, f) for label, f in FRIENDLY_FONTS if not found or f in found]
    known = {f for _, f in pairs}
    for f in sorted(found):
        if f not in known:
            pairs.append((f, f))
    return pairs or [(f, f) for _, f in FRIENDLY_FONTS]


# --- описание полей для каждого типа блока ----------------------------------

# Что означает каждое поле, человеческим языком. Всплывает при наведении.
# Названия в самих полях короткие, чтобы влезали, а объяснение живёт тут.
HINTS = {
    "__find": "Искать по названию, типу и тексту слоя. Рядом — показывать все слои, только видимые ночью или только днём.",
    "name": "Подпись для себя, в списке слева. На картинку не влияет.",
    "x": "Отступ слева, в точках. Начало координат — левый верхний угол.",
    "y": "Отступ сверху, в точках.",
    "x2": "Куда линия приходит по горизонтали.",
    "y2": "Куда линия приходит по вертикали.",
    "angle": "Наклон слоя в градусах, по часовой стрелке.",
    "stretch_x": "Растянуть слой вширь. 1 — как есть, 2 — вдвое шире.",
    "stretch_y": "Растянуть слой ввысь. 1 — как есть, 0.5 — вдвое ниже.",
    "opacity": "Насколько слой прозрачен: 0 — не видно совсем, 1 — плотно.",
    "text": "Что написать. В фигурных скобках подставляются показания: "
            "{cpu_load:.0f}% даст «37%».",
    "__preset": "Готовые надписи: часы, дата, погода, загрузка. Выбери — "
                "и текст подставится сам.",
    "font": "Файл шрифта. Любой из системы или положенный рядом с темой.",
    "size": "Высота букв в точках.",
    "color": "Цвет букв.",
    "anchor": "За какую точку слой держится координатами. По центру — "
              "удобно для цифр, что меняют длину.",
    "outline": "Цвет обводки. Помогает читать надпись поверх пёстрой картинки.",
    "outline_width": "Толщина обводки букв в точках.",
    "w": "Ширина слоя в точках.",
    "h": "Высота слоя в точках.",
    "radius": "Скругление углов. 0 — прямые углы.",
    "fill": "Основной цвет заливки.",
    "fill2": "Второй цвет: заливка станет переходом от первого ко второму.",
    "gradient": "В какую сторону идёт переход между двумя цветами.",
    "width": "Толщина линии или окантовки в точках.",
    "value": "Откуда берётся число: загрузка, температура, погода.",
    "min": "Какому значению соответствует пустая полоса или дуга.",
    "max": "Какому значению соответствует полная полоса или дуга.",
    "direction": "В какую сторону растёт заполнение.",
    "back": "Цвет незаполненной части. Можно не задавать.",
    "r": "Радиус в точках. Координаты — это центр, а не угол.",
    "r_inner": "Радиус впадин между лучами звезды.",
    "points": "Сколько лучей у звезды.",
    "turn": "Повернуть звезду на столько градусов.",
    "thickness": "Толщина дуги в точках.",
    "gap_at": "С какой стороны у кольца вырез.",
    "gap": "Ширина выреза в градусах. 60 — небольшой, 180 — половина круга.",
    "reverse": "Заполнять дугу с другого конца, навстречу обычному.",
    "cap": "Скруглить концы — дуга или линия смотрится мягче.",
    "head": "Размер наконечника стрелки в точках.",
    "src": "Файл картинки или папка с кадрами. Папка листается как ролик.",
    "fit": "Что делать, если картинка не совпала с отведённым местом.",
    "fps": "Своя частота листания кадров. Ставь ту, с которой резал ролик, "
           "иначе он поедет быстрее или медленнее задуманного.",
    "premultiplied": "Включи, если PNG выгружены из DaVinci: там цвет уже "
                     "умножен на прозрачность, и без этого по мягкому краю "
                     "пойдёт тёмная каёмка.",
    "alpha_gain": "Поднять непрозрачность, если объект вырезался полупрозрачным "
                  "и выглядит блёклым. 1 — не трогать, 1.5 — заметно плотнее.",
}


def fields_for(kind):
    common = [("name", "Название", "text"),
              ("x", "X", "int"), ("y", "Y", "int"),
              ("angle", "Поворот, °", "float"),
              ("stretch_x", "Шире", "float"),
              ("stretch_y", "Выше", "float"),
              ("opacity", "Прозрачность", "float")]
    grad = [("fill2", "Второй цвет", "color"),
            ("gradient", "Переход цвета", "list:gradients")]
    if kind == "text":
        return common + [
            ("__preset", "Готовая надпись", "preset"),
            ("text", "Текст", "text"),
            ("font", "Шрифт", "font"), ("size", "Размер", "int"),
            ("color", "Цвет", "color"),
            ("anchor", "Держится за", "list:anchors"),
            ("outline", "Обводка", "color"),
            ("outline_width", "Толщина обводки", "int"),
        ]
    if kind == "rect":
        return common + [
            ("w", "Ширина", "int"), ("h", "Высота", "int"),
            ("radius", "Скругление", "int"),
            ("fill", "Заливка", "color"),
        ] + grad + [
            ("outline", "Окантовка", "color"), ("width", "Толщина", "int"),
        ]
    if kind == "ellipse":
        return common + [
            ("w", "Ширина", "int"), ("h", "Высота", "int"),
            ("fill", "Заливка", "color"),
        ] + grad + [
            ("outline", "Окантовка", "color"), ("width", "Толщина", "int"),
        ]
    if kind in ("line", "arrow"):
        extra = [("head", "Наконечник", "int")] if kind == "arrow" else \
                [("cap", "Мягкие концы", "bool:round")]
        return common + [
            ("x2", "X конца", "int"), ("y2", "Y конца", "int"),
            ("width", "Толщина", "int"), ("fill", "Цвет", "color"),
        ] + extra
    if kind == "star":
        return common + [
            ("r", "Радиус", "int"), ("r_inner", "Радиус впадин", "int"),
            ("points", "Лучей", "int"), ("turn", "Наклон, °", "float"),
            ("fill", "Заливка", "color"),
        ] + grad + [
            ("outline", "Окантовка", "color"), ("width", "Толщина", "int"),
        ]
    if kind == "bar":
        return common + [
            ("value", "Показание", "sensor"),
            ("min", "Пусто при", "float"),
            ("max", "Полно при", "float"),
            ("w", "Ширина", "int"), ("h", "Высота", "int"),
            ("direction", "Направление", "list:directions"),
            ("radius", "Скругление", "int"),
            ("fill", "Цвет заполнения", "color"),
        ] + grad + [
            ("back", "Цвет пустоты", "color"),
            ("outline", "Окантовка", "color"), ("width", "Толщина", "int"),
        ]
    if kind == "ring":
        return common + [
            ("value", "Показание", "sensor"),
            ("min", "Пусто при", "float"),
            ("max", "Полно при", "float"),
            ("r", "Радиус", "int"), ("thickness", "Толщина дуги", "int"),
            ("gap_at", "Вырез", "list:gaps"),
            ("gap", "Вырез, °", "int"),
            ("reverse", "Наоборот", "bool"),
            ("fill", "Цвет заполнения", "color"),
            ("back", "Цвет пустоты", "color"),
            ("cap", "Мягкие концы", "bool:round"),
        ]
    if kind == "image":
        return common + [
            ("src", "Картинка", "path"),
            ("w", "Ширина", "int"), ("h", "Высота", "int"),
            ("fit", "Как вписать", "list:fits"),
            ("fps", "Кадров в секунду", "float"),
            ("premultiplied", "PNG из DaVinci", "bool"),
            ("alpha_gain", "Плотнее", "float"),
        ]
    return common


# По какому разделу раскладывать свойства. Порядок разделов тот же:
# сначала что слой показывает, потом где стоит, потом как выглядит.
GROUPS = [
    ("Что показывает", ["__preset", "text", "value", "min", "max",
                        "src", "fit", "fps", "premultiplied", "alpha_gain"]),
    ("Где и какого размера", ["name", "x", "y", "x2", "y2", "w", "h", "r",
                              "r_inner", "points", "turn", "thickness",
                              "radius", "angle", "stretch_x", "stretch_y",
                              "anchor"]),
    ("Как выглядит", ["font", "size", "color", "fill", "fill2", "gradient",
                      "back", "outline", "outline_width", "width", "opacity",
                      "direction", "gap_at", "gap", "reverse", "cap", "head"]),
]

# обратный поиск: поле -> название раздела
GROUP_OF = {k: name for name, keys in GROUPS for k in keys}


NEW_LAYER = {
    "text": {"type": "text", "name": "новый текст", "x": 400, "y": 240,
             "text": "{cpu_load:.0f}%", "font": "arialbd.ttf", "size": 40,
             "color": "#ffffff", "anchor": "mm"},
    "rect": {"type": "rect", "name": "новый прямоугольник", "x": 380, "y": 200,
             "w": 200, "h": 80, "radius": 12, "fill": "#203050", "opacity": 0.7},
    "bar": {"type": "bar", "name": "новая полоса", "x": 360, "y": 230,
            "w": 240, "h": 24, "radius": 12, "direction": "h",
            "value": "cpu_load", "min": 0, "max": 100,
            "fill": "#4aa8ff", "back": "#1b2436"},
    "ring": {"type": "ring", "name": "новое кольцо", "x": 480, "y": 240,
             "r": 70, "thickness": 16, "gap_at": "bottom", "gap": 70,
             "value": "cpu_load", "min": 0, "max": 100,
             "fill": "#ff2b2b", "back": "#33373f", "cap": "round"},
    "image": {"type": "image", "name": "новая картинка", "x": 0, "y": 0,
              "src": "", "fit": "cover"},
    "square": {"type": "rect", "name": "новый квадрат", "x": 430, "y": 190,
               "w": 100, "h": 100, "radius": 8, "fill": "#4aa8ff"},
    "ellipse": {"type": "ellipse", "name": "новый овал", "x": 400, "y": 200,
                "w": 160, "h": 90, "fill": "#66dd88"},
    "circle": {"type": "ellipse", "name": "новый круг", "x": 430, "y": 190,
               "w": 100, "h": 100, "fill": "#66dd88"},
    "line": {"type": "line", "name": "новая линия", "x": 340, "y": 240,
             "x2": 620, "y2": 240, "width": 4, "fill": "#c3cadb", "cap": "round"},
    "arrow": {"type": "arrow", "name": "новая стрелка", "x": 340, "y": 240,
              "x2": 600, "y2": 240, "width": 4, "head": 18, "fill": "#c3cadb"},
    "star": {"type": "star", "name": "новая звезда", "x": 480, "y": 240,
             "r": 60, "r_inner": 26, "points": 5, "fill": "#ffd24a"},
}


def bbox_of(layer, w_scr, h_scr):
    """Приблизительная рамка блока - для выбора мышкой и линий привязки."""
    kind = layer.get("type")
    x, y = int(layer.get("x", 0) or 0), int(layer.get("y", 0) or 0)
    if kind == "ring":
        r = int(layer.get("r", 60) or 60) + int(layer.get("thickness", 14) or 14) // 2
        return (x - r, y - r, x + r, y + r)
    if kind in ("rect", "bar"):
        return (x, y, x + int(layer.get("w", 100) or 100),
                y + int(layer.get("h", 100) or 100))
    if kind == "image":
        return (x, y, x + int(layer.get("w", w_scr) or w_scr),
                y + int(layer.get("h", h_scr) or h_scr))
    if kind == "ellipse":
        return (x, y, x + int(layer.get("w", 100) or 100),
                y + int(layer.get("h", 100) or 100))
    if kind in ("line", "arrow"):
        x2 = int(layer.get("x2", x + 200) or 0)
        y2 = int(layer.get("y2", y) or 0)
        pad = max(4, int(layer.get("width", 3) or 3))
        return (min(x, x2) - pad, min(y, y2) - pad,
                max(x, x2) + pad, max(y, y2) + pad)
    if kind == "star":
        r = int(layer.get("r", 60) or 60)
        return (x - r, y - r, x + r, y + r)
    if kind == "text":
        size = int(layer.get("size", 24) or 24)
        n = max(3, len(str(layer.get("text", ""))))
        w, h = int(n * size * 0.52), int(size * 1.2)
        a = str(layer.get("anchor", "la"))
        ax = {"l": 0, "m": -w // 2, "r": -w}.get(a[0], 0)
        ay = {"a": 0, "t": 0, "m": -h // 2, "d": -h}.get(
            a[1] if len(a) > 1 else "a", 0)
        return (x + ax, y + ay, x + ax + w, y + ay + h)
    return (x, y, x + 40, y + 40)


class Editor:
    def __init__(self, root, path, toplevel=None, sensors=None, on_change=None,
                 look=None):
        """root - контейнер, в который встроиться. toplevel - окно, к нему
        привязываются клавиши и заголовок. sensors - общий сбор датчиков.
        look - оформление окна, если редактор встроен в общую программу."""
        self.root = root
        self.top = toplevel if toplevel is not None else root
        self.on_change = on_change
        self.look = look
        self.app_ref = None      # общее окно, если редактор внутри него
        self.path = path
        self.dirty = False
        with open(path, encoding="utf-8") as f:
            self.cfg = json.load(f)
        self.layers = self.cfg.setdefault("layers", [])
        self.sel = 0
        self.job = None
        self.guides = []
        # Отмена действий: держим снимки описания целиком. Тема весит
        # десятки килобайт, так что полсотни снимков ничего не стоят,
        # зато отменяется что угодно, включая смену типа блока.
        self.history = []
        self.future = []
        self._mark_label = None
        self._mark_time = 0.0
        self.clipboard = None
        self.snap_on = True        # притягивать к краям соседних слоёв
        self.react_test = None     # придуманное значение для предпросмотра
        self.loop_test = None      # застывшая точка повтора, 0..1
        self.find_text = ""        # что ищем в списке слоёв
        self.find_when = "all"     # все слои, только ночные, только дневные
        self.shown = []            # какие слои сейчас в списке
        self.sels = []             # выбранные слои, все сразу
        self.grid_step = 0         # шаг сетки, 0 - выключена
        self.zoom = 1.0            # во сколько раз холст крупнее натуры
        self.streaming = False
        # True, пока поля настроек перечитываются из описания: их правки
        # в этот момент обратно в тему писать не нужно
        self._loading = False
        self.stream_stop = threading.Event()
        self.fonts = all_fonts()
        self.active = True      # открыта ли вкладка редактора
        self.own_sensors = sensors is None
        self.sensors = sensors or sensors_mod.Sensors()
        self.data = {}
        self.W = int(self.cfg.get("screen", {}).get("width", 960))
        self.H = int(self.cfg.get("screen", {}).get("height", 480))

        self._build()
        self._fill_list()
        self._refresh_props()
        self._tick()

    # --- интерфейс ------------------------------------------------------

    def _build(self):
        bar = ttk.Frame(self.root, padding=6)
        bar.pack(fill="x")
        if self.on_change is not None:      # встроен в общее окно
            ttk.Button(bar, text="←  К темам",
                       command=self._back_to_themes).pack(side="left",
                                                          padx=(0, 12))
        ttk.Button(bar, text="Сохранить", command=self.save).pack(side="left")
        ttk.Button(bar, text="Сохранить как…", command=self.save_as).pack(side="left", padx=4)
        ttk.Button(bar, text="Вернуть с диска", command=self.reload).pack(side="left")
        ttk.Button(bar, text="Открыть тему…",
                   command=self.open_theme).pack(side="left", padx=6)
        ttk.Button(bar, text="Описание темы…",
                   command=self.edit_meta).pack(side="left")

        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y",
                                                   padx=8, pady=2)
        ttk.Button(bar, text="↶", width=3, command=self.undo).pack(side="left")
        ttk.Button(bar, text="↷", width=3, command=self.redo).pack(side="left",
                                                                   padx=(2, 8))
        self.snap_btn = ttk.Button(bar, text="●  Магнит", width=11,
                                   style="Accent.TButton",
                                   command=self.toggle_snap)
        self.snap_btn.pack(side="left")
        self.grid_btn = ttk.Button(bar, text="○  Сетка", width=11,
                                   command=self.toggle_grid)
        self.grid_btn.pack(side="left", padx=(4, 0))

        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y",
                                                   padx=8, pady=2)
        ttk.Label(bar, text="Выровнять:", style="Dim.TLabel").pack(side="left")
        for text, how, tip in (
                ("⇤", "left", "К левому краю экрана"),
                ("⇔", "cx", "По центру экрана вбок"),
                ("⇥", "right", "К правому краю экрана"),
                ("⇞", "top", "К верхнему краю экрана"),
                ("⇕", "cy", "По центру экрана вниз"),
                ("⇟", "bottom", "К нижнему краю экрана")):
            b = ttk.Button(bar, text=text, width=3,
                           command=lambda h=how: self.align(h))
            b.pack(side="left", padx=1)
            self._hint_text(b, tip)

        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y",
                                                   padx=8, pady=2)
        ttk.Label(bar, text="Размер:", style="Dim.TLabel").pack(side="left")
        for text, k, tip in (
                ("−", 1 / 1.1, "Уменьшить выбранные слои на десятую часть"),
                ("+", 1.1, "Увеличить выбранные слои на десятую часть")):
            b = ttk.Button(bar, text=text, width=3,
                           command=lambda f=k: self.resize(f))
            b.pack(side="left", padx=1)
            self._hint_text(b, t(tip) + t(". Работает и на нескольких сразу: "
                                          "выдели их в списке с Ctrl или Shift."))
        self.stream_btn = ttk.Button(bar, text="Показать на экране",
                                     command=self.toggle_stream)
        if self.on_change is None:
            self.stream_btn.pack(side="right")
        self.status = ttk.Label(bar, text="")
        self.status.pack(side="right", padx=10)

        body = ttk.Frame(self.root)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body, padding=(6, 6, 4, 6))
        left.pack(side="left", fill="y")
        ttk.Label(left, text="Слои · нижние перекрываются верхними",
                  style="Dim.TLabel", wraplength=190,
                  justify="left").pack(anchor="w")

        # Тем на три десятка слоёв список превращается в простыню, где
        # половина - дневные двойники. Поиск и фильтр сокращают его вдвое.
        self.findvar = tk.StringVar()
        find = ttk.Entry(left, textvariable=self.findvar, width=18)
        find.pack(fill="x", pady=(4, 3))
        self.findvar.trace_add("write", lambda *a: self._set_find())
        self._hint(find, "__find")

        when = ttk.Frame(left)
        when.pack(fill="x", pady=(0, 4))
        self.whenvar = tk.StringVar(value="all")
        for label, val in (("все", "all"), ("ночь", "night"), ("день", "day")):
            ttk.Radiobutton(when, text=label, value=val, variable=self.whenvar,
                            command=self._set_when).pack(side="left")
        self.listbox = tk.Listbox(left, width=20, height=20, exportselection=False,
                                  activestyle="none", selectmode="extended")
        self.listbox.pack(fill="y", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=4)
        for text, cmd in (("↑", lambda: self.move(-1)), ("↓", lambda: self.move(1)),
                          ("Скрыть", self.toggle_hide), ("Копия", self.duplicate),
                          ("Удалить", self.delete)):
            ttk.Button(btns, text=text, width=7, command=cmd).pack(side="left", padx=1)

        add = ttk.Frame(left)
        add.pack(fill="x")
        ttk.Label(add, text="Добавить:").pack(side="left")
        self.newtype = tk.StringVar(value=t(ADD_LIST[0][0]))
        ttk.Combobox(add, textvariable=self.newtype, width=14, state="readonly",
                     values=[t(p[0]) for p in ADD_LIST]).pack(side="left", padx=3)
        ttk.Button(add, text="+", width=3, command=self.add_layer).pack(side="left")

        mid = ttk.Frame(body, padding=(4, 6))
        mid.pack(side="left")
        self.canvas = tk.Canvas(mid, width=self.W, height=self.H, bg="black",
                                highlightthickness=1, highlightbackground="#444")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        day = ttk.Frame(mid)
        day.pack(fill="x", pady=4)
        ttk.Label(day, text="Режим правки:").pack(side="left")
        self.view = tk.StringVar(value="night")
        for label, val in (("Ночной вид", "night"),
                           ("Переход", "trans"),
                           ("Дневной вид", "day")):
            ttk.Radiobutton(day, text=label, value=val, variable=self.view,
                            command=self._switch_view).pack(side="left", padx=3)

        self.scrub_box = ttk.Frame(mid)
        ttk.Label(self.scrub_box, text="Прокрутка перехода:").pack(side="left")
        self.dayvar = tk.DoubleVar(value=0.5)
        ttk.Scale(self.scrub_box, from_=0.0, to=1.0, variable=self.dayvar,
                  length=220, command=lambda v: self._render()).pack(side="left",
                                                                     padx=6)
        self.daylabel = ttk.Label(self.scrub_box, text="50 %", width=8)
        self.daylabel.pack(side="left")

        ttk.Label(mid, style="Dim.TLabel", justify="left",
                  text="Двигается только выбранный слой. Стрелки — на пиксель, "
                       "Shift+стрелки — на десять.\n"
                       "Магнит притягивает к краям и центрам соседей; "
                       "Alt при перетаскивании временно его отключает.\n"
                       "Несколько слоёв разом: Ctrl+щелчок или Shift+щелчок в списке.\n"
                       "Ctrl+Z отменить · Ctrl+Y вернуть · Ctrl+C, Ctrl+V, "
                       "Ctrl+D · Ctrl+S сохранить · Delete удалить"
                  ).pack(anchor="w", pady=4)

        for key in ("<Left>", "<Right>", "<Up>", "<Down>",
                    "<Shift-Left>", "<Shift-Right>", "<Shift-Up>", "<Shift-Down>"):
            self.top.bind(key, self._on_key)
        for key, fn in (("<Control-z>", self.undo), ("<Control-Z>", self.undo),
                        ("<Control-y>", self.redo), ("<Control-Y>", self.redo),
                        ("<Control-c>", self.copy_layer),
                        ("<Control-x>", self.cut_layer),
                        ("<Control-v>", self.paste_layer),
                        ("<Control-d>", self._dup_key),
                        ("<Control-s>", self._save_key),
                        ("<Delete>", self._delete_key)):
            self.top.bind(key, self._guarded(fn))

        right = ttk.Frame(body, padding=6, width=PROPS_W + 22)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        head = ttk.Frame(right)
        head.pack(fill="x")
        ttk.Label(head, text="Тип блока", width=20).pack(side="left")
        self.typevar = tk.StringVar()
        cb = ttk.Combobox(head, textvariable=self.typevar, width=16, state="readonly",
                          values=[t(p[0]) for p in TYPES])
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", self._change_type)

        canv = tk.Canvas(right, highlightthickness=0, bd=0, width=PROPS_W)
        scroll = ttk.Scrollbar(right, orient="vertical", command=canv.yview)
        self.props = ttk.Frame(canv)
        win = canv.create_window((0, 0), window=self.props, anchor="nw",
                                 width=PROPS_W)
        self.props.bind("<Configure>",
                        lambda e: canv.configure(scrollregion=canv.bbox("all")))
        canv.bind("<Configure>",
                  lambda e: canv.itemconfigure(win, width=e.width))
        canv.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canv.pack(side="left", fill="both", expand=True, pady=6)
        canv.bind("<MouseWheel>",
                  lambda e: canv.yview_scroll(-int(e.delta / 120), "units"))
        self.props_canvas = canv

        # Порядок важен: pack раздаёт место в порядке вызовов. Холст
        # растягивается под окно, и если он встанет раньше колонки
        # свойств, то заберёт всё, а свойствам не останется ничего.
        # Поэтому середину перекладываем последней.
        mid.pack_forget()
        mid.pack(side="left", fill="both", expand=True, before=None)

        scr = ttk.LabelFrame(self.root, text="Экран", padding=4)
        scr.pack(fill="x", padx=6, pady=4)

        # ссылки на поля раздела «Экран»: при открытии другой темы их
        # нужно перечитать, иначе они показывают числа от прежней
        self.screen_vars = {}

        # Частота кадров, качество, сглаживание и длительность перехода
        # переехали в «Настройки»: их задают один раз, а место в редакторе
        # они занимали постоянно. Здесь остаётся только то, что относится
        # к внешнему виду темы.
        self.modevar = tk.StringVar(
            value=str(self.cfg.get("screen", {}).get("day_mode", "auto")))
        self._build_background(scr)

    def _refresh_screen_fields(self):
        """Перечитать поля раздела «Экран» из описания темы."""
        screen = self.cfg.get("screen", {})
        self._loading = True
        try:
            self.modevar.set(str(screen.get("day_mode", "auto")))
            for key, var in self.screen_vars.items():
                var.set(str(screen.get(key, "")))
            for key, (var, _) in getattr(self, "bg_swatch", {}).items():
                var.set(str(screen.get(key, "")))
                self._paint_swatch(key)
            if hasattr(self, "packvar"):
                self.packvar.set(bool(screen.get("pack_frames", True)))
        finally:
            self._loading = False

    # --- заливка под всеми слоями ----------------------------------------

    def _build_background(self, parent):
        """Два цвета фона: ночной и дневной.

        Это та самая заливка, из-за которой ночью экран чёрный, а днём
        голубой. В описании темы она лежит отдельно от слоёв, поэтому
        в списке блоков её не видно и найти её было негде.
        """
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(6, 0))
        ttk.Label(row, text="Фон под всеми блоками:").pack(side="left", padx=(8, 6))

        self.bg_swatch = {}
        self._bg_field(row, "background", "ночью", "#000000")
        self._bg_field(row, "background_day", "днём", "")

        ttk.Button(row, text="Убрать дневной", width=16,
                   command=lambda: self._set_screen_color(
                       "background_day", None)).pack(side="left", padx=6)
        ttk.Label(row, foreground="#888",
                  text="нет дневного — фон ночной круглые сутки"
                  ).pack(side="left", padx=(8, 20))

        self.packvar = tk.BooleanVar(
            value=bool(self.cfg.get("screen", {}).get("pack_frames", True)))
        ttk.Checkbutton(row, text="Сжимать кадры фона", variable=self.packvar,
                        command=self._set_pack).pack(side="left")
        ttk.Label(row, foreground="#888",
                  text="памяти вчетверо меньше, картинка та же"
                  ).pack(side="left", padx=8)

    def _set_pack(self):
        """Сжимать ли кадры фона в памяти.

        Кадры уже разобраны и лежат в общей памяти, поэтому их приходится
        готовить заново - на большом ролике это пара секунд.
        """
        if self._loading:
            return
        on = bool(self.packvar.get())
        self.cfg.setdefault("screen", {})["pack_frames"] = on
        panel_mod._PREPARED.clear()
        self.status.config(text=t("кадры фона будут сжаты — готовлю заново")
                           if on else
                           t("кадры фона будут распакованы — готовлю заново"))
        self._changed(keep_props=True)

    def _bg_field(self, row, key, label, default):
        """Поле с шестнадцатеричным цветом и квадратиком для выбора мышкой."""
        ttk.Label(row, text=label).pack(side="left", padx=(6, 3))
        var = tk.StringVar(value=str(self.cfg.get("screen", {}).get(key, default)))
        ttk.Entry(row, textvariable=var, width=10).pack(side="left")
        # рамка нужна, чтобы чёрный квадратик не сливался с тёмным окном
        btn = tk.Button(row, width=3, relief="flat", takefocus=0,
                        borderwidth=0, highlightthickness=1,
                        highlightbackground="#4a5568", highlightcolor="#4a5568",
                        command=lambda v=var: self._pick_color(v))
        btn.pack(side="left", padx=(3, 0))
        self.bg_swatch[key] = (var, btn)
        self._paint_swatch(key)
        var.trace_add("write",
                      lambda *a, k=key, v=var: self._set_screen_color(k, v))

    def _paint_swatch(self, key):
        """Перекрасить квадратик рядом с полем в текущий цвет."""
        pair = getattr(self, "bg_swatch", {}).get(key)
        if not pair:
            return
        var, btn = pair
        c = panel_mod.parse_color(var.get().strip() or None)
        try:
            if c:
                colour = "#{:02x}{:02x}{:02x}".format(*c[:3])
                btn.config(bg=colour, activebackground=colour, text="")
            else:
                btn.config(bg="#2a2f3a", activebackground="#2a2f3a", text="—")
        except Exception:
            pass

    def _set_screen_color(self, key, var):
        """Записать цвет фона. Пустая строка убирает его из описания."""
        if var is None:                      # нажали «Убрать дневной»
            self.bg_swatch[key][0].set("")
            return
        if self._loading:
            return
        s = var.get().strip()
        screen = self.cfg.setdefault("screen", {})
        if s == "":
            screen.pop(key, None)
        else:
            if not s.startswith("#"):
                s = "#" + s
            if panel_mod.parse_color(s) is None:
                return                       # цвет ещё дописывают, ждём
            screen[key] = s
        self._paint_swatch(key)
        self._changed(keep_props=True)

    # --- отмена действий -------------------------------------------------

    def remember(self, label=""):
        """Запомнить состояние перед изменением.

        Правки одного рода, идущие подряд, склеиваются в одну отмену:
        иначе перетаскивание мышью оставляло бы сотню снимков, и Ctrl+Z
        двигал бы блок по пикселю.
        """
        now = time.time()
        if (self.history and label and self._mark_label == label
                and now - self._mark_time < 0.7):
            self._mark_time = now
            return
        self.history.append(copy.deepcopy(self.cfg))
        if len(self.history) > 60:
            self.history.pop(0)
        self.future.clear()
        self._mark_label, self._mark_time = label, now

    def undo(self, _=None):
        if not self.history:
            self.status.config(text="отменять нечего")
            return
        self.future.append(copy.deepcopy(self.cfg))
        self._restore(self.history.pop())
        self.status.config(text="отменено")

    def redo(self, _=None):
        if not self.future:
            self.status.config(text="возвращать нечего")
            return
        self.history.append(copy.deepcopy(self.cfg))
        self._restore(self.future.pop())
        self.status.config(text="возвращено")

    def _restore(self, cfg):
        self.cfg = cfg
        self.layers = self.cfg.setdefault("layers", [])
        self.sel = max(0, min(self.sel, len(self.layers) - 1))
        self._mark_label = None
        self._refresh_screen_fields()
        self.dirty = True
        self._fill_list()
        self._refresh_props()
        self._render()

    # --- буфер обмена ----------------------------------------------------

    def copy_layer(self, _=None):
        """Слой уходит в общий буфер обмена текстом.

        Не своя коробочка внутри программы, а именно буфер Windows:
        тогда слой можно вставить в другую тему, в другое окно программы
        или просто послать человеку сообщением.
        """
        if not self.layers:
            return
        self.clipboard = copy.deepcopy(self.layers[self.sel])
        try:
            self.top.clipboard_clear()
            self.top.clipboard_append(json.dumps(
                {"txw818_layer": self.clipboard}, ensure_ascii=False, indent=1))
        except Exception:
            pass
        self.status.config(text="слой скопирован")

    def cut_layer(self, _=None):
        if not self.layers:
            return
        self.copy_layer()
        self.remember("вырезать")
        self.layers.pop(self.sel)
        self.sel = max(0, self.sel - 1)
        self._changed()
        self.status.config(text="слой вырезан")

    def paste_layer(self, _=None):
        """Вставить слой из буфера. Понимает и то, что скопировали в другом окне."""
        layer = None
        try:
            text = self.top.clipboard_get()
            got = json.loads(text)
            if isinstance(got, dict) and "txw818_layer" in got:
                layer = got["txw818_layer"]
            elif isinstance(got, dict) and "type" in got:
                layer = got
        except Exception:
            layer = None
        if layer is None:
            layer = self.clipboard
        if not isinstance(layer, dict) or "type" not in layer:
            self.status.config(text="в буфере нет слоя")
            return
        self.remember("вставить")
        new = copy.deepcopy(layer)
        new["name"] = (new.get("name") or t("слой")) + t(" копия")
        new["x"] = int(new.get("x", 0) or 0) + 12
        new["y"] = int(new.get("y", 0) or 0) + 12
        at = min(self.sel + 1, len(self.layers))
        self.layers.insert(at, new)
        self.sel = at
        self._changed()
        self.status.config(text="слой вставлен")

    def toggle_snap(self, _=None):
        """Магнит: притягивать края блока к краям и центрам соседних."""
        self.snap_on = not self.snap_on
        self._show_snap()
        self.status.config(text=t("магнит включён") if self.snap_on
                           else t("магнит выключен"))

    def toggle_grid(self, _=None):
        """Сетка: восемь точек, шестнадцать или выключена."""
        self.grid_step = {0: 8, 8: 16, 16: 0}[self.grid_step]
        self.grid_btn.config(
            text=("○  Сетка" if not self.grid_step
                  else t("●  Сетка {}").format(self.grid_step)),
            style="TButton" if not self.grid_step else "Accent.TButton")
        self.status.config(text=t("сетка выключена") if not self.grid_step
                           else t("сетка по {} точек").format(self.grid_step))
        self._render()

    def align(self, how):
        """Придвинуть слой к краю экрана или поставить по центру."""
        if not self.layers:
            return
        self.remember("выравнивание")
        l = self._store()
        x0, y0, x1, y1 = bbox_of(self._eff(self.layers[self.sel]),
                                 self.W, self.H)
        w, h = x1 - x0, y1 - y0
        x = int(self._get("x") or 0)
        y = int(self._get("y") or 0)
        # двигаем не рамку, а сам слой: считаем, насколько рамка смещена
        # относительно его координат, и сохраняем это смещение
        dx, dy = x - x0, y - y0
        if how == "left":
            l["x"] = dx
        elif how == "cx":
            l["x"] = (self.W - w) // 2 + dx
        elif how == "right":
            l["x"] = self.W - w + dx
        elif how == "top":
            l["y"] = dy
        elif how == "cy":
            l["y"] = (self.H - h) // 2 + dy
        elif how == "bottom":
            l["y"] = self.H - h + dy
        self._changed(keep_props=True)

    # какие поля считаются размером у разных типов слоя
    SIZE_KEYS = ("w", "h", "r", "r_inner", "thickness", "size", "radius",
                 "width", "outline_width", "head")

    def resize(self, factor):
        """Изменить размер выбранных слоёв, сохранив их взаимное положение.

        Растёт не только сам слой, но и расстояние до центра пачки -
        иначе при увеличении соседние слои наезжали бы друг на друга.
        """
        picked = self.chosen()
        if not picked:
            return
        self.remember("размер")
        boxes = [bbox_of(self._eff(self.layers[i]), self.W, self.H)
                 for i in picked]
        cx = sum((b[0] + b[2]) / 2.0 for b in boxes) / len(boxes)
        cy = sum((b[1] + b[3]) / 2.0 for b in boxes) / len(boxes)
        for i in picked:
            l = self.layers[i]
            for key in self.SIZE_KEYS:
                v = l.get(key)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    l[key] = max(1, int(round(v * factor))) if key != "size" \
                        else max(4, int(round(v * factor)))
            for key, c in (("x", cx), ("y", cy)):
                v = l.get(key)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    l[key] = int(round(c + (v - c) * factor))
            for key, c in (("x2", cx), ("y2", cy)):
                v = l.get(key)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    l[key] = int(round(c + (v - c) * factor))
        self.status.config(text=t("размер {:+.0f} % у {} слоёв").format(
            (factor - 1) * 100, len(picked)))
        self._changed(keep_props=True)

    def _hint_text(self, widget, text):
        tip = getattr(getattr(self, "app_ref", None), "tip", None)
        if tip is not None:
            tip.add(widget, text)
        return widget

    def _show_snap(self):
        if hasattr(self, "snap_btn"):
            self.snap_btn.config(text=("●  Магнит" if self.snap_on
                                       else "○  Магнит"),
                                 style="Accent.TButton" if self.snap_on
                                 else "TButton")

    # --- список ---------------------------------------------------------

    def _visible_at(self, layer, f):
        """Видно ли слой при такой доле дня. По ней и делим ночь и день."""
        try:
            eff = panel_mod.apply_variants(layer, f, 0.0, {})
            return float(eff.get("opacity", 1) or 0) > 0.01
        except Exception:
            return True

    def _passes(self, layer):
        """Проходит ли слой через поиск и фильтр."""
        if self.find_text:
            hay = "{} {} {}".format(layer.get("name", ""), layer.get("type", ""),
                                    layer.get("text", "")).lower()
            if self.find_text not in hay:
                return False
        if self.find_when == "night":
            return self._visible_at(layer, 0.0)
        if self.find_when == "day":
            return self._visible_at(layer, 1.0)
        return True

    def _set_find(self):
        self.find_text = self.findvar.get().strip().lower()
        self._fill_list()

    def _set_when(self):
        self.find_when = self.whenvar.get()
        self._fill_list()

    def _fill_list(self):
        self.listbox.delete(0, "end")
        self.shown = []
        for i, l in enumerate(self.layers):
            if not self._passes(l):
                continue
            self.shown.append(i)
            mark = "× " if l.get("hidden") else "  "
            self.listbox.insert("end", "{}{:2d}. {}".format(
                mark, i + 1, l.get("name") or l.get("type")))
        if self.layers:
            self.sel = max(0, min(self.sel, len(self.layers) - 1))
            self.listbox.selection_clear(0, "end")
            keep = [i for i in (self.sels or [self.sel]) if i in self.shown]
            if not keep and self.sel in self.shown:
                keep = [self.sel]
            for i in keep:
                self.listbox.selection_set(self.shown.index(i))
            if keep:
                self.listbox.see(self.shown.index(keep[0]))
                self.sels = keep
        if hasattr(self, "status") and (self.find_text or self.find_when != "all"):
            self.status.config(text=t("показано {} из {}").format(
                len(self.shown), len(self.layers)))

    def _on_select(self, _=None):
        got = self.listbox.curselection()
        if not got:
            return
        self.sels = [self.shown[a] if a < len(self.shown) else a for a in got]
        self.sel = self.sels[0]        # главный - по нему показаны свойства
        self._refresh_props()
        self._render()

    def chosen(self):
        """Слои, с которыми работаем. Всегда хотя бы один."""
        if self.sels and all(0 <= i < len(self.layers) for i in self.sels):
            return list(self.sels)
        return [self.sel] if self.layers else []

    def move(self, d):
        i, j = self.sel, self.sel + d
        if 0 <= j < len(self.layers):
            self.remember("порядок")
            self.layers[i], self.layers[j] = self.layers[j], self.layers[i]
            self.sel = j
            self._changed()

    def toggle_hide(self):
        if not self.layers:
            return
        self.remember("скрыть")
        # ориентируемся на главный: если он был виден - прячем всю пачку
        hide = not self.layers[self.sel].get("hidden")
        for i in self.chosen():
            if hide:
                self.layers[i]["hidden"] = True
            else:
                self.layers[i].pop("hidden", None)
        self._changed()

    def duplicate(self):
        if self.layers:
            self.remember("копия")
            c = copy.deepcopy(self.layers[self.sel])
            c["name"] = (c.get("name") or t("блок")) + t(" копия")
            c["x"] = int(c.get("x", 0) or 0) + 12
            c["y"] = int(c.get("y", 0) or 0) + 12
            self.layers.insert(self.sel + 1, c)
            self.sel += 1
            self._changed()

    def delete(self):
        picked = self.chosen()
        if not picked:
            return
        what = (t("Удалить слой «{}»?").format(
            self.layers[self.sel].get("name", t("слой"))) if len(picked) == 1
            else t("Удалить выбранные слои ({} шт.)?").format(len(picked)))
        if not messagebox.askyesno(t("Удалить"), what):
            return
        self.remember("удаление")
        for i in sorted(picked, reverse=True):   # с конца, иначе номера съедут
            self.layers.pop(i)
        self.sel = max(0, min(self.sel, len(self.layers) - 1))
        self.sels = [self.sel] if self.layers else []
        self._changed()

    def add_layer(self):
        kind = self._value_of(ADD_LIST, self.newtype.get())
        if kind not in NEW_LAYER:
            return
        self.remember("новый слой")
        new = copy.deepcopy(NEW_LAYER[kind])
        new["name"] = t(new.get("name", ""))
        self.layers.append(new)
        self.sel = len(self.layers) - 1
        self._changed()

    def _change_type(self, _=None):
        if not self.layers:
            return
        kind = self._value_of(TYPES, self.typevar.get())
        l = self.layers[self.sel]
        if l.get("type") == kind or kind not in NEW_LAYER:
            return
        self.remember("смена типа")
        base = copy.deepcopy(NEW_LAYER[kind])
        base["name"] = l.get("name", base["name"])
        base["x"], base["y"] = l.get("x", base["x"]), l.get("y", base["y"])
        for k in ("value", "min", "max", "fill", "back", "opacity", "color"):
            if k in l and k in base:
                base[k] = l[k]
        self.layers[self.sel] = base
        self._changed()

    # --- свойства -------------------------------------------------------

    def _refresh_props(self):
        for w in self.props.winfo_children():
            w.destroy()
        if not self.layers:
            return
        layer = self.layers[self.sel]
        kind = layer.get("type", "text")
        self.typevar.set(self._label_of(TYPES, kind) or kind)
        view = self.view.get()

        if view == "trans":
            ttk.Label(self.props,
                      text="Здесь настраивается только движение.\n"
                           "Что именно меняется — задаётся\n"
                           "в ночном и дневном видах.",
                      foreground="#888").pack(anchor="w", pady=4)
            self._anim_section(layer)
            self._motion_section(layer)
            return

        if view == "day":
            head = ttk.Frame(self.props)
            head.pack(fill="x", pady=2)
            ttk.Label(head, text="Правки уходят в дневной вид",
                      foreground="#0a7").pack(side="left")
            ttk.Button(head, text="Сбросить",
                       command=self.reset_day_all).pack(side="right")

        # раскладываем поля по разделам, порядок внутри раздела прежний
        by_group = {}
        for item in fields_for(kind):
            by_group.setdefault(GROUP_OF.get(item[0], "Прочее"), []).append(item)
        for group_name, _keys in GROUPS + [("Прочее", [])]:
            items = by_group.get(group_name)
            if not items:
                continue
            ttk.Label(self.props, text=t(group_name).upper(),
                      style="Faint.TLabel").pack(anchor="w", pady=(14, 2))
            ttk.Separator(self.props, orient="horizontal").pack(fill="x",
                                                                pady=(0, 6))
            self._props_rows(items)

        self._anim_section(layer)
        self._motion_section(layer)

    def _props_rows(self, items):
        """Строки одного раздела свойств."""
        layer = self.layers[self.sel]
        for key, label, spec in items:
            row = ttk.Frame(self.props)
            row.pack(fill="x", pady=2)
            cap = ttk.Label(row, text=label, width=18, anchor="w",
                            style="Dim.TLabel")
            cap.pack(side="left")
            self._hint(row, key)
            self._hint(cap, key)
            cur = self._get(key)

            if spec == "preset":
                var = tk.StringVar(value=self._preset_label(layer.get("text")))
                cb = ttk.Combobox(row, textvariable=var, width=32, state="readonly",
                                  values=[t(p[0]) for p in TEXT_PRESETS])
                cb.pack(side="left")
                cb.bind("<<ComboboxSelected>>",
                        lambda e, v=var: self._apply_preset(v.get()))
                continue

            if spec == "bool" or spec.startswith("bool:"):
                on = spec.split(":", 1)[1] if ":" in spec else True
                var = tk.BooleanVar(value=bool(cur))
                ttk.Checkbutton(row, variable=var,
                                command=lambda k=key, v=var, o=on:
                                self._set(k, o if v.get() else None)).pack(side="left")
                continue

            if spec == "sensor":
                var = tk.StringVar(value=self._label_of(SENSORS, cur))
                cb = ttk.Combobox(row, textvariable=var, width=32, state="readonly",
                                  values=[t(s[0]) for s in SENSORS])
                cb.pack(side="left")
                cb.bind("<<ComboboxSelected>>",
                        lambda e, k=key, v=var: self._set(k, self._value_of(SENSORS, v.get())))
                continue

            if spec == "font":
                var = tk.StringVar(value=self._label_of(self.fonts, cur) or str(cur or ""))
                cb = ttk.Combobox(row, textvariable=var, width=32,
                                  values=[t(f[0]) for f in self.fonts])
                cb.pack(side="left")
                cb.bind("<<ComboboxSelected>>",
                        lambda e, k=key, v=var: self._set(k, self._value_of(self.fonts, v.get())))
                ttk.Button(row, text="…", width=3,
                           command=lambda k=key: self._pick_font(k)).pack(side="left")
                continue

            if spec.startswith("list:"):
                table = {"anchors": ANCHORS, "directions": DIRECTIONS,
                         "gaps": GAPS, "fits": FITS,
                         "gradients": GRADIENTS}[spec.split(":", 1)[1]]
                var = tk.StringVar(value=self._label_of(table, cur))
                cb = ttk.Combobox(row, textvariable=var, width=32, state="readonly",
                                  values=[t(p[0]) for p in table])
                cb.pack(side="left")
                cb.bind("<<ComboboxSelected>>",
                        lambda e, k=key, v=var, tab=table:
                        self._set(k, self._value_of(tab, v.get())))
                continue

            var = tk.StringVar(value="" if cur is None else str(cur))
            width = 30 if spec in ("text", "path") else 12
            ttk.Entry(row, textvariable=var, width=width).pack(side="left")
            if spec == "color":
                ttk.Button(row, text="…", width=3,
                           command=lambda v=var: self._pick_color(v)).pack(side="left")
            if spec == "path":
                ttk.Button(row, text="…", width=3,
                           command=lambda v=var: self._pick_path(v)).pack(side="left")
            var.trace_add("write",
                          lambda *a, k=key, v=var, s=spec: self._set_text(k, v, s))

    def _hint(self, widget, key):
        """Привязать к полю пояснение из HINTS, если оно там есть."""
        tip = getattr(getattr(self, "app_ref", None), "tip", None)
        if tip is not None and HINTS.get(key):
            tip.add(widget, HINTS[key])
        return widget

    def _anim_section(self, layer):
        """Настройки перехода блока между ночным и дневным видом."""
        box = ttk.LabelFrame(self.props, text="Переход к дневному виду", padding=4)
        box.pack(fill="x", pady=8)

        has_day = isinstance(layer.get("day"), dict)
        ttk.Label(box, text=("настроен" if has_day else "не настроен"),
                  foreground=("#0a0" if has_day else "#888")).pack(anchor="w")

        line = ttk.Frame(box)
        line.pack(fill="x", pady=3)
        ttk.Label(line, text="Что меняется:").pack(side="left")
        for name in ANIM_PARTS:
            keys = ANIM_PARTS[name]
            on = has_day and any(k in layer["day"] for k in keys)
            v = tk.BooleanVar(value=on)
            ttk.Checkbutton(line, text=name, variable=v,
                            command=lambda n=name, var=v: self._toggle_part(n, var)
                            ).pack(side="left", padx=2)

        anim = layer.get("anim") or {}
        seg = ttk.Frame(box)
        seg.pack(fill="x", pady=2)
        ttk.Label(seg, text="Отрезок перехода, %", width=22).pack(side="left")
        for key, default in (("start", 0.0), ("end", 1.0)):
            var = tk.StringVar(value="{:.0f}".format(
                float(anim.get(key, default)) * 100))
            ttk.Entry(seg, textvariable=var, width=6).pack(side="left", padx=2)
            var.trace_add("write",
                          lambda *a, k=key, v=var: self._set_anim_pct(k, v))

        for key, label, default in (("ease_in", "Начало", "средне"),
                                    ("ease_mid", "Середина", "средне"),
                                    ("ease_out", "Окончание", "средне")):
            row = ttk.Frame(box)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=label, width=22).pack(side="left")
            # подпись переводится, а в тему уходит русское слово: движок
            # знает только его
            var = tk.StringVar(value=t(str(anim.get(key, default))))
            cb = ttk.Combobox(row, textvariable=var, width=12, state="readonly",
                              values=[t(s[0]) for s in SPEEDS])
            cb.pack(side="left")
            cb.bind("<<ComboboxSelected>>",
                    lambda e, k=key, v=var:
                    self._set_anim(k, self._value_of(SPEEDS, v.get())))

        self.curve = tk.Canvas(box, width=150, height=150, bg="#101014",
                               highlightthickness=1, highlightbackground="#333")
        self.curve.pack(pady=4)
        self._draw_curve(layer)

    def _motion_section(self, layer):
        """Повтор по времени и реакция на датчик."""
        # --- повтор ---
        box = ttk.LabelFrame(self.props, text="Повтор по времени", padding=4)
        box.pack(fill="x", pady=6)
        loop = layer.get("loop") or {}

        row = ttk.Frame(box)
        row.pack(fill="x", pady=1)
        ttk.Label(row, text="Период, секунд", width=22).pack(side="left")
        var = tk.StringVar(value=str(loop.get("seconds", "")))
        ttk.Entry(row, textvariable=var, width=8).pack(side="left")
        var.trace_add("write", lambda *a, v=var: self._set_sub("loop", "seconds",
                                                               v, num=True))

        row = ttk.Frame(box)
        row.pack(fill="x", pady=1)
        ttk.Label(row, text="Как повторять", width=22).pack(side="left")
        mv = tk.StringVar(value=self._label_of(LOOP_MODES,
                                               loop.get("mode") or "pingpong"))
        cb = ttk.Combobox(row, textvariable=mv, width=14, state="readonly",
                          values=[t(m[0]) for m in LOOP_MODES])
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e, v=mv: self._set_sub_val(
            "loop", "mode", self._value_of(LOOP_MODES, v.get())))

        row = ttk.Frame(box)
        row.pack(fill="x", pady=(8, 2))
        ttk.Label(row, text="Показать в момент", width=22,
                  style="Dim.TLabel").pack(side="left")
        self.loopvar = tk.DoubleVar(value=self.loop_test or 0.0)
        ttk.Scale(row, from_=0.0, to=1.0, variable=self.loopvar, length=120,
                  command=lambda _v: self._loop_preview()).pack(side="left")
        ttk.Button(row, text="сброс", style="Quiet.TButton", width=6,
                   command=self._loop_off).pack(side="left", padx=4)

        line = ttk.Frame(box)
        line.pack(fill="x", pady=2)
        ttk.Label(line, text="Что меняется:").pack(side="left")
        for name in ANIM_PARTS:
            keys = ANIM_PARTS[name]
            on = any(k in (loop.get("to") or {}) for k in keys)
            v = tk.BooleanVar(value=on)
            ttk.Checkbutton(line, text=name, variable=v,
                            command=lambda n=name, var=v:
                            self._toggle_target("loop", "to", n, var)
                            ).pack(side="left", padx=1)

        # --- реакция на датчик ---
        box = ttk.LabelFrame(self.props, text="Реакция на датчик", padding=4)
        box.pack(fill="x", pady=6)
        react = layer.get("react") or {}

        row = ttk.Frame(box)
        row.pack(fill="x", pady=1)
        ttk.Label(row, text="Датчик", width=22).pack(side="left")
        sv = tk.StringVar(value=self._label_of(SENSORS, react.get("value")))
        cb = ttk.Combobox(row, textvariable=sv, width=28, state="readonly",
                          values=[""] + [t(s[0]) for s in SENSORS])
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e, v=sv: self._set_sub_val(
            "react", "value", self._value_of(SENSORS, v.get())))

        for key, label, default in (("from", "Начинает меняться при", 70),
                                    ("to", "Полностью при", 90)):
            row = ttk.Frame(box)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=label, width=22).pack(side="left")
            v = tk.StringVar(value=str(react.get(key, default)))
            ttk.Entry(row, textvariable=v, width=8).pack(side="left")
            v.trace_add("write", lambda *a, k=key, var=v:
                        self._set_sub("react", k, var, num=True))

        line = ttk.Frame(box)
        line.pack(fill="x", pady=2)
        ttk.Label(line, text="Что меняется:").pack(side="left")
        for name in ANIM_PARTS:
            keys = ANIM_PARTS[name]
            on = any(k in (react.get("to_state") or {}) for k in keys)
            v = tk.BooleanVar(value=on)
            ttk.Checkbutton(line, text=name, variable=v,
                            command=lambda n=name, var=v:
                            self._toggle_target("react", "to_state", n, var)
                            ).pack(side="left", padx=1)

        # Показания сейчас могут быть далеко от порога, и увидеть реакцию
        # было нельзя, пока железо реально не нагреется. Этот ползунок
        # подставляет любое значение прямо в предпросмотр.
        try:
            lo = float(react.get("from", 70))
            hi = float(react.get("to", 90))
        except (TypeError, ValueError):
            lo, hi = 70.0, 90.0
        prev = ttk.Frame(box)
        prev.pack(fill="x", pady=(8, 2))
        ttk.Label(prev, text="Показать при значении",
                  style="Dim.TLabel").pack(anchor="w")
        line2 = ttk.Frame(box)
        line2.pack(fill="x")
        span = max(1.0, hi - lo)
        self.reactvar = tk.DoubleVar(value=self.react_test
                                     if self.react_test is not None else lo)
        ttk.Scale(line2, from_=lo - span * 0.4, to=hi + span * 0.4,
                  variable=self.reactvar, length=170,
                  command=lambda _v: self._react_preview()).pack(side="left")
        self.react_lbl = ttk.Label(line2, text="—", style="Dim.TLabel", width=7)
        self.react_lbl.pack(side="left", padx=4)
        ttk.Button(line2, text="сброс", style="Quiet.TButton", width=6,
                   command=self._react_off).pack(side="left")

    def _loop_preview(self):
        """Замереть в выбранной точке повтора, вместо бега по времени."""
        self.loop_test = float(self.loopvar.get())
        self._render(fast=True)

    def _loop_off(self):
        self.loop_test = None
        self._render()

    def _react_preview(self):
        """Подставить в предпросмотр придуманное значение датчика."""
        self.react_test = float(self.reactvar.get())
        self.react_lbl.config(text="{:.0f}".format(self.react_test))
        self._render(fast=True)

    def _react_off(self):
        """Вернуться к настоящим показаниям."""
        self.react_test = None
        if hasattr(self, "react_lbl"):
            self.react_lbl.config(text="—")
        self._render()

    def _set_sub(self, section, key, var, num=False):
        s = var.get().strip().replace(",", ".")
        d = self.layers[self.sel].setdefault(section, {})
        if s == "":
            d.pop(key, None)
        elif num:
            try:
                d[key] = float(s)
            except ValueError:
                return
        else:
            d[key] = s
        if not d:
            self.layers[self.sel].pop(section, None)
        self._changed(keep_props=True)

    def _set_sub_val(self, section, key, value):
        if value in (None, ""):
            d = self.layers[self.sel].get(section) or {}
            d.pop(key, None)
        else:
            self.layers[self.sel].setdefault(section, {})[key] = value
        self._changed(keep_props=True)

    def _toggle_target(self, section, sub, name, var):
        """Включить или выключить поля в целевом наборе повтора или реакции."""
        l = self.layers[self.sel]
        d = l.setdefault(section, {})
        target = d.setdefault(sub, {})
        for k in ANIM_PARTS[name]:
            if var.get():
                if k in l and k not in target:
                    target[k] = l[k]
            else:
                target.pop(k, None)
        if not target:
            d.pop(sub, None)
        if not d:
            l.pop(section, None)
        self._changed()

    def _draw_curve(self, layer):
        """Нарисовать кривую перехода, как в видеоредакторе."""
        c = self.curve
        c.delete("all")
        w = h = 150
        for i in range(1, 4):
            c.create_line(i * w / 4, 0, i * w / 4, h, fill="#232630")
            c.create_line(0, i * h / 4, w, i * h / 4, fill="#232630")
        pts = []
        for i in range(61):
            x = i / 60.0
            y = panel_mod.layer_progress(layer, x)
            pts += [8 + x * (w - 16), h - 8 - y * (h - 16)]
        c.create_line(pts, fill="#4aa8ff", width=2, smooth=True)
        # холст крючок перевода не трогает - переводим сами
        c.create_text(6, h - 4, text=t("ночь"), anchor="sw", fill="#666",
                      font=("", 7))
        c.create_text(w - 4, 8, text=t("день"), anchor="ne", fill="#666",
                      font=("", 7))

    def _toggle_part(self, name, var):
        self.remember("дневной вид")
        l = self.layers[self.sel]
        day = l.setdefault("day", {})
        keys = ANIM_PARTS[name]
        if var.get():
            for k in keys:
                if k in l and k not in day:
                    day[k] = l[k]     # начальное значение равно ночному
        else:
            for k in keys:
                day.pop(k, None)
        if not day:
            l.pop("day", None)
        self._changed()

    def _set_anim(self, key, value):
        self.layers[self.sel].setdefault("anim", {})[key] = value
        self._changed()

    def _set_anim_pct(self, key, var):
        try:
            v = float(var.get().replace(",", ".")) / 100.0
        except ValueError:
            return
        self.layers[self.sel].setdefault("anim", {})[key] = max(0.0, min(1.0, v))
        self._changed(keep_props=True)
        if hasattr(self, "curve"):
            self._draw_curve(self.layers[self.sel])

    @staticmethod
    def _label_of(table, value):
        for label, val in table:
            if val == value:
                return t(label)
        return ""

    @staticmethod
    def _value_of(table, label):
        """Значение по подписи. Подпись приходит с языка окна, поэтому
        сверяем и с исходной русской, и с переведённой."""
        for lab, val in table:
            if lab == label or t(lab) == label:
                return val
        return label

    def _preset_label(self, text):
        for label, tpl in TEXT_PRESETS:
            if tpl == text:
                return t(label)
        return t(TEXT_PRESETS[0][0])

    def _apply_preset(self, label):
        tpl = self._value_of(TEXT_PRESETS, label)
        if tpl and tpl != label:
            self.layers[self.sel]["text"] = tpl
            self._changed()

    def _pick_font(self, key):
        """Выбрать файл шрифта вручную, если его нет в списке."""
        start = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts")
        if not os.path.isdir(start):
            start = r"C:\Windows\Fonts"
        p = filedialog.askopenfilename(
            title=t("Выбери файл шрифта"), initialdir=start,
            filetypes=[(t("Шрифты"), "*.ttf *.otf *.ttc")])
        if not p:
            return
        # если шрифт лежит вне известных папок, кладём копию рядом с программой
        here = os.path.dirname(os.path.abspath(self.path))
        known = [r"C:\Windows\Fonts", start, here, os.path.join(here, "fonts")]
        if not any(os.path.dirname(os.path.abspath(p)).lower() == d.lower()
                   for d in known if d):
            try:
                import shutil
                dest_dir = os.path.join(here, "fonts")
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(p, os.path.join(dest_dir, os.path.basename(p)))
                self.status.config(text="шрифт скопирован в папку fonts")
            except Exception as e:
                self.status.config(text=t("не смог скопировать: {}")
                                   .format(str(e)[:40]))
        name = os.path.basename(p)
        if name not in [f[1] for f in self.fonts]:
            self.fonts.append((name, name))
        self._set(key, name)
        self._refresh_props()

    def _pick_color(self, var):
        try:
            res = colorchooser.askcolor(color=(var.get() or "#ffffff")[:7])
        except Exception:
            res = colorchooser.askcolor()
        if res and res[1]:
            var.set(res[1])

    def _pick_path(self, var):
        p = filedialog.askdirectory(
            title=t("Папка с кадрами (Отмена - выбрать файл)"))
        if not p:
            p = filedialog.askopenfilename(
                filetypes=[(t("Картинки"),
                            "*.png *.jpg *.jpeg *.gif *.bmp *.webp")])
        if p:
            try:
                p = os.path.relpath(p, os.path.dirname(os.path.abspath(self.path)))
            except Exception:
                pass
            var.set(p)

    def _set(self, key, value):
        self.remember("поле " + str(key))
        store = self._store()
        if value is None:
            store.pop(key, None)
        else:
            store[key] = value
        self._tidy_day()
        self._changed(keep_props=True)

    def _tidy_day(self):
        """Убрать из дневного вида поля, совпавшие с ночным."""
        l = self.layers[self.sel]
        d = l.get("day")
        if not isinstance(d, dict):
            return
        for k in [k for k, v in d.items() if l.get(k) == v]:
            d.pop(k)
        if not d:
            l.pop("day", None)

    def _set_text(self, key, var, spec):
        self.remember("поле " + str(key))
        s = var.get().strip()
        store = self._store()
        if s == "":
            store.pop(key, None)
        elif spec in ("int", "float"):
            try:
                store[key] = int(float(s.replace(",", "."))) if spec == "int" \
                    else float(s.replace(",", "."))
            except ValueError:
                return
        else:
            store[key] = s
        self._tidy_day()
        self._changed(keep_props=True)

    # --- холст ----------------------------------------------------------

    def _eff(self, layer):
        """Как блок выглядит в текущем режиме правки."""
        try:
            return panel_mod.blend_layer(layer, self._day_factor())
        except Exception:
            return layer

    def _pt(self, e):
        """Точка на панели из точки на холсте: холст бывает крупнее."""
        k = self.zoom or 1.0
        return int(round(e.x / k)), int(round(e.y / k))

    def _hit(self, x, y):
        """Топовый подходящий блок. Фоновые картинки во весь экран пропускаем."""
        for i in range(len(self.layers) - 1, -1, -1):
            l = self.layers[i]
            if l.get("hidden"):
                continue
            x0, y0, x1, y1 = bbox_of(self._eff(l), self.W, self.H)
            if (x1 - x0) * (y1 - y0) > 0.5 * self.W * self.H:
                continue
            if x0 <= x <= x1 and y0 <= y <= y1:
                return i
        return None

    def _on_click(self, e):
        if not self.layers:
            return
        ex, ey = self._pt(e)
        cur = self._eff(self.layers[self.sel])
        x0, y0, x1, y1 = bbox_of(cur, self.W, self.H)
        inside_current = (x0 <= ex <= x1 and y0 <= ey <= y1
                          and not cur.get("hidden"))
        if not inside_current:
            hit = self._hit(ex, ey)
            if hit is not None:
                self.sel = hit
                self._fill_list()
                self._refresh_props()
        self.drag_from = (ex, ey)
        self.drag_orig = (int(self._get("x") or 0), int(self._get("y") or 0))
        # у остальных выбранных запоминаем их собственные координаты:
        # двигаться они будут на ту же величину, что и главный
        self.drag_rest = [(i, int(self.layers[i].get("x", 0) or 0),
                           int(self.layers[i].get("y", 0) or 0))
                          for i in self.chosen() if i != self.sel]
        self._dragged = False
        self._render()

    def _snap_lines(self):
        """Линии, к которым притягиваемся: края и центры остальных блоков."""
        vx, vy = {0, self.W // 2, self.W}, {0, self.H // 2, self.H}
        for i, l in enumerate(self.layers):
            if i == self.sel or l.get("hidden"):
                continue
            x0, y0, x1, y1 = bbox_of(self._eff(l), self.W, self.H)
            if (x1 - x0) * (y1 - y0) > 0.5 * self.W * self.H:
                continue
            vx.update((x0, (x0 + x1) // 2, x1))
            vy.update((y0, (y0 + y1) // 2, y1))
        return sorted(vx), sorted(vy)

    def _on_drag(self, e):
        if not self.layers or not hasattr(self, "drag_from"):
            return
        if not self._dragged:
            self.remember("перетаскивание")   # один снимок на всё движение
            self._dragged = True
        ex, ey = self._pt(e)
        l = self._store()
        nx = self.drag_orig[0] + (ex - self.drag_from[0])
        ny = self.drag_orig[1] + (ey - self.drag_from[1])
        l["x"], l["y"] = nx, ny

        # Магнит включается кнопкой на панели, а Alt или Ctrl временно
        # его отжимают - когда надо довести слой точно, до пикселя.
        # Бит 0x8 не трогаем: это NumLock, а не модификатор.
        held = bool(e.state & (0x4 | 0x20000))     # Ctrl или Alt
        if self.grid_step and not held:
            step = self.grid_step
            l["x"] = int(round(l["x"] / float(step)) * step)
            l["y"] = int(round(l["y"] / float(step)) * step)
            nx, ny = l["x"], l["y"]
        if not self.snap_on or held:
            self.guides = []
            self._render(fast=True)
            self._move_rest(l["x"] - self.drag_orig[0], l["y"] - self.drag_orig[1])
            self.status.config(text=t("X {}  Y {}   (без магнита)").format(
                l["x"], l["y"]))
            return

        x0, y0, x1, y1 = bbox_of(self._eff(self.layers[self.sel]), self.W, self.H)
        lines_x, lines_y = self._snap_lines()
        self.guides = []

        # по горизонтали: примеряем левый край, центр и правый край
        best = None
        for own in (x0, (x0 + x1) // 2, x1):
            for gx in lines_x:
                dist = abs(own - gx)
                if dist <= SNAP and (best is None or dist < best[0]):
                    best = (dist, gx - own, gx)
        if best:
            l["x"] = nx + best[1]
            self.guides.append(("v", best[2]))

        # по вертикали: верх, середина, низ
        best = None
        for own in (y0, (y0 + y1) // 2, y1):
            for gy in lines_y:
                dist = abs(own - gy)
                if dist <= SNAP and (best is None or dist < best[0]):
                    best = (dist, gy - own, gy)
        if best:
            l["y"] = ny + best[1]
            self.guides.append(("h", best[2]))

        self._move_rest(l["x"] - self.drag_orig[0], l["y"] - self.drag_orig[1])
        self._render(fast=True)
        n = len(self.chosen())
        self.status.config(text=t("X {}  Y {}{}").format(
            l["x"], l["y"], t("   ({} слоёв)").format(n) if n > 1 else ""))

    def _move_rest(self, dx, dy):
        """Подвинуть остальные выбранные на ту же величину."""
        for i, ox, oy in getattr(self, "drag_rest", ()):
            self.layers[i]["x"] = ox + dx
            self.layers[i]["y"] = oy + dy

    def _on_release(self, _):
        self.guides = []
        self._refresh_props()
        self._render()

    def edit_meta(self):
        """Название, автор и описание — то, что увидят другие.

        Здесь же, а не только в витрине: правишь тему и тут же можешь
        подписать её, не уходя со страницы.
        """
        import pages as pages_mod
        import themes as themes_mod
        info = dict(themes_mod.info(self.path))
        info["cfg"] = self.cfg
        dlg = pages_mod.MetaDialog(self.root, self.look or
                                   getattr(self.app_ref, "look", None), info)
        self.root.wait_window(dlg)
        if dlg.result is None:
            return
        self.remember("описание темы")
        was = info["name"]
        meta = self.cfg.setdefault("meta", {})
        for k, v in dlg.result.items():
            if v:
                meta[k] = v
            else:
                meta.pop(k, None)
        if not meta:
            self.cfg.pop("meta", None)

        new_name = (dlg.result.get("name") or "").strip()
        if new_name and new_name != was:
            # Имя тянет за собой папку на диске. Сначала сохраняем: иначе
            # переименуем папку, а правки останутся лежать в памяти, и не
            # будет понятно, куда они делись.
            self.save()
            try:
                old = self.path
                self.path = themes_mod.rename(self.path, new_name)
                app = self.app_ref
                if app is not None:
                    if app.running():
                        app.runner.base_dir = app.theme_dir()
                    import prefs
                    if os.path.abspath(prefs.get("start.last_theme", "") or "") \
                            == os.path.abspath(old):
                        prefs.set("start.last_theme",
                                  os.path.abspath(self.path))
                self.status.config(text="переименовано, папка тоже")
            except Exception as e:
                self.status.config(text=t("папку переименовать не вышло: {}")
                                   .format(str(e)[:40]))
            self._changed(keep_props=True, dirty=False)
            return
        self.status.config(text="описание изменено, не забудь сохранить")
        self._changed(keep_props=True)

    def _back_to_themes(self):
        """Вернуться к списку тем. Редактор открывается только оттуда."""
        try:
            self.top.nametowidget(".").winfo_toplevel()
        except Exception:
            pass
        if self.app_ref is not None:
            self.app_ref.show_page("themes")

    def _typing(self):
        """Курсор стоит в поле ввода - горячие клавиши не наши."""
        w = self.top.focus_get()
        return isinstance(w, (ttk.Entry, tk.Entry, ttk.Combobox, tk.Text))

    def _guarded(self, fn):
        """Клавиша срабатывает, только когда редактор открыт и не печатают."""
        def go(e=None):
            if not self.active or self._typing():
                return
            fn(e)
            return "break"
        return go

    def _dup_key(self, _=None):
        self.duplicate()

    def _save_key(self, _=None):
        self.save()

    def _delete_key(self, _=None):
        self.delete()

    def _on_key(self, e):
        if not self.layers or not self.active:
            return
        if self._typing():
            return
        step = 10 if (e.state & 0x1) else 1
        dx = {"Left": -step, "Right": step}.get(e.keysym, 0)
        dy = {"Up": -step, "Down": step}.get(e.keysym, 0)
        if dx or dy:
            self.remember("сдвиг стрелками")
            for i in self.chosen():
                if i == self.sel:
                    l = self._store()
                    l["x"] = int(self._get("x") or 0) + dx
                    l["y"] = int(self._get("y") or 0) + dy
                else:
                    lay = self.layers[i]
                    lay["x"] = int(lay.get("x", 0) or 0) + dx
                    lay["y"] = int(lay.get("y", 0) or 0) + dy
            self._refresh_props()
            self._render()

    # --- отрисовка ------------------------------------------------------

    def _changed(self, keep_props=False, dirty=True):
        """dirty=False - тема просто перечитана, правок в ней нет."""
        if dirty:
            self.dirty = True
        self._fill_list()
        if not keep_props:
            self._refresh_props()
        self._render()

    def _render(self, fast=False):
        if self.job:
            self.top.after_cancel(self.job)
        self.job = self.top.after(25 if fast else 70, self._render_now)

    def _switch_view(self):
        """Ночь, переход или день. От этого зависит, куда пишутся правки."""
        if self.view.get() == "trans":
            self.scrub_box.pack(fill="x", pady=2)
        else:
            self.scrub_box.pack_forget()
        self._refresh_props()
        self._render()

    def _day_factor(self):
        v = self.view.get()
        if v == "night":
            return 0.0
        if v == "day":
            return 1.0
        return float(self.dayvar.get())

    def _store(self):
        """Куда писать правки: в основной блок или в его дневной раздел."""
        l = self.layers[self.sel]
        if self.view.get() == "day":
            return l.setdefault("day", {})
        return l

    def _get(self, key):
        """Значение поля с точки зрения текущего режима."""
        l = self.layers[self.sel]
        if self.view.get() == "day":
            d = l.get("day") or {}
            if key in d:
                return d[key]
        return l.get(key)

    def reset_day_all(self):
        self.remember("сброс дневного вида")
        if self.layers[self.sel].pop("day", None) is not None:
            self.status.config(text="дневной вид блока сброшен")
            self._changed()

    def _render_now(self):
        self.job = None
        try:
            if self.top.state() in ("withdrawn", "iconic"):
                return      # окно спрятано, рисовать незачем
        except Exception:
            pass
        if not self.active:
            return          # вкладка не открыта, рисовать незачем
        try:
            self.panel = panel_mod.Panel(
                cfg=self.cfg, static=True,
                base_dir=os.path.dirname(os.path.abspath(self.path)))
            shown = dict(self.data)
            f = self._day_factor()
            shown["day_factor"] = f
            if self.react_test is not None and self.layers:
                key = ((self.layers[self.sel].get("react") or {}).get("value"))
                if key:
                    shown[key] = self.react_test
            if self.view.get() == "trans":
                self.daylabel.config(text="{:.0f} %".format(f * 100))
            self.panel.day_mode = "auto"
            moment = time.time() % 600
            if self.loop_test is not None and self.layers:
                loop = self.layers[self.sel].get("loop") or {}
                period = float(loop.get("seconds", 2) or 2)
                moment = self.loop_test * period      # застыли в этой точке
            img = self.panel.render(shown, 0, moment)
        except Exception as e:
            self.status.config(text=t("ошибка: {}").format(str(e)[:60]))
            return
        # Холст занимает то место, что осталось от окна. На большом
        # мониторе панель показывается крупнее натуральной величины -
        # мелкие цифры так виднее, а мышь пересчитывается через _pt.
        # спрашиваем у самой середины, сколько ей дали, а не гадаем
        holder = self.canvas.master
        avail_w = holder.winfo_width() - 16
        if avail_w < 200:      # первая отрисовка, места ещё не раздали
            avail_w = max(320, self.root.winfo_width() - PROPS_W - 320)
        avail_h = max(200, self.root.winfo_height() - 330)
        k = min(avail_w / float(self.W), avail_h / float(self.H), 2.0)
        k = max(0.4, k)
        self.zoom = k
        shown = img
        if k < 0.99 or k > 1.01:
            shown = img.resize((max(1, int(self.W * k)), max(1, int(self.H * k))),
                               Image.LANCZOS if k < 1 else Image.NEAREST)
        if (self.canvas.winfo_reqwidth() != shown.width
                or self.canvas.winfo_reqheight() != shown.height):
            self.canvas.config(width=shown.width, height=shown.height)
        self.photo = ImageTk.PhotoImage(shown)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
        if self.grid_step:
            step = self.grid_step * k
            gx = step
            while gx < self.W * k:
                self.canvas.create_line(gx, 0, gx, self.H * k, fill="#2a3140")
                gx += step
            gy = step
            while gy < self.H * k:
                self.canvas.create_line(0, gy, self.W * k, gy, fill="#2a3140")
                gy += step
        for kind, pos in self.guides:
            if kind == "v":
                self.canvas.create_line(pos * k, 0, pos * k, self.H * k,
                                        fill="#00ff88")
            else:
                self.canvas.create_line(0, pos * k, self.W * k, pos * k,
                                        fill="#00ff88")
        for i in self.chosen():
            x0, y0, x1, y1 = bbox_of(self._eff(self.layers[i]), self.W, self.H)
            self.canvas.create_rectangle(
                x0 * k, y0 * k, x1 * k, y1 * k,
                outline="#00ff88" if i == self.sel else "#2f8f5f",
                dash=(4, 3))
        title = "{}{}".format(os.path.basename(self.path),
                              " *" if self.dirty else "")
        if self.on_change:
            self.on_change(title, self.dirty)
        elif hasattr(self.top, "title"):
            self.top.title(t("{} · редактор · {} — {}").format(
                panel_mod.PROJECT, panel_mod.AUTHOR, title))

    def _tick(self):
        self.data = self.sensors.read()
        if not self.job:
            self._render()
        self.top.after(1000, self._tick)

    # --- вывод на экран водянки ------------------------------------------

    def toggle_stream(self):
        if self.streaming:
            self.stream_stop.set()
            self.streaming = False
            self.stream_btn.config(text="Показать на экране")
            return
        self.stream_stop.clear()
        self.streaming = True
        self.stream_btn.config(text="Остановить показ")
        threading.Thread(target=self._stream, daemon=True).start()

    def _say(self, text):
        """Написать в строку состояния из чужого потока.

        Виджеты Tk можно трогать только из его собственного цикла событий,
        поэтому передаём сообщение туда через after.
        """
        try:
            self.top.after(0, lambda: self.status.config(text=text))
        except Exception:
            pass

    def _stream(self):
        try:
            import txw818
            port = txw818.find_port()
            if not port:
                self._say(t("экран не найден"))
            else:
                d = txw818.Display(port)
                d.connect()
                pan = panel_mod.Panel(
                    cfg=copy.deepcopy(self.cfg),
                    base_dir=os.path.dirname(os.path.abspath(self.path)))
                t0, n = time.time(), 0
                while not self.stream_stop.is_set():
                    img = pan.render(self.data, n, time.time() - t0)
                    d.show_jpeg(txw818.to_jpeg(img, pan.width, pan.height,
                                               pan.quality))
                    n += 1
                    time.sleep(1.0 / max(1.0, pan.fps))
                d.close()
        except Exception as e:
            self._say(t("показ прерван: {}").format(str(e)[:50]))
        self.streaming = False
        try:
            self.top.after(0, lambda: self.stream_btn.config(
                text="Показать на экране"))
        except Exception:
            pass

    # --- файл -----------------------------------------------------------

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, ensure_ascii=False, indent=2)
        self.dirty = False
        self.status.config(text="сохранено")
        self._render()

    def open_theme(self):
        """Открыть тему из другой папки.

        Тема - это папка, в которой лежит файл описания и всё, на что он
        ссылается: папки кадров, картинки, шрифты. Пути внутри считаются
        относительно неё, поэтому такую папку можно переносить целиком.
        """
        if self.dirty and not messagebox.askyesno(
                t("Открыть"), t("Несохранённые правки пропадут. Продолжить?")):
            return

        folder = filedialog.askdirectory(
            title=t("Папка с темой (Отмена — выбрать файл)"))
        path = None
        if folder:
            names = sorted(n for n in os.listdir(folder)
                           if n.lower().endswith(".json")
                           and n.lower() not in ("weather.json",))
            if not names:
                messagebox.showwarning(
                    t("Открыть"),
                    t("В папке нет файлов описания темы (.json).\n\n"
                      "Файл темы должен лежать рядом с папками кадров."))
                return
            if len(names) == 1:
                path = os.path.join(folder, names[0])
            else:
                path = filedialog.askopenfilename(
                    title=t("Какой файл темы открыть"), initialdir=folder,
                    filetypes=[(t("Файл темы"), "*.json")])
        else:
            path = filedialog.askopenfilename(
                title=t("Файл темы"),
                filetypes=[(t("Файл темы"), "*.json")])
        if not path:
            return

        try:
            with open(path, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            messagebox.showerror(t("Открыть"),
                                 t("Не удалось прочитать файл:\n{}").format(e))
            return
        if "layers" not in cfg:
            messagebox.showwarning(
                t("Открыть"), t("Это не похоже на тему: нет раздела layers."))
            return

        self.path = path
        self.cfg = cfg
        self.layers = self.cfg.setdefault("layers", [])
        self.dirty = False
        self.sel = 0
        self.W = int(self.cfg.get("screen", {}).get("width", 960))
        self.H = int(self.cfg.get("screen", {}).get("height", 480))
        self.canvas.config(width=self.W, height=self.H)
        panel_mod._PREPARED.clear()      # кадры прежней темы больше не нужны
        self.status.config(text=t("открыто: ") + os.path.dirname(path))
        self._refresh_screen_fields()
        self._changed(dirty=False)
        self._check_theme()

    def _check_theme(self):
        """Предупредить, если тема ссылается на то, чего рядом нет."""
        base = os.path.dirname(os.path.abspath(self.path))
        missing = []
        for l in self.layers:
            if l.get("type") == "image" and l.get("src"):
                s = l["src"]
                if not (os.path.exists(s) or os.path.exists(os.path.join(base, s))):
                    missing.append(s)
        if missing:
            messagebox.showwarning(
                t("Открыть"),
                t("Тема ссылается на то, чего нет рядом с её файлом:\n\n  ")
                + "\n  ".join(sorted(set(missing)))
                + t("\n\nПеренеси эти папки в {}").format(base))

    def save_as(self):
        p = filedialog.asksaveasfilename(defaultextension=".json",
                                         initialfile=os.path.basename(self.path),
                                         filetypes=[(t("Описание панели"),
                                                     "*.json")])
        if p:
            self.path = p
            self.save()

    def adopt(self, path, cfg):
        """Перейти на другую тему, уже прочитанную с диска."""
        self.path = path
        self.cfg = cfg
        self.layers = self.cfg.setdefault("layers", [])
        self.dirty = False
        self.sel = 0
        self.W = int(cfg.get("screen", {}).get("width", 960))
        self.H = int(cfg.get("screen", {}).get("height", 480))
        self.canvas.config(width=self.W, height=self.H)
        self._refresh_screen_fields()
        self._changed(dirty=False)

    def sync_day_mode(self, mode):
        """Режим суток выбрали на главной - подхватить, не записывая заново."""
        self._loading = True
        try:
            self.modevar.set(mode)
        finally:
            self._loading = False

    def reload(self):
        if self.dirty and not messagebox.askyesno(
                t("Вернуть"), t("Несохранённые правки пропадут. Продолжить?")):
            return
        with open(self.path, encoding="utf-8") as f:
            self.cfg = json.load(f)
        self.layers = self.cfg.setdefault("layers", [])
        self.dirty = False
        self.sel = 0
        self._refresh_screen_fields()
        self._changed(dirty=False)


def main():
    # редактор запускают и отдельно от окна программы - язык берём оттуда же
    import prefs
    yazyk.vybrat(prefs.get("ui.lang", yazyk.RU))
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = args[0] if args else panel_mod.DEFAULT_LAYOUT
    if not os.path.exists(path):
        print(t("Не найден файл описания: {}").format(path))
        return
    root = tk.Tk()
    ed = Editor(root, path)

    def on_close():
        ed.stream_stop.set()
        ed.sensors.stop()
        if ed.dirty and messagebox.askyesno(t("Выход"), t("Сохранить правки?")):
            ed.save()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
