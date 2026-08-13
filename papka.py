#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Где лежит программа и всё её хозяйство.
#  Часть проекта EOne screen — открытой замены штатной программе
#  для экранов на контроллере TXW818.
#
#  Автор: EOne
#  Лицензия: CC BY-NC-SA 4.0 — использование в коммерческих целях
#  запрещено без письменного разрешения автора. См. файл LICENSE.
#
"""papka.py - одна точка правды о том, где лежат файлы программы.

Раньше каждый модуль искал своё рядом с собой, через __file__, а темы -
в текущей папке. Пока программа запускается как набор .py, это одно
и то же место, и всё сходится. Но стоит собрать её в один exe, и оба
способа врут:

  * PyInstaller распаковывает себя во временную папку, и __file__
    показывает туда, а не туда, куда человек поставил программу;
  * текущая папка у ярлыка может быть какой угодно - хоть рабочий стол.

Поэтому спрашивать надо здесь.

    import papka
    papka.programma()            ->  C:\\EOne screen
    papka.ryadom("weather.json") ->  C:\\EOne screen\\weather.json

Если когда-нибудь программа станет ставиться в Program Files, куда писать
нельзя, здесь появится вторая функция - для хозяйского добра, - и менять
придётся только этот файл.
"""

import os
import sys

_gde = None


def programma():
    """Папка, где лежит программа. Считается один раз."""
    global _gde
    if _gde is None:
        if getattr(sys, "frozen", False):
            # собранный exe: рядом с ним, а не в распакованном временном
            _gde = os.path.dirname(os.path.abspath(sys.executable))
        else:
            _gde = os.path.dirname(os.path.abspath(__file__))
    return _gde


def ryadom(*chasti):
    """Путь к файлу рядом с программой."""
    return os.path.join(programma(), *chasti)


def sobrana():
    """Работаем из собранного exe, а не из исходников."""
    return bool(getattr(sys, "frozen", False))


if __name__ == "__main__":
    print("папка программы: {}".format(programma()))
    print("собрана в exe:   {}".format("да" if sobrana() else "нет"))
