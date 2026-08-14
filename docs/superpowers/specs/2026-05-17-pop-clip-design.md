# Pop-Clip Workflow — Design

**Date:** 2026-05-17
**Status:** Approved design — ready for implementation planning

## Summary

A third video-stylization pipeline for the Video Production toolkit. It turns an
image — or a short section of any online video — into **pop-art / comic-book
style**: flat saturated colour, halftone dots in the shadows, and bold black
inked outlines.

It follows the exact structural pattern of the existing `char-clip` pipeline: a
standalone render engine plus a `bin\` folder of stage scripts, reusing
`tiled-clip`'s download and frame-extraction stages.

## Goals

- Produce a recognizable comic-book rendering of a real scene — punchy, but the
  scene and faces still read clearly.
- Work on both a single image and a video section, via the same engine.
- Match the existing pipelines' conventions so the toolkit stays consistent.
- Introduce zero risk to the working `char-clip` and `tiled-clip` pipelines.

## Non-Goals

- Photo-accurate output. Like char-clip, each pass collapses detail; this is a
  stylization, not a filter that preserves fidelity.
- A configurable cartoon spectrum (cel-shade, poster, etc.). Scope is pop-art
  only. Other looks would be separate pipelines.
- Temporal smoothing across frames. Frames are processed independently, as in
  the existing pipelines. Frame-to-frame flicker is accepted (and mitigated by
  the smooth + quantize passes — see Render Pipeline).

## Style Decisions (settled during brainstorming)

| Question   | Decision |
|------------|----------|
| Cartoon look | Pop-art / comic-book |
| Shading      | Halftone dots in shadow regions only; flat colour elsewhere |
| Colour       | Boost saturation — keep the source's real hues, crank saturation + contrast, then quantize |
| Outlines     | Bold inked lines — thick, on major boundaries only (not interior texture) |

## Architecture

A new pipeline mirroring `char-clip`. New files:

```
Libraries\PopArt\popart_render.py     the engine — stylizes one image to pop-art
bin\pop-clip\
    3-popart-frames.cmd               Stage 3: pop-art every extracted frame
    4-stitch.cmd                      Stage 4: stitch pop-art frames + audio
    run-all.cmd                       runs all 4 stages end-to-end
    stylize-image.cmd                 single-image entry point
    render-frames.ps1                 parallel frame renderer (Stage 3 helper)
workflows\pop-clip.md                 documentation
```

Stages 1 and 2 are **called from `bin\tiled-clip\`**, not copied — identical to
how `char-clip\run-all.cmd` already reuses them. Stages 3 and 4 are pop-clip's
own.

### Stage flow

```
YouTube URL + start/end timestamp
        |
   [1] download    -> Work/<clip>/source.mp4        (shared: tiled-clip\1-download.cmd)
   [2] extract     -> Work/<clip>/frames/f_*.png     (shared: tiled-clip\2-extract-frames.cmd)
                      Work/<clip>/audio.m4a
   [3] popart      -> Work/<clip>/popart/f_*.png     each frame -> pop-art
   [4] stitch      -> Output/<clip>_popart.mp4       final video + audio
```

### Engine contract

`popart_render.py` mirrors `char_render.py`:

- Renders **one input image to one explicit output path**, so Stage 3 can run
  many instances in parallel without clobbering each other.
- Tuning constants live at the top of the file (the project's established
  convention).
- Same CLI shape: `input output [flags]`.

## Render Pipeline

Each frame flows through five ordered passes inside `popart_render.py`. Each
pass is its own small, independently testable function.

```
1. PUNCH      boost saturation + contrast      loud, recognizable colour
2. SMOOTH     edge-preserving blur             flatten interior micro-texture
                                               (skin pores, fabric weave)
3. QUANTIZE   reduce to N flat colour bands     the flat pop-art colour
4. HALFTONE   shadow regions -> dot pattern     comic dots, shadows only
5. OUTLINE    bold edges -> black ink, on top   the inked-line look
```

### Why the order is load-bearing

- **SMOOTH before QUANTIZE:** raw video micro-texture, quantized directly,
  snaps each tiny variation to a different colour band — speckled noise instead
  of flat comic colour. An edge-preserving blur flattens interiors while
  keeping boundaries sharp, so QUANTIZE yields clean regions and OUTLINE still
  finds the real edges. This also reduces frame-to-frame flicker.
- **HALFTONE and OUTLINE drawn last, on top of flat colour:** quantizing after
  halftoning would colour-band the dots into mush. The black ink goes on the
  very top so no later pass softens it.

### Pass details

1. **PUNCH** — boost saturation and contrast. Operates on HSV saturation and a
   contrast stretch. Controlled by `--saturation` (default `1.6`). Optional
   `--normalize` first, for dark footage (same idea as char-clip's normalize).
2. **SMOOTH** — edge-preserving blur via `cv2.bilateralFilter` or
   `cv2.pyrMeanShiftFiltering`. Flattens interiors, preserves edges.
3. **QUANTIZE** — **K-means colour clustering**: find the K dominant colours in
   the frame, snap every pixel to the nearest. Produces a true limited palette
   (more "comic" than per-channel posterize, which yields arbitrary colours).
   Controlled by `--colors` (K, default `8`).
4. **HALFTONE** — pixels with brightness below `SHADOW_CUTOFF` are rendered as
   a dot pattern; brighter pixels are left as flat quantized colour. Dot grid
   size controlled by `--cell` (default `6`). `--shadow-cutoff` default `100`
   (dots in genuine shadows, not midtones).
5. **OUTLINE** — bold black edges on major boundaries only, drawn on top.
   Difference-of-Gaussians style for thick, slightly rough, steady-on-video
   lines (Canny flickers more frame-to-frame). Controlled by `--edge-strength`.

## CLI

`popart_render.py` mirrors `char_render.py`'s interface:

```
python popart_render.py <input> <output>
                        [--colors N] [--shadow-cutoff 0-255]
                        [--saturation F] [--edge-strength F]
                        [--cell N] [--normalize]
```

| Flag | Meaning | Default |
|------|---------|---------|
| `--colors` | K — number of palette colours (k-means clusters) | `8` |
| `--shadow-cutoff` | brightness below which halftone dots appear (0-255) | `100` |
| `--saturation` | saturation boost factor in PUNCH | `1.6` |
| `--edge-strength` | outline boldness | a concrete value picked during implementation by visual tuning on real frames, biased toward bold |
| `--cell` | halftone dot-grid cell size in pixels | `6` |
| `--normalize` | auto-stretch brightness before stylizing (dark footage) | off (engine flag) |

The `.cmd` wrappers expose the same knobs positionally, matching the
`stylize-image.cmd` / `run-all.cmd` argument style of char-clip.

> **Implementation deviation — NORMALIZE wrapper default.** The `--normalize`
> *engine* flag defaults off (the engine stays a neutral tool). But the
> `.cmd` wrappers' `NORMALIZE` positional argument defaults to **`on`**.
> Reason: visual testing on real footage during implementation showed that
> pop-art's k-means quantization collapses dark frames into muddy near-blacks;
> normalizing first keeps colour vivid and the scene readable. This diverges
> from char-clip's wrappers (which default `off`) — char-clip is monochrome
> and degrades gracefully on dark input, whereas pop-art does not. Users pass
> `NORMALIZE off` for already-bright footage.

### Entry points

```
bin\pop-clip\stylize-image.cmd  INPUT OUTPUT [COLORS] [SHADOW_CUTOFF] [SATURATION] [CELL] [NORMALIZE]
bin\pop-clip\run-all.cmd        URL START END CLIPNAME [COLORS] [SHADOW_CUTOFF] [SATURATION] [CELL] [NORMALIZE]
```

Running stages individually:

| Stage | Command | Produces |
|-------|---------|----------|
| 1 | `..\tiled-clip\1-download.cmd URL START END CLIPNAME` | `Work\<clip>\source.mp4` |
| 2 | `..\tiled-clip\2-extract-frames.cmd CLIPNAME` | `Work\<clip>\frames\`, `audio.m4a` |
| 3 | `3-popart-frames.cmd CLIPNAME [COLORS] [SHADOW_CUTOFF] [SATURATION] [CELL] [NORMALIZE]` | `Work\<clip>\popart\` |
| 4 | `4-stitch.cmd CLIPNAME` | `Output\<clip>_popart.mp4` |

## Error Handling

Same boundaries as `char_render.py` — validate at the edges only, trust
internal data flow:

- Input file not found → print message, exit non-zero.
- Input not a readable image → print message, exit non-zero.
- Output write failure → print message, exit non-zero.
- The five internal passes trust their inputs (NumPy arrays from the prior
  pass). No defensive checks between passes.

## Testing

The pure-function pass structure makes this clean:

- **Per-pass unit tests** on small synthetic images:
  - QUANTIZE on a known gradient → at most N distinct colours.
  - HALFTONE → bright regions untouched; shadow regions altered.
  - OUTLINE → a known edge is darkened; a flat region is not.
  - PUNCH → saturation of a known pixel increases.
- **End-to-end test:** a sample image through the full five-pass chain →
  output of the expected dimensions.
- **Manual visual check:** run on a real frame from `Work\pqoxclip\frames\`
  (the existing pqoxclip clip provides ready test frames) before wiring up the
  video stages. Confirm the result reads as pop-art.
- **Pipeline check:** after wiring, frame count in `Work\<clip>\popart\` is
  ~30 x clip-seconds; spot-check PNGs; play `Output\<clip>_popart.mp4` and
  confirm motion + audio.

## Render Cost

K-means quantization is the expensive pass. Stage 3 renders frames in parallel
(`CONCURRENCY=8`, editable at the top of `3-popart-frames.cmd`, matching
char-clip). A 4-second clip (~120 frames at 30fps) is expected to render in
roughly 1-3 minutes on a multi-core machine.

## Folders

- `Work\<clip>\` — per-clip intermediates (source, frames, popart, audio).
  Safe to delete after the final video.
- `Output\` — finished `<clip>_popart.mp4` files.

## Open Questions

None. All four style decisions and both pipeline-internal decisions
(quantize method, shadow-cutoff approach) were settled during brainstorming.
