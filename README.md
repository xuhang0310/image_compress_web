# Image Compress Web (ICW)

**Image Compress Web** 是一个基于 FastAPI 构建的本地 Web 工具，集成了 **AI 智能去水印**、**图片压缩** 和 **格式转换** 功能。前端采用原生 HTML/CSS/JS 开发，后端基于 PyTorch 和 LaMa 模型，支持 CPU/GPU 加速。


---

## 💡 创作背景

在开发过程中，经常会遇到需要处理图片的场景：**图片压缩**和**水印去除**总是让人头疼不已。每次都得折腾半天，要么找各种在线工具，要么安装复杂的软件，既费时又费力。

而且现在的在线图片压缩工具都只能一张张的压缩，太麻烦了，我平时一弄就三四张图片，网络上也没有这种工具

索性自己动手写一个！既能实现**图片批量压缩**，又能实现**水印去除**功能。

纯属瞎折腾

---

## 📸 效果展示

### 图片压缩效果

| 原图 | 压缩后 |
|------|--------|
| ![压缩前](docs/image_compress.png) | ![压缩后](docs/compress_after.png) |

### 水印去除效果

| 原图 | 去除后 |
|------|--------|
| ![去水印前](docs/watermark.png) | ![去水印后](docs/watermark_after.png) |

---

## 🚀 快速启动

### 方式一：linux 使用 run.sh（推荐）

```bash
# 进入项目目录
cd image_compress_web

# 一键启动（自动管理依赖，后台运行）
./run.sh
```

`run.sh` 会自动：
- 检查并安装 `uv` 工具
- 同步项目依赖
- 后台启动服务
- 日志输出到 `app.log`

### 方式二：Linux/Mac使用 start.sh

```bash

pip install -r requirements.txt
# 默认启动（自动检测设备，端口 8080）
./start.sh

# 指定参数启动
./start.sh --model=lama --device=mps --port=8081
```

### 方式三：直接运行 Python

```bash
cd image_compress_web
python3 main.py
```

启动成功后，浏览器将自动打开 `http://127.0.0.1:8080`。

---

## 📦 安装依赖

```bash
# 建议使用虚拟环境
cd image_compress_web
pip install -r requirements.txt
```

> **注意**：LaMa 模型依赖 PyTorch，如未安装请先执行：
> ```bash
> pip install torch torchvision
> ```

---

## ⚙️ 启动参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--host` | 127.0.0.1 | 服务器监听地址 |
| `--port` | 8080 | 服务器监听端口（被占用时自动递增） |
| `--model` | lama | 图像修复模型名称 |
| `--device` | auto | 推理设备：`cuda` / `mps` (Mac) / `cpu` |
| `--debug` | - | 开启调试模式（代码修改自动重载） |
| `--no-gui` | - | 启动时不自动打开浏览器 |

**示例：**
```bash
# 使用 CPU 运行在 8000 端口
python3 main.py --device=cpu --port=8000

# 开启调试模式，不自动打开浏览器
python3 main.py --debug --no-gui

# 使用 Mac GPU (M1/M2/M3)
python3 main.py --device=mps
```

---

## ✨ 核心功能

### 1. 🎨 AI 智能去水印
- 单图精修模式，支持笔刷涂抹需要去除的区域
- 左右分栏对比视图，实时查看修复效果
- 基于 LaMa 模型，支持大面积遮挡修复
- 自动检测 CUDA / MPS / CPU 设备

### 2. 📉 批量图片压缩
- 智能压缩：设置目标大小（如 500KB），自动调整质量
- 支持 JPG、PNG、WEBP 等格式互转
- 批量处理整个文件夹
- 自动备份原图至 `backup_originals` 目录

### 3. 🛠 技术架构
- **后端**：FastAPI + PyTorch + PIL
- **前端**：原生 HTML/CSS/JS (ES6 Modules)，无打包流程
- **模块化**：清晰的 API 结构，独立的压缩和水印模块

---

## 📁 项目结构

```
image_compress_web/
├── api/                # RESTful API 路由
│   ├── compress.py     # 压缩接口
│   ├── watermark.py    # 去水印接口
│   └── deps.py         # 依赖注入与配置
├── compressor/         # 图片压缩核心模块
├── watermark/          # 水印去除算法
│   └── lama/           # LaMa 模型实现
├── frontend/           # 前端静态资源
├── main.py             # 应用入口
├── backend.py          # FastAPI 应用定义
├── start.sh            # 启动脚本
└── requirements.txt    # 依赖列表
```

---

## 📋 开发计划 (Todo List)

### 水印功能增强
- [ ] 多种水印类型的支持（文字水印、图片水印、平铺水印等）
- [ ] 批量去水印功能
- [ ] 智能检测水印位置（自动识别水印区域）
- [ ] 支持透明水印去除

---

## 🤝 贡献与致谢

- 核心修复算法：[LaMa](https://github.com/advimman/lama)
- 灵感来源：[Lama Cleaner](https://github.com/Sanster/lama-cleaner)

---

**Happy Inpainting!** 🖌️
