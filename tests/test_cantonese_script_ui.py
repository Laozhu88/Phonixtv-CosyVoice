import unittest
from pathlib import Path


class CantoneseScriptUiTest(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.html = (root / "app" / "frontend" / "static" / "index.html").read_text(encoding="utf-8")
        self.js = (root / "app" / "frontend" / "static" / "app.js").read_text(encoding="utf-8")

    def test_three_stage_cantonese_controls_are_present(self):
        self.assertIn('id="sourceScriptLabel"', self.html)
        self.assertIn('id="translatedText"', self.html)
        self.assertIn('id="refreshTranslationBtn"', self.html)

    def test_cantonese_generation_uses_yue_script(self):
        self.assertIn('return isCantoneseMode() ? "yue"', self.js)
        self.assertIn('targetText = ($("translatedText").value || "").trim()', self.js)
        self.assertIn('formData.append("segment_mode", getSegmentMode())', self.js)

    def test_quality_and_broadcast_controls_are_present(self):
        self.assertIn('id="downloadBroadcastLink"', self.html)
        self.assertIn('id="qualityCheckBox"', self.html)
        self.assertIn('id="llmVariantSelect"', self.html)
        self.assertIn('fetchJson("/api/quality-check"', self.js)


if __name__ == "__main__":
    unittest.main()
