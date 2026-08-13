#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Движок отрисовки панели по описанию из layout.json.
#  Часть проекта EOne screen — открытой замены штатной программе
#  для экранов на контроллере TXW818.
#
#  Автор: EOne
#  Лицензия: CC BY-NC-SA 4.0 — использование в коммерческих целях
#  запрещено без письменного разрешения автора. См. файл LICENSE.
#
"""
panel.py - рисует панель мониторинга по описанию из layout.json
           и выводит её на экран водянки.

    python panel.py                    запустить на экране
    python panel.py --preview          сохранить картинку в preview.png,
                                       экран не нужен
    python panel.py другой.json        взять другое описание
    python panel.py --sensors          показать все доступные значения

Описание панели лежит в layout.json. Все параметры расписаны
в файле «Панель - справочник.md».
"""

import hashlib
import json
import math
import threading
import os
import string
import sys
import time
import zlib

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

try:
    import numpy as np
except ImportError:
    np = None            # без него не будет градиентов и режима premultiplied

import sensors as sensors_mod
import edinicy
import prefs

AUTHOR = "EOne"
PROJECT = "EOne screen"
LICENSE = "CC BY-NC-SA 4.0, некоммерческое использование"
VERSION = "3.8"

DEFAULT_LAYOUT = "layout.json"

# Как выбирается дневной или ночной вид. Порядок тот же, что и в окне.
DAY_MODES = ["auto", "system", "night", "day"]
DAY_MODE_NAMES = {
    "auto": "по солнцу",
    "system": "как в Windows",
    "night": "всегда ночная",
    "day": "всегда дневная",
}

# где искать шрифты
FONT_DIRS = [
    ".", "fonts",
    r"C:\Windows\Fonts",
    # Windows 11 по умолчанию ставит шрифты только для текущего пользователя,
    # и кладёт их сюда, а не в системную папку
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"),
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype",
    "/usr/share/fonts",
]
FONT_FALLBACKS = ["arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]

_font_cache = {}


# --- вспомогательное --------------------------------------------------------

class _SafeFormatter(string.Formatter):
    """Подставляет прочерк вместо значений, которых нет."""

    def get_value(self, key, args, kwargs):
        if isinstance(key, str):
            return kwargs.get(key, sensors_mod.MISSING)
        return super().get_value(key, args, kwargs)

    def format_field(self, value, spec):
        try:
            return super().format_field(value, spec)
        except (ValueError, TypeError):
            return sensors_mod.MISSING.text


_fmt = _SafeFormatter()


def render_text(template, data):
    """Надпись по шаблону темы.

    Единственное место, где числа становятся текстом, - поэтому здесь же
    их переводят в выбранную шкалу, а подпись «°C» меняют на «°F».
    Значения, которыми тема правит картинку, идут мимо и остаются
    в Цельсиях: см. edinicy.dlya_teksta.
    """
    if not isinstance(template, str):
        return str(template)
    try:
        return _fmt.vformat(edinicy.podpis(template), (),
                            edinicy.dlya_teksta(data))
    except Exception:
        return template


_color_cache = {}


def parse_color(value, opacity=1.0):
    """'#RRGGBB', '#RRGGBBAA', [r,g,b], [r,g,b,a] или None -> кортеж RGBA.

    Разбор цвета идёт по нескольку раз на каждый слой в каждом кадре,
    поэтому результат запоминается. Ключ строим только для строк:
    списков в темах немного, а хэшировать их пришлось бы отдельно.
    """
    if value is None:
        return None
    if type(value) is str:
        key = (value, opacity)
        got = _color_cache.get(key)
        if got is not None:
            return got
    else:
        key = None
    if isinstance(value, (list, tuple)):
        c = list(value)
        while len(c) < 4:
            c.append(255)
        r, g, b, a = c[:4]
    else:
        s = str(value).strip().lstrip("#")
        if len(s) == 3:
            s = "".join(ch * 2 for ch in s)
        if len(s) == 6:
            s += "ff"
        if len(s) != 8:
            return None
        r, g, b, a = (int(s[i:i + 2], 16) for i in (0, 2, 4, 6))
    a = int(max(0, min(255, a * float(opacity))))
    out = (int(r), int(g), int(b), a)
    if key is not None:
        if len(_color_cache) > 4096:
            _color_cache.clear()
        _color_cache[key] = out
    return out


def load_font(name, size):
    key = (name, int(size))
    if key in _font_cache:
        return _font_cache[key]
    candidates = []
    if name:
        candidates.append(name)
        for d in FONT_DIRS:
            candidates.append(os.path.join(d, name))
    for fb in FONT_FALLBACKS:
        candidates.append(fb)
        for d in FONT_DIRS:
            candidates.append(os.path.join(d, fb))
    for path in candidates:
        try:
            f = ImageFont.truetype(path, int(size))
            _font_cache[key] = f
            return f
        except Exception:
            continue
    try:
        f = ImageFont.load_default(size=int(size))
    except TypeError:
        f = ImageFont.load_default()
    _font_cache[key] = f
    return f


def get_number(spec, data, default=0.0):
    """Значение может быть числом или именем датчика."""
    if isinstance(spec, (int, float)):
        return float(spec)
    if isinstance(spec, str):
        v = data.get(spec)
        if isinstance(v, (int, float)):
            return float(v)
    return default


def fraction(layer, data):
    """Доля заполнения бара от 0 до 1."""
    value = get_number(layer.get("value"), data, 0.0)
    lo = float(layer.get("min", 0))
    hi = float(layer.get("max", 100))
    if hi == lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


# --- отрисовка слоёв --------------------------------------------------------

_image_cache = {}
_PREPARED = {}

# Разобранные кадры, отложенные на диск рядом с темой. Папка с точки:
# витрина её не видит, в копию и в архив она не попадает. Удалить можно
# в любой момент - соберётся заново.
CACHE_DIR = ".кадры"
CACHE_MARK = "КАДРЫ1".encode("utf-8")


class _Packed:
    """Кадр фона, сжатый прямо в памяти.

    Храним сами точки, сжатые zlib: достать кадр - семь десятых
    миллисекунды. Без потерь буквально: возвращаются ровно те же точки.
    Почему не WEBP - в УСТРОЙСТВО.md, «Хранение кадров».
    """

    __slots__ = ("blob", "width", "height")

    def __init__(self, img):
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        self.width, self.height = img.size
        # уровень 6: вдвое быстрее девятого при почти том же размере
        self.blob = zlib.compress(img.tobytes(), 6)

    @classmethod
    def raw(cls, blob, width, height):
        """Кадр из готовых сжатых байт — так он поднимается с диска."""
        p = cls.__new__(cls)
        p.blob, p.width, p.height = blob, width, height
        return p

    def image(self):
        """Распакованная картинка.

        frombuffer, а не frombytes: та же картинка, но без лишней копии
        в полмегабайта на каждом кадре. Портить её нельзя - Pillow сам
        сделает копию, если кто-то попробует в неё писать.
        """
        return Image.frombuffer("RGBA", (self.width, self.height),
                                zlib.decompress(self.blob), "raw", "RGBA", 0, 1)

    def __len__(self):
        return len(self.blob)


def _frame_sources(src):
    """Список источников кадров: пути к файлам или сами кадры для GIF.

    Для папки возвращаем пути, чтобы не держать в памяти всё сразу.
    """
    if os.path.isdir(src):
        names = sorted(n for n in os.listdir(src)
                       if n.lower().endswith((".png", ".jpg", ".jpeg",
                                              ".bmp", ".webp", ".tif", ".tiff")))
        return [os.path.join(src, n) for n in names]
    return _load_frames(src)


def _load_frames(src):
    """Одна картинка или анимированный GIF -> список кадров.

    Папки сюда не попадают: у них кадров бывают сотни, и _frame_sources
    отдаёт вместо них пути, чтобы не держать всё распакованным в памяти.
    """
    if src in _image_cache:
        return _image_cache[src]
    frames = []
    im = Image.open(src)
    try:
        while True:
            frames.append(im.convert("RGBA"))
            im.seek(im.tell() + 1)
    except EOFError:
        pass
    if not frames:
        frames = [im.convert("RGBA")]
    _image_cache[src] = frames
    return frames


def _apply_mask(img, spec, off_x, off_y):
    """Оставить видимой только часть картинки.

    Нужно, когда слой лежит ПОВЕРХ текста: без маски чёрный прямоугольник
    кадра закрыл бы всё, что нарисовано под ним.

    Координаты маски задаются в координатах экрана, off_x/off_y - смещение
    самого слоя.
    """
    kind = str(spec.get("type", "circle")).lower()
    feather = float(spec.get("feather", 0))
    m = Image.new("L", img.size, 0)
    md = ImageDraw.Draw(m)

    if kind == "circle":
        cx = float(spec.get("x", img.width / 2)) - off_x
        cy = float(spec.get("y", img.height / 2)) - off_y
        r = float(spec.get("r", min(img.size) / 2))
        md.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    elif kind == "ellipse":
        cx = float(spec.get("x", img.width / 2)) - off_x
        cy = float(spec.get("y", img.height / 2)) - off_y
        rx = float(spec.get("rx", spec.get("r", img.width / 2)))
        ry = float(spec.get("ry", spec.get("r", img.height / 2)))
        md.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
    else:  # rect
        x0 = float(spec.get("x", 0)) - off_x
        y0 = float(spec.get("y", 0)) - off_y
        w = float(spec.get("w", img.width))
        h = float(spec.get("h", img.height))
        rad = int(spec.get("radius", 0))
        box = [x0, y0, x0 + w, y0 + h]
        if rad > 0:
            md.rounded_rectangle(box, radius=rad, fill=255)
        else:
            md.rectangle(box, fill=255)

    if feather > 0:
        m = m.filter(ImageFilter.GaussianBlur(feather))

    alpha = img.getchannel("A")
    img = img.copy()
    img.putalpha(ImageChops.multiply(alpha, m))
    return img


def process_frame(img, layer, size):
    """Привести один кадр к готовому виду: масштаб, прозрачность, маска.

    Отдельно от наложения, потому что при подготовке сотен кадров
    накладывать каждый на пустой холст незачем - это лишнее выделение
    памяти и лишний проход по всем пикселям.

    Режим premultiplied здесь НЕ снимается: вызывающий делает это уже
    после обрезки по видимой области, где работы втрое меньше.
    """
    w = int(layer.get("w", size[0]))
    h = int(layer.get("h", size[1]))
    fit = layer.get("fit", "cover")

    if img.size != (w, h):
        if fit == "stretch":
            img = img.resize((w, h), Image.LANCZOS)
        elif fit in ("cover", "contain"):
            sw, sh = img.size
            k = max(w / sw, h / sh) if fit == "cover" else min(w / sw, h / sh)
            img = img.resize((max(1, int(sw * k)), max(1, int(sh * k))), Image.LANCZOS)
            if fit == "cover":
                left = (img.width - w) // 2
                top = (img.height - h) // 2
                img = img.crop((left, top, left + w, top + h))
            else:
                # contain вписывает картинку целиком, а значит по одной оси
                # остаётся поле. Кладём на прозрачный холст w x h, чтобы
                # картинка стояла ровно посередине отведённого места.
                pad = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                pad.paste(img, ((w - img.width) // 2, (h - img.height) // 2))
                img = pad

    op = float(layer.get("opacity", 1.0))
    if op < 1.0:
        img = img.copy()
        img.putalpha(img.getchannel("A").point(lambda v: int(v * op)))

    gain = float(layer.get("alpha_gain", 1) or 1)
    if gain != 1.0:
        # Спасение для кадров, вырезанных не полностью непрозрачными:
        # поднимаем альфу, не трогая полностью прозрачные места.
        img = img.copy()
        img.putalpha(img.getchannel("A").point(
            lambda v: 0 if v < 6 else min(255, int(v * gain))))

    # Отражение до маски: маска задана в координатах экрана, и если
    # отразить после неё, вырез окажется не с той стороны.
    if layer.get("mirror"):
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if layer.get("flip"):
        img = img.transpose(Image.FLIP_TOP_BOTTOM)

    mask_spec = layer.get("mask")
    if mask_spec:
        img = _apply_mask(img, mask_spec, int(layer.get("x", 0)),
                          int(layer.get("y", 0)))

    return img


def _unpremultiply(img):
    """Вернуть цвет из режима premultiplied в обычный.

    DaVinci выгружает PNG только с перемноженной прозрачностью: цвет
    пикселя уже умножен на альфу. Обычное наложение умножит его ещё раз,
    и по мягкому краю пойдёт тёмная каёмка. Здесь делим обратно.
    """
    if np is None:
        return img
    a = np.asarray(img).astype(np.float32)
    alpha = a[:, :, 3:4] / 255.0
    safe = np.where(alpha > 0.004, alpha, 1.0)
    a[:, :, :3] = np.clip(a[:, :, :3] / safe, 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def draw_rect(canvas, layer, data, size, frame_no):
    op = float(layer.get("opacity", 1.0))
    x, y = int(layer.get("x", 0)), int(layer.get("y", 0))
    w, h = int(layer.get("w", 100)), int(layer.get("h", 100))
    r = int(layer.get("radius", 0))
    outline = parse_color(layer.get("outline"), op)
    width = int(layer.get("width", 0))
    box = [x, y, x + w, y + h]
    # Границы у Pillow включительные, поэтому справа и снизу прибавляем точку.
    full = (x, y, x + w + 1, y + h + 1)
    if r > 0:
        paint_shape(canvas, lambda d, c, ox, oy: d.rounded_rectangle(
            [x - ox, y - oy, x + w - ox, y + h - oy], radius=r, fill=c),
            layer, op, box=full)
    else:
        paint_shape(canvas, lambda d, c, ox, oy: d.rectangle(
            [x - ox, y - oy, x + w - ox, y + h - oy], fill=c),
            layer, op, box=full, solid=True)
    if outline and width:
        d = ImageDraw.Draw(canvas)
        if r > 0:
            d.rounded_rectangle(box, radius=r, outline=outline, width=width)
        else:
            d.rectangle(box, outline=outline, width=width)


def draw_text(canvas, layer, data, size, frame_no):
    op = float(layer.get("opacity", 1.0))
    text = render_text(layer.get("text", ""), data)
    font = load_font(layer.get("font"), layer.get("size", 24))
    color = parse_color(layer.get("color", "#ffffff"), op) or (255, 255, 255, 255)
    x, y = int(layer.get("x", 0)), int(layer.get("y", 0))
    anchor = layer.get("anchor", "la")
    align = layer.get("align", "left")
    d = ImageDraw.Draw(canvas)

    shadow = layer.get("shadow")
    if shadow:
        sc = parse_color(shadow.get("color", "#000000"), op * shadow.get("opacity", 0.6))
        dx, dy = int(shadow.get("dx", 2)), int(shadow.get("dy", 2))
        d.text((x + dx, y + dy), text, font=font, fill=sc, anchor=anchor, align=align)

    stroke_w = int(layer.get("outline_width", 0))
    stroke_c = parse_color(layer.get("outline"), op)
    d.text((x, y), text, font=font, fill=color, anchor=anchor, align=align,
           stroke_width=stroke_w, stroke_fill=stroke_c)


def draw_bar(canvas, layer, data, size, frame_no):
    op = float(layer.get("opacity", 1.0))
    x, y = int(layer.get("x", 0)), int(layer.get("y", 0))
    w, h = int(layer.get("w", 200)), int(layer.get("h", 20))
    r = int(layer.get("radius", 0))
    direction = str(layer.get("direction", "h")).lower()
    frac = fraction(layer, data)

    back = parse_color(layer.get("back"), op)
    fill = parse_color(layer.get("fill", "#3aa0ff"), op)
    outline = parse_color(layer.get("outline"), op)
    width = int(layer.get("width", 0))

    d = ImageDraw.Draw(canvas)
    box = [x, y, x + w, y + h]
    if back:
        if r > 0:
            d.rounded_rectangle(box, radius=r, fill=back)
        else:
            d.rectangle(box, fill=back)

    if frac > 0 and fill:
        if direction in ("h", "lr", "right"):
            fb = [x, y, x + max(1, int(w * frac)), y + h]
        elif direction in ("rl", "left"):
            fb = [x + w - max(1, int(w * frac)), y, x + w, y + h]
        elif direction in ("v", "bt", "up"):
            fb = [x, y + h - max(1, int(h * frac)), x + w, y + h]
        else:  # tb, down
            fb = [x, y, x + w, y + max(1, int(h * frac))]
        rr = min(r, (fb[2] - fb[0]) // 2, (fb[3] - fb[1]) // 2) if r > 0 else 0
        full = (fb[0], fb[1], fb[2] + 1, fb[3] + 1)
        if rr > 0:
            paint_shape(canvas, lambda dd, c, ox, oy: dd.rounded_rectangle(
                [fb[0] - ox, fb[1] - oy, fb[2] - ox, fb[3] - oy],
                radius=rr, fill=c), layer, op, box=full)
        else:
            paint_shape(canvas, lambda dd, c, ox, oy: dd.rectangle(
                [fb[0] - ox, fb[1] - oy, fb[2] - ox, fb[3] - oy], fill=c),
                layer, op, box=full, solid=True)

    if outline and width:
        if r > 0:
            d.rounded_rectangle(box, radius=r, outline=outline, width=width)
        else:
            d.rectangle(box, outline=outline, width=width)



# --- заливка и градиенты ----------------------------------------------------

def _ramp(n, c1, c2, across=False):
    """Полоска толщиной в один пиксель: чистый переход от c1 к c2.

    across=False - полоска стоит (1 x n), across=True - лежит (n x 1).
    """
    n = max(1, int(n))
    if np is not None:
        t = np.linspace(0.0, 1.0, n)[:, None]
        a = (np.array(c1, float)[None, :] * (1 - t)
             + np.array(c2, float)[None, :] * t).astype("uint8")
        return Image.fromarray(a.reshape((1, n, 4) if across else (n, 1, 4)),
                               "RGBA")
    # без numpy - обычным перебором. Точек тут всего несколько сотен,
    # это доли миллисекунды.
    im = Image.new("RGBA", (n, 1) if across else (1, n))
    px = im.load()
    last = max(1, n - 1)
    for i in range(n):
        f = i / last
        c = tuple(int(a + (b - a) * f) for a, b in zip(c1, c2))
        if across:
            px[i, 0] = c
        else:
            px[0, i] = c
    return im


def _gradient(size, c1, c2, direction="v"):
    """Полотно с плавным переходом между двумя цветами.

    Считаем не всё полотно, а одну полоску в пиксель толщиной, и уже её
    размножаем средствами Pillow. Полотно во весь размер фигуры обошлось бы
    на большом овале в двадцать миллисекунд - треть бюджета кадра.

    Размножение NEAREST даёт ровно те же точки: по короткой стороне размер
    совпадает, а по длинной строка просто повторяется.
    """
    w, h = max(1, int(size[0])), max(1, int(size[1]))
    d = str(direction).lower()
    if d in ("h", "lr", "→"):
        return _ramp(w, c1, c2, True).resize((w, h), Image.NEAREST)
    if d in ("rl", "←"):
        return _ramp(w, c2, c1, True).resize((w, h), Image.NEAREST)
    if d in ("bt", "↑"):
        return _ramp(h, c2, c1).resize((w, h), Image.NEAREST)
    if d in ("diag", "d", "↘"):
        # переход по диагонали - это полусумма перехода вдоль и поперёк
        return Image.blend(_ramp(w, c1, c2, True).resize((w, h), Image.NEAREST),
                           _ramp(h, c1, c2).resize((w, h), Image.NEAREST), 0.5)
    return _ramp(h, c1, c2).resize((w, h), Image.NEAREST)   # v, сверху вниз


def paint_shape(canvas, shape, layer, op, box=None, solid=False):
    """Нарисовать фигуру сплошным цветом или градиентом.

    shape(draw, colour, ox, oy) должна нарисовать фигуру указанным цветом,
    сдвинув все свои координаты на (-ox, -oy). Сдвиг нужен, чтобы ту же
    фигуру можно было нарисовать не на целом холсте, а на клочке размером
    с неё саму.

    Если у слоя задан второй цвет fill2, фигура работает маской для
    градиентного полотна. Тут и была вся цена:

      box   - где фигура умещается целиком, в координатах холста. Если
              известен заранее, маска строится ТОЛЬКО внутри него, и не
              надо искать занятую область перебором всех точек экрана.
      solid - фигура закрывает свой box целиком, без единой прозрачной
              точки. Тогда маска не нужна вовсе.

    Пока этого не было, заливка неба во весь экран заводила маску
    в полтора миллиона точек, перебирала их в поисках границ и умножала
    по всему холсту. Три таких прямоугольника и два ореола солнца
    съедали сорок миллисекунд из сорока отпущенных на кадр.
    """
    fill = parse_color(layer.get("fill"), op)
    if not fill:
        return
    fill2 = parse_color(layer.get("fill2"), op)
    if not fill2:
        shape(ImageDraw.Draw(canvas), fill, 0, 0)
        return

    part = None
    if box is None:
        mask = Image.new("L", canvas.size, 0)
        shape(ImageDraw.Draw(mask), 255, 0, 0)
        box = mask.getbbox()
        if not box:
            return
        part = mask.crop(box)
    else:
        box = (max(0, int(box[0])), max(0, int(box[1])),
               min(canvas.width, int(box[2])), min(canvas.height, int(box[3])))
        if box[2] <= box[0] or box[3] <= box[1]:
            return
        if not solid:
            part = Image.new("L", (box[2] - box[0], box[3] - box[1]), 0)
            shape(ImageDraw.Draw(part), 255, box[0], box[1])

    grad = _gradient((box[2] - box[0], box[3] - box[1]), fill, fill2,
                     layer.get("gradient", "v"))
    if part is not None:
        grad.putalpha(ImageChops.multiply(grad.getchannel("A"), part))
    canvas.alpha_composite(grad, (box[0], box[1]))


# --- дополнительные фигуры --------------------------------------------------

def draw_ellipse(canvas, layer, data, size, frame_no):
    op = float(layer.get("opacity", 1.0))
    x, y = int(layer.get("x", 0)), int(layer.get("y", 0))
    w, h = int(layer.get("w", 120)), int(layer.get("h", 120))
    box = [x, y, x + w, y + h]
    paint_shape(canvas, lambda d, c, ox, oy: d.ellipse(
        [x - ox, y - oy, x + w - ox, y + h - oy], fill=c),
        layer, op, box=(x, y, x + w + 1, y + h + 1))
    outline = parse_color(layer.get("outline"), op)
    width = int(layer.get("width", 0))
    if outline and width:
        ImageDraw.Draw(canvas).ellipse(box, outline=outline, width=width)


def draw_line(canvas, layer, data, size, frame_no):
    op = float(layer.get("opacity", 1.0))
    x, y = int(layer.get("x", 0)), int(layer.get("y", 0))
    x2 = int(layer.get("x2", x + 200))
    y2 = int(layer.get("y2", y))
    colour = parse_color(layer.get("fill", "#ffffff"), op)
    width = max(1, int(layer.get("width", 3)))
    d = ImageDraw.Draw(canvas)
    d.line([x, y, x2, y2], fill=colour, width=width)
    if layer.get("cap") == "round":
        r = width / 2.0
        for px, py in ((x, y), (x2, y2)):
            d.ellipse([px - r, py - r, px + r, py + r], fill=colour)


def draw_arrow(canvas, layer, data, size, frame_no):
    op = float(layer.get("opacity", 1.0))
    x, y = int(layer.get("x", 0)), int(layer.get("y", 0))
    x2 = int(layer.get("x2", x + 200))
    y2 = int(layer.get("y2", y))
    colour = parse_color(layer.get("fill", "#ffffff"), op)
    width = max(1, int(layer.get("width", 3)))
    head = float(layer.get("head", width * 4))
    ang = math.atan2(y2 - y, x2 - x)
    # линию укорачиваем, чтобы она не торчала из наконечника
    bx = x2 - head * 0.85 * math.cos(ang)
    by = y2 - head * 0.85 * math.sin(ang)
    d = ImageDraw.Draw(canvas)
    d.line([x, y, bx, by], fill=colour, width=width)
    left = (x2 - head * math.cos(ang - 0.42), y2 - head * math.sin(ang - 0.42))
    right = (x2 - head * math.cos(ang + 0.42), y2 - head * math.sin(ang + 0.42))
    d.polygon([(x2, y2), left, right], fill=colour)


def _star_points(cx, cy, r_out, r_in, points, turn):
    pts = []
    for i in range(points * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(turn - 90) + i * math.pi / points
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def draw_star(canvas, layer, data, size, frame_no):
    op = float(layer.get("opacity", 1.0))
    cx, cy = int(layer.get("x", 100)), int(layer.get("y", 100))
    r_out = float(layer.get("r", 60))
    r_in = float(layer.get("r_inner", r_out * 0.45))
    points = max(3, int(layer.get("points", 5)))
    pts = _star_points(cx, cy, r_out, r_in, points, float(layer.get("turn", 0)))
    # Границы звезде не подсказываем: лучи не обязательно достают до краёв
    # описанной окружности, и градиент растянулся бы не по фигуре.
    paint_shape(canvas, lambda d, c, ox, oy: d.polygon(
        [(px - ox, py - oy) for px, py in pts], fill=c), layer, op)
    outline = parse_color(layer.get("outline"), op)
    width = int(layer.get("width", 0))
    if outline and width:
        ImageDraw.Draw(canvas).line(pts + [pts[0]], fill=outline, width=width,
                                    joint="curve")


def draw_ring(canvas, layer, data, size, frame_no):
    op = float(layer.get("opacity", 1.0))
    cx, cy = int(layer.get("x", 100)), int(layer.get("y", 100))
    # отрицательные радиус и толщина - опечатка; Pillow на них ругается
    # в каждом кадре, а рисовать всё равно нечего
    rad = max(0, int(layer.get("r", 60)))
    th = max(1, int(layer.get("thickness", 14)))
    if rad <= 0:
        return
    frac = fraction(layer, data)

    # Углы можно задать двумя способами.
    # Простой: gap_at говорит, с какой стороны разрыв дуги,
    #          gap - его ширина в градусах.
    # Точный:  start и end прямо в градусах (0 вправо, 90 вниз).
    gap_at = layer.get("gap_at")
    if gap_at:
        gap = float(layer.get("gap", 60))
        centers = {"top": 270, "bottom": 90, "left": 180, "right": 0}
        c = centers.get(str(gap_at).lower(), 90)
        start = c + gap / 2.0
        end = c + 360.0 - gap / 2.0
    else:
        start = float(layer.get("start", 135))
        end = float(layer.get("end", 405))

    back = parse_color(layer.get("back"), op)
    fill = parse_color(layer.get("fill", "#3aa0ff"), op)

    d = ImageDraw.Draw(canvas)
    box = [cx - rad, cy - rad, cx + rad, cy + rad]
    round_cap = layer.get("cap") == "round"

    def cap(colour, *angles):
        """Кружок на конце дуги. Радиус чуть меньше половины толщины,
        иначе на краю вылезает заметный уступ."""
        r = th / 2.0 - 0.5
        for ang in angles:
            a = math.radians(ang)
            px = cx + (rad - th / 2.0) * math.cos(a)
            py = cy + (rad - th / 2.0) * math.sin(a)
            d.ellipse([px - r, py - r, px + r, py + r], fill=colour)

    if back:
        d.arc(box, start, end, fill=back, width=th)
        if round_cap:
            cap(back, start, end)

    if frac > 0 and fill:
        # обычно дуга растёт от start к end; reverse разворачивает её,
        # тогда заполнение идёт от end обратно к start
        if layer.get("reverse"):
            a1 = end - (end - start) * frac
            a2 = end
        else:
            a1 = start
            a2 = start + (end - start) * frac
        d.arc(box, a1, a2, fill=fill, width=th)
        if round_cap:
            cap(fill, a1, a2)



def draw_transformed(target, layer, data, size, frame_no, fn):
    """Нарисовать слой с поворотом и растяжением.

    Проще всего сделать это отдельным проходом: рисуем фигуру на пустом
    холсте, вырезаем занятую ею область, растягиваем и поворачиваем,
    затем возвращаем на место относительно прежнего центра.
    """
    angle = float(layer.get("angle", 0) or 0)
    sx = float(layer.get("stretch_x", 1) or 1)
    sy = float(layer.get("stretch_y", 1) or 1)
    if angle == 0 and sx == 1 and sy == 1:
        fn(target, layer, data, size, frame_no)
        return

    scratch = Image.new("RGBA", size, (0, 0, 0, 0))
    fn(scratch, layer, data, size, frame_no)
    box = scratch.getbbox()
    if box is None:
        return
    part = scratch.crop(box)
    cx = (box[0] + box[2]) / 2.0
    cy = (box[1] + box[3]) / 2.0

    if sx != 1 or sy != 1:
        part = part.resize((max(1, int(part.width * sx)),
                            max(1, int(part.height * sy))), Image.LANCZOS)
    if angle:
        # знак меняем, чтобы положительный угол крутил по часовой стрелке
        part = part.rotate(-angle, expand=True, resample=Image.BICUBIC)

    target.alpha_composite(part, (int(cx - part.width / 2.0),
                                  int(cy - part.height / 2.0)))


# Слои-картинки сюда не попадают: их готовит и накладывает Panel сама,
# один раз на загрузке, а не заново в каждом кадре.
DRAWERS = {
    "ellipse": draw_ellipse,
    "line": draw_line,
    "arrow": draw_arrow,
    "star": draw_star,
    "rect": draw_rect,
    "text": draw_text,
    "bar": draw_bar,
    "ring": draw_ring,
}


# --- сборка кадра -----------------------------------------------------------

# «набор не указан» - не то же самое, что «следить за всеми» (None)
_MISSING_WATCH = object()

# Доли погоды и украшений, которые панель привязывает к своей доле дня.
SKY_KEYS = ("sky_clear", "sky_clouds", "sky_grey", "sky_rain", "sky_snow",
            "sky_storm", "sky_fog", "snow_calm", "snow_windy")

# Мороз и жара считаются по градусам и ко дню не привязаны: изморозь
# на стекле не пропадает оттого, что стемнело.
FROST = (-10.0, -22.0)      # ниже первого начинается, ко второму в полную силу
HEAT = (30.0, 42.0)

# Показывать ли погоду днём и ночью. Порознь: кому-то дождь на ночной
# теме мешает, кому-то наоборот. Звёзды, солнце и метеоры к погоде
# отношения не имеют и этими переключателями не гасятся.
WEATHER_DAY = True
WEATHER_NIGHT = True

# Насколько близко к краю суток появляется и исчезает всё небесное.
# Посреди перехода на экране только планеты и цифры - см. УСТРОЙСТВО.md,
# «Погода и доли неба».
GATE_EDGE = 0.12


def _gate(x):
    """Плавная ступенька: 0 слева, 1 справа, без рывков на краях."""
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


# --- плавная смена дневного и ночного вида -----------------------------------

def _is_colorish(v):
    return (isinstance(v, str) and v.startswith("#")) or \
           (isinstance(v, (list, tuple)) and 3 <= len(v) <= 4)


def _mix_color(a, b, f):
    ca, cb = parse_color(a), parse_color(b)
    if not ca or not cb:
        return b if f >= 0.5 else a
    return tuple(int(round(x + (y - x) * f)) for x, y in zip(ca, cb))



# --- кривые перехода ---------------------------------------------------------

# Три регулятора складываются в кубическую кривую Безье, как в видеоредакторах.
# Начало и конец задают, насколько медленно движение стартует и тормозит,
# середина - насколько круто оно проходит середину пути.
SPEED = {"резко": 0.0, "sharp": 0.0,
         "средне": 0.35, "medium": 0.35,
         "плавно": 0.75, "slow": 0.75}
MIDDLE = {"резко": 0.0, "sharp": 0.0,
          "средне": 0.18, "medium": 0.18,
          "плавно": 0.35, "slow": 0.35}


_bezier_cache = {}


def _bezier_y(x, x1, y1, x2, y2):
    """Значение кривой Безье в точке x. Кривая задана как в CSS.

    Считается для каждого блока в каждом кадре, а кривых в теме всего
    несколько, поэтому ответы запоминаем. Доля округляется до тысячной:
    на глаз это неотличимо, а попаданий в память становится много больше.
    """
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    key = (round(x, 3), x1, y1, x2, y2)
    got = _bezier_cache.get(key)
    if got is not None:
        return got
    x = key[0]

    def bx(t):
        u = 1 - t
        return 3 * u * u * t * x1 + 3 * u * t * t * x2 + t * t * t

    def by(t):
        u = 1 - t
        return 3 * u * u * t * y1 + 3 * u * t * t * y2 + t * t * t

    # ищем параметр t, при котором кривая даёт нужный x
    lo, hi, t = 0.0, 1.0, x
    for _ in range(24):
        cur = bx(t)
        if abs(cur - x) < 1e-5:
            break
        if cur < x:
            lo = t
        else:
            hi = t
        t = (lo + hi) / 2.0
    out = by(t)
    if len(_bezier_cache) > 20000:
        _bezier_cache.clear()
    _bezier_cache[key] = out
    return out


def _curve_of(anim):
    """Четыре числа кривой: либо заданы прямо, либо собраны из регуляторов."""
    curve = anim.get("curve")
    if isinstance(curve, (list, tuple)) and len(curve) == 4:
        return tuple(float(v) for v in curve)
    s = SPEED.get(str(anim.get("ease_in", "средне")).lower(), 0.35)
    e = SPEED.get(str(anim.get("ease_out", "средне")).lower(), 0.35)
    m = MIDDLE.get(str(anim.get("ease_mid", "средне")).lower(), 0.18)
    return s, m, 1.0 - e, 1.0 - m


def layer_progress(layer, f):
    """Насколько блок продвинулся к дневному виду при общей доле дня f.

    У блока может быть свой отрезок перехода и своя кривая: один начнёт
    двигаться в самом начале рассвета, другой подхватит в середине.
    """
    anim = layer.get("anim") or {}
    start = float(anim.get("start", 0.0))
    end = float(anim.get("end", 1.0))
    if end <= start:
        local = 1.0 if f >= end else 0.0
    else:
        local = (f - start) / (end - start)
    return _ease(anim, local)


# чему равно поле, если в обычном виде оно не задано
BLEND_DEFAULTS = {"opacity": 1.0, "angle": 0.0,
                  "stretch_x": 1.0, "stretch_y": 1.0}


def transition_minutes(cfg):
    """Длительность смены темы в минутах.

    Задать можно и в секундах - так удобнее, когда переход нужен быстрый,
    например три секунды вместо получаса.
    """
    scr = cfg.get("screen", {})
    if scr.get("transition_seconds"):
        return float(scr["transition_seconds"]) / 60.0
    return float(scr.get("transition_minutes", 45))


def _ease(anim, local):
    """Прогнать долю через кривую, заданную тремя регуляторами."""
    return _bezier_y(max(0.0, min(1.0, local)), *_curve_of(anim))


def mix_fields(layer, target, f):
    """Смешать поля блока с целевым набором в пропорции f."""
    if not target or f <= 0.001:
        return layer
    out = dict(layer)
    for k, v in target.items():
        base = layer.get(k)
        if base is None and isinstance(v, (int, float)) and not isinstance(v, bool):
            # в обычном виде поле не задано - берём его молчаливое значение,
            # а если и его нет, смешивать не с чем: ставим целевое как есть
            base = BLEND_DEFAULTS.get(k)
            if base is None:
                out[k] = v
                continue
        if isinstance(v, bool) or isinstance(base, bool):
            out[k] = v if f >= 0.5 else base
        elif isinstance(v, (int, float)) and isinstance(base, (int, float)):
            out[k] = base + (v - base) * f
        elif _is_colorish(v) and _is_colorish(base):
            out[k] = _mix_color(base, v, f)
        else:
            out[k] = v if f >= 0.5 else base
    return out


def blend_layer(layer, f):
    """Ночной вид блока, смешанный с дневным по общей доле дня."""
    day = layer.get("day")
    if not day:
        return layer
    return mix_fields(layer, day, layer_progress(layer, f))


def loop_progress(loop, t):
    """Доля повторяющейся анимации в момент времени t."""
    period = float(loop.get("seconds", 2) or 2)
    if period <= 0:
        return 0.0
    phase = (t % period) / period
    if str(loop.get("mode", "pingpong")).lower() in ("pingpong", "туда-обратно"):
        phase = 1.0 - abs(2.0 * phase - 1.0)   # плавно туда и обратно
    return _ease(loop, phase)


def react_progress(react, data):
    """Доля реакции на датчик: 0 до порога, 1 после верхней границы."""
    key = react.get("value")
    v = data.get(key) if key else None
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return 0.0
    lo = float(react.get("from", 0))
    hi = float(react.get("to", 100))
    if hi == lo:
        return 1.0 if v >= hi else 0.0
    return _ease(react, (float(v) - lo) / (hi - lo))


def apply_variants(layer, f_day, t, data):
    """Собрать итоговый вид блока: день, затем повтор, затем реакция."""
    out = blend_layer(layer, f_day)
    loop = layer.get("loop")
    if loop and loop.get("to"):
        amount = loop_progress(loop, t)
        # Повтор можно включать по датчику: «мигай, но только когда гроза».
        # Без этого молнию было не сделать - она сверкала бы и в ясный день.
        when = loop.get("when")
        if when:
            amount *= react_progress(when, data)
        out = mix_fields(out, loop["to"], amount)
    react = layer.get("react")
    if react and react.get("to_state"):
        out = mix_fields(out, react["to_state"], react_progress(react, data))
    return out


class Panel:
    def __init__(self, layout_path=DEFAULT_LAYOUT, cfg=None, static=False,
                 base_dir=None):
        """static=True - брать только первый кадр фона.

        Нужно редактору: там анимация не важна, а ждать разбора шестисот
        кадров при каждой правке невыносимо.
        """
        if cfg is None:
            with open(layout_path, encoding="utf-8") as f:
                cfg = json.load(f)
        self.cfg = cfg
        self.static = static
        # Всё, на что ссылается тема - папки кадров, картинки, шрифты -
        # ищется рядом с её файлом. Тогда тему можно держать в любом месте
        # и переносить целиком вместе с содержимым.
        self.base_dir = os.path.abspath(
            base_dir if base_dir else
            (os.path.dirname(os.path.abspath(layout_path)) if layout_path else "."))
        scr = self.cfg.get("screen", {})
        self.width = int(scr.get("width", 960))
        self.height = int(scr.get("height", 480))
        self.background = parse_color(scr.get("background", "#000000ff"))
        self._scale_was = self.scale
        # auto   - по солнцу, восход и закат
        # system - вслед за светлым или тёмным оформлением Windows
        # night  - всегда ночная, day - всегда дневная
        self.day_mode = str(scr.get("day_mode", "auto")).lower()
        # instant=True - никакой плавности, сразу конечный вид.
        # Так работает предпросмотр: анимацию проигрывает только экран.
        self.instant = False
        self._f_now = None
        self._f_time = None
        self.fonts = self.cfg.get("fonts", {})
        # слои сортируем по z, если он указан, иначе по порядку в файле
        layers = list(self.cfg.get("layers", []))
        self.layers = sorted(enumerate(layers),
                             key=lambda p: (p[1].get("z", p[0]), p[0]))
        self.layers = [l for _, l in self.layers]

        # Отрезки трёх видов: картинки, живые (есть повтор) и спокойные.
        # Зачем это нужно - в УСТРОЙСТВО.md, «Отрезки и отпечатки».
        self.runs = []
        for layer in self.layers:
            if layer.get("type") == "image":
                kind = "image"
            elif layer.get("loop"):
                # Живой - только тот, кто зависит от времени. Реакция на
                # датчик времени не требует: показания и так входят
                # в отпечаток, а меняются они раз в секунду, а не в кадр.
                kind = "live"
            else:
                kind = "draw"
            if self.runs and self.runs[-1][0] == kind:
                self.runs[-1][1].append(layer)
            else:
                self.runs.append((kind, [layer]))

        # Доля перехода считается по слоям с дневным видом, а не по теме
        # целиком: доехавший слой дальше не меняется. См. УСТРОЙСТВО.md.
        self._run_day_layers = [[l for l in layers if l.get("day")]
                                for _kind, layers in self.runs]
        self._run_cares_day = [bool(day) for day in self._run_day_layers]
        # Своя частота у повтора: ноль - как у всей панели.
        # Почему без неё дорого - в УСТРОЙСТВО.md, «Своя частота у повтора».
        self._run_rate = [max([float(l["loop"].get("fps", 0) or 0)
                               for l in layers if l.get("loop")] or [0])
                          for _kind, layers in self.runs]
        self._overlay_cache = {}
        self.has_motion = any(l.get("loop") or l.get("react")
                              for l in self.layers)
        self._font_paths = {}
        self._paths = {}         # где на самом деле лежит то, на что ссылаются
        self._frame_cache = {}   # последний распакованный кадр слоя
        # где у каждой картинки «своё место» для выреза, см. _mask_home
        self._homes = {id(l): self._mask_home(l) for l in self.layers
                       if l.get("type") == "image"}
        self._watch = self._collect_watch()
        # У каждого отрезка свой набор показаний: он смотрит только на то,
        # что на нём видно.
        self._run_watch = [None if self._watch is None
                           else self._collect_watch(layers)
                           for _kind, layers in self.runs]

    # Частота, качество и сглаживание читаются из описания каждый раз,
    # а не запоминаются при загрузке: настройку меняют на ходу, и работающая
    # на экране панель должна её увидеть, а не помнить старую.

    @property
    def fps(self):
        # ниже половины кадра в секунду экран решает, что его бросили,
        # и возвращается к заводской заставке
        return max(0.5, float(self.cfg.get("screen", {}).get("fps", 1) or 1))

    @property
    def quality(self):
        return max(1, min(100, int(self.cfg.get("screen", {})
                                   .get("quality", 85) or 85)))

    @property
    def scale(self):
        return max(1, min(4, int(self.cfg.get("screen", {})
                                 .get("supersample", 2) or 1)))

    @property
    def pack_frames(self):
        return bool(self.cfg.get("screen", {}).get("pack_frames", True))

    @property
    def potokov(self):
        """Во сколько потоков собирать отрезки кадра.

        Настройка машины, а не темы: одна и та же тема на слабом ноутбуке
        и на шестнадцати ядрах должна идти по-разному. Поэтому лежит
        в settings.json, а не в описании темы.

        0 - решить самому. Это два потока, а не по числу ядер: замерено
        на 32 потоках и теме в 97 слоёв (.проверки/potoki.py). Два потока
        срезают около 9 % времени отрисовки, четыре не дают ничего -
        упирается не в ядра, а в то, сколько отрезков за кадр вообще
        успело устареть. Обычно их единицы.
        """
        n = int(prefs.get("speed.threads", 1) or 1)
        if n == 0:
            return 1 if (os.cpu_count() or 1) < 4 else 2
        return max(1, min(16, n))

    def _pul(self):
        """Пул потоков для сборки отрезков. Нет - значит один поток.

        Пул держим один и переделываем, только если человек поменял
        настройку: создание пула стоит дороже кадра.
        """
        n = self.potokov
        if n <= 1:
            return None
        pul = getattr(self, "_pul_gotov", None)
        if pul is None or self._pul_razmer != n:
            if pul is not None:
                pul.shutdown(wait=False)
            from concurrent.futures import ThreadPoolExecutor
            pul = ThreadPoolExecutor(max_workers=n,
                                     thread_name_prefix="otrezok")
            self._pul_gotov, self._pul_razmer = pul, n
        return pul

    @property
    def trans_sec(self):
        """Сколько длится смена дня и ночи.

        Ручное переключение режима тоже идёт плавно, а не рывком: держим
        текущую долю дня и подтягиваем её к целевой за это время.
        """
        return max(0.2, transition_minutes(self.cfg) * 60.0)

    def _collect_watch(self, layers=None):
        """Какие показания участвуют в картинке (или в одном отрезке).

        Слои перерисовываются, только когда меняется то, что на них видно.
        Если тема показывает одни часы, незачем перерисовывать её из-за
        скачков загрузки сети. Для времени запоминаем ещё и формат: панель
        с часами без секунд должна обновляться раз в минуту, а не раз в
        секунду.

        Возвращает набор пар (имя, набор форматов) либо None - тогда
        отпечаток считается по всем показаниям подряд.
        """
        if layers is None:
            layers = self.layers
        keys = {}

        def note(name, spec):
            if not name or not isinstance(name, str):
                raise ValueError(name)
            keys.setdefault(name, set()).add(spec or "")

        def walk(node, field=None):
            if isinstance(node, dict):
                for k, v in node.items():
                    walk(v, k)
            elif isinstance(node, (list, tuple)):
                for v in node:
                    walk(v, field)
            elif isinstance(node, str):
                if field == "value":
                    note(node, None)      # у полосы и кольца это имя датчика
                if "{" in node:
                    for _, name, spec, _ in _fmt.parse(node):
                        if name is not None:
                            note(name, spec)

        try:
            walk(layers)
        except Exception:
            return None       # что-то необычное - считаем по всем показаниям
        return tuple(sorted((k, tuple(sorted(v))) for k, v in keys.items()))

    def resolve(self, name):
        """Путь относительно папки темы, если там такое есть.

        Ответ запоминаем: он не меняется, а спрашивают о нём каждый кадр
        по разу на каждый слой-картинку - это десяток обращений к диску
        тридцать раз в секунду впустую.
        """
        if not name:
            return name
        got = self._paths.get(name)
        if got is None:
            got = name
            if not (os.path.isabs(name) and os.path.exists(name)):
                near = os.path.join(self.base_dir, name)
                if os.path.exists(near):
                    got = near
            self._paths[name] = got
        return got

    def _font_of(self, name):
        """Файл шрифта и размер по умолчанию для имени из слоя.

        Ответ запоминаем: он не меняется, а иначе на каждую надпись
        в каждом кадре шло обращение к диску.
        """
        got = self._font_paths.get(name)
        if got is None:
            if name in self.fonts:
                f = self.fonts[name]
                got = (f.get("file"), f.get("size", 24))
            else:
                got = (name, None)
                for near in (os.path.join(self.base_dir, "fonts", name),
                             os.path.join(self.base_dir, name)):
                    if os.path.exists(near):
                        got = (near, None)
                        break
            self._font_paths[name] = got
        return got

    def _resolve_font(self, layer):
        """Слой может ссылаться на шрифт по имени из раздела fonts."""
        name = layer.get("font")
        if not name:
            return layer
        path, size = self._font_of(name)
        if path == name and size is None:
            return layer            # имя и есть имя файла, менять нечего
        merged = dict(layer)
        merged["font"] = path
        if size is not None and "size" not in layer:
            merged["size"] = size
        return merged

    def render(self, data, frame_no=0, t=None):
        """Собрать кадр.

        Две вещи, которые делают 30 кадров в секунду возможными.

        Первое: слои с цифрами и дугами меняются раз в секунду, вместе с
        показаниями датчиков. Пересчитывать их 30 раз в секунду незачем,
        поэтому результат кэшируется и переотрисовывается только когда
        показания реально изменились.

        Второе: кадры фона подготавливаются один раз при загрузке -
        масштаб, маска, режим premultiplied. В цикле остаётся только
        наложение.
        """
        k = self.scale
        if k != self._scale_was:
            # сглаживание поменяли на ходу: всё, что лежит в памяти,
            # нарисовано с прежним, и брать его оттуда больше нельзя
            self._overlay_cache.clear()
            self._scale_was = k
        base_size = (self.width, self.height)
        big_size = (self.width * k, self.height * k)
        if t is None:
            t = frame_no / float(self.fps or 1)

        if self.day_mode == "night":
            target = 0.0
        elif self.day_mode == "day":
            target = 1.0
        elif self.day_mode == "system":
            # вслед за оформлением самой Windows: светлая тема - дневной вид,
            # тёмная - ночной. Переключается так же плавно, как по солнцу
            target = 1.0 if data.get("system_light") else 0.0
        else:
            target = float(data.get("day_factor", 0) or 0)

        now = time.time()
        if self.instant or self._f_now is None:
            self._f_now = target          # сразу конечный вид
        else:
            dt = max(0.0, now - (self._f_time or now))
            step = dt / self.trans_sec
            if self._f_now < target:
                self._f_now = min(target, self._f_now + step)
            elif self._f_now > target:
                self._f_now = max(target, self._f_now - step)
        self._f_time = now
        f = self._f_now
        data = self._sky_by_day(data, f)

        # Отпечаток считаем отдельно для каждого отрезка, по тем показаниям,
        # что на нём видны. Одинаковые наборы встречаются часто, поэтому
        # готовый ответ придерживаем.
        sig_by_watch = {}

        def data_sig_for(watch):
            got = sig_by_watch.get(watch)
            if got is None:
                got = sig_by_watch[watch] = self._signature(data, watch)
            return got

        canvas = self._background(base_size, f)

        # Сначала считаем отпечатки и смотрим, какие отрезки устарели.
        # Собирать их можно в любом порядке и хоть в несколько потоков -
        # отрезки друг о друге не знают. А вот накладывать на холст надо
        # строго по очереди, иначе слои перепутаются местами.
        poryadok = []
        ustareli = []
        for run_no, (kind, layers) in enumerate(self.runs):
            if kind == "image":
                poryadok.append((run_no, kind, layers))
                continue
            sig = (self._day_mark(run_no, f),
                   data_sig_for(self._run_watch[run_no]))
            t_run = t
            if kind == "live":
                # У повтора может быть своя частота. Тогда время для него
                # идёт ступеньками: и отпечаток, и сама отрисовка берут
                # одну и ту же ступеньку, иначе картинка разошлась бы
                # с тем, что записано в памяти.
                rate = self._run_rate[run_no]
                if rate:
                    t_run = round(t * rate) / rate
                sig += (round(t_run, 3),)
            poryadok.append((run_no, kind, layers))
            cached = self._overlay_cache.get(run_no)
            if cached is None or cached[0] != sig:
                ustareli.append((run_no, layers, sig, t_run))

        if ustareli:
            self._sobrat_otrezki(ustareli, data, big_size, k, f, frame_no)

        for run_no, kind, layers in poryadok:
            if kind == "image":
                for layer in layers:
                    if layer.get("hidden"):
                        continue
                    try:
                        self._draw_prepared(canvas, apply_variants(layer, f, t, data),
                                            base_size, frame_no, t,
                                            self._homes.get(id(layer)))
                    except Exception as e:
                        print("  слой image ({}): {}".format(layer.get("name", ""), e))
                continue
            cached = self._overlay_cache.get(run_no)
            if cached is not None and cached[1] is not None:
                canvas.alpha_composite(cached[1], cached[2])

        return canvas.convert("RGB")

    def _sobrat_otrezki(self, ustareli, data, big_size, k, f, frame_no):
        """Пересобрать устаревшие отрезки - в один поток или в несколько.

        В несколько имеет смысл только когда их правда несколько: на один
        отрезок пул стоит дороже самой работы.
        """
        pul = self._pul() if len(ustareli) > 1 else None
        rabota = [(run_no, layers, sig, t_run)
                  for run_no, layers, sig, t_run in ustareli]
        if pul is None:
            for run_no, layers, sig, t_run in rabota:
                self._overlay_cache[run_no] = self._otrezok(
                    layers, sig, data, big_size, k, f, t_run, frame_no)
            return
        gotovo = list(pul.map(
            lambda z: (z[0], self._otrezok(z[1], z[2], data, big_size, k, f,
                                           z[3], frame_no)),
            rabota))
        for run_no, cached in gotovo:
            self._overlay_cache[run_no] = cached

    def _otrezok(self, layers, sig, data, big_size, k, f, t_run, frame_no):
        """Собрать один отрезок в отдельную картинку."""
        # Сначала выясняем, кому вообще есть что рисовать. Пустому
        # отрезку не нужен ни холст, ни поиск занятой области: а пустых
        # бывает много - все украшения, пока идёт не их половина суток.
        ready = []
        for layer in layers:
            if layer.get("hidden"):
                continue
            fn = DRAWERS.get(layer.get("type"))
            if not fn:
                continue
            try:
                eff = apply_variants(layer, f, t_run, data)
                # полностью прозрачный блок рисовать незачем:
                # при разлёте таких в каждый момент около половины
                if float(eff.get("opacity", 1) or 0) <= 0.003:
                    continue
                ready.append((fn, eff))
            except Exception as e:
                print("  слой {} ({}): {}".format(
                    layer.get("type"), layer.get("name", ""), e))
        if not ready:
            return (sig, None, (0, 0))
        over = Image.new("RGBA", big_size, (0, 0, 0, 0))
        for fn, eff in ready:
            try:
                draw_transformed(
                    over, self._scale_layer(self._resolve_font(eff), k),
                    data, big_size, frame_no, fn)
            except Exception as e:
                print("  слой {} ({}): {}".format(
                    eff.get("type"), eff.get("name", ""), e))
        return (sig,) + self._shrink(over, k)

    def _background(self, size, f):
        """Заливка под всеми слоями.

        Обычно это один цвет, ночной и дневной, между которыми фон плавно
        перетекает. Но если задан второй цвет, получается градиент - и тогда
        ночное небо можно сделать не плоским, а с глубиной, не заводя ради
        этого слой во весь экран.

        Описание читаем каждый кадр, а не запоминаем при загрузке: в
        настройках фон можно менять на ходу, и правка должна быть видна
        сразу. Разбор цвета всё равно берётся из памяти, а готовое полотно
        придерживаем - пока доля дня не сдвинулась, оно то же самое.
        """
        scr = self.cfg.get("screen", {})
        night, day = scr.get("background", "#000000ff"), scr.get("background_day")
        mix = (lambda a, b: _mix_color(a, b, f) if (b and f > 0.001)
               else (parse_color(a) or (0, 0, 0, 255)))
        top = mix(night, day)

        second = scr.get("background2")
        if not second and not scr.get("background_day2"):
            return Image.new("RGBA", size, top)

        bottom = mix(second or night, scr.get("background_day2") or day)
        key = (size, top, bottom, scr.get("background_gradient", "v"))
        if getattr(self, "_bg_ready", None) is None or self._bg_ready[0] != key:
            self._bg_ready = (key, _gradient(size, top, bottom, key[3]))
        return self._bg_ready[1].copy()

    @staticmethod
    def _mask_home(layer):
        """Где слой стоит, когда его видно лучше всего.

        Вырез задан в координатах экрана, поэтому считать его надо по
        домашнему месту слоя, а не по текущему. Почему - в УСТРОЙСТВО.md,
        «Маска по домашнему месту».
        """
        day = layer.get("day") or {}
        base_op = float(layer.get("opacity", 1.0) or 0.0)
        day_op = float(day.get("opacity", base_op) or 0.0)
        if day_op > base_op:
            return {"x": day.get("x", layer.get("x", 0)),
                    "y": day.get("y", layer.get("y", 0))}
        return {"x": layer.get("x", 0), "y": layer.get("y", 0)}

    def _day_mark(self, run_no, f):
        """Насколько отрезок продвинулся к дневному виду.

        Отрезок, в котором ни у кого нет дневного вида, от доли дня не
        зависит вовсе - у него ноль. У остальных считаем долю по каждому
        слою отдельно: у слоя может быть свой отрезок перехода, и когда
        он пройден, слой замирает. Замерли все - замирает и отпечаток,
        а значит картинка берётся из памяти.
        """
        day = self._run_day_layers[run_no]
        if not day:
            return 0
        return tuple(round(layer_progress(l, f), 3) for l in day)

    @staticmethod
    def _sky_by_day(data, f):
        """Привязать погоду и украшения к той доле дня, которую рисует панель.

        Долю дня знает только панель: в меню можно приказать «всегда ночная»,
        и тогда неважно, что солнце снаружи стоит высоко. Пока этим занимались
        датчики, на ночной теме шёл дождь, плыли облака и не было ни одной
        звезды, а круглый задник луны, наоборот, оставался на дневной.

        Появляется и гаснет всё небесное у самых краёв суток, а не через всю
        дорогу перехода. Иначе на рассвете экран показывал разом звёзды,
        облака и переезжающие блоки - и не успевал: ореол вокруг луны один
        стоит треть кадра, а перерисовывался все десять секунд подряд.
        """
        day = _gate((f - (1.0 - GATE_EDGE)) / GATE_EDGE)
        night = _gate((GATE_EDGE - f) / GATE_EDGE)
        # Погода видна и днём, и ночью - каждую половину суток можно
        # выключить отдельно. Посреди перехода обе доли равны нулю,
        # поэтому экран там по-прежнему чистый.
        vidno = (day if WEATHER_DAY else 0.0) + (night if WEATHER_NIGHT else 0.0)
        vidno = min(1.0, vidno)

        out = dict(data)
        for key in SKY_KEYS:
            v = out.get(key)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[key] = round(float(v) * vidno, 3)
        # солнце светит, когда ясно И день - иначе оно светило бы в полночь
        out["sky_sun"] = round(float(out.get("sky_clear", 0.0)) * day, 3)
        # Мороз и жара - по градусам, а не по времени суток.
        gradusy = out.get("weather_temp")
        gradusy = float(gradusy) if isinstance(gradusy, (int, float)) else None
        for key, (ot, do) in (("sky_frost", FROST), ("sky_heat", HEAT)):
            out[key] = 0.0 if gradusy is None else round(
                _gate((gradusy - ot) / (do - ot)) * vidno, 3)
        # Долю дня выключатели не трогают: звёзды, солнце и метеоры
        # к погоде отношения не имеют и живут дальше.
        out["sky_day"] = round(day, 3)
        out["sky_night"] = round(night, 3)
        return out

    @staticmethod
    def _shrink(over, k):
        """Уменьшить крупный холст до размера экрана.

        Уменьшается не весь холст, а только занятая часть. Это не
        приблизительный приём: границу обрезки кладём на кратные k
        пиксели, а значит каждый квадрат k x k целиком либо попадает
        в обрезок, либо не попадает вовсе и всё равно пустой.

        Выигрыш заметный: Pillow уменьшает RGBA в три прохода по всем
        пикселям, и на слое из четырёх надписей в углу экрана это была
        почти половина всего времени кадра.
        """
        box = over.getbbox()
        if box is None:
            return None, (0, 0)          # рисовать нечего
        if k <= 1:
            return over.crop(box), (box[0], box[1])
        x0 = (box[0] // k) * k
        y0 = (box[1] // k) * k
        x1 = min(over.width, -(-box[2] // k) * k)
        y1 = min(over.height, -(-box[3] // k) * k)
        part = over.crop((x0, y0, x1, y1))
        # reduce - точное усреднение блоков k x k. Для целого коэффициента
        # это ровно то, что нужно для сглаживания, и впятеро быстрее
        # LANCZOS на больших холстах.
        if part.width % k == 0 and part.height % k == 0:
            part = part.reduce(k)
        else:
            part = part.resize((max(1, part.width // k),
                                max(1, part.height // k)), Image.LANCZOS)
        return part, (x0 // k, y0 // k)

    def _signature(self, data, watch=_MISSING_WATCH):
        """Отпечаток показаний. Пока он не меняется, перерисовывать нечего.

        watch - набор имён, за которыми следим. None - следить за всеми.
        Если не указан вовсе, берём набор всей темы.
        """
        if watch is _MISSING_WATCH:
            watch = self._watch
        # Сверяем то же, что и покажем. При Фаренгейте шаг шкалы мельче:
        # два разных градуса Цельсия могут дать одно целое число, а после
        # перевода - два разных, и надпись отстала бы на кадр.
        data = edinicy.dlya_teksta(data)
        if watch is None:
            return tuple((key, self._mark(key, data[key]))
                         for key in sorted(data))
        parts = []
        for key, specs in watch:
            v = data.get(key)
            if hasattr(v, "strftime"):
                # время: смотрим ровно на то, что попадёт в надпись
                try:
                    parts.append((key, tuple(v.strftime(s) if s else str(v)[:19]
                                             for s in specs)))
                except Exception:
                    parts.append((key, str(v)[:19]))
            elif isinstance(v, float):
                parts.append((key, self._mark_number(v, specs)))
            else:
                parts.append((key, self._mark(key, v)))
        return tuple(parts)

    @staticmethod
    def _mark_number(v, specs):
        """Отпечаток числа с той точностью, с какой оно видно на панели.

        Надпись «{cpu_load:.0f}» показывает целые проценты - значит пока
        целая часть не изменилась, перерисовывать нечего, сколько бы ни
        дёргалась дробная.

        А вот число, которое участвует в самой картинке - долей заполнения
        кольца, реакцией на датчик, - надо брать точно, до тысячных: доли
        неба ходят от нуля до единицы, и грубое округление превратило бы
        плавное появление в три ступеньки.
        """
        out = []
        for s in specs:
            try:
                out.append(format(v, s) if s else round(v, 3))
            except (ValueError, TypeError):
                out.append(round(v, 3))
        return tuple(out)

    @staticmethod
    def _mark(key, v):
        if isinstance(v, float):
            return round(v, 3)
        if isinstance(v, int):
            return v
        if key == "day_factor":
            return round(float(v), 2)
        if hasattr(v, "replace") and hasattr(v, "year"):
            return v.replace(microsecond=0)
        return str(v)

    def _cache_path(self, key):
        """Файл с разобранными кадрами. Имя - по настройкам слоя."""
        h = hashlib.sha1(repr(key).encode("utf-8")).hexdigest()[:16]
        return os.path.join(self.base_dir, CACHE_DIR, h + ".bin")

    @staticmethod
    def _fingerprint(sources):
        """Отпечаток исходников: имена, размеры, время правки."""
        h = hashlib.sha1()
        for s in sources:
            if not isinstance(s, str):
                return None          # кадры из GIF, отдельных файлов нет
            try:
                st = os.stat(s)
            except OSError:
                return None
            h.update("{}|{}|{}".format(os.path.basename(s), st.st_mtime_ns,
                                       st.st_size).encode("utf-8"))
        return h.hexdigest()

    @staticmethod
    def _cache_read(path, mark):
        """Поднять кадры с диска.

        mark - отпечаток исходников или None, если их рядом нет. Пока
        исходники на месте, они и решают: разошлись - кадры собираем
        заново. А если их убрали, кэш годится сам по себе.
        """
        try:
            with open(path, "rb") as f:
                if f.read(len(CACHE_MARK)) != CACHE_MARK:
                    return None
                head = json.loads(
                    f.read(int.from_bytes(f.read(4), "little")).decode("utf-8"))
                data = f.read()
        except (OSError, ValueError, KeyError):
            return None
        if mark is not None and head.get("исходники") != mark:
            return None
        frames, at = [], 0
        for w, h, ox, oy, size in head.get("кадры", []):
            if not size:
                frames.append((None, 0, 0))
                continue
            if at + size > len(data):
                return None
            frames.append((_Packed.raw(data[at:at + size], w, h), ox, oy))
            at += size
        return frames

    @staticmethod
    def _cache_write(path, frames, mark):
        head = {"исходники": mark,
                "кадры": [[f.width if f else 0, f.height if f else 0, ox, oy,
                           len(f.blob) if f else 0] for f, ox, oy in frames]}
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "wb") as out:
                body = json.dumps(head, ensure_ascii=False).encode("utf-8")
                out.write(CACHE_MARK)
                out.write(len(body).to_bytes(4, "little"))
                out.write(body)
                for f, _ox, _oy in frames:
                    if f:
                        out.write(f.blob)
            os.replace(tmp, path)
        except OSError:
            pass

    def _prepare_frames(self, layer, base_size, home=None):
        """Один раз привести кадры слоя к готовому виду.

        Обрабатываем по одному, а не загружаем всё сразу: 600 кадров
        в распакованном виде это гигабайт, и держать его незачем.
        Каждый кадр сразу обрезается по своей видимой области, и уже
        обрезанный пересчитывается из режима premultiplied - это втрое
        меньше работы, чем по всему кадру.

        home - слой на своём домашнем месте, до дневного вида и повторов.
        Маска считается по НЕМУ, а не по тому, где слой оказался сейчас:
        едущий слой проезжает десятки целых значений x, и кадры готовились
        бы заново на каждое из них.
        """
        # Прозрачность в ключ НЕ входит: при смене темы она меняется на
        # каждом кадре, и пересчитывать из-за неё сотни кадров недопустимо.
        # Её применяем позже, в момент наложения.
        home = home if home is not None else layer
        src = self.resolve(layer.get("src"))
        # в предпросмотре кадр всего один, сжимать его незачем
        pack = self.pack_frames and not self.static
        # В ключ идёт src, как он записан в теме, а не найденный путь:
        # иначе, стоит убрать исходники, ключ поменяется и кэш не найдётся.
        key = (layer.get("src"), layer.get("w"), layer.get("h"),
               layer.get("fit"), layer.get("premultiplied"),
               repr(layer.get("mask")), layer.get("alpha_gain"),
               layer.get("mirror"), layer.get("flip"), self.static, pack,
               (int(home.get("x", 0)), int(home.get("y", 0)))
               if layer.get("mask") else None)
        if key in _PREPARED:
            return _PREPARED[key]

        sources = _frame_sources(src) if src and os.path.exists(src) else []
        if self.static:
            sources = sources[:1]
        total = len(sources)

        # Разбор сотен кадров - это десятки секунд при каждом запуске,
        # а результат один и тот же. Держим его рядом с темой. Если
        # исходники убрали, кадры поднимутся отсюда и без них.
        cache = self._cache_path(key) if pack else None
        if cache:
            mark = self._fingerprint(sources) if total else None
            got = self._cache_read(cache, mark)
            if got is not None and (not total or len(got) == total):
                _PREPARED[key] = got
                print("  фон «{}»: {} кадров подняты с диска".format(
                    layer.get("name", src), len(got)))
                return got

        if not total:
            _PREPARED[key] = None
            return None
        # Вырез кладём по домашнему месту слоя: тогда он едет вместе
        # с картинкой, а не остаётся дыркой в воздухе.
        layer = dict(layer, src=src, x=home.get("x", 0), y=home.get("y", 0))

        loud = total > 120
        if loud:
            print("  готовлю фон «{}»: {} кадров...".format(
                layer.get("name", src), total))

        prep_layer = dict(layer)
        prep_layer.pop("opacity", None)

        def one(item):
            img = item if isinstance(item, Image.Image) else Image.open(item)
            img = img.convert("RGBA")
            img = process_frame(img, prep_layer, base_size)
            box = img.getbbox()
            if box is None:
                # Пустой кадр. У метеоров таких три четверти: небо и должно
                # быть пустым большую часть времени. Хранить и накладывать
                # тут нечего - полмиллиона прозрачных точек.
                return None, 0, 0
            img = img.crop(box)
            if layer.get("premultiplied"):
                img = _unpremultiply(img)
            return (_Packed(img) if pack else img), box[0], box[1]

        frames = []
        try:
            from concurrent.futures import ThreadPoolExecutor
            workers = min(8, (os.cpu_count() or 4))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for i, res in enumerate(pool.map(one, sources)):
                    frames.append(res)
                    if loud and (i + 1) % max(1, total // 20) == 0:
                        print("    {:3.0f} %".format(100.0 * (i + 1) / total),
                              end="\r", flush=True)
        except Exception:
            frames = [one(s) for s in sources]
        if loud:
            print("          ", end="\r")

        _PREPARED[key] = frames
        _image_cache.pop(src, None)
        if cache:
            self._cache_write(cache, frames, self._fingerprint(sources))

        full = sum(f.width * f.height * 4 for f, _, _ in frames if f) / 1048576.0
        mem = (sum(len(f) for f, _, _ in frames if f) / 1048576.0
               if pack else full)
        was = total * base_size[0] * base_size[1] * 4 / 1048576.0
        print("  фон «{}»: {} кадров, память {:.0f} МБ вместо {:.0f}{}".format(
            layer.get("name", src), total, mem, was,
            " (сжаты, без потерь)" if pack else ""))
        return frames

    def _draw_prepared(self, canvas, layer, base_size, frame_no, t, home=None):
        """Наложить заранее подготовленный кадр фона.

        У слоя может быть своя частота: кадры нарезаны с одной скоростью,
        а панель выводит с другой. Без этого 60 кадров, нарезанных под
        3 в секунду, при выводе 30 проиграются за две секунды вместо
        двадцати.
        """
        # Кадры готовим ВСЕГДА, даже когда слой сейчас невидим. Иначе
        # «земля» разбиралась бы не при запуске, а посреди рассвета,
        # когда она впервые проступает - и переход вставал бы намертво.
        frames = self._prepare_frames(layer, base_size, home)
        if not frames:
            return
        op = float(layer.get("opacity", 1.0) or 0.0)
        if op <= 0.002:
            return
        if self.static:
            # предпросмотр: только первый файл из папки, без перелистывания
            idx = 0
        else:
            own_fps = float(layer.get("fps", 0) or self.fps)
            idx = int(t * own_fps) % len(frames)
        img, ox, oy = frames[idx]
        if img is None:
            return                       # пустой кадр, накладывать нечего
        if isinstance(img, _Packed):
            # Держим последний распакованный: у слоя может быть своя
            # частота, ниже экранной, и тогда номер кадра меняется
            # не каждый раз.
            got = self._frame_cache.get(id(frames))
            if got is not None and got[0] == idx:
                img = got[1]
            else:
                img = img.image()
                img.load()
                self._frame_cache[id(frames)] = (idx, img)
        if op < 0.998:
            img = img.copy()       # кадр общий, портить его нельзя
            img.putalpha(img.getchannel("A").point(lambda v: int(v * op)))
        canvas.alpha_composite(img, (int(layer.get("x", 0)) + ox,
                                     int(layer.get("y", 0)) + oy))

    @staticmethod
    def _scale_layer(layer, k):
        if k == 1:
            return layer
        out = dict(layer)
        # x2/y2 - конец линии и стрелки, r_inner - впадины звезды,
        # head - наконечник. Их забыли, и при сглаживании больше единицы
        # линии растягивались через весь экран, а звёзды выворачивались:
        # начало умножалось на k, а конец оставался как был.
        for key in ("x", "y", "x2", "y2", "w", "h", "r", "r_inner", "radius",
                    "thickness", "head", "size", "width", "outline_width"):
            if isinstance(out.get(key), (int, float)):
                out[key] = out[key] * k
        if isinstance(out.get("shadow"), dict):
            sh = dict(out["shadow"])
            for key in ("dx", "dy"):
                if isinstance(sh.get(key), (int, float)):
                    sh[key] = sh[key] * k
            out["shadow"] = sh
        return out


# --- запуск -----------------------------------------------------------------

def make_icon(size=64):
    """Значок программы: кольцо, похожее на индикаторы панели.

    Незакрытая дуга переливается из синего в зелёный - те же цвета, что
    у окна в ночном виде.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad, th = max(3, size // 11), max(3, size // 7)
    box = [pad, pad, size - pad, size - pad]
    d.arc(box, 135, 405, fill=(38, 52, 78, 255), width=th)
    # Перелив дуги: рисуем её короткими кусками, у каждого свой цвет.
    ot, do = 135, 315
    shagov = max(8, size // 3)
    sinij, zelenyj = (26, 127, 184), (51, 214, 166)
    for i in range(shagov):
        a = ot + (do - ot) * i / shagov
        b = ot + (do - ot) * (i + 1) / shagov + 1
        dolya = i / max(1, shagov - 1)
        cvet = tuple(int(round(s + (z - s) * dolya))
                     for s, z in zip(sinij, zelenyj))
        d.arc(box, a, b, fill=cvet + (255,), width=th)
    return img


def save_icon(path, sizes=(16, 24, 32, 48, 64, 128, 256)):
    """Записать значок в .ico - его просит ярлык Windows."""
    big = make_icon(256)
    big.save(path, format="ICO",
             sizes=[(s, s) for s in sizes])
    return path


class Runner:
    """Цикл вывода панели на экран. Умеет вставать на паузу и останавливаться."""

    def __init__(self, layout_path, cfg=None, base_dir=None, sensors=None):
        self.layout_path = layout_path
        self.cfg = cfg                # если задано, файл не читается
        self.base_dir = base_dir
        self.shared_sensors = sensors # общий сбор датчиков на всю программу
        self.cfg_off = True          # гасить подсветку при выходе
        self.day_mode = "auto"       # auto, night или day
        self.forced_mode = None      # режим, выбранный в меню
        self.panel = None
        self.stop = threading.Event()
        self.paused = False
        self.status = "запускается"
        self.sent = self.errors = 0
        self.fps_real = 0.0
        self.thread = None
        # Яркость меняют из окна, а команду экрану должен послать тот поток,
        # который держит порт. Поэтому просто оставляем здесь пожелание,
        # а цикл вывода его подхватывает.
        self._want_bright = None
        self._want_time = 0.0
        self.bright_now = None      # что реально ушло на экран
        self.bright_settle = 0.25   # сколько ждать, пока ползунок замрёт

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def apply_cfg(self, cfg, base_dir=None):
        """Подменить тему на ходу, не останавливая вывод."""
        self.cfg = cfg
        if base_dir:
            self.base_dir = base_dir
        try:
            p = Panel(self.layout_path, cfg=cfg, base_dir=self.base_dir)
            p.day_mode = self.day_mode
            self.panel = p
            return True
        except Exception as e:
            self.status = "тема с ошибкой: {}".format(str(e)[:50])
            return False

    def set_day_mode(self, mode):
        """Переключить тему прямо на ходу, без перезапуска."""
        self.day_mode = mode
        if self.panel is not None:
            self.panel.day_mode = mode

    def set_brightness(self, value):
        """Яркость подсветки, 0..100.

        Уходит на экран не сразу, а когда ползунок замрёт: смена яркости
        обрывает приём кадра, и экран на миг моргает. Пока значение
        меняется, ждём - тогда моргнёт один раз в конце, а не на каждый
        пиксель, пройденный мышью.
        """
        self._want_bright = max(0, min(100, int(value)))
        self._want_time = time.time()
        if self.panel is not None:
            self.panel.cfg.setdefault("screen", {})["brightness"] = \
                self._want_bright

    def _run(self):
        import txw818
        try:
            panel = Panel(self.layout_path, cfg=self.cfg, base_dir=self.base_dir)
        except Exception as e:
            self.status = "ошибка темы: {}".format(str(e)[:60])
            return
        own = self.shared_sensors is None
        s = self.shared_sensors or sensors_mod.Sensors()
        s.twilight_min = transition_minutes(panel.cfg)
        port = txw818.find_port()
        if not port:
            self.status = "экран не найден"
            if own:
                s.stop()
            return
        try:
            d = txw818.Display(port)
            d.connect()
            d.set_brightness(int(panel.cfg.get("screen", {}).get("brightness", 90)))
        except Exception as e:
            self.status = "порт занят: {}".format(str(e)[:50])
            if own:
                s.stop()
            return

        self.panel = panel
        self.day_mode = panel.day_mode
        if self.forced_mode:
            panel.day_mode = self.day_mode = self.forced_mode
        self.cfg_off = bool(panel.cfg.get("screen", {}).get("dark_on_exit", True))
        t_start = time.time()
        due = t_start         # срок ближайшего кадра
        win_t, win_n = t_start, 0     # окно для счёта настоящей частоты
        n = 0
        in_row = 0            # сбоев подряд, а не за всё время работы
        # Кадры фона разбираются на первом кадре, и на тяжёлой теме это
        # десятки секунд. Пока это идёт, экран пустой - надо сказать, что
        # происходит, а не писать «работает».
        self.status = "готовлю кадры фона"
        while not self.stop.is_set():
            t0 = time.time()
            if self.panel is not panel:
                panel = self.panel
            # Срок кадра считаем каждый раз: частоту можно поменять
            # в настройках прямо на ходу, и это должно быть видно сразу.
            period = 1.0 / panel.fps
            if not self.paused:
                try:
                    img = panel.render(s.read(), n, time.time() - t_start)
                    d.show_jpeg(txw818.to_jpeg(img, d.width, d.height, panel.quality))
                    self.sent += 1
                    n += 1
                    in_row = 0
                    if n == 1:
                        self.status = "работает"
                    # Яркость шлём сразу после кадра и не ждём ответа:
                    # так команда точно не влезет в середину передачи
                    # картинки, а чтение не отнимет время у следующего кадра.
                    if (self._want_bright is not None
                            and time.time() - self._want_time
                            >= self.bright_settle):
                        want, self._want_bright = self._want_bright, None
                        try:
                            # Во время потока кадров прошивка команду
                            # яркости пропускает мимо ушей: она всё ещё
                            # ждёт продолжения картинки. Ресинхронизация
                            # закрывает приём кадра, и команда доходит.
                            # Ответа не ждём, иначе встанет вывод.
                            d.resync(settle=0.004, clear=False)
                            d.set_brightness(want, wait=False)
                            self.bright_now = want
                        except Exception as e:
                            self.status = "яркость не прошла: {}".format(
                                str(e)[:40])
                except Exception:
                    self.errors += 1
                    in_row += 1
                    if in_row > 30:
                        self.status = "слишком много сбоев"
                        break
                # Считаем по последним двум секундам, а не за всё время
                # работы. Средним за час не увидишь, подействовала правка
                # или нет: оно ползёт к новому значению полчаса.
                win_n += 1
                el = time.time() - win_t
                if el >= 2.0:
                    self.fps_real = win_n / el
                    win_t, win_n = time.time(), 0
            # Ритм держим по расписанию, а не «поспать остаток»: у каждого
            # кадра свой срок, и отставание не копится.
            due += period
            now2 = time.time()
            # Опоздали на кадр-другой - следующий уходит сразу, без сна,
            # и ритм догоняется. Начинать счёт заново стоит, только когда
            # отстали безнадёжно.
            if now2 - due > 3 * period:
                due = now2 + period      # отстали безнадёжно - начинаем заново
            sleep = due - now2
            if sleep > 0:
                time.sleep(sleep)
        if own:
            s.stop()
        # Заставка прошивки включается сама, когда кадры перестают приходить.
        # Убрать её мы пока не можем, но можем погасить подсветку - тогда
        # вместо чужой анимации будет просто тёмный экран.
        if self.cfg_off:
            try:
                d.set_brightness(0)
                time.sleep(0.2)
            except Exception:
                pass
        d.close()
        self.status = "остановлена"


def run_tray(layout_path):
    """Запуск в фоне со значком возле часов."""
    try:
        import pystray
    except ImportError:
        print("Для значка в трее нужна библиотека pystray.")
        print("Выполни:  pip install pystray")
        return

    # Меню значка рисует pystray, а не tkinter, поэтому крючок перевода
    # из look.py сюда не дотягивается - переводим руками. Словарь берём
    # только здесь: движку он ни для чего больше не нужен.
    from yazyk import t
    try:
        import prefs
        import yazyk
        yazyk.vybrat(prefs.get("ui.lang", yazyk.RU))
    except Exception:
        pass

    box = {"runner": Runner(layout_path)}
    box["runner"].start()

    def cur():
        return box["runner"]

    def title(_=None):
        r = cur()
        return t("{} · {} — {} ({:.1f} кадр/с, тема {})").format(
            PROJECT, AUTHOR, t(r.status), r.fps_real,
            t(DAY_MODE_NAMES.get(r.day_mode, r.day_mode)))

    def toggle_pause(icon, item):
        r = cur()
        r.paused = not r.paused
        r.status = "на паузе" if r.paused else "работает"
        icon.update_menu()

    def set_mode(mode):
        def do(icon, item):
            cur().set_day_mode(mode)
            icon.update_menu()
        return do

    def checked(mode):
        return lambda item: cur().day_mode == mode

    def restart(icon, item):
        old_mode = cur().day_mode
        cur().stop.set()
        time.sleep(0.7)
        box["runner"] = Runner(layout_path)
        box["runner"].forced_mode = old_mode
        box["runner"].start()
        icon.update_menu()

    def quit_all(icon, item):
        cur().stop.set()
        time.sleep(0.5)
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem(title, None, enabled=False),
        pystray.Menu.SEPARATOR,
        # первую букву заглавной, остальные не трогаем: capitalize()
        # превратил бы «как в Windows» в «Как в windows»
        *[pystray.MenuItem(t(DAY_MODE_NAMES[m])[:1].upper()
                           + t(DAY_MODE_NAMES[m])[1:], set_mode(m),
                           checked=checked(m), radio=True) for m in DAY_MODES],
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(t("Пауза"), toggle_pause,
                         checked=lambda i: cur().paused),
        pystray.MenuItem(t("Перечитать тему"), restart),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(t("Выход"), quit_all),
    )
    icon = pystray.Icon("eone_screen", make_icon(), title(), menu)
    icon.run()


def main():
    args = sys.argv[1:]
    print("{} {}  ·  автор {}  ·  {}".format(
        PROJECT, VERSION, AUTHOR, LICENSE))

    if "--sensors" in args:
        s = sensors_mod.Sensors()
        print("\nИсточники данных:")
        print(s.describe())
        print("\nЖду 3 секунды...")
        time.sleep(3)
        print(s.describe())
        print("\nДоступные значения:")
        print(sensors_mod.ALL_KEYS)
        data = s.read()
        print("Сейчас:")
        for key in sorted(data):
            v = data[key]
            print("  {:20s} {}".format(
                key, "{:.2f}".format(v) if isinstance(v, float) else v))
        s.stop()
        return

    if "--tray" in args:
        rest = [a for a in args if not a.startswith("--")]
        run_tray(rest[0] if rest else DEFAULT_LAYOUT)
        return

    preview = "--preview" in args
    args = [a for a in args if not a.startswith("--")]
    layout_path = args[0] if args else DEFAULT_LAYOUT

    if not os.path.exists(layout_path):
        print("Не найден файл описания панели: {}".format(layout_path))
        return

    panel = Panel(layout_path)
    print("\nЧитаю компоновку из файла:")
    print("  {}".format(os.path.abspath(layout_path)))
    print("Панель {}x{}, {:g} кадр/с, качество {}, сглаживание x{}".format(
        panel.width, panel.height, panel.fps, panel.quality, panel.scale))

    names = []
    for l in panel.layers:
        n = l.get("name") or l.get("type", "?")
        if l.get("type") == "image":
            s = l.get("src", "")
            n += " [{}]".format(s if os.path.exists(panel.resolve(s))
                                else s + " — НЕ НАЙДЕН")
        names.append(n)
    print("Слоёв: {} — {}".format(len(names), ", ".join(names[:6])
                                  + (" ..." if len(names) > 6 else "")))

    s = sensors_mod.Sensors()
    s.twilight_min = transition_minutes(panel.cfg)
    print("\nИсточники данных:")
    print(s.describe())

    if preview:
        print("\nЖду 6 секунд, чтобы все датчики успели опроситься...")
        time.sleep(6)
        print("\nИсточники данных после опроса:")
        print(s.describe())
        img = panel.render(s.read(), 0)
        img.save("preview.png")
        print("\nСохранил preview.png — открой и посмотри, как будет выглядеть.")
        s.stop()
        return

    import txw818

    port = txw818.find_port()
    if port is None:
        print("\nНе нашёл экран. Проверь: python txw818.py --ports")
        s.stop()
        return
    print("\nЭкран на порту {}.".format(port))

    try:
        d = txw818.Display(port)
        info = d.connect()
    except Exception as e:
        print("Экран не ответил: {}".format(e))
        print("Закрой родную программу экрана, включая значок в трее.")
        s.stop()
        return
    dd = info.get("data", {})
    if dd.get("width"):
        print("Экран сообщает: {}x{}".format(dd["width"], dd["height"]))
    d.set_brightness(int(panel.cfg.get("screen", {}).get("brightness", 90)))

    period = 1.0 / panel.fps
    frame_no, sent, errors, bytes_sent = 0, 0, 0, 0
    t_start = time.time()
    t_report = t_start

    print("\nПанель запущена. Ctrl+C для выхода.\n")
    try:
        while True:
            t0 = time.time()
            img = panel.render(s.read(), frame_no, time.time() - t_start)
            jpeg = txw818.to_jpeg(img, d.width, d.height, panel.quality)
            try:
                d.show_jpeg(jpeg, begin=True)
                sent += 1
                bytes_sent += len(jpeg)
            except Exception as e:
                errors += 1
                print("  сбой отправки #{}: {}".format(errors, e))
                if errors >= 10:
                    print("  Слишком много сбоев, останавливаюсь.")
                    break
            frame_no += 1

            now = time.time()
            if now - t_report >= 10:
                dt = now - t_start
                print("  {:.0f} с: кадров {}, сбоев {}, {:.1f} кадр/с, "
                      "{:.0f} КБ/с, размер кадра {:.0f} КБ".format(
                          dt, sent, errors, sent / dt,
                          bytes_sent / dt / 1024, len(jpeg) / 1024))
                t_report = now

            sleep = period - (time.time() - t0)
            if sleep > 0:
                time.sleep(sleep)
            elif frame_no == 5:
                print("  Не успеваю за заданной частотой. Уменьши fps "
                      "или quality в layout.json.")
    except KeyboardInterrupt:
        pass

    dt = max(0.001, time.time() - t_start)
    print("\nОстановлено. Кадров {}, сбоев {}, средне {:.1f} кадр/с, {:.0f} КБ/с."
          .format(sent, errors, sent / dt, bytes_sent / dt / 1024))
    s.stop()
    if panel.cfg.get("screen", {}).get("dark_on_exit", True):
        try:
            d.set_brightness(0)
            time.sleep(0.2)
            print("Подсветка выключена, чтобы не показывалась заводская заставка.")
        except Exception:
            pass
    d.close()


if __name__ == "__main__":
    main()
