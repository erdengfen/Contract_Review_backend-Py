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
    && rm -rf /var/lib/apt/lists/* \

RUN python3 -m pip install --user poetry -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 复制依赖并安装
#COPY requirements.txt /app/

COPY pyproject.toml /app/

RUN #pip install --upgrade pip setuptools wheel \
#    && pip install --no-cache-dir -r requirements.txt \

RUN poetry install --no-root --no-dev -i https://pypi.tuna.tsinghua.edu.cn/simple/
# 复制项目代码s
COPY . /app

# 暴露端口（FastAPI 默认端口）
EXPOSE 8080

# 启动命令（你的主程序）
COPY . .

CMD ["uvicorn", "main_new:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "8"]
