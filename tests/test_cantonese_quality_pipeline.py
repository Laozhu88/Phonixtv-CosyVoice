import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.backend.rainfall_adapter import RainfallCosyVoiceService


class CantoneseQualityPipelineTest(unittest.TestCase):
    def test_sensevoice_prefers_rainfall_runtime_with_funasr(self):
        source = Path(__file__).resolve().parents[1] / "app" / "backend" / "rainfall_adapter.py"
        code = source.read_text(encoding="utf-8")
        self.assertIn("python_path = self.embedded_python if self.embedded_python.exists()", code)

    def test_quality_check_passes_matching_transcript(self):
        service = object.__new__(RainfallCosyVoiceService)
        service.transcribe_reference = lambda _: {"text": "今日香港天气晴朗。", "language": "yue"}
        with tempfile.TemporaryDirectory() as folder:
            output_dir = Path(folder)
            audio_path = output_dir / "result.wav"
            audio_path.touch()
            with patch("app.backend.rainfall_adapter.config.output_dir", output_dir):
                result = service.quality_check_generated(audio_path, "今日香港天气晴朗。")

        self.assertEqual(result["level"], "pass")
        self.assertEqual(result["score"], 100.0)

    def test_quality_check_flags_large_text_difference(self):
        service = object.__new__(RainfallCosyVoiceService)
        service.transcribe_reference = lambda _: {"text": "完全无关内容", "language": "yue"}
        with tempfile.TemporaryDirectory() as folder:
            output_dir = Path(folder)
            audio_path = output_dir / "result.wav"
            audio_path.touch()
            with patch("app.backend.rainfall_adapter.config.output_dir", output_dir):
                result = service.quality_check_generated(audio_path, "凤凰卫视新闻报道")

        self.assertEqual(result["level"], "fail")

    def test_quality_normalization_ignores_traditional_simplified_difference(self):
        service = object.__new__(RainfallCosyVoiceService)
        self.assertEqual(service._normalize_quality_text("蒙古馬位於內蒙古。"), service._normalize_quality_text("蒙古马位于内蒙古"))

    def test_broadcast_master_uses_required_pcm_spec(self):
        service = object.__new__(RainfallCosyVoiceService)
        service.rainfall_home = Path("C:/rainfall")
        with tempfile.TemporaryDirectory() as folder:
            output_dir = Path(folder)
            source = output_dir / "source.wav"
            source.touch()

            def create_output(command, **_):
                Path(command[-1]).touch()
                return type("Completed", (), {"returncode": 0, "stderr": "", "stdout": ""})()

            with patch("app.backend.rainfall_adapter.config.output_dir", output_dir), patch("app.backend.rainfall_adapter.config.rainfall_output_dir", output_dir / "ffmpeg-work"), patch.object(service, "_ffmpeg_path", return_value="ffmpeg"), patch("app.backend.rainfall_adapter.subprocess.run", side_effect=create_output) as run:
                result = service._create_broadcast_master(source, "news")

        command = run.call_args.args[0]
        self.assertIn("loudnorm=I=-23:LRA=7:TP=-2", command)
        self.assertIn("48000", command)
        self.assertIn("pcm_s24le", command)
        self.assertTrue(result["broadcast_audio_url"].endswith(".wav"))


if __name__ == "__main__":
    unittest.main()
