from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import uuid
import zipfile

from .config import config

LANGUAGE_TEXT_MAP = {
    "zh": "中文",
    "en": "英文",
    "jp": "日语",
    "kr": "韩语",
    "de": "德语",
    "es": "西班牙语",
    "fr": "法语",
    "it": "意大利语",
    "ru": "俄语",
}

DIALECT_TEXT_MAP = {
    "mandarin": "普通话",
    "cantonese": "粤语",
    "minnan": "闽南话",
    "sichuan": "四川话",
    "dongbei": "东北话",
    "shanghai": "上海话",
    "tianjin": "天津话",
    "shandong": "山东话",
    "shanxi_jin": "山西话",
    "shaanxi": "陕西话",
    "ningxia": "宁夏话",
    "gansu": "甘肃话",
    "hunan": "湖南话",
    "henan": "河南话",
    "fuzhou": "福州话",
    "hakka": "客家话",
    "chaozhou": "潮州话",
    "jiangxi": "江西话",
    "guangxi_baihua": "广西白话",
    "guizhou": "贵州话",
    "yunnan": "云南话",
    "zhejiang": "浙江话",
    "anhui": "安徽话",
}

EXPERIMENTAL_DIALECTS = {
    "minnan", "tianjin", "shandong", "shanxi_jin", "shaanxi", "ningxia", "gansu",
    "hunan", "henan", "fuzhou", "hakka", "chaozhou", "jiangxi", "guangxi_baihua",
    "guizhou", "yunnan", "zhejiang", "anhui",
}

HIGH_RISK_DIALECTS = {
    "fuzhou",
    "hakka",
    "chaozhou",
}

EMOTION_PROFILES = {
    "natural": {
        "light": {"semitones": 0.0, "gain_db": 0.0, "lowpass": None, "highpass": None},
        "soft": {"semitones": 0.0, "gain_db": 0.0, "lowpass": None, "highpass": None},
        "medium": {"semitones": 0.0, "gain_db": 0.0, "lowpass": None, "highpass": None},
        "strong": {"semitones": 0.0, "gain_db": 0.0, "lowpass": None, "highpass": None},
        "full": {"semitones": 0.0, "gain_db": 0.0, "lowpass": None, "highpass": None},
    },
    "steady": {
        "light": {"semitones": -0.1, "gain_db": -0.2, "lowpass": 7600, "highpass": None},
        "soft": {"semitones": -0.2, "gain_db": -0.4, "lowpass": 7000, "highpass": None},
        "medium": {"semitones": -0.4, "gain_db": -0.8, "lowpass": 6200, "highpass": None},
        "strong": {"semitones": -0.7, "gain_db": -1.2, "lowpass": 5600, "highpass": None},
        "full": {"semitones": -1.0, "gain_db": -1.5, "lowpass": 5200, "highpass": None},
    },
    "serious": {
        "light": {"semitones": -0.1, "gain_db": -0.1, "lowpass": 8200, "highpass": None},
        "soft": {"semitones": -0.2, "gain_db": -0.3, "lowpass": 7600, "highpass": None},
        "medium": {"semitones": -0.5, "gain_db": -0.6, "lowpass": 6800, "highpass": None},
        "strong": {"semitones": -0.8, "gain_db": -1.0, "lowpass": 6000, "highpass": None},
        "full": {"semitones": -1.1, "gain_db": -1.4, "lowpass": 5400, "highpass": None},
    },
    "gentle": {
        "light": {"semitones": -0.2, "gain_db": -0.2, "lowpass": 7000, "highpass": None},
        "soft": {"semitones": -0.4, "gain_db": -0.4, "lowpass": 6200, "highpass": None},
        "medium": {"semitones": -0.8, "gain_db": -0.7, "lowpass": 5200, "highpass": None},
        "strong": {"semitones": -1.2, "gain_db": -1.0, "lowpass": 4300, "highpass": None},
        "full": {"semitones": -1.6, "gain_db": -1.4, "lowpass": 3600, "highpass": None},
    },
    "warm": {
        "light": {"semitones": -0.1, "gain_db": 0.2, "lowpass": 7600, "highpass": None},
        "soft": {"semitones": -0.3, "gain_db": 0.4, "lowpass": 6800, "highpass": None},
        "medium": {"semitones": -0.6, "gain_db": 0.7, "lowpass": 5600, "highpass": None},
        "strong": {"semitones": -0.9, "gain_db": 1.0, "lowpass": 4600, "highpass": None},
        "full": {"semitones": -1.2, "gain_db": 1.2, "lowpass": 4000, "highpass": None},
    },
    "uplifting": {
        "light": {"semitones": 0.4, "gain_db": 0.3, "lowpass": None, "highpass": 90},
        "soft": {"semitones": 0.8, "gain_db": 0.6, "lowpass": None, "highpass": 110},
        "medium": {"semitones": 1.4, "gain_db": 1.0, "lowpass": None, "highpass": 140},
        "strong": {"semitones": 2.1, "gain_db": 1.4, "lowpass": None, "highpass": 180},
        "full": {"semitones": 2.8, "gain_db": 1.8, "lowpass": None, "highpass": 220},
    },
    "sad": {
        "light": {"semitones": -0.6, "gain_db": -0.5, "lowpass": 5600, "highpass": None},
        "soft": {"semitones": -1.0, "gain_db": -0.8, "lowpass": 4800, "highpass": None},
        "medium": {"semitones": -1.6, "gain_db": -1.2, "lowpass": 4200, "highpass": None},
        "strong": {"semitones": -2.3, "gain_db": -1.6, "lowpass": 3600, "highpass": None},
        "full": {"semitones": -3.0, "gain_db": -2.0, "lowpass": 3200, "highpass": None},
    },
    "happy": {
        "light": {"semitones": 0.6, "gain_db": 0.4, "lowpass": None, "highpass": 100},
        "soft": {"semitones": 1.0, "gain_db": 0.8, "lowpass": None, "highpass": 120},
        "medium": {"semitones": 1.6, "gain_db": 1.2, "lowpass": None, "highpass": 150},
        "strong": {"semitones": 2.3, "gain_db": 1.6, "lowpass": None, "highpass": 190},
        "full": {"semitones": 3.0, "gain_db": 2.0, "lowpass": None, "highpass": 230},
    },
}

PRESET_VOICE_META = {
    "中文女": {"label": "系统预置 · 中文台普通话女声", "language": "zh", "dialect": "mandarin"},
    "中文男": {"label": "系统预置 · 中文台普通话男声", "language": "zh", "dialect": "mandarin"},
    "粤语女": {"label": "系统预置 · 中文台粤语女声", "language": "zh", "dialect": "cantonese"},
    "英文女": {"label": "系统预置 · 国际新闻英文女声", "language": "en", "dialect": ""},
    "英文男": {"label": "系统预置 · 国际新闻英文男声", "language": "en", "dialect": ""},
    "日语男": {"label": "系统预置 · 日语男声", "language": "jp", "dialect": ""},
    "韩语女": {"label": "系统预置 · 韩语女声", "language": "kr", "dialect": ""},
}

RAINFALL_INSTRUCT_PROMPTS = {
    "cantonese": "You are a helpful assistant. 请用广东话表达。<|endofprompt|>",
    "dongbei": "You are a helpful assistant. 请用东北话表达。<|endofprompt|>",
    "gansu": "You are a helpful assistant. 请用甘肃话表达。<|endofprompt|>",
    "guizhou": "You are a helpful assistant. 请用贵州话表达。<|endofprompt|>",
    "henan": "You are a helpful assistant. 请用河南话表达。<|endofprompt|>",
    "hunan": "You are a helpful assistant. 请用湖南话表达。<|endofprompt|>",
    "jiangxi": "You are a helpful assistant. 请用江西话表达。<|endofprompt|>",
    "minnan": "You are a helpful assistant. 请用闽南话表达。<|endofprompt|>",
    "ningxia": "You are a helpful assistant. 请用宁夏话表达。<|endofprompt|>",
    "shanxi_jin": "You are a helpful assistant. 请用山西话表达。<|endofprompt|>",
    "shaanxi": "You are a helpful assistant. 请用陕西话表达。<|endofprompt|>",
    "shandong": "You are a helpful assistant. 请用山东话表达。<|endofprompt|>",
    "shanghai": "You are a helpful assistant. 请用上海话表达。<|endofprompt|>",
    "sichuan": "You are a helpful assistant. 请用四川话表达。<|endofprompt|>",
    "tianjin": "You are a helpful assistant. 请用天津话表达。<|endofprompt|>",
    "yunnan": "You are a helpful assistant. 请用云南话表达。<|endofprompt|>",
}


@dataclass
class BundleStatus:
    rainfall_home: str
    embedded_python: str
    model_dir: str
    available: bool
    message: str
    engine_backend: str = "rainfall"


class RainfallCosyVoiceService:
    def __init__(self) -> None:
        self.engine_backend = (config.engine_backend or "rainfall").strip().lower()
        self.rainfall_home = config.rainfall_home
        self.embedded_python = self.rainfall_home / "python" / "python.exe"
        self.official_root = config.official_cosyvoice_root
        self.official_model_dir = config.official_model_dir
        self.model_dir = self.official_model_dir if self.engine_backend == "official" else config.rainfall_model_dir
        self._engine = None
        self._torch = None
        self._torchaudio = None
        self._history_lock = threading.Lock()
        self._template_lock = threading.Lock()
        self._voice_lock = threading.Lock()
        self._prompt_cache_lock = threading.Lock()
        self._registered_prompt_speakers: set[str] = set()
        self._prompt_embedding_cache: dict[str, object] = {}
        self._engine_runtime: dict[str, object] = {"fp16": False, "cuda": False, "llm_variant": "not_loaded"}
        self._preset_embedding_cache: dict[str, object] = {}

    def bundle_status(self) -> BundleStatus:
        if self.engine_backend == "official":
            available = self.official_root.exists() and self.model_dir.exists()
            message = "Official CosyVoice backend detected and ready for Phoenix cloud workstation." if available else "Official CosyVoice backend not found. Check PHOENIX_OFFICIAL_COSYVOICE_ROOT and PHOENIX_OFFICIAL_MODEL_DIR."
        else:
            available = self.rainfall_home.exists() and self.embedded_python.exists() and self.model_dir.exists()
            message = "Rainfall bundle detected and ready for Phoenix workstation." if available else "Rainfall bundle not found. Check PHOENIX_RAINFALL_HOME."
        return BundleStatus(
            rainfall_home=str(self.rainfall_home),
            embedded_python=str(self.embedded_python),
            model_dir=str(self.model_dir),
            available=available,
            message=message,
            engine_backend=self.engine_backend,
        )

    def runtime_status(self) -> dict:
        cuda_available = False
        device_name = ""
        try:
            self._ensure_import_paths()
            torch = self._torch
            if torch is None:
                import torch as imported_torch
                torch = imported_torch
                self._torch = imported_torch
            cuda_available = bool(torch.cuda.is_available())
            if cuda_available:
                device_name = torch.cuda.get_device_name(0)
        except Exception:
            cuda_available = False
            device_name = ""
        return {
            "cuda_available": cuda_available,
            "fp16_available": cuda_available,
            "cuda_active": bool(self._engine_runtime.get("cuda")),
            "fp16_active": bool(self._engine_runtime.get("fp16")),
            "engine_initialized": self._engine is not None,
            "device_name": device_name,
            "llm_variant": str(self._engine_runtime.get("llm_variant") or "not_loaded"),
        }

    def capabilities(self) -> dict:
        return {
            "languages": [
                {"value": "zh", "label": "中文"},
                {"value": "en", "label": "英文"},
                {"value": "jp", "label": "日语"},
                {"value": "kr", "label": "韩语"},
                {"value": "de", "label": "德语"},
                {"value": "es", "label": "西班牙语"},
                {"value": "fr", "label": "法语"},
                {"value": "it", "label": "意大利语"},
                {"value": "ru", "label": "俄语"},
            ],
            "dialects": [
                {"value": "mandarin", "label": "普通话", "group": "recommended"},
                {"value": "cantonese", "label": "粤语 / 广东话", "group": "recommended"},
                {"value": "sichuan", "label": "四川话", "group": "recommended"},
                {"value": "dongbei", "label": "东北话", "group": "recommended"},
                {"value": "shanghai", "label": "上海话", "group": "recommended"},
                {"value": "henan", "label": "河南话", "group": "experimental"},
                {"value": "minnan", "label": "闽南话", "group": "experimental"},
                {"value": "tianjin", "label": "天津话", "group": "experimental"},
                {"value": "shandong", "label": "山东话", "group": "experimental"},
                {"value": "shanxi_jin", "label": "山西话", "group": "experimental"},
                {"value": "shaanxi", "label": "陕西话", "group": "experimental"},
                {"value": "ningxia", "label": "宁夏话", "group": "experimental"},
                {"value": "gansu", "label": "甘肃话", "group": "experimental"},
                {"value": "hunan", "label": "湖南话", "group": "experimental"},
                {"value": "fuzhou", "label": "福州话", "group": "experimental"},
                {"value": "hakka", "label": "客家话", "group": "experimental"},
                {"value": "chaozhou", "label": "潮州话", "group": "experimental"},
                {"value": "jiangxi", "label": "江西话", "group": "experimental"},
                {"value": "guangxi_baihua", "label": "广西白话", "group": "experimental"},
                {"value": "guizhou", "label": "贵州话", "group": "experimental"},
                {"value": "yunnan", "label": "云南话", "group": "experimental"},
                {"value": "zhejiang", "label": "浙江话", "group": "experimental"},
                {"value": "anhui", "label": "安徽话", "group": "experimental"},
            ],
            "dialect_guidance": {
                "default": "推荐先用一两句短文本试听，再决定是否用于整篇配音。",
                "recommended": "当前方言为推荐可用档，整体更稳，适合继续试听与细调。",
                "experimental": "当前方言建议先试听，效果可能因文稿和音色不同而波动。",
                "high_risk": "当前方言建议先试听，公开模型可能更接近带口音普通话，建议先用短句确认效果。",
            },
            "segment_modes": [
                {"value": "natural", "label": "自然分段（按回车）"},
            ],
            "modes": [
                {"value": "zero_shot", "label": "参考音色播报"},
                {"value": "cross_lingual", "label": "跨语种 / 多方言"},
            ],
            "engine_features": [
                "zero_shot",
                "cross_lingual",
                "instruct",
                "voice_conversion",
                "embedding_ready",
                "paragraph_segment_workflow",
                "reference_audio_asr",
                "reference_wave_preview",
            ],
        }

    def _ensure_import_paths(self) -> None:
        if self.engine_backend == "official":
            candidates = [
                self.official_root,
                self.official_root / "third_party" / "Matcha-TTS",
            ]
        else:
            candidates = [
                self.rainfall_home,
                self.rainfall_home / "python" / "Lib" / "site-packages",
                self.rainfall_home / "python" / "Lib",
                self.rainfall_home / "python" / "DLLs",
                self.rainfall_home / "third_party" / "Matcha-TTS",
            ]
        for path in candidates:
            path_str = str(path)
            if path.exists() and path_str not in sys.path:
                sys.path.insert(0, path_str)

    def _protect_rainfall_prompt_cache(self, engine) -> None:
        frontend = getattr(engine, "frontend", None)
        if frontend is None or getattr(frontend, "_phoenix_prompt_cache_safe", False):
            return
        original = getattr(frontend, "frontend_zero_shot", None)
        if not callable(original):
            return

        def safe_frontend_zero_shot(tts_text, prompt_text, prompt_wav, resample_rate, zero_shot_spk_id):
            if not zero_shot_spk_id:
                return original(tts_text, prompt_text, prompt_wav, resample_rate, zero_shot_spk_id)
            text_token, text_token_len = frontend._extract_text_token(tts_text)
            model_input = dict(frontend.spk2info[zero_shot_spk_id])
            model_input["text"] = text_token
            model_input["text_len"] = text_token_len
            return model_input

        frontend.frontend_zero_shot = safe_frontend_zero_shot
        frontend._phoenix_prompt_cache_safe = True

    def _ensure_engine(self):
        if self._engine is not None:
            return self._engine
        self._ensure_import_paths()
        import torch
        import torchaudio
        self._torch = torch
        self._torchaudio = torchaudio
        cuda_available = bool(torch.cuda.is_available())
        if self.engine_backend == "official":
            from cosyvoice.cli.cosyvoice import AutoModel
            self._engine_runtime = {"fp16": False, "cuda": cuda_available, "llm_variant": "official"}
            self._engine = AutoModel(model_dir=str(self.model_dir))
        else:
            from cosyvoice.cli.cosyvoice import CosyVoice3
            rl_model_path = self.model_dir / "llm.rl.pt"
            if not rl_model_path.exists():
                raise FileNotFoundError(f"CosyVoice3 RL model not found: {rl_model_path}")
            self._engine_runtime = {"fp16": cuda_available, "cuda": cuda_available, "llm_variant": "loading_rl"}
            try:
                self._engine = CosyVoice3(str(self.model_dir), load_trt=False, load_vllm=False, fp16=cuda_available)
                rl_state_dict = torch.load(str(rl_model_path), map_location="cpu")
                self._engine.model.llm.load_state_dict(rl_state_dict, strict=True)
                self._engine.model.llm.to(self._engine.model.device).eval()
                del rl_state_dict
                self._engine_runtime["llm_variant"] = "rl"
            except Exception:
                self._engine = None
                self._engine_runtime["llm_variant"] = "load_failed"
                raise
            self._protect_rainfall_prompt_cache(self._engine)
        return self._engine

    def available_speakers(self) -> list[str]:
        try:
            self._ensure_import_paths()
            import torch
            spk_file = self.model_dir / "spk2info.pt"
            if not spk_file.exists():
                return []
            payload = torch.load(str(spk_file), map_location="cpu")
            return list(payload.keys())
        except Exception:
            return []

    def list_preset_voices(self) -> list[dict]:
        if self.engine_backend == "official":
            return []
        preset_dir = self.rainfall_home / "resources" / "sft_audios"
        items: list[dict] = []
        for name, meta in PRESET_VOICE_META.items():
            pt_path = preset_dir / f"{name}.pt"
            if not pt_path.exists():
                continue
            items.append({
                "id": f"preset:{name}",
                "name": name,
                "label": meta["label"],
                "language": meta.get("language", ""),
                "dialect": meta.get("dialect", ""),
                "kind": "preset",
                "audio_url": "",
                "transcript": "",
                "created_at": "",
                "pinned_at": None,
            })
        return items

    def get_preset_voice(self, voice_id: str | None) -> dict | None:
        if self.engine_backend == "official":
            return None
        if not voice_id or not str(voice_id).startswith("preset:"):
            return None
        preset_name = str(voice_id).split(":", 1)[1]
        meta = PRESET_VOICE_META.get(preset_name)
        if not meta:
            return None
        pt_path = self.rainfall_home / "resources" / "sft_audios" / f"{preset_name}.pt"
        if not pt_path.exists():
            return None
        return {
            "id": f"preset:{preset_name}",
            "name": preset_name,
            "label": meta["label"],
            "language": meta.get("language", ""),
            "dialect": meta.get("dialect", ""),
            "kind": "preset",
            "pt_path": pt_path,
        }

    def _load_preset_embedding(self, preset_name: str):
        if preset_name in self._preset_embedding_cache:
            return self._preset_embedding_cache[preset_name]
        self._ensure_engine()
        pt_path = self.rainfall_home / "resources" / "sft_audios" / f"{preset_name}.pt"
        payload = self._torch.load(str(pt_path), map_location="cpu")
        if isinstance(payload, dict) and preset_name in payload and isinstance(payload[preset_name], dict) and "embedding" in payload[preset_name]:
            embedding = payload[preset_name]["embedding"]
        else:
            raise ValueError(f"预置音色 {preset_name} 的 embedding 不存在。")
        self._preset_embedding_cache[preset_name] = embedding
        return embedding

    def load_history(self, limit: int = 10) -> list[dict]:
        with self._history_lock:
            try:
                data = json.loads(config.history_path.read_text(encoding="utf-8"))
            except Exception:
                return []
        records = [item for item in data if isinstance(item, dict)]
        records.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return records[:limit]

    def save_history(self, payload: dict) -> dict:
        record = {
            "id": payload.get("id") or uuid.uuid4().hex,
            "created_at": payload.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "text": payload.get("text") or "",
            "text_preview": payload.get("text_preview") or (payload.get("text") or "")[:120],
            "translated_text": payload.get("translated_text") or "",
            "translated_preview": payload.get("translated_preview") or (payload.get("translated_text") or "")[:120],
            "language": payload.get("language") or "zh",
            "dialect": payload.get("dialect") or "",
            "mode": payload.get("mode") or "zero_shot",
            "speech_rate": payload.get("speech_rate") or "1.00",
            "auto_segment_used": bool(payload.get("auto_segment_used", False)),
            "segment_mode": payload.get("segment_mode") or "natural",
            "segments_count": int(payload.get("segments_count") or 1),
            "audio_url": payload.get("audio_url") or "",
            "zip_url": payload.get("zip_url") or "",
            "segments": payload.get("segments") or [],
            "result_state": payload.get("result_state") or "原始版",
            "voice_id": payload.get("voice_id") or "",
            "voice_name": payload.get("voice_name") or "",
            "voice_kind": payload.get("voice_kind") or "",
            "prompt_text": payload.get("prompt_text") or "",
            "prompt_language": payload.get("prompt_language") or "",
            "history_prompt_audio_url": payload.get("history_prompt_audio_url") or "",
            "history_prompt_audio_name": payload.get("history_prompt_audio_name") or "",
            "prompt_clip_active": bool(payload.get("prompt_clip_active", False)),
            "prompt_clip_start": payload.get("prompt_clip_start") or "0.00",
            "prompt_clip_end": payload.get("prompt_clip_end") or "0.00",
            "instruction": payload.get("instruction") or "",
            "style": payload.get("style") or "natural",
        }
        with self._history_lock:
            try:
                existing = json.loads(config.history_path.read_text(encoding="utf-8"))
                if not isinstance(existing, list):
                    existing = []
            except Exception:
                existing = []
            existing = [item for item in existing if isinstance(item, dict) and item.get("id") != record["id"]]
            existing.insert(0, record)
            config.history_path.write_text(json.dumps(existing[:10], ensure_ascii=False, indent=2), encoding="utf-8")
        return record

    def list_voices(self) -> list[dict]:
        with self._voice_lock:
            try:
                data = json.loads(config.voice_meta_path.read_text(encoding="utf-8"))
            except Exception:
                return []
        voices = [item for item in data if isinstance(item, dict)]
        for item in voices:
            item.setdefault("kind", "saved")
        voices.sort(
            key=lambda item: (
                1 if item.get("pinned_at") else 0,
                item.get("pinned_at") or "",
                item.get("created_at") or "",
            ),
            reverse=True,
        )
        return voices

    def list_templates(self) -> list[dict]:
        with self._template_lock:
            try:
                data = json.loads(config.template_meta_path.read_text(encoding="utf-8"))
            except Exception:
                return []
        templates = []
        for item in data:
            if not isinstance(item, dict):
                continue
            normalized = dict(item)
            normalized["name"] = self._normalize_template_name(item.get("name") or "")
            templates.append(normalized)
        templates.sort(key=lambda item: (item.get("updated_at") or "", item.get("name") or ""), reverse=True)
        deduped: list[dict] = []
        seen_names: set[str] = set()
        for item in templates:
            name = (item.get("name") or "").strip()
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            deduped.append(item)
        return deduped

    def _normalize_template_name(self, value: str) -> str:
        name = (value or "").strip()
        if not name:
            return ""
        if name.endswith("模版"):
            name = f"{name[:-2]}模板"
        elif not name.endswith("模板"):
            name = f"{name}模板"
        return name

    def save_template(self, payload: dict) -> dict:
        name = self._normalize_template_name(payload.get("name") or "")
        if not name:
            raise ValueError("模板名称不能为空。")
        record = {
            "id": payload.get("id") or uuid.uuid4().hex,
            "name": name,
            "language": payload.get("language") or "zh",
            "dialect": payload.get("dialect") or "",
            "speech_rate": payload.get("speech_rate") or "1.00",
            "style": payload.get("style") or "natural",
            "instruction": payload.get("instruction") or "",
            "voice_id": payload.get("voice_id") or "",
            "voice_name": payload.get("voice_name") or "",
            "voice_kind": payload.get("voice_kind") or "",
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        with self._template_lock:
            try:
                existing = json.loads(config.template_meta_path.read_text(encoding="utf-8"))
                if not isinstance(existing, list):
                    existing = []
            except Exception:
                existing = []
            existing = [
                item
                for item in existing
                if isinstance(item, dict) and (item.get("name") or "").strip() != name
            ]
            same_name = next((item for item in existing if isinstance(item, dict) and item.get("id") == record["id"]), None)
            if same_name:
                same_name.update(record)
                record = same_name
            else:
                existing.append(record)
            config.template_meta_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        return record

    def delete_template(self, template_id: str) -> None:
        with self._template_lock:
            try:
                existing = json.loads(config.template_meta_path.read_text(encoding="utf-8"))
                if not isinstance(existing, list):
                    existing = []
            except Exception:
                existing = []
            target = next((item for item in existing if isinstance(item, dict) and item.get("id") == template_id), None)
            if not target:
                raise ValueError("未找到该模板。")
            existing = [item for item in existing if not (isinstance(item, dict) and item.get("id") == template_id)]
            config.template_meta_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_voice(self, voice_id: str | None) -> dict | None:
        if not voice_id:
            return None
        return next((item for item in self.list_voices() if item.get("id") == voice_id), None)

    def resolve_voice_prompt(
        self,
        *,
        voice_id: str | None,
        prompt_text: str | None,
        prompt_wav_path: Path | None,
    ) -> tuple[str | None, Path | None, dict | None]:
        resolved_text = (prompt_text or "").strip() or None
        resolved_path = prompt_wav_path
        voice = self.get_voice(voice_id)
        if voice is None:
            return resolved_text, resolved_path, None
        if resolved_path is None and voice.get("audio_filename"):
            candidate = config.voice_audio_dir / voice["audio_filename"]
            if candidate.exists():
                resolved_path = candidate
        if not resolved_text:
            resolved_text = (voice.get("transcript") or "").strip() or None
        return resolved_text, resolved_path, voice

    def save_voice(self, *, name: str, transcript: str, audio_path: Path, source_filename: str | None = None, prompt_language: str | None = None) -> dict:
        voice_name = (name or "").strip()
        if not voice_name:
            raise ValueError("音色名称不能为空。")
        with self._voice_lock:
            try:
                existing = json.loads(config.voice_meta_path.read_text(encoding="utf-8"))
                if not isinstance(existing, list):
                    existing = []
            except Exception:
                existing = []
            if any(item.get("name") == voice_name for item in existing if isinstance(item, dict)):
                raise ValueError("已存在同名音色，请换一个名称。")
            ext = audio_path.suffix.lower() or ".wav"
            voice_id = uuid.uuid4().hex
            stored_filename = f"{voice_id}{ext}"
            stored_path = config.voice_audio_dir / stored_filename
            shutil.copyfile(audio_path, stored_path)
            item = {
                "id": voice_id,
                "name": voice_name,
                "kind": "saved",
                "transcript": (transcript or "").strip(),
                "prompt_language": (prompt_language or "").strip(),
                "audio_filename": stored_filename,
                "audio_url": f"/voice-library/audio/{stored_filename}",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "pinned_at": None,
                "source_filename": source_filename or audio_path.name,
            }
            existing.append(item)
            config.voice_meta_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        return item

    def pin_voice(self, voice_id: str) -> dict:
        with self._voice_lock:
            try:
                existing = json.loads(config.voice_meta_path.read_text(encoding="utf-8"))
                if not isinstance(existing, list):
                    existing = []
            except Exception:
                existing = []
            target = next((item for item in existing if isinstance(item, dict) and item.get("id") == voice_id), None)
            if not target:
                raise ValueError("未找到该音色。")
            target["pinned_at"] = None if target.get("pinned_at") else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            config.voice_meta_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
            return target

    def delete_voice(self, voice_id: str) -> None:
        with self._voice_lock:
            try:
                existing = json.loads(config.voice_meta_path.read_text(encoding="utf-8"))
                if not isinstance(existing, list):
                    existing = []
            except Exception:
                existing = []
            target = next((item for item in existing if isinstance(item, dict) and item.get("id") == voice_id), None)
            if not target:
                raise ValueError("未找到该音色。")
            if target.get("audio_filename"):
                audio_path = config.voice_audio_dir / target["audio_filename"]
                if audio_path.exists():
                    try:
                        audio_path.unlink()
                    except Exception:
                        pass
            existing = [item for item in existing if not (isinstance(item, dict) and item.get("id") == voice_id)]
            config.voice_meta_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    def transcribe_reference(self, audio_path: Path) -> dict:
        if self._resolve_sensevoice_model_dir() is not None:
            return self._transcribe_reference_with_sensevoice(audio_path)
        if self.engine_backend == "official":
            raise ValueError(f"未找到本地 SenseVoiceSmall 模型：{self._sensevoice_model_candidates()[0]}")
        python_path = config.asr_python
        if not python_path.exists():
            raise ValueError(f"未找到 ASR 运行时：{python_path}")
        script = (
            "import json, sys; "
            "from faster_whisper import WhisperModel; "
            f"model = WhisperModel({config.asr_model!r}, device='cpu', compute_type='int8'); "
            "segments, info = model.transcribe(sys.argv[1], language='zh', beam_size=5, vad_filter=True); "
            "text = ''.join(seg.text for seg in segments).strip(); "
            "print(json.dumps({'text': text, 'language': getattr(info, 'language', 'zh')}, ensure_ascii=False))"
        )
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        try:
            completed = subprocess.run(
                [str(python_path), "-c", script, str(audio_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=240,
                check=True,
                env=env,
            )
        except subprocess.CalledProcessError as exc:
            detail = ((exc.stderr or exc.stdout or "")[-800:]).strip()
            raise RuntimeError(f"参考音频识别失败：{detail or exc}") from exc
        stdout = (completed.stdout or "").strip()
        if not stdout:
            raise RuntimeError("识别结果为空。")
        payload = json.loads(stdout.splitlines()[-1])
        return {"text": (payload.get("text") or "").strip(), "language": payload.get("language") or "zh"}

    def _clean_sensevoice_text(self, text: str) -> str:
        clean = re.sub(r"<\|[^|]+?\|>", "", text or "")
        clean = re.sub(r"\s+", "", clean)
        return clean.strip()

    def _sensevoice_model_candidates(self) -> list[Path]:
        return [
            self.rainfall_home / "models" / "SenseVoiceSmall",
            config.workspace_root / "models" / "SenseVoiceSmall",
            config.workspace_root / "release_staging" / "PhoenixTV-IndexTTS-Cloud-V1" / "models" / "SenseVoiceSmall",
            config.workspace_root / "release_staging" / "凤凰卫视中文台多语种、多方言智能配音工作台_V1" / "runtime" / "rainfall" / "models" / "SenseVoiceSmall",
        ]

    def _resolve_sensevoice_model_dir(self) -> Path | None:
        for model_dir in self._sensevoice_model_candidates():
            if (model_dir / "model.pt").exists():
                return model_dir
        return None

    def _transcribe_reference_with_sensevoice(self, audio_path: Path) -> dict:
        model_dir = self._resolve_sensevoice_model_dir()
        if model_dir is None:
            raise ValueError(f"未找到本地 SenseVoiceSmall 模型：{self._sensevoice_model_candidates()[0]}")
        python_path = Path(config.asr_python)
        script = r'''
import json
import re
import sys
from funasr import AutoModel
try:
    import torch
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
except Exception:
    device = "cpu"

model_dir = sys.argv[1]
audio_path = sys.argv[2]
model = AutoModel(
    model=model_dir,
    trust_remote_code=True,
    disable_update=True,
    device=device,
)
res = model.generate(
    input=audio_path,
    language="auto",
    use_itn=True,
    batch_size_s=60,
)
text = ""
language = ""
if isinstance(res, list) and res:
    first = res[0]
    if isinstance(first, dict):
        text = first.get("text") or ""
        language = first.get("language") or ""
elif isinstance(res, dict):
    text = res.get("text") or ""
    language = res.get("language") or ""
language_match = re.search(r"<\|(zh|en|yue|ja|ko|nospeech)\|>", text)
if language_match:
    language = language_match.group(1)
text = re.sub(r"<\|[^|]+?\|>", "", text or "")
text = re.sub(r"\s+", "", text).strip()
print(json.dumps({"text": text, "language": language or "zh"}, ensure_ascii=False))
'''
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        try:
            completed = subprocess.run(
                [str(python_path), "-c", script, str(model_dir), str(audio_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=240,
                check=True,
                env=env,
            )
        except subprocess.CalledProcessError as exc:
            detail = ((exc.stderr or exc.stdout or "")[-1200:]).strip()
            raise RuntimeError(f"SenseVoice 识别失败：{detail or exc}") from exc
        stdout = (completed.stdout or "").strip()
        if not stdout:
            raise RuntimeError("SenseVoice 识别结果为空。")
        payload = json.loads(stdout.splitlines()[-1])
        return {"text": self._clean_sensevoice_text(payload.get("text") or ""), "language": payload.get("language") or "zh"}

    def split_text_for_tts(self, text: str, mode: str = "natural") -> list[str]:
        text = re.sub(r"\r\n?|\n", "\n", text or "").strip()
        if not text:
            return []
        if mode == "cantonese_news":
            units = [item.strip() for item in re.findall(r"[^。！？!?；;\n]+[。！？!?；;]?[”’」』】）》〕]*", text) if item.strip()]
            chunks: list[str] = []
            current = ""
            for unit in units:
                pieces = [unit]
                if len(unit) > 56:
                    pieces = [item.strip() for item in re.findall(r"[^，,、：:]+[，,、：:]?", unit) if item.strip()]
                for piece in pieces:
                    if current and len(current) + len(piece) > 56:
                        chunks.append(current)
                        current = piece
                    else:
                        current += piece
                    if re.search(r"[。！？!?；;]$", current) and len(current) >= 24:
                        chunks.append(current)
                        current = ""
            if current:
                chunks.append(current)
            return chunks or [text]
        return [item.strip() for item in re.split(r"\n+", text) if item and item.strip()]

    def split_text_by_paragraphs(self, text: str) -> list[str]:
        text = (text or "").replace("\u2028", "\n").replace("\u2029", "\n").replace("\x85", "\n")
        text = re.sub(r"\r\n?|\n", "\n", text)
        if not text.strip():
            return []
        return [item.strip() for item in re.split(r"\n+", text) if item and item.strip()]

    def build_user_segments(self, text: str, auto_segment: bool, segment_mode: str = "natural") -> list[dict]:
        clean = (text or "").strip()
        if not clean:
            return []
        if not auto_segment:
            return [{"index": 1, "text": clean, "subsegments": self.split_text_for_tts(clean, mode=segment_mode) or [clean]}]
        return [{"index": idx, "text": para, "subsegments": self.split_text_for_tts(para, mode=segment_mode) or [para]} for idx, para in enumerate(self.split_text_by_paragraphs(clean), start=1)]

    def preview_segments(self, text: str, auto_segment: bool, segment_mode: str = "natural") -> dict:
        user_segments = self.build_user_segments(text, auto_segment, segment_mode)
        return {
            "auto_segment_used": auto_segment,
            "segment_mode": segment_mode,
            "segments_count": len(user_segments),
            "segments": [{"index": seg["index"], "text": seg["text"], "subsegments": seg["subsegments"], "subsegments_count": len(seg["subsegments"])} for seg in user_segments],
        }

    def _concat_tensors(self, tensors: list, add_pause: bool = False, pause_seconds: float | None = None):
        if len(tensors) == 1:
            return tensors[0]
        sample_rate = self._engine.sample_rate
        chunks = []
        pause_length = pause_seconds if pause_seconds is not None else (0.12 if add_pause else 0.0)
        pause = self._torch.zeros((1, max(1, int(sample_rate * max(0.0, pause_length)))), dtype=tensors[0].dtype) if pause_length > 0 else None
        for index, tensor in enumerate(tensors):
            chunks.append(tensor)
            if pause is not None and index < len(tensors) - 1:
                chunks.append(pause)
        return self._torch.cat(chunks, dim=1)

    def _concat_spoken_subsegments(self, tensors: list, texts: list[str]):
        if len(tensors) <= 1:
            return tensors[0]
        chunks = []
        sample_rate = self._engine.sample_rate
        for index, tensor in enumerate(tensors):
            chunks.append(tensor)
            if index >= len(tensors) - 1:
                continue
            previous_text = texts[index].rstrip()
            if re.search(r"[。！？!?]$", previous_text):
                pause_seconds = 0.28
            elif re.search(r"[；;]$", previous_text):
                pause_seconds = 0.20
            else:
                pause_seconds = 0.14
            chunks.append(self._torch.zeros((1, int(sample_rate * pause_seconds)), dtype=tensor.dtype))
        return self._torch.cat(chunks, dim=1)

    def _write_pcm_wav(self, out_path: Path, speech) -> None:
        # Use 16-bit PCM for broad browser/player compatibility.
        pcm = speech.detach().cpu()
        pcm = self._torch.clamp(pcm, -0.999, 0.999)
        self._torchaudio.save(
            str(out_path),
            pcm,
            self._engine.sample_rate,
            format="wav",
            encoding="PCM_S",
            bits_per_sample=16,
        )

    def _get_emotion_profile(self, style: str | None, intensity: str | None) -> dict:
        style_key = (style or "natural").strip() or "natural"
        intensity_key = (intensity or "medium").strip() or "medium"
        return EMOTION_PROFILES.get(style_key, EMOTION_PROFILES["natural"]).get(intensity_key, EMOTION_PROFILES["natural"]["medium"])

    def _apply_emotion_profile(self, speech, *, style: str | None, intensity: str | None):
        profile = self._get_emotion_profile(style, intensity)
        if not any(profile.values()):
            return speech
        processed = speech.detach().cpu()
        sample_rate = self._engine.sample_rate
        semitones = float(profile.get("semitones") or 0.0)
        gain_db = float(profile.get("gain_db") or 0.0)
        lowpass = profile.get("lowpass")
        highpass = profile.get("highpass")
        try:
            if abs(semitones) > 0.01:
                processed = self._torchaudio.functional.pitch_shift(processed, sample_rate, semitones)
            if lowpass:
                processed = self._torchaudio.functional.lowpass_biquad(processed, sample_rate, float(lowpass))
            if highpass:
                processed = self._torchaudio.functional.highpass_biquad(processed, sample_rate, float(highpass))
            if abs(gain_db) > 0.01:
                processed = self._torchaudio.functional.gain(processed, gain_db)
            peak = float(processed.abs().max().item()) if processed.numel() else 0.0
            if peak > 0.98:
                processed = processed * (0.98 / peak)
        except Exception:
            return speech
        return processed

    def _save_tensor_to_output(self, speech, prefix: str) -> tuple[str, Path]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{prefix}_{timestamp}_{uuid.uuid4().hex[:8]}.wav"
        out_path = config.output_dir / file_name
        self._write_pcm_wav(out_path, speech)
        return file_name, out_path

    def _normalize_output_name(self, value: str | None) -> str:
        text = (value or "").strip()
        if not text:
            return ""
        text = re.sub(r'[\\/:*?"<>|\r\n]+', "", text)
        text = re.sub(r"\s+", "_", text).strip(" ._")
        return text[:80]

    def _build_named_output_filename(self, base_name: str | None, fallback_prefix: str, *, suffix: str = "", ext: str = ".wav") -> str:
        normalized = self._normalize_output_name(base_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if normalized:
            suffix_text = f"_{suffix}" if suffix else ""
            return f"{normalized}{suffix_text}_{timestamp}{ext}"
        random_part = uuid.uuid4().hex[:8]
        return f"{fallback_prefix}_{timestamp}_{random_part}{ext}"

    def _build_control_instruction(self, *, language: str | None, dialect: str | None, scenario: str | None, instruction: str | None, speed: float) -> str | None:
        explicit = (instruction or "").strip()
        language_value = (language or "zh").strip() or "zh"
        dialect_value = (dialect or "mandarin").strip() or "mandarin"

        def instruction_body(value: str) -> str:
            normalized = value.strip()
            prefix = "You are a helpful assistant."
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
            return normalized.replace("<|endofprompt|>", "").strip()

        clauses = []
        if language_value == "zh" and dialect_value != "mandarin":
            dialect_prompt = RAINFALL_INSTRUCT_PROMPTS.get(dialect_value)
            if dialect_prompt:
                clauses.append(instruction_body(dialect_prompt))
            else:
                dialect_text = DIALECT_TEXT_MAP.get(dialect_value, "")
                if dialect_text:
                    clauses.append(f"请用{dialect_text}表达。")
        elif language_value != "zh":
            lang_text = LANGUAGE_TEXT_MAP.get(language_value, "中文")
            clauses.append(f"请用{lang_text}表达。")

        if language_value == "zh" and dialect_value == "cantonese" and (scenario or "").strip().lower() == "news":
            clauses.append("请采用香港电视新闻播报语气，沉稳自然，停连清楚，避免普通话腔。")

        if explicit:
            reverse_dialect_map = {label: key for key, label in DIALECT_TEXT_MAP.items()}
            mapped_key = reverse_dialect_map.get(explicit) or reverse_dialect_map.get(explicit.replace(" / 广东话", "")) or reverse_dialect_map.get(explicit.replace(" / 广东话", ""))
            if mapped_key and mapped_key in RAINFALL_INSTRUCT_PROMPTS:
                explicit = RAINFALL_INSTRUCT_PROMPTS[mapped_key]
            elif explicit in RAINFALL_INSTRUCT_PROMPTS:
                explicit = RAINFALL_INSTRUCT_PROMPTS[explicit]
            explicit_body = instruction_body(explicit)
            if explicit_body and explicit_body not in clauses:
                clauses.append(explicit_body)

        if not clauses:
            return None
        return f"You are a helpful assistant. {' '.join(clauses)}<|endofprompt|>"

    def _build_prompt_cache_key(self, *, mode: str, cache_text: str, prompt_wav_path: Path, voice_id: str | None) -> str:
        stat = prompt_wav_path.stat()
        source = "|".join([
            mode,
            voice_id or "",
            str(prompt_wav_path.resolve()),
            str(stat.st_mtime_ns),
            str(stat.st_size),
            cache_text,
        ])
        digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:16]
        return f"{mode}_{digest}"

    def _ensure_cached_prompt_speaker(self, *, mode: str, cache_text: str, prompt_wav_path: Path | None, voice_id: str | None) -> str:
        if prompt_wav_path is None:
            return ""
        engine = self._ensure_engine()
        normalized_cache_text = cache_text or "保持音色一致"
        cache_key = self._build_prompt_cache_key(mode=mode, cache_text=normalized_cache_text, prompt_wav_path=prompt_wav_path, voice_id=voice_id)
        with self._prompt_cache_lock:
            if cache_key not in self._registered_prompt_speakers:
                engine.add_zero_shot_spk(normalized_cache_text, str(prompt_wav_path), cache_key)
                self._registered_prompt_speakers.add(cache_key)
        return cache_key

    def _extract_prompt_embedding(self, *, prompt_wav_path: Path | None, voice_id: str | None):
        if prompt_wav_path is None:
            raise ValueError("instruct mode requires a prompt audio file")
        engine = self._ensure_engine()
        cache_key = self._build_prompt_cache_key(
            mode="embedding",
            cache_text="",
            prompt_wav_path=prompt_wav_path,
            voice_id=voice_id,
        )
        with self._prompt_cache_lock:
            if cache_key not in self._prompt_embedding_cache:
                self._prompt_embedding_cache[cache_key] = engine.frontend._extract_spk_embedding(str(prompt_wav_path))
        return self._prompt_embedding_cache[cache_key]

    def _official_prompt_text(self, prompt_text: str | None, control_instruction: str | None) -> str:
        transcript = (prompt_text or "").strip() or "这是一段参考音频，用于保持说话人的音色和语气。"
        instruction = (control_instruction or "").strip()
        if not instruction:
            instruction = "You are a helpful assistant.<|endofprompt|>"
        elif "<|endofprompt|>" not in instruction:
            instruction = f"{instruction}<|endofprompt|>"
        return f"{instruction}{transcript}"

    def _official_iterator(self, *, text: str, mode: str, prompt_text: str | None, prompt_wav_path: Path | None, control_instruction: str | None, speed: float):
        engine = self._ensure_engine()
        if prompt_wav_path is None:
            raise ValueError("official CosyVoice backend requires prompt audio for current cloud mode")
        normalized_prompt = self._official_prompt_text(prompt_text, control_instruction)
        try:
            return engine.inference_zero_shot(
                text,
                normalized_prompt,
                str(prompt_wav_path),
                stream=False,
                speed=speed,
            )
        except TypeError:
            return engine.inference_zero_shot(text, normalized_prompt, str(prompt_wav_path), stream=False)

    def _synthesize_text(self, *, text: str, mode: str, prompt_text: str | None, prompt_wav_path: Path | None, speed: float, text_frontend: bool, instruction: str | None = None, language: str | None = None, dialect: str | None = None, scenario: str | None = None, voice_id: str | None = None, preset_voice: dict | None = None, style: str | None = None, style_intensity: str | None = None):
        engine = self._ensure_engine()
        local_chunks = []
        effective_mode = mode
        control_instruction = self._build_control_instruction(language=language, dialect=dialect, scenario=scenario, instruction=instruction, speed=speed)
        if effective_mode == "zero_shot" and self._target_speech_language(language, dialect) == "yue":
            # A native Cantonese reference already carries pronunciation and cadence.
            # Do not wrap its transcript in a generic dialect instruction.
            control_instruction = None
        if self.engine_backend == "official":
            iterator = self._official_iterator(
                text=text,
                mode=effective_mode,
                prompt_text=prompt_text,
                prompt_wav_path=prompt_wav_path,
                control_instruction=control_instruction,
                speed=speed,
            )
            for item in iterator:
                local_chunks.append(item["tts_speech"].cpu())
            if not local_chunks:
                raise RuntimeError("No audio returned from official CosyVoice engine")
            return self._concat_tensors(local_chunks)
        instruct_text_frontend = text_frontend
        if effective_mode == "instruct" and (language or "zh") == "zh" and (dialect or "mandarin") != "mandarin":
            # Dialect prompting sounds less "one character at a time" when we reduce
            # extra frontend normalization and let the model handle the sentence more directly.
            instruct_text_frontend = False
        if preset_voice is not None:
            embedding = self._load_preset_embedding(preset_voice["name"])
            if control_instruction:
                iterator = engine.inference_instruct(
                    tts_text=text,
                    embedding=embedding,
                    instruct_text=control_instruction,
                    stream=False,
                    speed=speed,
                    text_frontend=instruct_text_frontend,
                )
            else:
                iterator = engine.inference_sft(
                    tts_text=text,
                    embedding=embedding,
                    stream=False,
                    speed=speed,
                    text_frontend=text_frontend,
                )
        else:
            if effective_mode == "instruct":
                embedding = self._extract_prompt_embedding(
                    prompt_wav_path=prompt_wav_path,
                    voice_id=voice_id,
                )
                iterator = engine.inference_instruct(
                    tts_text=text,
                    embedding=embedding,
                    instruct_text=control_instruction or "",
                    stream=False,
                    speed=speed,
                    text_frontend=instruct_text_frontend,
                )
            elif effective_mode == "instruct2":
                # Keep instruct2 as a last-resort compatibility path only.
                iterator = engine.inference_instruct2(
                    tts_text=text,
                    instruct_text=control_instruction or "",
                    prompt_wav=str(prompt_wav_path),
                    zero_shot_spk_id="",
                    stream=False,
                    speed=speed,
                    text_frontend=text_frontend,
                )
            elif effective_mode == "cross_lingual":
                if prompt_wav_path is None:
                    raise ValueError("cross_lingual mode requires a prompt audio file")
                normalized_target = self._official_prompt_text(text, control_instruction)
                cache_spk_id = self._ensure_cached_prompt_speaker(
                    mode="cross_lingual",
                    cache_text="",
                    prompt_wav_path=prompt_wav_path,
                    voice_id=voice_id,
                )
                iterator = engine.inference_cross_lingual(tts_text=normalized_target, prompt_wav=str(prompt_wav_path), zero_shot_spk_id=cache_spk_id, stream=False, speed=speed, text_frontend=text_frontend)
            elif effective_mode == "zero_shot":
                if prompt_wav_path is None or not prompt_text:
                    raise ValueError("zero_shot mode requires prompt text and prompt audio")
                normalized_prompt = self._official_prompt_text(prompt_text, control_instruction)
                cache_spk_id = self._ensure_cached_prompt_speaker(
                    mode="zero_shot",
                    cache_text=normalized_prompt,
                    prompt_wav_path=prompt_wav_path,
                    voice_id=voice_id,
                )
                iterator = engine.inference_zero_shot(tts_text=text, prompt_text=normalized_prompt, prompt_wav=str(prompt_wav_path), zero_shot_spk_id=cache_spk_id, stream=False, speed=speed, text_frontend=text_frontend)
            else:
                raise ValueError(f"Unsupported mode: {effective_mode}")
        for item in iterator:
            local_chunks.append(item["tts_speech"].cpu())
        if not local_chunks:
            raise RuntimeError("No audio returned from CosyVoice engine")
        return self._concat_tensors(local_chunks)

    def _load_audio_tensor(self, path: Path):
        speech, sample_rate = self._torchaudio.load(str(path))
        if sample_rate != self._engine.sample_rate:
            speech = self._torchaudio.functional.resample(speech, sample_rate, self._engine.sample_rate)
        return speech

    def rebuild_outputs_from_segments(self, segments: list[dict], build_zip: bool = True, pause_seconds: float = 0.12, output_name: str | None = None) -> dict:
        if not segments:
            raise ValueError("没有可重建的分段数据。")
        self._ensure_engine()
        normalized = []
        for raw in segments:
            if not isinstance(raw, dict):
                continue
            index = int(raw.get("index") or (len(normalized) + 1))
            text = (raw.get("text") or "").strip() or f"第{index}段"
            file_path_value = (raw.get("file_path") or "").strip()
            file_path = Path(file_path_value) if file_path_value else config.output_dir / Path((raw.get("audio_url") or "").strip()).name
            if not file_path.exists():
                raise ValueError(f"第 {index} 段音频文件不存在：{file_path.name}")
            normalized.append({"index": index, "text": text, "file_path": file_path})
        normalized.sort(key=lambda item: item["index"])
        tensors = [self._load_audio_tensor(item["file_path"]) for item in normalized]
        merged = self._concat_tensors(tensors, add_pause=True, pause_seconds=pause_seconds)
        normalized_output_name = self._normalize_output_name(output_name)
        merged_name = self._build_named_output_filename(normalized_output_name, "phoenix_merged_rebuilt")
        merged_path = config.output_dir / merged_name
        self._write_pcm_wav(merged_path, merged)
        zip_url = None
        zip_name = None
        if build_zip and len(normalized) > 1:
            zip_name = self._build_named_output_filename(normalized_output_name, "phoenix_segments_rebuilt", suffix="segments", ext=".zip")
            zip_path = config.output_dir / zip_name
            self._build_segments_zip([{"index": item["index"], "text": item["text"], "file_path": item["file_path"]} for item in normalized], zip_path)
            zip_url = f"/api/outputs/{zip_name}"
        return {"audio_url": f"/api/outputs/{merged_name}", "filename": merged_name, "zip_url": zip_url, "zip_filename": zip_name, "segments_count": len(normalized), "output_name_base": normalized_output_name}

    def _build_segments_zip(self, segments: list[dict], zip_output_path: Path) -> None:
        manifest_lines = []
        with zipfile.ZipFile(str(zip_output_path), "w", zipfile.ZIP_DEFLATED) as zf:
            for seg in segments:
                fragment = re.sub(r'[\\/:*?"<>|\r\n]+', "", seg["text"]).strip()[:18] or "segment"
                arcname = f"{seg['index']:02d}_{fragment}.wav"
                zf.write(str(seg["file_path"]), arcname)
                manifest_lines.append(f"第 {seg['index']} 段\n文件名: {arcname}\n文本: {seg['text']}\n")
            zf.writestr("segments_manifest.txt", "\n".join(manifest_lines))

    def _resolve_generation_mode_and_warning(
        self,
        *,
        mode: str,
        prompt_text: str | None,
        prompt_language: str | None,
        prompt_wav_path: Path | None,
        preset_voice: dict | None,
        language: str | None,
        dialect: str | None,
        scenario: str | None,
        instruction: str | None,
        speed: float,
    ) -> tuple[str, str | None, str | None]:
        warning = None
        control_instruction = self._build_control_instruction(
            language=language,
            dialect=dialect,
            scenario=scenario,
            instruction=instruction,
            speed=speed,
        )
        effective_mode = mode
        source_language = self._detect_reference_language(prompt_language, prompt_text)
        target_language = self._target_speech_language(language, dialect)
        if target_language == "yue" and prompt_wav_path is not None and preset_voice is None:
            if not (prompt_text or "").strip():
                effective_mode = "cross_lingual"
                warning = "粤语参考音频识别文字为空，已切换跨语种兼容模式；补充准确粤语文字可提高稳定性。"
            elif source_language and source_language != target_language:
                effective_mode = "cross_lingual"
                warning = f"参考音频语言为 {source_language}，目标语言为 {target_language}，已自动切换跨语种音色克隆。"
            else:
                effective_mode = "zero_shot"
                warning = None
                control_instruction = None
        elif prompt_wav_path is not None and preset_voice is None and source_language and target_language and source_language != target_language:
            effective_mode = "cross_lingual"
            warning = f"参考音频语言为 {source_language}，目标语言为 {target_language}，已自动切换跨语种音色克隆。"
        elif control_instruction and (preset_voice is not None or prompt_wav_path is not None):
            effective_mode = "instruct"
            warning = "当前正在走 embedding + instruct 的实验方言链路。系统预置音色通常更稳；已保存音色/参考音频也会尝试执行，但效果可能波动。"
        elif self.engine_backend == "official" and prompt_wav_path is not None and not (prompt_text or "").strip():
            effective_mode = "zero_shot"
            warning = "参考音频识别文字为空，官方云端模式已使用默认提示文本继续生成；建议补充参考音频对应文字以提升音色稳定性。"
        elif effective_mode == "zero_shot" and prompt_wav_path is not None and not (prompt_text or "").strip():
            effective_mode = "cross_lingual"
            warning = "未填写提示文本，系统已自动切换为“跨语种 / 多方言”兼容模式生成。若需更稳定的参考音色播报，请补充参考音频对应的提示文本。"
        if language == "zh" and (dialect or "mandarin") in EXPERIMENTAL_DIALECTS:
            extra = "当前方言建议先用一两句短文本试听。"
            if (dialect or "mandarin") in HIGH_RISK_DIALECTS:
                extra = "当前方言建议先试听，公开模型可能更接近带口音普通话，建议先用一两句短文本确认效果。"
            warning = f"{warning} {extra}".strip() if warning else extra
        return effective_mode, warning, control_instruction

    def _detect_reference_language(self, prompt_language: str | None, prompt_text: str | None) -> str:
        text = (prompt_text or "").strip()
        cantonese_markers = ("收睇", "我系", "喺", "嘅", "咗", "唔", "冇", "佢", "哋", "嗰", "而家")
        if any(marker in text for marker in cantonese_markers):
            return "yue"
        normalized = (prompt_language or "").strip().lower()
        aliases = {"jp": "ja", "kr": "ko", "cantonese": "yue", "mandarin": "zh", "chinese": "zh"}
        if normalized and normalized not in {"auto", "nospeech"}:
            return aliases.get(normalized, normalized)
        if re.search(r"[\u3040-\u30ff]", text):
            return "ja"
        if re.search(r"[\uac00-\ud7af]", text):
            return "ko"
        if re.search(r"[\u4e00-\u9fff]", text):
            return "zh"
        return ""

    def _target_speech_language(self, language: str | None, dialect: str | None) -> str:
        language_value = (language or "zh").strip().lower() or "zh"
        if language_value == "zh" and (dialect or "mandarin") == "cantonese":
            return "yue"
        return {"jp": "ja", "kr": "ko"}.get(language_value, language_value)

    def generate(self, *, text: str, mode: str, prompt_text: str | None, prompt_wav_path: Path | None, speed: float, text_frontend: bool, language: str | None = None, dialect: str | None = None, scenario: str | None = None, auto_segment: bool = True, segment_mode: str = "natural", voice_id: str | None = None, instruction: str | None = None, style: str | None = None, style_intensity: str | None = None, output_name: str | None = None, prompt_language: str | None = None) -> dict:
        preset_voice = self.get_preset_voice(voice_id)
        prompt_text, prompt_wav_path, selected_voice = self.resolve_voice_prompt(
            voice_id=voice_id,
            prompt_text=prompt_text,
            prompt_wav_path=prompt_wav_path,
        )
        if selected_voice and not prompt_language:
            prompt_language = selected_voice.get("prompt_language") or None
        if preset_voice is None and prompt_wav_path is None:
            raise ValueError("请先从音色库选择一个音色，或上传参考音频后再生成。")
        self._ensure_engine()
        requested_mode = mode
        mode, warning, control_instruction = self._resolve_generation_mode_and_warning(
            mode=mode,
            prompt_text=prompt_text,
            prompt_language=prompt_language,
            prompt_wav_path=prompt_wav_path,
            preset_voice=preset_voice,
            language=language,
            dialect=dialect,
            scenario=scenario,
            instruction=instruction,
            speed=speed,
        )
        user_segments = self.build_user_segments(text, auto_segment, segment_mode)
        if not user_segments:
            raise ValueError("text cannot be empty")
        segment_results = []
        for user_seg in user_segments:
            subsegment_tensors = [self._synthesize_text(text=sub_text, mode=mode, prompt_text=prompt_text, prompt_wav_path=prompt_wav_path, speed=speed, text_frontend=text_frontend, instruction=instruction, language=language, dialect=dialect, scenario=scenario, voice_id=voice_id, preset_voice=preset_voice, style=style, style_intensity=style_intensity) for sub_text in user_seg["subsegments"]]
            segment_tensor = self._concat_spoken_subsegments(subsegment_tensors, user_seg["subsegments"])
            file_name, file_path = self._save_tensor_to_output(segment_tensor, f"phoenix_segment_{user_seg['index']:02d}")
            segment_results.append({"index": user_seg["index"], "text": user_seg["text"], "audio_url": f"/api/outputs/{file_name}", "file_name": file_name, "file_path": str(file_path), "subsegments_count": len(user_seg["subsegments"]), "used_fallback": bool(warning)})
        rebuild = self.rebuild_outputs_from_segments(segment_results, build_zip=len(segment_results) > 1, output_name=output_name)
        return {
            "file_name": rebuild["filename"],
            "file_path": str(config.output_dir / rebuild["filename"]),
            "audio_url": rebuild["audio_url"],
            "zip_url": rebuild["zip_url"],
            "zip_filename": rebuild["zip_filename"],
            "sample_rate": self._engine.sample_rate,
            "mode": mode,
            "requested_mode": requested_mode,
            "language": language or "",
            "dialect": dialect or "",
            "prompt_language": self._detect_reference_language(prompt_language, prompt_text),
            "scenario": scenario or "",
            "rainfall_output_dir": str(config.rainfall_output_dir),
            "chunk_count": sum(item["subsegments_count"] for item in segment_results),
            "warning": warning,
            "segments_count": len(segment_results),
            "segments": segment_results,
            "auto_segment_used": auto_segment,
            "segment_mode": segment_mode,
            "voice_id": (selected_voice or preset_voice or {}).get("id"),
            "voice_name": (selected_voice or preset_voice or {}).get("name"),
            "voice_kind": (selected_voice or preset_voice or {}).get("kind", "saved" if selected_voice else ""),
            "control_instruction": control_instruction or "",
            "style": style or "natural",
            "style_intensity": style_intensity or "medium",
            "output_name_base": rebuild.get("output_name_base") or self._normalize_output_name(output_name),
        }

    def regenerate_segment(self, *, text: str, index: int, mode: str, prompt_text: str | None, prompt_wav_path: Path | None, speed: float, text_frontend: bool, voice_id: str | None = None, instruction: str | None = None, language: str | None = None, dialect: str | None = None, scenario: str | None = None, style: str | None = None, style_intensity: str | None = None, output_name: str | None = None, prompt_language: str | None = None) -> dict:
        preset_voice = self.get_preset_voice(voice_id)
        prompt_text, prompt_wav_path, selected_voice = self.resolve_voice_prompt(
            voice_id=voice_id,
            prompt_text=prompt_text,
            prompt_wav_path=prompt_wav_path,
        )
        if selected_voice and not prompt_language:
            prompt_language = selected_voice.get("prompt_language") or None
        if preset_voice is None and prompt_wav_path is None:
            raise ValueError("请先选择音色或参考音频后，再重生成本段。")
        self._ensure_engine()
        mode, _, _ = self._resolve_generation_mode_and_warning(
            mode=mode,
            prompt_text=prompt_text,
            prompt_language=prompt_language,
            prompt_wav_path=prompt_wav_path,
            preset_voice=preset_voice,
            language=language,
            dialect=dialect,
            scenario=scenario,
            instruction=instruction,
            speed=speed,
        )
        segment_tensor = self._synthesize_text(text=(text or "").strip(), mode=mode, prompt_text=prompt_text, prompt_wav_path=prompt_wav_path, speed=speed, text_frontend=text_frontend, instruction=instruction, language=language, dialect=dialect, scenario=scenario, voice_id=voice_id, preset_voice=preset_voice, style=style, style_intensity=style_intensity)
        file_name, file_path = self._save_tensor_to_output(segment_tensor, f"phoenix_segment_{int(index):02d}_regen")
        return {"index": int(index), "text": (text or "").strip(), "audio_url": f"/api/outputs/{file_name}", "file_name": file_name, "file_path": str(file_path), "subsegments_count": 1, "used_fallback": False, "voice_id": (selected_voice or preset_voice or {}).get("id"), "voice_name": (selected_voice or preset_voice or {}).get("name"), "voice_kind": (selected_voice or preset_voice or {}).get("kind", "saved" if selected_voice else ""), "style": style or "natural", "style_intensity": style_intensity or "medium", "output_name_base": self._normalize_output_name(output_name)}

    def persist_upload(self, file_bytes: bytes, suffix: str, prefix: str = "prompt") -> Path:
        out_path = config.temp_dir / f"{prefix}_{uuid.uuid4().hex}{suffix}"
        out_path.write_bytes(file_bytes)
        return out_path

    def persist_history_reference(self, file_bytes: bytes, suffix: str, prefix: str = "history_ref") -> tuple[str, Path]:
        out_name = f"{prefix}_{uuid.uuid4().hex}{suffix}"
        out_path = config.history_audio_dir / out_name
        out_path.write_bytes(file_bytes)
        return out_name, out_path


service = RainfallCosyVoiceService()
