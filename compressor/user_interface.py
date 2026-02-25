def display_progress(current, total, file_name):
    """
    显示处理进度
    
    Args:
        current (int): 当前处理数量
        total (int): 总数量
        file_name (str): 当前处理的文件名
    """
    percentage = (current / total) * 100
    print(f"\r处理进度: {current}/{total} ({percentage:.1f}%) - 正在处理: {file_name}", end='', flush=True)


def get_user_confirmation(action_desc):
    """
    获取用户确认
    
    Args:
        action_desc (str): 操作描述
        
    Returns:
        bool: 用户是否确认
    """
    while True:
        response = input(f"\n{action_desc} (y/n): ").strip().lower()
        if response in ['y', 'yes', '是']:
            return True
        elif response in ['n', 'no', '否']:
            return False
        else:
            print("请输入 y(是) 或 n(否)")


def show_summary(total_files, processed_files, skipped_files):
    """
    显示处理摘要
    
    Args:
        total_files (int): 总文件数
        processed_files (int): 已处理文件数
        skipped_files (int): 已跳过文件数
    """
    print(f"\n\n处理完成!")
    print(f"总文件数: {total_files}")
    print(f"已处理: {processed_files}")
    print(f"已跳过: {skipped_files}")
    print(f"成功率: {processed_files/total_files*100:.1f}%")