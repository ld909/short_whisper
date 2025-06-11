#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多主题故事内容处理脚本
处理 ai_studio_bot.py 生成的故事文件，进行以下替换：
1. 将 - 符号替换为空格
2. 将 – 符号（长破折号）替换为空格  
3. 将多个连续空格替换为单个空格

📚 支持的主题:
- scifi: 科 
- romance: 爱情故事
- horror: 恐怖故事
- thriller: 惊悚故事
- fantasy: 奇幻故事

📥 输入信息:
- 默认输入目录: /Volumes/dhl/audio/{theme}/full_story/
- 支持文件格式: .txt 文件
- 文件编码: UTF-8
- 文件命名规则: 数字.txt (例如: 1.txt, 2.txt, 3.txt...)

📤 输出信息:
- 默认输出目录: /Volumes/dhl/audio/{theme}/full_story_refine/
- 输出文件格式: .txt 文件
- 输出文件编码: UTF-8
- 文件名保持不变

🔄 处理规则:
1. 将所有 '-' 符号替换为空格
2. 将所有 '–' 符号（长破折号）替换为空格
3. 将多个连续空格压缩为单个空格
4. 保持其他字符不变
5. 自动排除以点开头的Mac系统文件

💡 使用示例:
# 处理所有主题的故事（默认）
python process_stories.py

# 处理指定主题
python process_stories.py --theme scifi
python process_stories.py --theme romance,horror

# 指定自定义根目录
python process_stories.py --base-dir /custom/path

# 处理单个文件
python process_stories.py --file /path/to/story.txt

# 预览模式（不实际处理，只显示会处理哪些文件）
python process_stories.py --preview

# 查看所有支持的主题
python process_stories.py --list-themes

# 查看帮助信息
python process_stories.py --help
"""

import os
import glob
import argparse
import shutil
import re
import platform
from pathlib import Path


def get_default_base_dir():
    """根据操作系统返回合适的音频基础目录"""
    if platform.system() == "Darwin":  # macOS
        return "/Volumes/dhl/audio"
    else:  # Linux 和其他系统
        return "/media/dhl/audio"


# 支持的主题配置
SUPPORTED_THEMES = {
    'scifi': {
        'name': '科幻',
        'description': '科幻故事，包含未来科技、太空探索、时间旅行等元素'
    },
    'romance': {
        'name': '爱情',
        'description': '爱情故事，包含浪漫情节、感情发展等元素'
    },
    'horror': {
        'name': '恐怖',
        'description': '恐怖故事，包含惊悚、悬疑、超自然等元素'
    },
    'thriller': {
        'name': '惊悚',
        'description': '惊悚故事，包含紧张刺激、悬念等元素'
    },
    'fantasy': {
        'name': '奇幻',
        'description': '奇幻故事，包含魔法、龙、精灵等奇幻元素'
    }
}

# 默认基础目录 - 根据操作系统自动选择
DEFAULT_BASE_DIR = get_default_base_dir()


def process_story_content(content):
    """
    处理故事内容，进行多种符号替换
    
    Args:
        content (str): 原始故事内容
        
    Returns:
        str: 处理后的故事内容
    """
    # 将所有的 - 符号替换为空格
    processed_content = content.replace('-', ' ')
    
    # 将所有的 – 符号（长破折号）替换为空格
    processed_content = processed_content.replace('–', ' ')
    
    # 将多个连续空格替换为单个空格
    processed_content = re.sub(r' {2,}', ' ', processed_content)
    
    return processed_content


def get_theme_directories(base_dir, theme):
    """
    获取指定主题的输入和输出目录
    
    Args:
        base_dir (str): 基础目录
        theme (str): 主题名称
        
    Returns:
        tuple: (输入目录, 输出目录)
    """
    input_dir = os.path.join(base_dir, theme, "full_story")
    output_dir = os.path.join(base_dir, theme, "full_story_refine")
    return input_dir, output_dir


def get_story_files(input_dir):
    """
    获取输入目录中的所有故事文件
    
    Args:
        input_dir (str): 输入目录路径
        
    Returns:
        list: 故事文件路径列表
    """
    if not os.path.exists(input_dir):
        return []
    
    # 查找所有 .txt 文件
    pattern = os.path.join(input_dir, "*.txt")
    all_txt_files = glob.glob(pattern)
    
    # 过滤掉以点开头的隐藏文件（如Mac的.DS_Store等meta文件）
    story_files = []
    skipped_files = []
    for file_path in all_txt_files:
        filename = os.path.basename(file_path)
        # 排除以点开头的文件
        if not filename.startswith('.'):
            story_files.append(file_path)
        else:
            skipped_files.append(filename)
    
    if skipped_files:
        print(f"🚫 跳过 {len(skipped_files)} 个Mac系统文件: {', '.join(skipped_files)}")
    
    # 按文件名中的数字排序
    def extract_number(filepath):
        basename = os.path.basename(filepath)
        try:
            # 提取文件名中的数字部分
            number_str = basename.split('.')[0]
            return int(number_str)
        except:
            return 0
    
    story_files.sort(key=extract_number)
    return story_files


def get_processed_files(output_dir):
    """
    获取已处理的文件列表（用于断点续传）
    
    Args:
        output_dir (str): 输出目录路径
        
    Returns:
        set: 已处理的文件名集合
    """
    if not os.path.exists(output_dir):
        return set()
    
    pattern = os.path.join(output_dir, "*.txt")
    processed_files = glob.glob(pattern)
    
    # 只返回文件名，不包含路径
    processed_filenames = set()
    for file_path in processed_files:
        filename = os.path.basename(file_path)
        # 排除以点开头的文件
        if not filename.startswith('.'):
            processed_filenames.add(filename)
    
    return processed_filenames


def process_single_file(input_file, output_file, theme_name=""):
    """
    处理单个故事文件
    
    Args:
        input_file (str): 输入文件路径
        output_file (str): 输出文件路径
        theme_name (str): 主题名称（用于显示）
        
    Returns:
        bool: 处理是否成功
    """
    try:
        # 读取原始文件
        with open(input_file, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # 处理内容
        processed_content = process_story_content(original_content)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 写入处理后的内容
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(processed_content)
        
        filename = os.path.basename(input_file)
        prefix = f"[{theme_name}] " if theme_name else ""
        print(f"✅ {prefix}已处理: {filename}")
        return True
        
    except Exception as e:
        filename = os.path.basename(input_file)
        prefix = f"[{theme_name}] " if theme_name else ""
        print(f"❌ {prefix}处理文件 {filename} 时出错: {e}")
        return False


def process_theme(theme, base_dir, preview_mode=False, resume_mode=True):
    """
    处理指定主题的所有故事文件
    
    Args:
        theme (str): 主题名称
        base_dir (str): 基础目录
        preview_mode (bool): 是否为预览模式
        resume_mode (bool): 是否启用断点续传
        
    Returns:
        dict: 处理结果统计
    """
    theme_name = SUPPORTED_THEMES[theme]['name']
    input_dir, output_dir = get_theme_directories(base_dir, theme)
    
    print(f"\n=== 🎭 处理{theme_name}主题 ({theme}) ===")
    print(f"📁 输入目录: {input_dir}")
    print(f"📁 输出目录: {output_dir}")
    
    # 获取所有故事文件
    story_files = get_story_files(input_dir)
    
    if not story_files:
        print(f"❌ 在目录 {input_dir} 中未找到任何 .txt 文件")
        return {
            'theme': theme,
            'theme_name': theme_name,
            'total': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
    
    print(f"📊 找到 {len(story_files)} 个{theme_name}故事文件")
    
    # 获取已处理的文件（断点续传）
    processed_files = set()
    skipped_count = 0
    
    if resume_mode:
        processed_files = get_processed_files(output_dir)
        if processed_files:
            print(f"🔄 断点续传模式：发现 {len(processed_files)} 个已处理的文件")
    
    # 筛选需要处理的文件
    files_to_process = []
    for input_file in story_files:
        filename = os.path.basename(input_file)
        if resume_mode and filename in processed_files:
            skipped_count += 1
            if not preview_mode:
                print(f"⏭️  跳过已处理文件: {filename}")
        else:
            files_to_process.append(input_file)
    
    if skipped_count > 0:
        print(f"📋 跳过 {skipped_count} 个已处理文件，还需处理 {len(files_to_process)} 个文件")
    
    if not files_to_process:
        print(f"✅ {theme_name}主题的所有文件都已处理完成")
        return {
            'theme': theme,
            'theme_name': theme_name,
            'total': len(story_files),
            'successful': len(story_files) - skipped_count,
            'failed': 0,
            'skipped': skipped_count
        }
    
    if preview_mode:
        print(f"\n📋 预览模式 - {theme_name}主题将要处理的文件:")
        for i, input_file in enumerate(files_to_process, 1):
            filename = os.path.basename(input_file)
            output_file = os.path.join(output_dir, filename)
            print(f"  {i:2d}. {filename}")
            print(f"      输入: {input_file}")
            print(f"      输出: {output_file}")
        return {
            'theme': theme,
            'theme_name': theme_name,
            'total': len(story_files),
            'successful': 0,
            'failed': 0,
            'skipped': skipped_count,
            'preview': len(files_to_process)
        }
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n🔄 开始处理{theme_name}主题的 {len(files_to_process)} 个文件...")
    
    successful_count = 0
    failed_count = 0
    
    for i, input_file in enumerate(files_to_process, 1):
        filename = os.path.basename(input_file)
        output_file = os.path.join(output_dir, filename)
        
        print(f"\n[{theme_name}] 处理第 {i}/{len(files_to_process)} 个文件: {filename}")
        
        success = process_single_file(input_file, output_file, theme_name)
        
        if success:
            successful_count += 1
        else:
            failed_count += 1
    
    # 返回处理结果
    return {
        'theme': theme,
        'theme_name': theme_name,
        'total': len(story_files),
        'successful': successful_count,
        'failed': failed_count,
        'skipped': skipped_count
    }


def list_themes():
    """列出所有支持的主题"""
    print("\n=== 📚 支持的主题列表 ===")
    for theme_id, theme_info in SUPPORTED_THEMES.items():
        print(f"  {theme_id}: {theme_info['name']}")
        print(f"    描述: {theme_info['description']}")
    print()


def validate_themes(theme_list):
    """验证主题列表是否有效"""
    invalid_themes = []
    for theme in theme_list:
        if theme not in SUPPORTED_THEMES:
            invalid_themes.append(theme)
    
    if invalid_themes:
        print(f"❌ 不支持的主题: {', '.join(invalid_themes)}")
        list_themes()
        return False
    
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="多主题故事内容处理器 - 符号替换和空格规范化",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
支持的主题:
  scifi    - 科幻故事
  romance  - 爱情故事
  horror   - 恐怖故事
  thriller - 惊悚故事
  fantasy  - 奇幻故事

使用示例:
  python process_stories.py                    # 处理所有主题
  python process_stories.py --theme scifi     # 处理科幻主题
  python process_stories.py --theme scifi,romance  # 处理多个主题
  python process_stories.py --preview         # 预览模式
  python process_stories.py --no-resume       # 禁用断点续传
        """
    )
    
    parser.add_argument(
        "--theme", "-t",
        help="要处理的主题，用逗号分隔多个主题 (默认: 处理所有主题)"
    )
    parser.add_argument(
        "--base-dir",
        default=DEFAULT_BASE_DIR,
        help=f"基础目录路径 (默认: {DEFAULT_BASE_DIR})"
    )
    parser.add_argument(
        "--file",
        help="处理单个文件（指定此参数时忽略其他参数）"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="预览模式，只显示会处理哪些文件，不实际处理"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="禁用断点续传，重新处理所有文件"
    )
    parser.add_argument(
        "--list-themes",
        action="store_true",
        help="列出所有支持的主题"
    )
    
    args = parser.parse_args()
    
    # 显示支持的主题
    if args.list_themes:
        list_themes()
        return
    
    # 处理单个文件
    if args.file:
        input_file = args.file
        if not os.path.exists(input_file):
            print(f"❌ 指定的文件不存在: {input_file}")
            return
        
        # 使用相同目录作为输出目录
        output_dir = os.path.dirname(input_file)
        filename = os.path.basename(input_file)
        output_file = os.path.join(output_dir, filename)
        
        if args.preview:
            print(f"\n📋 预览模式 - 将要处理的文件:")
            print(f"  输入: {input_file}")
            print(f"  输出: {output_file}")
            return
        
        print(f"\n🔄 开始处理单个文件...")
        success = process_single_file(input_file, output_file)
        
        if success:
            print(f"✅ 文件处理完成!")
        else:
            print(f"❌ 文件处理失败!")
        
        return
    
    # 确定要处理的主题
    if args.theme:
        # 解析用户指定的主题
        theme_list = [theme.strip() for theme in args.theme.split(',')]
        if not validate_themes(theme_list):
            return
    else:
        # 默认处理所有主题
        theme_list = list(SUPPORTED_THEMES.keys())
    
    base_dir = args.base_dir
    resume_mode = not args.no_resume
    
    print(f"🎯 多主题故事内容处理器")
    print(f"📁 基础目录: {base_dir}")
    print(f"🎭 处理主题: {', '.join([SUPPORTED_THEMES[t]['name'] for t in theme_list])}")
    print(f"🔄 处理规则: 1) '-' → 空格  2) '–' → 空格  3) 多空格 → 单空格")
    print(f"📋 断点续传: {'启用' if resume_mode else '禁用'}")
    print(f"🚫 自动排除Mac系统文件 (.DS_Store等)")
    
    if args.preview:
        print(f"👁️  预览模式：只显示将要处理的文件")
    
    # 处理所有主题
    all_results = []
    
    for theme in theme_list:
        try:
            result = process_theme(theme, base_dir, args.preview, resume_mode)
            all_results.append(result)
        except Exception as e:
            theme_name = SUPPORTED_THEMES[theme]['name']
            print(f"❌ 处理{theme_name}主题时出错: {e}")
            import traceback
            traceback.print_exc()
    
    # 统计总结果
    if all_results:
        print(f"\n=== 🎉 处理完成总结 ===")
        
        total_files = sum(r['total'] for r in all_results)
        total_successful = sum(r['successful'] for r in all_results)
        total_failed = sum(r['failed'] for r in all_results)
        total_skipped = sum(r['skipped'] for r in all_results)
        
        if args.preview:
            total_preview = sum(r.get('preview', 0) for r in all_results)
            print(f"📊 预览统计:")
            print(f"  - 发现文件总数: {total_files} 个")
            print(f"  - 需要处理: {total_preview} 个")
            print(f"  - 已处理跳过: {total_skipped} 个")
            
            print(f"\n📋 各主题详情:")
            for result in all_results:
                preview_count = result.get('preview', 0)
                print(f"  - {result['theme_name']}: 发现 {result['total']} 个，需处理 {preview_count} 个，跳过 {result['skipped']} 个")
        else:
            print(f"📊 处理统计:")
            print(f"  - 文件总数: {total_files} 个")
            print(f"  - 成功处理: {total_successful} 个")
            print(f"  - 处理失败: {total_failed} 个")
            print(f"  - 跳过文件: {total_skipped} 个")
            
            if total_files > 0:
                success_rate = (total_successful / (total_successful + total_failed)) * 100 if (total_successful + total_failed) > 0 else 0
                print(f"  - 成功率: {success_rate:.1f}%")
            
            print(f"\n📋 各主题详情:")
            for result in all_results:
                print(f"  - {result['theme_name']}: 成功 {result['successful']} 个，失败 {result['failed']} 个，跳过 {result['skipped']} 个")
            
            if total_successful > 0:
                print(f"\n📝 处理后的文件已保存到各主题的 full_story_refine 目录")


if __name__ == "__main__":
    main() 