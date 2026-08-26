import unittest
from pathlib import Path

from app.backend.rainfall_adapter import RainfallCosyVoiceService


class CrossLingualRoutingTest(unittest.TestCase):
    def setUp(self):
        self.service = object.__new__(RainfallCosyVoiceService)
        self.service.engine_backend = "rainfall"

    def resolve(self, prompt_text, prompt_language, language="zh", dialect="mandarin"):
        return self.service._resolve_generation_mode_and_warning(
            mode="zero_shot",
            prompt_text=prompt_text,
            prompt_language=prompt_language,
            prompt_wav_path=Path("reference.wav"),
            preset_voice=None,
            language=language,
            dialect=dialect,
            scenario="news",
            instruction=None,
            speed=1.0,
        )

    def test_cantonese_reference_to_mandarin_uses_cross_lingual(self):
        mode, warning, _ = self.resolve("大家好，我系主播，而家开始新闻。", "zh")

        self.assertEqual(mode, "cross_lingual")
        self.assertIn("yue", warning)
        self.assertIn("zh", warning)

    def test_english_reference_to_mandarin_uses_cross_lingual(self):
        mode, _, _ = self.resolve("Good evening, this is the news.", "en")

        self.assertEqual(mode, "cross_lingual")

    def test_mandarin_reference_to_mandarin_keeps_zero_shot(self):
        mode, warning, _ = self.resolve("各位观众晚上好。", "zh")

        self.assertEqual(mode, "zero_shot")
        self.assertIsNone(warning)


if __name__ == "__main__":
    unittest.main()
