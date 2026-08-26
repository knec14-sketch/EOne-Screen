#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Разбор того, что отдаёт Linux, — на подложенных файлах.

Linux-машины у автора нет, поэтому проверяем единственное, что можно
проверить без неё: правильно ли программа читает то, что выкладывает
ядро. Файлы /sys и /proc — обычные текстовые, их легко подделать, и на
подделке видно, верно ли выбран датчик из десятка.

Чего эта проверка НЕ говорит: заведётся ли окно, найдётся ли экран
на /dev/ttyACM*, лягут ли значки. Это покажет только живая машина.

    python проверки/linux.py
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sistema

bedy = []


def sverit(chto, bylo, nado):
    if bylo != nado:
        bedy.append("{}: вышло {!r}, надо {!r}".format(chto, bylo, nado))
        print("  {:52s} ПЛОХО — {!r}".format(chto, bylo))
    else:
        print("  {:52s} хорошо".format(chto))


def hwmon(*datchiki):
    """Подделать /sys/class/hwmon так, как его выкладывает ядро."""
    koren = tempfile.mkdtemp(prefix="hwmon-")
    for nomer, (imya, temps) in enumerate(datchiki):
        p = os.path.join(koren, "hwmon{}".format(nomer))
        os.makedirs(p)
        with open(os.path.join(p, "name"), "w") as f:
            f.write(imya + "\n")
        for n, (podpis, gradusy) in enumerate(temps, 1):
            # ядро отдаёт тысячные доли градуса
            with open(os.path.join(p, "temp{}_input".format(n)), "w") as f:
                f.write(str(int(gradusy * 1000)) + "\n")
            if podpis:
                with open(os.path.join(p, "temp{}_label".format(n)), "w") as f:
                    f.write(podpis + "\n")
    return koren


print("=== температуры из /sys/class/hwmon ===")
# Притворяемся Linux целиком: одного признака мало, иначе программа
# считает, что мы на Linux и на Windows разом, и отвечает вразнобой.
sistema.LINUX, sistema.WINDOWS = True, False

koren = hwmon(("k10temp", [("Tctl", 61.5), ("Tccd1", 48.2)]),
              ("amdgpu", [("edge", 52.0), ("junction", 64.0)]),
              ("nvme", [("Composite", 39.0)]))
sverit("Ryzen: берётся Tctl, а не отдельный кристалл",
       sistema.temperatury(koren).get("процессор"), 61.5)
sverit("Radeon: берётся edge, а не junction",
       sistema.temperatury(koren).get("видеокарта"), 52.0)
sverit("диск не считается ни процессором, ни видеокартой",
       sorted(sistema.temperatury(koren)), ["видеокарта", "процессор"])
shutil.rmtree(koren, ignore_errors=True)

koren = hwmon(("coretemp", [("Package id 0", 54.0), ("Core 0", 49.0),
                            ("Core 1", 61.0)]),
              ("acpitz", [(None, 27.8)]))
sverit("Intel: берётся Package, а не самое горячее ядро",
       sistema.temperatury(koren).get("процессор"), 54.0)
shutil.rmtree(koren, ignore_errors=True)

koren = hwmon(("k10temp", [(None, 55.0), (None, 61.0)]))
sverit("без подписей берётся самое горячее",
       sistema.temperatury(koren).get("процессор"), 61.0)
shutil.rmtree(koren, ignore_errors=True)

koren = hwmon(("k10temp", [("Tctl", 999.0)]))
sverit("явная чепуха отбрасывается", sistema.temperatury(koren), {})
shutil.rmtree(koren, ignore_errors=True)

sverit("нет папки hwmon — пусто, а не падение",
       sistema.temperatury("/такого/пути/нет"), {})


print("\n=== видеокарта из /sys/class/drm ===")


def drm(*karty):
    """Подделать /sys/class/drm так, как его выкладывает драйвер.

    Каждая карта — (номер, {файл: содержимое}, {файл в hwmon: содержимое}).
    """
    koren = tempfile.mkdtemp(prefix="drm-")
    for nomer, svoi, hwmon_svoi in karty:
        put = os.path.join(koren, "card{}".format(nomer), "device")
        os.makedirs(put)
        for imya, chto in svoi.items():
            with open(os.path.join(put, imya), "w") as f:
                f.write(str(chto) + "\n")
        if hwmon_svoi is not None:
            h = os.path.join(put, "hwmon", "hwmon3")
            os.makedirs(h)
            for imya, chto in hwmon_svoi.items():
                with open(os.path.join(h, imya), "w") as f:
                    f.write(str(chto) + "\n")
    return koren


# Radeon RX 7900 XT: 20 ГБ видеопамяти, из них занято 4 ГБ
koren = drm((1, {"gpu_busy_percent": 37,
                 "mem_info_vram_used": 4 * 1073741824,
                 "mem_info_vram_total": 20 * 1073741824},
             {"power1_average": 132000000,      # микроватты
              "freq1_input": 2100000000,        # герцы
              "fan1_input": 1450}))
got = sistema.videokarta_pokazaniya(koren)
sverit("загрузка берётся как есть", got.get("загрузка"), 37.0)
sverit("видеопамять переводится в мегабайты",
       got.get("память_занято_мб"), 4096.0)
sverit("вся видеопамять переводится в мегабайты",
       got.get("память_всего_мб"), 20480.0)
sverit("доля занятой видеопамяти считается", got.get("память_доля"), 20.0)
sverit("микроватты переводятся в ватты", got.get("мощность_вт"), 132.0)
sverit("герцы переводятся в мегагерцы", got.get("частота_мгц"), 2100.0)
sverit("обороты вентилятора берутся как есть", got.get("вентилятор"), 1450.0)
sverit("температуры здесь нет — она приходит из hwmon",
       [k for k in got if "температ" in k], [])
shutil.rmtree(koren, ignore_errors=True)

# У части плат RDNA есть только мгновенное значение
koren = drm((0, {"gpu_busy_percent": 5}, {"power1_input": 24000000}))
sverit("нет power1_average — берётся power1_input",
       sistema.videokarta_pokazaniya(koren).get("мощность_вт"), 24.0)
shutil.rmtree(koren, ignore_errors=True)

# Встроенная карта молчит, настоящая отвечает: берём ту, что содержательнее
koren = drm((0, {}, None),
            (1, {"gpu_busy_percent": 61,
                 "mem_info_vram_used": 1073741824,
                 "mem_info_vram_total": 8 * 1073741824}, None))
sverit("из двух карт берётся та, что ответила",
       sistema.videokarta_pokazaniya(koren).get("загрузка"), 61.0)
shutil.rmtree(koren, ignore_errors=True)

# Драйвер отдаёт чепуху — лучше промолчать, чем показать 300 %
koren = drm((0, {"gpu_busy_percent": 300}, None))
sverit("невозможная загрузка отбрасывается",
       sistema.videokarta_pokazaniya(koren), {})
shutil.rmtree(koren, ignore_errors=True)

# Пустая папка устройства: у Intel и старых Radeon этих файлов нет вовсе
koren = drm((0, {}, None))
sverit("нечего читать — пусто, а не падение",
       sistema.videokarta_pokazaniya(koren), {})
shutil.rmtree(koren, ignore_errors=True)

sverit("нет папки drm — пусто, а не падение",
       sistema.videokarta_pokazaniya("/такого/пути/нет"), {})


print("\n=== заголовок значка возле часов ===")
# Xorg пишет заголовок в latin-1: на этом падал весь запуск
sverit("русский заголовок переживает latin-1",
       sistema.bezopasnyy_zagolovok("EOne screen — экран выключен", "xorg")
       .encode("latin-1", "strict").decode("latin-1"),
       "EOne screen - ekran vyklyuchen")
sverit("длинное тире заменяется",
       "—" in sistema.bezopasnyy_zagolovok("EOne screen — работа", "xorg"),
       False)
sverit("латиница не трогается",
       sistema.bezopasnyy_zagolovok("EOne screen off", "xorg"),
       "EOne screen off")
sverit("AppIndicator получает заголовок как есть",
       sistema.bezopasnyy_zagolovok("EOne screen — экран выключен",
                                    "appindicator"),
       "EOne screen — экран выключен")
sverit("не знаем подложки — переводим на всякий случай",
       "экран" in sistema.bezopasnyy_zagolovok("EOne screen — экран", None),
       False)

bylo_podlozhki = os.environ.get("PYSTRAY_BACKEND")
os.environ["PYSTRAY_BACKEND"] = "appindicator"
sverit("выбор человека не перебивается", sistema.podgotovit_trey(),
       "appindicator")
if bylo_podlozhki is None:
    os.environ.pop("PYSTRAY_BACKEND", None)
else:
    os.environ["PYSTRAY_BACKEND"] = bylo_podlozhki


class PystrayДляВида:
    class Icon:
        pass


PystrayДляВида.Icon.__module__ = "pystray._xorg"
sverit("подложку спрашиваем у самого pystray",
       sistema.podlozhka_treya(PystrayДляВида), "xorg")
PystrayДляВида.Icon.__module__ = "pystray._appindicator"
sverit("и узнаём AppIndicator",
       sistema.podlozhka_treya(PystrayДляВида), "appindicator")


print("\n=== код устройства ===")


class ПортДляВида:
    def __init__(self, vid, pid):
        self.vid, self.pid = vid, pid


import txw818                                              # noqa: E402

sverit("наша помпа Flow 360 узнаётся",
       txw818.nash_li(ПортДляВида(0x33C3, 0x7788)), True)
sverit("родственная Flow 240 тоже узнаётся",
       txw818.nash_li(ПортДляВида(0x33C3, 0x7792)), True)
sverit("чужое устройство не берётся",
       txw818.nash_li(ПортДляВида(0x33C3, 0x1234)), False)
sverit("чужой производитель не берётся",
       txw818.nash_li(ПортДляВида(0x1A86, 0x7788)), False)


print("\n=== единицы по локали ===")
bylo_lang = os.environ.get("LANG")
for lokal, klyuch, nado in (("ru_RU.UTF-8", "temp", "c"),
                            ("en_US.UTF-8", "temp", "f"),
                            ("en_US.UTF-8", "wind", "mph"),
                            ("en_US.UTF-8", "date", "mdy"),
                            ("en_GB.UTF-8", "temp", "c"),
                            ("en_GB.UTF-8", "clock", "12"),
                            ("de_DE.UTF-8", "clock", "24")):
    os.environ["LANG"] = lokal
    os.environ.pop("LC_MEASUREMENT", None)
    os.environ.pop("LC_ALL", None)
    sverit("{}: {}".format(lokal, klyuch),
           sistema.edinicy_sistemy().get(klyuch), nado)
if bylo_lang is None:
    os.environ.pop("LANG", None)
else:
    os.environ["LANG"] = bylo_lang

print("\n=== ярлык .desktop ===")
dom = tempfile.mkdtemp(prefix="dom-")
os.environ["XDG_DATA_HOME"] = dom
os.environ["XDG_CONFIG_HOME"] = dom
sverit("ярлык создался", sistema.sdelat_yarlyk(True, "/opt/eone/app.py",
                                               "/opt/eone/icon.png"), True)
put = sistema.yarlyk_put()
tekst = open(put, encoding="utf-8").read()
sverit("в ярлыке правильная команда",
       "Exec=/opt/eone/app.py" in tekst, True)
sverit("в ярлыке есть значок", "Icon=/opt/eone/icon.png" in tekst, True)
sverit("тип записи задан", tekst.startswith("[Desktop Entry]"), True)
sverit("автозапуск ложится в свою папку",
       "autostart" in (sistema.yarlyk_put(avtozapusk=True) or ""), True)
sverit("ярлык убирается", sistema.sdelat_yarlyk(False, ""), True)
sverit("после уборки файла нет", os.path.exists(put), False)
shutil.rmtree(dom, ignore_errors=True)

print("\n=== чего на Linux нет вовсе ===")
sverit("библиотека датчиков не нужна",
       sistema.nuzhna_biblioteka_datchikov(), False)
sverit("пометки «из интернета» не бывает",
       sistema.pometka_iz_interneta(__file__), False)


print("\n=== короткое имя видеокарты из lspci ===")
# lspci отвечает длинно и для машины. На панели такое упирается в край.
for syroe, nado in (
        ("Advanced Micro Devices, Inc. [AMD/ATI] Navi 31 "
         "[Radeon RX 7900 XT/7900 XTX/7900 GRE/7900M] (rev cc)",
         "Radeon RX 7900 XT"),
        ("NVIDIA Corporation GA104 [GeForce RTX 3070] (rev a1)",
         "GeForce RTX 3070"),
        ("Intel Corporation AlderLake-S GT1 [UHD Graphics 730] (rev 0c)",
         "UHD Graphics 730"),
        ("Intel Corporation UHD Graphics 620 (rev 02)",
         "UHD Graphics 620"),
        # Кроме кодового имени кристалла ничего не сказано - берём его,
        # но без канцелярии производителя и без обрезков скобок
        ("Advanced Micro Devices, Inc. [AMD/ATI] Raphael (rev c9)",
         "Raphael"),
        ("", "")):
    sverit(syroe[:44] or "пустая строка",
           sistema.korotko_o_karte(syroe), nado)


print("\n=== показания карты ложатся в ключи панели ===")
# Разбор проверен выше. Здесь другое: те ли имена получит панель.
# Ошибиться тут легко и незаметно - панель просто покажет прочерк.
import sensors as sensors_mod                               # noqa: E402

bylo_chtenie = sistema.videokarta_pokazaniya
sistema.videokarta_pokazaniya = lambda *a, **k: {
    "загрузка": 37.0, "память_занято_мб": 4096.0,
    "память_всего_мб": 20480.0, "память_доля": 20.0,
    "мощность_вт": 132.0, "частота_мгц": 2100.0, "вентилятор": 1450.0}
s = sensors_mod.Sensors.__new__(sensors_mod.Sensors)
s.gpu_source = None
legli = s._karta_linux()
sverit("загрузка", legli.get("gpu_load"), 37.0)
sverit("видеопамять занято, ГБ", legli.get("gpu_mem_used_gb"), 4.0)
sverit("видеопамять всего, ГБ", legli.get("gpu_mem_total_gb"), 20.0)
sverit("доля видеопамяти", legli.get("gpu_mem_load"), 20.0)
sverit("мощность", legli.get("gpu_power_w"), 132.0)
sverit("частота", legli.get("gpu_mhz"), 2100.0)
sverit("вентилятор", legli.get("gpu_fan"), 1450.0)
sverit("источник показаний назван", s.gpu_source, "ядро Linux (drm)")
sverit("все ключи известны панели",
       sorted(k for k in legli if k not in sensors_mod.Sensors.GPU_KEYS),
       ["gpu_mem_total_gb", "gpu_mem_used_gb"])   # эти две считает панель

sistema.videokarta_pokazaniya = lambda *a, **k: {}
s.gpu_source = None
sverit("нечего читать — ничего и не кладём", s._karta_linux(), {})
sistema.videokarta_pokazaniya = bylo_chtenie


print("\n=== осмотр машины не просит лишнего ===")
import osmotr                                              # noqa: E402

osmotr.IS_WINDOWS = False
sverit("прав администратора не требует",
       [n.horosho for n in osmotr.prava()[0]], [None])
sverit("библиотеку датчиков не требует",
       [n.horosho for n in osmotr.dll()[0]], [None])
sverit("pythonnet в список не попадает",
       any(n.chto == "pythonnet" for n in osmotr.biblioteki()[0]), False)
sverit("про app.bat не поминает",
       any("bat" in (n.chinit or "") for n in osmotr.prava()[0]), False)

print("\nитог: {}".format("всё сошлось" if not bedy
                          else "замечаний: {}".format(len(bedy))))
for b in bedy:
    print("   " + b)
print("\nЭто разбор данных, а не проверка на живой машине. Окно, экран "
      "на порту\nи значок в трее проверяются только на настоящем Linux.")
sys.exit(1 if bedy else 0)
