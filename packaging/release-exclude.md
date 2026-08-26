# V1 打包排除清单

以下内容不应直接进入 V1 试用包：

## 1. 本地敏感配置

- `config/app.local.json`

说明：

- 该文件可能包含本地翻译密钥或内部配置
- 正式试用包默认只保留 `config/app.example.json`

## 2. 测试输出音频

- `projects/outputs/` 下全部历史测试音频
- `projects/outputs/` 下全部历史分段压缩包

说明：

- 当前目录内已有大量历史测试结果
- 打包时应只保留空目录结构，或仅保留一两个明确的演示样例

## 3. 调试日志

- `logs/phoenix_uvicorn.out.log`
- `logs/phoenix_uvicorn.err.log`

说明：

- 这类日志应在打包前清空或移除

## 4. 设计参考素材

根目录下这些文件属于研发参考，不建议打入正式试用包：

- `*.psd`
- `*.jpg`
- `*.png`

但以下品牌资源如果前端实际使用，应保留：

- `PhoenixTV_LogoA.png`
- `PhoenixTV_LogoB.png`

## 5. 非试用必需目录内容

- `projects/temp/` 下临时文件
- `projects/history/` 下无关测试记录
- `projects/saved_projects/` 下测试项目残留

## 6. 打包建议

不要直接对当前研发目录原地清理后压缩。

建议流程：

1. 先复制一份发布副本
2. 在副本中清理本清单内容
3. 再压缩发布副本

这样不会影响当前开发与测试环境。
