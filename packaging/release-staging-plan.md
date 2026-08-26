# V1 发布副本整理方案

## 1. 原则

不要在当前研发目录直接清理后压缩。

应采用：

1. 复制研发目录
2. 在发布副本中清理
3. 在发布副本中回归检查
4. 对发布副本压缩

这样可以避免误删：

- 测试音频
- 历史任务
- 调试日志
- 本地敏感配置
- 设计草稿

## 2. 推荐副本目录

建议把发布副本放到单独目录，例如：

```text
H:\Codex pj\phoenix_v1_release_staging\
```

副本目录名称建议：

```text
凤凰卫视中文台多语种、多方言智能配音工作台_V1
```

## 3. 复制后第一步清理

### 配置

- 删除 `config/app.local.json`
- 保留 `config/app.example.json`

### 输出与日志

- 清空 `projects/outputs/`
- 清空 `projects/temp/`
- 清空 `projects/history/`
- 清空 `projects/saved_projects/`
- 清空 `logs/phoenix_uvicorn.out.log`
- 清空 `logs/phoenix_uvicorn.err.log`

### 根目录研发素材

删除或不带入以下参考素材：

- `*.psd`
- `*.jpg`
- `*.png`

但前端实际使用的品牌资源应保留：

- `PhoenixTV_LogoA.png`
- `PhoenixTV_LogoB.png`

## 4. 副本内应保留

- `app/`
- `config/`
- `docs/`
- `logs/`
- `models/`
- `packaging/`
- `projects/`
- `scripts/`
- `tools/`
- `README.md`
- `start_phoenix_tts.bat`
- `start_phoenix_tts.ps1`

## 5. 副本内回归建议

至少验证这几项：

1. 双击启动正常
2. 单人配音正常
3. 外语自动翻译正常
4. 中文多方言正常
5. 参考音频识别与剪辑正常
6. 模板保存/套用/删除正常
7. 多角色对话正常
8. 历史任务恢复正常

## 6. 压缩前最终检查

- 没有 `app.local.json`
- 没有无关测试音频
- 没有无关调试日志
- 没有研发草稿图
- 文档齐全
- 启动脚本可运行

## 7. 压缩包命名

建议：

```text
凤凰卫视中文台多语种多方言智能配音工作台_V1_Windows版.zip
```

## 8. 交付建议

先给小范围试用，不要立刻大范围分发。

先收这几类反馈：

- 最常用语种
- 最常用方言
- 常见报错
- 参考音频剪辑习惯
- 模板使用频率
- 多角色实际使用频率
