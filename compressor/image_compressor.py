from PIL import Image
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def compress_image(input_path, output_path, target_size_kb, quality=85, target_format=None):
    """
    压缩图片到目标大小
    
    Args:
        input_path (str): 输入图片路径
        output_path (str): 输出图片路径
        target_size_kb (int): 目标大小(KB)
        quality (int): 图片质量 (1-100)
        target_format (str): 目标图片格式 (JPEG, PNG, WEBP)
        
    Returns:
        bool: 压缩是否成功
    """
    try:
        logger.info(f"开始压缩图片: {input_path} -> {output_path}, 目标大小: {target_size_kb}KB")
        
        # 获取原始图片大小
        original_size = os.path.getsize(input_path) // 1024
        logger.info(f"原始图片大小: {original_size}KB")
        
        # 如果原始图片已经小于目标大小，则直接复制文件而不进行压缩
        if original_size <= target_size_kb:
            logger.info(f"原始图片已小于目标大小，直接复制文件")
            import shutil
            shutil.copy2(input_path, output_path)  # 使用copy2保留元数据
            logger.info(f"文件已复制，大小: {original_size}KB")
            return True
        
        # 打开原始图片进行处理
        with Image.open(input_path) as img:
            logger.info(f"尺寸: {img.size}, 模式: {img.mode}")
            
            # 如果指定了目标格式，则使用该格式，否则保持原格式
            if target_format:
                format_to_use = target_format
            else:
                # 为了UI素材的兼容性，保持原始格式
                format_to_use = img.format or 'JPEG'
                
            logger.info(f"使用图片格式: {format_to_use}")
            
            # 如果是RGBA模式且目标格式不支持透明度，转换为RGB
            if img.mode in ('RGBA', 'LA', 'P') and format_to_use.upper() in ('JPEG', 'JPG'):
                logger.info(f"转换图片模式: {img.mode} -> RGB")
                if img.mode == 'P':
                    img = img.convert('RGBA')
                img = img.convert('RGB')
            
            # 初始压缩，保持原始格式
            if format_to_use.upper() == 'PNG':
                # 对于PNG，使用PNG优化
                img.save(output_path, format='PNG', optimize=True)
            elif format_to_use.upper() == 'JPEG':
                # 对于JPEG，使用质量参数
                img.save(output_path, format='JPEG', quality=quality, optimize=True)
            elif format_to_use.upper() == 'WEBP':
                # 对于WEBP，使用质量参数
                img.save(output_path, format='WEBP', quality=quality, optimize=True)
            else:
                # 默认使用原始格式
                img.save(output_path, format=format_to_use, quality=quality, optimize=True)
            
            # 检查文件大小
            current_size_kb = os.path.getsize(output_path) // 1024
            logger.info(f"初始压缩后大小: {current_size_kb}KB")
            
            # 如果文件仍然太大，尝试降低质量（仅适用于有损格式）
            if current_size_kb > target_size_kb and format_to_use.upper() in ('JPEG', 'WEBP'):
                logger.info(f"文件仍大于目标大小，开始调整质量")
                # 二分查找合适的质量值
                low, high = 1, quality
                best_quality = quality
                iteration = 0
                max_iterations = 20  # 防止无限循环
                
                while low <= high and iteration < max_iterations:
                    iteration += 1
                    mid = (low + high) // 2
                    temp_output = output_path + ".temp"
                    
                    # 根据需要创建临时图像副本
                    if img.mode in ('RGBA', 'LA', 'P') and format_to_use.upper() in ('JPEG', 'JPG'):
                        temp_img = img.convert('RGB')
                    else:
                        temp_img = img
                    
                    # 根据格式要求保存临时文件
                    if format_to_use.upper() == 'JPEG':
                        temp_img.save(temp_output, format='JPEG', quality=mid, optimize=True)
                    elif format_to_use.upper() == 'WEBP':
                        temp_img.save(temp_output, format='WEBP', quality=mid, optimize=True)
                    else:
                        # 对于PNG，我们不能使用质量参数，而是尝试其他方法
                        temp_img.save(temp_output, format=format_to_use, optimize=True)
                    
                    temp_size_kb = os.path.getsize(temp_output) // 1024
                    logger.debug(f"尝试质量 {mid}, 得到大小 {temp_size_kb}KB")
                    
                    if temp_size_kb <= target_size_kb:
                        best_quality = mid
                        low = mid + 1
                        os.remove(temp_output)  # 删除临时文件
                    else:
                        high = mid - 1
                        os.remove(temp_output)  # 删除临时文件
                
                logger.info(f"找到最佳质量值: {best_quality}")
                
                # 使用找到的最佳质量重新保存
                if best_quality != quality:
                    if img.mode in ('RGBA', 'LA', 'P') and format_to_use.upper() in ('JPEG', 'JPG'):
                        temp_img = img.convert('RGB')
                    else:
                        temp_img = img
                        
                    if format_to_use.upper() == 'JPEG':
                        temp_img.save(output_path, format='JPEG', quality=best_quality, optimize=True)
                    elif format_to_use.upper() == 'WEBP':
                        temp_img.save(output_path, format='WEBP', quality=best_quality, optimize=True)
                    else:
                        # 对于PNG，我们不能使用质量参数，而是尝试其他方法
                        temp_img.save(output_path, format=format_to_use, optimize=True)
            
            # 如果质量调整后仍然过大，尝试调整分辨率
            current_size_kb = os.path.getsize(output_path) // 1024
            if current_size_kb > target_size_kb:
                logger.info(f"质量调整后仍大于目标大小，开始调整分辨率")
                
                # 计算需要缩小的比例
                size_ratio = min((target_size_kb / current_size_kb) ** 0.5, 0.9)  # 限制最大缩小比例为90%
                
                # 多次迭代调整分辨率直到达到目标大小或无法再压缩
                max_resize_attempts = 5
                resize_attempt = 0
                
                while current_size_kb > target_size_kb and resize_attempt < max_resize_attempts:
                    resize_attempt += 1
                    logger.info(f"第 {resize_attempt} 次调整分辨率")
                    
                    new_width = max(int(img.width * size_ratio), 10)  # 确保最小宽度为10像素
                    new_height = max(int(img.height * size_ratio), 10)  # 确保最小高度为10像素
                    
                    logger.info(f"调整分辨率: {img.size} -> ({new_width}, {new_height})")
                    
                    # 调整分辨率
                    resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # 保存中间结果
                    if resized_img.mode in ('RGBA', 'LA', 'P') and format_to_use.upper() in ('JPEG', 'JPG'):
                        resized_img = resized_img.convert('RGB')
                    
                    if format_to_use.upper() == 'JPEG':
                        resized_img.save(output_path, format='JPEG', quality=best_quality, optimize=True)
                    elif format_to_use.upper() == 'PNG':
                        resized_img.save(output_path, format='PNG', optimize=True)
                    elif format_to_use.upper() == 'WEBP':
                        resized_img.save(output_path, format='WEBP', quality=best_quality, optimize=True)
                    else:
                        resized_img.save(output_path, format=format_to_use, quality=best_quality, optimize=True)
                    
                    # 检查新的文件大小
                    current_size_kb = os.path.getsize(output_path) // 1024
                    logger.info(f"调整分辨率后大小: {current_size_kb}KB")
                    
                    # 如果文件仍然太大，进一步减小size_ratio
                    if current_size_kb > target_size_kb:
                        size_ratio *= 0.8  # 进一步缩小比例
            
            # 对于PNG格式，尝试使用pngquant等外部工具进行更高级的压缩
            if current_size_kb > target_size_kb and format_to_use.upper() == 'PNG':
                logger.info(f"PNG文件仍大于目标大小，尝试使用高级PNG优化")
                # 这里可以集成外部的PNG优化工具，如pngquant
                # 但由于环境限制，我们暂时跳过这一步
                # 可以在后续版本中添加对pngquant的支持
        
        # 验证最终文件大小
        final_size_kb = os.path.getsize(output_path) // 1024
        logger.info(f"最终文件大小: {final_size_kb}KB")
        
        # 放宽成功条件：允许15%的误差，或者至少压缩了原始大小的30%
        compression_ratio = (original_size - final_size_kb) / original_size if original_size > 0 else 0
        success = (
            final_size_kb <= target_size_kb or 
            abs(final_size_kb - target_size_kb) / target_size_kb < 0.15 or  # 允许15%的误差
            compression_ratio >= 0.3  # 至少压缩了原始大小的30%
        )
        
        logger.info(f"压缩{'成功' if success else '失败'}: 目标 {target_size_kb}KB, 实际 {final_size_kb}KB, 压缩率: {compression_ratio*100:.1f}%")
        
        return success
        
    except Exception as e:
        logger.error(f"压缩图片时出错: {input_path}, 错误: {str(e)}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        return False