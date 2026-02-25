import os
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Response
from .models import RenameRequest, CompressionSettings

logger = logging.getLogger(__name__)
router = APIRouter()

def validate_directory_path(directory_path: str) -> bool:
    """验证目录路径是否有效"""
    return os.path.isdir(directory_path)

def get_supported_image_formats() -> set:
    """获取支持的图片格式集合"""
    return {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.gif'}

def scan_image_files_in_directory(directory_path: str) -> list:
    """扫描指定目录中的图片文件"""
    supported_formats = get_supported_image_formats()
    files_info = []
    
    all_items = os.listdir(directory_path)
    
    for file_name in all_items:
        file_path = os.path.join(directory_path, file_name)
        
        # 检查是否是文件（而不是子文件夹）
        if os.path.isfile(file_path):
            file_ext = Path(file_name).suffix.lower()
            
            # 检查文件扩展名是否是支持的图片格式
            if file_ext in supported_formats:
                try:
                    size_kb = os.path.getsize(file_path) // 1024
                    files_info.append({
                        "path": file_path,
                        "name": file_name,
                        "size_kb": size_kb
                    })
                except PermissionError:
                    # 如果无法访问某个文件，跳过它
                    logger.warning(f"Permission denied for file: {file_path}")
                    continue
                except OSError as e:
                    # 如果文件有问题，跳过它
                    logger.warning(f"Error accessing file {file_path}: {e}")
                    continue
    
    return files_info

def ensure_unique_filename(file_path):
    """确保文件名唯一，如果文件已存在则添加序号"""
    path_obj = Path(file_path)
    directory = path_obj.parent
    stem = path_obj.stem
    suffix = path_obj.suffix
    
    counter = 1
    unique_path = file_path
    while os.path.exists(unique_path):
        new_name = f"{stem}({counter}){suffix}"
        unique_path = str(directory / new_name)
        counter += 1
        
    return unique_path

def rename_image_file(original_path, new_name):
    """重命名图片文件，确保新名称不与其他文件冲突"""
    if not os.path.exists(original_path):
        raise FileNotFoundError(f"文件不存在: {original_path}")
    
    # 获取原始文件的目录和扩展名
    original_dir = os.path.dirname(original_path)
    original_ext = os.path.splitext(original_path)[1]
    
    # 确保新名称包含正确的扩展名
    if not new_name.lower().endswith(original_ext.lower()):
        new_name = new_name + original_ext
    
    # 构造新路径 - 使用原始文件的目录，而不是文件路径
    new_path = os.path.join(original_dir, new_name)
    
    # 确保新路径唯一
    unique_new_path = ensure_unique_filename(new_path)
    
    # 重命名文件
    os.rename(original_path, unique_new_path)
    
    return unique_new_path

@router.get("/api/settings")
async def get_settings():
    """获取当前设置"""
    return {
        "default_target_size": 128,
        "default_quality": 85,
        "supported_formats": ["保持原格式", "JPEG", "PNG", "WEBP"]
    }

@router.get("/api/default-path")
async def get_default_path():
    """获取系统默认下载路径"""
    # 获取系统默认下载文件夹路径
    download_path = str(Path.home() / "Downloads")
    return {"default_path": download_path}

@router.get("/api/preview")
async def get_image_preview(file: str):
    """获取图片预览"""
    logger.info(f"请求预览图片: {file}")
    
    # 验证文件路径，防止路径遍历攻击
    if '..' in file or not file.startswith(('C:', '/')):
        logger.warning(f"无效的文件路径: {file}")
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    # 检查文件是否存在
    if not os.path.exists(file):
        logger.error(f"文件不存在: {file}")
        raise HTTPException(status_code=404, detail="File not found")
    
    # 检查文件扩展名是否为图片格式
    valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff']
    if not any(file.lower().endswith(ext) for ext in valid_extensions):
        logger.error(f"文件不是有效的图片格式: {file}")
        raise HTTPException(status_code=400, detail="File is not a valid image")
    
    try:
        # 读取图片文件
        logger.debug(f"尝试读取文件: {file}")
        with open(file, 'rb') as f:
            image_data = f.read()
        
        # 获取文件的MIME类型
        ext = os.path.splitext(file)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.bmp': 'image/bmp',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.tiff': 'image/tiff'
        }
        mime_type = mime_types.get(ext, 'image/jpeg')
        
        logger.info(f"成功返回图片预览: {file}")
        return Response(content=image_data, media_type=mime_type)
    except PermissionError:
        logger.error(f"权限不足，无法访问文件: {file}")
        raise HTTPException(status_code=403, detail="Permission denied to access the file")
    except Exception as e:
        logger.error(f"读取图片时出错 {file}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error reading image: {str(e)}")

@router.post("/api/folder/scan")
async def scan_folder(settings: CompressionSettings):
    """扫描文件夹中的图片文件（非递归）"""
    logger.info(f"开始扫描文件夹: {settings.directory}")
    
    try:
        if not validate_directory_path(settings.directory):
            logger.error(f"指定的路径不是有效的文件夹: {settings.directory}")
            raise HTTPException(status_code=400, detail=f"指定的路径不是有效的文件夹: {settings.directory}")
        
        logger.info(f"支持的图片格式: {get_supported_image_formats()}")
        
        try:
            logger.info(f"文件夹 '{settings.directory}' 开始扫描")
            files_info = scan_image_files_in_directory(settings.directory)
            logger.info(f"扫描完成，找到 {len(files_info)} 个图片文件")
            
        except PermissionError as e:
            logger.error(f"没有权限访问文件夹: {settings.directory}, 错误: {e}")
            raise HTTPException(status_code=403, detail=f"没有权限访问文件夹: {settings.directory}")
        except Exception as e:
            logger.error(f"访问文件夹时出错: {e}")
            raise HTTPException(status_code=500, detail=f"访问文件夹时出错: {str(e)}")
        
        return {
            "folder_path": settings.directory,
            "total_files": len(files_info),
            "files": files_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"扫描文件夹时出错: {e}")
        raise HTTPException(status_code=500, detail=f"扫描文件夹时出错: {str(e)}")

@router.post("/api/rename")
async def rename_file_api(request: RenameRequest):
    """重命名图片文件"""
    try:
        original_path = request.original_path
        new_name = request.new_name
        
        if not os.path.exists(original_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 验证新名称是否为空
        if not new_name or new_name.strip() == "":
            raise HTTPException(status_code=400, detail="新文件名不能为空")
        
        # 验证文件扩展名是否为图片格式
        valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.gif'}
        original_ext = os.path.splitext(original_path)[1].lower()
        new_ext = os.path.splitext(new_name)[1].lower()
        
        # 如果新名称没有扩展名，使用原始扩展名
        if not new_ext:
            new_name = new_name + original_ext
        elif new_ext not in valid_extensions:
            # 如果新扩展名不在允许的图片格式中，使用原始扩展名
            new_name = os.path.splitext(new_name)[0] + original_ext
        
        # 重命名文件
        new_path = rename_image_file(original_path, new_name)
        
        return {
            "success": True,
            "original_path": original_path,
            "new_path": new_path,
            "message": f"文件已成功重命名为: {os.path.basename(new_path)}"
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"重命名文件时出错: {e}")
        raise HTTPException(status_code=500, detail=f"重命名失败: {str(e)}")
