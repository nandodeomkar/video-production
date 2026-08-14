# Tiled-Clip Workflow

Turn a short section of any online video into a **mosaic-styled clip** — every frame
rebuilt out of small tiles — for use as a standardised, recognisable insert in
explainer videos.

## What it does

```
YouTube URL + start/end timestamp
        |
   [1] download    -> Work/<clip>/source.mp4        trimmed, up to 1080p
   [2] extract     -> Work/<clip>/frames/f_*.png     30fps PNG sequence, 1920x1080
                      Work/<clip>/audio.m4a          original audio (copied)
   [3] tile        -> Work/<clip>/tiled/f_*.png      each frame -> tile mosaic
   [4] stitch      -> Output/<clip>_tiled.mp4        final video + audio
```

## Quick start

Run the whole pipeline in one go:

```
pipelines\tiled-clip\run-all.cmd  "<URL>"  <START>  <END>  <CLIPNAME>  [TILES_FOLDER]
```

Example — tile a 4-second section:

```
pipelines\tiled-clip\run-all.cmd "https://www.youtube.com/watch?v=XXXX" 00:01:12 00:01:16 newsclip1
```

Result: `Output\newsclip1_tiled.mp4`

`START` / `END` accept either `HH:MM:SS` or plain seconds.
`CLIPNAME` becomes the work-folder name and the output filename prefix.

## Running stages individually

Each stage is a standalone script in `pipelines\tiled-clip\`. Useful to inspect output
between steps, or to re-run just one stage after tweaking settings.

| Stage | Command | Produces |
|-------|---------|----------|
| 1 | `1-download.cmd URL START END CLIPNAME` | `Work\<clip>\source.mp4` |
| 2 | `2-extract-frames.cmd CLIPNAME` | `Work\<clip>\frames\`, `audio.m4a` |
| 3 | `3-tile-frames.cmd CLIPNAME [TILES_FOLDER]` | `Work\<clip>\tiled\` |
| 4 | `4-stitch.cmd CLIPNAME` | `Output\<clip>_tiled.mp4` |

## Tuning

### Tile look
By default Stage 3 generates a **solid-square tile set** (`engines\tiler\tiles\squares\`)
and reuses it for every clip. To use your own tiles, pass a folder of tile images as
the last argument to `run-all.cmd` or `3-tile-frames.cmd`.

Edit the top of `pipelines\tiled-clip\3-tile-frames.cmd`:
- `SQUARE_SIZE` — tile pixel size. Bigger = chunkier mosaic and **faster** rendering.
- `CONCURRENCY` — how many frames render at once (default 8, tuned for 16 cores).
- `POOLSIZE` — Tiler's internal worker pool per frame (default 2).
  `CONCURRENCY x POOLSIZE` should stay around your CPU core count.

### Mosaic detail
Editable in `engines\tiler\conf.py`:
- `COLOR_DEPTH` — colour gradations (default 32). Lower = blockier, more stylised,
  and reduces frame-to-frame flicker.
- `PIXEL_SHIFT` — tile placement step (default `(5,5)`). Larger = fewer tiles =
  much faster, coarser mosaic.

### Render cost
At 30fps/1080p a 4-second clip is ~120 frames. Tiling is CPU-heavy; with parallel
rendering on a 16-core machine expect roughly tens of minutes per clip. Raise
`SQUARE_SIZE` / `PIXEL_SHIFT` to trade detail for speed.

## Known behaviour: flicker

Tiler matches tiles **per frame independently**, so tiny colour shifts between
consecutive frames can swap tiles and cause a shimmer/"boiling" effect. For a tiled
aesthetic this often reads as intentional. If it looks distracting:
- lower `COLOR_DEPTH` in `conf.py` so neighbouring frames pick the same tiles, or
- pre-blur frames slightly before Stage 3.

## Components

| Path | Role |
|------|------|
| `pipelines\_shared\1-download.cmd`, `2-extract-frames.cmd` | shared stages 1-2 |
| `pipelines\tiled-clip\3-tile-frames.cmd`, `4-stitch.cmd` | tiled-clip stages 3-4 |
| `pipelines\tiled-clip\run-all.cmd` | runs all stages end to end |
| `pipelines\tiled-clip\render-frames.ps1` | parallel frame renderer (Stage 3 helper) |
| `engines\tiler\tile_frame.py` | tiles a single frame to an explicit output path |
| `engines\tiler\build_tiles.py` | builds the shared `tiles.pickle` once |
| `bin\yt-dlp.cmd` / `bin\ffmpeg.cmd` | tool wrappers used by the stages |

## Folders

- `Work\<clip>\` — per-clip intermediate files (source, frames, tiled, audio).
  Safe to delete after the final video is produced.
- `Output\` — finished `<clip>_tiled.mp4` files.
- `engines\tiler\tiles\squares\` — generated tile set, reused across clips.

## Verifying a run

- Check the trimmed download:  `bin\ffprobe.cmd Work\<clip>\source.mp4`
- Frame count should be ~30 x clip-length-in-seconds in `Work\<clip>\frames\`.
- Open a few PNGs in `Work\<clip>\tiled\` — they should look like a tile mosaic.
- Play `Output\<clip>_tiled.mp4` and confirm motion + audio.
