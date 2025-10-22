# 使用轻量化 Python 基础镜像
FROM python:3.11.13-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量（防止 pyc 缓存、日志输出及时）
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安装系统依赖（aiohttp、pydantic、uvicorn 等可能需要编译支持）
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖并安装
COPY requirements.txt /app/
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . /app

# 暴露端口（FastAPI 默认端口）
EXPOSE 8080

# 启动命令（你的主程序）
COPY . .
CMD ["python","main_new.py"]
