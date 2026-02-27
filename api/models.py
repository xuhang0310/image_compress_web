from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# 支持的 AI 绘图尺寸选项
VALID_SIZES = Literal["1024x1024", "960x1280", "768x1024", "720x1440", "720x1280"]

class CompressionSettings(BaseModel):
    directory: str
    target_size: int
    quality: int = 85
    format: str = "保持原格式"
    selected_files: List[str] = []

class TaskStatus(BaseModel):
    task_id: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    progress: float
    total_files: int
    processed_files: int
    skipped_files: int
    message: str

class RenameRequest(BaseModel):
    original_path: str
    new_name: str

class WatermarkBatchRequest(BaseModel):
    input_folder: str
    output_folder: str
    skip_low_confidence: bool = True


class AIGenerateRequest(BaseModel):
    """AI 绘图请求模型"""
    prompt: str = Field(..., description="提示词，描述想要生成的图像")
    negative_prompt: str = Field(default="", description="反向提示词，描述不想要的内容")
    size: VALID_SIZES = Field(default="1024x1024", description="图片尺寸")
    num_inferences_steps: int = Field(default=20, ge=1, le=50, description="采样步数")
    guidance_scale: float = Field(default=7.5, ge=1, le=20, description="引导系数 CFG")
    seed: Optional[int] = Field(default=None, description="随机种子，None 表示随机")
    image: Optional[str] = Field(default=None, description="输入图片 base64(以图生图时使用)")
    strength: Optional[float] = Field(default=0.75, ge=0, le=1, description="以图生图的重绘强度")


class AIGenerateResponse(BaseModel):
    """AI 绘图响应模型"""
    success: bool
    image_url: Optional[str] = Field(default=None, description="生成的图片 URL 或 base64")
    error: Optional[str] = Field(default=None, description="错误信息")
