async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const message = typeof payload === "string" ? payload : payload.detail || payload.message || `Request failed: ${response.status}`;
    throw new Error(message);
  }
  return payload;
}

function $(id) {
  return document.getElementById(id);
}

function getCurrentMode() {
  return "zero_shot";
}

function isCantoneseMode(languageValue = $("language")?.value, dialectValue = $("dialect")?.value) {
  return (languageValue || "zh") === "zh" && (dialectValue || "mandarin") === "cantonese";
}

function usesTranslatedScript() {
  return ($("language").value || "zh") !== "zh" || isCantoneseMode();
}

function getTranslationTargetLanguage() {
  return isCantoneseMode() ? "yue" : ($("language").value || "zh");
}

function getSegmentMode() {
  return isCantoneseMode() ? "cantonese_news" : "natural";
}

const state = {
  status: null,
  currentResult: null,
  segmentsExpanded: false,
  historyExpanded: false,
  resultSummaryExpanded: false,
  presetVoices: [],
  voices: [],
  templates: [],
  dialectGuidance: {},
  translation: {},
  translationSignature: "",
  translationEdited: false,
  translationTimer: null,
  sourceTextZh: "",
  progressTimer: null,
  progressMessage: "",
  progressPercent: 0,
  progressCeiling: 92,
  promptWave: null,
  promptRegionsPlugin: null,
  resultWave: null,
  resultWaveUrl: "",
  promptObjectUrl: "",
  promptAudioFile: null,
  promptSourceUrl: "",
  promptRegion: null,
  promptClipDuration: 0,
  promptClipStart: 0,
  promptClipEnd: 0,
  promptClipActive: false,
  promptBaseSource: null,
  promptTranscribeTimer: null,
  pendingPromptClipRestore: null,
  promptLanguage: "",
  templateApplying: false,
};

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function setStatus(message) {
  $("statusBox").textContent = message;
}

function formatSeconds(seconds) {
  return `${Number(seconds || 0).toFixed(2)} 秒`;
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function setProgress(percent, message) {
  $("progressFill").style.width = `${Math.max(0, Math.min(100, percent))}%`;
  $("progressText").textContent = message;
}

function stopBusyProgress(finalPercent = null, finalMessage = "") {
  if (state.progressTimer) {
    clearInterval(state.progressTimer);
    state.progressTimer = null;
  }
  $("progressFill").classList.remove("live");
  if (finalPercent !== null) {
    state.progressPercent = finalPercent;
    setProgress(finalPercent, finalMessage);
  }
}

function startBusyProgress(message, startPercent = 12, ceiling = 92) {
  stopBusyProgress();
  state.progressMessage = message;
  state.progressPercent = startPercent;
  state.progressCeiling = ceiling;
  let tick = 0;
  $("progressFill").classList.add("live");
  const render = () => {
    const dots = ".".repeat((tick % 3) + 1);
    setProgress(state.progressPercent, `${state.progressMessage}${dots}`);
  };
  render();
  state.progressTimer = setInterval(() => {
    tick += 1;
    if (state.progressPercent < 46) {
      state.progressPercent = Math.min(state.progressPercent + 1.8, state.progressCeiling);
    } else if (state.progressPercent < 72) {
      state.progressPercent = Math.min(state.progressPercent + 0.9, state.progressCeiling);
    } else if (state.progressPercent < 86) {
      state.progressPercent = Math.min(state.progressPercent + 0.35, state.progressCeiling);
    } else {
      state.progressPercent = Math.min(state.progressPercent + 0.08, state.progressCeiling);
    }
    render();
  }, 420);
}

function updateCharCount() {
  $("charCount").textContent = `当前字数：${$("text").value.trim().length}`;
}

function getLiveSegmentCount() {
  const text = ($("text").value || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
  if (!text) return 0;
  if (!$("autoSegment").checked) return 1;
  return text.split(/\n+/).map((item) => item.trim()).filter(Boolean).length || 1;
}

function updateSegmentSummaryLive() {
  if (state.currentResult?.segments?.length) return;
  const count = getLiveSegmentCount();
  if (!count) {
    $("segmentSummary").textContent = "尚未输入可生成的文稿内容。";
    return;
  }
  if ($("autoSegment").checked) {
    $("segmentSummary").textContent = `当前按回车自然分为 ${count} 个主段。生成后可查看分段详情。`;
  } else {
    $("segmentSummary").textContent = "当前未启用自然段分段配音，生成时将整篇作为 1 个配音段。";
  }
}

function applyLanguageChangeState(nextLanguage) {
  if (nextLanguage === "zh") {
    $("text").value = state.sourceTextZh || $("text").value || "";
    if (!isCantoneseMode(nextLanguage, $("dialect").value)) {
      $("translatedText").value = "";
    }
    updateCharCount();
  } else if (!state.sourceTextZh) {
    state.sourceTextZh = $("text").value || "";
  }
  updateDialectVisibility();
  updateTranslationPanel();
  state.translationEdited = false;
  scheduleAutoTranslate();
}

function renderSelect(select, items, value) {
  select.innerHTML = items.map((item) => `<option value="${item.value}" ${item.disabled ? "disabled" : ""} ${item.group ? `data-group="${item.group}"` : ""}>${item.label}</option>`).join("");
  if (value !== undefined) select.value = value;
}

function renderDialectSelect(items, value) {
  const options = (items || []).map((item) => {
    let suffix = "";
    if (item.group === "recommended") suffix = "（推荐）";
    if (item.group === "experimental") suffix = "（试听优先）";
    return {
      ...item,
      label: `${item.label}${suffix}`,
    };
  });
  renderSelect($("dialect"), options, value);
}

function renderVoiceSelect(selectedValue = "") {
  const options = [{ value: "", label: "请选择音色" }];
  if (state.presetVoices.length) {
    options.push({ value: "__preset__", label: "──────── 系统预置音色 ────────", disabled: true });
    options.push(...state.presetVoices.map((voice) => ({
      value: voice.id,
      label: `${voice.label}`,
    })));
  }
  if (state.voices.length) {
    options.push({ value: "__saved__", label: "──────── 已保存参考音色 ────────", disabled: true });
    options.push(...state.voices.map((voice) => ({
      value: voice.id,
      label: `${voice.pinned_at ? "置顶 · " : ""}${voice.name} | ${voice.created_at || ""}`,
    })));
  }
  renderSelect($("voiceSelect"), options, selectedValue);
  updatePinButtonState();
}

function initWave() {
  if (!window.WaveSurfer) {
    setStatus("音频波形组件未能加载，请刷新页面后重试。");
    return;
  }
  if (state.promptWave) return;
  state.promptRegionsPlugin = window.WaveSurfer?.Regions?.create
    ? window.WaveSurfer.Regions.create()
    : null;
  const plugins = state.promptRegionsPlugin ? [state.promptRegionsPlugin] : [];
  state.promptWave = WaveSurfer.create({
    container: "#promptWave",
    waveColor: "#f0a53c",
    progressColor: "#ff8f1f",
    cursorColor: "#ffd08a",
    height: 88,
    barWidth: 3,
    barGap: 2,
    barRadius: 2,
    normalize: true,
    dragToSeek: true,
    plugins,
  });
  state.promptWave.on("play", () => { $("promptWavePlayBtn").textContent = "暂停参考音频"; });
  state.promptWave.on("pause", () => { $("promptWavePlayBtn").textContent = "播放参考音频"; });
  state.promptWave.on("finish", () => { $("promptWavePlayBtn").textContent = "播放参考音频"; });
  state.promptWave.on("error", () => {
    $("promptWavePlayBtn").disabled = true;
    $("promptClipApplyBtn").disabled = true;
    setStatus("参考音频已导入，但浏览器未能解码波形。请重新选择 WAV 文件。");
  });
  state.promptWave.on("ready", () => {
    if (state.pendingPromptClipRestore) {
      state.promptClipActive = !!state.pendingPromptClipRestore.active;
      state.promptClipStart = Number(state.pendingPromptClipRestore.start || 0);
      state.promptClipEnd = Number(state.pendingPromptClipRestore.end || 0);
      syncPromptClipSelection(true);
      state.pendingPromptClipRestore = null;
      return;
    }
    syncPromptClipSelection(false);
  });
}

function initResultWave(force = false) {
  if (!window.WaveSurfer) {
    setStatus("音频波形组件未能加载，请刷新页面后重试。");
    return;
  }
  if (force && state.resultWave) {
    try { state.resultWave.destroy(); } catch (error) {}
    state.resultWave = null;
    $("resultWaveform").innerHTML = "";
  }
  if (state.resultWave) return;
  state.resultWave = WaveSurfer.create({
    container: "#resultWaveform",
    waveColor: "#f0a53c",
    progressColor: "#ff8f1f",
    cursorColor: "#ffd08a",
    height: 84,
    barWidth: 3,
    barGap: 2,
    barRadius: 2,
    normalize: true,
    dragToSeek: true,
  });
  state.resultWave.on("play", () => { $("resultWavePlayBtn").textContent = "暂停结果"; });
  state.resultWave.on("pause", () => { $("resultWavePlayBtn").textContent = "播放结果"; });
  state.resultWave.on("finish", () => { $("resultWavePlayBtn").textContent = "播放结果"; });
  state.resultWave.on("ready", () => {
    requestAnimationFrame(() => {
      try {
        state.resultWave?.setOptions({ height: 84 });
      } catch (error) {}
    });
    $("resultWavePlayBtn").disabled = false;
  });
  state.resultWave.on("error", () => {
    $("resultWavePlayBtn").disabled = true;
    setStatus("结果音频已生成，但波形加载失败。可先直接下载或刷新后再试。");
  });
}

function loadPromptWaveFromUrl(url) {
  initWave();
  if (!state.promptWave || !url) return;
  state.promptSourceUrl = url;
  state.promptWave.load(url);
  $("promptWavePlayBtn").textContent = "播放参考音频";
}

function loadResultWave(url) {
  if (!url) {
    if (state.resultWave && typeof state.resultWave.empty === "function") {
      state.resultWave.empty();
    }
    state.resultWaveUrl = "";
    $("resultWavePlayBtn").textContent = "播放结果";
    $("resultWavePlayBtn").disabled = true;
    return;
  }
  state.resultWaveUrl = url;
  initResultWave(true);
  if (!state.resultWave) {
    return;
  }
  $("resultWavePlayBtn").disabled = true;
  state.resultWave.load(url);
}

function syncResultWaveCursor() {
  return;
}

function schedulePromptTranscribe() {
  if (state.promptTranscribeTimer) {
    clearTimeout(state.promptTranscribeTimer);
  }
  state.promptTranscribeTimer = setTimeout(async () => {
    if (!state.promptClipActive) return;
    try {
      await transcribeCurrentReference();
    } catch (error) {
      setStatus(error.message || "参考音频剪辑后重新识别失败。");
    }
  }, 320);
}

function removePromptRegion() {
  if (state.promptRegion) {
    try { state.promptRegion.remove(); } catch (error) {}
    state.promptRegion = null;
  }
  $("promptClipApplyBtn").classList.remove("active");
}

function resetPromptClipUi() {
  state.promptClipDuration = 0;
  state.promptClipStart = 0;
  state.promptClipEnd = 0;
  removePromptRegion();
  $("promptClipApplyBtn").disabled = true;
  $("promptClipResetBtn").disabled = !state.promptClipActive;
  $("promptClipStartLabel").textContent = formatSeconds(0);
  $("promptClipEndLabel").textContent = formatSeconds(0);
  $("promptClipKeepLabel").textContent = formatSeconds(0);
  $("promptClipDurationLabel").textContent = formatSeconds(0);
  $("promptClipTip").textContent = state.promptClipActive
    ? "当前将按所选范围提交。"
    : "当前未剪辑，将默认提交完整参考音频；若超过15秒，优先在8–15秒内的自然停顿处截取。";
}

function updatePromptClipUi() {
  const duration = Math.max(0, state.promptClipDuration || 0);
  const start = clamp(state.promptClipStart || 0, 0, duration || 0);
  const end = clamp(state.promptClipEnd || 0, start, duration || 0);
  const effectiveEnd = Math.min(end, start + 15);
  const keepDuration = Math.max(0, effectiveEnd - start);
  state.promptClipStart = start;
  state.promptClipEnd = end;
  const hasAudio = duration > 0.05;
  $("promptClipApplyBtn").disabled = !hasAudio;
  $("promptClipResetBtn").disabled = !state.promptClipActive;
  $("promptClipStartLabel").textContent = formatSeconds(start);
  $("promptClipEndLabel").textContent = formatSeconds(effectiveEnd);
  $("promptClipKeepLabel").textContent = formatSeconds(keepDuration);
  $("promptClipDurationLabel").textContent = formatSeconds(duration);
  if (!state.promptClipActive || !state.promptRegion) {
    $("promptClipTip").textContent = "当前未剪辑，将默认提交完整参考音频；若超过15秒，优先在8–15秒内的自然停顿处截取。";
  } else if ((end - start) > 15) {
    $("promptClipTip").textContent = "当前选区超过15秒，提交时将自动保留前15秒。";
  } else {
    $("promptClipTip").textContent = "当前将按所选范围提交。";
  }
}

function createDefaultPromptRegion() {
  if (!state.promptRegionsPlugin || !state.promptClipDuration) return;
  removePromptRegion();
  state.promptRegion = state.promptRegionsPlugin.addRegion({
    start: 0,
    end: Math.min(state.promptClipDuration, 10),
    drag: true,
    resize: true,
    color: "rgba(255, 157, 47, 0.18)",
  });
  state.promptClipStart = state.promptRegion.start;
  state.promptClipEnd = state.promptRegion.end;
  state.promptRegion.on("update", () => {
    state.promptClipStart = state.promptRegion.start;
    state.promptClipEnd = state.promptRegion.end;
    updatePromptClipUi();
  });
  state.promptRegion.on("update-end", () => {
    state.promptClipStart = state.promptRegion.start;
    state.promptClipEnd = state.promptRegion.end;
    updatePromptClipUi();
    schedulePromptTranscribe();
  });
  $("promptClipApplyBtn").classList.add("active");
  $("promptClipResetBtn").disabled = false;
  updatePromptClipUi();
}

function syncPromptClipSelection(preserve = false) {
  initWave();
  if (!state.promptWave) {
    resetPromptClipUi();
    return;
  }
  const duration = Number(state.promptWave.getDuration() || 0);
  if (!duration) {
    resetPromptClipUi();
    return;
  }
  state.promptClipDuration = duration;
  if (!preserve) {
    state.promptClipStart = 0;
    state.promptClipEnd = Math.min(duration, 15);
    state.promptClipActive = false;
  } else {
    state.promptClipStart = clamp(state.promptClipStart, 0, duration);
    state.promptClipEnd = clamp(state.promptClipEnd || duration, state.promptClipStart, duration);
  }
  removePromptRegion();
  if (state.promptClipActive && state.promptRegionsPlugin) {
    state.promptRegion = state.promptRegionsPlugin.addRegion({
      start: state.promptClipStart,
      end: state.promptClipEnd,
      drag: true,
      resize: true,
      color: "rgba(255, 157, 47, 0.18)",
    });
    state.promptRegion.on("update", () => {
      state.promptClipStart = state.promptRegion.start;
      state.promptClipEnd = state.promptRegion.end;
      updatePromptClipUi();
    });
    state.promptRegion.on("update-end", () => {
      state.promptClipStart = state.promptRegion.start;
      state.promptClipEnd = state.promptRegion.end;
      updatePromptClipUi();
      schedulePromptTranscribe();
    });
    $("promptClipApplyBtn").classList.add("active");
  }
  updatePromptClipUi();
}

function setPromptBaseSource(source) {
  state.promptBaseSource = source;
  state.promptLanguage = source?.language || "";
  state.promptClipActive = false;
  state.pendingPromptClipRestore = null;
}

function clearPromptAudioInput() {
  $("promptAudio").value = "";
  state.promptAudioFile = null;
  if (state.promptObjectUrl) {
    URL.revokeObjectURL(state.promptObjectUrl);
    state.promptObjectUrl = "";
  }
}

function clearPromptWaveAndText() {
  $("promptText").value = "";
  state.promptSourceUrl = "";
  state.promptClipActive = false;
  state.promptBaseSource = null;
  state.promptLanguage = "";
  state.pendingPromptClipRestore = null;
  if (state.promptTranscribeTimer) {
    clearTimeout(state.promptTranscribeTimer);
    state.promptTranscribeTimer = null;
  }
  if (state.promptWave) {
    state.promptWave.empty();
  }
  $("promptWavePlayBtn").textContent = "播放参考音频";
  resetPromptClipUi();
}

function resetVoiceSelection() {
  $("voiceSelect").value = "";
  updatePinButtonState();
}

function applyPromptAudioFile(file) {
  state.promptAudioFile = file || null;
  if (state.promptObjectUrl) {
    URL.revokeObjectURL(state.promptObjectUrl);
    state.promptObjectUrl = "";
  }
  if (file) {
    state.promptObjectUrl = URL.createObjectURL(file);
    state.promptSourceUrl = state.promptObjectUrl;
    loadPromptWaveFromUrl(state.promptObjectUrl);
  } else {
    state.promptSourceUrl = "";
    resetPromptClipUi();
  }
}

async function getPromptSourceArrayBuffer() {
  if (state.promptAudioFile) {
    return await state.promptAudioFile.arrayBuffer();
  }
  if (state.promptSourceUrl) {
    const response = await fetch(state.promptSourceUrl);
    if (!response.ok) {
      throw new Error("无法读取当前参考音频。");
    }
    return await response.arrayBuffer();
  }
  throw new Error("当前没有可裁剪的参考音频。");
}

function audioBufferToWavBlob(audioBuffer) {
  const channels = audioBuffer.numberOfChannels;
  const sampleRate = audioBuffer.sampleRate;
  const samples = audioBuffer.length;
  const bytesPerSample = 2;
  const blockAlign = channels * bytesPerSample;
  const buffer = new ArrayBuffer(44 + samples * blockAlign);
  const view = new DataView(buffer);
  const writeString = (offset, value) => {
    for (let index = 0; index < value.length; index += 1) {
      view.setUint8(offset + index, value.charCodeAt(index));
    }
  };
  writeString(0, "RIFF");
  view.setUint32(4, 36 + samples * blockAlign, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, channels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * blockAlign, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, samples * blockAlign, true);
  let offset = 44;
  const channelData = Array.from({ length: channels }, (_, channel) => audioBuffer.getChannelData(channel));
  for (let index = 0; index < samples; index += 1) {
    for (let channel = 0; channel < channels; channel += 1) {
      const sample = Math.max(-1, Math.min(1, channelData[channel][index] || 0));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
      offset += 2;
    }
  }
  return new Blob([buffer], { type: "audio/wav" });
}

function cropPromptAudio() {
  if (state.promptClipDuration <= 0) {
    setStatus("请先上传参考音频，再进行剪辑。");
    return;
  }
  state.promptClipActive = true;
  if (!state.promptRegion) {
    createDefaultPromptRegion();
    $("promptClipTip").textContent = "已进入剪辑模式，可直接在波形上拖动选区两端。";
  } else {
    $("promptClipApplyBtn").classList.add("active");
    $("promptClipTip").textContent = "可继续拖动选区两端，或按住选区整体左右移动。";
    updatePromptClipUi();
  }
  setStatus("已进入参考音频剪辑模式，可直接在波形上拖动选区两端或整体移动。");
}

function restorePromptAudio() {
  state.promptClipActive = false;
  removePromptRegion();
  syncPromptClipSelection(false);
  if (state.promptBaseSource?.transcript) {
    $("promptText").value = state.promptBaseSource.transcript;
  }
  $("promptClipTip").textContent = "已撤销剪辑，恢复完整波形。";
  setStatus("已撤销参考音频剪辑，恢复为原始参考音频。");
}

async function buildPromptAudioForSubmit() {
  const sourceBuffer = await getPromptSourceArrayBuffer();
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const decoded = await audioContext.decodeAudioData(sourceBuffer.slice(0));
  const duration = decoded.duration || 0;
  let start = 0;
  let end = duration;
  if (state.promptClipActive && state.promptRegion) {
    start = clamp(state.promptRegion.start || 0, 0, duration);
    end = clamp(state.promptRegion.end || duration, start, duration);
  } else if (duration > 15) {
    end = findNaturalPromptClipEnd(decoded);
  }
  const startFrame = Math.max(0, Math.floor(start * decoded.sampleRate));
  const endFrame = Math.min(decoded.length, Math.ceil(end * decoded.sampleRate));
  const frameLength = Math.max(1, endFrame - startFrame);
  const clippedBuffer = audioContext.createBuffer(decoded.numberOfChannels, frameLength, decoded.sampleRate);
  for (let channel = 0; channel < decoded.numberOfChannels; channel += 1) {
    const source = decoded.getChannelData(channel).subarray(startFrame, endFrame);
    clippedBuffer.copyToChannel(source, channel, 0);
  }
  const wavBlob = audioBufferToWavBlob(clippedBuffer);
  const originalName = (state.promptBaseSource?.name || state.promptAudioFile?.name || "reference").replace(/\.[^.]+$/, "");
  return new File([wavBlob], `${originalName}_submit.wav`, { type: "audio/wav" });
}

function findNaturalPromptClipEnd(audioBuffer) {
  const sampleRate = audioBuffer.sampleRate;
  const windowFrames = Math.max(1, Math.round(sampleRate * 0.02));
  const firstWindow = Math.floor(8 * sampleRate / windowFrames);
  const lastWindow = Math.min(Math.floor(15 * sampleRate / windowFrames), Math.floor(audioBuffer.length / windowFrames));
  const levels = [];
  for (let windowIndex = 0; windowIndex < lastWindow; windowIndex += 1) {
    const startFrame = windowIndex * windowFrames;
    const endFrame = Math.min(audioBuffer.length, startFrame + windowFrames);
    let sumSquares = 0;
    let sampleCount = 0;
    for (let channel = 0; channel < audioBuffer.numberOfChannels; channel += 1) {
      const samples = audioBuffer.getChannelData(channel);
      for (let frame = startFrame; frame < endFrame; frame += 1) {
        sumSquares += samples[frame] * samples[frame];
        sampleCount += 1;
      }
    }
    levels.push(Math.sqrt(sumSquares / Math.max(1, sampleCount)));
  }
  const sortedLevels = levels.slice().sort((a, b) => a - b);
  const speechLevel = sortedLevels[Math.floor(sortedLevels.length * 0.7)] || 0;
  const silenceThreshold = Math.max(0.003, speechLevel * 0.18);
  const minimumSilentWindows = 9;
  let silentStart = -1;
  let lastNaturalEnd = 15;
  for (let index = firstWindow; index < lastWindow; index += 1) {
    if (levels[index] <= silenceThreshold) {
      if (silentStart < 0) silentStart = index;
    } else if (silentStart >= 0) {
      if ((index - silentStart) >= minimumSilentWindows) {
        lastNaturalEnd = ((silentStart + index) / 2) * windowFrames / sampleRate;
      }
      silentStart = -1;
    }
  }
  if (silentStart >= 0 && (lastWindow - silentStart) >= minimumSilentWindows) {
    lastNaturalEnd = ((silentStart + lastWindow) / 2) * windowFrames / sampleRate;
  }
  return Math.min(15, Math.max(8, lastNaturalEnd));
}

function renderFromStatus(status) {
    state.status = status;
    state.presetVoices = status.preset_voices || [];
    state.voices = status.voices || [];
    state.templates = status.templates || [];
    state.dialectGuidance = status.capabilities.dialect_guidance || {};
    state.translation = status.translation || {};
    $("bundleChip").textContent = status.bundle.available ? "Rainfall 已连接" : "Rainfall 未连接";
    renderSelect($("language"), status.capabilities.languages, "zh");
    renderDialectSelect(status.capabilities.dialects, "mandarin");
    renderChannelTemplateSelect("");
    renderVoiceSelect("");
    updateDialectVisibility();
    renderHistory(status.history || []);
  }

function renderChannelTemplateSelect(selectedValue = "") {
  const items = [{ value: "", label: "请选择已保存模板" }]
    .concat((state.templates || []).map((item) => ({
      value: item.id,
      label: item.name,
    })));
  renderSelect($("channelTemplateSelect"), items, selectedValue);
}

function updateDialectVisibility() {
  const showDialect = $("language").value === "zh";
  $("dialectField").classList.toggle("hidden", !showDialect);
  $("dialectHint").classList.toggle("hidden", !showDialect);
  $("translatePanel").classList.toggle("hidden", showDialect);
  if (!showDialect) return;
  const selected = $("dialect").selectedOptions[0];
  const group = selected?.dataset?.group || "";
  let message = state.dialectGuidance.default || "推荐先用一两句短文本试听，再决定是否用于整篇配音。";
  if (group === "recommended") {
    message = state.dialectGuidance.recommended || message;
  } else if (group === "experimental") {
    message = state.dialectGuidance.experimental || message;
    if (["fuzhou", "hakka", "chaozhou"].includes($("dialect").value)) {
      message = state.dialectGuidance.high_risk || message;
    }
  }
  $("dialectHint").textContent = message;
}

function getLanguageLabel(value) {
  const match = state.status?.capabilities?.languages?.find((item) => item.value === value);
  return match?.label || value;
}

function getHistoryPreview(item) {
  const shorten = (value, limit = 72) => {
    const text = (value || "").replace(/\s+/g, " ").trim();
    if (text.length <= limit) return text;
    return `${text.slice(0, limit)}...`;
  };
  if ((item.language || "zh") !== "zh") {
    return shorten(item.translated_preview || item.translated_text || item.text_preview || "");
  }
  return shorten(item.text_preview || "");
}

function getHistorySourcePreview(item) {
  if ((item.language || "zh") === "zh") return "";
  const source = (item.text_preview || item.text || "").trim();
  const translated = (item.translated_preview || item.translated_text || "").trim();
  if (!source || source === translated) return "";
  const compact = source.length > 64 ? `${source.slice(0, 64)}...` : source;
  return `中文原稿：${compact}`;
}

function buildResultSummary(result) {
  const languageValue = result.language || "zh";
  const languageLabel = getLanguageLabel(languageValue);
  const translated = (languageValue !== "zh" ? (($("text").value || result.translated_text || "").trim()) : "").trim();
  const sourceText = ((languageValue !== "zh" ? (state.sourceTextZh || result.source_text || "") : ($("text").value || result.source_text || "")) || "").trim();
  return [
    `输出文件：${result.file_name}`,
    `语种：${languageLabel}`,
    result.dialect ? `方言：${result.dialect}` : "",
    result.requested_mode && result.requested_mode !== result.mode ? `请求模式：${result.requested_mode}` : "",
    `当前模式：${result.mode}`,
    languageValue !== "zh" ? `译文状态：${translated ? "已就绪，可人工微调" : "未记录译文"}` : "",
    languageValue !== "zh" && sourceText ? `中文原稿：已保留` : "",
    result.control_instruction ? `控制指令：${result.control_instruction}` : "",
    `自然分段：${result.auto_segment_used ? "按回车启用" : "未启用"}`,
    `主段数量：${result.segments_count || 1}`,
    result.warning ? `提示：${result.warning}` : "",
    result.zip_filename ? `分段压缩包：${result.zip_filename}` : "",
  ].filter(Boolean).join("\n");
}

function normalizeSegment(segment) {
  const normalized = { ...segment };
  normalized.original_text = normalized.original_text || normalized.text || "";
  normalized.original_audio_url = normalized.original_audio_url || normalized.audio_url || "";
  normalized.original_file_name = normalized.original_file_name || normalized.file_name || "";
  normalized.original_file_path = normalized.original_file_path || normalized.file_path || "";
  normalized.modified_fields = Array.isArray(normalized.modified_fields) ? normalized.modified_fields : [];
  normalized.edit_text = normalized.edit_text ?? normalized.text ?? "";
  normalized.edit_speed = normalized.edit_speed || "";
  normalized.edit_voice_id = normalized.edit_voice_id || "";
  normalized.edit_language = normalized.edit_language || "";
  normalized.edit_dialect = normalized.edit_dialect || "";
  normalized.edit_style = "";
  normalized.editor_open = false;
  normalized.regenerated = !!normalized.regenerated;
  normalized.edited = !!normalized.edited || normalized.modified_fields.length > 0 || normalized.text !== normalized.original_text;
  return normalized;
}

function normalizeResult(result) {
  if (!result) return result;
  const segments = (result.segments || []).map((seg) => normalizeSegment(seg));
  return { ...result, segments, segments_count: result.segments_count || segments.length || 1 };
}

function buildSegmentStatuses(seg) {
  const labels = {
    text: "已改文稿",
    speed: "已改语速",
    voice: "已改音色",
    language: "已改语种",
    dialect: "已改方言",
  };
  const statuses = (seg.modified_fields || []).map((field) => ({ label: labels[field] || field, active: true }));
  return statuses;
}

function normalizeInstructionInput(baseInstruction) {
  return (baseInstruction || "").trim();
}

function normalizeTemplateName(value) {
  let name = String(value || "").trim();
  if (!name) return "";
  if (name.endsWith("模版")) {
    name = `${name.slice(0, -2)}模板`;
  } else if (!name.endsWith("模板")) {
    name = `${name}模板`;
  }
  return name;
}

function getScenarioValueFor(languageValue, dialectValue) {
  if ((languageValue || "zh") !== "zh") return "multilingual";
  if ((dialectValue || "mandarin") === "cantonese") return "news";
  return dialectValue && dialectValue !== "mandarin" ? "dialect" : "news";
}

function getEffectiveSegmentSettings(seg) {
  const globalLanguage = $("language").value || "zh";
  const language = seg.edit_language || globalLanguage;
  const globalDialect = globalLanguage === "zh" ? ($("dialect").value || "mandarin") : "";
  const dialect = language === "zh"
    ? (seg.edit_dialect || (seg.edit_language ? (globalLanguage === "zh" ? globalDialect : "mandarin") : globalDialect || "mandarin"))
    : "";
  const voice_id = seg.edit_voice_id || $("voiceSelect").value || "";
  const style = "natural";
  const speed = Number(seg.edit_speed || $("speechRate").value || 1).toFixed(2);
  const text = (seg.edit_text ?? seg.text ?? "").trim();
  const instruction = normalizeInstructionInput($("instruction").value || "");
  return {
    text,
    language,
    dialect,
    voice_id,
    speed,
    style,
    instruction,
    scenario: getScenarioValueFor(language, dialect),
  };
}

function buildSegmentModifiedFields(seg) {
  const fields = [];
  const settings = getEffectiveSegmentSettings(seg);
  if (settings.text !== (seg.original_text || seg.text || "").trim()) fields.push("text");
  if (seg.edit_speed) fields.push("speed");
  if (seg.edit_voice_id) fields.push("voice");
  if (seg.edit_language) fields.push("language");
  if (seg.edit_dialect) fields.push("dialect");
  return fields;
}

function getEditorVoiceOptions(selectedValue) {
  const options = [`<option value="">跟随全局${$("voiceSelect").value ? "" : "（当前未指定）"}</option>`];
  if (state.presetVoices.length) {
    options.push('<option value="__preset__" disabled>──────── 系统预置音色 ────────</option>');
    options.push(...state.presetVoices.map((voice) => `<option value="${escapeHtml(voice.id)}" ${voice.id === selectedValue ? "selected" : ""}>${escapeHtml(voice.label)}</option>`));
  }
  if (state.voices.length) {
    options.push('<option value="__saved__" disabled>──────── 已保存参考音色 ────────</option>');
    options.push(...state.voices.map((voice) => `<option value="${escapeHtml(voice.id)}" ${voice.id === selectedValue ? "selected" : ""}>${escapeHtml(voice.pinned_at ? `置顶 · ${voice.name}` : voice.name)}</option>`));
  }
  return options.join("");
}

function getEditorLanguageOptions(selectedValue) {
  const globalLabel = getLanguageLabel($("language").value || "zh");
  const options = [`<option value="">跟随全局（${escapeHtml(globalLabel)}）</option>`];
  options.push(...(state.status?.capabilities?.languages || []).map((item) => `<option value="${escapeHtml(item.value)}" ${item.value === selectedValue ? "selected" : ""}>${escapeHtml(item.label)}</option>`));
  return options.join("");
}

function getEditorDialectOptions(languageValue, selectedValue) {
  if (languageValue !== "zh") {
    return '<option value="">当前语种无需方言</option>';
  }
  const globalDialectLabel = $("dialect").selectedOptions[0]?.textContent?.trim() || "普通话";
  const options = [`<option value="">跟随全局（${escapeHtml(globalDialectLabel)}）</option>`];
  options.push(...(state.status?.capabilities?.dialects || []).map((item) => `<option value="${escapeHtml(item.value)}" ${item.value === selectedValue ? "selected" : ""}>${escapeHtml(item.label)}</option>`));
  return options.join("");
}

function getEditorSpeedOptions(selectedValue) {
  const globalSpeedLabel = `${Number($("speechRate").value || 1).toFixed(2)}x`;
  const values = ["0.50", "0.80", "1.00", "1.20", "1.50", "1.80", "2.00"];
  return [`<option value="">跟随全局（${globalSpeedLabel}）</option>`, ...values.map((value) => `<option value="${value}" ${value === selectedValue ? "selected" : ""}>${value}x</option>`)].join("");
}

function renderSegmentEditor(seg) {
  if (!seg.editor_open) return "";
  const effectiveLanguage = seg.edit_language || $("language").value || "zh";
  const gridClass = effectiveLanguage === "zh" ? "segment-editor-grid four" : "segment-editor-grid";
  return `
    <div class="segment-editor">
      <label class="field">
        <span>文稿微调</span>
        <textarea class="segment-editor-input" data-index="${seg.index}" data-field="edit_text">${escapeHtml(seg.edit_text ?? seg.text ?? "")}</textarea>
      </label>
      <div class="${gridClass}">
        <label class="field">
          <span>语速</span>
          <select class="segment-editor-input" data-index="${seg.index}" data-field="edit_speed">${getEditorSpeedOptions(seg.edit_speed || "")}</select>
        </label>
        <label class="field">
          <span>音色选择</span>
          <select class="segment-editor-input" data-index="${seg.index}" data-field="edit_voice_id">${getEditorVoiceOptions(seg.edit_voice_id || "")}</select>
        </label>
        <label class="field">
          <span>语种</span>
          <select class="segment-editor-input" data-index="${seg.index}" data-field="edit_language">${getEditorLanguageOptions(seg.edit_language || "")}</select>
        </label>
        <label class="field">
          <span>方言</span>
          <select class="segment-editor-input" data-index="${seg.index}" data-field="edit_dialect">${getEditorDialectOptions(effectiveLanguage, seg.edit_dialect || "")}</select>
        </label>
      </div>
    </div>
  `;
}

function setTranslationStatus(message) {
  $("translateStatus").textContent = message || "";
}

const translationProviderHelp = {
  aliyun: "阿里云机器翻译：速度稳定，适合日常新闻稿翻译。需要 AccessKey ID 与 AccessKey Secret。",
  qwen_mt: "千问翻译（Qwen-MT）：面向翻译优化，适合多语种新闻稿与术语表达。需要 DashScope API Key。",
  baidu: "百度翻译：百度翻译开放平台标准接口。需要 APP ID 与密钥。",
  baidu_qianfan: "百度千帆大模型翻译：基于大模型理解上下文，适合需要润色与语境判断的稿件。需要千帆 API Key。",
};

const translationCredentialFields = {
  aliyun: [
    ["aliyunAccessKeyId", "aliyun_access_key_id"],
    ["aliyunAccessKeySecret", "aliyun_access_key_secret"],
  ],
  qwen_mt: [["qwenApiKey", "qwen_api_key"]],
  baidu: [
    ["baiduAppId", "baidu_translate_app_id"],
    ["baiduSecret", "baidu_translate_secret"],
  ],
  baidu_qianfan: [["baiduQianfanApiKey", "baidu_qianfan_api_key"]],
};

function updateTranslationCredentialPlaceholders() {
  const credentialStatus = state.translationSettings?.credential_status || {};
  Object.values(translationCredentialFields).flat().forEach(([inputId, settingKey]) => {
    const input = $(inputId);
    const saved = !!credentialStatus[settingKey];
    input.placeholder = saved ? "已保存：.............." : "可配置可留空";
    input.classList.toggle("credential-saved", saved);
  });
}

function updateTranslationProviderForm() {
  const provider = $("translationProvider").value || "aliyun";
  document.querySelectorAll(".translation-provider-fields").forEach((section) => {
    section.classList.toggle("hidden", section.dataset.provider !== provider);
  });
  const configuredProvider = (state.translationSettings?.providers || []).find((item) => item.value === provider);
  const credentials = translationCredentialFields[provider] || [];
  const hasSavedCredentials = credentials.some(([, settingKey]) => state.translationSettings?.credential_status?.[settingKey]);
  const suffix = configuredProvider?.configured
    ? "当前已配置；输入框以掩码提示，直接输入新值可替换已保存的凭据。"
    : "当前尚未配置。";
  $("translationProviderHelp").textContent = `${translationProviderHelp[provider] || "请选择翻译引擎。"} ${suffix}`;
  $("translationSettingsClearBtn").disabled = !hasSavedCredentials;
  $("translationSettingsClearBtn").title = hasSavedCredentials ? "清除当前翻译平台保存的凭据" : "当前平台没有可清除的已保存凭据";
  updateTranslationCredentialPlaceholders();
  $("translationSettingsStatus").textContent = "";
}

function applyTranslationSettingsForm(settings) {
  state.translationSettings = settings || {};
  $("translationProvider").value = settings?.provider || "aliyun";
  $("qwenMtModel").value = settings?.qwen_mt_model || "qwen-mt-plus";
  $("baiduQianfanModel").value = settings?.baidu_qianfan_model || "ernie-4.5-turbo-20260402";
  updateTranslationProviderForm();
}

function translationSettingsPayload() {
  return {
    translation_provider: $("translationProvider").value,
    aliyun_access_key_id: $("aliyunAccessKeyId").value,
    aliyun_access_key_secret: $("aliyunAccessKeySecret").value,
    qwen_api_key: $("qwenApiKey").value,
    qwen_mt_model: $("qwenMtModel").value,
    baidu_translate_app_id: $("baiduAppId").value,
    baidu_translate_secret: $("baiduSecret").value,
    baidu_qianfan_api_key: $("baiduQianfanApiKey").value,
    baidu_qianfan_model: $("baiduQianfanModel").value,
  };
}

async function loadTranslationSettings() {
  const payload = await fetchJson("/api/translation-settings");
  applyTranslationSettingsForm(payload.settings || {});
}

async function saveTranslationSettings(quiet = false) {
  const payload = await fetchJson("/api/translation-settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(translationSettingsPayload()),
  });
  state.translationSettings = payload.settings || {};
  state.translation = payload.translation || state.translation;
  ["aliyunAccessKeyId", "aliyunAccessKeySecret", "qwenApiKey", "baiduAppId", "baiduSecret", "baiduQianfanApiKey"].forEach((id) => { $(id).value = ""; });
  updateTranslationProviderForm();
  updateTranslationPanel();
  if (!quiet) {
    $("translationSettingsStatus").textContent = "翻译设置已保存。";
    setStatus(`翻译引擎已切换为${state.translation.provider_label || "当前设置"}。`);
  }
  return payload;
}

async function clearTranslationSettingsCredentials() {
  const provider = $("translationProvider").value || "aliyun";
  const label = $("translationProvider").selectedOptions[0]?.textContent || "当前翻译平台";
  if (!window.confirm(`确定清除${label}已保存的凭据吗？清除后该平台将不能自动翻译，直到重新填写凭据。`)) {
    return;
  }
  const payload = await fetchJson("/api/translation-settings/clear-credentials", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider }),
  });
  state.translationSettings = payload.settings || {};
  state.translation = payload.translation || state.translation;
  (translationCredentialFields[provider] || []).forEach(([inputId]) => { $(inputId).value = ""; });
  updateTranslationProviderForm();
  updateTranslationPanel();
  $("translationSettingsStatus").textContent = "当前平台凭据已清除。";
  setStatus(`${label}凭据已清除。`);
}

async function testTranslationSettings() {
  $("translationSettingsStatus").textContent = "正在保存并测试翻译连接……";
  await saveTranslationSettings(true);
  const payload = await fetchJson("/api/translation-settings/test", { method: "POST" });
  $("translationSettingsStatus").textContent = `连接正常，测试译文：${payload.translated_text || "已返回结果"}`;
  setStatus(`${payload.provider_label || "翻译引擎"}连接测试成功。`);
}

async function openTranslationSettings() {
  await loadTranslationSettings();
  $("translationSettingsDialog").showModal();
}

function updateTranslationPanel() {
  const cantoneseMode = isCantoneseMode();
  const translatedMode = usesTranslatedScript();
  $("translatePanel").classList.toggle("hidden", !translatedMode);
  $("sourceScriptLabel").textContent = cantoneseMode ? "第一步：原始中文稿" : "配音文稿";
  $("translatedScriptLabel").textContent = cantoneseMode ? "第二步：粤语播报稿（人工确认后配音）" : "自动译稿（可人工修改）";
  $("translatedText").placeholder = cantoneseMode
    ? "系统会把普通话书面稿转换为香港粤语播报稿。生成配音前请核对人名、地名、数字和专业术语。"
    : "系统会自动翻译当前中文文稿；这里也可以人工微调译文。";
  if (!translatedMode) {
    $("translatedText").value = "";
    state.translationSignature = "";
    state.translationEdited = false;
    setTranslationStatus("");
    return;
  }
  const targetLabel = cantoneseMode ? "香港粤语播报稿" : getLanguageLabel($("language").value);
  const providerReady = !!state.translation?.configured;
  setTranslationStatus(providerReady ? `当前目标：${targetLabel}，系统会自动生成，可人工修改。` : "自动转换暂不可用，请在译稿框中人工填写后再配音。");
}

function getTranslationSignature() {
  const sourceText = isCantoneseMode() ? ($("text").value || "") : (state.sourceTextZh || "");
  return `${$("language").value}|${$("dialect").value || ""}|${sourceText.trim()}`;
}

function updateRateValue() {
  const value = Number($("speechRate").value).toFixed(2);
  $("speechRateValue").textContent = `${value}x`;
  document.querySelectorAll(".speed-preset-btn").forEach((button) => {
    button.classList.toggle("active", button.dataset.rate === value);
  });
}

function setSpeechRateValue(value) {
  const normalized = Math.max(0.5, Math.min(2, Number(value) || 1)).toFixed(2);
  $("speechRate").value = normalized;
  updateRateValue();
}

function clearTemplateSelectionIfDirty(reason = "当前参数已改动，已退出模板状态。") {
  if (state.templateApplying) return;
  const currentTemplateId = $("channelTemplateSelect").value || "";
  if (!currentTemplateId) return;
  $("channelTemplateSelect").value = "";
  setStatus(reason);
}

function resetChannelTemplateFields() {
  state.templateApplying = true;
  $("channelTemplateSelect").value = "";
  $("language").value = "zh";
  applyLanguageChangeState("zh");
  $("dialect").value = "mandarin";
  setSpeechRateValue("1.00");
  $("styleSelect").value = "natural";
  $("instruction").value = "";
  renderVoiceSelect("");
  applyVoice("");
  $("channelTemplateNameInput").value = "";
  state.templateApplying = false;
  setStatus("已取消模板套用。");
}

function applyChannelTemplate(templateId) {
  const template = (state.templates || []).find((item) => item.id === templateId);
  if (!template) {
    resetChannelTemplateFields();
    return;
  }
  state.templateApplying = true;
  $("language").value = template.language;
  applyLanguageChangeState(template.language);
  if (template.language === "zh") {
    $("dialect").value = template.dialect || "mandarin";
  }
  setSpeechRateValue(template.speech_rate || template.speed || "1.00");
  $("styleSelect").value = "natural";
  $("instruction").value = template.instruction || "";
  if (template.voice_id) {
    renderVoiceSelect(template.voice_id);
    applyVoice(template.voice_id);
  } else {
    renderVoiceSelect("");
    applyVoice("");
  }
  $("channelTemplateNameInput").value = "";
  state.templateApplying = false;
  setStatus(`已套用模板：${template.name || "模板"}${template.voice_name ? `，音色：${template.voice_name}` : ""}`);
}

function getScenarioValue() {
  if ($("language").value !== "zh") return "multilingual";
  if ($("dialect").value === "cantonese") return "news";
  return $("dialect").value && $("dialect").value !== "mandarin" ? "dialect" : "news";
}

function updatePinButtonState() {
  const voice = state.voices.find((item) => item.id === $("voiceSelect").value);
  const selectedValue = $("voiceSelect").value;
  if (selectedValue.startsWith("preset:")) {
    $("pinVoiceBtn").textContent = "系统预置音色";
    return;
  }
  $("pinVoiceBtn").textContent = voice?.pinned_at ? "取消置顶音色" : "置顶当前音色";
}

async function saveCurrentChannelTemplate() {
  let name = normalizeTemplateName($("channelTemplateNameInput").value || "");
  if (!name) {
    throw new Error("请先输入模板名称。");
  }
  const voiceId = $("voiceSelect").value || "";
  if (!voiceId) {
    throw new Error("请先选择一个音色，再保存模板。若当前使用临时参考音频，请先保存为音色。");
  }
  const selectedPreset = state.presetVoices.find((item) => item.id === voiceId);
  const selectedVoice = state.voices.find((item) => item.id === voiceId);
  const payload = await fetchJson("/api/templates", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name,
      language: $("language").value || "zh",
      dialect: $("language").value === "zh" ? ($("dialect").value || "mandarin") : "",
      speech_rate: Number($("speechRate").value || 1).toFixed(2),
      style: $("styleSelect").value || "natural",
      instruction: $("instruction").value || "",
      voice_id: voiceId,
      voice_name: selectedPreset?.label || selectedVoice?.name || "",
      voice_kind: selectedPreset ? "preset" : selectedVoice ? "saved" : "",
    }),
  });
  state.templates = payload.items || [];
  const saved = payload.item || {};
  renderChannelTemplateSelect(saved.id || "");
  $("channelTemplateNameInput").value = "";
  setStatus(`已保存模板：${saved.name || name}${saved.voice_name ? `，音色：${saved.voice_name}` : ""}`);
}

async function deleteCurrentChannelTemplate() {
  const templateId = $("channelTemplateSelect").value || "";
  if (!templateId) {
    throw new Error("请先选择要删除的模板。");
  }
  const payload = await fetchJson(`/api/templates/${encodeURIComponent(templateId)}`, {
    method: "DELETE",
  });
  state.templates = payload.items || [];
  renderChannelTemplateSelect("");
  resetChannelTemplateFields();
  setStatus("已删除所选模板。");
}

async function getBaseFormDataWithText(textValue) {
  const formData = new FormData();
  formData.append("text", textValue || "");
  formData.append("mode", getCurrentMode());
  formData.append("prompt_text", $("promptText").value || "");
  formData.append("prompt_language", state.promptLanguage || "");
  formData.append("instruction", normalizeInstructionInput($("instruction").value || ""));
  formData.append("speed", Number($("speechRate").value || 1).toFixed(2));
  formData.append("text_frontend", "true");
  formData.append("language", $("language").value);
  formData.append("scenario", getScenarioValue());
  formData.append("style", $("styleSelect").value || "natural");
  formData.append("auto_segment", $("autoSegment").checked ? "true" : "false");
  formData.append("segment_mode", getSegmentMode());
  if ($("language").value === "zh") {
    formData.append("dialect", $("dialect").value);
  }
  const promptAudio = $("promptAudio").files[0] || state.promptAudioFile || state.promptSourceUrl;
  if (promptAudio) {
    formData.append("prompt_audio", await buildPromptAudioForSubmit());
  }
  const selectedVoiceId = $("voiceSelect").value;
  if (selectedVoiceId) {
    formData.append("voice_id", selectedVoiceId);
  }
  return formData;
}

async function translateCurrentText(force = false) {
  const cantoneseMode = isCantoneseMode();
  if ($("language").value === "zh" && !cantoneseMode) {
    state.sourceTextZh = $("text").value || "";
    return { translated_text: $("text").value || "" };
  }
  const sourceText = (cantoneseMode ? ($("text").value || "") : (state.sourceTextZh || "")).trim();
  if (!sourceText) {
    $("translatedText").value = "";
    state.translationSignature = "";
    state.translationEdited = false;
    throw new Error("请先输入中文文稿，再进行自动翻译。");
  }
  const signature = getTranslationSignature();
  const existing = (cantoneseMode ? ($("translatedText").value || "") : ($("text").value || "")).trim();
  if (!force && existing && state.translationSignature === signature) {
    setTranslationStatus(`当前播报稿已就绪：${cantoneseMode ? "粤语" : getLanguageLabel($("language").value)}。`);
    return { translated_text: existing };
  }
  const targetLabel = cantoneseMode ? "香港粤语播报稿" : getLanguageLabel($("language").value);
  setStatus(`正在生成${targetLabel}……`);
  const fd = new FormData();
  fd.append("text", sourceText);
  fd.append("target_language", getTranslationTargetLanguage());
  fd.append("source_language", cantoneseMode ? "zh" : "auto");
  try {
    const payload = await fetchJson("/api/translate", { method: "POST", body: fd });
    if (!cantoneseMode) {
      $("text").value = payload.translated_text || "";
    }
    $("translatedText").value = payload.translated_text || "";
    updateCharCount();
    state.translationSignature = signature;
    state.translationEdited = false;
    setTranslationStatus(`已生成${targetLabel}，请核对人名、地名、数字和专业术语后配音。`);
    setStatus(`已完成${targetLabel}转换。`);
    return payload;
  } catch (error) {
    if (existing) {
      setTranslationStatus(cantoneseMode
        ? "自动转换暂时失败，已保留当前粤语播报稿，可人工核对后继续配音。"
        : `自动翻译暂时失败，已保留当前${getLanguageLabel($("language").value)}文稿，可直接继续配音。`);
      setStatus(`自动翻译失败，已保留当前文稿：${error.message}`);
      return { translated_text: existing, fallback_used: true };
    }
    setTranslationStatus(`自动翻译失败，请稍后重试。`);
    throw error;
  }
}

async function translateArbitraryText(text, targetLanguage, sourceLanguage = "auto") {
  const sourceText = (text || "").trim();
  if (!sourceText) return "";
  if (!targetLanguage || targetLanguage === "zh") return sourceText;
  const fd = new FormData();
  fd.append("text", sourceText);
  fd.append("target_language", targetLanguage);
  fd.append("source_language", sourceLanguage);
  const payload = await fetchJson("/api/translate", { method: "POST", body: fd });
  return (payload.translated_text || "").trim();
}

function scheduleAutoTranslate() {
  if (state.translationTimer) {
    clearTimeout(state.translationTimer);
    state.translationTimer = null;
  }
  if (!usesTranslatedScript()) {
    updateTranslationPanel();
    return;
  }
  const sourceText = (isCantoneseMode() ? ($("text").value || "") : (state.sourceTextZh || "")).trim();
  if (!sourceText) {
    $("translatedText").value = "";
    state.translationSignature = "";
    state.translationEdited = false;
    updateTranslationPanel();
    return;
  }
  state.translationTimer = setTimeout(async () => {
    try {
      await translateCurrentText(true);
    } catch (error) {
      setStatus(`自动翻译失败：${error.message}`);
    }
  }, 400);
}

function renderGeneratedSegments(result) {
  $("toggleSegmentsBtn").disabled = !(result.segments || []).length;
  $("segmentSummary").textContent = result.segments?.length ? `已生成完成 ${result.segments.length} 个主段。` : "尚未生成分段结果。";
  $("segmentList").innerHTML = (result.segments || []).map((seg) => `
    <div class="segment-card ${seg.regenerated || seg.edited ? "modified" : ""}" data-index="${seg.index}">
      <div class="segment-top">
        <span class="segment-index">第 ${seg.index} 段</span>
        <div class="segment-actions">
          <button class="secondary ghost-mini segment-edit-toggle-btn" data-index="${seg.index}" type="button">${seg.editor_open ? "收起本段" : "编辑本段"}</button>
        </div>
      </div>
      <div class="segment-text">${escapeHtml(seg.text)}</div>
      ${buildSegmentStatuses(seg).length ? `<div class="segment-statuses">${buildSegmentStatuses(seg).map((item) => `<span class="segment-pill ${item.active ? "active" : ""}">${item.label}</span>`).join("")}</div>` : ""}
      ${renderSegmentEditor(seg)}
      <audio class="segment-audio" controls src="${seg.audio_url}"></audio>
      <div class="segment-actions">
        <a class="download-link" href="${seg.audio_url}" download>下载本段音频</a>
        <button class="secondary segment-regenerate-btn" data-index="${seg.index}" type="button">重生成本段</button>
        ${seg.regenerated && seg.original_audio_url ? `<button class="secondary segment-restore-btn" data-index="${seg.index}" type="button">恢复原始生成</button>` : ""}
      </div>
    </div>
  `).join("");
  document.querySelectorAll(".segment-edit-toggle-btn").forEach((button) => {
    button.addEventListener("click", () => toggleSegmentEditor(Number(button.dataset.index)));
  });
  document.querySelectorAll(".segment-regenerate-btn").forEach((button) => {
    button.addEventListener("click", () => regenerateSegment(Number(button.dataset.index)));
  });
  document.querySelectorAll(".segment-restore-btn").forEach((button) => {
    button.addEventListener("click", () => restoreOriginalSegment(Number(button.dataset.index)));
  });
  document.querySelectorAll(".segment-editor-input").forEach((input) => {
    if (input.dataset.field === "edit_language") {
      input.addEventListener("change", () => applySegmentLanguageChange(Number(input.dataset.index), input.value));
      return;
    }
    const handler = () => updateSegmentEditField(Number(input.dataset.index), input.dataset.field, input.value);
    input.addEventListener(input.tagName === "TEXTAREA" ? "input" : "change", handler);
  });
}

function renderResult(result) {
  state.currentResult = normalizeResult(result);
  result = state.currentResult;
  $("resultState").textContent = `已生成 ${result.segments_count || 1} 段`;
  loadResultWave(result.audio_url);
  $("resultSummary").textContent = buildResultSummary(result);
  $("downloadLink").href = result.audio_url;
  $("downloadLink").classList.remove("hidden");
  if (result.zip_url) {
    $("downloadZipLink").href = result.zip_url;
    $("downloadZipLink").classList.remove("hidden");
  } else {
    $("downloadZipLink").classList.add("hidden");
  }
  renderGeneratedSegments(result);
}

function toggleSegmentEditor(index) {
  if (!state.currentResult?.segments?.length) return;
  state.currentResult.segments = state.currentResult.segments.map((seg) => Number(seg.index) === Number(index) ? { ...seg, editor_open: !seg.editor_open } : seg);
  renderGeneratedSegments(state.currentResult);
}

function updateSegmentEditField(index, field, value) {
  const target = state.currentResult?.segments?.find((seg) => Number(seg.index) === Number(index));
  if (!target) return;
  target[field] = value;
  if (field === "edit_language") {
    if (value !== "zh") target.edit_dialect = "";
    renderGeneratedSegments(state.currentResult);
  }
}

async function applySegmentLanguageChange(index, nextLanguage) {
  const target = state.currentResult?.segments?.find((seg) => Number(seg.index) === Number(index));
  if (!target) return;
  const currentText = (target.edit_text ?? target.text ?? "").trim();
  const previousLanguage = target.edit_language || $("language").value || "zh";
  target.edit_language = nextLanguage || "";
  if ((nextLanguage || "zh") !== "zh") target.edit_dialect = "";
  if (!currentText) {
    renderGeneratedSegments(state.currentResult);
    return;
  }
  if (!nextLanguage || nextLanguage === "zh") {
    target.edit_text = (target.source_text || target.original_text || currentText).trim();
    renderGeneratedSegments(state.currentResult);
    return;
  }
  try {
    setStatus(`正在把第 ${index} 段翻译为${getLanguageLabel(nextLanguage)}……`);
    if (previousLanguage === "zh" && !target.source_text) {
      target.source_text = currentText;
    }
    target.edit_text = await translateArbitraryText(currentText, nextLanguage, "auto");
    renderGeneratedSegments(state.currentResult);
    setStatus(`第 ${index} 段已切换为${getLanguageLabel(nextLanguage)}文稿，可继续微调后重生成。`);
  } catch (error) {
    renderGeneratedSegments(state.currentResult);
    setStatus(`第 ${index} 段自动翻译失败：${error.message}`);
  }
}

async function generate() {
  const selectedVoiceId = $("voiceSelect").value || "";
  const promptAudio = $("promptAudio").files[0] || state.promptAudioFile || state.promptSourceUrl;
  if (!selectedVoiceId && !promptAudio) {
    throw new Error("请先从音色库选择一个音色，或上传参考音频后再生成。");
  }
  setStatus("正在生成，请稍候……");
  startBusyProgress("已提交生成任务，开始逐段生成", 14, 94);
  let targetText = $("text").value || "";
  const cantoneseMode = isCantoneseMode();
  if (cantoneseMode) {
    state.sourceTextZh = $("text").value || "";
    targetText = ($("translatedText").value || "").trim();
    if (!targetText) {
      targetText = (await translateCurrentText(false)).translated_text || "";
    }
    if (!targetText.trim()) {
      throw new Error("粤语播报稿为空，请先生成或人工填写粤语播报稿。");
    }
  } else if ($("language").value === "zh") {
    state.sourceTextZh = $("text").value || "";
  } else {
    targetText = ($("text").value || "").trim() || (await translateCurrentText(false)).translated_text;
  }
  const payload = await fetchJson("/api/generate", { method: "POST", body: await getBaseFormDataWithText(targetText) });
  payload.result.source_text = usesTranslatedScript() ? (state.sourceTextZh || "") : ($("text").value || "");
  payload.result.translated_text = usesTranslatedScript() ? (cantoneseMode ? ($("translatedText").value || "") : ($("text").value || "")) : "";
  stopBusyProgress(100, `已生成完成，共 ${payload.result.segments_count || 1} 段。`);
  renderResult(payload.result);
  setStatus(`生成成功，共 ${payload.result.segments_count || 1} 段，当前语速 ${Number($("speechRate").value).toFixed(2)}x。`);
  await saveCurrentHistory();
}

async function regenerateSegment(index) {
  const target = state.currentResult?.segments?.find((item) => Number(item.index) === Number(index));
  if (!target) return;
  const settings = getEffectiveSegmentSettings(target);
  const modifiedFields = buildSegmentModifiedFields(target);
  let targetText = settings.text;
  if (settings.language !== "zh") {
    setStatus(`正在将第 ${index} 段翻译为${getLanguageLabel(settings.language)}……`);
    targetText = await translateArbitraryText(settings.text, settings.language, "auto");
    if (!targetText) {
      throw new Error(`第 ${index} 段自动翻译失败，未得到可用译文。`);
    }
  }
  setStatus(`正在重生成第 ${index} 段……`);
  startBusyProgress(`正在重生成第 ${index} 段`, 18, 88);
  const fd = new FormData();
  fd.append("text", targetText);
  fd.append("index", String(index));
  fd.append("mode", getCurrentMode());
  fd.append("prompt_text", $("promptText").value || "");
  fd.append("instruction", settings.instruction || "");
  fd.append("speed", settings.speed);
  fd.append("text_frontend", "true");
  fd.append("language", settings.language);
  fd.append("scenario", settings.scenario);
  fd.append("style", settings.style || "natural");
  if (settings.language === "zh") {
    fd.append("dialect", settings.dialect);
  }
  fd.append("prompt_language", state.promptLanguage || "");
  const promptAudio = $("promptAudio").files[0] || state.promptAudioFile;
  if (promptAudio) fd.append("prompt_audio", await buildPromptAudioForSubmit());
  const selectedVoiceId = settings.voice_id;
  if (selectedVoiceId) fd.append("voice_id", selectedVoiceId);
  const payload = await fetchJson("/api/regenerate-segment", { method: "POST", body: fd });
  const newSegments = state.currentResult.segments.map((item) => {
    if (Number(item.index) !== Number(index)) return item;
    return normalizeSegment({
      ...payload.segment,
      text: targetText,
      source_text: settings.text,
      original_text: item.original_text || item.text,
      original_audio_url: item.original_audio_url || item.audio_url,
      original_file_name: item.original_file_name || item.file_name,
      original_file_path: item.original_file_path || item.file_path,
      regenerated: true,
      edited: modifiedFields.length > 0,
      modified_fields: modifiedFields,
      edit_text: settings.text,
      edit_speed: target.edit_speed || "",
      edit_voice_id: target.edit_voice_id || "",
      edit_language: target.edit_language || "",
      edit_dialect: target.edit_dialect || "",
      edit_style: target.edit_style || "",
      editor_open: false,
    });
  });
  const rebuilt = await fetchJson("/api/rebuild-output", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ segments: newSegments, build_zip: true }),
  });
  state.currentResult = { ...state.currentResult, file_name: rebuilt.result.filename, audio_url: rebuilt.result.audio_url, zip_url: rebuilt.result.zip_url, zip_filename: rebuilt.result.zip_filename, segments: newSegments, segments_count: rebuilt.result.segments_count };
  stopBusyProgress(100, `第 ${index} 段已重生成并完成整篇拼接。`);
  renderResult(state.currentResult);
  setStatus(`第 ${index} 段已重生成并重新拼接整篇结果。`);
  await saveCurrentHistory();
}

async function restoreOriginalSegment(index) {
  const target = state.currentResult?.segments?.find((item) => Number(item.index) === Number(index));
  if (!target?.original_audio_url) return;
  setStatus(`正在恢复第 ${index} 段的原始生成……`);
  startBusyProgress(`正在恢复第 ${index} 段的原始生成`, 18, 86);
  const restoredSegments = state.currentResult.segments.map((item) => {
    if (Number(item.index) !== Number(index)) return item;
    return normalizeSegment({
      ...item,
      text: item.original_text || item.text,
      audio_url: item.original_audio_url,
      file_name: item.original_file_name || item.file_name,
      file_path: item.original_file_path || item.file_path,
      regenerated: false,
      edited: false,
      modified_fields: [],
      edit_text: item.original_text || item.text,
      edit_speed: "",
      edit_voice_id: "",
      edit_language: "",
      edit_dialect: "",
      edit_style: "",
      editor_open: false,
    });
  });
  const rebuilt = await fetchJson("/api/rebuild-output", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ segments: restoredSegments, build_zip: true }),
  });
  state.currentResult = normalizeResult({
    ...state.currentResult,
    file_name: rebuilt.result.filename,
    audio_url: rebuilt.result.audio_url,
    zip_url: rebuilt.result.zip_url,
    zip_filename: rebuilt.result.zip_filename,
    segments: restoredSegments,
    segments_count: rebuilt.result.segments_count,
  });
  stopBusyProgress(100, `第 ${index} 段已恢复原始生成并完成整篇拼接。`);
  renderResult(state.currentResult);
  setStatus(`第 ${index} 段已恢复原始生成。`);
  await saveCurrentHistory();
}

async function transcribeCurrentReference() {
  const file = $("promptAudio").files[0] || state.promptAudioFile;
  if (!file) {
    setStatus("请先上传参考音频。");
    return;
  }
  const fd = new FormData();
  fd.append("ref_audio", await buildPromptAudioForSubmit());
  setStatus("正在识别参考音频文字……");
  const payload = await fetchJson("/api/transcribe-reference", { method: "POST", body: fd });
  $("promptText").value = payload.text || "";
  state.promptLanguage = payload.language || "";
  if (state.promptBaseSource && !state.promptClipActive) {
    state.promptBaseSource.transcript = payload.text || "";
    state.promptBaseSource.language = state.promptLanguage;
  }
  const languageLabels = { zh: "普通话/中文", yue: "粤语", en: "英文", ja: "日语", ko: "韩语" };
  setStatus(`参考音频识别完成。识别语言：${languageLabels[state.promptLanguage] || state.promptLanguage || "未确定"}`);
}

async function saveVoice() {
  const file = $("promptAudio").files[0] || state.promptAudioFile;
  if (!file) {
    setStatus("请先上传参考音频，再保存到音色库。");
    return;
  }
  const name = $("voiceNameInput").value.trim();
  if (!name) {
    setStatus("请先填写音色名称。");
    return;
  }
  const fd = new FormData();
  fd.append("name", name);
  fd.append("transcript", $("promptText").value || "");
  fd.append("prompt_language", state.promptLanguage || "");
  fd.append("ref_audio", await buildPromptAudioForSubmit());
  const payload = await fetchJson("/api/voices", { method: "POST", body: fd });
  state.voices.unshift(payload.voice);
  renderVoiceSelect(payload.voice.id);
  clearPromptAudioInput();
  $("promptText").value = payload.voice.transcript || $("promptText").value;
  loadPromptWaveFromUrl(payload.voice.audio_url);
  setStatus(`已保存音色：${payload.voice.name}`);
}

async function deleteVoice() {
  const voiceId = $("voiceSelect").value;
  const voice = state.voices.find((item) => item.id === voiceId);
  if (!voice) {
    setStatus("当前选择不是已保存音色，无法删除。");
    return;
  }
  await fetchJson(`/api/voices/${voiceId}`, { method: "DELETE" });
  state.voices = state.voices.filter((item) => item.id !== voiceId);
  renderVoiceSelect("");
  applyVoice("");
  setStatus(`已删除音色：${voice.name}`);
}

async function pinVoice() {
  const voiceId = $("voiceSelect").value;
  if (voiceId.startsWith("preset:")) {
    setStatus("系统预置音色不需要置顶。");
    return;
  }
  const voice = state.voices.find((item) => item.id === voiceId);
  if (!voice) {
    setStatus("请先从音色库选择一个已保存音色。");
    return;
  }
  const payload = await fetchJson(`/api/voices/${voiceId}/pin`, { method: "POST" });
  state.voices = payload.voices || state.voices;
  renderVoiceSelect(voiceId);
  const refreshed = state.voices.find((item) => item.id === voiceId) || payload.voice;
  setStatus(refreshed?.pinned_at ? `已置顶音色：${refreshed.name}` : `已取消置顶：${refreshed?.name || voice.name}`);
  updatePinButtonState();
}

function applyVoice(voiceId) {
  if (!voiceId) {
    clearPromptAudioInput();
    clearPromptWaveAndText();
    updatePinButtonState();
    setStatus("已取消音色选择。");
    return;
  }
  const presetVoice = state.presetVoices.find((item) => item.id === voiceId);
  if (presetVoice) {
    clearPromptAudioInput();
    clearPromptWaveAndText();
    updatePinButtonState();
    setStatus(`已切换到系统预置音色：${presetVoice.label}。该模式不需要上传参考音频。`);
    return;
  }
  const voice = state.voices.find((item) => item.id === voiceId);
  if (!voice) return;
  clearPromptAudioInput();
  setPromptBaseSource({
    kind: "saved",
    voiceId: voice.id,
    url: voice.audio_url,
    transcript: voice.transcript || "",
    language: voice.prompt_language || "",
    name: voice.name || "saved_voice",
  });
  $("promptText").value = voice.transcript || "";
  state.promptSourceUrl = voice.audio_url;
  loadPromptWaveFromUrl(voice.audio_url);
  updatePinButtonState();
  setStatus(`已载入音色：${voice.name}，并已清除当前参考音频文件选择。`);
}

async function saveCurrentHistory() {
  if (!state.currentResult) return;
  const payload = await buildWorkspacePayload();
  await fetchJson("/api/history", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await loadHistory();
}

async function buildWorkspacePayload() {
  const currentResult = state.currentResult || {};
  const voiceId = $("voiceSelect").value || "";
  const selectedPreset = state.presetVoices.find((item) => item.id === voiceId);
  const selectedVoice = state.voices.find((item) => item.id === voiceId);
  let historyPromptAudioUrl = "";
  let historyPromptAudioName = "";
  if (!voiceId && (state.promptAudioFile || state.promptSourceUrl)) {
    try {
      const fd = new FormData();
      fd.append("ref_audio", await buildPromptAudioForSubmit());
      const savedPrompt = await fetchJson("/api/history-reference", { method: "POST", body: fd });
      historyPromptAudioUrl = savedPrompt.audio_url || "";
      historyPromptAudioName = savedPrompt.file_name || "";
      } catch (error) {
        setStatus(`历史任务保存时未能附带参考音频：${error.message || error}`);
      }
    }
  const translatedMode = usesTranslatedScript();
  const sourceText = translatedMode ? (state.sourceTextZh || "") : ($("text").value || "");
  const translatedText = translatedMode ? (isCantoneseMode() ? ($("translatedText").value || "") : ($("text").value || "")) : "";
  return {
      text: sourceText,
      text_preview: sourceText.slice(0, 120),
      translated_text: translatedText,
      translated_preview: translatedText.slice(0, 120),
      language: $("language").value,
        dialect: $("language").value === "zh" ? $("dialect").value : "",
        mode: currentResult.mode || getCurrentMode(),
      speech_rate: Number($("speechRate").value).toFixed(2),
      auto_segment_used: $("autoSegment").checked,
      segment_mode: getSegmentMode(),
      segments_count: currentResult.segments_count || 1,
      audio_url: currentResult.audio_url || "",
      zip_url: currentResult.zip_url || "",
      segments: currentResult.segments || [],
      result_state: "最新结果",
      voice_id: voiceId,
      voice_name: selectedPreset?.label || selectedVoice?.name || "",
      voice_kind: selectedPreset ? "preset" : selectedVoice ? "saved" : "",
    prompt_text: $("promptText").value || "",
    prompt_language: state.promptLanguage || currentResult.prompt_language || "",
    history_prompt_audio_url: historyPromptAudioUrl,
    history_prompt_audio_name: historyPromptAudioName,
    prompt_clip_active: !!state.promptClipActive,
      prompt_clip_start: Number(state.promptClipStart || 0).toFixed(2),
      prompt_clip_end: Number(state.promptClipEnd || 0).toFixed(2),
      instruction: $("instruction").value || "",
      style: $("styleSelect").value || "natural",
    };
}

  function renderHistory(items) {
  if (!items.length) {
    $("historyList").innerHTML = '<div class="history-item"><div class="history-preview">暂无历史任务记录。</div></div>';
    return;
  }
  $("historyList").innerHTML = items.map((item) => `
    <div class="history-item">
      <div class="history-head">
        <span class="history-time">${item.created_at || "--"}</span>
        <span class="history-meta">${getLanguageLabel(item.language || "zh")} / ${item.dialect || "普通"} / ${item.speech_rate || "1.00"}x</span>
      </div>
      <div class="history-preview">${getHistoryPreview(item)}</div>
      ${getHistorySourcePreview(item) ? `<div class="history-source">${getHistorySourcePreview(item)}</div>` : ""}
      <div class="history-actions">
        <button class="secondary history-apply-btn" data-id="${item.id}" type="button">恢复到当前界面</button>
        ${item.audio_url ? `<a class="download-link" href="${item.audio_url}" target="_blank">打开结果音频</a>` : ""}
      </div>
    </div>
  `).join("");
    document.querySelectorAll(".history-apply-btn").forEach((button) => button.addEventListener("click", () => applyHistory(button.dataset.id, items)));
  }

function applyWorkspaceItem(item, sourceLabel = "历史任务") {
  if (!item) return;
  const promptClipRestore = item.voice_id || item.history_prompt_audio_url ? {
    active: !!item.prompt_clip_active,
    start: Number(item.prompt_clip_start || 0),
    end: Number(item.prompt_clip_end || 0),
  } : null;

  state.sourceTextZh = item.text || "";
  $("text").value = (item.language || "zh") === "zh" ? (item.text || "") : (item.translated_text || item.text || "");
  $("language").value = item.language || "zh";
  if (item.dialect) $("dialect").value = item.dialect;
  updateDialectVisibility();
  updateTranslationPanel();
  $("speechRate").value = Number(item.speech_rate || 1).toFixed(2);
  $("autoSegment").checked = !!item.auto_segment_used;
  $("promptText").value = item.prompt_text || "";
  $("instruction").value = item.instruction || "";
  $("styleSelect").value = "natural";
  $("translatedText").value = item.translated_text || "";
  state.translationSignature = getTranslationSignature();
  state.translationEdited = false;
  if (usesTranslatedScript() && (item.translated_text || "").trim()) {
    setTranslationStatus(`已恢复${isCantoneseMode() ? "粤语播报稿" : `${getLanguageLabel($("language").value)}译文`}，可继续人工修改后配音。`);
  }
  if (item.voice_id) {
    state.pendingPromptClipRestore = promptClipRestore;
    renderVoiceSelect(item.voice_id);
    applyVoice(item.voice_id);
  } else if (item.history_prompt_audio_url) {
    renderVoiceSelect("");
    clearPromptAudioInput();
    setPromptBaseSource({
      kind: "history",
      url: item.history_prompt_audio_url,
      transcript: item.prompt_text || "",
      language: item.prompt_language || "",
      name: item.history_prompt_audio_name || "history_reference",
    });
    $("promptText").value = item.prompt_text || "";
    state.promptSourceUrl = item.history_prompt_audio_url;
    loadPromptWaveFromUrl(item.history_prompt_audio_url);
    if (promptClipRestore?.active) {
      state.pendingPromptClipRestore = promptClipRestore;
    }
  } else {
    renderVoiceSelect("");
    clearPromptAudioInput();
  }
  updateRateValue();
  updateCharCount();

  if (item.audio_url) {
    $("downloadLink").href = item.audio_url;
    $("downloadLink").classList.remove("hidden");
  }
  if (item.zip_url) {
    $("downloadZipLink").href = item.zip_url;
    $("downloadZipLink").classList.remove("hidden");
  } else {
    $("downloadZipLink").classList.add("hidden");
  }
  if (item.audio_url) {
    state.currentResult = {
      file_name: item.audio_url.split("/").pop(),
      audio_url: item.audio_url,
      zip_url: item.zip_url,
      segments: item.segments || [],
      segments_count: item.segments_count || (item.segments?.length || 1),
      auto_segment_used: item.auto_segment_used,
      mode: item.mode,
      language: item.language,
      dialect: item.dialect,
      voice_id: item.voice_id,
      voice_name: item.voice_name,
      voice_kind: item.voice_kind,
      control_instruction: item.instruction || "",
      translated_text: item.translated_text || "",
      source_text: item.text || "",
    };
    if (item.segments?.length) {
      renderGeneratedSegments(state.currentResult);
    } else {
      $("toggleSegmentsBtn").disabled = true;
      $("toggleSegmentsBtn").textContent = "查看分段详情";
      state.segmentsExpanded = false;
      $("segmentList").classList.add("hidden");
      $("segmentSummary").textContent = "当前任务未保存分段详情。";
      $("segmentList").innerHTML = "";
    }
    renderResult(state.currentResult);
  } else {
    state.currentResult = null;
    $("resultState").textContent = "等待生成结果";
    $("resultSummary").textContent = "尚未生成可下载内容。";
    $("downloadLink").classList.add("hidden");
    $("downloadZipLink").classList.add("hidden");
    $("toggleSegmentsBtn").disabled = true;
    $("toggleSegmentsBtn").textContent = "查看分段详情";
    state.segmentsExpanded = false;
    $("segmentList").classList.add("hidden");
    $("segmentList").innerHTML = "";
    loadResultWave("");
    updateSegmentSummaryLive();
  }
  setStatus(`已恢复${sourceLabel}：${item.project_name || item.created_at || "--"}`);
}

  function applyHistory(id, items) {
    const item = items.find((entry) => entry.id === id);
    applyWorkspaceItem(item, "历史任务");
  }

  async function loadHistory() {
    const payload = await fetchJson("/api/history");
    renderHistory(payload.items || []);
  }

function toggleSegments() {
  if ($("toggleSegmentsBtn").disabled) return;
  state.segmentsExpanded = !state.segmentsExpanded;
  $("segmentList").classList.toggle("hidden", !state.segmentsExpanded);
  $("toggleSegmentsBtn").textContent = state.segmentsExpanded ? "收起分段详情" : "查看分段详情";
}

  function toggleHistory(expanded = !state.historyExpanded) {
    state.historyExpanded = !!expanded;
    $("historyList").classList.toggle("hidden", !state.historyExpanded);
    $("toggleHistoryBtn").textContent = state.historyExpanded ? "收起历史记录" : "展开历史记录";
  }

function toggleResultSummary(expanded = !state.resultSummaryExpanded) {
  state.resultSummaryExpanded = !!expanded;
  $("resultSummaryPanel").classList.toggle("hidden", !state.resultSummaryExpanded);
  $("toggleResultSummaryBtn").textContent = state.resultSummaryExpanded ? "收起生成结果" : "查看生成结果";
}

function bindEvents() {
    $("text").addEventListener("input", () => {
      updateCharCount();
      if ($("language").value === "zh") {
        state.sourceTextZh = $("text").value || "";
      } else {
        $("translatedText").value = $("text").value || "";
      }
      state.translationEdited = false;
      state.currentResult = null;
    $("toggleSegmentsBtn").disabled = true;
    $("toggleSegmentsBtn").textContent = "查看分段详情";
    state.segmentsExpanded = false;
    $("segmentList").classList.add("hidden");
    $("segmentList").innerHTML = "";
    loadResultWave("");
    updateSegmentSummaryLive();
    scheduleAutoTranslate();
  });
  $("textFile").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    try {
      const fd = new FormData();
      fd.append("file", file);
        const payload = await fetchJson("/api/parse-text-file", { method: "POST", body: fd });
        $("text").value = payload.text || "";
        state.sourceTextZh = payload.text || "";
        updateCharCount();
      state.translationEdited = false;
        state.currentResult = null;
        $("toggleSegmentsBtn").disabled = true;
        $("toggleSegmentsBtn").textContent = "查看分段详情";
        state.segmentsExpanded = false;
        $("segmentList").classList.add("hidden");
        $("segmentList").innerHTML = "";
        loadResultWave("");
        updateSegmentSummaryLive();
        scheduleAutoTranslate();
        setStatus(`已导入文稿文件：${payload.filename || file.name}`);
    } catch (error) {
      setStatus(`导入文稿失败：${error.message}`);
    }
  });
    $("clearTextBtn").addEventListener("click", () => {
      $("text").value = "";
      $("textFile").value = "";
      state.sourceTextZh = "";
      $("translatedText").value = "";
      updateCharCount();
    state.translationEdited = false;
    state.currentResult = null;
    $("toggleSegmentsBtn").disabled = true;
    $("toggleSegmentsBtn").textContent = "查看分段详情";
    state.segmentsExpanded = false;
    $("segmentList").classList.add("hidden");
    $("segmentList").innerHTML = "";
    loadResultWave("");
    updateSegmentSummaryLive();
    scheduleAutoTranslate();
  });
  $("language").addEventListener("change", () => {
      clearTemplateSelectionIfDirty("语种已改动，已退出模板状态。");
      applyLanguageChangeState($("language").value);
  });
  $("translationSettingsBtn").addEventListener("click", async () => {
    try {
      await openTranslationSettings();
    } catch (error) {
      setStatus(`读取翻译设置失败：${error.message}`);
    }
  });
  $("translationSettingsCloseBtn").addEventListener("click", () => $("translationSettingsDialog").close());
  $("translationProvider").addEventListener("change", updateTranslationProviderForm);
  $("translationSettingsSaveBtn").addEventListener("click", async () => {
    try {
      await saveTranslationSettings();
    } catch (error) {
      $("translationSettingsStatus").textContent = `保存失败：${error.message}`;
    }
  });
    $("translationSettingsTestBtn").addEventListener("click", async () => {
    try {
      await testTranslationSettings();
    } catch (error) {
        $("translationSettingsStatus").textContent = `连接测试失败：${error.message}`;
      }
    });
    $("translationSettingsClearBtn").addEventListener("click", async () => {
      try {
        await clearTranslationSettingsCredentials();
      } catch (error) {
        $("translationSettingsStatus").textContent = `清除失败：${error.message}`;
      }
    });
  $("dialect").addEventListener("change", () => {
      clearTemplateSelectionIfDirty("方言已改动，已退出模板状态。");
      state.sourceTextZh = $("text").value || state.sourceTextZh || "";
      updateDialectVisibility();
      state.translationEdited = false;
      updateTranslationPanel();
      scheduleAutoTranslate();
    });
    $("channelTemplateSelect").addEventListener("change", () => applyChannelTemplate($("channelTemplateSelect").value));
    $("saveChannelTemplateBtn").addEventListener("click", async () => { try { await saveCurrentChannelTemplate(); } catch (error) { setStatus(`保存模板失败：${error.message}`); } });
    $("deleteChannelTemplateBtn").addEventListener("click", async () => { try { await deleteCurrentChannelTemplate(); } catch (error) { setStatus(`删除模板失败：${error.message}`); } });
    $("autoSegment").addEventListener("change", () => {
    state.currentResult = null;
    $("toggleSegmentsBtn").disabled = true;
    $("toggleSegmentsBtn").textContent = "查看分段详情";
    state.segmentsExpanded = false;
    $("segmentList").classList.add("hidden");
    $("segmentList").innerHTML = "";
    updateSegmentSummaryLive();
  });
    $("translatedText").addEventListener("input", () => {
      state.translationEdited = true;
    });
    $("refreshTranslationBtn").addEventListener("click", async () => {
      try {
        await translateCurrentText(true);
      } catch (error) {
        setStatus(`播报稿生成失败：${error.message}`);
      }
    });
    $("resultWavePlayBtn").addEventListener("click", () => {
      if (!state.resultWave) return;
      state.resultWave.playPause();
    });
    $("promptWavePlayBtn").addEventListener("click", () => {
      if (!state.promptWave) return;
      state.promptWave.playPause();
    });
    $("promptClipApplyBtn").addEventListener("click", cropPromptAudio);
    $("promptClipResetBtn").addEventListener("click", restorePromptAudio);
    $("speechRate").addEventListener("input", () => {
      clearTemplateSelectionIfDirty("语速已改动，已退出模板状态。");
      updateRateValue();
    });
  document.querySelectorAll(".speed-preset-btn").forEach((button) => button.addEventListener("click", () => {
    $("speechRate").value = button.dataset.rate;
    clearTemplateSelectionIfDirty("语速已改动，已退出模板状态。");
    updateRateValue();
  }));
  $("generateBtn").addEventListener("click", async () => {
    try {
      await generate();
    } catch (error) {
      stopBusyProgress(0, "生成失败。");
      setStatus(`生成失败：${error.message}`);
    }
  });
    $("toggleSegmentsBtn").addEventListener("click", toggleSegments);
    $("toggleResultSummaryBtn").addEventListener("click", () => toggleResultSummary());
    $("toggleHistoryBtn").addEventListener("click", () => toggleHistory());
    $("refreshHistoryBtn").addEventListener("click", loadHistory);
    $("saveHistoryBtn").addEventListener("click", saveCurrentHistory);
    $("refreshPromptTextBtn").addEventListener("click", async () => { try { await transcribeCurrentReference(); } catch (error) { setStatus(`参考音频识别失败：${error.message}`); } });
  $("saveVoiceBtn").addEventListener("click", async () => { try { await saveVoice(); } catch (error) { setStatus(`保存音色失败：${error.message}`); } });
  $("deleteVoiceBtn").addEventListener("click", async () => { try { await deleteVoice(); } catch (error) { setStatus(`删除音色失败：${error.message}`); } });
  $("pinVoiceBtn").addEventListener("click", async () => { try { await pinVoice(); } catch (error) { setStatus(`置顶音色失败：${error.message}`); } });
  $("voiceSelect").addEventListener("change", (event) => {
    clearTemplateSelectionIfDirty("音色已改动，已退出模板状态。");
    applyVoice(event.target.value);
  });
  $("promptAudio").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (file) {
      clearTemplateSelectionIfDirty("参考音频已改动，已退出模板状态。");
      resetVoiceSelection();
      setPromptBaseSource({
        kind: "upload",
        file,
        transcript: "",
        language: "",
        name: file.name || "reference_audio",
      });
      $("promptText").value = "";
      applyPromptAudioFile(file);
      try {
        await transcribeCurrentReference();
        setStatus("已加载参考音频，并已清除当前音色库选择。");
      } catch (error) {
        setStatus(`参考音频识别失败：${error.message}`);
      }
    } else {
      clearTemplateSelectionIfDirty("参考音频已改动，已退出模板状态。");
      clearPromptWaveAndText();
    }
  });
  $("instruction").addEventListener("input", () => clearTemplateSelectionIfDirty("控制指令已改动，已退出模板状态。"));
}

async function boot() {
  initWave();
  resetPromptClipUi();
  bindEvents();
  updateCharCount();
  updateRateValue();
    updateSegmentSummaryLive();
    toggleResultSummary(false);
    state.sourceTextZh = $("text").value || "";
  const status = await fetchJson("/api/status");
    renderFromStatus(status);
    updateTranslationPanel();
    toggleHistory(false);
    setProgress(0, "尚未开始生成。");
    setStatus(status.bundle.available ? "Rainfall 底座已连接，可开始预览分段或生成。" : "Rainfall 底座未连接。");
  }

boot().catch((error) => setStatus(`初始化失败：${error.message}`));
