import argparse
import os

def parse_arguments():
    """
    解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数对象
    """
    parser = argparse.ArgumentParser(
        description='批量压缩指定目录下的图片到目标大小',
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        '-d', '--directory',
        required=True,
        type=str,
        help='目标目录路径'
    )
    
    parser.add_argument(
        '-s', '--size',
        required=True,
        type=int,
        help='目标压缩大小(KB)'
    )
    
    parser.add_argument(
        '-f', '--format',
        type=str,
        default=None,
        choices=['JPEG', 'PNG', 'WEBP'],
        help='目标图片格式 (默认: 保持原格式)'
    )
    
    parser.add_argument(
        '-q', '--quality',
        type=int,
        default=85,
        choices=range(1, 101),
        metavar='[1-100]',
        help='图片质量 (1-100)，数值越高质量越好，默认85'
    )
    
    args = parser.parse_args()
    
    # 验证目录是否存在
    if not os.path.isdir(args.directory):
        raise ValueError(f"目录不存在: {args.directory}")
    
    # 验证目标大小是否有效
    if args.size <= 0:
        raise ValueError("目标大小必须大于0KB")
    
    return args