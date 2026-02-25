import os
import shutil
from pathlib import Path

def create_backup_name(original_path):
    """
    为原始文件创建备份名称
    
    Args:
        original_path (str): 原始文件路径
        
    Returns:
        str: 备份文件路径
    """
    path_obj = Path(original_path)
    backup_name = f"{path_obj.stem}_compress{path_obj.suffix}"
    return str(path_obj.parent / backup_name)

def create_backup_folder(base_path):
    """
    创建备份文件夹
    
    Args:
        base_path (str): 基础路径
        
    Returns:
        str: 备份文件夹路径
    """
    backup_folder = os.path.join(os.path.dirname(base_path), "backup_originals")
    os.makedirs(backup_folder, exist_ok=True)
    return backup_folder

def rename_to_original(compress_path):
    """
    将压缩后的文件重命名为原始文件名
    
    Args:
        compress_path (str): 压缩后文件路径（通常带有_compress后缀）
        
    Returns:
        str: 重命名后的文件路径
    """
    path_obj = Path(compress_path)
    original_name = compress_path.replace('_compress', '')
    os.rename(compress_path, original_name)
    return original_name

def move_original_to_backup(original_path):
    """
    将原始文件移动到备份文件夹
    
    Args:
        original_path (str): 原始文件路径
    """
    if os.path.exists(original_path):
        # 创建备份文件夹
        backup_folder = create_backup_folder(original_path)
        
        # 构建备份文件路径
        filename = os.path.basename(original_path)
        backup_path = os.path.join(backup_folder, filename)
        
        # 如果备份路径已存在同名文件，添加序号
        counter = 1
        original_backup_path = backup_path
        while os.path.exists(backup_path):
            name, ext = os.path.splitext(original_backup_path)
            backup_path = f"{name}_{counter}{ext}"
            counter += 1
        
        # 移动文件到备份文件夹
        shutil.move(original_path, backup_path)
        print(f"已将原始文件移动到备份文件夹: {backup_path}")
    else:
        print(f"警告: 原始文件不存在，无法移动: {original_path}")

def safe_replace_original(compress_path):
    """
    安全地替换原始文件，即将原始文件移动到备份文件夹，并将压缩文件重命名为原始文件名
    
    Args:
        compress_path (str): 压缩后文件路径（带_compress后缀）
    """
    # 获取原始文件路径
    original_path = compress_path.replace('_compress', '')
    
    # 检查压缩文件是否存在
    if not os.path.exists(compress_path):
        print(f"错误: 压缩文件不存在: {compress_path}")
        return False
    
    # 检查原始文件是否存在
    if not os.path.exists(original_path):
        print(f"错误: 原始文件不存在: {original_path}")
        return False
    
    # 将原始文件移动到备份文件夹
    move_original_to_backup(original_path)
    
    # 将压缩文件重命名为原始文件名
    final_path = rename_to_original(compress_path)
    print(f"已将压缩文件重命名为原始文件名: {final_path}")
    
    return True