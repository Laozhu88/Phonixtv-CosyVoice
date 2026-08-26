import unittest
from pathlib import Path


class LocalWaveSurferAssetsTest(unittest.TestCase):
    def test_workbench_uses_packaged_waveform_player(self):
        static_dir = Path(__file__).resolve().parents[1] / "app" / "frontend" / "static"
        html = (static_dir / "index.html").read_text(encoding="utf-8")

        self.assertNotIn("unpkg.com/wavesurfer", html)
        self.assertIn("/static/vendor/wavesurfer/wavesurfer.min.js", html)
        self.assertIn("/static/vendor/wavesurfer/regions.min.js", html)
        self.assertGreater((static_dir / "vendor" / "wavesurfer" / "wavesurfer.min.js").stat().st_size, 40000)
        self.assertGreater((static_dir / "vendor" / "wavesurfer" / "regions.min.js").stat().st_size, 15000)


if __name__ == "__main__":
    unittest.main()
