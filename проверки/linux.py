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

print("\nитог: {}".format("всё сошлось" if not bedy
                          else "замечаний: {}".format(len(bedy))))
for b in bedy:
    print("   " + b)
print("\nЭто разбор данных, а не проверка на живой машине. Окно, экран "
      "на порту\nи значок в трее проверяются только на настоящем Linux.")
sys.exit(1 if bedy else 0)
