import unittest

from app.backend.rainfall_adapter import RainfallCosyVoiceService


class OfficialPromptFormatTest(unittest.TestCase):
    def setUp(self):
        self.service = object.__new__(RainfallCosyVoiceService)

    def test_default_instruction_uses_official_prompt_boundary(self):
        value = self.service._official_prompt_text("参考文本。", None)

        self.assertEqual(value, "You are a helpful assistant.<|endofprompt|>参考文本。")

    def test_control_instruction_is_not_double_wrapped(self):
        value = self.service._official_prompt_text(
            "参考文本。",
            "You are a helpful assistant. 请非常伤心地表达。<|endofprompt|>",
        )

        self.assertEqual(value.count("<|endofprompt|>"), 1)
        self.assertTrue(value.endswith("<|endofprompt|>参考文本。"))


if __name__ == "__main__":
    unittest.main()
