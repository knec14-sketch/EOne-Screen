#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Темы: описание, предпросмотр, обмен.
#  Часть проекта EOne screen.
#
#  Автор: EOne
#  Лицензия: CC BY-NC-SA 4.0 — использование в коммерческих целях
#  запрещено без письменного разрешения автора. См. файл LICENSE.
#
"""
themes.py - всё про темы, кроме их отрисовки.

Тема - это папка: описание в .json и рядом всё, на что оно ссылается.
Такую папку можно переслать целиком, и она заработает у другого человека.

    themes.find()               найти темы рядом с программой
    themes.info(path)           имя, автор, описание, что умеет
    themes.thumb(path)          картинка предпросмотра, с кэшем
    themes.export(path, zip)    упаковать для пересылки
    themes.import_zip(zip)      распаковать чужую

Раздел meta в описании темы держит то, что о ней хочет сказать автор.
Что тема умеет - не спрашиваем, а определяем по ней самой: так надпись
не разойдётся с делом.
"""

import json
import os
import shutil
import zipfile

from PIL import Image, ImageDraw, ImageFont

import panel as panel_mod
import yazyk
from yazyk import t

THUMB_NAME = ".preview.png"
THUMB_W = 480
SKIP_JSON = ("weather.json", "package.json", "settings.json")


def is_junk(name):
    """Не то, что стоит копировать вместе с темой и класть в архив.

    Предпросмотр соберётся заново, копии описания нужны только на этой
    машине, а служебные файлы с точки чужому человеку и подавно ни к чему.
    """
    return (name == THUMB_NAME or name.startswith(".")
            or ".bak-" in name or name.endswith((".bak", ".tmp")))

FONT_PLACES = [
    ".", "fonts",
    r"C:\Windows\Fonts",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"),
]

NEW_THEME = {
    "meta": {"name": "", "author": "", "description": ""},
    "screen": {"width": 960, "height": 480, "fps": 1, "quality": 85,
               "brightness": 90, "supersample": 2, "background": "#0a0d14",
               "day_mode": "auto"},
    "fonts": {"часы": {"file": "arialbd.ttf", "size": 96},
              "мелкий": {"file": "arial.ttf", "size": 22}},
    "layers": [
        {"type": "text", "name": "часы", "x": 480, "y": 200, "anchor": "mm",
         "text": "{now:%H:%M}", "font": "часы", "color": "#ffffff"},
        {"type": "text", "name": "дата", "x": 480, "y": 280, "anchor": "mm",
         "text": "{now:%d.%m.%Y}", "font": "мелкий", "color": "#8b94a3"},
        {"type": "text", "name": "процессор", "x": 480, "y": 350, "anchor": "mm",
         "text": "ЦП {cpu_load:.0f}%   ОЗУ {ram_load:.0f}%",
         "font": "мелкий", "color": "#4aa8ff"},
    ],
}


# --- поиск -------------------------------------------------------------------

def _own_json(folder):
    """Описание темы прямо в этой папке, если оно там есть."""
    try:
        names = sorted(os.listdir(folder))
    except Exception:
        return None
    # tema.json - имя по умолчанию у собранных тем, его и предпочитаем
    for f in sorted(names, key=lambda x: (x.lower() != "tema.json", x)):
        if f.startswith("."):
            continue          # .sobrano.json и прочая служебная мелочь
        if f.lower().endswith(".json") and f.lower() not in SKIP_JSON:
            return os.path.join(folder, f)
    return None


def find(root_dir=".", depth=2):
    """Темы рядом с программой: папки с описанием и отдельные файлы.

    Заглядываем и на этаж ниже: темы часто складывают в общую папку
    вроде «темы» или «theme», и каждая лежит в своей подпапке.
    """
    found = []
    try:
        names = sorted(os.listdir(root_dir))
    except Exception:
        return found
    for n in names:
        # служебные папки темами не бывают
        if n.startswith(".") or n == "__pycache__":
            continue
        p = os.path.join(root_dir, n)
        if os.path.isdir(p):
            # И своё описание, и то, что лежит этажом ниже. Если брать
            # только своё, то забытый .json в общей папке тем выдал бы её
            # за одну тему, а остальные пропали бы из витрины.
            own = _own_json(p)
            if own:
                found.append(own)
            if depth > 1:
                found.extend(find(p, depth - 1))
        elif n.lower().endswith(".json") and n.lower() not in SKIP_JSON:
            try:
                with open(p, encoding="utf-8") as fh:
                    if "layers" in json.load(fh):
                        found.append(p)
            except Exception:
                pass
    return found


def read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write(path, cfg):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# --- что тема из себя представляет -------------------------------------------

def umeet_den(cfg):
    """Есть ли у темы дневной вид, отличный от ночного.

    Спрашивает главная страница: тему в одном-единственном исполнении
    незачем спрашивать, день сейчас или ночь.
    """
    layers = (cfg or {}).get("layers", [])
    return bool(any(l.get("day") for l in layers)
                or (cfg or {}).get("screen", {}).get("background_day"))


def umeet_pogodu(cfg):
    """Меняется ли тема от погоды."""
    return _mentions((cfg or {}).get("layers", []), "weather") or \
        _mentions((cfg or {}).get("layers", []), "sky_") or \
        _mentions((cfg or {}).get("layers", []), "snow_")


def abilities(cfg):
    """Что тема умеет. Определяется по ней самой, а не со слов автора."""
    layers = cfg.get("layers", [])
    out = []
    if umeet_den(cfg):
        out.append(("День и ночь", "sunrise"))
    if any(l.get("type") == "image" and l.get("src") for l in layers):
        out.append(("Картинки", "grid"))
    if any(l.get("loop") or l.get("react") for l in layers):
        out.append(("Движение", "play"))
    if _mentions(layers, "weather"):
        out.append(("Погода", "water"))
    if _mentions(layers, "gpu_"):
        out.append(("Видео", "screen"))
    if _mentions(layers, "cpu_"):
        out.append(("Процессор", "chip"))
    return out


def _mentions(layers, needle):
    for l in layers:
        for v in l.values():
            if isinstance(v, str) and needle in v:
                return True
    return False


def _opisanie(meta):
    """Описание темы на языке темы.

    Описание пишет автор темы, а не мы, и в словарь программы оно
    не попадает. Тема вправе носить его на всех языках сразу:
    description, description_en, description_de и так далее.
    """
    yaz = yazyk.yazyk_temy()
    if yaz != yazyk.RU:
        gotovo = meta.get("description_" + yaz) or meta.get("description_en")
        if gotovo:
            return gotovo
    return meta.get("description", "")


def info(path):
    """Всё, что нужно карточке темы."""
    try:
        cfg = read(path)
    except Exception as e:
        return {"path": path, "name": os.path.basename(path),
                "broken": str(e)[:80], "abilities": [], "meta": {}}
    meta = cfg.get("meta") or {}
    folder = os.path.dirname(os.path.abspath(path))
    default_name = os.path.basename(folder) \
        if os.path.basename(path).lower() in ("tema.json", "layout.json") \
        else os.path.splitext(os.path.basename(path))[0]
    scr = cfg.get("screen", {})
    return {
        "path": path,
        "cfg": cfg,
        "meta": meta,
        "name": meta.get("name") or default_name,
        "author": meta.get("author", ""),
        # Описание пишет автор темы, а не мы, и в словарь программы оно
        # не попадает. Тема вправе носить его на двух языках рядом.
        "description": _opisanie(meta),
        "abilities": abilities(cfg),
        "layers": len(cfg.get("layers", [])),
        "size": "{}x{}".format(scr.get("width", 960), scr.get("height", 480)),
        "fps": scr.get("fps", 1),
        "broken": None,
    }


def set_meta(path, cfg, **fields):
    """Записать имя, автора или описание. Пустое поле убирается."""
    meta = cfg.setdefault("meta", {})
    for k, v in fields.items():
        if v:
            meta[k] = v
        else:
            meta.pop(k, None)
    if not meta:
        cfg.pop("meta", None)
    write(path, cfg)
    return cfg


# --- предпросмотр ------------------------------------------------------------

def thumb(path, width=THUMB_W, force=False):
    """Картинка темы. Держим рядом с ней, пересобираем при изменении."""
    folder = os.path.dirname(os.path.abspath(path))
    cache = os.path.join(folder, THUMB_NAME)
    try:
        if not force and os.path.exists(cache) \
                and os.path.getmtime(cache) >= os.path.getmtime(path):
            img = Image.open(cache)
            img.load()
            if img.width == width:
                return img
    except Exception:
        pass

    cfg = read(path)
    p = panel_mod.Panel(cfg=cfg, static=True, base_dir=folder)
    p.instant = True
    p.day_mode = str(cfg.get("screen", {}).get("day_mode", "night"))
    if p.day_mode == "auto":
        p.day_mode = "night"          # витрина показывает тему в покое
    img = p.render({}, 0, 0.0)
    h = max(1, int(round(img.height * width / img.width)))
    img = img.resize((width, h), Image.LANCZOS)
    try:
        img.save(cache)
    except Exception:
        pass
    return img


def showcase(path, out_path=None, width=1200):
    """Картинка темы для показа: ночь и день рядом, с подписью.

    Миниатюра в витрине маленькая и всегда ночная. А чтобы показать тему
    другим - выложить или прислать, - нужна нормальная картинка, по которой
    сразу видно и оба вида, и кто её сделал, и что она умеет.
    """
    folder = os.path.dirname(os.path.abspath(path))
    cfg = read(path)
    meta = info(path)

    shots = []
    for mode in ("night", "day"):
        p = panel_mod.Panel(cfg=cfg, static=True, base_dir=folder)
        p.instant = True
        p.day_mode = mode
        shots.append(p.render({}, 0, 0.0))

    pad, gap, bar = 28, 20, 132
    half = (width - pad * 2 - gap) // 2
    scale = half / float(shots[0].width)
    hh = int(round(shots[0].height * scale))
    height = pad + hh + bar

    card = Image.new("RGB", (width, height), (12, 14, 18))
    d = ImageDraw.Draw(card)
    for i, shot in enumerate(shots):
        small = shot.resize((half, hh), Image.LANCZOS)
        x = pad + i * (half + gap)
        card.paste(small, (x, pad))
        d.rectangle([x, pad, x + half - 1, pad + hh - 1], outline=(48, 54, 66))

    def font(size, bold=False):
        for name in (("seguisb.ttf", "segoeuib.ttf", "arialbd.ttf") if bold
                     else ("segoeui.ttf", "arial.ttf")):
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    y = pad + hh + 22
    d.text((pad, y), meta["name"], font=font(34, True), fill=(236, 240, 247))
    line = t("{} слоёв · {} · {:g} кадр/с").format(
        meta["layers"], meta["size"], float(meta["fps"] or 1))
    if meta["author"]:
        line = t("автор: {}   ·   {}").format(meta["author"], line)
    d.text((pad, y + 46), line, font=font(19), fill=(126, 137, 154))
    if meta["abilities"]:
        d.text((pad, y + 74), "   ·   ".join(a for a, _ in meta["abilities"]),
               font=font(19), fill=(74, 168, 255))

    d.text((width - pad, y + 4), t("ночь"), font=font(19), fill=(90, 98, 112),
           anchor="ra")
    d.text((width - pad, y + 32), t("и день"), font=font(19), fill=(90, 98, 112),
           anchor="ra")

    out_path = out_path or os.path.join(folder, "показ.png")
    card.save(out_path)
    return out_path


# --- создание, копирование, переименование -----------------------------------

HOME = "themes"


def home_dir(base="."):
    """Общая папка тем. Заводится сама, если её ещё нет."""
    out = os.path.join(base, HOME)
    if not os.path.isdir(out):
        os.makedirs(out, exist_ok=True)
    return out


def safe_name(name):
    """Имя, которое можно дать папке. Windows не любит \\ / : * ? \" < > |."""
    out = "".join(ch for ch in (name or "") if ch not in '\\/:*?"<>|')
    return out.strip().strip(".") or "тема"


def unique_dir(base, name, keep=None):
    """Свободное имя папки рядом с base.

    keep - папка, которую занятой не считаем: своё же имя при
    переименовании мешать не должно.
    """
    safe = safe_name(name)
    keep = os.path.abspath(keep) if keep else None
    out = os.path.join(base, safe)
    n = 2
    while os.path.exists(out) and os.path.abspath(out) != keep:
        out = os.path.join(base, "{} {}".format(safe, n))
        n += 1
    return out


def create(base=".", name="Моя тема", author=""):
    """Новая тема с часами и парой строк — чтобы было с чего начать.

    Кладётся в общую папку тем, а не рядом с программой: иначе новые темы
    расползаются по корню, и найти их потом можно только глазами.
    """
    folder = unique_dir(home_dir(base), name)
    os.makedirs(folder)
    cfg = json.loads(json.dumps(NEW_THEME))     # своя копия
    cfg["meta"]["name"] = name
    cfg["meta"]["author"] = author
    path = os.path.join(folder, "tema.json")
    write(path, cfg)
    return path


def _copy_tree(src, dst, progress=None):
    """Скопировать папку, отчитываясь о ходе дела.

    shutil.copytree копирует молча, а тема с кадрами весит сотни мегабайт:
    без полоски окно выглядит зависшим, и человек лезет копировать
    проводником. Поэтому идём по файлам сами.
    """
    files = []
    for root, dirs, names in os.walk(src):
        dirs[:] = [d for d in dirs if not is_junk(d)]
        for n in names:
            if is_junk(n):
                continue
            full = os.path.join(root, n)
            files.append((full, os.path.relpath(full, src)))
    for i, (full, rel) in enumerate(files):
        if progress:
            progress(i, len(files), rel)
        target = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(target) or dst, exist_ok=True)
        shutil.copy2(full, target)
    return len(files)


def duplicate(path, new_name=None, progress=None):
    """Копия темы целиком, вместе с кадрами и шрифтами."""
    src = os.path.dirname(os.path.abspath(path))
    parent = os.path.dirname(src)
    nice = (new_name or "").strip() or (info(path)["name"] + " — копия")
    dst = unique_dir(parent, nice)
    os.makedirs(dst)
    _copy_tree(src, dst, progress)
    out = os.path.join(dst, os.path.basename(path))
    if os.path.exists(out):
        cfg = read(out)
        cfg.setdefault("meta", {})["name"] = nice
        write(out, cfg)
    return out


def rename(path, new_name):
    """Переименовать тему: и подпись внутри, и саму папку.

    Одного meta мало: в витрине имя поменяется, а папка на диске останется
    со старым, и найти тему через проводник станет труднее. Папка следует
    за именем.

    Возвращает новый путь к описанию - он мог измениться.
    """
    nice = (new_name or "").strip()
    if not nice:
        raise ValueError("имя не может быть пустым")
    path = os.path.abspath(path)
    folder = os.path.dirname(path)

    cfg = read(path)
    cfg.setdefault("meta", {})["name"] = nice
    write(path, cfg)

    # Собранная тема - это папка, и переименовывать надо её. А описание,
    # лежащее отдельным файлом, само себе имя: тогда переименовываем файл.
    if os.path.basename(path).lower() in ("tema.json", "layout.json"):
        target = unique_dir(os.path.dirname(folder), nice, keep=folder)
        if os.path.abspath(target) == folder:
            return path
        # предпросмотр пересоберётся сам: он привязан ко времени правки
        try:
            os.remove(os.path.join(folder, THUMB_NAME))
        except OSError:
            pass
        os.rename(folder, target)
        return os.path.join(target, os.path.basename(path))

    target = os.path.join(folder, safe_name(nice) + ".json")
    n = 2
    while os.path.exists(target) and os.path.abspath(target) != path:
        target = os.path.join(folder, "{} {}.json".format(safe_name(nice), n))
        n += 1
    if os.path.abspath(target) != path:
        os.rename(path, target)
    return target


def remove(path, to_trash=True):
    """Убрать тему. По умолчанию не насовсем, а с глаз долой.

    Папки, чьё имя начинается с точки, движок пропускает и в витрину они
    не попадают. Значит тему видно не будет, а вернуть её можно одним
    переименованием в проводнике - это куда добрее, чем стереть сотни
    мегабайт без спроса.
    """
    folder = os.path.dirname(os.path.abspath(path))
    if not to_trash:
        shutil.rmtree(folder)
        return None
    parent = os.path.dirname(folder)
    dst = os.path.join(parent, "." + os.path.basename(folder))
    n = 2
    while os.path.exists(dst):
        dst = os.path.join(parent, ".{} {}".format(os.path.basename(folder), n))
        n += 1
    os.rename(folder, dst)
    return dst


# --- обмен -------------------------------------------------------------------

def collect(path, dest_dir, progress=None):
    """Собрать всё, на что ссылается тема, в отдельную папку.

    Нужно, когда описание лежит само по себе, а кадры и шрифты разбросаны
    рядом с программой. После сборки папку можно переслать как есть.
    """
    base = os.path.dirname(os.path.abspath(path)) or "."
    cfg = read(path)
    os.makedirs(dest_dir, exist_ok=True)

    plan, missing = [], []
    for l in cfg.get("layers", []):
        s = l.get("src")
        if l.get("type") != "image" or not s:
            continue
        p = s if os.path.exists(s) else os.path.join(base, s)
        if not os.path.exists(p):
            missing.append(s)
            continue
        name = os.path.basename(os.path.normpath(p))
        plan.append((p, name))
        l["src"] = name

    wanted = {l["font"] for l in cfg.get("layers", []) if l.get("font")}
    wanted |= {f["file"] for f in (cfg.get("fonts") or {}).values()
               if f.get("file")}
    for name in sorted(wanted):
        if not name.lower().endswith((".ttf", ".otf", ".ttc")):
            continue
        for d in [base, os.path.join(base, "fonts")] + FONT_PLACES:
            p = os.path.join(d, name)
            if os.path.isfile(p):
                plan.append((p, os.path.join("fonts", os.path.basename(p))))
                break
        else:
            missing.append(name + " (шрифт)")

    for i, (src, rel) in enumerate(plan):
        if progress:
            progress(i, len(plan), os.path.basename(rel))
        target = os.path.join(dest_dir, rel)
        os.makedirs(os.path.dirname(target) or dest_dir, exist_ok=True)
        if os.path.isdir(src):
            if os.path.exists(target):
                shutil.rmtree(target)
            shutil.copytree(src, target)
        else:
            shutil.copy2(src, target)

    write(os.path.join(dest_dir, "tema.json"), cfg)
    return missing


def is_selfcontained(path):
    """Лежит ли уже всё нужное рядом с описанием."""
    base = os.path.dirname(os.path.abspath(path))
    try:
        cfg = read(path)
    except Exception:
        return False
    for l in cfg.get("layers", []):
        if l.get("type") == "image" and l.get("src"):
            if not os.path.exists(os.path.join(base, l["src"])):
                return False
    return True


def export(path, zip_path, progress=None):
    """Упаковать тему в один файл для пересылки."""
    import tempfile
    base = os.path.dirname(os.path.abspath(path))
    tmp = None
    try:
        if not is_selfcontained(path):
            tmp = tempfile.mkdtemp(prefix="tema-")
            collect(path, tmp, progress)
            base = tmp
        files = []
        for root, dirs, names in os.walk(base):
            dirs[:] = [d for d in dirs if not is_junk(d)]
            for n in names:
                if is_junk(n):
                    continue
                full = os.path.join(root, n)
                files.append((full, os.path.relpath(full, base)))
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED,
                             compresslevel=6) as z:
            for i, (full, rel) in enumerate(files):
                if progress:
                    progress(i, len(files), rel)
                z.write(full, rel)
        return len(files)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def import_zip(zip_path, base=".", progress=None):
    """Распаковать присланную тему рядом с программой."""
    name = os.path.splitext(os.path.basename(zip_path))[0]
    folder = unique_dir(base, name)
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        for i, n in enumerate(names):
            if progress:
                progress(i, len(names), n)
            z.extract(n, folder)
    # описание могло оказаться в подпапке - поднимем содержимое наверх
    inside = [n for n in os.listdir(folder)]
    if len(inside) == 1 and os.path.isdir(os.path.join(folder, inside[0])):
        deep = os.path.join(folder, inside[0])
        for n in os.listdir(deep):
            shutil.move(os.path.join(deep, n), os.path.join(folder, n))
        os.rmdir(deep)
    for n in sorted(os.listdir(folder)):
        if n.lower().endswith(".json") and n.lower() not in SKIP_JSON:
            return os.path.join(folder, n)
    raise ValueError("в архиве нет описания темы")
