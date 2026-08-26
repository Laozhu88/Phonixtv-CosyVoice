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

    def test_cantonese_news_mode_builds_lossless_breath_groups(self):
        text = (
            "赛马、射箭同搏克，系内蒙古草原男子必须掌握嘅三项传统技能，被称为男儿三艺。"
            "骑马射箭结合赛马同射箭技巧，骑手需要喺马匹高速奔跑期间完成取箭、拉弓、瞄准同发射。"
        )

        segments = self.service.build_user_segments(text, auto_segment=True, segment_mode="cantonese_news")
        subsegments = segments[0]["subsegments"]

        self.assertGreater(len(subsegments), 1)
        self.assertTrue(all(len(item) <= 56 for item in subsegments))
        self.assertEqual("".join(subsegments), text)

    def test_newline_still_creates_editable_main_segments(self):
        segments = self.service.build_user_segments("第一段。\n第二段。", auto_segment=True)

        self.assertEqual([item["text"] for item in segments], ["第一段。", "第二段。"])


if __name__ == "__main__":
    unittest.main()
