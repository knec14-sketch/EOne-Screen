#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Настройки самой программы.
#  Часть проекта EOne screen.
#
#  Автор: EOne
#  Лицензия: CC BY-NC-SA 4.0 — использование в коммерческих целях
#  запрещено без письменного разрешения автора. См. файл LICENSE.
#
"""
prefs.py - настройки программы, а не темы.

Тема описывает, что показано на экране водянки. Здесь всё остальное:
каким должно быть само окно, какие датчики опрашивать, что делать при
запуске. Хранится в settings.json рядом с программой.

    import prefs
    prefs.get("ui.theme")            ->  "system"
    prefs.set("ui.theme", "light")   записывает и сохраняет
"""

import json
import os
import threading

FILE = "settings.json"

DEFAULTS = {
    "ui": {
        # оформление окна: system - как в Windows, screen - как у панели
        # на экране водянки, dark и light - принудительно
        "theme": "system",
        "font_scale": 1.0,
    },
    "start": {
        "last_theme": "",          # что открыть при следующем запуске
        "minimized": False,        # сразу свернуться в трей
        "screen_on": False,        # сразу начать вывод на экран
        "close_to_tray": True,     # крестик прячет, а не закрывает
        "autostart": False,        # запускаться вместе с Windows
        "desktop_shortcut": False,  # ярлык на рабочем столе
        "osmotr_byl": False,       # осмотр машины уже показывали
    },
    # Во сколько потоков собирать кадр. 1 - в один, 0 - решить самому
    # по числу ядер. Это про машину, а не про тему: одна и та же тема
    # на ноутбуке и на шестнадцати ядрах может идти по-разному.
    "speed": {
        "threads": 1,
    },
    # В чём показывать числа. Действует и в окне, и на экране водянки.
    "units": {
        "temp": "c",           # c - Цельсий, f - Фаренгейт
        "wind": "kmh",         # kmh, ms или mph
        "clock": "24",         # 24 - обычные часы, 12 - с AM и PM
        "date": "dmy",         # порядок чисел: dmy, mdy, ymd
        "week_start": "mon",   # с какого дня начинается неделя: mon, sun
    },
    # Какие источники опрашивать и как часто. Выключенный источник
    # не опрашивается вообще - это и есть экономия.
    "sensors": {
        "system":  {"on": True, "every": 1.0},   # ЦП, память, диски, сеть
        "gpu":     {"on": True, "every": 1.0},   # nvidia-smi
        "temps":   {"on": True, "every": 1.0},   # температуры через LHM
        "weather": {"on": True, "every": 15.0},  # погода и время восхода
    },
}

_lock = threading.Lock()
_data = None
_path = None


def path():
    global _path
    if _path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        _path = os.path.join(here, FILE)
    return _path


def _merge(base, over):
    """Значения из файла поверх значений по умолчанию, вглубь."""
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def all():
    """Все настройки целиком. Читаются один раз за запуск."""
    global _data
    with _lock:
        if _data is None:
            saved = {}
            try:
                with open(path(), encoding="utf-8") as f:
                    saved = json.load(f)
            except Exception:
                saved = {}
            _data = _merge(DEFAULTS, saved)
        return _data


def get(where, default=None):
    """Значение по пути через точку: get("ui.theme")."""
    node = all()
    for part in str(where).split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def set(where, value, save_now=True):
    """Записать значение по пути через точку и сразу сохранить."""
    node = all()
    parts = str(where).split(".")
    with _lock:
        for part in parts[:-1]:
            nxt = node.get(part)
            if not isinstance(nxt, dict):
                nxt = {}
                node[part] = nxt
            node = nxt
        if node.get(parts[-1]) == value:
            return value          # ничего не изменилось, файл не трогаем
        node[parts[-1]] = value
    if save_now:
        save()
    return value


def save():
    """Записать настройки на диск. Ошибку записи молча переживаем:
    без настроек программа работает, просто с обычными значениями."""
    with _lock:
        snapshot = json.dumps(_data or DEFAULTS, ensure_ascii=False, indent=2)
    try:
        tmp = path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(snapshot)
        os.replace(tmp, path())
        return True
    except Exception:
        return False


# --- запуск вместе с Windows -------------------------------------------------

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "EOne screen"


def autostart_state():
    """Прописана ли программа в автозапуск. None - выяснить не удалось."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, RUN_NAME)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return None


def set_autostart(on, command=None):
    """Прописать или убрать запуск вместе с Windows.

    Запускаем через app.bat, чтобы он сам поднял права: без них
    не читается температура процессора.
    """
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
            if on:
                if command is None:
                    here = os.path.dirname(os.path.abspath(__file__))
                    bat = os.path.join(here, "app.bat")
                    command = '"{}"'.format(bat if os.path.exists(bat)
                                            else os.path.join(here, "app.py"))
                winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(k, RUN_NAME)
                except FileNotFoundError:
                    pass
        set("start.autostart", bool(on))
        return True
    except Exception:
        return False


# --- ярлык на рабочем столе --------------------------------------------------

YARLYK = "EOne screen.lnk"


def _rabochiy_stol():
    """Где у этого человека рабочий стол.

    Спрашиваем Windows, а не складываем путь из имени пользователя:
    папку можно перенести куда угодно, в том числе в OneDrive, и тогда
    сложенный путь ведёт в пустоту.
    """
    try:
        import ctypes
        import ctypes.wintypes as wt
        buf = ctypes.create_unicode_buffer(wt.MAX_PATH)
        # 0 - рабочий стол текущего пользователя
        if ctypes.windll.shell32.SHGetFolderPathW(None, 0, None, 0, buf) == 0:
            return buf.value
    except Exception:
        pass
    return os.path.join(os.path.expanduser("~"), "Desktop")


def yarlyk_put():
    return os.path.join(_rabochiy_stol(), YARLYK)


def yarlyk_est():
    return os.path.exists(yarlyk_put())


def set_yarlyk(on, icon=None):
    """Создать или убрать ярлык на рабочем столе.

    Ярлык ведёт на app.bat, а не на app.py: батник поднимает права,
    без которых не читается температура процессора.

    Сам ярлык делает WScript.Shell через powershell - так не нужна
    ни одна лишняя библиотека.
    """
    put = yarlyk_put()
    if not on:
        try:
            if os.path.exists(put):
                os.remove(put)
            set("start.desktop_shortcut", False)
            return True
        except Exception:
            return False
    here = os.path.dirname(os.path.abspath(__file__))
    cel = os.path.join(here, "app.bat")
    if not os.path.exists(cel):
        cel = os.path.join(here, "app.py")
    stroki = [
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut({!r})"
        .format(put).replace("'", '"'),
        '$s.TargetPath = "{}"'.format(cel),
        '$s.WorkingDirectory = "{}"'.format(here),
        '$s.Description = "EOne screen"',
    ]
    if icon and os.path.exists(icon):
        stroki.append('$s.IconLocation = "{},0"'.format(icon))
    stroki.append("$s.Save()")
    try:
        import subprocess
        got = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "; ".join(stroki)],
            capture_output=True, timeout=20,
            creationflags=0x08000000)      # без чёрного окошка
        ok = got.returncode == 0 and os.path.exists(put)
        set("start.desktop_shortcut", bool(ok))
        return ok
    except Exception:
        return False


if __name__ == "__main__":
    print("Файл настроек: {}".format(path()))
    print("Есть на диске: {}".format(os.path.exists(path())))
    print(json.dumps(all(), ensure_ascii=False, indent=2))
    print("\nАвтозапуск: {}".format(
        {True: "включён", False: "выключен", None: "неизвестно"}[
            autostart_state()]))
