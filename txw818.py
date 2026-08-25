#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
txw818.py - управление экраном водянки Jungle Leopard Pro Flow 360
            (контроллер TXW818, панель ST7701S, 960x480)

    python txw818.py                 тестовая картинка
    python txw818.py картинка.jpg    своя картинка
    python txw818.py --clock         часы
    python txw818.py --diag          подобрать рабочий способ отправки
    python txw818.py --help          все ключи
"""

import io
import json
import struct
import sys
import time

VERSION = "0.7"

# --- параметры порта, ровно как у родной программы (лог, пакеты 19-36) ------
BAUDRATE = 2000000
USE_DTR = True          # IOCTL_SERIAL_SET_DTR
USE_RTS = False         # IOCTL_SERIAL_CLR_RTS
# управление потоком отключено, формат 8N1

# идентификатор устройства из настроек родной программы
DEVICE_VID = 0x33C3
DEVICE_PID = 0x7788           # Jungle Leopard Pro Flow 360

# Тот же контроллер стоит и в родственных помпах, отличается только
# вторым числом. 7792 (панель HONGTAI, Flow 240) проверен на живой
# машине: протокол не менялся вовсе, экран принял кадры как свой.
# Новое число сюда дописывать только после такой же проверки - на слово
# верить нечему, разъём один, а начинка может быть любая.
DEVICE_PIDS = (0x7788, 0x7792)

# --- протокол ---------------------------------------------------------------
# Команда: 55 AA | длина (2 байта) | код | данные | сумма (2 байта)
#   длина - размер всего пакета целиком
#   сумма - сложение всех предыдущих байт пакета
# Картинка: команда 0x11, затем 4 байта длины, затем байты JPEG.

MAGIC = b"\x55\xaa"

CMD_BRIGHTNESS = 0x03
CMD_INFO = 0x06
CMD_IMG_BEGIN = 0x11
CMD_MODE = 0x15

RESYNC = b"\xff\xd9\xff\xd9\x00\x00\x00\x00"

W_DEFAULT, H_DEFAULT = 960, 480

# Сторожевой таймер прошивки: без свежего КАДРА экран возвращается к
# заводской заставке примерно через 3 секунды. Опрос командой info
# таймер не сбрасывает - проверено на практике.
WATCHDOG_SEC = 3.0
# На практике при 2 с экран успевал моргнуть заставкой между кадрами:
# порог считается не от конца, а от начала передачи. 1 с даёт тройной запас.
DEFAULT_INTERVAL = 1.0


def build(cmd, payload=b""):
    total = 2 + 2 + 1 + len(payload) + 2
    body = MAGIC + struct.pack("<H", total) + bytes([cmd]) + payload
    return body + struct.pack("<H", sum(body) & 0xFFFF)


def parse(frame):
    if frame[:2] != MAGIC:
        raise ValueError("ответ не начинается с 55 AA")
    total = struct.unpack("<H", frame[2:4])[0]
    if len(frame) != total:
        raise ValueError("длина ответа не совпадает с заявленной")
    got = struct.unpack("<H", frame[-2:])[0]
    calc = sum(frame[:-2]) & 0xFFFF
    if got != calc:
        raise ValueError("не сошлась контрольная сумма")
    return frame[4], frame[5:-2]


def _need_serial():
    try:
        import serial
        import serial.tools.list_ports
        return serial
    except ImportError:
        # не sys.exit: в потоке вывода SystemExit никто не ловит
        raise ImportError("не установлена библиотека pyserial. Выполни: pip install pyserial pillow")


def _need_pil():
    try:
        from PIL import Image, ImageDraw, ImageFont
        return Image, ImageDraw, ImageFont
    except ImportError:
        # не sys.exit: в потоке вывода SystemExit никто не ловит
        raise ImportError("не установлена библиотека Pillow. Выполни: pip install pyserial pillow")


def nash_li(p):
    """Наш ли это экран. p - то, что отдаёт list_ports."""
    return p.vid == DEVICE_VID and p.pid in DEVICE_PIDS


def find_port():
    _need_serial()
    from serial.tools import list_ports as lp
    for p in lp.comports():
        if nash_li(p):
            return p.device
    return None


# Одно и то же гнездо называется по-разному: на Windows это COM-порт,
# на Linux - /dev/ttyACM. Говорить человеку про COM там, где их нет,
# значит посылать его искать несуществующее.
LINUX = sys.platform.startswith("linux")
IMYA_PORTOV = "устройств на /dev/ttyACM" if LINUX else "COM-портов"
PRIMER_PORTA = "/dev/ttyACM0" if LINUX else "COM3"


def list_ports():
    _need_serial()
    from serial.tools import list_ports as lp
    ports = list(lp.comports())
    if not ports:
        print("{} не найдено вообще.".format(IMYA_PORTOV))
        print("Проверь кабель от помпы к разъёму USB на плате.")
        if LINUX:
            print("И проверь, что ты в группе доступа к порту: "
                  "dialout в Debian и Ubuntu, uucp в Arch.")
        return
    print("Найденные порты:\n")
    for p in ports:
        mark = "  <-- наш экран" if nash_li(p) else ""
        print("  {:<14} {}{}".format(p.device, p.description, mark))
        if p.vid is not None:
            print("           VID:PID = {:04X}:{:04X}".format(p.vid, p.pid))
    print()


class Display:
    def __init__(self, port, timeout=2.0):
        serial = _need_serial()
        try:
            self.ser = serial.Serial(port, baudrate=BAUDRATE, bytesize=8,
                                     parity="N", stopbits=1, timeout=timeout,
                                     write_timeout=5.0,
                                     rtscts=False, dsrdtr=False, xonxoff=False)
        except Exception as e:
            # Именно исключение, а не sys.exit: SystemExit не Exception,
            # его не ловит ни один обработчик, и поток вывода умер бы
            # молча, оставив в окне вечное «запускается».
            raise OSError(
                "не удалось открыть порт {}: {}. Чаще всего он занят "
                "родной программой экрана — закрой её полностью, "
                "включая значок рядом с часами.".format(port, e))
        self.ser.rts = USE_RTS
        self.ser.dtr = USE_DTR
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        self.width = W_DEFAULT
        self.height = H_DEFAULT

    # --- низкий уровень -----------------------------------------------------

    def drain(self):
        """Выбросить всё, что экран прислал и мы не прочитали."""
        n = 0
        try:
            while self.ser.in_waiting:
                n += len(self.ser.read(self.ser.in_waiting))
                time.sleep(0.005)
        except Exception:
            pass
        return n

    def _read_frame(self, timeout=None):
        limit = time.time() + (timeout if timeout is not None else self.ser.timeout)
        buf = b""
        while time.time() < limit:
            b = self.ser.read(1)
            if not b:
                continue
            buf = (buf + b)[-2:]
            if buf == MAGIC:
                break
        else:
            raise TimeoutError("экран не ответил")
        head = self.ser.read(2)
        if len(head) < 2:
            raise TimeoutError("обрезанный ответ")
        total = struct.unpack("<H", head)[0]
        rest = self.ser.read(total - 4)
        return MAGIC + head + rest

    def cmd(self, code, payload=b"", wait=True, timeout=None):
        self.ser.write(build(code, payload))
        self.ser.flush()
        if not wait:
            return None
        return parse(self._read_frame(timeout))

    # --- полезные действия --------------------------------------------------

    def resync(self, settle=0.05, clear=True):
        """Закрыть приём картинки, чтобы прошивка снова слушала команды.

        При подключении можно и подождать, и вычистить входной буфер.
        А посреди показа каждая лишняя миллисекунда видна глазом: экран
        на это время остаётся без кадра. Поэтому там settle поменьше,
        а входной буфер не трогаем - его и так чистит drain перед кадром.
        """
        self.ser.write(RESYNC)
        self.ser.flush()
        if settle:
            time.sleep(settle)
        if clear:
            self.ser.reset_input_buffer()

    def info(self, timeout=None):
        _, payload = self.cmd(CMD_INFO, timeout=timeout)
        data = json.loads(payload.decode("utf-8"))
        d = data.get("data", {})
        self.width = d.get("width", W_DEFAULT)
        self.height = d.get("height", H_DEFAULT)
        return data

    def alive(self, timeout=1.5):
        """Отвечает ли экран вообще."""
        self.drain()
        try:
            self.info(timeout=timeout)
            return True
        except Exception:
            return False

    def set_brightness(self, value, wait=True):
        """Яркость подсветки, 0..100.

        wait=False - не ждать ответа. Так надо звать во время показа:
        экран отвечает на команды не всегда, а блокирующее чтение на две
        секунды роняет сторожевой таймер, и кадр не успевает уйти.
        """
        value = max(0, min(100, int(value)))
        return self.cmd(CMD_BRIGHTNESS, bytes([value]), wait=wait)

    def connect(self):
        self.resync()
        data = self.info()
        try:
            self.cmd(CMD_MODE, b"\x00\x03")
        except Exception:
            pass
        return data

    def show_jpeg(self, jpeg, begin=True, presync=False):
        """Отправить готовый кадр.

        begin   - слать ли команду 0x11 перед кадром
        presync - слать ли последовательность ресинхронизации перед кадром

        Ответ на 0x11 НЕ ожидается: экран отвечает на неё не всегда,
        а блокирующее чтение съедает время и роняет сторожевой таймер.
        """
        if jpeg[:2] != b"\xff\xd8":
            raise ValueError("это не JPEG")
        self.drain()
        if presync:
            self.ser.write(RESYNC)
        if begin:
            self.ser.write(build(CMD_IMG_BEGIN))
        self.ser.write(struct.pack("<I", len(jpeg)))
        self.ser.write(jpeg)
        self.ser.flush()

    def show_image(self, pil_image, quality=80, **kw):
        self.show_jpeg(to_jpeg(pil_image, self.width, self.height, quality), **kw)

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass


# --- работа с картинками ----------------------------------------------------

def to_jpeg(pil_image, width=W_DEFAULT, height=H_DEFAULT, quality=80):
    # Панель отдаёт кадр уже в RGB, а convert на том же режиме всё равно
    # делает копию: полмиллиона точек впустую на каждом кадре.
    img = pil_image if pil_image.mode == "RGB" else pil_image.convert("RGB")
    if img.size != (width, height):
        img = img.resize((width, height))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _font(size):
    Image, ImageDraw, ImageFont = _need_pil()
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def make_test_image(width=W_DEFAULT, height=H_DEFAULT, label="ЭКРАН РАБОТАЕТ"):
    Image, ImageDraw, ImageFont = _need_pil()
    img = Image.new("RGB", (width, height), (16, 16, 20))
    dr = ImageDraw.Draw(img)
    bars = [(220, 60, 50), (230, 150, 40), (240, 220, 60),
            (70, 190, 90), (60, 150, 230), (140, 90, 220)]
    bw = width // len(bars)
    for i, c in enumerate(bars):
        dr.rectangle([i * bw, 0, (i + 1) * bw, height // 4], fill=c)
    dr.text((width // 2, height // 2 - 20), label,
            font=_font(56), fill=(255, 255, 255), anchor="mm")
    dr.text((width // 2, height // 2 + 45), "{} x {}".format(width, height),
            font=_font(30), fill=(160, 160, 170), anchor="mm")
    dr.rectangle([2, 2, width - 3, height - 3], outline=(90, 90, 100), width=3)
    return img


def make_clock_image(width=W_DEFAULT, height=H_DEFAULT):
    Image, ImageDraw, ImageFont = _need_pil()
    img = Image.new("RGB", (width, height), (10, 12, 16))
    dr = ImageDraw.Draw(img)
    now = time.localtime()
    dr.text((width // 2, height // 2 - 30), time.strftime("%H:%M:%S", now),
            font=_font(150), fill=(240, 240, 245), anchor="mm")
    dr.text((width // 2, height // 2 + 80), time.strftime("%d.%m.%Y", now),
            font=_font(40), fill=(120, 130, 150), anchor="mm")
    return img


# --- режимы работы ----------------------------------------------------------

STRATEGIES = [
    ("A", "команда 0x11 перед каждым кадром", dict(begin=True, presync=False)),
    ("B", "0x11 только перед первым кадром", dict(begin=False, presync=False)),
    ("C", "ресинхронизация и 0x11 перед кадром", dict(begin=True, presync=True)),
    ("D", "только ресинхронизация, без 0x11", dict(begin=False, presync=True)),
]


def bench(d, seconds_each=5.0):
    """Измерить настоящую пропускную способность порта.

    Оценка по скорости в бодах верна только для настоящего UART.
    У этого экрана собственный USB, и цифра 2000000 скорее всего
    ничего не значит. Поэтому просто гоним кадры и считаем.
    """
    print("\nЗамер пропускной способности. Экран будет мигать, это нормально.")
    print("Каждый заход примерно {:.0f} секунд.\n".format(seconds_each))

    results = []
    for quality in (90, 78, 65, 50):
        img = make_test_image(d.width, d.height, "ЗАМЕР q{}".format(quality))
        jpeg = to_jpeg(img, d.width, d.height, quality)
        size = len(jpeg)

        # прогрев, чтобы первый медленный кадр не портил статистику
        try:
            d.show_jpeg(jpeg, begin=True)
        except Exception:
            pass

        sent, errors = 0, 0
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < seconds_each:
            try:
                d.show_jpeg(jpeg, begin=True)
                sent += 1
            except Exception:
                errors += 1
                if errors > 20:
                    break
        dt = time.perf_counter() - t0

        fps = sent / dt
        kbs = sent * size / dt / 1024
        results.append((quality, size, fps, kbs, errors))
        print("  качество {:2d}: кадр {:5.1f} КБ  ->  {:5.1f} кадр/с, "
              "{:6.0f} КБ/с{}".format(
                  quality, size / 1024, fps, kbs,
                  "  (сбоев: {})".format(errors) if errors else ""))
        d.drain()
        time.sleep(0.3)

    best = max(results, key=lambda r: r[3])
    print("\n  Реальная пропускная способность: около {:.0f} КБ/с".format(best[3]))
    theory = BAUDRATE / 10.0 / 1024
    print("  Оценка по скорости порта дала бы:  {:.0f} КБ/с".format(theory))
    if best[3] > theory * 1.5:
        print("  Значит скорость в бодах фиктивная, упираемся в USB.")
    elif best[3] < theory * 0.7:
        print("  Значит упираемся не в канал, а во что-то ещё —")
        print("  скорее всего в скорость приёма самой прошивки.")

    print("\n  Сколько кадров в секунду можно ставить в layout.json:")
    for quality, size, fps, kbs, _ in results:
        print("    при quality {:2d} — примерно {:.0f}".format(quality, fps * 0.85))
    print("\n  Беру 85 % от измеренного, чтобы остался запас на отрисовку.")
    return results


def diag(d):
    """Перебрать способы отправки и найти тот, при котором экран остаётся живым."""
    print("\nПробую четыре способа отправки по 4 кадра каждый.")
    print("Смотри на экран: он должен непрерывно показывать букву способа.\n")
    results = []
    for letter, desc, kw in STRATEGIES:
        img = make_test_image(d.width, d.height, "СПОСОБ " + letter)
        jpeg = to_jpeg(img, d.width, d.height)
        errors = 0
        # первый кадр всегда с 0x11, дальше по стратегии
        try:
            d.show_jpeg(jpeg, begin=True, presync=kw["presync"])
        except Exception:
            errors += 1
        for _ in range(3):
            time.sleep(DEFAULT_INTERVAL)
            try:
                d.show_jpeg(jpeg, **kw)
            except Exception:
                errors += 1
        time.sleep(0.3)
        ok = d.alive()
        results.append((letter, desc, errors, ok))
        print("  способ {}  {:38s} ошибок отправки: {}, экран отвечает: {}".format(
            letter, desc, errors, "да" if ok else "НЕТ"))
        d.drain()
        time.sleep(0.5)

    good = [r for r in results if r[2] == 0 and r[3]]
    print()
    if good:
        print("Похоже, рабочие способы: " + ", ".join(r[0] for r in good))
        print("Скажи, при каком из них картинка на экране держалась без пропаданий.")
    else:
        print("Ни один способ не отработал чисто. Пришли этот вывод целиком.")


def keep_showing(d, image, interval=DEFAULT_INTERVAL, begin=True):
    print("\nКадр обновляется каждые {:g} с. Ctrl+C для выхода.".format(interval))
    jpeg = to_jpeg(image, d.width, d.height)
    sent, errors, started = 0, 0, time.time()
    try:
        d.show_jpeg(jpeg, begin=True)
        sent += 1
        while True:
            time.sleep(interval)
            try:
                d.show_jpeg(jpeg, begin=begin)
                sent += 1
            except Exception as e:
                errors += 1
                print("  сбой отправки #{}: {}".format(errors, e))
                if errors >= 5:
                    print("  Слишком много сбоев, останавливаюсь.")
                    break
    except KeyboardInterrupt:
        pass
    print("\nОстановлено. Кадров: {}, сбоев: {}, время: {:.0f} с.".format(
        sent, errors, time.time() - started))


HELP = """
  txw818.py версия {v}

    python txw818.py                 тестовая картинка
    python txw818.py картинка.jpg    своя картинка
    python txw818.py --clock         часы

  Кадр переотправляется каждые {i:g} с, иначе экран примерно через {w:g} с
  возвращается к заводской заставке. Выход по Ctrl+C.

  Дополнительно:

    --bench          измерить реальную скорость порта
    --diag           перебрать способы отправки и найти рабочий
    --interval 2.5   свой интервал переотправки в секундах
    --nobegin        не слать команду 0x11 перед каждым кадром
    --once           отправить один раз и выйти
    --ports          список COM-портов
    --off / --on     подсветка
    COM3             указать порт вручную первым словом
""".format(v=VERSION, i=DEFAULT_INTERVAL, w=WATCHDOG_SEC)


def main():
    args = sys.argv[1:]
    print("txw818.py версия {}".format(VERSION))

    if args and args[0] in ("--help", "-h", "/?"):
        print(HELP)
        return

    if args and args[0] == "--ports":
        list_ports()
        return

    if args and (args[0].upper().startswith("COM") or args[0].startswith("/dev/")):
        port = args[0]
        args = args[1:]
    else:
        port = find_port()
        if port is None:
            print("Не нашёл экран автоматически (искал VID {:04X}, PID {}).\n"
                  .format(DEVICE_VID,
                          " или ".join("{:04X}".format(x)
                                       for x in DEVICE_PIDS)))
            list_ports()
            print("Запусти ещё раз с портом первым словом, например:")
            print("    python txw818.py {}".format(PRIMER_PORTA))
            return
        print("Экран найден на порту {}.".format(port))

    interval = DEFAULT_INTERVAL
    if "--interval" in args:
        i = args.index("--interval")
        try:
            interval = float(args[i + 1].replace(",", "."))
            del args[i:i + 2]
        except (IndexError, ValueError):
            print("После --interval нужно число, например: --interval 2.5")
            return

    once = "--once" in args
    do_diag = "--diag" in args
    do_bench = "--bench" in args
    begin = "--nobegin" not in args
    args = [a for a in args if a not in ("--once", "--diag", "--bench", "--nobegin")]
    option = args[0] if args else None

    d = Display(port)
    try:
        data = d.connect()
    except Exception as e:
        print("Экран не ответил. Причина: {}\n".format(e))
        print("Что попробовать:")
        print("  1. Закрыть родную программу, включая значок в трее.")
        print("  2. Выключить компьютер, вынуть кабель питания,")
        print("     подождать полминуты, включить снова.")
        print("  3. Проверить другой порт: python txw818.py --ports")
        d.close()
        sys.exit(1)

    print("Экран отозвался:\n")
    print(json.dumps(data.get("data", data), indent=2, ensure_ascii=False))

    if option == "--off":
        d.set_brightness(0)
        print("\nПодсветка выключена.")

    elif option == "--on":
        d.set_brightness(90)
        print("\nПодсветка включена.")

    elif do_bench:
        d.set_brightness(90)
        bench(d)

    elif do_diag:
        d.set_brightness(90)
        diag(d)

    elif option == "--clock":
        d.set_brightness(90)
        step = min(interval, 1.0)
        print("\nЧасы обновляются каждые {:g} с. Ctrl+C для выхода.".format(step))
        errors = 0
        try:
            first = True
            while True:
                try:
                    d.show_image(make_clock_image(d.width, d.height),
                                 begin=True if first else begin)
                    first = False
                except Exception as e:
                    errors += 1
                    print("  сбой отправки #{}: {}".format(errors, e))
                    if errors >= 5:
                        break
                time.sleep(step)
        except KeyboardInterrupt:
            pass
        print("\nОстановлено.")

    else:
        if option:
            Image, _, _ = _need_pil()
            try:
                picture = Image.open(option)
            except Exception as e:
                print("\nНе удалось открыть файл {}: {}".format(option, e))
                d.close()
                sys.exit(1)
        else:
            picture = make_test_image(d.width, d.height)

        d.set_brightness(90)
        if once:
            d.show_image(picture)
            print("\nКадр отправлен, выхожу. Пропадёт примерно через {:g} с."
                  .format(WATCHDOG_SEC))
        else:
            keep_showing(d, picture, interval, begin=begin)

    d.close()


if __name__ == "__main__":
    main()
