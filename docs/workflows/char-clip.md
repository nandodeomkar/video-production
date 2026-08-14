# Char-Clip Workflow

Stylize an image — or a short section of any online video — into **character
art**: every cell of the picture rebuilt out of typed characters. Two
independent choices shape the result: a **style** (which characters) and a
**fill** (whether/how colour is kept).

## Styles

| Style | What it does | Look |
|-------|--------------|------|
| `ascii` | Each cell picks a **different** character by brightness (`@%#*+=-:. `) | Classic terminal ASCII art |
| `mono`  | One repeated character, drawn only where the cell is dark | Stippled / halftone, e.g. a field of `+` |
| `hatch` | Stroke glyphs (`X / - .`) chosen by brightness band | Sketched, pen-hatched shading |
| `custom`| Maps brightness to an arbitrary user-supplied character ramp (passed via the `CHAR` argument) | Custom brightness-to-character shading |

`ascii` and `custom` carry the image in the glyph choice itself; `mono` and `hatch` carry it in density.


## Fill — colour and scene recognizability

`style` decides the characters; `fill` decides what goes *behind* them. This is
the biggest lever for whether a scene actually reads.

| Fill | What it does | Best for |
|------|--------------|----------|
| `none` | Glyphs in a flat ink colour on a dark background. Pure character art. | Stylized / abstract look |
| `tint` | Each cell washed with a dimmed version of its own colour, glyph on top. | Scene as solid colour blocks |
| `image` | The dimmed real frame shows through behind the glyphs. | **Most recognizable** — faces and scenes read clearly |

Why it matters: with `none`, a busy scene becomes an even field of glyphs and is
hard to parse. `tint` and `image` bring colour back, so the brain can read the
scene instantly. `image` keeps the most facial/edge detail; `tint` is slightly
more abstract.

**Limit to know:** even `image` can't make a face *photo-accurate* — each cell
collapses sub-cell detail to one block. Smaller `CELL` values sharpen faces at
the cost of render time and a finer, less chunky character texture.

## Two ways to use it

### A single image

```
pipelines\char-clip\stylize-image.cmd  INPUT OUTPUT [STYLE] [CELL] [CHAR] [FILL] [NORMALIZE]
```

Example — colour character art with the real image showing through:

```
pipelines\char-clip\stylize-image.cmd photo.jpg photo_art.png ascii 10 + image on
```

`INPUT` / `OUTPUT` may be relative or absolute. The output's parent folder is
created if missing.

### A video section

```
pipelines\char-clip\run-all.cmd  URL START END CLIPNAME [STYLE] [CELL] [CHAR] [FILL] [NORMALIZE]
```

Example — a recognizable colour clip from a 4-second section:

```
pipelines\char-clip\run-all.cmd "https://youtu.be/XXXX" 00:01:12 00:01:16 newsclip1 ascii 10 + image on
```

Result: `Output\newsclip1_char.mp4`

`START` / `END` accept `HH:MM:SS` or plain seconds. `CLIPNAME` becomes the
work-folder name and the output filename prefix.

> **Paste the bare `youtu.be/<id>` URL.** A `?si=...` share suffix (added by
> YouTube's Copy-link button) breaks `cmd` argument parsing — strip it.

## What the video pipeline does

```
YouTube URL + start/end timestamp
        |
   [1] download    -> Work/<clip>/source.mp4        trimmed, up to 1080p
   [2] extract     -> Work/<clip>/frames/f_*.png     30fps PNG sequence, 1920x1080
                      Work/<clip>/audio.m4a          original audio (copied)
   [3] charize     -> Work/<clip>/charized/f_*.png   each frame -> character art
   [4] stitch      -> Output/<clip>_char.mp4         final video + audio
```

Stages 1 and 2 are **shared with the tiled-clip pipeline** — downloading and
frame extraction are identical regardless of style, so `run-all.cmd` calls the
tiled-clip implementations directly. Stages 3 and 4 are char-clip's own.

## Running stages individually

| Stage | Command | Produces |
|-------|---------|----------|
| 1 | `..\_shared\1-download.cmd URL START END CLIPNAME` | `Work\<clip>\source.mp4` |
| 2 | `..\_shared\2-extract-frames.cmd CLIPNAME` | `Work\<clip>\frames\`, `audio.m4a` |
| 3 | `3-charize-frames.cmd CLIPNAME [STYLE] [CELL] [CHAR] [FILL] [NORMALIZE]` | `Work\<clip>\charized\` |
| 4 | `4-stitch.cmd CLIPNAME` | `Output\<clip>_char.mp4` |

## Tuning

All knobs are command-line arguments — no file edits needed.

- **`STYLE`** — `ascii` | `mono` | `hatch` | `custom` (default `ascii`).
- **`CELL`** — grid cell size in source pixels (default `12`). Bigger = coarser,
  chunkier art and **faster** rendering; smaller = finer detail, sharper faces.
- **`CHAR`** — the stipple character for `mono` style (default `+`), OR the entire custom character ramp string for `custom` style (e.g. `".:-+*#%@"` or a math ramp `"·÷±×"`). If the ramp does not end with a space, a space is automatically appended so highlights fade cleanly to a blank background canvas. Ignored by `ascii` and `hatch`. *Note: When using the `.cmd` wrappers, avoid using standard Command Prompt delimiters (such as spaces, commas `,`, or equal signs `=`) inside your custom ramp string because they split Batch arguments. To use those characters, invoke the Python engine `char_render.py` directly.*
- **`FILL`** — `none` | `tint` | `image` (default `none`). See the Fill section
  above — `image` is the most recognizable.
- **`NORMALIZE`** — `on` | `off` (default `off`). Auto-stretches each frame's
  brightness before stylizing. Turn `on` for dark footage so colours render
  vividly instead of muddy.

Deeper look-tuning lives at the top of `engines\charart\char_render.py`:

- `ASCII_RAMP` — the dark-to-light character ramp. Longer = smoother shading.
  A trailing space means highlights go blank; a trailing `.` inks every cell.
- `MONO_THRESHOLD` — brightness cutoff for `mono` (default 128). Lower = sparser
  ink (only deep shadows); higher = inkier.
- `HATCH_BANDS` — the `(upper-bound, glyph)` brightness bands for `hatch`.
- `TINT_BG_FACTOR` / `IMAGE_BG_FACTOR` — how much the cell background is dimmed
  in `tint` / `image` fill. Lower = darker background, glyphs pop more.
- `COLOR_FLOOR` — minimum brightness a glyph's colour is lifted to (keeps very
  dark cells from vanishing).
- `NORM_LOW_PCT` / `NORM_HIGH_PCT` — percentiles mapped to black/white by
  `--normalize`.
- `--ink` / `--bg` — for `fill=none`, `char_render.py` accepts `R,G,B` colours
  directly (e.g. `--ink 0,255,0 --bg 0,0,0` for green-on-black). The `.cmd`
  wrappers use defaults; call `char_render.py` directly to override.
- `--fontscale` — glyph size within the cell. Raise it if glyphs look too
  small / sparse for the cell.

## Render cost

Charizing is pure NumPy and fast — far cheaper than the tiled-clip mosaic.
Stage 3 renders frames in parallel (`CONCURRENCY=8`, editable at the top of
`3-charize-frames.cmd`). A 4-second clip (~120 frames at 30fps) charizes in well
under a minute on a multi-core machine.

## Components

| Path | Role |
|------|------|
| `engines\charart\char_render.py` | the engine: stylizes one image to character art |
| `pipelines\char-clip\stylize-image.cmd` | single-image entry point |
| `pipelines\char-clip\3-charize-frames.cmd` | Stage 3: charize every frame |
| `pipelines\char-clip\4-stitch.cmd` | Stage 4: stitch charized frames + audio |
| `pipelines\char-clip\run-all.cmd` | runs all 4 stages end to end |
| `pipelines\char-clip\render-frames.ps1` | parallel frame renderer (Stage 3 helper) |
| `pipelines\_shared\1-download.cmd` / `2-extract-frames.cmd` | shared stages 1-2 |

## Folders

- `Work\<clip>\` — per-clip intermediate files (source, frames, charized,
  audio). Safe to delete after the final video is produced.
- `Output\` — finished `<clip>_char.mp4` files.

## Verifying a run

- Single image: open the `OUTPUT` file — it should read as character art.
- Video: frame count in `Work\<clip>\charized\` should be ~30 x clip-seconds.
- Open a few PNGs in `Work\<clip>\charized\` — they should look stylized.
- Play `Output\<clip>_char.mp4` and confirm motion + audio.
