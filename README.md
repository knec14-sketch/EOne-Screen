[Русский](README.ru.md) · **English**

# EOne screen — an open replacement for the Jungle Leopard stock software

An open replacement for the stock software of the **Jungle Leopard Pro
Flow 360** and **Pro Flow 240** water-cooler screens (TXW818 controller,
ST7701S panel, 960×480, over a COM port).

The program draws a monitoring panel from a JSON description and pushes
it to the screen as JPEG frames. Plus a window where all of it is set up:
a theme gallery, a layer editor, sensors, weather.

**Runs on Windows and on Linux.** Both have been used on real hardware —
Linux on CachyOS with KDE Plasma 6 and Wayland, with the screen driven
over `/dev/ttyACM0` at 30 frames a second.

**Speaks seven languages:** Russian, English, Spanish, German, French,
Portuguese and Italian. The window and the panel can speak different
ones — the window is where you work, the panel is what other people see.

![Home page](snimki/home-night.png)

---

## What it does

**Shows the hardware.** Load and temperature of the processor and the
graphics card, memory, disks, network, uptime. Nvidia is read through
`nvidia-smi`, AMD and Intel through LibreHardwareMonitor.

**Shows the weather.** Five ready-made services plus the option to plug
in any other one. The sky on the panel changes by itself: rain, snow,
blizzard, fog, storm, frost, heat. Day and night flow into each other
by the real sunrise and sunset in your city.

**Lets you rearrange all of it.** A layer editor with a canvas, snapping,
undo and a clipboard — a theme can be shared as an archive, or a single
layer through the clipboard.

**Does not eat the processor.** A theme of 97 layers runs at 30 frames
per second and costs about half a per cent of the processor. How that is
done is at the end of this file.

| | |
|---|---|
| ![Rain during the day](snimki/weather-rain.png) | ![Themes](snimki/themes.png) |
| ![Machine checkup](snimki/checkup.png) | ![Units](snimki/units.png) |

---

## Installing

You need **Windows** and **Python 3.9 or newer**
([python.org](https://www.python.org/downloads/) — tick «Add python.exe
to PATH» while installing). Linux is [further down](#linux).

```
pip install pillow psutil pyserial pythonnet numpy pystray
```

The first three and `tkinter` (comes with Python) are required. The rest
are optional: without `pythonnet` there is no processor temperature,
without `pystray` no icon next to the clock, without `numpy` the soft
colour transitions are worked out more slowly.

Then just start it:

```
app.bat
```

It asks Windows for administrator rights and opens the window. On the
first run the program looks the machine over by itself — which sensors
answer, whether the screen is visible on a COM port, whether there is
internet and whether the weather service replies — and says what is
missing and what to do about it. The same page lives in the settings,
section **Looking the machine over**, and can be opened at any time.

The rights are needed for exactly one thing — the processor temperature:
Windows does not let ordinary programs read the processor registers.
Everything else works without them.

**Then — from the shortcut.** In the settings, section **Startup**, tick
«A shortcut on the desktop»: the program makes one with its own icon,
and it starts the same way, with the rights. After that neither the
folder nor the command line is needed.

### When `start.bat` is needed

Only for one thing the window cannot do: Windows marks files downloaded
from the internet, and while that mark is on the `.dll` files, .NET
refuses to load the sensor library. `start.bat` strips the mark and then
does the same looking-over in the console.

If the machine checkup says the library is «marked as downloaded from
the internet» — run `start.bat` once. Otherwise it is not needed at
all.

---

## How to use it

### The first run

The program looks the machine over itself and shows what it found:
libraries, rights, the sensor library files, the hardware, the sensors,
the screen on the port, the weather. Next to every trouble it says what
to do, and where a press is enough there is a button.

The window is laid out simply: three sections at the top.

### Home

Here you see the same thing that goes to the water-cooler screen, only
without the animation — the window deliberately spends nothing on it.

| | |
|---|---|
| **Turn the screen on** | start or stop the output |
| **Pause** | hold it without closing the port |
| **Restart** | reopen the port if the picture went wrong |
| the slider on the right | backlight brightness |

Below that — **What to show**. Two rows, and they are about different
things:

* **Day and night** — when the screen shows the day view and when the
  night one. «By the sun» takes the real sunrise and sunset in your city.
* **Weather on the screen** — you can see how the theme behaves in
  a storm or a blizzard without waiting for one. The real forecast stays
  where it is; «Forecast» puts everything back.

If a theme knows neither day and night nor weather, this block is not
shown at all.

### Themes

A gallery of everything lying next to the program. On a theme card:

| | |
|---|---|
| **To the screen** | make this theme the current one |
| **Edit** | open it in the editor |
| **Rename** | the folder on disk is renamed together with the theme |
| the icons on the right | description, copy, pack into an archive, showcase picture, remove |

A theme can be sent to another person whole: «pack» puts everything it
refers to into a single archive. Back the other way — the «From an
archive…» button.

### The editor

The list of layers on the left, an exact preview of what will go to the
screen in the middle, the properties of the chosen layer on the right.

* move with the mouse, the arrows (Shift — by ten dots) or the X and Y
  fields;
* the magnet pulls to the edges and centres of the neighbours, Alt turns
  it off for the moment;
* several layers at once — Ctrl+click or Shift+click in the list;
* Ctrl+Z to undo, Ctrl+C and Ctrl+V to copy and paste — including into
  another theme or to another person in a message;
* the **night / transition / day** switch at the top: edits go into
  exactly the view that is chosen.

![The editor](snimki/editor.png)

Every field of a theme can be set here; the editor shows what each
one does as you hover over it.

### Settings

| section | what is there |
|---|---|
| **Program appearance** | light or dark window, language |
| **Units and time** | °C or °F, km/h, m/s or mph, 12 or 24 hours, order of the numbers in the date, first day of the week |
| **Startup** | a shortcut on the desktop, starting with Windows, hiding to the tray |
| **Sensors** | what to poll and what of it is being read right now |
| **Weather and place** | city, forecast service, your own source |
| **Performance** | frame rate, quality, antialiasing, putting the frame together in threads |

The frame rate, quality and antialiasing settings take effect **at once**,
nothing needs restarting.

---

## Linux

It works. A volunteer ran it on **CachyOS with KDE Plasma 6 and
Wayland**, an Intel i5-13600KF and a Radeon RX 7900 XT: the window, the
temperatures, the weather, the themes, the tray icon and the physical
screen itself, at about 28 frames a second against a target of 30. The
[full report is in issue #1][issue1].

There is no Linux machine here, so anything not yet run on one is
marked as such below.

```
pip install pillow psutil pyserial numpy pystray
python app.py
```

`pythonnet` is not needed on Linux at all, and neither is `start.bat` —
it clears a mark that only exists on Windows.

**Getting at the screen.** Reading the serial port is granted by a
group: `dialout` on Debian and Ubuntu, `uucp` on Arch and its relatives
(CachyOS, Manjaro).

```
sudo usermod -a -G uucp $USER      # on Debian and Ubuntu: dialout
```

Then log out and back in.

**The tray icon.** It needs AppIndicator, which is installed by the
system rather than by `pip`:

```
sudo pacman -S --needed libappindicator python-gobject python-cairo
```

If you work inside a virtual environment, create it with
`--system-site-packages`, or the `gi` module stays invisible and there
is no icon:

```
python -m venv --system-site-packages .venv
```

The program runs without the icon too — the cross then closes it
instead of hiding it.

Everything that depends on the system lives in one file, `sistema.py`:

| | Windows | Linux |
|---|---|---|
| temperatures | LibreHardwareMonitor, needs admin rights | `/sys/class/hwmon`, no rights needed |
| graphics card load, memory, power | the sensor library | `/sys/class/drm` |
| processor name | registry | `/proc/cpuinfo` |
| graphics card name | WMI | `nvidia-smi`, otherwise `lspci` |
| units and formats | registry | the locale |
| shortcut and autostart | WScript.Shell and the registry | `.desktop` files |
| the sensor library | four `.dll` files | not needed at all |

**Devices.** Two are recognised: `33C3:7788` (Flow 360) and `33C3:7792`
(Flow 240, the HONGTAI panel). The second was added after it was
confirmed on real hardware — the protocol turned out to be the same.
Other ids are deliberately left out until somebody confirms them the
same way.

**Not yet run on real hardware:** the graphics-card load, memory and
power readings from `/sys/class/drm` — the parsing is checked against
fabricated files, not against a real card; autostart after a reboot;
and the shortcut in the applications menu. If any of those works or
does not on your machine, [open an issue][issues].

Run `python проверки/linux.py` to see the parsing checks.

[issue1]: https://github.com/knec14-sketch/EOne-Screen/issues/1
[issues]: https://github.com/knec14-sketch/EOne-Screen/issues

---

## The sensor library

For temperatures you need **exactly four files** from the
[LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases)
archive, put next to the program:

```
LibreHardwareMonitorLib.dll
HidSharp.dll
System.Memory.dll
System.Runtime.CompilerServices.Unsafe.dll
```

The other two dozen assemblies in the archive belong to the
LibreHardwareMonitor window itself. Checked by trying every combination:
with the four files exactly as many sensors are found (118) as with all
twenty-five.

Anyone whose graphics card is **not Nvidia** needs a fifth file as well —
`System.Numerics.Vectors.dll`: without it the library does not open the
graphics card section.

---

## Weather

| service | key | note |
|---|---|---|
| Open-Meteo | not needed | the default; gives sunrise and sunset too |
| met.no | not needed | the Norwegian Meteorological Institute |
| wttr.in | not needed | closest to what the Windows widget shows |
| OpenWeatherMap | needed | the key is given out on registration |
| WeatherAPI | needed | the same |
| your own source | as it turns out | your own address, the fields are pointed at with the mouse |

About «the same as Windows», honestly: the Windows widget takes its
weather from MSN Weather, and that gives no open access — it answers with
a refusal without a key that is built into the system itself. Putting
somebody else's key into an open program is not right. The difference
between services is a degree or two.

You plug in your own service like this: write the address (it may
contain `{lat}`, `{lon}` and `{key}`), press «Ask the service» — the
program asks it once and takes the answer apart into paths — and then
pick from the lists where the temperature is, where the wind is, where
the sunrise is. You do not have to read somebody else's JSON by hand.

---

## Languages

Seven: Russian, English, Spanish, German, French, Portuguese, Italian.
Switched in the settings, applied at once.

**The window** and **the theme** have separate settings. The window is
where you work; the panel hangs where other people see it, and the two
may well need different languages. The theme setting governs everything
that belongs to the theme — the weather words, the wind unit, the layer
names in the editor — and defaults to following the window.

Each language lives in its own file: `yazyk_es.py` and its kin, holding
the window dictionary, the weather words and their abbreviations. The
dictionary key is the Russian string itself, so a missing line falls back
to English and then to Russian — a half-finished translation breaks
nothing.

> **The Spanish, German, French, Portuguese and Italian translations were
> made with the help of AI and have not been checked by native speakers.**
> Russian and English are the author's own. If you speak one of the five
> and see something wrong or merely clumsy, please
> [open an issue][issues] — a correction from someone who speaks the
> language is worth more than any amount of careful machinery.

---

## How it is built

```
panel.py     putting a frame together from layers, caching, output to the screen
sensors.py   polling the hardware and the weather in background threads
txw818.py    the screen protocol: port, commands, sending JPEG
edinicy.py   degrees, clock, date, first day of the week

app.py       the window: three sections at the top, page switching, tray
home.py      home: a mirror of the screen, on/off, brightness, day/night, weather
pages.py     themes and settings
editor.py    the layer editor: canvas, properties, undo, clipboard, magnet
look.py      the look of the window: palettes, fonts, icons, cards
themes.py    finding themes, metadata, previews, copies, archive exchange
prefs.py     program settings, autostart, shortcut
papka.py     where the program lives
yazyk.py     Russian and English
start.py     looking the machine over before the first run
```

### Why it is fast

The layers are split into **runs**, and each has its own fingerprint.
While the fingerprint does not change, the run is taken from memory. Only
what is visible on that run goes into the fingerprint: a clock without
seconds is redrawn once a minute, not thirty times a second.

Numbers are compared with the precision they are seen at. `{cpu_load:.0f}`
is compared as whole numbers.

Background frames are taken apart once and kept compressed with zlib;
what has been taken apart goes into `.кадры/` inside the theme, so the
first start takes a few seconds and the next ones take a fraction of one.
Empty frames are neither stored nor composited at all.

Measured on the «Skywatch» theme, 97 layers, 30 fps,
antialiasing 2:

| | |
|---|---|
| night, transition, day | 30.0 fps everywhere |
| a calm frame | 6.7 ms at night, 9.2 in the day, out of a budget of 33 |
| load | 16 % of one thread = 0.5 % of the processor |
| memory | 369 MB, 276 of it background frames |

The engineering notes are in [ENGINE.md](ENGINE.md).

---

## Licence

[CC BY-NC-SA 4.0](LICENSE.en) — you may use, rework and pass it on, you
may not make money from it, what you rework goes out on the same terms
with the author named.

The LibreHardwareMonitor library belongs to its authors and is
distributed under its own licence, MPL 2.0.

The "Skywatch" theme carries its own typeface — **Project Space** by Ver
Wave, under the SIL Open Font License 1.1. It lives in
`themes/Skywatch/fonts/` together with the licence text, so the theme
looks the same on any machine without installing anything.

Author — **EOne**.
