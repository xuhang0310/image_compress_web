from typing import List, Optional
from pydantic import BaseModel
from fastapi import UploadFile

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
