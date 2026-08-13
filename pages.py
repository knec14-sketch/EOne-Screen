#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Страницы окна: темы, настройки, датчики.
#  Часть проекта EOne screen.
#
#  Автор: EOne
#  Лицензия: CC BY-NC-SA 4.0 — использование в коммерческих целях
#  запрещено без письменного разрешения автора. См. файл LICENSE.
#
"""
pages.py - страницы, кроме главной и редактора.

Настройки собраны здесь целиком и намеренно подробно: главная страница
от этого стала пустой, а сюда заходят разбираться, и объяснения тут
уместны.
"""

import os
import threading
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk

import edinicy
import look as L
import panel as panel_mod
import prefs
import sensors as sensors_mod
import themes as themes_mod
import yazyk
from yazyk import t

THUMB_W = 360

# Юридическую силу имеет только полный текст на сайте Creative Commons;
# файл LICENSE рядом с программой - пересказ для человека.
#
# И файл, и ссылка - на языке окна: читать условия на чужом языке
# человек не обязан, а у Creative Commons есть и то, и другое.
LICENSE_URL = {
    "ru": "https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.ru",
    "en": "https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode",
}
LICENSE_FILE = {"ru": "LICENSE", "en": "LICENSE.en"}


class ThemesPage(ttk.Frame):
    """Работа с темами: слева выбор занятия, справа витрина."""

    SECTIONS = [
        ("my", "Мои темы", "grid"),
        ("create", "Создать тему", "add"),
        ("edit", "Редактор", "layers"),
    ]

    def __init__(self, parent, look, app):
        super().__init__(parent, style="TFrame", padding=(22, 18))
        self.look = look
        self.app = app
        self.thumbs = {}
        self.mode = "my"

        self.sub = L.Banner(self, look, "Темы")
        self.sub.pack(fill="x", pady=(0, 14))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        self.side = L.SideList(body, look, self.SECTIONS, value="my",
                               command=self.pick_job, width=300)
        self.side.pack(side="left", fill="y", padx=(0, 18))

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        self.tools = ttk.Frame(right)
        self.tools.pack(fill="x", pady=(0, 10))

        # витрина прокручивается: тем может быть много
        self.wrap = ttk.Frame(right)
        self.canvas = tk.Canvas(self.wrap, highlightthickness=0, bd=0,
                                bg=look.c["bg"])
        bar = ttk.Scrollbar(self.wrap, orient="vertical",
                            command=self.canvas.yview)
        self.strip = ttk.Frame(self.canvas)
        self.strip.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.strip, anchor="nw")
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", self._wheel, add="+")
        look.on_change(lambda lk: self.canvas.configure(bg=lk.c["bg"]))
        self.loaded = False
        self.pick_job("my", first=True)

    def pick_job(self, key, first=False):
        """Нажали блок слева: справа разворачивается нужное."""
        if key == "create" and not first:
            self.side.set(self.mode)      # блок не залипает: это действие
            self.create()
            return
        if key == "edit" and not first:
            self.side.set(self.mode)
            self.app.show_page("editor")
            return
        self.mode = "my"
        self.side.set("my")
        self.sub.set_subtitle(
            "Всё, что лежит рядом с программой. Отсюда тему отправляют "
            "на экран, правят, копируют и упаковывают для пересылки.")
        for w in self.tools.winfo_children():
            w.destroy()
        for text, icon, cmd in (
                ("Обновить", "refresh", self.refresh),
                ("Из папки…", "folder", self.open_folder),
                ("Из архива…", "import", self.import_zip)):
            ttk.Button(self.tools, text=self.look.icon(icon) + "  " + t(text),
                       style="Quiet.TButton", command=cmd).pack(side="right",
                                                                padx=(6, 0))
        self.wrap.pack(fill="both", expand=True)
        self.refresh()

    def _wheel(self, e):
        if self.winfo_ismapped():
            self.canvas.yview_scroll(-int(e.delta / 120), "units")

    def show(self):
        self.refresh()

    def tick(self):
        pass

    def refresh(self):
        for w in self.strip.winfo_children():
            w.destroy()
        cur = os.path.abspath(self.app.editor.path)
        row = None
        for i, path in enumerate(themes_mod.find(".")):
            if i % 3 == 0:
                row = ttk.Frame(self.strip)
                row.pack(fill="x", pady=(0, 14), anchor="w")
            try:
                self._card(row, themes_mod.info(path),
                           os.path.abspath(path) == cur)
            except Exception as e:
                ttk.Label(row, text="{}: {}".format(os.path.basename(path), e),
                          style="Bad.TLabel").pack(side="left")

    def _card(self, row, info, current):
        lk = self.look
        path = info["path"]
        # Ширина с запасом от картинки: под ней стоят подписи умений
        # и ряд кнопок, а по-английски они заметно длиннее русских.
        # Обводка цветом накала: по карточке щёлкают, и это должно быть
        # видно до того, как человек попробует.
        card = L.Card(row, lk, radius=14, padding=12, width=THUMB_W + 76,
                      stroke="accent")
        card.pack(side="left", padx=(0, 14), anchor="n")
        b = card.body

        # Картинка тоже кнопка - щелчок по ней отправляет тему на экран.
        # Обводим, иначе об этом никто не догадается.
        holder = tk.Label(b, bd=0, highlightthickness=2,
                          highlightbackground=lk.c["accent"],
                          highlightcolor=lk.c["accent"],
                          bg=lk.c["raised"], cursor="hand2")
        holder.pack()
        try:
            img = themes_mod.thumb(path, THUMB_W)
            photo = ImageTk.PhotoImage(img)
            self.thumbs[path] = photo          # ссылку надо держать
            holder.configure(image=photo, width=img.width, height=img.height)
        except Exception:
            holder.configure(text="нет предпросмотра", fg=lk.c["faint"],
                             width=THUMB_W // 7, height=6)
        holder.bind("<Button-1>", lambda e, p=path: self.app.load_theme(p))

        line = ttk.Frame(b, style="Card.TFrame")
        line.pack(fill="x", pady=(10, 0))
        ttk.Label(line, text=info["name"], style="Card.Sub.TLabel").pack(
            side="left")
        if current:
            ttk.Label(line, text="открыта", style="Card.Ok.TLabel").pack(
                side="right")

        under = t("{} слоёв · {} · {:g} кадр/с").format(
            info["layers"], info["size"], float(info["fps"] or 1))
        if info["author"]:
            under = t("автор: {}   ·   {}").format(info["author"], under)
        ttk.Label(b, text=under, style="Card.Faint.TLabel").pack(anchor="w")
        if info["description"]:
            ttk.Label(b, text=info["description"], style="Card.Faint.TLabel",
                      wraplength=THUMB_W).pack(anchor="w", pady=(4, 0))

        # значки умений раскладываем по три в ряд, иначе последний
        # вылезает за край карточки
        marks = None
        for n, (label, icon) in enumerate(info["abilities"]):
            if n % 3 == 0:
                marks = ttk.Frame(b, style="Card.TFrame")
                marks.pack(fill="x", pady=(8 if n == 0 else 4, 0))
            chip = ttk.Frame(marks, style="Card.TFrame")
            chip.pack(side="left", padx=(0, 12))
            L.icon_label(chip, lk, icon, 11).pack(side="left")
            ttk.Label(chip, text=" " + t(label),
                      style="Card.Faint.TLabel").pack(side="left")

        btns = ttk.Frame(b, style="Card.TFrame")
        btns.pack(fill="x", pady=(10, 0))
        ttk.Button(btns, text="На экран",
                   style="Quiet.TButton" if current else "Accent.TButton",
                   command=lambda p=path: self.app.load_theme(p)).pack(
            side="left")
        self.app.tip.add(
            btns.winfo_children()[-1],
            "Сделать эту тему текущей: она уйдёт на экран водянки "
            "и откроется на главной.")
        ttk.Button(btns, text=lk.icon("edit") + "  " + t("Изменить"),
                   style="Quiet.TButton",
                   command=lambda p=path: self.open_in_editor(p)).pack(
            side="left", padx=6)
        self.app.tip.add(btns.winfo_children()[-1],
                         "Открыть тему в редакторе: слои, надписи, цвета, "
                         "дневной и ночной вид.")
        ttk.Button(btns, text="Переименовать", style="Quiet.TButton",
                   command=lambda p=path: self.rename(p)).pack(side="left")
        self.app.tip.add(btns.winfo_children()[-1],
                         "Сменить название темы. Папка на диске получит "
                         "то же имя — тема и папка ходят вместе.")
        # Значки - своей строкой. В одной с надписями они не помещались
        # и молча выдавливались за край карточки: по-английски подписи
        # длиннее, и первым пропадал ряд из пяти кнопок.
        znachki = ttk.Frame(b, style="Card.TFrame")
        znachki.pack(fill="x", pady=(6, 0))
        for icon, tip, cmd in (
                ("about", "Название, автор и пояснение к теме. Эти строки "
                          "уедут вместе с ней к другому человеку. Название "
                          "меняет и имя папки на диске.",
                 lambda p=path: self.edit_meta(p)),
                ("copy", "Копия темы целиком, вместе с кадрами и шрифтами. "
                         "Спросит имя. Оригинал не пострадает.",
                 lambda p=path: self.duplicate(p)),
                ("export", "Упаковать тему в один файл, чтобы переслать. "
                           "Всё, на что она ссылается, попадёт внутрь.",
                 lambda p=path: self.export(p)),
                ("show", "Картинка для показа: ночь и день рядом, с именем, "
                         "автором и списком умений. Чтобы выложить или "
                         "прислать.",
                 lambda p=path: self.showcase(p)),
                ("delete", "Убрать тему из витрины. Папка остаётся на диске "
                          "и переименовывается с точки — вернуть можно "
                          "в проводнике.",
                 lambda p=path: self.remove(p))):
            btn = ttk.Button(znachki, text=lk.icon(icon), style="Icon.TButton",
                             command=cmd, width=3)
            btn.pack(side="right", padx=(4, 0))
            self.app.tip.add(btn, tip)

    # --- действия ---------------------------------------------------------

    def create(self):
        name = _ask(self, self.look, "Новая тема", "Как её назвать?", "Моя тема")
        if not name:
            return
        try:
            path = themes_mod.create(".", name, prefs.get("ui.author", ""))
        except Exception as e:
            messagebox.showerror("Темы", str(e))
            return
        self.refresh()
        self.open_in_editor(path)
        return path

    def rename(self, path):
        """Сменить название темы вместе с именем её папки."""
        info = themes_mod.info(path)
        name = _ask(self, self.look, "Переименовать тему",
                    "Новое название:", info["name"], verb="Переименовать")
        if not name or name == info["name"]:
            return
        try:
            new_path = themes_mod.rename(path, name)
        except Exception as e:
            messagebox.showerror("Переименовать тему", str(e))
            return
        self._follow(path, new_path)
        self.refresh()

    def edit_meta(self, path):
        """Название, автор и пояснение. Название тянет за собой и папку."""
        try:
            info = themes_mod.info(path)
        except Exception as e:
            messagebox.showerror("Описание темы", str(e))
            return
        dlg = MetaDialog(self, self.look, info)
        self.wait_window(dlg)
        if dlg.result is None:
            return
        was = info["name"]
        try:
            cfg = themes_mod.read(path)
            themes_mod.set_meta(path, cfg,
                                author=dlg.result["author"],
                                description=dlg.result["description"])
            new_name = dlg.result["name"]
            if new_name and new_name != was:
                path = themes_mod.rename(path, new_name)
                self._follow(info["path"], path)
        except Exception as e:
            messagebox.showerror("Описание темы", str(e))
        self.refresh()

    def _follow(self, old_path, new_path):
        """Тема переехала: догнать её везде, где она была записана."""
        if os.path.abspath(old_path) == os.path.abspath(self.app.editor.path):
            self.app.editor.path = new_path
            if self.app.running():
                self.app.runner.base_dir = self.app.theme_dir()
        if os.path.abspath(prefs.get("start.last_theme", "") or "") \
                == os.path.abspath(old_path):
            prefs.set("start.last_theme", os.path.abspath(new_path))

    def remove(self, path):
        info = themes_mod.info(path)
        if os.path.abspath(path) == os.path.abspath(self.app.editor.path):
            messagebox.showwarning(
                "Убрать тему",
                "Эта тема сейчас открыта. Откройте другую и попробуйте снова.")
            return
        if not messagebox.askyesno(
                "Убрать тему",
                "Убрать «{}» из витрины?\n\nПапка останется на диске — она "
                "просто получит точку в начале имени. Вернуть можно "
                "переименованием в проводнике.".format(info["name"])):
            return
        try:
            themes_mod.remove(path)
        except Exception as e:
            messagebox.showerror("Убрать тему", str(e))
            return
        self.refresh()

    def export(self, path):
        """Упаковать тему в архив для пересылки."""
        info = themes_mod.info(path)
        dst = filedialog.asksaveasfilename(
            title="Куда упаковать тему", defaultextension=".zip",
            initialfile=themes_mod.safe_name(info["name"]) + ".zip",
            filetypes=[("Архив с темой", "*.zip")])
        if not dst:
            return
        done = self._long("Упаковываю тему",
                          lambda step: themes_mod.export(path, dst, step))
        if done is None:
            return
        if messagebox.askyesno("Упаковать тему",
                               "Готово, файлов внутри: {}.\n{}\n\n"
                               "Показать в папке?".format(done, dst)):
            try:
                os.startfile(os.path.dirname(dst))
            except Exception:
                pass

    def _long(self, title, work):
        """Долгая работа с полоской: копирование, упаковка, распаковка.

        Тема с кадрами весит сотни мегабайт. Без полоски окно выглядит
        зависшим, и человек идёт делать то же самое проводником.
        """
        prog = Progress(self, self.look, title)
        out = {}

        def run():
            try:
                out["v"] = work(prog.step)
            except Exception as e:
                out["err"] = e
            self.after(0, prog.close)

        threading.Thread(target=run, daemon=True).start()
        self.wait_window(prog)
        if "err" in out:
            messagebox.showerror(title, str(out["err"]))
            return None
        return out.get("v")

    def open_in_editor(self, path):
        """Взять тему в работу: открыть её и сразу перейти к правке."""
        if os.path.abspath(path) != os.path.abspath(self.app.editor.path):
            if not self.app.load_theme(path):
                return
        self.app.show_page("editor")

    def duplicate(self, path):
        info = themes_mod.info(path)
        name = _ask(self, self.look, "Копия темы", "Как назвать копию?",
                    info["name"] + " — копия", verb="Скопировать")
        if not name:
            return
        new = self._long(
            "Копирую тему",
            lambda step: themes_mod.duplicate(path, name, step))
        if new is None:
            return
        self.refresh()
        if messagebox.askyesno("Копия темы",
                               "Готово:\n{}\n\nОткрыть копию?".format(
                                   os.path.dirname(os.path.abspath(new)))):
            self.app.load_theme(new)

    def showcase(self, path):
        """Собрать картинку темы для показа и предложить открыть."""
        try:
            out = themes_mod.showcase(path)
        except Exception as e:
            messagebox.showerror("Картинка для показа", str(e))
            return
        if messagebox.askyesno(
                "Картинка для показа",
                "Готово:\n{}\n\nОткрыть её?".format(out)):
            try:
                os.startfile(out)
            except Exception:
                pass

    def import_zip(self):
        src = filedialog.askopenfilename(title="Архив с темой",
                                         filetypes=[("Архив с темой", "*.zip")])
        if not src:
            return
        got = self._long("Распаковываю тему",
                         lambda step: themes_mod.import_zip(
                             src, themes_mod.home_dir("."), step))
        if got is None:
            return
        self.refresh()
        if messagebox.askyesno("Открыть архив", "Тема добавлена. Открыть её?"):
            self.app.load_theme(got)

    def open_folder(self):
        folder = filedialog.askdirectory(title="Папка с темой")
        if not folder:
            return
        found = themes_mod._own_json(folder)
        if not found:
            messagebox.showwarning("Темы", "В папке нет описания темы.")
            return
        self.app.load_theme(found)


# --- маленькие окошки --------------------------------------------------------

class MetaDialog(tk.Toplevel):
    """Имя, автор и описание темы — то, что увидят другие."""

    def __init__(self, parent, look, info):
        super().__init__(parent)
        self.result = None
        self.title("Описание темы")
        self.configure(bg=look.c["bg"])
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        body = ttk.Frame(self, padding=18)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Что увидят другие", style="Title.TLabel").pack(
            anchor="w")
        ttk.Label(body, text="эти строки уедут вместе с темой",
                  style="Faint.TLabel").pack(anchor="w", pady=(0, 12))
        self.vars = {}
        for key, label in (("name", "Название"), ("author", "Автор")):
            ttk.Label(body, text=label, style="Dim.TLabel").pack(anchor="w")
            var = tk.StringVar(value=info.get(key, "") or "")
            ttk.Entry(body, textvariable=var, width=46).pack(anchor="w",
                                                             pady=(0, 8))
            self.vars[key] = var
        ttk.Label(body, text="Описание", style="Dim.TLabel").pack(anchor="w")
        self.text = tk.Text(body, width=46, height=5, relief="flat", bd=0,
                            highlightthickness=1, wrap="word",
                            bg=look.c["raised"], fg=look.c["text"],
                            insertbackground=look.c["text"],
                            highlightbackground=look.c["border"],
                            font=look.font("body"))
        self.text.insert("1.0", info.get("description", "") or "")
        self.text.pack(anchor="w", pady=(0, 12))
        row = ttk.Frame(body)
        row.pack(fill="x")
        ttk.Button(row, text="Сохранить", style="Accent.TButton",
                   command=self.ok).pack(side="right")
        ttk.Button(row, text="Отмена", command=self.destroy).pack(side="right",
                                                                  padx=6)
        self.grab_set()

    def ok(self):
        self.result = {k: v.get().strip() for k, v in self.vars.items()}
        self.result["description"] = self.text.get("1.0", "end").strip()
        self.destroy()


class Progress(tk.Toplevel):
    """Полоска на время долгой работы: упаковки или распаковки."""

    def __init__(self, parent, look, title):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=look.c["bg"])
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        body = ttk.Frame(self, padding=18)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=title, style="Sub.TLabel").pack(anchor="w")
        self.what = ttk.Label(body, text="", style="Faint.TLabel", width=52)
        self.what.pack(anchor="w", pady=(4, 8))
        self.bar = ttk.Progressbar(body, length=380, maximum=100)
        self.bar.pack()
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.grab_set()

    def step(self, i, total, what=""):
        """Зовётся из рабочего потока, поэтому через after."""
        def show():
            try:
                self.bar["value"] = 100.0 * (i + 1) / max(1, total)
                self.what.configure(text=t("{} из {}   {}").format(
                    i + 1, total, os.path.basename(str(what))[:40]))
            except Exception:
                pass
        try:
            self.after(0, show)
        except Exception:
            pass

    def close(self):
        try:
            self.grab_release()
            self.destroy()
        except Exception:
            pass


def _ask(parent, look, title, question, default="", verb="Создать"):
    """Обычный вопрос со строкой ввода, но в нашем оформлении."""
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.configure(bg=look.c["bg"])
    dlg.transient(parent.winfo_toplevel())
    dlg.resizable(False, False)
    body = ttk.Frame(dlg, padding=18)
    body.pack(fill="both", expand=True)
    ttk.Label(body, text=question, style="Sub.TLabel").pack(anchor="w")
    var = tk.StringVar(value=default)
    entry = ttk.Entry(body, textvariable=var, width=38)
    entry.pack(anchor="w", pady=10)
    entry.focus_set()
    entry.select_range(0, "end")
    out = {}

    def ok(_=None):
        out["v"] = var.get().strip()
        dlg.destroy()

    row = ttk.Frame(body)
    row.pack(fill="x")
    ttk.Button(row, text=verb, style="Accent.TButton",
               command=ok).pack(side="right")
    ttk.Button(row, text="Отмена", command=dlg.destroy).pack(side="right",
                                                             padx=6)
    entry.bind("<Return>", ok)
    dlg.grab_set()
    parent.wait_window(dlg)
    return out.get("v")


class SettingsPage(ttk.Frame):
    """Слева разделы, справа их содержимое.

    Всё сразу не вываливается: заходят обычно за чем-то одним, и проще
    выбрать раздел, чем искать нужное поле в длинной простыне.
    """

    SECTIONS = [
        ("osmotr", "Осмотр машины", "ok"),
        ("look", "Оформление программы", "windows"),
        ("units", "Единицы и время", "thermo"),
        ("start", "Запуск", "power"),
        ("sensors", "Датчики", "sensors"),
        ("weather", "Погода и адрес", "water"),
        ("speed", "Производительность", "sliders"),
        ("about", "О программе", "about"),
    ]

    def __init__(self, parent, look, app):
        super().__init__(parent, style="TFrame", padding=(22, 18))
        self.look = look
        self.app = app
        self.sub = L.Banner(self, look, "Настройки")
        self.sub.pack(fill="x", pady=(0, 14))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        self.side = L.SideList(body, look, self.SECTIONS, value="look",
                               command=self.show_section, width=300)
        self.side.pack(side="left", fill="y", padx=(0, 18))

        # Содержимое прокручивается: разделы бывают длиннее окна, а на
        # маленьком окне без прокрутки нижние строчки просто пропадали.
        obertka = ttk.Frame(body)
        obertka.pack(side="left", fill="both", expand=True)
        self.polotno = tk.Canvas(obertka, highlightthickness=0, bd=0,
                                 bg=look.c["bg"])
        polosa = ttk.Scrollbar(obertka, orient="vertical",
                               command=self.polotno.yview)
        self.area = ttk.Frame(self.polotno)
        self._okno = self.polotno.create_window((0, 0), window=self.area,
                                                anchor="nw")
        self.area.bind("<Configure>", self._pod_soderzhimoe)
        self.polotno.bind("<Configure>", self._po_shirine)
        self.polotno.configure(yscrollcommand=polosa.set)
        self.polotno.pack(side="left", fill="both", expand=True)
        polosa.pack(side="right", fill="y")
        self.polosa = polosa
        self._polosa_vidna = True
        # add="+", иначе колесо перехватит одна страница на всю программу
        self.polotno.bind_all("<MouseWheel>", self._koleso, add="+")
        look.on_change(lambda lk: self.polotno.configure(bg=lk.c["bg"]))
        self.show_section("look")

    def _pod_soderzhimoe(self, _e=None):
        """Полоса прокрутки знает, сколько содержимого под ней.

        Показана она или нет - помним сами. Спрашивать winfo_ismapped
        нельзя: у скрытого окна он равен нулю у всего подряд, и полоса
        не появлялась бы вовсе.
        """
        self.polotno.configure(scrollregion=self.polotno.bbox("all"))
        # Полосу прячем, когда всё и так помещается: она только мешает.
        nado = self.area.winfo_reqheight() > self.polotno.winfo_height() + 2
        if nado and not self._polosa_vidna:
            self.polosa.pack(side="right", fill="y")
            self._polosa_vidna = True
        elif not nado and self._polosa_vidna:
            self.polosa.pack_forget()
            self._polosa_vidna = False

    def _po_shirine(self, e):
        """Содержимое во всю ширину полотна, а не по своей мерке."""
        self.polotno.itemconfigure(self._okno, width=e.width)
        self._pod_soderzhimoe()

    def _koleso(self, e):
        if self.winfo_ismapped() and self._polosa_vidna:
            self.polotno.yview_scroll(-int(e.delta / 120), "units")

    def show(self):
        pass

    def tick(self):
        if getattr(self, "current", None) == "sensors":
            self._live()
        elif getattr(self, "current", None) == "speed":
            self._show_real()

    def show_section(self, key):
        self.current = key
        for w in self.area.winfo_children():
            w.destroy()
        # Новый раздел - прокрутка сначала: остаться на середине прошлого
        # было бы странно.
        try:
            self.polotno.yview_moveto(0)
        except Exception:
            pass
        hints = {
            "osmotr": "что на этой машине есть, что отвечает и чего "
                      "не хватает",
            "look": "как выглядит само окно программы, а не картинка на экране",
            "units": "в чём показывать градусы, время и дату — и в окне, "
                     "и на экране",
            "start": "что делать при включении компьютера и при закрытии окна",
            "sensors": "откуда берутся значения и что из этого читается сейчас",
            "speed": "чем платим за плавность: памятью, процессором, качеством",
            "weather": "откуда брать прогноз, восход и закат",
            "about": "кто это написал и на каких условиях этим можно "
                     "пользоваться",
        }
        self.sub.set_subtitle(hints.get(key, ""))
        {"osmotr": self._osmotr, "look": self._look, "units": self._units,
         "start": self._start, "sensors": self._sensors,
         "weather": self._weather, "speed": self._speed,
         "about": self._about}[key](self.area)
        # Считаем высоту после того, как раскладка закончится: в момент
        # сборки виджеты ещё не знают своего размера, и полоса прокрутки
        # решала бы, что всё помещается.
        self.after_idle(self._pod_soderzhimoe)
        self.after(80, self._pod_soderzhimoe)

    # --- разделы ---------------------------------------------------------

    def _look(self, parent):
        lk = self.look
        card = L.Card(parent, lk, padding=18)
        card.pack(fill="x")
        b = card.body
        ttk.Label(b, text="Светлое или тёмное",
                  style="Card.Sub.TLabel").pack(anchor="w")
        ttk.Label(b, text="«Как в Windows» следит за оформлением системы, "
                          "«Как на экране» — за тем, день сейчас на панели "
                          "или ночь.",
                  style="Card.Faint.TLabel", wraplength=620,
                  justify="left").pack(anchor="w", pady=(2, 12))
        seg = L.Segmented(b, lk, [("system", "Как в Windows", "windows"),
                                  ("screen", "Как на экране", "screen"),
                                  ("light", "Светлое", "sun"),
                                  ("dark", "Тёмное", "moon")],
                          value=prefs.get("ui.theme", "system"),
                          command=self._set_ui_theme)
        seg.pack(anchor="w")

        card = L.Card(parent, lk, padding=18)
        card.pack(fill="x", pady=(14, 0))
        b = card.body
        ttk.Label(b, text="Язык", style="Card.Sub.TLabel").pack(anchor="w")
        L.Segmented(b, lk, [(code, name, "about")
                            for code, name in yazyk.YAZYKI],
                    value=prefs.get("ui.lang", yazyk.RU),
                    command=self._set_lang).pack(anchor="w", pady=(10, 0))
        self.lang_lbl = ttk.Label(b, text="", style="Card.Faint.TLabel")
        self.lang_lbl.pack(anchor="w", pady=(8, 0))

    def _set_lang(self, value):
        prefs.set("ui.lang", value)
        yazyk.vybrat(value)
        self.lang_lbl.configure(
            text="Изменения применятся при следующем запуске.")

    def _set_ui_theme(self, value):
        prefs.set("ui.theme", value)
        self.look.set_mode(value)

    def _osmotr(self, parent):
        """Осмотр машины прямо в окне.

        Раньше это был отдельный запуск start.bat перед программой.
        Отдельный обряд перед делом люди пропускают, а потом удивляются
        прочеркам вместо температуры - поэтому те же проверки живут
        здесь, и рядом с каждой бедой стоит то, чем её починить.
        """
        lk = self.look
        card = L.Card(parent, lk, padding=18)
        card.pack(fill="x")
        b = card.body
        ttk.Label(b, text="Что на этой машине",
                  style="Card.Sub.TLabel").pack(anchor="w")
        ttk.Label(b, text="те же проверки, что делает start.bat перед первым "
                          "запуском. Опрос датчиков занимает несколько "
                          "секунд.",
                  style="Card.Faint.TLabel", wraplength=620,
                  justify="left").pack(anchor="w", pady=(0, 10))
        ryad = ttk.Frame(b, style="Card.TFrame")
        ryad.pack(fill="x")
        self.osm_btn = ttk.Button(ryad, text="Осмотреть", style="Accent.TButton",
                                  command=self._osmotr_pusk)
        self.osm_btn.pack(side="left")
        self.osm_state = ttk.Label(ryad, text="", style="Card.Faint.TLabel")
        self.osm_state.pack(side="left", padx=(12, 0))

        self.osm_mesto = ttk.Frame(b, style="Card.TFrame")
        self.osm_mesto.pack(fill="x", pady=(12, 0))
        if getattr(self, "osm_nahodki", None):
            self._osmotr_pokazat(self.osm_nahodki)
        else:
            ttk.Label(self.osm_mesto,
                      text="Осмотр ещё не делался.",
                      style="Card.Faint.TLabel").pack(anchor="w")

    def _osmotr_pusk(self):
        """Пройти проверки в отдельном потоке, чтобы окно не замирало.

        Поток только складывает результат, а забирает его главный поток
        сам, по времени. Звать after из чужого потока нельзя: Tk заводит
        обработчик в своём цикле и на это ругается.
        """
        self.osm_btn.state(["disabled"])
        self.osm_state.configure(text=t("  смотрю…"))
        self._osm_gotovo = None
        self.after(400, self._osmotr_zhdat)
        self.update_idletasks()

        def rabota():
            import osmotr
            razdely = []
            try:
                razdely.append(("Библиотеки", osmotr.biblioteki()[0]))
                razdely.append(("Права", osmotr.prava()[0]))
                razdely.append(("Библиотека датчиков", osmotr.dll()[0]))
                razdely.append(("Железо", osmotr.zhelezo()[0]))
                # Сбор датчиков у окна уже поднят - второй не нужен,
                # он бы полез в те же порты и в ту же библиотеку.
                nahodki, _s, _est = osmotr.datchiki(zhdat=6.0,
                                                    s=self.app.sensors)
                razdely.append(("Датчики", nahodki))
                razdely.append(("Экран", osmotr.ekran()[0]))
                razdely.append(("Погода", osmotr.pogoda(self.app.sensors)[0]))
            except Exception as e:
                razdely.append(("Осмотр", [osmotr.Nahodka(
                    False, "не вышло", str(e)[:120])]))
            self._osm_gotovo = razdely

        threading.Thread(target=rabota, daemon=True).start()

    def _osmotr_zhdat(self):
        """Заглянуть, не закончил ли осмотр. Идёт в главном потоке."""
        gotovo = getattr(self, "_osm_gotovo", None)
        if gotovo is None:
            self.after(400, self._osmotr_zhdat)
            return
        self._osm_gotovo = None
        self._osmotr_gotov(gotovo)

    def _osmotr_gotov(self, razdely):
        self.osm_nahodki = razdely
        if self.current != "osmotr":
            return
        bed = sum(1 for _imya, spisok in razdely
                  for n in spisok if n.horosho is False and n.vazhno)
        self.osm_state.configure(
            text=t("всё в порядке") if not bed
            else t("важных замечаний: {}").format(bed))
        try:
            self.osm_btn.state(["!disabled"])
        except Exception:
            pass
        self._osmotr_pokazat(razdely)

    def _osmotr_pokazat(self, razdely):
        """Разложить находки по разделам. Беды - наверх каждого раздела."""
        lk = self.look
        for w in self.osm_mesto.winfo_children():
            w.destroy()
        for imya, spisok in razdely:
            if not spisok:
                continue
            ttk.Label(self.osm_mesto, text=imya,
                      style="Card.Sub.TLabel").pack(anchor="w", pady=(10, 4))
            for n in spisok:
                stroka = ttk.Frame(self.osm_mesto, style="Card.TFrame")
                stroka.pack(fill="x")
                if n.horosho is None:
                    znak, stil = " ", "Card.Faint.TLabel"
                elif n.horosho:
                    znak, stil = lk.icon("ok"), "Card.Ok.TLabel"
                else:
                    znak = lk.icon("warning")
                    stil = "Card.Bad.TLabel" if n.vazhno else "Card.Warn.TLabel"
                ttk.Label(stroka, text=znak, style=stil,
                          font=lk.icon_font(11), width=3).pack(side="left")
                ttk.Label(stroka, text=t(n.chto), style="Card.TLabel",
                          width=34, anchor="w").pack(side="left")
                ttk.Label(stroka, text=t(n.pojasnenie),
                          style="Card.Faint.TLabel").pack(side="left")
                if n.chinit:
                    self._osmotr_chinit(n)

    def _osmotr_chinit(self, n):
        """Строчка «что делать» и кнопка, если чинится нажатием."""
        lk = self.look
        stroka = ttk.Frame(self.osm_mesto, style="Card.TFrame")
        stroka.pack(fill="x", pady=(0, 4))
        ttk.Label(stroka, text="", width=3).pack(side="left")
        ttk.Label(stroka, text=t(n.chinit), style="Card.Warn.TLabel",
                  wraplength=520, justify="left").pack(side="left")
        chinit = str(n.chinit)
        if chinit.startswith("pip install"):
            ttk.Button(stroka, text="Скопировать",
                       style="Quiet.TButton",
                       command=lambda c=chinit: self._v_bufer(c)).pack(
                side="left", padx=(8, 0))
        elif "Погода" in chinit:
            ttk.Button(stroka, text="Открыть", style="Quiet.TButton",
                       command=lambda: self.show_section("weather")).pack(
                side="left", padx=(8, 0))

    def _v_bufer(self, text):
        """Положить команду в буфер обмена: набирать её руками незачем."""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.osm_state.configure(text=t("команда в буфере обмена"))
        except Exception:
            pass

    def _units(self, parent):
        """Градусы, часы, дата, начало недели.

        Настройка общая: её слушают и окно, и то, что уходит на экран
        водянки. Тему при этом переписывать не надо - подпись «°C»
        движок меняет сам, см. edinicy.podpis.
        """
        lk = self.look
        card = L.Card(parent, lk, padding=18)
        card.pack(fill="x")
        b = card.body
        for zagolovok, poyasnenie, klyuch, varianty in (
                ("Градусы", "и температура железа, и погода",
                 "units.temp",
                 [("system", "Как в Windows", "windows"),
                  ("c", "Цельсий", "thermo"), ("f", "Фаренгейт", "thermo")]),
                ("Ветер", "и в окне, и в надписях на экране",
                 "units.wind",
                 [("system", "Как в Windows", "windows"),
                  ("kmh", "км/ч", "sliders"), ("ms", "м/с", "sliders"),
                  ("mph", "миль/ч", "sliders")]),
                ("Часы", "двенадцать часов дописывают AM и PM",
                 "units.clock",
                 [("system", "Как в Windows", "windows"),
                  ("24", "24 часа", "about"), ("12", "12 часов", "about")]),
                ("Порядок чисел в дате", "день, месяц и год",
                 "units.date",
                 [("system", "Как в Windows", "windows"),
                  ("dmy", "13.08.2026", "about"),
                  ("mdy", "08/13/2026", "about"),
                  ("ymd", "2026-08-13", "about")]),
                ("Неделя начинается", "по этому дню тема считает номер дня",
                 "units.week_start",
                 [("mon", "с понедельника", "about"),
                  ("sun", "с воскресенья", "about")])):
            ttk.Label(b, text=zagolovok,
                      style="Card.Sub.TLabel").pack(anchor="w", pady=(14, 0))
            ttk.Label(b, text=t(poyasnenie),
                      style="Card.Faint.TLabel").pack(anchor="w", pady=(0, 6))
            L.Segmented(b, lk, varianty, value=str(prefs.get(klyuch)),
                        command=lambda v, k=klyuch: self._set_unit(k, v)
                        ).pack(anchor="w")

        card = L.Card(parent, lk, padding=18)
        card.pack(fill="x", pady=(14, 0))
        b = card.body
        ttk.Label(b, text="Как это будет выглядеть",
                  style="Card.Sub.TLabel").pack(anchor="w")
        ttk.Label(b, text="по умолчанию всё берётся из самой Windows: "
                          "какие единицы и форматы там выбраны, такие "
                          "и здесь",
                  style="Card.Faint.TLabel", wraplength=620,
                  justify="left").pack(anchor="w", pady=(2, 0))
        self.units_lbl = ttk.Label(b, text="", style="Card.TLabel")
        self.units_lbl.pack(anchor="w", pady=(6, 0))
        ttk.Label(b, text="Тема может брать готовые {time}, {date} и {deg} — "
                          "они идут по этой настройке. А может писать свой "
                          "вид через {now:…} — тогда настройка его не тронет.",
                  style="Card.Faint.TLabel", wraplength=620,
                  justify="left").pack(anchor="w", pady=(8, 0))
        self._units_primer()

    def _set_unit(self, key, value):
        prefs.set(key, value)
        self._units_primer()

    def _units_primer(self):
        """Строка-образец: та же, что уйдёт на экран."""
        from datetime import datetime
        now = datetime.now()
        self.units_lbl.configure(
            text="{:.0f} {}   ·   {:.0f} {}   ·   {}   ·   {}   ·   {} ({})"
            .format(edinicy.gradusy(67.0), edinicy.znak(),
                    edinicy.veter(14.0), t(edinicy.znak_vetra()),
                    edinicy.chasy(now), edinicy.data(now),
                    now.strftime("%A"), edinicy.den_nedeli(now)))

    def _start(self, parent):
        lk = self.look
        card = L.Card(parent, lk, padding=18)
        card.pack(fill="x")
        b = card.body
        for key, label, hint in (
                ("start.desktop_shortcut", "Ярлык на рабочем столе",
                 "чтобы запускать не из папки, а с рабочего стола"),
                ("start.autostart", "Запускать вместе с Windows",
                 "через app.bat, чтобы поднялись права на температуру"),
                ("start.minimized", "Открывать сразу свёрнутым в трей",
                 "окно не мешает, панель работает"),
                ("start.screen_on", "Сразу включать экран",
                 "не нажимать кнопку каждый раз"),
                ("start.close_to_tray", "Крестик прячет в трей, а не закрывает",
                 "иначе панель погаснет вместе с окном")):
            # Ярлык спрашиваем у рабочего стола, а не у настроек: его
            # могли убрать мимо программы, и галочка врала бы.
            est = (prefs.yarlyk_est() if key == "start.desktop_shortcut"
                   else bool(prefs.get(key)))
            var = tk.BooleanVar(value=est)
            cb = ttk.Checkbutton(b, text=label, variable=var,
                                 style="Card.TCheckbutton",
                                 command=lambda k=key, v=var: self._flag(k, v))
            cb.pack(anchor="w", pady=(8, 0))
            ttk.Label(b, text="      " + t(hint),
                      style="Card.Faint.TLabel").pack(anchor="w")
            self.app.tip.add(cb, hint)

    def _flag(self, key, var):
        on = bool(var.get())
        if key == "start.autostart":
            if not prefs.set_autostart(on):
                messagebox.showwarning(
                    t("Автозапуск"),
                    t("Не удалось изменить запись в реестре."))
                return
        if key == "start.desktop_shortcut":
            # Значок для ярлыка рисуем той же рукой, что и значок в трее,
            # и кладём рядом с программой - ярлык на него сошлётся.
            znachok = None
            try:
                znachok = os.path.join(
                    os.path.dirname(os.path.abspath(prefs.__file__)),
                    "EOne screen.ico")
                if on and not os.path.exists(znachok):
                    panel_mod.save_icon(znachok)
            except Exception:
                znachok = None
            if not prefs.set_yarlyk(on, znachok):
                messagebox.showwarning(
                    t("Ярлык на рабочем столе"),
                    t("Не получилось. Рабочий стол может быть закрыт "
                      "для записи."))
                var.set(prefs.yarlyk_est())
                return
            return                    # состояние уже записано внутри
        prefs.set(key, on)

    def _sensors(self, parent):
        lk = self.look
        card = L.Card(parent, lk, padding=18)
        card.pack(fill="x")
        b = card.body
        ttk.Label(b, text="Что опрашивать",
                  style="Card.Sub.TLabel").pack(anchor="w")
        ttk.Label(b, text="выключенный источник не опрашивается вообще — "
                          "это и есть экономия",
                  style="Card.Faint.TLabel").pack(anchor="w", pady=(0, 6))
        row = ttk.Frame(b, style="Card.TFrame")
        row.pack(fill="x")
        for key, label, hint, icon in (
                ("system", "Процессор, память, диски, сеть",
                 "почти бесплатно", "chip"),
                ("gpu", "Видеокарта", "через nvidia-smi", "screen"),
                ("temps", "Температуры",
                 "нужны права администратора", "thermo"),
                ("weather", "Погода, восход и закат",
                 "нужен интернет", "water")):
            var = tk.BooleanVar(value=bool(prefs.get("sensors.%s.on" % key, True)))
            cb = ttk.Checkbutton(b, text=label, variable=var,
                                 style="Card.TCheckbutton",
                                 command=lambda k=key, v=var: self._sensor(k, v))
            cb.pack(anchor="w", pady=(8, 0))
            ttk.Label(b, text="      " + t(hint),
                      style="Card.Faint.TLabel").pack(anchor="w")
            self.app.tip.add(cb, hint)
        ttk.Label(b, text="Изменения применятся при следующем запуске.",
                  style="Card.Faint.TLabel").pack(anchor="w", pady=(10, 0))

        live = L.Card(parent, lk, padding=18)
        live.pack(fill="both", expand=True, pady=(14, 0))
        lb = live.body
        ttk.Label(lb, text="Что читается прямо сейчас",
                  style="Card.Sub.TLabel").pack(anchor="w")
        self.src = ttk.Label(lb, text="", style="Card.Faint.TLabel",
                             justify="left")
        self.src.pack(anchor="w", pady=(4, 8))
        # Список сырой: по нему настраивают реакцию слоёв, а пороги
        # реакции всегда в Цельсиях - иначе выбор шкалы сдвинул бы их все.
        ttk.Label(lb, text="значения как есть, до перевода в выбранные "
                           "единицы: температуры здесь всегда в Цельсиях, "
                           "на них настраивается реакция слоёв",
                  style="Card.Faint.TLabel", wraplength=620,
                  justify="left").pack(anchor="w", pady=(0, 6))
        self.values = tk.Text(lb, height=16, relief="flat", bd=0,
                              highlightthickness=0, bg=lk.c["surface"],
                              fg=lk.c["text"], font=lk.font("mono"))
        self.values.pack(fill="both", expand=True)
        self._live()

    def _live(self):
        if not hasattr(self, "values") or not self.values.winfo_exists():
            return
        try:
            self.src.configure(text=self.app.sensors.describe())
            lines = ["  {:22s} {}".format(
                k, "{:.2f}".format(v) if isinstance(v, float) else v)
                for k, v in sorted(self.app.data.items())]
            self.values.delete("1.0", "end")
            self.values.insert("1.0", "\n".join(lines))
        except Exception:
            pass

    def _sensor(self, key, var):
        prefs.set("sensors.%s.on" % key, bool(var.get()))

    def _weather(self, parent):
        """Где мы находимся. От этого зависит и погода, и время восхода."""
        lk = self.look
        card = L.Card(parent, lk, padding=18)
        card.pack(fill="x")
        b = card.body
        ttk.Label(b, text="Место", style="Card.Sub.TLabel").pack(anchor="w")
        ttk.Label(b, text="по нему берётся прогноз, а заодно время восхода "
                          "и заката — от них панель светлеет и темнеет",
                  style="Card.Faint.TLabel", wraplength=620,
                  justify="left").pack(anchor="w", pady=(0, 10))

        row = ttk.Frame(b, style="Card.TFrame")
        row.pack(fill="x")
        self.city_var = tk.StringVar()
        ent = ttk.Entry(row, textvariable=self.city_var, width=28)
        ent.pack(side="left")
        ent.bind("<Return>", lambda e: self._find_city())
        ttk.Button(row, text="Найти", style="Accent.TButton",
                   command=self._find_city).pack(side="left", padx=6)
        ttk.Button(row, text="По адресу в сети", style="Quiet.TButton",
                   command=self._city_by_ip).pack(side="left")
        self.app.tip.add(ent, "Название города на любом языке. "
                              "Нажми «Найти» и выбери из списка.")

        self.city_list = tk.Listbox(b, height=6, activestyle="none",
                                    exportselection=False)
        self.city_list.pack(fill="x", pady=(10, 6))
        self.city_list.bind("<Double-Button-1>", lambda e: self._pick_city())
        self.found = []
        ttk.Button(b, text="Выбрать это место", style="Accent.TButton",
                   command=self._pick_city).pack(anchor="w")

        self.city_now = ttk.Label(b, text="", style="Card.Faint.TLabel",
                                  justify="left")
        self.city_now.pack(anchor="w", pady=(12, 0))
        self._show_place()
        ttk.Label(b, text="Проверить, как тема выглядит в дождь или метель, "
                          "можно на главной — ряд справа от выбора дня и ночи.",
                  style="Card.Faint.TLabel", wraplength=620,
                  justify="left").pack(anchor="w", pady=(10, 0))
        self._istochnik(parent)

    def _istochnik(self, parent):
        """Откуда брать прогноз. По умолчанию Open-Meteo, но можно свой."""
        lk = self.look
        card = L.Card(parent, lk, padding=18)
        card.pack(fill="x", pady=(14, 0))
        b = card.body
        conf = sensors_mod._weather_config()
        ttk.Label(b, text="Источник прогноза",
                  style="Card.Sub.TLabel").pack(anchor="w")
        ttk.Label(b, text="по умолчанию Open-Meteo: без ключа и без "
                          "регистрации. Другие службы отвечают по-своему, "
                          "поэтому у каждой свой переходник — выберите "
                          "нужную, и программа сама переведёт её ответ "
                          "в понятный панели вид.",
                  style="Card.Faint.TLabel", wraplength=620,
                  justify="left").pack(anchor="w", pady=(0, 10))

        self.kind_var = tk.StringVar(
            value=str(conf.get("source_kind") or "open-meteo"))
        # Двумя рядами, а не одним: шесть служб в строку не помещаются,
        # и разделение по ключу сразу отвечает на главный вопрос -
        # надо ли где-то регистрироваться.
        for podpis, spisok in (
                ("Без ключа и без регистрации",
                 ("open-meteo", "metno", "wttr")),
                ("По ключу службы", ("openweather", "weatherapi", "svoy"))):
            ttk.Label(b, text=podpis, style="Card.Faint.TLabel").pack(
                anchor="w", pady=(6, 2))
            L.Segmented(b, lk,
                        [(vid, sensors_mod.PEREHODNIKI[vid]["imya"], "water")
                         for vid in spisok],
                        value=self.kind_var.get(),
                        command=self._set_kind).pack(anchor="w")

        # Поле ключа показываем только тем службам, которым он нужен:
        # у Open-Meteo его нет вовсе, и пустая строка только путала бы.
        self.key_var = tk.StringVar(value=str(conf.get("source_key", "")))
        if sensors_mod.PEREHODNIKI.get(self.kind_var.get(), {}).get("klyuch"):
            krow = ttk.Frame(b, style="Card.TFrame")
            krow.pack(fill="x", pady=(0, 8))
            ttk.Label(krow, text="Ключ", style="Card.TLabel",
                      width=8, anchor="w").pack(side="left")
            kent = ttk.Entry(krow, textvariable=self.key_var, width=44)
            kent.pack(side="left")
            self.app.tip.add(kent, "Ключ выдаёт сама служба при регистрации. "
                                   "Он хранится в weather.json рядом "
                                   "с программой.")

        row = ttk.Frame(b, style="Card.TFrame")
        row.pack(fill="x")
        ttk.Label(row, text="Адрес", style="Card.TLabel",
                  width=8, anchor="w").pack(side="left")
        self.src_var = tk.StringVar(value=conf.get("source", ""))
        ent = ttk.Entry(row, textvariable=self.src_var, width=44)
        ent.pack(side="left")
        self.app.tip.add(ent, "Пусто — обычный адрес выбранной службы. "
                              "Свой нужен для зеркала или своего сервера: "
                              "полный адрес без вопросов и параметров, "
                              "их программа допишет сама.")

        row = ttk.Frame(b, style="Card.TFrame")
        row.pack(fill="x", pady=(8, 0))
        ttk.Button(row, text="Проверить", style="Accent.TButton",
                   command=self._proba_istochnika).pack(side="left")
        ttk.Button(row, text="Обычный", style="Quiet.TButton",
                   command=self._obychny).pack(side="left", padx=6)
        self.src_lbl = ttk.Label(b, text="", style="Card.Faint.TLabel",
                                 wraplength=620, justify="left")
        self.src_lbl.pack(anchor="w", pady=(10, 0))
        vid = sensors_mod.PEREHODNIKI.get(self.kind_var.get(), {})
        self.src_lbl.configure(text=self.src_var.get() or vid.get("base", ""))
        if self.kind_var.get() == "svoy":
            self._svoy(parent, conf)

    # --- своя служба погоды ----------------------------------------------

    # Что панели нужно от службы. Обязательна только температура:
    # без неё показывать нечего, остальное панель переживёт прочерком.
    SVOI_POLYA = [
        ("temp", "Температура", True),
        ("code", "Состояние погоды числом", False),
        ("feels", "Ощущается как", False),
        ("humidity", "Влажность", False),
        ("wind", "Ветер", False),
        ("min", "Минимум за сутки", False),
        ("max", "Максимум за сутки", False),
        ("sunrise", "Восход", False),
        ("sunset", "Закат", False),
    ]

    def _svoy(self, parent, conf):
        """Описать чужую службу, не заглядывая в её JSON руками.

        Порядок такой: человек вписывает адрес, программа спрашивает
        службу один раз и раскладывает ответ на пути. Дальше остаётся
        выбрать из списков, где лежит температура, где ветер, - и
        описание записывается в weather.json.
        """
        lk = self.look
        karta = dict(conf.get("source_map") or {})
        polya = dict(karta.get("polya") or {})
        card = L.Card(parent, lk, padding=18)
        card.pack(fill="x", pady=(14, 0))
        b = card.body
        ttk.Label(b, text="Где что лежит в ответе",
                  style="Card.Sub.TLabel").pack(anchor="w")
        ttk.Label(b, text="В адресе можно писать {lat}, {lon} и {key} — "
                          "программа подставит место и ключ. Нажмите "
                          "«Спросить службу»: ответ разберётся на пути, "
                          "и останется выбрать нужные из списков.",
                  style="Card.Faint.TLabel", wraplength=620,
                  justify="left").pack(anchor="w", pady=(0, 10))
        ttk.Button(b, text="Спросить службу", style="Accent.TButton",
                   command=self._svoy_sprosit).pack(anchor="w")

        self.svoy_vars = {}
        got = getattr(self, "svoy_puti", None) or sorted(
            set(v for v in polya.values() if v))
        for key, podpis, nuzhno in self.SVOI_POLYA:
            row = ttk.Frame(b, style="Card.TFrame")
            row.pack(fill="x", pady=(6, 0))
            ttk.Label(row, text=t(podpis) + ("  *" if nuzhno else ""),
                      style="Card.TLabel", width=26,
                      anchor="w").pack(side="left")
            var = tk.StringVar(value=str(polya.get(key, "")))
            box = ttk.Combobox(row, textvariable=var, width=42,
                               values=[""] + list(got))
            box.pack(side="left")
            self.svoy_vars[key] = var

        row = ttk.Frame(b, style="Card.TFrame")
        row.pack(fill="x", pady=(12, 0))
        ttk.Label(row, text="Ветер в", style="Card.TLabel",
                  width=26, anchor="w").pack(side="left")
        self.svoy_veter = tk.StringVar(value=str(karta.get("veter", "km/h")))
        ttk.Combobox(row, textvariable=self.svoy_veter, width=12,
                     values=["km/h", "m/s", "mph"]).pack(side="left")

        row = ttk.Frame(b, style="Card.TFrame")
        row.pack(fill="x", pady=(6, 0))
        ttk.Label(row, text="Восход записан как", style="Card.TLabel",
                  width=26, anchor="w").pack(side="left")
        self.svoy_vremya = tk.StringVar(value=str(karta.get("vremya", "iso")))
        ttk.Combobox(row, textvariable=self.svoy_vremya, width=22,
                     values=["iso", "unix", "12h", "24h"]).pack(side="left")
        ttk.Label(b, text="iso — 2026-08-13T05:08, unix — число секунд, "
                          "12h — 05:08 AM, 24h — 05:08",
                  style="Card.Faint.TLabel").pack(anchor="w", pady=(2, 0))

        row = ttk.Frame(b, style="Card.TFrame")
        row.pack(fill="x", pady=(6, 0))
        ttk.Label(row, text="Числа состояния", style="Card.TLabel",
                  width=26, anchor="w").pack(side="left")
        self.svoy_kody = tk.StringVar(
            value="wmo" if not karta.get("kody") else str(karta.get("kody")))
        ttk.Combobox(row, textvariable=self.svoy_kody, width=22,
                     values=["wmo", "openweather",
                             "weatherapi"]).pack(side="left")
        ttk.Label(b, text="wmo — служба уже отдаёт коды по стандарту ВМО. "
                          "Своя таблица чисел прописывается в weather.json, "
                          "см. справочник.",
                  style="Card.Faint.TLabel", wraplength=620,
                  justify="left").pack(anchor="w", pady=(2, 0))

        self.svoy_lbl = ttk.Label(b, text="", style="Card.Faint.TLabel",
                                  wraplength=620, justify="left")
        self.svoy_lbl.pack(anchor="w", pady=(10, 0))

    def _svoy_karta(self):
        """Собрать описание из того, что выбрано в списках."""
        polya = {k: v.get().strip()
                 for k, v in self.svoy_vars.items() if v.get().strip()}
        kody = self.svoy_kody.get().strip()
        return {"imya": "свой источник",
                "base": self.src_var.get().strip(),
                "klyuch": bool(self.key_var.get().strip()),
                "zapros": "",
                "polya": polya,
                "veter": self.svoy_veter.get().strip() or "km/h",
                "vremya": self.svoy_vremya.get().strip() or "iso",
                "kody": None if kody in ("", "wmo") else kody}

    def _svoy_sprosit(self):
        """Спросить службу и разложить её ответ на пути."""
        conf = sensors_mod._weather_config()
        lat, lon = conf.get("latitude"), conf.get("longitude")
        if lat is None:
            self.svoy_lbl.configure(text="Сначала выберите место — без него "
                                         "спрашивать не о чем.")
            return
        url = self.src_var.get().strip()
        if not url:
            self.svoy_lbl.configure(text="Впишите адрес службы.")
            return
        key = self.key_var.get().strip()
        self.svoy_lbl.configure(text="  спрашиваю…")
        self.update_idletasks()

        def rabota():
            try:
                otvet = sensors_mod.syroy_otvet(url, lat, lon, "svoy", key,
                                                self._svoy_karta())
                self.svoy_puti = sorted(set(sensors_mod.puti(otvet)))
                itog = t("служба ответила, полей нашлось: {}. "
                         "Выберите нужные из списков и нажмите "
                         "«Проверить».").format(len(self.svoy_puti))
            except Exception as e:
                self.svoy_puti = None
                itog = t("не вышло: {}").format(str(e)[:150])
            self.after(0, lambda: self._svoy_gotovo(itog))

        threading.Thread(target=rabota, daemon=True).start()

    def _svoy_gotovo(self, itog):
        """Ответ пришёл: перерисовать раздел, чтобы в списках были пути."""
        if getattr(self, "svoy_puti", None):
            self.show_section("weather")
        self.svoy_lbl.configure(text=itog)

    def _set_kind(self, value):
        """Сменить службу. Записываем сразу и перерисовываем раздел:
        у одних служб нужно поле ключа, у других его быть не должно."""
        sensors_mod.save_source(self.src_var.get().strip(), value,
                                self.key_var.get().strip())
        self.show_section("weather")

    def _obychny(self):
        """Вернуть всё к Open-Meteo: ни ключа, ни адреса, ни описания."""
        self.svoy_puti = None
        sensors_mod.save_source("", "open-meteo", "", {})
        self.app.sensors.refresh_weather()
        self.show_section("weather")

    def _proba_istochnika(self):
        """Спросить источник один раз и записать, если ответил."""
        conf = sensors_mod._weather_config()
        lat, lon = conf.get("latitude"), conf.get("longitude")
        if lat is None:
            self.src_lbl.configure(text="Сначала выберите место — без него "
                                        "спрашивать не о чем.")
            return
        url = self.src_var.get().strip()
        kind = self.kind_var.get()
        key = self.key_var.get().strip()
        self.src_lbl.configure(text="  спрашиваю…")
        self.update_idletasks()

        karta = self._svoy_karta() if kind == "svoy" else None

        def rabota():
            try:
                got = sensors_mod.try_source(url, lat, lon, kind, key, karta)
                sensors_mod.save_source(url, kind, key, karta)
                self.app.sensors.refresh_weather()
                itog = t("{} отвечает: {}, {:.0f} {}, ветер {:.0f} {}. "
                         "Записано.").format(
                             got["source"], got["text"],
                             edinicy.gradusy(got["temp"]), edinicy.znak(),
                             edinicy.veter(got["wind"]),
                             t(edinicy.znak_vetra()))
                if not got.get("sunrise"):
                    itog += t("\nВосхода и заката эта служба не даёт — "
                              "считаем их сами по координатам.")
            except Exception as e:
                itog = t("Не отвечает или отвечает не тем: {}").format(
                    str(e)[:90])
            try:      # окно могли закрыть, пока мы спрашивали
                self.after(0, lambda: self.src_lbl.configure(text=itog))
            except Exception:
                pass

        threading.Thread(target=rabota, daemon=True).start()

    def _place_conf(self):
        import json
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(
                    sensors_mod.__file__)), "weather.json"),
                    encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _show_place(self):
        conf = self._place_conf()
        if conf.get("latitude") is None:
            self.city_now.configure(text="Место не выбрано — прогноза не будет, "
                                         "а восход и закат возьмутся "
                                         "запасные: 07:00 и 20:00.")
            return
        self.city_now.configure(
            text="Сейчас: {}   ({:.3f}, {:.3f})\n{}".format(
                conf.get("city") or "без названия",
                float(conf["latitude"]), float(conf["longitude"]),
                self.app.sensors.describe().strip().splitlines()[-1].strip()))

    def _find_city(self):
        name = self.city_var.get().strip()
        if not name:
            return
        self.city_list.delete(0, "end")
        self.city_list.insert("end", "  ищу…")
        self.update_idletasks()

        def work():
            try:
                got = sensors_mod.find_places(name)
            except Exception as e:
                got = e
            self.after(0, lambda: self._show_found(got))

        threading.Thread(target=work, daemon=True).start()

    def _show_found(self, got):
        self.city_list.delete(0, "end")
        if isinstance(got, Exception):
            self.city_list.insert("end", "  не вышло: {}".format(str(got)[:60]))
            self.found = []
            return
        self.found = got
        if not got:
            self.city_list.insert("end", "  ничего не нашлось")
            return
        for p in got:
            self.city_list.insert("end", "  {} — {}".format(p["city"],
                                                            p["where"]))
        self.city_list.selection_set(0)

    def _pick_city(self):
        sel = self.city_list.curselection()
        if not self.found or not sel:
            return
        p = self.found[sel[0]]
        try:
            sensors_mod.save_location(p["latitude"], p["longitude"], p["city"])
            self.app.sensors.refresh_weather()
        except Exception as e:
            messagebox.showerror("Место", str(e))
            return
        self._show_place()
        self.app.head_state.config(text=t("место: {}").format(p["city"]))

    def _city_by_ip(self):
        """Определить место по адресу в сети - если название вводить лень."""
        def work():
            try:
                import urllib.request, json as js
                with urllib.request.urlopen(
                        "http://ip-api.com/json/?fields=lat,lon,city",
                        timeout=8) as r:
                    d = js.loads(r.read().decode("utf-8"))
                sensors_mod.save_location(d["lat"], d["lon"], d.get("city", ""))
                self.app.sensors.refresh_weather()
                self.after(0, self._show_place)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Место", str(e)))

        threading.Thread(target=work, daemon=True).start()

    def _speed(self, parent):
        lk = self.look
        card = L.Card(parent, lk, padding=18)
        card.pack(fill="x")
        b = card.body
        ttk.Label(b, text="Картинка и нагрузка",
                  style="Card.Sub.TLabel").pack(anchor="w")
        ttk.Label(b, text="эти значения хранятся внутри темы",
                  style="Card.Faint.TLabel").pack(anchor="w", pady=(0, 10))
        for key, label, hint in (
                ("fps", "Кадров в секунду", "ниже 0.5 нельзя: экран уснёт"),
                ("quality", "Качество JPEG", "1–100, влияет на размер кадра"),
                ("supersample", "Сглаживание", "2 или 3, больше — плавнее края"),
                ("transition_seconds", "Переход день/ночь, секунд",
                 "сколько длится смена вида")):
            row = ttk.Frame(b, style="Card.TFrame")
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label, style="Card.TLabel", width=26,
                      anchor="w").pack(side="left")
            var = tk.StringVar(value=str(self.app.cfg().get("screen", {})
                                         .get(key, "")))
            ent = ttk.Entry(row, textvariable=var, width=8)
            ent.pack(side="left")
            ttk.Label(row, text="  " + t(hint),
                      style="Card.Faint.TLabel").pack(side="left")
            var.trace_add("write", lambda *a, k=key, v=var: self._num(k, v))
            self.app.tip.add(ent, hint)

        # Потоки - настройка машины, а не темы, поэтому отдельной карточкой
        # и с прямым разговором о том, чего от неё ждать.
        card = L.Card(parent, lk, padding=18)
        card.pack(fill="x", pady=(14, 0))
        bp = card.body
        ttk.Label(bp, text="Сборка кадра",
                  style="Card.Sub.TLabel").pack(anchor="w")
        ttk.Label(bp, text="это про машину, а не про тему: настройка "
                           "остаётся при смене темы",
                  style="Card.Faint.TLabel").pack(anchor="w", pady=(0, 10))
        L.Segmented(bp, lk, [("1", "В один поток", "chip"),
                             ("2", "В два потока", "chip"),
                             ("4", "В четыре", "chip"),
                             ("0", "Пусть решит сама", "sliders")],
                    value=str(prefs.get("speed.threads", 1)),
                    command=self._set_threads).pack(anchor="w")
        ttk.Label(bp, text="Кадр собирается кусками, и куски друг о друге "
                           "не знают — их можно готовить разом. Картинка "
                           "выходит та же до последней точки, проверено. "
                           "Но выигрыш во времени невелик и на быстрой "
                           "машине теряется в разбросе: если панель и так "
                           "укладывается в отпущенное время, кадров "
                           "в секунду не прибавится. Смысл — уложиться "
                           "на слабой машине.",
                  style="Card.Faint.TLabel", wraplength=620,
                  justify="left").pack(anchor="w", pady=(8, 0))

        card = L.Card(parent, lk, padding=18)
        card.pack(fill="x", pady=(14, 0))
        b = card.body
        self.pack_var = tk.BooleanVar(
            value=bool(self.app.cfg().get("screen", {}).get("pack_frames", True)))
        cb = ttk.Checkbutton(b, text="Сжимать кадры фона в памяти",
                             variable=self.pack_var, style="Card.TCheckbutton",
                             command=self._set_pack)
        cb.pack(anchor="w", pady=(12, 0))
        self.app.tip.add(cb, "Сжатие без потерь: картинка та же до последнего "
                             "бита, памяти уходит втрое меньше. Плата — "
                             "около семи десятых миллисекунды на кадр. "
                             "Переключение заставляет заново разобрать все "
                             "кадры фона: на тяжёлой теме экран замрёт "
                             "на несколько секунд.")
        self.mem_lbl = ttk.Label(b, text="", style="Card.Faint.TLabel")
        self.mem_lbl.pack(anchor="w")
        self._show_mem()

        # Что из заданного выходит на самом деле. Без этой строчки непонятно,
        # подействовала настройка или нет: поставил тридцать, а экран как шёл,
        # так и идёт - и не разберёшь, то ли не применилось, то ли не тянет.
        self.real_lbl = ttk.Label(b, text="", style="Card.Sub.TLabel")
        self.real_lbl.pack(anchor="w", pady=(12, 0))
        self.real_hint = ttk.Label(b, text="", style="Card.Faint.TLabel",
                                   wraplength=520, justify="left")
        self.real_hint.pack(anchor="w")
        self._show_real()

    def _show_real(self):
        """Сколько кадров экран выдаёт прямо сейчас против заданного."""
        if not hasattr(self, "real_lbl") or not self.real_lbl.winfo_exists():
            return
        want = float(self.app.cfg().get("screen", {}).get("fps", 1) or 1)
        if not self.app.running():
            self.real_lbl.configure(text="Экран выключен")
            self.real_hint.configure(
                text="Включите вывод на главной — здесь будет видно, "
                     "сколько кадров получается на самом деле.")
            return
        got = float(getattr(self.app.runner, "fps_real", 0.0) or 0.0)
        self.real_lbl.configure(
            text=t("Задано {:g}, выходит {:.1f} кадр/с").format(want, got))
        if got < 1:
            note = "Только запустились, счёт ещё набирается."
        elif got >= want * 0.95:
            note = "Успевает."
        else:
            note = ("Не успевает: {:.0f} %. Упирается либо в отрисовку — "
                    "тогда помогут меньше сглаживание и меньше живых слоёв, — "
                    "либо в канал до экрана: тогда снижайте качество JPEG, "
                    "кадр станет легче.".format(100.0 * got / want))
        self.real_hint.configure(text=note)

    def _show_mem(self):
        try:
            import psutil
            mb = psutil.Process().memory_info().rss / 1048576.0
            self.mem_lbl.configure(
                text=t("      сейчас программа занимает {:.0f} МБ").format(mb))
        except Exception:
            self.mem_lbl.configure(text="")

    def _num(self, key, var):
        s = var.get().strip().replace(",", ".")
        try:
            self.app.cfg().setdefault("screen", {})[key] = \
                float(s) if "." in s else int(s)
        except ValueError:
            return
        self.app.editor.dirty = True

    def _set_threads(self, value):
        """Во сколько потоков собирать кадр.

        Панель читает это на каждом кадре, поэтому перезапуска не нужно:
        следующий же кадр соберётся по-новому.
        """
        prefs.set("speed.threads", int(value))

    def _set_pack(self):
        on = bool(self.pack_var.get())
        self.app.cfg().setdefault("screen", {})["pack_frames"] = on
        panel_mod._PREPARED.clear()
        self.app.editor.dirty = True
        self._show_mem()

    # --- о программе -----------------------------------------------------

    def _about(self, parent):
        lk = self.look
        card = L.Card(parent, lk, padding=18)
        card.pack(fill="x")
        b = card.body
        ttk.Label(b, text=panel_mod.PROJECT,
                  style="Card.Title.TLabel").pack(anchor="w")
        ttk.Label(b, text=t("версия {} · автор {}").format(
                      panel_mod.VERSION, panel_mod.AUTHOR),
                  style="Card.Faint.TLabel").pack(anchor="w", pady=(2, 10))
        ttk.Label(b, text="Открытая замена штатной программе для экрана "
                          "водянки: контроллер TXW818, панель ST7701S, "
                          "960x480 по COM-порту.",
                  style="Card.TLabel", wraplength=620,
                  justify="left").pack(anchor="w")

        card = L.Card(parent, lk, padding=18)
        card.pack(fill="x", pady=(14, 0))
        b = card.body
        ttk.Label(b, text="Лицензия", style="Card.Sub.TLabel").pack(anchor="w")
        ttk.Label(b, text="Creative Commons BY-NC-SA 4.0",
                  style="Card.TLabel").pack(anchor="w", pady=(2, 12))
        for icon, line in (
                ("ok", "Пользоваться, копировать и переделывать — можно."),
                ("warning", "Зарабатывать на этом — нельзя."),
                ("copy", "Переделанное раздавать на тех же условиях "
                         "и с указанием автора.")):
            row = ttk.Frame(b, style="Card.TFrame")
            row.pack(fill="x", pady=2)
            L.icon_label(row, lk, icon, 12).pack(side="left", padx=(0, 8))
            ttk.Label(row, text=line, style="Card.TLabel", wraplength=560,
                      justify="left").pack(side="left")
        ttk.Label(b, text="Условия распространяются и на программу, и на темы, "
                          "которые с ней идут. Про коммерческое использование "
                          "договариваются с автором письменно.",
                  style="Card.Faint.TLabel", wraplength=620,
                  justify="left").pack(anchor="w", pady=(12, 0))

        row = ttk.Frame(b, style="Card.TFrame")
        row.pack(anchor="w", pady=(14, 0))
        # Файл на языке окна: читать условия на чужом языке человек
        # не обязан. Нет английского рядом - открываем русский.
        yaz = "en" if yazyk._teper == yazyk.EN else "ru"
        ryadom = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(ryadom, LICENSE_FILE.get(yaz, "LICENSE"))
        if not os.path.exists(path):
            path = os.path.join(ryadom, "LICENSE")
        btn = ttk.Button(row, text="Открыть файл лицензии",
                         style="Accent.TButton",
                         command=lambda: self._open_license(path))
        btn.pack(side="left")
        if not os.path.exists(path):
            btn.state(["disabled"])
            self.app.tip.add(btn, "Файла LICENSE нет рядом с программой.")
        ttk.Button(row, text="Полный текст в сети", style="Quiet.TButton",
                   command=lambda: webbrowser.open(
                       LICENSE_URL.get(yaz, LICENSE_URL["ru"]))).pack(
            side="left", padx=(8, 0))
        ttk.Label(b, text="      Наш файл — пересказ для человека. "
                          "Юридическую силу имеет полный текст на сайте "
                          "Creative Commons.",
                  style="Card.Faint.TLabel", wraplength=620,
                  justify="left").pack(anchor="w", pady=(6, 0))

        card = L.Card(parent, lk, padding=18)
        card.pack(fill="x", pady=(14, 0))
        b = card.body
        ttk.Label(b, text="Чужое", style="Card.Sub.TLabel").pack(anchor="w")
        ttk.Label(b, text="Температуры читает LibreHardwareMonitor — четыре "
                          "файла .dll рядом с программой. Библиотека "
                          "принадлежит своим авторам и идёт по своей "
                          "лицензии, MPL 2.0.",
                  style="Card.Faint.TLabel", wraplength=620,
                  justify="left").pack(anchor="w", pady=(4, 0))

    def _open_license(self, path):
        try:
            os.startfile(path)
        except Exception as e:
            messagebox.showwarning("Лицензия",
                                   t("Не удалось открыть файл: {}").format(e))
