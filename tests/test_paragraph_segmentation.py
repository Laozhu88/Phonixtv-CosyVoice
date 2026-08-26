import unittest

from app.backend.rainfall_adapter import RainfallCosyVoiceService


class ParagraphSegmentationTest(unittest.TestCase):
    def setUp(self):
        self.service = object.__new__(RainfallCosyVoiceService)

    def test_sentence_punctuation_does_not_create_short_zero_shot_calls(self):
        text = "第一句话。第二句话。第三句话。第四句话。"

        segments = self.service.build_user_segments(text, auto_segment=True)

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["subsegments"], [text])

    def test_newline_still_creates_editable_main_segments(self):
        segments = self.service.build_user_segments("第一段。\n第二段。", auto_segment=True)

        self.assertEqual([item["text"] for item in segments], ["第一段。", "第二段。"])


if __name__ == "__main__":
    unittest.main()
