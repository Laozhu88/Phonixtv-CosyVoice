# 凤凰卫视中文台多语种、多方言智能配音工作台

本项目是基于 `CosyVoice / Rainfall` 打造的凤凰卫视中文台专用本地配音工作台。当前正式版本为 `V1.0.0`，本版本功能已经冻结。

定位：
- 独立维护的多语种、中文多方言配音工作台
- 面向凤凰卫视中文台节目生产场景
- 本地化、一键启动、低配置门槛
- 优先保证编导易用性和结果可控性

## V1 已完成能力

- 单人配音：
  - 音色库音色
  - 参考音频配音
  - 自动识别参考音频文字
  - 参考音频波形剪辑
  - 中文自然分段
  - 单段编辑、重生成、恢复原始生成
  - 多语种自动翻译后配音
  - 中文多方言配音
- 资产与配置：
  - 保存参考音色
  - 用户自定义栏目模板 / 频道模板
  - 历史任务恢复
- 结果与审听：
  - 结果波形预览
  - 分段结果回听与下载
  - 播出标准 WAV 下载
  - 分段压缩包下载
  - 粤语生成文字一致性机器预检

## 启动

- 双击 [start_phoenix_tts.bat](start_phoenix_tts.bat)
- 浏览器打开 `http://127.0.0.1:8090`

## 当前 V1 原则

- 不再继续堆叠新功能
- 当前 `V1.0.0` 作为唯一正式基线版本
- 粤语机器预检仅用于发现疑似错漏，正式播出前仍须人工审听
- 根据编导真实使用反馈再规划 `V1.1 / V2`

## 文档

- [V1 使用说明](docs/v1-user-guide.md)
- [V1 测试清单](docs/v1-test-checklist.md)
- [V1 发布说明](docs/v1-release-notes.md)
- [V1 打包清单](docs/v1-package-checklist.md)
- [实施方案](docs/implementation-plan.md)
- [产品需求草案](docs/product-requirements.md)
- [部署打包方案](docs/deployment-bundle.md)
- [打包排除清单](packaging/release-exclude.md)
- [发布副本目录结构方案](packaging/release-copy-layout.md)
- [发布副本整理方案](packaging/release-staging-plan.md)
