# 使用官方 Python 精简版镜像
FROM python:3.9-slim

WORKDIR /app

# 设置Python环境
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        gcc \
        libc-dev \
        libffi-dev \
        zlib1g-dev \
        libjpeg-dev \
        libgl1-mesa-glx \
        fonts-liberation \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装中文字体支持
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        fonts-wqy-microhei \
        fonts-wqy-zenhei \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY ./requirements.txt /app/requirements.txt

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pandas numpy matplotlib seaborn scikit-learn fastapi uvicorn python-multipart

# 创建沙盒目录
RUN mkdir -p /app/sandboxes

# 复制应用代码
COPY ./app /app/app

# 暴露端口
EXPOSE 8000

# 设置启动命令
# 设置pip源为阿里云
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
RUN pip config set install.trusted-host mirrors.aliyun.com

# 安装必要的依赖和中文字体
RUN apt-get update && \
    apt-get install -y fonts-wqy-microhei && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 创建必要的目录并设置权限
WORKDIR /app
RUN mkdir -p /app/temp /app/data /app/sandboxes /app/logs && \
    chmod -R 777 /app/temp /app/data /app/sandboxes /app/logs && \
    chown -R nobody:nogroup /app/temp /app/data /app/sandboxes /app/logs

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制应用代码
COPY . .

# 设置字体配置
RUN echo "font.sans-serif : WenQuanYi Micro Hei" >> /usr/local/lib/python3.12/site-packages/matplotlib/mpl-data/matplotlibrc

# 设置运行用户
USER nobody

# 启动服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
