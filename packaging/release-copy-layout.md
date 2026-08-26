# V1 发布副本目录结构方案

## 1. 建议副本根目录

建议先复制出一份独立发布副本，例如：

```text
H:\Codex pj\phoenix_v1_release_staging\
```

再在该目录下整理正式试用包目录：

```text
H:\Codex pj\phoenix_v1_release_staging\凤凰卫视中文台多语种、多方言智能配音工作台_V1\
```

## 2. 建议副本结构

```text
凤凰卫视中文台多语种、多方言智能配音工作台_V1/
  app/
  config/
  docs/
  logs/
  models/
  packaging/
  projects/
    history/
    outputs/
    saved_projects/
    temp/
    voice_library/
  scripts/
  tools/
  README.md
  start_phoenix_tts.bat
  start_phoenix_tts.ps1
```

## 3. 副本中应保留为空目录的部分

这些目录建议保留，但内容清空：

- `logs/`
- `projects/history/`
- `projects/outputs/`
- `projects/saved_projects/`
- `projects/temp/`

保留空目录的原因：

- 工作台首次启动后可直接写入
- 不需要用户手工创建目录
- 目录结构更稳定

## 4. 副本中应保留现有数据的部分

### 必须保留

- `app/`
- `models/`
- `scripts/`
- `tools/`
- `docs/`
- `packaging/`

### 视情况保留

- `projects/voice_library/`

说明：

- 如果 V1 试用包希望内置少量示例音色，可保留一到两个明确可公开试用的音色
- 如果不希望预置任何试用音色，可以仅保留空目录和基础元数据结构

## 5. 配置目录建议

`config/` 建议最终只保留：

- `app.example.json`

如需内部试用版带自动翻译能力，可在内部副本中额外补：

- `app.local.json`

但该文件不建议进入更广泛分发包。

## 6. 根目录建议保留

- `README.md`
- `start_phoenix_tts.bat`
- `start_phoenix_tts.ps1`

不建议在试用包根目录保留大量研发参考图片、草稿和设计源文件。

## 7. 品牌资源建议

如果前端运行仍依赖根目录 Logo 资源，则保留：

- `PhoenixTV_LogoA.png`
- `PhoenixTV_LogoB.png`

如果前端静态资源目录已经自带完整副本，则根目录可不再重复保留。

## 8. 建议压缩前最终形态

压缩前副本应满足：

- 目录完整
- 启动脚本可运行
- 无敏感配置
- 无大量测试音频
- 无无关截图草稿
- 文档齐全

## 9. 当前阶段不建议做

- 再造一个单独安装版目录
- 再拆 `Lite / Pro` 双版本目录
- 在 V1 阶段引入复杂发布脚本

V1 先以单一、清晰、易分发的绿色副本为准。
