import unittest

from app.backend.translator import TranslationService


class CantoneseTranslationTest(unittest.TestCase):
    def test_cantonese_uses_translation_provider_instead_of_chinese_passthrough(self):
        service = object.__new__(TranslationService)
        service.provider = "aliyun"
        calls = []

        def fake_translate(text, source_language, target_language):
            calls.append((text, source_language, target_language))
            return {"translated_text": "呢段系粤语播报稿。", "target_language": "yue"}

        service._translate_aliyun = fake_translate

        result = service.translate(
            text="这是一段中文稿。",
            source_language="zh",
            target_language="yue",
        )

        self.assertEqual(result["translated_text"], "呢段系粤语播报稿。")
        self.assertEqual(calls, [("这是一段中文稿。", "zh", "yue")])


if __name__ == "__main__":
    unittest.main()
