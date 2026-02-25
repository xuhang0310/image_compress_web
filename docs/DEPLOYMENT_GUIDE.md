# 图片压缩工具部署指南（国内用户专用）

> 本指南专为没有开发经验的国内用户编写，提供三种部署方式

## 重要提示

### LaMa-cleaner 深度学习模型 Python 版本要求

| 功能 | Python版本 | 说明 |
|------|-----------|------|
| 图片压缩 | 3.8 - 3.13 | 任意版本均可 |
| 基础水印去除 | 3.8 - 3.13 | 使用OpenCV |
| **LaMa去水印** | **3.11 或 3.12** | **PyTorch尚未支持3.13** |

**建议**：统一使用 Python 3.11，兼容性最好。

---

## 方案一：Docker 部署（最简单，推荐）

### 优点
- 一键运行，无需配置环境
- 自动解决依赖问题
- 跨平台支持（Windows/Mac/Linux）

### 前提条件
1. 安装 Docker Desktop
   - Windows/Mac: https://www.docker.com/products/docker-desktop
   - 国内镜像下载：https://docker.mirrors.ustc.edu.cn

### 部署步骤

#### 步骤 1：创建 Dockerfile

在项目根目录创建 `Dockerfile` 文件：

```dockerfile
FROM python:3.11-slim

# 设置国内镜像源加速
RUN echo "deb https://mirrors.aliyun.com/debian/ bookworm main contrib non-free" > /etc/apt/sources.list && \
    echo "deb https://mirrors.aliyun.com/debian/ bookworm-updates main contrib non-free" >> /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . /app/

# 设置 pip 国内镜像
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set install.trusted-host pypi.tuna.tsinghua.edu.cn

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "backend.py"]
```

#### 步骤 2：创建 docker-compose.yml

```yaml
version: '3.8'

services:
  image-tools:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./uploads:/app/uploads
      - ./outputs:/app/outputs
    environment:
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
```

#### 步骤 3：一键启动

**Windows 用户**：
双击运行 `start-docker.bat`：
```bat
@echo off
echo 正在构建 Docker 镜像...
docker-compose build
echo 正在启动服务...
docker-compose up -d
echo 服务已启动，请访问 http://localhost:8000
pause
```

**Mac/Linux 用户**：
```bash
# 在终端中执行
cd image_compress_web
docker-compose up -d
```

#### 步骤 4：访问

浏览器打开：http://localhost:8000

#### 常用命令

```bash
# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 更新代码后重新构建
docker-compose up -d --build
```

---

## 方案二：Windows 宿主机安装

### 前提条件
- Windows 10/11 64位系统
- 磁盘空间：至少 2GB

### 步骤 1：安装 Python 3.11

1. **下载 Python 3.11**
   - 官网：https://www.python.org/downloads/release/python-3119/
   - 国内镜像：https://mirrors.aliyun.com/pypi/simple/python/3.11.9/
   - 下载文件：`python-3.11.9-amd64.exe`

2. **安装 Python**
   - 双击运行安装程序
   - **重要**：勾选 "Add Python to PATH"
   - 点击 "Install Now"
   - 等待安装完成

3. **验证安装**
   - 按 `Win + R`，输入 `cmd`，回车
   - 输入：`python --version`
   - 显示 `Python 3.11.9` 即成功

### 步骤 2：配置 pip 国内镜像

1. 打开命令提示符（CMD）
2. 执行以下命令：

```cmd
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip config set install.trusted-host pypi.tuna.tsinghua.edu.cn
```

### 步骤 3：下载项目代码

**方法一：使用 Git（推荐）**
```cmd
# 安装 Git：https://git-scm.com/download/win
# 然后执行：
git clone https://github.com/yourusername/image_compress_web.git
cd image_compress_web
```

**方法二：直接下载 ZIP**
1. 在浏览器中访问项目页面
2. 点击 "Code" -> "Download ZIP"
3. 解压到桌面，例如 `C:\Users\你的用户名\Desktop\image_compress_web`

### 步骤 4：安装依赖

```cmd
# 进入项目目录
cd C:\Users\你的用户名\Desktop\image_compress_web

# 安装依赖
pip install -r requirements.txt

# 如果安装慢，使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 步骤 5：启动服务

**方法一：双击启动（最简单）**
双击运行 `start.bat` 或 `launch_app.ps1`

**方法二：命令行启动**
```cmd
cd C:\Users\你的用户名\Desktop\image_compress_web
python backend.py
```

### 步骤 6：访问

浏览器打开：http://127.0.0.1:8000

### 常见问题

**问题 1：提示 "python" 不是内部或外部命令**
- 解决：重新安装 Python，勾选 "Add Python to PATH"

**问题 2：pip 安装超时**
- 解决：确保已配置国内镜像，或使用手机热点

**问题 3：端口被占用**
- 解决：关闭占用 8000 端口的程序，或修改 backend.py 中的端口

---

## 方案三：Linux CentOS 安装

### 前提条件
- CentOS 7/8 或 Rocky Linux/AlmaLinux
- root 权限或 sudo 权限

### 步骤 1：安装 Python 3.11

```bash
# 安装依赖
sudo yum groupinstall -y "Development Tools"
sudo yum install -y openssl-devel bzip2-devel libffi-devel zlib-devel

# 下载 Python 3.11
cd /usr/src
sudo wget https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz
# 国内镜像
sudo wget https://mirrors.huaweicloud.com/python/3.11.9/Python-3.11.9.tgz

# 解压并编译
sudo tar xzf Python-3.11.9.tgz
cd Python-3.11.9
sudo ./configure --enable-optimizations
sudo make altinstall

# 验证
python3.11 --version
```

### 步骤 2：配置 pip 国内镜像

```bash
# 创建 pip 配置目录
mkdir -p ~/.pip

# 创建配置文件
cat > ~/.pip/pip.conf << EOF
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF
```

### 步骤 3：安装系统依赖

```bash
# CentOS 7/8
sudo yum install -y \
    mesa-libGL \
    glib2 \
    libSM \
    libXext \
    libXrender \
    libgomp

# 或使用国内镜像源加速
sudo sed -e 's|^mirrorlist=|#mirrorlist=|g' \
         -e 's|^#baseurl=http://mirror.centos.org|baseurl=https://mirrors.aliyun.com|g' \
         -i.bak \
         /etc/yum.repos.d/CentOS-*.repo

sudo yum makecache
sudo yum install -y mesa-libGL glib2 libSM libXext
```

### 步骤 4：下载并部署项目

```bash
# 创建应用目录
sudo mkdir -p /opt/image-tools
cd /opt/image-tools

# 下载代码（使用 git）
sudo yum install -y git
git clone https://github.com/yourusername/image_compress_web.git .

# 或使用 wget 下载 zip
# wget https://github.com/yourusername/image_compress_web/archive/refs/heads/main.zip

# 设置权限
sudo chown -R $USER:$USER /opt/image-tools
```

### 步骤 5：安装 Python 依赖

```bash
cd /opt/image-tools

# 使用 Python 3.11 安装依赖
python3.11 -m pip install -r requirements.txt
```

### 步骤 6：创建系统服务（可选，推荐）

```bash
# 创建服务文件
sudo tee /etc/systemd/system/image-tools.service > /dev/null << EOF
[Unit]
Description=Image Compression Web Tool
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/image-tools
ExecStart=/usr/local/bin/python3.11 backend.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable image-tools
sudo systemctl start image-tools

# 查看状态
sudo systemctl status image-tools

# 查看日志
sudo journalctl -u image-tools -f
```

### 步骤 7：防火墙配置

```bash
# 开放 8000 端口
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload

# 或者关闭防火墙（测试环境）
sudo systemctl stop firewalld
sudo systemctl disable firewalld
```

### 步骤 8：访问

浏览器打开：http://服务器IP:8000

---

## LaMa-cleaner 深度学习安装（可选）

如果需要使用 LaMa 深度学习去水印，需要额外安装：

### Python 版本要求
- **必须使用 Python 3.11 或 3.12**
- Python 3.13 暂不支持（PyTorch 未适配）

### 安装步骤

```bash
# 1. 确认 Python 版本
python --version  # 应显示 3.11.x 或 3.12.x

# 2. 安装 PyTorch（CPU版本）
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 国内镜像加速
pip install torch torchvision -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 安装 LaMa-cleaner
pip install lama-cleaner

# 4. 验证安装
python -c "from lama_inpainting import load_model; print('LaMa 安装成功')"
```

**首次运行会自动下载模型**（约 500MB）：
- 模型将下载到：`~/.cache/lama-cleaner/`
- 或使用命令：`lama-cleaner --device=cpu --port=8080`

---

## 网络问题解决方案

### pip 安装慢/超时

**临时使用国内镜像**：
```bash
pip install 包名 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**永久配置**：
```bash
# Windows
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# Linux/Mac
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << EOF
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF
```

**常用国内镜像**：
- 清华：https://pypi.tuna.tsinghua.edu.cn/simple
- 阿里云：https://mirrors.aliyun.com/pypi/simple/
- 中科大：https://pypi.mirrors.ustc.edu.cn/simple/
- 豆瓣：http://pypi.douban.com/simple/

### Docker 镜像加速

```bash
# 编辑 Docker 配置
# Windows/Mac: Docker Desktop -> Settings -> Docker Engine
# 添加：
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
```

---

## 总结对比

| 方案 | 难度 | 适合人群 | 优点 | 缺点 |
|------|------|---------|------|------|
| Docker | ⭐ 最简单 | 完全零基础 | 一键运行，环境隔离 | 需要安装 Docker |
| Windows | ⭐⭐ 简单 | Windows 用户 | 直接运行，可视化 | 需手动配置 Python |
| CentOS | ⭐⭐⭐ 中等 | 服务器部署 | 稳定，适合长期运行 | 需要 Linux 基础 |

**推荐**：
- 个人使用/快速体验 → **Docker 方案**
- Windows 日常办公 → **Windows 方案**
- 服务器/生产环境 → **CentOS 方案**
