#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
故事内容处理脚本
处理 ai_studio_bot.py 生成的故事文件，进行以下替换：
1. 将 - 符号替换为空格
2. 将 – 符号（长破折号）替换为空格  
3. 将多个连续空格替换为单个空格
"""

import os
import glob
import argparse
import shutil
from pathlib import Path


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
    import re
    processed_content = re.sub(r' {2,}', ' ', processed_content)
    
    return processed_content


def process_single_file(input_file, output_file):
    """
    处理单个故事文件
    
    Args:
        input_file (str): 输入文件路径
        output_file (str): 输出文件路径
        
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
        
        print(f"✅ 已处理: {os.path.basename(input_file)}")
        return True
        
    except Exception as e:
        print(f"❌ 处理文件 {input_file} 时出错: {e}")
        return False


def get_story_files(input_dir):
    """
    获取输入目录中的所有故事文件
    
    Args:
        input_dir (str): 输入目录路径
        
    Returns:
        list: 故事文件路径列表
    """
    if not os.path.exists(input_dir):
        print(f"❌ 输入目录不存在: {input_dir}")
        return []
    
    # 查找所有 .txt 文件
    pattern = os.path.join(input_dir, "*.txt")
    story_files = glob.glob(pattern)
    
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


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="故事内容处理器 - 符号替换和空格规范化")
    parser.add_argument(
        "--input-dir", 
        default="/mnt/dhl/audio/scifi/full_story/language_code",
        help="输入目录路径 (默认: /mnt/dhl/audio/scifi/full_story/language_code)"
    )
    parser.add_argument(
        "--output-dir",
        default="/mnt/dhl/audio/scifi/full_story_refine",
        help="输出目录路径 (默认: /mnt/dhl/audio/scifi/full_story_refine)"
    )
    parser.add_argument(
        "--file",
        help="处理单个文件（可选，如果指定则只处理该文件）"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="预览模式，只显示会处理哪些文件，不实际处理"
    )
    
    args = parser.parse_args()
    
    input_dir = args.input_dir
    output_dir = args.output_dir
    
    print(f"🎯 故事内容处理器")
    print(f"📁 输入目录: {input_dir}")
    print(f"📁 输出目录: {output_dir}")
    print(f"🔄 处理规则: 1) '-' → 空格  2) '–' → 空格  3) 多空格 → 单空格")
    
    if args.file:
        # 处理单个文件
        input_file = args.file
        if not os.path.exists(input_file):
            print(f"❌ 指定的文件不存在: {input_file}")
            return
        
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
    
    # 处理目录中的所有文件
    story_files = get_story_files(input_dir)
    
    if not story_files:
        print(f"❌ 在目录 {input_dir} 中未找到任何 .txt 文件")
        return
    
    print(f"\n📊 找到 {len(story_files)} 个故事文件")
    
    if args.preview:
        print(f"\n📋 预览模式 - 将要处理的文件:")
        for i, input_file in enumerate(story_files, 1):
            filename = os.path.basename(input_file)
            output_file = os.path.join(output_dir, filename)
            print(f"  {i:2d}. {filename}")
            print(f"      输入: {input_file}")
            print(f"      输出: {output_file}")
        return
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n🔄 开始批量处理...")
    
    successful_count = 0
    failed_count = 0
    
    for i, input_file in enumerate(story_files, 1):
        filename = os.path.basename(input_file)
        output_file = os.path.join(output_dir, filename)
        
        print(f"\n处理第 {i}/{len(story_files)} 个文件: {filename}")
        
        success = process_single_file(input_file, output_file)
        
        if success:
            successful_count += 1
        else:
            failed_count += 1
    
    # 统计结果
    print(f"\n=== 🎉 处理完成 ===")
    print(f"✅ 成功处理: {successful_count} 个文件")
    print(f"❌ 处理失败: {failed_count} 个文件")
    print(f"📊 成功率: {successful_count/(successful_count+failed_count)*100:.1f}%")
    print(f"📁 输出目录: {output_dir}")
    
    if successful_count > 0:
        print(f"\n📝 处理后的文件已保存到: {output_dir}")


if __name__ == "__main__":
    main() 