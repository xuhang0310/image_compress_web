"""AI 绘图 API - 文生图/以图生图功能"""
import os
import base64
import logging
import requests
from fastapi import APIRouter, HTTPException, Depends
from api.models import AIGenerateRequest, AIGenerateResponse
from api.deps import get_siliconflow_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI 绘图"])

# 硅基流动 API 配置
SILICONFLOW_API_URL = "https://api.siliconflow.cn/v1/images/generations"

# 支持的尺寸选项
VALID_SIZES = {
    "1024x1024": "1:1 正方形",
    "960x1280": "3:4 纵向",
    "768x1024": "3:4 文档",
    "720x1440": "1:2 超纵向",
    "720x1280": "9:16 全面屏"
}

# 默认模型
DEFAULT_MODEL = "Kwai-Kolors/Kolors"


@router.post("/generate", response_model=AIGenerateResponse)
async def generate_image(
    request: AIGenerateRequest,
    api_key: str = Depends(get_siliconflow_api_key)
):
    """
    文生图/以图生图接口

    使用硅基流动 API 生成图像
    """
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": DEFAULT_MODEL,
            "prompt": request.prompt,
            "size": request.size,
        }

        # 可选参数
        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt

        if request.num_inferences_steps:
            payload["num_inferences_steps"] = request.num_inferences_steps

        if request.guidance_scale:
            payload["guidance_scale"] = request.guidance_scale

        if request.seed is not None:
            payload["seed"] = request.seed

        # 以图生图模式
        if request.image:
            payload["input_image"] = request.image
            if request.strength is not None:
                payload["strength"] = request.strength

        logger.info(f"调用硅基流动 API: prompt={request.prompt[:50]}..., size={request.size}")

        response = requests.post(SILICONFLOW_API_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()

        result = response.json()

        # 解析响应
        if "data" in result and len(result["data"]) > 0:
            image_data = result["data"][0]

            # 检查是 URL 还是 base64
            if "url" in image_data:
                return AIGenerateResponse(
                    success=True,
                    image_url=image_data["url"],
                    error=None
                )
            elif "b64_json" in image_data:
                return AIGenerateResponse(
                    success=True,
                    image_url=f"data:image/png;base64,{image_data['b64_json']}",
                    error=None
                )
            else:
                logger.error(f"API 响应格式异常：{result}")
                raise HTTPException(status_code=500, detail="API 响应格式异常")
        else:
            logger.error(f"API 返回空结果：{result}")
            raise HTTPException(status_code=500, detail="API 返回空结果")

    except requests.exceptions.Timeout:
        logger.error("API 请求超时")
        raise HTTPException(status_code=504, detail="API 请求超时，请重试")
    except requests.exceptions.RequestException as e:
        logger.error(f"API 请求失败：{e}")
        raise HTTPException(status_code=502, detail=f"API 请求失败：{str(e)}")
    except Exception as e:
        logger.error(f"生成图像失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """获取服务状态"""
    api_key = os.getenv("SILICONFLOW_API_KEY")
    return {
        "status": "ok" if api_key else "no_api_key",
        "model": DEFAULT_MODEL,
        "valid_sizes": list(VALID_SIZES.keys())
    }


@router.get("/sizes")
async def get_valid_sizes():
    """获取支持的图片尺寸"""
    return {
        "sizes": VALID_SIZES
    }
