import unittest

from app.backend.rainfall_adapter import RainfallCosyVoiceService


class FakeFrontend:
    def __init__(self):
        self.spk2info = {
            "cached": {
                "prompt_text": "prompt-token",
                "prompt_text_len": 1,
                "llm_prompt_speech_token": "speech-token",
                "llm_prompt_speech_token_len": 1,
            }
        }

    def _extract_text_token(self, text):
        return f"token:{text}", len(text)

    def frontend_zero_shot(self, tts_text, prompt_text, prompt_wav, resample_rate, zero_shot_spk_id):
        model_input = self.spk2info[zero_shot_spk_id]
        model_input["text"], model_input["text_len"] = self._extract_text_token(tts_text)
        return model_input

    def frontend_cross_lingual(self, text):
        model_input = self.frontend_zero_shot(text, "", "prompt.wav", 24000, "cached")
        del model_input["prompt_text"]
        del model_input["prompt_text_len"]
        return model_input


class RainfallPromptCacheTest(unittest.TestCase):
    def test_cross_lingual_sentences_do_not_mutate_cached_prompt(self):
        engine = type("FakeEngine", (), {"frontend": FakeFrontend()})()
        service = object.__new__(RainfallCosyVoiceService)
        service._protect_rainfall_prompt_cache(engine)
        service._protect_rainfall_prompt_cache(engine)

        first = engine.frontend.frontend_cross_lingual("第一句")
        second = engine.frontend.frontend_cross_lingual("第二句")

        self.assertEqual(first["text"], "token:第一句")
        self.assertEqual(second["text"], "token:第二句")
        self.assertIn("prompt_text", engine.frontend.spk2info["cached"])
        self.assertIn("prompt_text_len", engine.frontend.spk2info["cached"])


if __name__ == "__main__":
    unittest.main()
