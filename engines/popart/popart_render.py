"""Stylize an image into pop-art / comic-book style.

Renders a single image to an explicit output path so many instances can run
in parallel as a video-frame stage without clobbering each other.

The image flows through five ordered passes:
  1. PUNCH     boost saturation + contrast  -> loud, recognizable colour
  2. SMOOTH    edge-preserving blur         -> flatten interior micro-texture
  3. QUANTIZE  reduce to N flat colours     -> the flat pop-art colour
  4. HALFTONE  shadows -> dot pattern       -> comic dots, shadows only
  5. OUTLINE   bold edges -> black ink      -> the inked-line look

Pass order matters: SMOOTH before QUANTIZE keeps quantized regions clean;
HALFTONE and OUTLINE are drawn last, on top of the flat colour.

Usage:
    python popart_render.py <input> <output>
                            [--colors N] [--shadow-cutoff 0-255]
                            [--saturation F] [--edge-strength F]
                            [--cell N] [--normalize]
"""
import sys
import os
import argparse
import cv2
import numpy as np

# Contrast stretch applied in PUNCH, around mid-grey (128). >1.0 widens the
# tonal range so shadows deepen and highlights brighten before quantizing.
CONTRAST_FACTOR = 1.25

# cv2.bilateralFilter parameters for SMOOTH. A bilateral filter blurs flat
# interiors while preserving strong edges — exactly what QUANTIZE needs.
#   BILATERAL_DIAMETER : pixel neighbourhood diameter
#   BILATERAL_SIGMA    : colour AND space sigma (one value, used for both);
#                        higher = stronger flattening
BILATERAL_DIAMETER = 9
BILATERAL_SIGMA = 75

# cv2.kmeans settings for QUANTIZE.
#   KMEANS_ITERATIONS : max iterations of the clustering loop
#   KMEANS_EPSILON    : stop early once cluster centres move less than this
#   KMEANS_ATTEMPTS   : restarts with different seeds; best result is kept
KMEANS_ITERATIONS = 20
KMEANS_EPSILON = 1.0
KMEANS_ATTEMPTS = 3

# Halftone dot radius as a fraction of the cell size. 0.32 gives dots that
# read clearly without merging into solid black at the default cell size.
HALFTONE_DOT_RATIO = 0.32

# OUTLINE edge detection (Difference-of-Gaussians).
#   DOG_BLUR_NARROW / DOG_BLUR_WIDE : the two Gaussian blur kernel sizes;
#       their difference isolates edges. Both must be odd.
#   EDGE_BASE_THRESHOLD : DoG response above this becomes an inked pixel.
#       Divided by edge_strength, so a larger --edge-strength inks more.
#   OUTLINE_DILATE : kernel size for thickening the detected lines so they
#       read as bold comic ink rather than thin hairlines.
DOG_BLUR_NARROW = 3
DOG_BLUR_WIDE = 9
EDGE_BASE_THRESHOLD = 12.0
OUTLINE_DILATE = 2

# Percentiles mapped to full black/white when --normalize is used. Clipping a
# little off each end ignores stray outlier pixels that would pin the range.
NORM_LOW_PCT = 2
NORM_HIGH_PCT = 98


def punch(img, saturation):
    """Boost saturation and contrast so colours read loud.

    Saturation is scaled on the HSV S channel; contrast is a linear stretch
    around mid-grey on the BGR pixels. Both are clipped back into 0-255.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype('float32')
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255)
    boosted = cv2.cvtColor(hsv.astype('uint8'), cv2.COLOR_HSV2BGR)

    stretched = (boosted.astype('float32') - 128.0) * CONTRAST_FACTOR + 128.0
    return np.clip(stretched, 0, 255).astype('uint8')


def smooth(img):
    """Edge-preserving blur: flatten interiors, keep boundaries crisp.

    A bilateral filter averages nearby pixels only when they are also similar
    in colour, so smooth regions get flattened while strong edges survive.
    """
    return cv2.bilateralFilter(img, BILATERAL_DIAMETER,
                               BILATERAL_SIGMA, BILATERAL_SIGMA)


def quantize(img, colors):
    """Reduce the image to `colors` dominant colours via k-means clustering.

    Every pixel is treated as a 3-D point (B, G, R). cv2.kmeans finds the
    `colors` cluster centres; each pixel is then snapped to its centre. The
    result is a true limited palette — flat comic colour.
    """
    samples = img.reshape(-1, 3).astype('float32')
    # cv2.kmeans throws if there are fewer pixels than clusters. A real frame
    # has millions of pixels, but a pathologically tiny image could not -- so
    # never ask for more clusters than there are pixels.
    k = min(colors, samples.shape[0])
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
                KMEANS_ITERATIONS, KMEANS_EPSILON)
    _, labels, centers = cv2.kmeans(
        samples, k, None, criteria, KMEANS_ATTEMPTS,
        cv2.KMEANS_RANDOM_CENTERS)
    palette = centers.astype('uint8')
    quantized = palette[labels.flatten()]
    return quantized.reshape(img.shape)


def halftone(img, shadow_cutoff, cell):
    """Overlay black comic dots wherever the image is in shadow.

    The image is divided into `cell`-sized squares. For each cell, the mean
    brightness is measured; cells darker than `shadow_cutoff` get a black dot
    drawn at their centre. Brighter cells are left as flat colour. The result
    is the classic newsprint dot texture, confined to the shadows.
    """
    out = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    radius = max(1, int(cell * HALFTONE_DOT_RATIO))
    for y in range(0, h - cell + 1, cell):
        for x in range(0, w - cell + 1, cell):
            block = gray[y:y + cell, x:x + cell]
            if block.mean() < shadow_cutoff:
                center = (x + cell // 2, y + cell // 2)
                cv2.circle(out, center, radius, (0, 0, 0), -1, cv2.LINE_AA)
    return out


def outline(img, edge_strength):
    """Ink bold black outlines on the image's major boundaries.

    Edges are found by Difference-of-Gaussians: two Gaussian blurs at
    different radii are subtracted, leaving a strong response only where the
    image changes sharply. The response is thresholded into an edge mask, the
    mask is dilated so lines read as bold ink, and those pixels are painted
    black on top of the input.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype('float32')
    narrow = cv2.GaussianBlur(gray, (DOG_BLUR_NARROW, DOG_BLUR_NARROW), 0)
    wide = cv2.GaussianBlur(gray, (DOG_BLUR_WIDE, DOG_BLUR_WIDE), 0)
    dog = np.abs(narrow - wide)

    threshold = EDGE_BASE_THRESHOLD / max(edge_strength, 0.01)
    mask = (dog > threshold).astype('uint8')
    if OUTLINE_DILATE > 0:
        kernel = np.ones((OUTLINE_DILATE, OUTLINE_DILATE), dtype='uint8')
        mask = cv2.dilate(mask, kernel)

    out = img.copy()
    out[mask > 0] = (0, 0, 0)
    return out


def auto_normalize(img):
    """Stretch a frame's brightness to the full range, preserving colour.

    Works on the HSV value channel only — hue and saturation untouched — so a
    dark, colour-cast frame is lifted into a visible range without
    neutralizing its colours. Low/high percentiles (not absolute min/max) map
    to 0/255 so outlier pixels do not pin the range.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    v = hsv[:, :, 2]
    lo, hi = np.percentile(v, (NORM_LOW_PCT, NORM_HIGH_PCT))
    if hi <= lo:
        return img  # flat frame — nothing to stretch
    stretched = (v.astype('float32') - lo) * (255.0 / (hi - lo))
    hsv[:, :, 2] = np.clip(stretched, 0, 255).astype('uint8')
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def render(img, colors, shadow_cutoff, saturation, edge_strength, cell,
           normalize):
    """Stylize a BGR image into pop-art and return the rendered canvas.

    Runs the five passes in order. The canvas is first cropped to a whole
    number of `cell`-sized squares so the halftone grid divides evenly — this
    keeps the output a stable size, suitable for a video-frame stage.

    When `normalize` is True the frame's brightness is stretched to the full
    range first — helps dark footage render with vivid colour.
    """
    if normalize:
        img = auto_normalize(img)

    # Crop to a whole number of halftone cells so the grid divides evenly.
    h, w = img.shape[:2]
    out_h = max(cell, (h // cell) * cell)
    out_w = max(cell, (w // cell) * cell)
    img = img[:out_h, :out_w]

    img = punch(img, saturation)
    img = smooth(img)
    img = quantize(img, colors)
    img = halftone(img, shadow_cutoff, cell)
    img = outline(img, edge_strength)
    return img


def main():
    ap = argparse.ArgumentParser(
        description="Stylize an image into pop-art / comic-book style.")
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--colors", type=int, default=8,
                    help="number of palette colours (k-means clusters)")
    ap.add_argument("--shadow-cutoff", type=int, default=100,
                    help="brightness (0-255) below which halftone dots appear")
    ap.add_argument("--saturation", type=float, default=1.6,
                    help="saturation boost factor")
    ap.add_argument("--edge-strength", type=float, default=1.0,
                    help="outline boldness multiplier")
    ap.add_argument("--cell", type=int, default=6,
                    help="halftone dot-grid cell size in pixels")
    ap.add_argument("--normalize", action="store_true",
                    help="auto-stretch brightness before stylizing")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print(f"Input not found: {args.input}")
        sys.exit(1)

    img = cv2.imread(args.input, cv2.IMREAD_COLOR)
    if img is None:
        print(f"Could not read image: {args.input}")
        sys.exit(1)

    canvas = render(img, args.colors, args.shadow_cutoff, args.saturation,
                    args.edge_strength, args.cell, args.normalize)

    if not cv2.imwrite(args.output, canvas):
        print(f"Failed to write output: {args.output}")
        sys.exit(1)


if __name__ == "__main__":
    main()
