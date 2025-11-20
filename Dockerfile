# CabbageEditor AI 服务端 Dockerfile
# 基于 Python 3.12 slim 镜像
FROM python:3.12-slim

LABEL maintainer="CabbageEditor Team"
LABEL description="CabbageEditor AI Service - 提供 LLM、图像生成、视频生成等 AI 能力"

# ==================== 1. 配置镜像源（腾讯云） ====================
ENV PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple

RUN set -eux; \
    . /etc/os-release; \
    # 兼容传统 sources.list
    if [ -f /etc/apt/sources.list ]; then \
        sed -i 's|http://deb.debian.org|https://mirrors.cloud.tencent.com|g; \
                s|https://deb.debian.org|https://mirrors.cloud.tencent.com|g; \
                s|http://security.debian.org|https://mirrors.cloud.tencent.com|g; \
                s|https://security.debian.org|https://mirrors.cloud.tencent.com|g' \
                /etc/apt/sources.list; \
    fi; \
    # 兼容 deb822 格式（Debian 12+）
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's|deb.debian.org|mirrors.cloud.tencent.com|g; \
                s|security.debian.org|mirrors.cloud.tencent.com|g' \
                /etc/apt/sources.list.d/debian.sources; \
    else \
        printf 'Types: deb\nURIs: https://mirrors.cloud.tencent.com/debian/\nSuites: %s %s-updates %s-security\nComponents: main contrib non-free non-free-firmware\n' \
            "$VERSION_CODENAME" "$VERSION_CODENAME" "$VERSION_CODENAME" \
            > /etc/apt/sources.list.d/debian.sources; \
    fi

# ==================== 2. 安装系统依赖 ====================
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 编译依赖
    gcc \
    g++ \
    # 图像处理依赖（Pillow）
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    # OpenCV 依赖
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    # 清理缓存
    && rm -rf /var/lib/apt/lists/*

# ==================== 3. 设置工作目录 ====================
WORKDIR /app

# ==================== 4. 安装 Python 依赖 ====================
# 先复制 requirements.txt（利用 Docker 缓存）
COPY requirements.txt ./

# 创建服务端专用的精简依赖文件（排除 GUI 相关）
RUN grep -v -E "^PySide6|^PyQt" requirements.txt > requirements.server.txt || true

# 安装依赖
RUN pip install --no-cache-dir -r requirements.server.txt && \
    pip install --no-cache-dir gunicorn

# ==================== 5. 复制项目文件 ====================
# 复制配置文件
COPY config/ ./config/

# 复制 Backend 模块（AI 服务核心）
COPY Backend/artificial_intelligence/ ./Backend/artificial_intelligence/
COPY Backend/utils/ ./Backend/utils/
COPY Backend/engine_core/ ./Backend/engine_core/
COPY Backend/network_service/ ./Backend/network_service/
COPY Backend/__init__.py ./Backend/

# 复制主入口文件
COPY main.py ./

# 创建自动保存目录
RUN mkdir -p autosave

# ==================== 6. 环境变量配置 ====================
# 应用模式：服务端
ENV APP_MODE=server

# 服务器配置
ENV SERVER_HOST=0.0.0.0
ENV SERVER_PORT=20100

# 公网 IP（用于生成图片 URL，根据实际情况修改）
ENV PUBLIC_IP=175.24.227.58

# Python 配置
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ==================== 7. 健康检查 ====================
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:20100/healthz', timeout=5)" || exit 1

# ==================== 8. 暴露端口 ====================
EXPOSE 20100

# ==================== 9. 启动服务 ====================
# 生产环境推荐使用 Gunicorn
CMD ["gunicorn", \
     "--bind", "0.0.0.0:20100", \
     "--workers", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "Backend.network_service.server:app"]

# 或者使用 Python 直接启动（开发/测试）
CMD ["python", "main.py"]
