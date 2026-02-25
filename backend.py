import os
import argparse
import warnings
import logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Filter out the specific warning from torch.amp.autocast_mode
warnings.filterwarnings("ignore", message="User provided device_type of 'cuda', but CUDA is not available")

# Import routers and deps
from api.file_ops import router as file_ops_router
from api.compress import router as compress_router
from api.watermark import router as watermark_router
from api.deps import set_lama_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="图片压缩工具网页版", version="1.0.0")

# 添加CORS中间件，允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应指定具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(file_ops_router)
app.include_router(compress_router)
app.include_router(watermark_router)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """返回主页HTML"""
    frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
    if os.path.exists(frontend_path):
        with open(frontend_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<h1>图片压缩工具网页版</h1><p>前端文件未找到</p>")

# 挂载静态文件
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
app.mount("/js", StaticFiles(directory=os.path.join(static_dir, "js")), name="js")
app.mount("/css", StaticFiles(directory=os.path.join(static_dir, "css")), name="css")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Image Compress & Watermark Removal Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8080, type=int)
    parser.add_argument("--model", default="lama", help="Model name")
    parser.add_argument("--device", default=None, help="Device to use (cuda, mps, cpu)")
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    # Update global config for Lama
    set_lama_config(args.model, args.device)

    uvicorn.run(app, host=args.host, port=args.port)
