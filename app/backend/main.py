from __future__ import annotations

import io
from pathlib import Path
import re
from typing import Optional
import zipfile
import xml.etree.ElementTree as ET

from fastapi import Body, FastAPI, File, HTTPException, Form, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import config
from .rainfall_adapter import service
from .translator import translator


app = FastAPI(
    title="Phoenix TV Chinese TTS Workstation",
    version="0.5.0",
    summary="Phoenix-branded workstation for CosyVoice multilingual and Chinese dialect dubbing.",
)

app.mount("/static", StaticFiles(directory=str(config.frontend_dir)), name="static")
app.mount("/voice-library/audio", StaticFiles(directory=str(config.voice_audio_dir)), name="voice_library_audio")
app.mount("/history/audio", StaticFiles(directory=str(config.history_audio_dir)), name="history_audio")


def _normalize_imported_text(text: str) -> str:
    clean = (text or "").replace("\r\n", "\n").replace("\r", "\n").replace("\u3000", " ")
    clean = re.sub(r"[ \t]+\n", "\n", clean)
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean.strip()


def _extract_docx_text(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", ns):
        parts: list[str] = []
        for node in paragraph.iter():
            if node.tag == f"{{{ns['w']}}}t":
                parts.append(node.text or "")
            elif node.tag == f"{{{ns['w']}}}tab":
                parts.append("\t")
        line = "".join(parts).strip()
        if line:
            paragraphs.append(line)
    return "\n".join(paragraphs)


def _parse_uploaded_text_file(filename: str, content: bytes) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix == ".txt":
        for encoding in ("utf-8", "utf-8-sig", "gb18030", "gbk"):
            try:
                return _normalize_imported_text(content.decode(encoding))
            except UnicodeDecodeError:
                continue
        raise ValueError("txt 文稿编码无法识别，请保存为 UTF-8 或 GBK 后重试。")
    if suffix == ".docx":
        try:
            return _normalize_imported_text(_extract_docx_text(content))
        except KeyError as exc:
            raise ValueError("docx 文稿内容无法识别，缺少正文结构。") from exc
        except zipfile.BadZipFile as exc:
            raise ValueError("docx 文件结构无效，请确认文件未损坏。") from exc
        except ET.ParseError as exc:
            raise ValueError("docx 文稿解析失败，请确认文件内容正常。") from exc
    raise ValueError("当前仅支持导入 txt 或 docx 文稿。")


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse((config.frontend_dir / "index.html").read_text(encoding="utf-8"))


@app.post("/api/parse-text-file")
async def api_parse_text_file(file: UploadFile = File(...)) -> dict:
    try:
        text = _parse_uploaded_text_file(file.filename or "", await file.read())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "text": text, "filename": file.filename or ""}


@app.get("/api/status")
def api_status() -> dict:
    status = service.bundle_status()
    translation = translator.status()
    return {
        "app": "Phoenix TV Chinese TTS Workstation",
        "brand": "凤凰卫视中文台",
        "bundle": status.__dict__,
        "runtime": service.runtime_status(),
        "translation": translation.__dict__,
        "capabilities": service.capabilities(),
        "speakers": service.available_speakers(),
        "preset_voices": service.list_preset_voices(),
        "history": service.load_history(limit=10),
        "templates": service.list_templates(),
        "voices": service.list_voices(),
    }


@app.post("/api/model-variant")
def api_model_variant(payload: dict = Body(...)) -> dict:
    try:
        variant = service.set_llm_variant(payload.get("variant") or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "variant": variant, "message": "模型权重已切换，将在下次生成时重新加载。"}


@app.post("/api/preview-segments")
async def api_preview_segments(
    text: str = Form(...),
    auto_segment: str = Form(default="true"),
    segment_mode: str = Form(default="natural"),
) -> dict:
    enabled = str(auto_segment).strip().lower() in {"1", "true", "yes", "on"}
    return service.preview_segments(text, enabled, segment_mode)


@app.post("/api/generate")
async def api_generate(
    text: str = Form(...),
    mode: str = Form(...),
    voice_id: Optional[str] = Form(default=None),
    prompt_text: Optional[str] = Form(default=None),
    prompt_language: Optional[str] = Form(default=None),
    instruction: Optional[str] = Form(default=None),
    style: Optional[str] = Form(default="natural"),
    style_intensity: Optional[str] = Form(default="medium"),
    speed: float = Form(default=1.0),
    text_frontend: bool = Form(default=True),
    language: Optional[str] = Form(default="zh"),
    dialect: Optional[str] = Form(default="mandarin"),
    scenario: Optional[str] = Form(default="news"),
    auto_segment: str = Form(default="true"),
    segment_mode: str = Form(default="natural"),
    output_name: Optional[str] = Form(default=None),
    prompt_audio: Optional[UploadFile] = File(default=None),
) -> dict:
    if not (voice_id or "").strip() and not (prompt_audio is not None and prompt_audio.filename):
        raise HTTPException(status_code=400, detail="请先从音色库选择一个音色，或上传参考音频后再生成。")
    prompt_path: Path | None = None
    if prompt_audio is not None and prompt_audio.filename:
        suffix = Path(prompt_audio.filename).suffix or ".wav"
        prompt_path = service.persist_upload(await prompt_audio.read(), suffix)
    try:
        result = service.generate(
            text=text.strip(),
            mode=mode,
            voice_id=(voice_id or "").strip() or None,
            prompt_text=(prompt_text or "").strip() or None,
            prompt_language=(prompt_language or "").strip() or None,
            instruction=(instruction or "").strip() or None,
            style=(style or "").strip() or "natural",
            style_intensity=(style_intensity or "").strip() or "medium",
            prompt_wav_path=prompt_path,
            speed=speed,
            text_frontend=text_frontend,
            language=(language or "").strip() or None,
            dialect=(dialect or "").strip() or None,
            scenario=(scenario or "").strip() or None,
            auto_segment=str(auto_segment).strip().lower() in {"1", "true", "yes", "on"},
            segment_mode=(segment_mode or "natural").strip() or "natural",
            output_name=(output_name or "").strip() or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"生成失败：{exc}") from exc
    return {"ok": True, "message": "凤凰智能配音已生成。", "result": result}


@app.post("/api/regenerate-segment")
async def api_regenerate_segment(
    text: str = Form(...),
    index: int = Form(...),
    mode: str = Form(...),
    voice_id: Optional[str] = Form(default=None),
    prompt_text: Optional[str] = Form(default=None),
    prompt_language: Optional[str] = Form(default=None),
    instruction: Optional[str] = Form(default=None),
    style: Optional[str] = Form(default="natural"),
    style_intensity: Optional[str] = Form(default="medium"),
    speed: float = Form(default=1.0),
    text_frontend: bool = Form(default=True),
    language: Optional[str] = Form(default="zh"),
    dialect: Optional[str] = Form(default="mandarin"),
    scenario: Optional[str] = Form(default="news"),
    output_name: Optional[str] = Form(default=None),
    prompt_audio: Optional[UploadFile] = File(default=None),
) -> dict:
    if not (voice_id or "").strip() and not (prompt_audio is not None and prompt_audio.filename):
        raise HTTPException(status_code=400, detail="请先选择音色或参考音频后，再重生成本段。")
    prompt_path: Path | None = None
    if prompt_audio is not None and prompt_audio.filename:
        suffix = Path(prompt_audio.filename).suffix or ".wav"
        prompt_path = service.persist_upload(await prompt_audio.read(), suffix, prefix="segment_prompt")
    try:
        result = service.regenerate_segment(
            text=text,
            index=index,
            mode=mode,
            voice_id=(voice_id or "").strip() or None,
            prompt_text=(prompt_text or "").strip() or None,
            prompt_language=(prompt_language or "").strip() or None,
            instruction=(instruction or "").strip() or None,
            style=(style or "").strip() or "natural",
            style_intensity=(style_intensity or "").strip() or "medium",
            prompt_wav_path=prompt_path,
            speed=speed,
            text_frontend=text_frontend,
            language=(language or "").strip() or None,
            dialect=(dialect or "").strip() or None,
            scenario=(scenario or "").strip() or None,
            output_name=(output_name or "").strip() or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"单段重生成失败：{exc}") from exc
    return {"ok": True, "segment": result}


@app.post("/api/rebuild-output")
def api_rebuild_output(payload: dict = Body(...)) -> dict:
    try:
        result = service.rebuild_outputs_from_segments(
            payload.get("segments") or [],
            build_zip=bool(payload.get("build_zip", True)),
            output_name=(payload.get("output_name") or "").strip() or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"重建结果失败：{exc}") from exc
    return {"ok": True, "result": result}


@app.post("/api/quality-check")
def api_quality_check(payload: dict = Body(...)) -> dict:
    filename = Path(payload.get("filename") or "").name
    expected_text = (payload.get("text") or "").strip()
    if not filename or not expected_text:
        raise HTTPException(status_code=400, detail="缺少待质检音频或播报稿。")
    try:
        result = service.quality_check_generated(config.output_dir / filename, expected_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"文字质检失败：{exc}") from exc
    return {"ok": True, "result": result}


@app.post("/api/transcribe-reference")
async def api_transcribe_reference(ref_audio: UploadFile = File(...)) -> dict:
    suffix = Path(ref_audio.filename or "reference.wav").suffix or ".wav"
    audio_path = service.persist_upload(await ref_audio.read(), suffix, prefix="reference_asr")
    try:
        result = service.transcribe_reference(audio_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"识别失败：{exc}") from exc
    return {"ok": True, **result}


@app.post("/api/translate")
def api_translate(
    text: str = Form(...),
    target_language: str = Form(...),
    source_language: str = Form(default="auto"),
) -> dict:
    try:
        result = translator.translate(
            text=text,
            target_language=(target_language or "").strip(),
            source_language=(source_language or "auto").strip() or "auto",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"自动翻译失败：{exc}") from exc
    return {"ok": True, **result}


@app.get("/api/translation-settings")
def api_translation_settings() -> dict:
    return {"ok": True, "settings": translator.settings()}


@app.post("/api/translation-settings")
def api_update_translation_settings(payload: dict = Body(...)) -> dict:
    try:
        settings = translator.update_settings(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "settings": settings, "translation": translator.status().__dict__}


@app.post("/api/translation-settings/test")
def api_test_translation_settings() -> dict:
    try:
        return {"ok": True, **translator.test_connection()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/translation-settings/clear-credentials")
def api_clear_translation_credentials(payload: dict = Body(...)) -> dict:
    try:
        settings = translator.clear_credentials(str(payload.get("provider") or ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "settings": settings, "translation": translator.status().__dict__}


@app.get("/api/voices")
def api_list_voices() -> dict:
    return {"ok": True, "voices": service.list_voices()}


@app.post("/api/voices")
async def api_save_voice(
    name: str = Form(...),
    transcript: str = Form(default=""),
    prompt_language: str = Form(default=""),
    ref_audio: UploadFile = File(...),
) -> dict:
    suffix = Path(ref_audio.filename or "reference.wav").suffix or ".wav"
    audio_path = service.persist_upload(await ref_audio.read(), suffix, prefix="voice_ref")
    try:
        voice = service.save_voice(name=name, transcript=transcript, audio_path=audio_path, source_filename=ref_audio.filename or audio_path.name, prompt_language=prompt_language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"保存音色失败：{exc}") from exc
    return {"ok": True, "voice": voice}


@app.delete("/api/voices/{voice_id}")
def api_delete_voice(voice_id: str) -> dict:
    try:
        service.delete_voice(voice_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@app.post("/api/voices/{voice_id}/pin")
def api_pin_voice(voice_id: str) -> dict:
    try:
        voice = service.pin_voice(voice_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "voice": voice, "voices": service.list_voices()}


@app.post("/api/history-reference")
async def api_history_reference(ref_audio: UploadFile = File(...)) -> dict:
    suffix = Path(ref_audio.filename or "reference.wav").suffix or ".wav"
    file_name, _ = service.persist_history_reference(
        await ref_audio.read(),
        suffix,
        prefix="history_ref",
    )
    return {
        "ok": True,
        "file_name": file_name,
        "audio_url": f"/history/audio/{file_name}",
    }


@app.get("/api/history")
def api_history(limit: int = 10) -> dict:
    return {"ok": True, "items": service.load_history(limit=limit)}


@app.post("/api/history")
def api_save_history(payload: dict = Body(...)) -> dict:
    return {"ok": True, "item": service.save_history(payload)}


@app.get("/api/templates")
def api_templates() -> dict:
    return {"ok": True, "items": service.list_templates()}


@app.post("/api/templates")
def api_save_template(payload: dict = Body(...)) -> dict:
    try:
        item = service.save_template(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "item": item, "items": service.list_templates()}


@app.delete("/api/templates/{template_id}")
def api_delete_template(template_id: str) -> dict:
    try:
        service.delete_template(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "items": service.list_templates()}



@app.get("/api/outputs/{file_name}")
def api_output(file_name: str):
    file_path = config.output_dir / file_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="输出文件不存在")
    return FileResponse(file_path)
