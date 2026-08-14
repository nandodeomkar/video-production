"""test_char_render.py - Unit tests for the CharArt rendering engine.

Run tests using:
    python -m unittest test_char_render -v
"""

import unittest
import numpy as np
import cv2
import sys
import os

# Add current folder to path to load char_render successfully
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import char_render


class TestASCII(unittest.TestCase):
    def test_char_for_ascii_bounds(self):
        # Brightness 0 maps to first character in ASCII_RAMP
        self.assertEqual(char_render.char_for_ascii(0), char_render.ASCII_RAMP[0])
        # Brightness 255 maps to last character in ASCII_RAMP
        self.assertEqual(char_render.char_for_ascii(255), char_render.ASCII_RAMP[-1])

    def test_char_for_ascii_gradients(self):
        # Verify that mid-range mapping behaves smoothly
        halfway_char = char_render.char_for_ascii(128)
        self.assertIn(halfway_char, char_render.ASCII_RAMP)


class TestMono(unittest.TestCase):
    def test_char_for_mono_below_threshold(self):
        # Brightness below MONO_THRESHOLD (128) should render the character
        self.assertEqual(char_render.char_for_mono(100, "+"), "+")
        self.assertEqual(char_render.char_for_mono(0, "#"), "#")

    def test_char_for_mono_above_threshold(self):
        # Brightness at or above MONO_THRESHOLD (128) should render blank (empty string)
        self.assertEqual(char_render.char_for_mono(128, "+"), "")
        self.assertEqual(char_render.char_for_mono(250, "#"), "")


class TestHatch(unittest.TestCase):
    def test_char_for_hatch_bands(self):
        # Test boundaries in HATCH_BANDS = ((50, "X"), (110, "/"), (175, "-"), (235, "."))
        self.assertEqual(char_render.char_for_hatch(20), "X")   # < 50
        self.assertEqual(char_render.char_for_hatch(80), "/")   # < 110
        self.assertEqual(char_render.char_for_hatch(150), "-")  # < 175
        self.assertEqual(char_render.char_for_hatch(200), ".")  # < 235
        self.assertEqual(char_render.char_for_hatch(250), " ")  # >= 235


class TestCustom(unittest.TestCase):
    def test_char_for_custom_appends_space(self):
        # Custom ramp without trailing space should automatically append space
        ramp_no_space = ".:+=#"  # length 5
        # Interally becomes ".:+=# " (length 6)
        # Brightness 0 should map to '.'
        self.assertEqual(char_render.char_for_custom(0, ramp_no_space), ".")
        # Brightness 255 should map to ' ' (the appended highlight space)
        self.assertEqual(char_render.char_for_custom(255, ramp_no_space), " ")
        # Midpoint should map to '+' or '='
        mid_char = char_render.char_for_custom(128, ramp_no_space)
        self.assertIn(mid_char, "+=")

    def test_char_for_custom_retains_space(self):
        # Custom ramp with trailing space should stay exactly length 5
        ramp_with_space = ".:#@ "  # has trailing space
        self.assertEqual(char_render.char_for_custom(0, ramp_with_space), ".")
        self.assertEqual(char_render.char_for_custom(255, ramp_with_space), " ")
        # Mid-high brightness (210) maps to '@' (only if length is 5, not 6)
        self.assertEqual(char_render.char_for_custom(210, ramp_with_space), "@")


class TestHelpers(unittest.TestCase):
    def test_lift_color_under_floor(self):
        # Pure black gets lifted to a flat gray
        black = (0, 0, 0)
        self.assertEqual(char_render.lift_color(black), (char_render.COLOR_FLOOR,) * 3)

        # A very dark color (e.g. 4, 10, 20) is scaled up uniformly
        dark = (20, 10, 4)
        lifted = char_render.lift_color(dark)
        self.assertGreaterEqual(max(lifted), char_render.COLOR_FLOOR)
        # Check aspect ratio / hue preservation
        self.assertAlmostEqual(lifted[0] / lifted[1], dark[0] / dark[1], places=1)
        self.assertAlmostEqual(lifted[1] / lifted[2], dark[1] / dark[2], places=1)

    def test_lift_color_above_floor(self):
        # Already bright colors are returned exactly as-is
        bright = (150, 120, 80)
        self.assertEqual(char_render.lift_color(bright), bright)

    def test_auto_normalize_flat_image(self):
        # A perfectly flat/solid color image shouldn't stretch and should return unmodified
        flat_img = np.full((100, 100, 3), (120, 120, 120), dtype=np.uint8)
        norm = char_render.auto_normalize(flat_img)
        np.testing.assert_array_equal(flat_img, norm)

    def test_auto_normalize_stretches(self):
        # A low-contrast image should be stretched. We use enough extreme pixels
        # to ensure that the 2% and 98% percentiles detect the dark and light points.
        low_contrast = np.full((10, 10, 3), (50, 50, 50), dtype=np.uint8)
        # Set 3 pixels to 20, and 3 pixels to 80 (3% of 100 pixels each)
        for i in range(3):
            low_contrast[0, i] = (20, 20, 20)
            low_contrast[-1, -1-i] = (80, 80, 80)
        
        stretched = char_render.auto_normalize(low_contrast)
        # Stretches the range to make highlights brighter and shadows darker
        self.assertGreater(np.max(stretched), 80)
        self.assertLess(np.min(stretched), 20)


class TestRenderEndToEnd(unittest.TestCase):
    def setUp(self):
        # Construct a small synthetic image (48x48 BGR)
        self.img = np.zeros((48, 48, 3), dtype=np.uint8)
        # Add visual details: a gray diagonal gradient
        for y in range(48):
            for x in range(48):
                val = int((x + y) * 255 / 96)
                self.img[y, x] = (val, val, val)

    def test_render_shapes_and_sizing(self):
        # Sizing should round down to cell boundary (e.g. 48 width with cell 10 -> 40 width)
        canvas = char_render.render(
            self.img, style="ascii", cell=10, ink=(255, 255, 255),
            bg=(0, 0, 0), fontscale=0.5, mono_char="+", fill="none", normalize=False
        )
        self.assertEqual(canvas.shape, (40, 40, 3))

    def test_render_fills_and_styles(self):
        # Custom style, cell 12, fill image, normalize true
        canvas = char_render.render(
            self.img, style="custom", cell=12, ink=(200, 200, 200),
            bg=(10, 10, 10), fontscale=0.5, mono_char=".:-=+#@", fill="image", normalize=True
        )
        self.assertEqual(canvas.shape, (48, 48, 3))
        # Image background fill makes output canvas not flat solid background
        self.assertFalse(np.all(canvas == (10, 10, 10)))


if __name__ == "__main__":
    unittest.main()
