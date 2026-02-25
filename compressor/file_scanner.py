import os
from pathlib import Path

def scan_images(directory, supported_formats=None):
    """
    扫描指定目录下的所有图片文件
    
    Args:
        directory (str): 目标目录路径
        supported_formats (set): 支持的图片格式集合
        
    Returns:
        list: 图片文件路径列表
    """
    if supported_formats is None:
        supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.gif'}
    
    image_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_ext = Path(file).suffix.lower()
            # 检查文件是否是图片格式，且不包含"_compress"后缀
            if file_ext in supported_formats and not file.endswith('_compress' + file_ext):
                image_files.append(os.path.join(root, file))
    
    return image_files