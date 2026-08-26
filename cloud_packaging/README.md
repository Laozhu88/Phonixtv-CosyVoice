# 凤凰卫视中文台多语种、多方言 AI 智能配音工作台 V1 云端整合包

本目录用于制作 AutoDL 等 Linux 算力云平台可部署的云端整合包。

交付目标分两层：

- 推荐交付：Docker 镜像 tar。依赖、Python 环境、官方 CosyVoice 源码和模型在镜像构建阶段完成，AutoDL 上不再执行 pip、conda 或 apt 安装。
- 调试交付：源码 zip。用于重新构建镜像或在云端排查问题，仍保留 `install_once.sh`。

## 推荐部署方式：镜像免安装运行

在构建机上执行：

```powershell
cd "H:\Codex pj\Phonixtv-CosyVoice\工程项目"
powershell -ExecutionPolicy Bypass -File cloud_packaging\build_cloud_bundle.ps1 -BuildDockerImage -SaveDockerImage
```

如果 Windows 机器没有 Docker Desktop，也可以先只生成源码 zip，再把 zip 上传到 Linux/Docker 构建机执行：

```bash
unzip Phonixtv-CosyVoice-Cloud-Official-V1.zip
cd Phonixtv-CosyVoice-Cloud-Official-V1
chmod +x build_docker_image.sh cloud_packaging/*.sh
bash build_docker_image.sh
```

产物位于 `release_staging`：

- `Phonixtv-CosyVoice-Cloud-Official-V1.zip`
- `phoenix-cosyvoice-cloud-v1_latest.tar`

上传到 AutoDL 后：

```bash
mkdir -p /root/autodl-tmp/phoenix-cosyvoice
unzip Phonixtv-CosyVoice-Cloud-Official-V1.zip -d /root/autodl-tmp/phoenix-cosyvoice
docker load -i phoenix-cosyvoice-cloud-v1_latest.tar
cd /root/autodl-tmp/phoenix-cosyvoice/Phonixtv-CosyVoice-Cloud-Official-V1
chmod +x start_container.sh cloud_packaging/*.sh
bash start_container.sh
```

启动后在 AutoDL 控制台打开自定义服务端口 `6006`。

自动翻译密钥不打入整合包。需要翻译时，在启动容器前设置：

```bash
export PHOENIX_ALIYUN_ACCESS_KEY_ID="你的 AccessKeyId"
export PHOENIX_ALIYUN_ACCESS_KEY_SECRET="你的 AccessKeySecret"
bash start_container.sh
```

## 源码包调试方式

如果没有提前构建 Docker 镜像，可在 AutoDL 上用源码包执行首次安装：

```bash
cd /root/autodl-tmp/phoenix-cosyvoice/Phonixtv-CosyVoice-Cloud-Official-V1
chmod +x install_once.sh start_cloud.sh cloud_packaging/*.sh
bash install_once.sh
bash start_cloud.sh
```

这种方式会现场安装依赖，只用于调试或制作云平台自定义镜像，不属于最终免安装交付形态。

## GPU 要求

正式生成必须使用 NVIDIA GPU，推荐：

- RTX 4090 / 4090D 24GB
- RTX 3090 24GB
- A5000 24GB
- 至少 16GB 显存的同级显卡

无卡环境只能验证页面和接口，不能作为音质测试依据。

## 运行数据

容器启动脚本默认把运行数据挂载到：

```text
/root/autodl-tmp/phoenix-cosyvoice-data
```

其中包含输出音频、历史记录、音色库和日志。更新镜像时保留该目录即可保留业务数据。
