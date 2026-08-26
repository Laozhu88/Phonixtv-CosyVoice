# AutoDL 快速部署说明

## 生成镜像 tar

如果本地 Windows 没有 Docker Desktop，先把源码 zip 上传到一台支持 Docker 的 Linux 构建机：

```bash
unzip Phonixtv-CosyVoice-Cloud-Official-V1.zip
cd Phonixtv-CosyVoice-Cloud-Official-V1
chmod +x build_docker_image.sh cloud_packaging/*.sh
bash build_docker_image.sh
```

脚本会生成：

```text
release_staging/phoenix-cosyvoice-cloud-v1_latest.tar
```

## 免安装部署

上传两个文件到 AutoDL：

- `Phonixtv-CosyVoice-Cloud-Official-V1.zip`
- `phoenix-cosyvoice-cloud-v1_latest.tar`

执行：

```bash
mkdir -p /root/autodl-tmp/phoenix-cosyvoice
unzip Phonixtv-CosyVoice-Cloud-Official-V1.zip -d /root/autodl-tmp/phoenix-cosyvoice
docker load -i phoenix-cosyvoice-cloud-v1_latest.tar
cd /root/autodl-tmp/phoenix-cosyvoice/Phonixtv-CosyVoice-Cloud-Official-V1
chmod +x start_container.sh cloud_packaging/*.sh
bash start_container.sh
```

看到容器启动后，在 AutoDL 控制台打开自定义服务，端口填写 `6006`。

如需启用自动翻译，启动前设置密钥环境变量：

```bash
export PHOENIX_ALIYUN_ACCESS_KEY_ID="你的 AccessKeyId"
export PHOENIX_ALIYUN_ACCESS_KEY_SECRET="你的 AccessKeySecret"
bash start_container.sh
```

查看日志：

```bash
docker logs -f phoenix-cosyvoice
```

停止服务：

```bash
docker rm -f phoenix-cosyvoice
```

## 重要说明

- 镜像 tar 已包含 Python 环境、依赖、官方 CosyVoice 代码和模型，部署机器不需要再安装 Python 依赖。
- AutoDL 宿主机仍需要提供 NVIDIA 驱动和 Docker GPU 运行能力，这是算力云平台基础能力，不打入业务包。
- 运行数据默认保存在 `/root/autodl-tmp/phoenix-cosyvoice-data`，更新镜像不会清空历史输出。
- 整合包不会内置云服务密钥，翻译服务通过环境变量传入。
