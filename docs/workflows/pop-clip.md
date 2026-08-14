# Pop-Clip Workflow

Stylize an image — or a short section of any online video — into **pop-art /
comic-book style**: flat saturated colour, halftone dots in the shadows, and
bold black inked outlines.

## What the look is made of

Every frame runs through five passes:

| Pass | Effect |
|------|--------|
| Punch    | Saturation + contrast boosted so colour reads loud |
| Smooth   | Edge-preserving blur flattens skin/fabric micro-texture |
| Quantize | Colours reduced to a small palette via k-means — flat comic colour |
| Halftone | Shadow regions get a grid of black dots — the newsprint texture |
| Outline  | Major edges inked bold black, drawn on top |

The original hues are kept (then boosted), so scenes and faces stay
recognizable — it reads as a comic adaptation of the real footage, not a
random recolour.

## Two ways to use it

### A single image

```
pipelines\pop-clip\stylize-image.cmd  INPUT OUTPUT [COLORS] [SHADOW_CUTOFF] [SATURATION] [CELL] [NORMALIZE]
```

Example:

```
pipelines\pop-clip\stylize-image.cmd photo.jpg photo_pop.png 8 100 1.6 6 on
```

`INPUT` / `OUTPUT` may be relative or absolute. The output's parent folder is
created if missing.

### A video section

```
pipelines\pop-clip\run-all.cmd  URL START END CLIPNAME [COLORS] [SHADOW_CUTOFF] [SATURATION] [CELL] [NORMALIZE]
```

Example — a 4-second section:

```
pipelines\pop-clip\run-all.cmd "https://youtu.be/XXXX" 00:01:12 00:01:16 newsclip1
```

Result: `Output\newsclip1_popart.mp4`

`START` / `END` accept `HH:MM:SS` or plain seconds. `CLIPNAME` becomes the
work-folder name and the output filename prefix.

> **Paste the bare `youtu.be/<id>` URL.** A `?si=...` share suffix (added by
> YouTube's Copy-link button) breaks `cmd` argument parsing — strip it.

## What the video pipeline does

```
YouTube URL + start/end timestamp
        |
   [1] download    -> Work/<clip>/source.mp4        trimmed, up to 1080p
   [2] extract     -> Work/<clip>/frames/f_*.png     30fps PNG sequence
                      Work/<clip>/audio.m4a          original audio (copied)
   [3] popart      -> Work/<clip>/popart/f_*.png     each frame -> pop-art
   [4] stitch      -> Output/<clip>_popart.mp4       final video + audio
```

Stages 1 and 2 are **shared with the tiled-clip and char-clip pipelines** —
`run-all.cmd` calls the tiled-clip implementations directly. Stages 3 and 4
are pop-clip's own.

## Running stages individually

| Stage | Command | Produces |
|-------|---------|----------|
| 1 | `..\_shared\1-download.cmd URL START END CLIPNAME` | `Work\<clip>\source.mp4` |
| 2 | `..\_shared\2-extract-frames.cmd CLIPNAME` | `Work\<clip>\frames\`, `audio.m4a` |
| 3 | `3-popart-frames.cmd CLIPNAME [COLORS] [SHADOW_CUTOFF] [SATURATION] [CELL] [NORMALIZE]` | `Work\<clip>\popart\` |
| 4 | `4-stitch.cmd CLIPNAME` | `Output\<clip>_popart.mp4` |

## Tuning

All knobs are command-line arguments — no file edits needed.

- **`COLORS`** — palette size, the number of k-means colour clusters
  (default `8`). Fewer = bolder, blockier, more abstract; more = subtler.
- **`SHADOW_CUTOFF`** — brightness 0-255 below which halftone dots appear
  (default `100`). Lower = dots only in deep shadow; higher = dots spread into
  the midtones for a heavier comic texture.
- **`SATURATION`** — saturation boost factor (default `1.6`). Higher = louder,
  more pop-art colour.
- **`CELL`** — halftone dot-grid cell size in pixels (default `6`). Bigger =
  larger, sparser dots.
- **`NORMALIZE`** — `on` | `off` (**default `on`**). Auto-stretches each
  frame's brightness before stylizing. This defaults **on** because pop-art's
  colour quantization collapses into muddy near-blacks on dark footage —
  normalizing first keeps colours vivid and the scene readable. Pass `off`
  only for footage that is already bright and well-exposed.

Deeper look-tuning lives in constants at the top of
`engines\popart\popart_render.py`:

- `CONTRAST_FACTOR` — contrast stretch strength in the Punch pass.
- `BILATERAL_DIAMETER` / `BILATERAL_SIGMA` — Smooth pass blur strength.
- `KMEANS_ITERATIONS` / `KMEANS_EPSILON` / `KMEANS_ATTEMPTS` — quantization
  quality vs. speed.
- `HALFTONE_DOT_RATIO` — dot radius as a fraction of the cell.
- `DOG_BLUR_NARROW` / `DOG_BLUR_WIDE` / `EDGE_BASE_THRESHOLD` /
  `OUTLINE_DILATE` — outline edge detection and line thickness.

## Render cost

Pop-arting is pure cv2/numpy. The k-means quantization is the heaviest pass.
Stage 3 renders frames in parallel (`CONCURRENCY=8`, editable at the top of
`3-popart-frames.cmd`). A 4-second clip (~120 frames at 30fps) renders in
roughly 1-3 minutes on a multi-core machine.

## Components

| Path | Role |
|------|------|
| `engines\popart\popart_render.py` | the engine: stylizes one image to pop-art |
| `engines\popart\test_popart_render.py` | unit tests for the engine's passes |
| `pipelines\pop-clip\stylize-image.cmd` | single-image entry point |
| `pipelines\pop-clip\3-popart-frames.cmd` | Stage 3: pop-art every frame |
| `pipelines\pop-clip\4-stitch.cmd` | Stage 4: stitch pop-art frames + audio |
| `pipelines\pop-clip\run-all.cmd` | runs all 4 stages end to end |
| `pipelines\pop-clip\render-frames.ps1` | parallel frame renderer (Stage 3 helper) |
| `pipelines\_shared\1-download.cmd` / `2-extract-frames.cmd` | shared stages 1-2 |

## Folders

- `Work\<clip>\` — per-clip intermediate files (source, frames, popart,
  audio). Safe to delete after the final video is produced.
- `Output\` — finished `<clip>_popart.mp4` files.

## Verifying a run

- Single image: open the `OUTPUT` file — it should read as pop-art.
- Video: frame count in `Work\<clip>\popart\` should be ~30 x clip-seconds.
- Open a few PNGs in `Work\<clip>\popart\` — they should look stylized.
- Play `Output\<clip>_popart.mp4` and confirm motion + audio.

## Engine tests

The engine has unit tests covering each pass. Run them from
`engines\popart`:

```
.venv\Scripts\python.exe -m unittest test_popart_render -v
```

All tests should pass.
