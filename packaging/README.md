# Packaging 说明

本目录用于整理 `凤凰卫视中文台多语种、多方言智能配音工作台 V1` 的 Windows 试用整合包。

当前目标不是安装器，而是 `绿色免安装压缩包`。

## V1 打包原则

- 不改功能代码
- 不引入新依赖
- 不加入半成品功能
- 仅整理可试用、可分发、可回归的稳定内容

## 当前建议结构

```text
packaging/
  README.md
  release-manifest.md
  release-exclude.md
  release-copy-layout.md
  release-staging-plan.md
  scripts/
  templates/
```

## 推荐打包流程

1. 先按 [v1-test-checklist.md](H:\Codex pj\Phonixtv-CosyVoice\工程项目\docs\v1-test-checklist.md) 做回归
2. 按 [v1-package-checklist.md](H:\Codex pj\Phonixtv-CosyVoice\工程项目\docs\v1-package-checklist.md) 清理目录
3. 参考 [release-manifest.md](H:\Codex pj\Phonixtv-CosyVoice\工程项目\packaging\release-manifest.md) 整理试用包内容
4. 按 [release-exclude.md](H:\Codex pj\Phonixtv-CosyVoice\工程项目\packaging\release-exclude.md) 排除不应入包的内容
5. 按 [release-copy-layout.md](H:\Codex pj\Phonixtv-CosyVoice\工程项目\packaging\release-copy-layout.md) 整理副本目录结构
6. 按 [release-staging-plan.md](H:\Codex pj\Phonixtv-CosyVoice\工程项目\packaging\release-staging-plan.md) 整理发布副本
7. 输出 V1 Windows 压缩包

## 当前不建议做

- 安装器
- 在线升级
- 自动更新脚本
- 额外功能开关页

V1 只以稳定试用为目标。
