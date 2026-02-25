# LaMa API 水印去除使用指南

## 概述

新的 API 模式通过 HTTP 调用本地 lama-cleaner 服务，无需在代码中加载模型，更加稳定可靠。

## 启动服务

### 1. 安装 lama-cleaner

```bash
pip install lama-cleaner
```

### 2. 启动服务

**CPU 模式：**
```bash
lama-cleaner --device cpu --port 8080
```

**GPU 模式：**
```bash
lama-cleaner --device cuda --port 8080
```

**后台运行（Linux/Mac）：**
```bash
nohup lama-cleaner --device cpu --port 8080 > lama.log 2>&1 &
```

### 3. 验证服务

```bash
curl http://127.0.0.1:8080
```

## 使用 API 去除水印

### 方式一：ApiWatermarkRemover（推荐）

```python
from watermark.removal import ApiWatermarkRemover

# 创建去除器（自动连接本地服务）
remover = ApiWatermarkRemover(
    api_url="http://127.0.0.1:8080",
    hd_strategy="Original",  # Original / Resize / Crop
    fallback_to_opencv=True  # 服务不可用时降级到 OpenCV
)

# 从文件去除水印
result = remover.remove_file(
    input_path="/path/to/input.jpg",
    output_path="/path/to/output.jpg",
    bbox=(100, 100, 300, 200),  # 水印区域 (x1, y1, x2, y2)
    mode="normal"  # normal / conservative
)

print(result)
# {
#     'success': True,
#     'input_path': '/path/to/input.jpg',
#     'output_path': '/path/to/output.jpg',
#     'bbox': (100, 100, 300, 200),
#     'mode': 'normal',
#     'processing_time': 2.5,
#     'algorithm': 'LaMa API'
# }
```

### 方式二：直接使用 LamaApiClient

```python
from watermark.removal import LamaApiClient
import cv2
import numpy as np

# 创建客户端
client = LamaApiClient("http://127.0.0.1:8080")

# 检查服务状态
if not client.is_available():
    print("服务未启动！")
    exit(1)

# 读取图片
image = cv2.imread("/path/to/input.jpg")

# 创建掩码（水印区域）
mask = np.zeros((image.shape[0], image.shape[1]), dtype=np.uint8)
mask[100:200, 100:300] = 255  # 水印区域设为 255

# 调用 API
success, result = client.inpaint(
    image=image,
    mask=mask,
    hd_strategy="Original",
    timeout=120
)

if success:
    cv2.imwrite("/path/to/output.jpg", result)
```

## API 参数说明

### hd_strategy 策略

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| `Original` | 使用原图尺寸处理 | 图片较小（< 2048px） |
| `Resize` | 缩放后处理再放大 | 大图（> 2048px） |
| `Crop` | 裁剪水印区域处理 | 超大图或内存有限 |

### 其他参数

```python
success, result = client.inpaint(
    image=image,                    # BGR 图像
    mask=mask,                      # 单通道掩码，255=修复区域
    hd_strategy="Original",         # 处理策略
    hd_strategy_resize_limit=2048,  # Resize 策略的边长限制
    ldm_steps=50,                   # 推理步数（越多越慢效果越好）
    timeout=120                     # 超时时间（秒）
)
```

## 完整示例

```python
import cv2
import numpy as np
from watermark.removal import ApiWatermarkRemover

# 创建去除器
remover = ApiWatermarkRemover()

# 检查服务是否可用
if not remover.service_available:
    print("LaMa 服务未启动，将使用 OpenCV 降级")

# 读取图片
image = cv2.imread("test.jpg")

# 定义水印区域（右下角）
h, w = image.shape[:2]
bbox = (w - 300, h - 100, w - 50, h - 30)

# 去除水印
success, result = remover.remove(image, bbox)

if success:
    cv2.imwrite("output.jpg", result)
    print("水印去除成功！")
else:
    print("水印去除失败！")

# 查看统计
print(remover.get_stats())
```

## 常见问题

### 1. 连接失败

**错误：** `[LaMa API] 连接失败: 请确保服务已启动`

**解决：**
```bash
# 检查服务是否运行
curl http://127.0.0.1:8080

# 重新启动服务
lama-cleaner --device cpu --port 8080
```

### 2. 请求超时

**错误：** `[LaMa API] 请求超时 (120s)`

**解决：**
- 增大 timeout 参数
- 使用 `hd_strategy="Resize"` 处理大图
- 检查系统资源（CPU/GPU 占用）

### 3. 显存不足

**解决：**
```bash
# 使用 CPU 模式
lama-cleaner --device cpu --port 8080

# 或使用 Resize 策略
remover = ApiWatermarkRemover(hd_strategy="Resize")
```

## 与本地模式对比

| 特性 | API 模式 | 本地模式 |
|------|----------|----------|
| 内存占用 | 低（模型在服务中） | 高（模型在进程中） |
| 首次调用 | 快（无需加载模型） | 慢（需要加载模型） |
| 多进程 | 支持 | 需要特殊处理 |
| 稳定性 | 高 | 有兼容性问题 |
| 部署复杂度 | 需启动服务 | 直接导入使用 |

## 推荐用法

**开发/测试：** 使用 API 模式，快速迭代

**生产环境：**
- 单机：启动 lama-cleaner 服务，使用 API 模式
- 分布式：单独部署 lama-cleaner 服务集群

## 服务配置建议

**config.py 配置：**

```python
# 水印去除配置
WATERMARK_REMOVAL = {
    "mode": "api",  # api / local
    "api_url": "http://127.0.0.1:8080",
    "hd_strategy": "Original",
    "fallback_to_opencv": True
}
```

**启动脚本 start.sh：**

```bash
#!/bin/bash

# 启动 lama-cleaner 服务
echo "Starting LaMa service..."
nohup lama-cleaner --device cpu --port 8080 > logs/lama.log 2>&1 &
sleep 5

# 检查服务
curl -s http://127.0.0.1:8080 > /dev/null
if [ $? -eq 0 ]; then
    echo "LaMa service started successfully"
else
    echo "Failed to start LaMa service"
    exit 1
fi

# 启动主应用
echo "Starting main application..."
python run.py
```
