# AI 绘图功能实现总结

## 已完成的功能

### 后端 API

1. **新增文件**: `api/ai_draw.py`
   - 硅基流动 API 集成
   - 文生图/以图生图接口
   - 服务状态查询接口
   - 支持的尺寸查询接口

2. **修改文件**: `api/models.py`
   - 新增 `AIGenerateRequest` 请求模型
   - 新增 `AIGenerateResponse` 响应模型
   - 添加支持的尺寸类型定义

3. **修改文件**: `api/deps.py`
   - 新增 `get_siliconflow_api_key()` 依赖函数

4. **修改文件**: `backend.py`
   - 注册 AI 绘图路由
   - 新增 `/ai` 页面路由

### 前端页面

1. **新增文件**: `frontend/index_ai.html`
   - 文生图模式
   - 以图生图模式
   - 参数设置界面
   - 结果展示界面

2. **新增文件**: `frontend/css/ai-draw.css`
   - AI 绘图专用样式
   - 响应式设计
   - 加载动画
   - 错误提示样式

3. **新增文件**: `frontend/js/modules/ai-draw.js`
   - Tab 切换逻辑
   - 图片上传处理
   - API 调用逻辑
   - 结果下载功能

4. **修改文件**: `frontend/index.html`
   - 添加 AI 绘图入口按钮

### 配置文件

1. **新增文件**: `.env.example`
   - 硅基流动 API Key 配置示例

2. **修改文件**: `requirements.txt`
   - 添加 `requests` 依赖

---

## 使用方式

### 1. 配置 API Key

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑.env 文件，填入你的硅基流动 API Key
# 获取地址：https://cloud.siliconflow.cn/
SILICONFLOW_API_KEY=sk-xxx
```

### 2. 安装依赖

```bash
# 使用 uv (推荐)
uv sync --link-mode copy --extra cpu

# 或使用 pip
pip install -r requirements.txt
```

### 3. 启动服务

```bash
python3 main.py
```

### 4. 访问页面

- **主页**: http://127.0.0.1:8080/
- **AI 绘图**: http://127.0.0.1:8080/ai

---

## API 端点

| 端点 | 方法 | 描述 |
|-----|------|------|
| `/api/ai/generate` | POST | 生成图像（文生图/以图生图） |
| `/api/ai/status` | GET | 查询服务状态 |
| `/api/ai/sizes` | GET | 获取支持的图片尺寸 |

---

## 支持的图片尺寸

| 尺寸 | 比例 | 用途 |
|-----|------|------|
| 1024x1024 | 1:1 | 正方形（默认） |
| 960x1280 | 3:4 | 纵向（社交媒体） |
| 768x1024 | 3:4 | 纵向（文档） |
| 720x1440 | 1:2 | 超纵向（手机壁纸） |
| 720x1280 | 9:16 | 纵向（全面屏） |

---

## 功能参数

### 文生图
- 提示词（必填）
- 反向提示词（可选）
- 图片尺寸（5 种预设）
- 采样步数（1-50，默认 20）
- 引导系数 CFG（1-20，默认 7.5）
- 随机种子（可选，留空表示随机）

### 以图生图
- 上传参考图片
- 重绘强度（0-1，默认 0.75）
- 其他参数同文生图

---

## 验收状态

- [x] 可以在浏览器访问 `/ai` 看到 AI 绘图页面
- [x] 文生图模式：输入提示词 → 点击生成 → 显示结果
- [x] 以图生图模式：上传图片 → 调整参数 → 生成 → 展示结果
- [x] 所有参数可调整并有合理默认值
- [x] 错误处理完善（API 不可用、超时等）
- [x] 响应式设计：移动端可用
- [x] 主页添加 AI 绘图入口

---

## 注意事项

1. **API Key**: 必须设置 `SILICONFLOW_API_KEY` 环境变量才能使用
2. **默认模型**: Kwai-Kolors/Kolors（由硅基流动 API 支持）
3. **超时设置**: API 请求超时时间为 120 秒
4. **图片存储**: 生成的图片通过 URL 或 base64 返回，前端直接下载
