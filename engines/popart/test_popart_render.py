"""Unit tests for popart_render — the pop-art stylization engine.

Run from Libraries\\PopArt with the project venv:
    ..\\Tiler\\.venv\\Scripts\\python.exe -m unittest test_popart_render -v
"""
import unittest
import numpy as np
import cv2
import popart_render as pr


class TestModuleSurface(unittest.TestCase):
    def test_module_exposes_render(self):
        """The engine must expose a render() callable."""
        self.assertTrue(callable(pr.render))


class TestPunch(unittest.TestCase):
    def test_punch_increases_saturation(self):
        """A muted slightly-coloured pixel should gain saturation after PUNCH."""
        # A 4x4 image of one slightly-coloured pixel value (BGR).
        img = np.full((4, 4, 3), (120, 110, 90), dtype=np.uint8)
        out = pr.punch(img, saturation=1.6)
        before = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 1].mean()
        after = cv2.cvtColor(out, cv2.COLOR_BGR2HSV)[:, :, 1].mean()
        self.assertGreater(after, before)

    def test_punch_preserves_shape(self):
        """PUNCH must not change image dimensions."""
        img = np.full((8, 6, 3), (50, 90, 130), dtype=np.uint8)
        out = pr.punch(img, saturation=1.6)
        self.assertEqual(out.shape, img.shape)


class TestSmooth(unittest.TestCase):
    def test_smooth_reduces_interior_noise(self):
        """Random speckle noise should have lower variance after SMOOTH."""
        rng = np.random.default_rng(0)
        img = rng.integers(90, 165, size=(64, 64, 3), dtype=np.uint8)
        out = pr.smooth(img)
        self.assertLess(float(out.std()), float(img.std()))

    def test_smooth_preserves_shape(self):
        """SMOOTH must not change image dimensions."""
        img = np.full((20, 30, 3), (60, 120, 200), dtype=np.uint8)
        out = pr.smooth(img)
        self.assertEqual(out.shape, img.shape)


class TestQuantize(unittest.TestCase):
    def test_quantize_limits_distinct_colors(self):
        """A smooth gradient quantized to K colours yields at most K colours."""
        # Horizontal gradient, 64 distinct grey levels across the width.
        row = np.linspace(0, 252, 64, dtype=np.uint8)
        gray = np.repeat(row[None, :], 16, axis=0)
        img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        out = pr.quantize(img, colors=6)
        distinct = np.unique(out.reshape(-1, 3), axis=0)
        self.assertLessEqual(len(distinct), 6)

    def test_quantize_preserves_shape(self):
        """QUANTIZE must not change image dimensions."""
        rng = np.random.default_rng(1)
        img = rng.integers(0, 256, size=(24, 24, 3), dtype=np.uint8)
        out = pr.quantize(img, colors=8)
        self.assertEqual(out.shape, img.shape)


class TestHalftone(unittest.TestCase):
    def test_halftone_leaves_bright_regions_untouched(self):
        """A fully bright image is above the cutoff — must be returned as-is."""
        img = np.full((48, 48, 3), 240, dtype=np.uint8)
        out = pr.halftone(img, shadow_cutoff=100, cell=6)
        np.testing.assert_array_equal(out, img)

    def test_halftone_darkens_shadow_regions(self):
        """A fully dark image is below the cutoff — dots make it differ."""
        img = np.full((48, 48, 3), 20, dtype=np.uint8)
        out = pr.halftone(img, shadow_cutoff=100, cell=6)
        self.assertFalse(np.array_equal(out, img))

    def test_halftone_preserves_shape(self):
        """HALFTONE must not change image dimensions."""
        img = np.full((30, 40, 3), 60, dtype=np.uint8)
        out = pr.halftone(img, shadow_cutoff=100, cell=6)
        self.assertEqual(out.shape, img.shape)


class TestOutline(unittest.TestCase):
    def test_outline_inks_a_strong_edge(self):
        """An image with a hard black/white edge gains dark outline pixels."""
        img = np.full((40, 40, 3), 255, dtype=np.uint8)
        img[:, 20:] = 0  # hard vertical edge down the middle
        out = pr.outline(img, edge_strength=1.0)
        # Some pixels near the seam should be inked toward black.
        seam = out[:, 18:22].reshape(-1, 3)
        self.assertTrue((seam.max(axis=1) < 40).any())

    def test_outline_leaves_flat_region_intact(self):
        """A perfectly flat image has no edges — outline must not blacken it."""
        img = np.full((40, 40, 3), 200, dtype=np.uint8)
        out = pr.outline(img, edge_strength=1.0)
        np.testing.assert_array_equal(out, img)

    def test_outline_preserves_shape(self):
        """OUTLINE must not change image dimensions."""
        img = np.full((26, 34, 3), 150, dtype=np.uint8)
        img[10:16, :] = 0
        out = pr.outline(img, edge_strength=1.0)
        self.assertEqual(out.shape, img.shape)


class TestRenderEndToEnd(unittest.TestCase):
    def _sample_image(self):
        """A 96x72 image: a bright-ish coloured left half, a dark right half.

        The dark right half falls below the default shadow cutoff (so HALFTONE
        acts); the centre seam is a hard edge (so OUTLINE inks). The input
        contains no pure-black (0,0,0) pixels.
        """
        img = np.zeros((72, 96, 3), dtype=np.uint8)
        img[:, :48] = (200, 180, 60)   # bright-ish left
        img[:, 48:] = (40, 30, 20)     # dark right (will halftone)
        return img

    def test_render_preserves_dimensions_rounding_to_cells(self):
        """Output dimensions stay a whole number of halftone cells."""
        img = self._sample_image()
        out = pr.render(img, colors=6, shadow_cutoff=100, saturation=1.6,
                        edge_strength=1.0, cell=6, normalize=False)
        self.assertEqual(out.shape[0], (72 // 6) * 6)
        self.assertEqual(out.shape[1], (96 // 6) * 6)
        self.assertEqual(out.shape[2], 3)

    def test_render_quantizes_color_count(self):
        """After the full chain, distinct colours stay small (palette + ink)."""
        img = self._sample_image()
        out = pr.render(img, colors=6, shadow_cutoff=100, saturation=1.6,
                        edge_strength=1.0, cell=6, normalize=False)
        distinct = np.unique(out.reshape(-1, 3), axis=0)
        # palette (<=6) + black ink + halftone dots; generously bounded.
        self.assertLessEqual(len(distinct), 10)

    def test_render_applies_outline_ink(self):
        """The full chain introduces pure-black ink pixels not in the input."""
        img = self._sample_image()  # input has no (0,0,0) pixels
        self.assertFalse((img.reshape(-1, 3) == 0).all(axis=1).any())
        out = pr.render(img, colors=6, shadow_cutoff=100, saturation=1.6,
                        edge_strength=1.0, cell=6, normalize=False)
        self.assertTrue((out.reshape(-1, 3) == 0).all(axis=1).any())

    def test_render_normalize_runs_without_error(self):
        """normalize=True must produce a valid 3-channel output."""
        img = self._sample_image()
        out = pr.render(img, colors=6, shadow_cutoff=100, saturation=1.6,
                        edge_strength=1.0, cell=6, normalize=True)
        self.assertEqual(out.shape[2], 3)


if __name__ == "__main__":
    unittest.main()
