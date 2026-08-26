# V1 打包清单

## 1. 打包前清理

- 删除或替换 `config/app.local.json`
- 清理 `logs/` 下无关调试日志
- 清理 `projects/outputs/` 下无关测试音频
- 清理无关临时文件

## 2. 必带目录

- `app/`
- `config/`
- `docs/`
- `logs/`
- `models/`
- `packaging/`
- `projects/`
- `scripts/`
- `tools/`

## 3. 必带文件

- `README.md`
- `start_phoenix_tts.bat`
- `start_phoenix_tts.ps1`

## 4. 配置要求

- 正式包默认保留 `config/app.example.json`
- 若需要自动翻译能力，内部版本再补正式配置
- 不应把测试密钥、个人账号信息、临时路径写入公开试用包

## 5. 功能回归

- 单人配音正常
- 外语自动翻译正常
- 中文多方言正常
- 参考音频识别正常
- 参考音频剪辑正常
- 保存参考音色正常
- 模板保存/套用/删除正常
- 分段编辑、重生成、恢复正常
- 历史任务恢复正常

## 6. 打包命名建议

- 目录名：
  - `凤凰卫视中文台多语种、多方言智能配音工作台_V1`
- 压缩包名：
  - `凤凰卫视中文台多语种多方言智能配音工作台_V1_Windows版.zip`

## 7. 试用说明随包文档

建议随包保留：

- [README.md](H:\Codex pj\Phonixtv-CosyVoice\工程项目\README.md)
- [v1-user-guide.md](H:\Codex pj\Phonixtv-CosyVoice\工程项目\docs\v1-user-guide.md)
- [v1-test-checklist.md](H:\Codex pj\Phonixtv-CosyVoice\工程项目\docs\v1-test-checklist.md)
- [v1-release-notes.md](H:\Codex pj\Phonixtv-CosyVoice\工程项目\docs\v1-release-notes.md)

## 8. 发布后建议

- 先给小范围编导试用
- 记录高频问题和真实使用场景
- 以反馈为依据再决定 `V1.1` 是否加入：
  - 术语表
  - 发音词典
  - 批量生成
  - 角色模板
