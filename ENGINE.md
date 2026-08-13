[Русский](УСТРОЙСТВО.md) · **English**

# How the engine works

This document is about «why it is like this, and not otherwise». Short,
to-the-point notes stayed in the code; everything long that explains
a reason lives here.

Worth reading before your first edit of `panel.py`. Almost everything
that looks strange in it is what holds thirty frames per second, and it
comes off silently: the picture stays the same, and the panel starts to
stutter.

---

## Runs and fingerprints

Layers are split into **runs** of three kinds:

| kind | what is in it |
|---|---|
| `image` | pictures, composited ready-made |
| `live` | have a `loop`, depend on time |
| `draw` | calm ones |

Each run has its own **fingerprint**. While it does not change, the run
is taken from memory instead of being drawn again. Into the fingerprint
go:

* **the share of the transition** — but a separate one for every layer
  with a `day` section. Once a layer has arrived at its day view, the run
  freezes, even if the overall share of day is still creeping;
* **time** — only for `live`, and in steps of `loop.fps`;
* **sensor readings** — but only those visible on that run.

Numbers are compared with the precision they are seen at. `{cpu_load:.0f}`
is compared as whole numbers, and a number that takes part in the picture
(the fill of a ring, a `react` value) down to thousandths. That is why
a clock without seconds is refreshed once a minute and not thirty times
a second.

An empty run — one where every layer is transparent — does not get
a canvas at all. There are many of those: all the decorations while it is
not their half of the day.

---

## A loop has its own frame rate

`loop` has **its own rate**, `loop.fps`. A cloud creeping 33 dots in
46 seconds moves by a hundredth of a dot at thirty frames per second —
and all 25 layers of the run were being redrawn for that.

Clouds were given 5, stars 10, lightning none — a flash is abrupt. That
took two thirds off the cost of the live layers: 5.3 ms against 1.9.

**The rate of a picture layer must match the rate it was shot at.** Set
it lower and a frame hangs on the screen longer than it should, and even
rotation reads as a stutter. The moon had 12 with 600 frames shot at 30:
a turn stretched from 20 seconds to 50, and every frame was shown two and
a half times over.

The check is simple: the number of frames in the folder divided by the
rate of the layer must give the length of the original clip.

---

## The mask by the home position

A layer's mask is worked out at its **home** position
(`Panel._mask_home`) — where the layer is seen at its best, not where it
happens to be right now.

If it were worked out at the current one, a moving layer passes dozens of
whole values of `x`, and 600 frames would be prepared again for every
one of them. That is exactly why the transition once ground to a halt.

---

## Storing frames

Background frames are taken apart once and kept compressed with zlib.
Getting a frame out takes 0.7 ms. WEBP would squeeze twice as well, but
a frame takes three times longer to get out of it: Pillow takes it apart
with a video decoder.

An empty frame is neither stored nor composited at all. The meteors have
827 such frames out of 1000 — 6 ms per frame was going on them for
nothing.

**The cache on disk.** What has been taken apart goes into `.кадры/`
inside the theme. The first start takes 3–25 seconds, the next ones 0.2.
The file name comes from the settings of the layer, and the fingerprint
of the sources lives inside the file. While the sources are in place they
decide; if they have been taken away, the cache is good on its own, and
a theme can be carried around without its source frames.

The folder starts with a dot: it goes into neither a copy nor an archive,
and not into the repository either. Files that have outlived their use
are not removed by themselves; the folder is worth clearing by hand every
few edits.

---

## The order the variants are applied in

`apply_variants`: `day` first, then `loop`, then `react`.

**The reaction comes last and overrides the day.** Dim a decoration with
opacity in `day` — and `react` lifts it straight back up: the sun shines
at night, clouds drift in the dark. The right way is to dim it not with
opacity but in the sensor value itself. That is why the weather shares
are already multiplied by the share of day, and why there is a separate
`sky_sun` for the sun.

---

## Weather and the shares of the sky

A weather code is a number of a state, not a scale: there is no middle
between «clear» and «storm», you cannot pull along it smoothly. The
sensors break it out into the shares `sky_clear`, `sky_clouds`,
`sky_grey`, `sky_rain`, `sky_snow`, `sky_storm`, `sky_fog` and give them
**as they are**, with no tie to the day.

The panel is what ties them — `Panel._sky_by_day`. It alone knows which
share of day it is drawing right now: the menu can be told «always
night», and it does not matter that the sun outside is high. While the
sensors were doing this, rain fell on the night theme and there was not
a single star.

`sky_day` and `sky_night` are **not** the share of day. They are steps at
the very edges of the day (`GATE_EDGE = 0.12`). In the middle of the
transition both are zero, so there are only planets and blocks on the
screen — no stars, no clouds. Done both for the look and for the speed:
otherwise the frame did not fit into the time it was given.

---

## Live settings

`fps`, `quality`, `supersample`, `pack_frames`, the length of the
transition and the number of threads are properties that read the
description **on every frame**. Change it in the settings and a running
panel sees it at once.

Do not turn them back into fields: the setting would stop working while
looking as though it does.

---

## Shrinking after supersampling

Done only over the occupied part of the canvas (`Panel._shrink`), with
the crop aligned to multiples of `k`. Mathematically that is exactly the
same as shrinking the whole thing, and it has been verified for antialiasing from 1 to 4.

---

## Putting a frame together in several threads

Runs know nothing of each other, so the stale ones can be built at once
and composited onto the canvas in order afterwards. The picture comes out
the same down to the last dot — that has been checked.

The gain in time is small and on a fast machine it is lost in the spread
between identical runs. The setting exists for weak machines; no gain can
be promised from it.

---

## How to make it pretty without killing the speed

* **Draw effects into frames beforehand** and put them in as a single
  `image` layer. A hundred separate drops as layers stretched a frame
  from 33 ms to 250.
* **A gradient (`fill2`) is expensive by area.** A rectangle is filled
  with no mask at all; an ellipse and a rounded one with a mask over
  their own place, not over the whole canvas.
* **A `day` section drags a layer into the crossfade.** Decorations do not
  need it — dim them through `react` on `sky_day` / `sky_night`.

---

## How to measure speed

Only in the real `Runner` loop with a stub instead of the screen.
Isolated measurements of `render()` lie: 10 ms in a test, 45 in real
life.

One run proves nothing: on a live machine the spread between identical
runs reaches a tenth. Repeat and take the best — it is the least spoiled
by other work.

---

## A trap with names

The module `themes.py` and the folder `themes` lie side by side. That
works: Python prefers the module to a folder with no `__init__.py`.

**Do not create an `__init__.py` in `themes/`** — the program will stop
starting.
