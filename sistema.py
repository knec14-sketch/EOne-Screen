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

ПРОВЕРЕНО НА WINDOWS. Linux-часть проверена на поддельных файлах /sys,
а 23.08.2026 её впервые прогнали на живой машине: CachyOS, KDE Plasma 6,
Wayland, Intel i5-13600KF и Radeon RX 7900 XT. Отчёт - в issue #1.
Там подтвердились температуры, имена железа, единицы по локали, окно
и сам экран; там же вылезли значок в трее и второй код устройства.
Что на живой машине ещё НЕ проверено: автозапуск после перезагрузки
и ярлык из меню приложений.
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


def _chislo(put):
    """Число из файла /sys. Нет файла или не число - None."""
    syroe = _prochest(put)
    if not syroe:
        return None
    try:
        return float(syroe.split()[0])
    except (ValueError, IndexError):
        return None


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


# --- что ещё отдаёт видеокарта -----------------------------------------------

# Драйвер amdgpu выкладывает загрузку и видеопамять прямо в папке
# устройства, а мощность и обороты - в hwmon внутри неё. Nvidia про это
# молчит: у неё есть nvidia-smi, и он отвечает подробнее.
def videokarta_pokazaniya(koren="/sys/class/drm"):
    """Загрузка, видеопамять, мощность и обороты видеокарты. Не Linux - None.

    Температуру сюда не кладём: она приходит из hwmon вместе с процессором,
    и читает её temperatury().

    koren задаётся, чтобы разбор можно было проверить на подложенных
    файлах, не имея Linux под рукой.
    """
    if not LINUX:
        return None
    itog = {}
    try:
        karty = sorted(d for d in os.listdir(koren)
                       if d.startswith("card") and d[4:].isdigit())
    except OSError:
        return itog
    for karta in karty:
        put = os.path.join(koren, karta, "device")

        zanyato = _chislo(os.path.join(put, "mem_info_vram_used"))
        vsego = _chislo(os.path.join(put, "mem_info_vram_total"))
        zagruzka = _chislo(os.path.join(put, "gpu_busy_percent"))

        vatty = chastota = oboroty = None
        hwmon = os.path.join(put, "hwmon")
        try:
            papki = sorted(os.listdir(hwmon))
        except OSError:
            papki = []
        for papka in papki:
            h = os.path.join(hwmon, papka)
            # power1_average есть не у всех: у части плат RDNA есть только
            # мгновенное power1_input. Берём то, что нашлось.
            mkvt = (_chislo(os.path.join(h, "power1_average"))
                    or _chislo(os.path.join(h, "power1_input")))
            if mkvt:
                vatty = mkvt / 1000000.0          # ядро отдаёт микроватты
            gc = _chislo(os.path.join(h, "freq1_input"))
            if gc:
                chastota = gc / 1000000.0         # и герцы
            ob = _chislo(os.path.join(h, "fan1_input"))
            if ob is not None:
                oboroty = ob

        nashli = {}
        if zagruzka is not None and 0 <= zagruzka <= 100:
            nashli["загрузка"] = zagruzka
        if zanyato is not None:
            nashli["память_занято_мб"] = zanyato / 1048576.0
        if vsego:
            nashli["память_всего_мб"] = vsego / 1048576.0
            if zanyato is not None:
                nashli["память_доля"] = 100.0 * zanyato / vsego
        if vatty is not None:
            nashli["мощность_вт"] = vatty
        if chastota is not None:
            nashli["частота_мгц"] = chastota
        if oboroty is not None:
            nashli["вентилятор"] = oboroty

        # На машине бывает две карты: встроенная и настоящая. Встроенная
        # обычно молчит про загрузку, поэтому берём ту, что ответила
        # содержательнее.
        if len(nashli) > len(itog):
            itog = nashli
    return itog


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


# --- значок возле часов ------------------------------------------------------

# На чём pystray рисует значок, решается один раз при его загрузке.
# Сам он пробует по порядку: appindicator, gtk, xorg - и до Xorg
# доходит, когда первых двух нет. А Xorg пишет заголовок окна в latin-1,
# и на первой же русской букве падает с UnicodeEncodeError.
#
# Мы вмешиваемся только в один случай: AppIndicator есть, но за ним
# в очереди стоит ещё и GTK со своим StatusIcon, который на Wayland
# давно не показывается. Тогда называем подложку прямо.
PODLOZHKI_TREYA = ("AppIndicator3", "AyatanaAppIndicator3")


def _est_appindicator():
    """Поднимется ли ветка AppIndicator у pystray.

    Спрашиваем ровно то же, что спрашивает он сам: gi, Gtk 3.0 и один
    из двух индикаторов. Проверять меньше нельзя - назовём подложку,
    которая не заведётся, и останемся вовсе без значка.
    """
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        __import__("gi.repository", fromlist=["Gtk"])
    except Exception:
        return False
    for imya in PODLOZHKI_TREYA:
        try:
            gi.require_version(imya, "0.1")
            __import__("gi.repository", fromlist=[imya])
            return True
        except Exception:
            continue
    return False


# Назвали ли подложку мы сами. Чужой выбор отменять нельзя: человек
# ставил его руками и, скорее всего, знает почему.
_NAZVALI_SAMI = False


def podgotovit_trey():
    """Выбрать, на чём рисовать значок. Возвращает выбранное или None.

    Звать ДО «import pystray»: после загрузки он уже не переспросит.
    Свой выбор человека не трогаем - он знает, что делает.
    """
    global _NAZVALI_SAMI
    _NAZVALI_SAMI = False
    if not LINUX:
        return None
    vybor = os.environ.get("PYSTRAY_BACKEND")
    if vybor:
        return vybor
    if _est_appindicator():
        os.environ["PYSTRAY_BACKEND"] = "appindicator"
        _NAZVALI_SAMI = True
        return "appindicator"
    return None


def otstupit_s_treya(nazvali=None):
    """Убрать нашу подложку, чтобы pystray выбирал сам.

    True - убрали, стоит попробовать ещё раз. False - отступать некуда:
    подложку назвали не мы, а человек, либо её и не называли вовсе.
    """
    global _NAZVALI_SAMI
    if not _NAZVALI_SAMI:
        return False
    os.environ.pop("PYSTRAY_BACKEND", None)
    _NAZVALI_SAMI = False
    return True


def podlozhka_treya(pystray):
    """На чём pystray рисует значок НА САМОМ ДЕЛЕ.

    Не по нашей переменной, а по тому, что у него вышло: он решает при
    загрузке и молча отступает на следующую ветку, если первая не встала.
    От ответа зависит, выдержит ли заголовок русские буквы.
    """
    imya = getattr(getattr(pystray, "Icon", None), "__module__", "") or ""
    return imya.rsplit(".", 1)[-1].lstrip("_")


# Xorg пишет заголовок в latin-1, поэтому для него кириллицу переводим
# в латинские буквы. Читать хуже, чем по-русски, но лучше, чем никак:
# без этого программа просто не запускалась.
_LATINICEY = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    "—": "-", "–": "-", "«": '"', "»": '"', "…": "...",
}


def bezopasnyy_zagolovok(stroka, podlozhka=None):
    """Заголовок, который переживёт подложку значка.

    podlozhka - что вернул podlozhka_treya(). Не сказали - считаем
    худшее и переводим в латиницу: лишний раз перевести не страшно,
    а не перевести - значит не запуститься.
    """
    if not LINUX or not stroka:
        return stroka
    if podlozhka in ("appindicator", "gtk"):
        return stroka
    try:
        stroka.encode("latin-1")
        return stroka                      # и так пройдёт
    except UnicodeEncodeError:
        pass
    kuski = []
    for bukva in stroka:
        zamena = _LATINICEY.get(bukva.lower())
        if zamena is None:
            kuski.append(bukva)
            continue
        kuski.append(zamena.upper() if bukva.isupper() else zamena)
    gotovo = "".join(kuski)
    # Что не легло в таблицу - выкидываем: заголовок важнее буквы.
    return gotovo.encode("latin-1", "replace").decode("latin-1")


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
    print("показания карты:    {}".format(videokarta_pokazaniya()))
    print("подложка значка:    {}".format(podgotovit_trey()))
    print("единицы системы:    {}".format(edinicy_sistemy()))
    print("тёмное оформление:  {}".format(temnoe_oformlenie()))
    print("нужна библиотека:   {}".format(nuzhna_biblioteka_datchikov()))
    print("ярлык лёг бы в:     {}".format(yarlyk_put()))
