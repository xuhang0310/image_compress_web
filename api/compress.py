import os
import time
import logging
import sys
from pathlib import Path
from threading import Thread
from fastapi import APIRouter, HTTPException

from .models import CompressionSettings, TaskStatus
from .file_ops import get_supported_image_formats

# 导入现有的图片压缩工具模块
from compressor.image_compressor import compress_image
from compressor.file_manager import create_backup_name, safe_replace_original

logger = logging.getLogger(__name__)
router = APIRouter()

# 存储压缩任务状态
tasks_status = {}

def get_files_for_processing(settings: CompressionSettings) -> list:
    """根据设置获取需要处理的文件列表"""
    if settings.selected_files:
        return settings.selected_files
    else:
        # 扫描当前文件夹（非递归）
        supported_formats = get_supported_image_formats()
        image_files = []
        
        # 遏当前文件夹中的文件
        for file_name in os.listdir(settings.directory):
            file_path = os.path.join(settings.directory, file_name)
            
            # 检查是否是文件（而不是子文件夹）
            if os.path.isfile(file_path):
                file_ext = Path(file_name).suffix.lower()
                
                # 检查文件扩展名是否是支持的图片格式
                if file_ext in supported_formats:
                    image_files.append(file_path)
        
        return image_files

def process_single_image(image_path: str, settings: CompressionSettings) -> tuple[bool, str]:
    """处理单个图片文件"""
    # 创建备份文件名（带_compress后缀）
    backup_path = create_backup_name(image_path)
    
    # 压缩图片
    success = compress_image(
        input_path=image_path,
        output_path=backup_path,
        target_size_kb=settings.target_size,
        quality=settings.quality,
        target_format=settings.format if settings.format != "保持原格式" else None
    )
    
    return success, backup_path

def update_task_progress(task_id: str, current_index: int, total_files: int, file_name: str):
    """更新任务进度"""
    progress = ((current_index + 1) / total_files) * 100
    tasks_status[task_id]["progress"] = progress
    tasks_status[task_id]["message"] = f"正在处理: {file_name}"

def finalize_task(task_id: str, compressed_files: list, processed_count: int):
    """完成任务的最终处理"""
    if processed_count > 0:
        tasks_status[task_id]["message"] = "正在移动原始文件到备份文件夹..."
        
        successful_replacements = 0
        for compress_path in compressed_files:
            if safe_replace_original(compress_path):
                successful_replacements += 1
        
        tasks_status[task_id]["message"] = f"处理完成！成功处理 {successful_replacements} 个文件，原始文件已保存在备份文件夹中"

def run_compression_task(task_id: str, settings: CompressionSettings):
    """在后台线程中执行压缩任务"""
    try:
        # 更新任务状态
        tasks_status[task_id]["status"] = "processing"
        tasks_status[task_id]["message"] = "正在准备压缩任务..."
        
        # 获取要处理的文件列表
        image_files = get_files_for_processing(settings)
        total_files = len(image_files)
        tasks_status[task_id]["total_files"] = total_files
        
        processed_files = 0
        skipped_files = 0
        compressed_files = []
        
        # 遏历图片文件进行压缩
        for i, image_path in enumerate(image_files):
            # 检查文件是否存在
            if not os.path.exists(image_path):
                tasks_status[task_id]["message"] = f"跳过: {os.path.basename(image_path)} (文件不存在)"
                skipped_files += 1
                tasks_status[task_id]["skipped_files"] = skipped_files
                continue
            
            # 检查原始文件大小
            original_size = os.path.getsize(image_path) // 1024
            
            # 如果原始文件已经小于目标大小，跳过处理
            if original_size <= settings.target_size:
                tasks_status[task_id]["message"] = f"跳过: {os.path.basename(image_path)} (原大小 {original_size}KB <= 目标大小 {settings.target_size}KB)"
                skipped_files += 1
                tasks_status[task_id]["skipped_files"] = skipped_files
                continue
            
            # 更新进度
            update_task_progress(task_id, i, total_files, os.path.basename(image_path))
            
            # 处理单个图片
            success, backup_path = process_single_image(image_path, settings)
            
            if success:
                compressed_files.append(backup_path)
                processed_files += 1
                tasks_status[task_id]["processed_files"] = processed_files
            else:
                # 如果压缩失败，删除可能创建的不完整文件
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                processed_files += 1  # 失败也算处理过
                tasks_status[task_id]["processed_files"] = processed_files
        
        # 更新最终状态
        tasks_status[task_id]["status"] = "completed"
        tasks_status[task_id]["message"] = f"压缩完成！共处理 {processed_files} 个文件，跳过 {skipped_files} 个小于目标大小的文件"
        
        # 完成任务的最终处理
        finalize_task(task_id, compressed_files, processed_files)
        
    except Exception as e:
        tasks_status[task_id]["status"] = "failed"
        tasks_status[task_id]["message"] = f"处理失败: {str(e)}"

@router.post("/api/compress")
async def start_compression(settings: CompressionSettings):
    """开始压缩任务"""
    task_id = f"task_{int(time.time())}"
    
    # 初始化任务状态
    tasks_status[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
        "total_files": 0,
        "processed_files": 0,
        "skipped_files": 0,
        "message": "任务初始化中"
    }
    
    # 在后台线程中执行压缩任务
    thread = Thread(target=run_compression_task, args=(task_id, settings))
    thread.start()
    
    return {"task_id": task_id}

@router.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in tasks_status:
        raise HTTPException(status_code=404, detail="任务不存在")

    return tasks_status[task_id]
