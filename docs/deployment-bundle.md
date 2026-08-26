# Windows 一键部署整合包方案

## 1. 当前目标

当前版本按 `V1 绿色免安装整合包` 准备，不做安装器。

目标是：

1. 员工拿到压缩包
2. 解压到本地目录
3. 双击 [start_phoenix_tts.bat](H:\Codex pj\Phonixtv-CosyVoice\工程项目\start_phoenix_tts.bat)
4. 浏览器自动或手动打开 `http://127.0.0.1:8090`
5. 直接开始使用

## 2. V1 整合包必须包含

- `app/`
- `config/`
- `docs/`
- `logs/`
- `models/`
- `projects/`
- `scripts/`
- `tools/`
- `start_phoenix_tts.bat`
- `start_phoenix_tts.ps1`

说明：

- `config/app.local.json` 不应打入正式对外包
- 试用包内应只保留 `config/app.example.json`
- 若需内部分发带翻译能力版本，再单独注入正式密钥配置

## 3. 推荐目录结构

```text
凤凰卫视中文台多语种、多方言智能配音工作台_V1/
  app/
  config/
  docs/
  logs/
  models/
  packaging/
  projects/
  scripts/
  tools/
  start_phoenix_tts.bat
  start_phoenix_tts.ps1
  README.md
```

## 4. 打包方式

建议固定为 `绿色压缩包`：

- 不做安装器
- 不改注册表
- 不强依赖管理员权限
- 便于栏目组直接拷贝和试用

建议压缩包命名：

- `凤凰卫视中文台多语种多方言智能配音工作台_V1_Windows版.zip`

## 5. 发布前检查

- 启动脚本双击可正常运行
- 默认端口 `8090` 可正常启动
- 单人配音可生成
- 参考音频识别、波形、剪辑正常
- 模板保存/套用/删除正常
- 历史任务恢复正常
- 自动翻译链正常
- `config/app.local.json` 已排除或替换为安全版本
- `logs/` 和 `projects/outputs/` 无无关测试垃圾文件

## 6. 建议分发版本

### 内部试用版

- 保留调试日志
- 保留示例音色与示例历史
- 供编导试用和提反馈

### 对外正式试用版

- 清空敏感配置
- 清空无关日志
- 清空历史测试结果
- 仅保留必要示例资源

## 7. 当前不建议加入

- 安装器
- 在线升级
- 自动模型热更新
- 额外功能开关页

V1 先以稳定分发和低学习成本为先。
