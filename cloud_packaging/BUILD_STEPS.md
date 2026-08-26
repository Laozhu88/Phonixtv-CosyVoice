# 云端整合包制作步骤

## 1. 确认资源齐全

完整云端包必须包含 CosyVoice/Rainfall Linux 资源。脚本默认会从以下位置自动嵌入资源包：

```text
H:\Codex pj\Phonixtv-CosyVoice-AutoDL-V1\cosyvoice-rainfall-linux-resources.zip
```

如果不用资源包，也可以在项目根目录确认存在：

```text
models/CosyVoice3-0.5B
models/SenseVoiceSmall
resources
cosyvoice
third_party/Matcha-TTS
```

如果这些目录为空或不存在，云端包只能启动页面，不能正常生成配音。

## 2. 生成云端整合包

在 Windows PowerShell 中进入项目根目录：

```powershell
cd "H:\Codex pj\Phonixtv-CosyVoice\工程项目"
powershell -ExecutionPolicy Bypass -File ".\cloud_packaging\build_cloud_bundle.ps1"
```

如资源包在其他位置：

```powershell
powershell -ExecutionPolicy Bypass -File ".\cloud_packaging\build_cloud_bundle.ps1" -ResourceZip "D:\path\cosyvoice-rainfall-linux-resources.zip"
```

生成结果：

```text
release_staging\Phonixtv-CosyVoice-Cloud-V1
release_staging\Phonixtv-CosyVoice-Cloud-V1.zip
```

## 3. 生成轻量测试包

如果只想测试云端脚本，不上传大模型资源：

```powershell
powershell -ExecutionPolicy Bypass -File ".\cloud_packaging\build_cloud_bundle.ps1" -SkipLargeResources
```

轻量包不能生成配音，只用于验证页面和启动脚本。

## 4. 上传到 AutoDL

把 `release_staging\Phonixtv-CosyVoice-Cloud-V1.zip` 上传到 AutoDL `/root/autodl-tmp`。

云端执行：

```bash
mkdir -p /root/phoenix-cosyvoice-workbench
unzip /root/autodl-tmp/Phonixtv-CosyVoice-Cloud-V1.zip -d /root/phoenix-cosyvoice-workbench
cd /root/phoenix-cosyvoice-workbench/Phonixtv-CosyVoice-Cloud-V1
chmod +x install_once.sh start_cloud.sh cloud_packaging/*.sh
./install_once.sh
./start_cloud.sh
```

`install_once.sh` 会自动解压内置的 `cosyvoice-rainfall-linux-resources.zip`，无需手工再上传第二个资源包。

## 5. 保存云端镜像

首次安装并测试通过后，在 AutoDL 控制台保存实例为自定义镜像。后续再使用时，只需：

```bash
cd /root/phoenix-cosyvoice-workbench/Phonixtv-CosyVoice-Cloud-V1
./start_cloud.sh
```

## 6. 官方 CosyVoice 底座启动

如果云端已经按官方方式安装并验证：

```text
/root/autodl-tmp/official/CosyVoice-official
/root/autodl-tmp/conda_envs/cosyvoice-official
```

则启动凤凰工作台时使用：

```bash
cd /root/autodl-tmp/phoenix-cosyvoice-workbench/Phonixtv-CosyVoice-Cloud-V1
bash cloud_packaging/start_official_cloud.sh
```
