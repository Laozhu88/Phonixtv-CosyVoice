from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from typing import Optional
from urllib import error, parse, request

from .config import config


ALIYUN_LANGUAGE_CODE_MAP = {
    "zh": "zh",
    "yue": "yue",
    "en": "en",
    "jp": "ja",
    "kr": "ko",
    "de": "de",
    "es": "es",
    "fr": "fr",
    "it": "it",
    "ru": "ru",
}

BAIDU_LANGUAGE_CODE_MAP = {
    "zh": "zh",
    "yue": "yue",
    "en": "en",
    "jp": "jp",
    "kr": "kor",
    "de": "de",
    "es": "spa",
    "fr": "fra",
    "it": "it",
    "ru": "ru",
}

LANGUAGE_LABEL_MAP = {
    "zh": "中文",
    "yue": "粤语播报稿",
    "en": "英文",
    "jp": "日语",
    "kr": "韩语",
    "de": "德语",
    "es": "西班牙语",
    "fr": "法语",
    "it": "意大利语",
    "ru": "俄语",
}

QWEN_LANGUAGE_NAME_MAP = {
    "zh": "Chinese",
    "yue": "Cantonese",
    "en": "English",
    "jp": "Japanese",
    "kr": "Korean",
    "de": "German",
    "es": "Spanish",
    "fr": "French",
    "it": "Italian",
    "ru": "Russian",
}

PROVIDER_LABELS = {
    "aliyun": "阿里云机器翻译",
    "qwen_mt": "千问翻译（Qwen-MT）",
    "baidu": "百度翻译",
    "baidu_qianfan": "百度千帆大模型翻译",
}


@dataclass
class TranslatorStatus:
    provider: str
    configured: bool
    message: str
    supported_languages: list[str]
    provider_label: str


class TranslationService:
    def __init__(self) -> None:
        self._load_from_config()

    def _load_from_config(self) -> None:
        self.provider = (config.translation_provider or "aliyun").strip().lower()
        self.aliyun_access_key_id = (config.aliyun_access_key_id or "").strip()
        self.aliyun_access_key_secret = (config.aliyun_access_key_secret or "").strip()
        self.aliyun_region = (config.aliyun_translate_region or "cn-hangzhou").strip()
        self.aliyun_endpoint = (config.aliyun_translate_endpoint or "mt.cn-hangzhou.aliyuncs.com").strip()
        self.baidu_app_id = (config.baidu_translate_app_id or "").strip()
        self.baidu_secret = (config.baidu_translate_secret or "").strip()
        self.baidu_endpoint = (config.baidu_translate_endpoint or "").strip()
        self.qwen_api_key = (config.qwen_api_key or "").strip()
        self.qwen_mt_model = (config.qwen_mt_model or "qwen-mt-plus").strip()
        self.qwen_mt_endpoint = (config.qwen_mt_endpoint or "").strip()
        self.baidu_qianfan_api_key = (config.baidu_qianfan_api_key or "").strip()
        self.baidu_qianfan_model = (config.baidu_qianfan_model or "ernie-4.5-turbo-20260402").strip()
        self.baidu_qianfan_endpoint = (config.baidu_qianfan_endpoint or "").strip()

    def status(self) -> TranslatorStatus:
        provider = self.provider
        configured = self._is_provider_configured(provider)
        label = PROVIDER_LABELS.get(provider, provider or "未选择")
        if configured:
            message = f"{label}已配置，可用于外语翻译和粤语播报稿转换。"
        else:
            message = f"未配置{label}所需凭据，暂时不能自动翻译或转换粤语播报稿。"
        return TranslatorStatus(
            provider=provider,
            configured=configured,
            message=message,
            supported_languages=[code for code in LANGUAGE_LABEL_MAP if code != "zh"],
            provider_label=label,
        )

    def settings(self) -> dict:
        return {
            "provider": self.provider,
            "providers": [
                {"value": "aliyun", "label": PROVIDER_LABELS["aliyun"], "configured": self._is_provider_configured("aliyun")},
                {"value": "qwen_mt", "label": PROVIDER_LABELS["qwen_mt"], "configured": self._is_provider_configured("qwen_mt")},
                {"value": "baidu", "label": PROVIDER_LABELS["baidu"], "configured": self._is_provider_configured("baidu")},
                {"value": "baidu_qianfan", "label": PROVIDER_LABELS["baidu_qianfan"], "configured": self._is_provider_configured("baidu_qianfan")},
            ],
            "aliyun_region": self.aliyun_region,
            "aliyun_endpoint": self.aliyun_endpoint,
            "qwen_mt_model": self.qwen_mt_model,
            "qwen_mt_endpoint": self.qwen_mt_endpoint,
            "baidu_endpoint": self.baidu_endpoint,
            "baidu_qianfan_model": self.baidu_qianfan_model,
            "baidu_qianfan_endpoint": self.baidu_qianfan_endpoint,
            "credential_status": {
                "aliyun_access_key_id": bool(self.aliyun_access_key_id),
                "aliyun_access_key_secret": bool(self.aliyun_access_key_secret),
                "qwen_api_key": bool(self.qwen_api_key),
                "baidu_translate_app_id": bool(self.baidu_app_id),
                "baidu_translate_secret": bool(self.baidu_secret),
                "baidu_qianfan_api_key": bool(self.baidu_qianfan_api_key),
            },
        }

    def update_settings(self, values: dict) -> dict:
        provider = str(values.get("translation_provider") or values.get("provider") or self.provider).strip().lower()
        if provider not in PROVIDER_LABELS:
            raise ValueError("请选择有效的翻译引擎。")
        normalized = {key: value for key, value in values.items() if isinstance(value, str)}
        normalized["translation_provider"] = provider
        config.update_translation_settings(normalized)
        self._load_from_config()
        return self.settings()

    def clear_credentials(self, provider: str) -> dict:
        provider = (provider or self.provider).strip().lower()
        if provider not in PROVIDER_LABELS:
            raise ValueError("请选择有效的翻译引擎。")
        config.clear_translation_credentials(provider)
        self._load_from_config()
        return self.settings()

    def test_connection(self) -> dict:
        result = self.translate(text="凤凰卫视中文台。", target_language="en", source_language="zh")
        return {"provider": self.provider, "provider_label": PROVIDER_LABELS[self.provider], "translated_text": result["translated_text"]}

    def translate(self, *, text: str, target_language: str, source_language: Optional[str] = "auto") -> dict:
        clean_text = (text or "").strip()
        if not clean_text:
            raise ValueError("待翻译文稿不能为空。")
        if target_language == "zh":
            return {
                "provider": self.provider,
                "source_language": source_language or "auto",
                "target_language": "zh",
                "translated_text": clean_text,
                "target_language_label": LANGUAGE_LABEL_MAP["zh"],
            }
        provider = self.provider
        if provider == "aliyun":
            return self._translate_aliyun(clean_text, source_language or "auto", target_language)
        if provider == "qwen_mt":
            return self._translate_qwen_mt(clean_text, source_language or "auto", target_language)
        if provider == "baidu":
            return self._translate_baidu(clean_text, source_language or "auto", target_language)
        if provider == "baidu_qianfan":
            return self._translate_baidu_qianfan(clean_text, source_language or "auto", target_language)
        raise ValueError("当前翻译服务尚未配置。")

    def _is_provider_configured(self, provider: str) -> bool:
        if provider == "aliyun":
            return bool(self.aliyun_access_key_id and self.aliyun_access_key_secret)
        if provider == "qwen_mt":
            return bool(self.qwen_api_key)
        if provider == "baidu":
            return bool(self.baidu_app_id and self.baidu_secret)
        if provider == "baidu_qianfan":
            return bool(self.baidu_qianfan_api_key)
        return False

    def _translate_aliyun(self, text: str, source_language: str, target_language: str) -> dict:
        if not self._is_provider_configured("aliyun"):
            raise ValueError("请先在翻译设置中填写阿里云 AccessKey。")
        target_code = ALIYUN_LANGUAGE_CODE_MAP.get(target_language)
        if not target_code:
            raise ValueError("当前目标语种暂不支持自动翻译。")
        source_code = ALIYUN_LANGUAGE_CODE_MAP.get(source_language, source_language or "auto")
        try:
            from aliyunsdkcore.client import AcsClient
            from aliyunsdkcore.request import CommonRequest
        except Exception as exc:
            raise ValueError("当前运行环境缺少阿里云翻译依赖。") from exc

        client = AcsClient(self.aliyun_access_key_id, self.aliyun_access_key_secret, self.aliyun_region)
        req = CommonRequest()
        req.set_accept_format("json")
        req.set_method("POST")
        req.set_domain(self.aliyun_endpoint)
        req.set_version("2018-10-12")
        req.set_action_name("TranslateGeneral")
        req.add_body_params("FormatType", "text")
        req.add_body_params("SourceLanguage", source_code or "auto")
        req.add_body_params("TargetLanguage", target_code)
        req.add_body_params("SourceText", text)
        req.add_body_params("Scene", "general")
        try:
            raw = client.do_action_with_exception(req)
        except Exception as exc:
            message = str(exc)
            if "NoPermission" in message:
                raise ValueError("阿里云密钥已识别，但当前账号没有机器翻译调用权限。") from exc
            raise ValueError(f"阿里云翻译请求失败：{message}") from exc
        payload = self._decode_json(raw, "阿里云翻译")
        data = payload.get("Data") or {}
        translated = (data.get("Translated") or "").strip()
        if not translated:
            raise ValueError(f"阿里云翻译失败：{payload.get('Message') or payload.get('Code') or '未返回可用译文'}")
        return self._result("aliyun", translated, data.get("DetectedLanguage") or source_code or "auto", target_code, target_language)

    def _translate_qwen_mt(self, text: str, source_language: str, target_language: str) -> dict:
        if not self._is_provider_configured("qwen_mt"):
            raise ValueError("请先在翻译设置中填写千问 API Key。")
        target_name = QWEN_LANGUAGE_NAME_MAP.get(target_language)
        if not target_name:
            raise ValueError("当前目标语种暂不支持自动翻译。")
        payload = {
            "model": self.qwen_mt_model,
            "messages": [{"role": "user", "content": text}],
            "translation_options": {
                "source_lang": QWEN_LANGUAGE_NAME_MAP.get(source_language, "auto"),
                "target_lang": target_name,
            },
        }
        data = self._post_json(
            self.qwen_mt_endpoint,
            payload,
            {"Authorization": f"Bearer {self.qwen_api_key}"},
            "千问翻译",
        )
        translated = self._extract_chat_content(data)
        return self._result("qwen_mt", translated, source_language, target_language, target_language)

    def _translate_baidu(self, text: str, source_language: str, target_language: str) -> dict:
        if not self._is_provider_configured("baidu"):
            raise ValueError("请先在翻译设置中填写百度翻译 APP ID 和密钥。")
        target_code = BAIDU_LANGUAGE_CODE_MAP.get(target_language)
        if not target_code:
            raise ValueError("当前目标语种暂不支持自动翻译。")
        source_code = BAIDU_LANGUAGE_CODE_MAP.get(source_language, source_language or "auto")
        salt = hashlib.md5(os.urandom(16)).hexdigest()[:12]
        sign = hashlib.md5(f"{self.baidu_app_id}{text}{salt}{self.baidu_secret}".encode("utf-8")).hexdigest()
        payload = parse.urlencode({"q": text, "from": source_code or "auto", "to": target_code, "appid": self.baidu_app_id, "salt": salt, "sign": sign}).encode("utf-8")
        req = request.Request(self.baidu_endpoint, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        try:
            with request.urlopen(req, timeout=30) as response:
                data = self._decode_json(response.read(), "百度翻译")
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"百度翻译请求失败：{exc}") from exc
        if data.get("error_code"):
            raise ValueError(f"百度翻译失败：{data.get('error_msg') or data.get('error_code')}")
        translated = "\n".join(item.get("dst", "") for item in data.get("trans_result") or []).strip()
        if not translated:
            raise ValueError("百度翻译未返回可用译文。")
        return self._result("baidu", translated, data.get("from") or source_code or "auto", data.get("to") or target_code, target_language)

    def _translate_baidu_qianfan(self, text: str, source_language: str, target_language: str) -> dict:
        if not self._is_provider_configured("baidu_qianfan"):
            raise ValueError("请先在翻译设置中填写百度千帆 API Key。")
        target_label = LANGUAGE_LABEL_MAP.get(target_language)
        if not target_label:
            raise ValueError("当前目标语种暂不支持自动翻译。")
        source_label = LANGUAGE_LABEL_MAP.get(source_language, "自动识别")
        prompt = (
            "你是新闻配音稿翻译引擎。将用户文本从"
            f"{source_label}翻译为{target_label}。只输出译文，不解释、不加标题，"
            "保留段落、人名、节目名、数字和标点。"
        )
        data = self._post_json(
            self.baidu_qianfan_endpoint,
            {
                "model": self.baidu_qianfan_model,
                "temperature": 0.1,
                "enable_thinking": False,
                "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": text}],
            },
            {"Authorization": f"Bearer {self.baidu_qianfan_api_key}"},
            "百度千帆翻译",
        )
        translated = self._extract_chat_content(data)
        return self._result("baidu_qianfan", translated, source_language, target_language, target_language)

    @staticmethod
    def _decode_json(raw: bytes | str, service_name: str) -> dict:
        try:
            return json.loads(raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw))
        except Exception as exc:
            raise ValueError(f"{service_name}返回了无法解析的响应。") from exc

    def _post_json(self, endpoint: str, payload: dict, extra_headers: dict[str, str], service_name: str) -> dict:
        req = request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", **extra_headers},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=45) as response:
                data = self._decode_json(response.read(), service_name)
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise ValueError(f"{service_name}请求失败：HTTP {exc.code} {detail}") from exc
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"{service_name}请求失败：{exc}") from exc
        if data.get("error"):
            detail = data["error"]
            raise ValueError(f"{service_name}失败：{detail.get('message') if isinstance(detail, dict) else detail}")
        if data.get("code") and data.get("message"):
            raise ValueError(f"{service_name}失败：{data.get('message')}")
        return data

    @staticmethod
    def _extract_chat_content(data: dict) -> str:
        choices = data.get("choices") or []
        message = choices[0].get("message") if choices and isinstance(choices[0], dict) else {}
        content = message.get("content") if isinstance(message, dict) else ""
        if isinstance(content, list):
            content = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
        translated = str(content or "").strip()
        if not translated:
            raise ValueError("翻译服务未返回可用译文。")
        return translated

    @staticmethod
    def _result(provider: str, translated: str, source_language: str, target_code: str, target_language: str) -> dict:
        return {
            "provider": provider,
            "source_language": source_language,
            "target_language": target_code,
            "translated_text": translated,
            "target_language_label": LANGUAGE_LABEL_MAP.get(target_language, target_language),
        }


translator = TranslationService()
