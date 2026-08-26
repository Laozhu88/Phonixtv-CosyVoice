ARG CUDA_BASE_IMAGE=nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04
FROM ${CUDA_BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive
ENV PHOENIX_HOST=0.0.0.0
ENV PHOENIX_PORT=6006
ENV PHOENIX_CONDA_ENV=/opt/conda/envs/phoenix-cosyvoice
ENV PHOENIX_OFFICIAL_COSYVOICE_ROOT=/opt/phoenix/official/CosyVoice
ENV PHOENIX_OFFICIAL_MODEL_DIR=/opt/phoenix/official/CosyVoice/pretrained_models/Fun-CosyVoice3-0.5B
ARG UBUNTU_APT_MIRROR=http://mirrors.aliyun.com/ubuntu

RUN sed -i "s#http://archive.ubuntu.com/ubuntu#${UBUNTU_APT_MIRROR}#g; s#http://security.ubuntu.com/ubuntu#${UBUNTU_APT_MIRROR}#g" /etc/apt/sources.list \
  && apt-get -o Acquire::Retries=5 update \
  && apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
    bash \
    build-essential \
    ca-certificates \
    curl \
    ffmpeg \
    git \
    libgl1 \
    libglib2.0-0 \
    unzip \
    wget \
  && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o /tmp/miniconda.sh \
  && bash /tmp/miniconda.sh -b -p /opt/conda \
  && rm /tmp/miniconda.sh

ENV PATH=/opt/conda/bin:/opt/conda/envs/phoenix-cosyvoice/bin:$PATH

WORKDIR /workspace/phoenix-cosyvoice

COPY cloud_packaging/install_once.sh /workspace/phoenix-cosyvoice/cloud_packaging/install_once.sh
COPY cloud_packaging/requirements-cloud.txt /workspace/phoenix-cosyvoice/cloud_packaging/requirements-cloud.txt

RUN bash cloud_packaging/install_once.sh

COPY . /workspace/phoenix-cosyvoice

EXPOSE 6006
CMD ["bash", "cloud_packaging/start_cloud.sh"]
