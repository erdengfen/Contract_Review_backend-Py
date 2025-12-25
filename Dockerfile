# 更完整的基础镜像（含 ping、curl、vim 等常用工具）
FROM python:3.11-slim-bookworm

# 设置工作目录
WORKDIR /app

# 替换 apt 源为清华（解决学校网络问题）
RUN rm -f /etc/apt/sources.list.d/debian.sources && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian bookworm main contrib non-free" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian bookworm-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list

# 安装常用调试工具（ping/curl/telnet/dig/apt-utils/vim）
RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping \
    curl \
    dnsutils \
    telnet \
    net-tools \
    iproute2 \
    vim \
    nano \
    apt-transport-https \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 安装 LibreOffice（你需要的）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-core \
    libreoffice-writer \
    fonts-liberation \
    fonts-dejavu-core \
    fonts-noto-cjk \
    ttf-mscorefonts-installer \
    libxrender1 libfontconfig1 \
    libxt6 libgl1 libsm6 libice6 \
    && rm -rf /var/lib/apt/lists/*

# 安装常用编译依赖（某些 Python 包需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装 poetry
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple poetry

ENV PATH="/root/.local/bin:$PATH"

# 复制 poetry 配置并安装依赖
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root

# 复制项目文件
COPY . .

EXPOSE 8080

CMD ["poetry", "run", "uvicorn", "main_new:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "8"]

