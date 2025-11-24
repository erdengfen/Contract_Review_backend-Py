# 使用轻量化 Python 基础镜像
FROM docker.xuanyuan.run/library/python:3.11.14
# 设置工作目录
WORKDIR /app

# 设置 Debian 镜像源（bookworm）

# 先删除可能存在的 deb822 源文件
RUN rm -f /etc/apt/sources.list.d/debian.sources

# 再写入传统的 sources.list（使用清华源）
RUN set -eux; \
    CODENAME="$(grep -oP 'VERSION_CODENAME=\K\w+' /etc/os-release || echo bookworm)"; \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian $CODENAME main contrib non-free" > /etc/apt/sources.list; \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian $CODENAME-updates main contrib non-free" >> /etc/apt/sources.list; \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security $CODENAME-security main contrib non-free" >> /etc/apt/sources.list


# 安装 LibreOffice
RUN apt-get update && \
    apt-get install -y --no-install-recommends  \
    libreoffice-core  \
    libreoffice-writer  \
    fonts-liberation  \
    fonts-dejavu-core  \
    fonts-noto-cjk  \
    ttf-mscorefonts-installer  \
    libxrender1 libfontconfig1  \
    libxt6 libgl1 libsm6 libice6 && \
    rm -rf /var/lib/apt/lists/*

# 设置环境变量（防止 pyc 缓存、日志输出及时）
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

#安装系统依赖（aiohttp、pydantic、uvicorn 等可能需要编译支持）
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    git \
    && rm -rf /var/lib/apt/lists/* \


WORKDIR /app


RUN python3 -m pip install --user poetry -i https://pypi.tuna.tsinghua.edu.cn/simple/ && \
    export PATH="/root/.local/bin:$PATH"


ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml ./
RUN poetry install --no-root

COPY . .

EXPOSE 8080

CMD ["poetry", "run", "uvicorn", "main_new:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "8"]
