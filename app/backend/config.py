from __future__ import annotations

import json
import os
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
LOCAL_CONFIG_PATH = WORKSPACE_ROOT / "config" / "app.local.json"
LOCAL_RAINFALL_HOME = WORKSPACE_ROOT / "runtime" / "rainfall"
LOCAL_RAINFALL_PYTHON = LOCAL_RAINFALL_HOME / "python" / "python.exe"
LOCAL_ASR_PYTHON = WORKSPACE_ROOT / "runtime" / "asr" / "Scripts" / "python.exe"


def _load_local_settings() -> dict:
    if not LOCAL_CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(LOCAL_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


LOCAL_SETTINGS = _load_local_settings()


def _save_local_settings() -> None:
    """Persist local workstation settings without exposing them through the API."""
    LOCAL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = LOCAL_CONFIG_PATH.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(LOCAL_SETTINGS, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(LOCAL_CONFIG_PATH)


def _setting(env_name: str, default="", local_key: str | None = None):
    key = local_key or env_name.lower()
    return os.environ.get(env_name, LOCAL_SETTINGS.get(key, default))


def _resolve_default_rainfall_home() -> Path:
    env_or_local = (_setting("PHOENIX_RAINFALL_HOME", "") or "").strip()
    if env_or_local:
        return Path(env_or_local)
    if LOCAL_RAINFALL_HOME.exists():
        return LOCAL_RAINFALL_HOME
    return Path(r"F:\cosyvoice-rainfall-v2\cosyvoice-rainfall")


def _resolve_default_asr_python() -> Path:
    env_or_local = (_setting("PHOENIX_ASR_PYTHON", "") or "").strip()
    if env_or_local:
        return Path(env_or_local)
    if LOCAL_ASR_PYTHON.exists():
        return LOCAL_ASR_PYTHON
    if LOCAL_RAINFALL_PYTHON.exists():
        return LOCAL_RAINFALL_PYTHON
    return Path(r"F:\AI-Pr\phoenix_v1_windows_release\runtime\Scripts\python.exe")


DEFAULT_RAINFALL_HOME = Path(
    _resolve_default_rainfall_home()
)
DEFAULT_ASR_PYTHON = Path(
    _resolve_default_asr_python()
)


class AppConfig:
    def __init__(self) -> None:
        self.workspace_root = WORKSPACE_ROOT
        self.frontend_dir = WORKSPACE_ROOT / "app" / "frontend" / "static"
        self.project_dir = WORKSPACE_ROOT / "projects"
        self.log_dir = WORKSPACE_ROOT / "logs"
        self.output_dir = self.project_dir / "outputs"
        self.temp_dir = self.project_dir / "temp"
        self.history_dir = self.project_dir / "history"
        self.history_path = self.history_dir / "task_history.json"
        self.history_audio_dir = self.history_dir / "reference_audio"
        self.voice_library_dir = self.project_dir / "voice_library"
        self.voice_audio_dir = self.voice_library_dir / "audio"
        self.voice_meta_path = self.voice_library_dir / "metadata.json"
        self.template_meta_path = self.project_dir / "channel_templates.json"
        self.rainfall_home = DEFAULT_RAINFALL_HOME
        self.rainfall_model_dir = self.rainfall_home / "models" / "CosyVoice3-0.5B"
        self.rainfall_output_dir = self.rainfall_home / "outputs"
        self.engine_backend = _setting("PHOENIX_ENGINE_BACKEND", "rainfall", "engine_backend")
        self.llm_variant = str(_setting("PHOENIX_LLM_VARIANT", "rl", "llm_variant")).strip().lower()
        if self.llm_variant not in {"base", "rl"}:
            self.llm_variant = "rl"
        self.official_cosyvoice_root = Path(_setting("PHOENIX_OFFICIAL_COSYVOICE_ROOT", str(self.rainfall_home), "official_cosyvoice_root"))
        self.official_model_dir = Path(_setting("PHOENIX_OFFICIAL_MODEL_DIR", str(self.official_cosyvoice_root / "pretrained_models" / "Fun-CosyVoice3-0.5B"), "official_model_dir"))
        self.asr_python = DEFAULT_ASR_PYTHON
        self.asr_model = _setting("PHOENIX_ASR_MODEL", "small", "asr_model")
        self.translation_provider = _setting("PHOENIX_TRANSLATION_PROVIDER", "aliyun", "translation_provider")
        self.aliyun_access_key_id = os.environ.get("PHOENIX_ALIYUN_ACCESS_KEY_ID") or os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID") or LOCAL_SETTINGS.get("aliyun_access_key_id", "")
        self.aliyun_access_key_secret = os.environ.get("PHOENIX_ALIYUN_ACCESS_KEY_SECRET") or os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET") or LOCAL_SETTINGS.get("aliyun_access_key_secret", "")
        self.aliyun_translate_region = _setting("PHOENIX_ALIYUN_TRANSLATE_REGION", "cn-hangzhou", "aliyun_translate_region")
        self.aliyun_translate_endpoint = _setting("PHOENIX_ALIYUN_TRANSLATE_ENDPOINT", "mt.cn-hangzhou.aliyuncs.com", "aliyun_translate_endpoint")
        self.baidu_translate_app_id = _setting("PHOENIX_BAIDU_TRANSLATE_APP_ID", "", "baidu_translate_app_id")
        self.baidu_translate_secret = _setting("PHOENIX_BAIDU_TRANSLATE_SECRET", "", "baidu_translate_secret")
        self.baidu_translate_endpoint = _setting("PHOENIX_BAIDU_TRANSLATE_ENDPOINT", "https://fanyi-api.baidu.com/api/trans/vip/translate", "baidu_translate_endpoint")
        self.qwen_api_key = _setting("PHOENIX_QWEN_API_KEY", "", "qwen_api_key")
        self.qwen_mt_model = _setting("PHOENIX_QWEN_MT_MODEL", "qwen-mt-plus", "qwen_mt_model")
        self.qwen_mt_endpoint = _setting("PHOENIX_QWEN_MT_ENDPOINT", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "qwen_mt_endpoint")
        self.baidu_qianfan_api_key = _setting("PHOENIX_BAIDU_QIANFAN_API_KEY", "", "baidu_qianfan_api_key")
        self.baidu_qianfan_model = _setting("PHOENIX_BAIDU_QIANFAN_MODEL", "ernie-4.5-turbo-20260402", "baidu_qianfan_model")
        self.baidu_qianfan_endpoint = _setting("PHOENIX_BAIDU_QIANFAN_ENDPOINT", "https://qianfan.baidubce.com/v2/chat/completions", "baidu_qianfan_endpoint")
        self.host = _setting("PHOENIX_HOST", "127.0.0.1", "host")
        try:
            self.port = int(_setting("PHOENIX_PORT", "8090", "port"))
        except (TypeError, ValueError):
            self.port = 8090

        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.history_audio_dir.mkdir(parents=True, exist_ok=True)
        self.voice_library_dir.mkdir(parents=True, exist_ok=True)
        self.voice_audio_dir.mkdir(parents=True, exist_ok=True)

        if not self.history_path.exists():
            self.history_path.write_text("[]", encoding="utf-8")
        if not self.voice_meta_path.exists():
            self.voice_meta_path.write_text("[]", encoding="utf-8")
        if not self.template_meta_path.exists():
            self.template_meta_path.write_text("[]", encoding="utf-8")

    def update_translation_settings(self, values: dict) -> None:
        """Save only approved translation settings and apply them to this process."""
        allowed_keys = {
            "translation_provider",
            "aliyun_access_key_id",
            "aliyun_access_key_secret",
            "aliyun_translate_region",
            "aliyun_translate_endpoint",
            "baidu_translate_app_id",
            "baidu_translate_secret",
            "baidu_translate_endpoint",
            "qwen_api_key",
            "qwen_mt_model",
            "qwen_mt_endpoint",
            "baidu_qianfan_api_key",
            "baidu_qianfan_model",
            "baidu_qianfan_endpoint",
        }
        credential_keys = {
            "aliyun_access_key_id",
            "aliyun_access_key_secret",
            "baidu_translate_app_id",
            "baidu_translate_secret",
            "qwen_api_key",
            "baidu_qianfan_api_key",
        }
        for key, value in values.items():
            if key not in allowed_keys:
                continue
            if not isinstance(value, str):
                raise ValueError(f"翻译设置字段无效：{key}")
            clean_value = value.strip()
            # Leaving a credential blank means "keep the existing value".
            if key in credential_keys and not clean_value:
                continue
            LOCAL_SETTINGS[key] = clean_value

        _save_local_settings()
        for key in allowed_keys:
            if key in LOCAL_SETTINGS:
                setattr(self, key, LOCAL_SETTINGS[key])

    def update_llm_variant(self, variant: str) -> str:
        normalized = (variant or "").strip().lower()
        if normalized not in {"base", "rl"}:
            raise ValueError("模型权重仅支持 base 或 rl。")
        LOCAL_SETTINGS["llm_variant"] = normalized
        _save_local_settings()
        self.llm_variant = normalized
        return normalized

    def clear_translation_credentials(self, provider: str) -> None:
        """Remove saved credentials for one provider without exposing any secret."""
        provider_credentials = {
            "aliyun": ("aliyun_access_key_id", "aliyun_access_key_secret"),
            "qwen_mt": ("qwen_api_key",),
            "baidu": ("baidu_translate_app_id", "baidu_translate_secret"),
            "baidu_qianfan": ("baidu_qianfan_api_key",),
        }
        environment_credentials = {
            "aliyun": ("PHOENIX_ALIYUN_ACCESS_KEY_ID", "ALIBABA_CLOUD_ACCESS_KEY_ID", "PHOENIX_ALIYUN_ACCESS_KEY_SECRET", "ALIBABA_CLOUD_ACCESS_KEY_SECRET"),
            "qwen_mt": ("PHOENIX_QWEN_API_KEY",),
            "baidu": ("PHOENIX_BAIDU_TRANSLATE_APP_ID", "PHOENIX_BAIDU_TRANSLATE_SECRET"),
            "baidu_qianfan": ("PHOENIX_BAIDU_QIANFAN_API_KEY",),
        }
        if provider not in provider_credentials:
            raise ValueError("请选择有效的翻译引擎。")
        if any(os.environ.get(name) for name in environment_credentials[provider]):
            raise ValueError("当前平台凭据由系统环境变量提供，不能通过工作台界面清除。")

        for key in provider_credentials[provider]:
            LOCAL_SETTINGS.pop(key, None)
            setattr(self, key, "")
        _save_local_settings()


config = AppConfig()
