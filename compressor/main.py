import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径，以便导入模块
sys.path.insert(0, str(Path(__file__).parent))

from args_parser import parse_arguments
from file_scanner import scan_images
from image_compressor import compress_image
from file_manager import create_backup_name, safe_replace_original
from user_interface import display_progress, get_user_confirmation, show_summary

def main():
    """
    主程序入口
    """
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        print(f"目标目录: {args.directory}")
        print(f"目标大小: {args.size}KB")
        print(f"目标格式: {args.format or '保持原格式'}")
        print(f"图片质量: {args.quality}")
        
        # 扫描目录中的图片文件
        print("\n正在扫描图片文件...")
        image_files = scan_images(args.directory)
        
        if not image_files:
            print("指定目录中没有找到支持的图片文件。")
            return
        
        print(f"找到 {len(image_files)} 个图片文件")
        
        # 统计变量
        total_files = len(image_files)
        processed_files = 0
        skipped_files = 0
        
        # 存储需要后续处理的压缩文件路径
        compressed_files = []
        
        # 遍历图片文件进行压缩
        for i, image_path in enumerate(image_files, 1):
            print()  # 换行以清晰显示进度
            display_progress(i, total_files, os.path.basename(image_path))
            
            # 获取原始文件大小
            original_size = os.path.getsize(image_path) // 1024
            
            # 如果原始文件已经小于目标大小，跳过处理
            if original_size <= args.size:
                print(f"\n跳过: {os.path.basename(image_path)} (原大小 {original_size}KB <= 目标大小 {args.size}KB)")
                skipped_files += 1
                continue
            
            # 创建备份文件名（带_compress后缀）
            backup_path = create_backup_name(image_path)
            
            # 压缩图片
            success = compress_image(
                input_path=image_path,
                output_path=backup_path,
                target_size_kb=args.size,
                quality=args.quality,
                target_format=args.format
            )
            
            if success:
                print(f"\n已压缩: {os.path.basename(image_path)} -> {os.path.basename(backup_path)}")
                compressed_files.append(backup_path)
                processed_files += 1
            else:
                print(f"\n压缩失败: {os.path.basename(image_path)}")
                # 如果压缩失败，删除可能创建的不完整文件
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                skipped_files += 1
        
        # 显示处理摘要
        show_summary(total_files, processed_files, skipped_files)
        
        # 如果没有任何文件被成功压缩，直接退出
        if processed_files == 0:
            print("没有文件被成功压缩，程序退出。")
            return
        
        # 询问用户是否要将原图移至备份文件夹并重命名压缩图
        print(f"\n即将执行以下操作:")
        print(f"- 将 {len(compressed_files)} 个原始图片文件移动到备份文件夹")
        print(f"- 将对应的压缩文件重命名为原始文件名")
        print(f"原始文件将被保存在 'backup_originals' 文件夹中，请谨慎确认！")
        
        if get_user_confirmation("确认执行上述操作吗?"):
            print("\n正在执行文件替换操作...")
            successful_replacements = 0
            
            for compress_path in compressed_files:
                if safe_replace_original(compress_path):
                    successful_replacements += 1
            
            print(f"\n文件替换完成！成功处理 {successful_replacements} 个文件")
            print(f"原始文件已保存在 'backup_originals' 文件夹中")
        else:
            print("\n用户取消操作。原始文件保持不变。")
            print("压缩后的文件保留在原位置，文件名带有 '_compress' 后缀。")
    
    except KeyboardInterrupt:
        print("\n\n操作被用户中断。")
    except Exception as e:
        print(f"\n程序执行出错: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()