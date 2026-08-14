"""Stylize an image into character art (ASCII / mono-character / crosshatch).

Renders a single image to an explicit output path so many instances can run in
parallel as a video-frame stage without clobbering each other.

How it works:
  1. The image is downscaled to a grid_w x grid_h grid. With INTER_AREA that
     resize IS the per-cell brightness sample -- one averaged value per cell.
  2. Each cell's brightness (0-255) is mapped to a character by the active
     style's ramp function.
  3. Characters are drawn with cv2.putText at fixed cell origins onto a
     monochrome canvas (single ink colour on a flat background).

Usage:
    python char_render.py <input> <output> [--style ascii|mono|hatch]
                          [--cell N] [--ink R,G,B] [--bg R,G,B]
                          [--fontscale F] [--char C]

  --style      which character mapping to use (default: ascii)
  --cell       source-pixel size of one grid cell; bigger = coarser (default 12)
  --ink        character colour as R,G,B (default 220,220,220)
  --bg         background colour as R,G,B (default 12,12,12)
  --fontscale  cv2.putText scale; tune so glyphs fill the cell (default 0.5)
  --char       the single character for --style mono (default '+')
"""
import sys
import os
import argparse
import cv2
import numpy as np

# cv2.putText draws bottom-left-origin glyphs; this font is near-monospace
# enough that fixed cell origins keep the grid rigid.
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_THICKNESS = 1


# ----------------------------------------------------------------------------
# Style ramp functions.
#
# Each takes a cell brightness in 0-255 and returns the character to draw
# (return '' or ' ' to leave the cell blank). These three functions define the
# entire look of the pipeline -- they are intentionally left for you to fill in.
# ----------------------------------------------------------------------------

# Darkest -> lightest. Last entry is a space so highlights read as blank
# canvas, letting the subject float on the background.
ASCII_RAMP = "@%#*+=-:. "


def char_for_ascii(brightness):
    """True ASCII art: map brightness -> a character from a dark->light ramp."""
    idx = brightness * (len(ASCII_RAMP) - 1) // 255
    return ASCII_RAMP[idx]


# Cells darker than this get the character; lighter cells stay blank. 128 is a
# neutral midpoint -- roughly half the image inks in.
MONO_THRESHOLD = 128


def char_for_mono(brightness, char):
    """Single-character stipple: draw `char` only where the cell is dark."""
    return char if brightness < MONO_THRESHOLD else ""


# (upper-bound, glyph) ordered dark -> light. Boundaries are weighted toward
# the midtones, where most photographic detail lives, so shading gradients get
# two distinct bands ('X' and '/') instead of one.
HATCH_BANDS = ((50, "X"), (110, "/"), (175, "-"), (235, "."))


def char_for_hatch(brightness):
    """Crosshatch shading: pick a stroke glyph by brightness band."""
    for upper, glyph in HATCH_BANDS:
        if brightness < upper:
            return glyph
    return " "


def char_for_custom(brightness, ramp):
    """Custom ramp: map brightness -> a character from user-supplied ramp.

    If the ramp does not end in a space, a trailing space is automatically
    appended to ensure that image highlights read as blank canvas.
    """
    if not ramp:
        return " "
    if not ramp.endswith(" "):
        ramp = ramp + " "
    idx = brightness * (len(ramp) - 1) // 255
    return ramp[idx]


# ----------------------------------------------------------------------------
# Rendering core -- style-agnostic; calls the ramp functions above.
# ----------------------------------------------------------------------------

def pick_char(brightness, style, mono_char):
    """Dispatch one cell's brightness to the active style's ramp function."""
    if style == "ascii":
        return char_for_ascii(brightness)
    if style == "mono":
        return char_for_mono(brightness, mono_char)
    if style == "hatch":
        return char_for_hatch(brightness)
    if style == "custom":
        return char_for_custom(brightness, mono_char)
    raise ValueError(f"unknown style: {style}")


# In --color mode, a glyph is drawn in its cell's own average colour. A very
# dark cell would then be near-invisible on a dark background, so its colour is
# lifted to at least this brightness (per channel max). Keeps shadow detail
# readable without washing out the palette.
COLOR_FLOOR = 70


# Percentiles mapped to full black/white when auto-normalizing. Clipping a
# little off each end ignores stray dark/bright outlier pixels that would
# otherwise pin the range and defeat the stretch.
NORM_LOW_PCT = 2
NORM_HIGH_PCT = 98


def auto_normalize(img):
    """Stretch a frame's brightness to the full range, preserving colour.

    Works on the HSV value (brightness) channel only -- hue and saturation are
    untouched -- so a dark, colour-cast frame is lifted into a visible range
    without neutralizing its colours. The low/high percentiles (not absolute
    min/max) are mapped to 0/255 so outlier pixels don't pin the range.

    Returns the brightened BGR image. A frame that already spans the range is
    effectively unchanged.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    v = hsv[:, :, 2]
    lo, hi = np.percentile(v, (NORM_LOW_PCT, NORM_HIGH_PCT))
    if hi <= lo:
        return img  # flat frame -- nothing to stretch
    stretched = (v.astype('float32') - lo) * (255.0 / (hi - lo))
    hsv[:, :, 2] = np.clip(stretched, 0, 255).astype('uint8')
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def lift_color(bgr):
    """Brighten a too-dark cell colour so its glyph stays visible.

    Scales the colour up uniformly (preserving hue) until its brightest channel
    reaches COLOR_FLOOR. Cells already bright enough are returned unchanged.
    """
    peak = int(max(bgr))
    if peak == 0:
        return (COLOR_FLOOR, COLOR_FLOOR, COLOR_FLOOR)  # pure black -> grey
    if peak >= COLOR_FLOOR:
        return (int(bgr[0]), int(bgr[1]), int(bgr[2]))
    scale = COLOR_FLOOR / peak
    return tuple(min(255, int(c * scale)) for c in bgr)


# How heavily the cell background is darkened, per fill mode, so the glyph
# drawn on top still stands out as the brighter element.
TINT_BG_FACTOR = 0.35    # 'tint': cell painted with its own colour, dimmed
IMAGE_BG_FACTOR = 0.45   # 'image': the real frame shows through, dimmed


def render(img, style, cell, ink, bg, fontscale, mono_char, fill, normalize):
    """Stylize a BGR image into character art and return the rendered canvas.

    The output canvas is the same pixel size as the input (rounded down to a
    whole number of cells), so this drops straight into a video frame stage.

    `fill` controls how each cell's background is treated -- the lever that
    decides scene recognizability:
      'none'   flat `bg`; glyph drawn in flat `ink`. Pure monochrome
               character art on a plain background.
      'tint'   each cell washed with a dimmed version of its own colour, glyph
               drawn in the cell's own colour. Scene reads as solid blocks.
      'image'  the dimmed real frame shows through behind the glyphs. Most
               photo-recognizable.

    When `normalize` is True the frame's brightness is stretched to the full
    range first -- helps dark footage render with vivid colour.
    """
    if normalize:
        img = auto_normalize(img)

    h, w = img.shape[:2]
    grid_w = max(1, w // cell)
    grid_h = max(1, h // cell)

    # Downscale to one pixel per cell -- INTER_AREA averaging gives, in one
    # pass, both the per-cell brightness (via gray) and the per-cell average
    # colour (small itself), used for glyph colour and the 'tint' background.
    small = cv2.resize(img, (grid_w, grid_h), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

    out_h, out_w = grid_h * cell, grid_w * cell

    # Build the background layer the glyphs will be drawn onto.
    if fill == "tint":
        # Upscale the per-cell colour grid to full size (NEAREST keeps crisp
        # cell edges), dimmed so glyphs stay the brighter element.
        bgimg = cv2.resize(small, (out_w, out_h), interpolation=cv2.INTER_NEAREST)
        canvas = (bgimg.astype('float32') * TINT_BG_FACTOR).astype('uint8')
    elif fill == "image":
        # The real (already grid-sized) frame, blocky and dimmed.
        bgimg = cv2.resize(small, (out_w, out_h), interpolation=cv2.INTER_NEAREST)
        canvas = (bgimg.astype('float32') * IMAGE_BG_FACTOR).astype('uint8')
    else:  # 'none'
        canvas = np.full((out_h, out_w, 3), bg, dtype=np.uint8)

    # Place each glyph at a fixed cell origin so the grid stays rigid. The
    # baseline sits near the cell's lower edge with a small inset. In a colour
    # fill the glyph takes the cell's own lifted colour; in 'none' the flat ink.
    baseline_inset = max(2, cell // 6)
    for gy in range(grid_h):
        for gx in range(grid_w):
            ch = pick_char(int(gray[gy, gx]), style, mono_char)
            if not ch or ch == " ":
                continue
            glyph_color = lift_color(small[gy, gx]) if fill != "none" else ink
            origin = (gx * cell + 1, (gy + 1) * cell - baseline_inset)
            cv2.putText(canvas, ch, origin, FONT, fontscale, glyph_color,
                        FONT_THICKNESS, cv2.LINE_AA)
    return canvas


def parse_rgb(text):
    """Parse 'R,G,B' (0-255 each) into a BGR tuple for OpenCV."""
    parts = text.split(",")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("colour must be R,G,B")
    r, g, b = (int(p) for p in parts)
    return (b, g, r)  # OpenCV is BGR


def main():
    ap = argparse.ArgumentParser(description="Stylize an image into character art.")
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--style", choices=["ascii", "mono", "hatch", "custom"], default="ascii")
    ap.add_argument("--cell", type=int, default=12)
    ap.add_argument("--ink", type=parse_rgb, default=parse_rgb("220,220,220"))
    ap.add_argument("--bg", type=parse_rgb, default=parse_rgb("12,12,12"))
    ap.add_argument("--fontscale", type=float, default=0.5)
    ap.add_argument("--char", default="+")
    ap.add_argument("--fill", choices=["none", "tint", "image"], default="none",
                    help="cell background: none = flat bg, monochrome glyphs; "
                         "tint = cell washed with its colour; image = real "
                         "frame shows through. tint/image make scenes "
                         "far more recognizable")
    ap.add_argument("--normalize", action="store_true",
                    help="auto-stretch frame brightness before stylizing; "
                         "helps dark footage render with vivid colour")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print(f"Input not found: {args.input}")
        sys.exit(1)

    img = cv2.imread(args.input, cv2.IMREAD_COLOR)
    if img is None:
        print(f"Could not read image: {args.input}")
        sys.exit(1)

    canvas = render(img, args.style, args.cell, args.ink, args.bg,
                    args.fontscale, args.char, args.fill, args.normalize)

    if not cv2.imwrite(args.output, canvas):
        print(f"Failed to write output: {args.output}")
        sys.exit(1)


if __name__ == "__main__":
    main()
