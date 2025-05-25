#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
故事分块脚本
将 process_stories.py 处理后的故事文件分割成400词以上的块
每个块保存为单独的文件，格式：/mnt/dhl/audio/scifi/story_chunks/story_index/chunk_index.txt
"""

import os
import glob
import argparse
import re
from pathlib import Path


def count_words(text):
    """
    计算文本中的单词数量
    
    Args:
        text (str): 输入文本
        
    Returns:
        int: 单词数量
    """
    # 使用正则表达式分割单词，包括中文字符
    words = re.findall(r'\b\w+\b|[\u4e00-\u9fff]', text)
    return len(words)


def split_story_into_chunks(content, min_words=400):
    """
    将故事内容分割成指定最小单词数的块
    
    Args:
        content (str): 故事内容
        min_words (int): 每个块的最小单词数
        
    Returns:
        list: 分割后的文本块列表
    """
    chunks = []
    lines = content.split('\n')
    current_chunk = []
    current_word_count = 0
    
    for line in lines:
        line_word_count = count_words(line)
        
        # 如果当前块加上这一行还没达到最小单词数，继续添加
        if current_word_count + line_word_count < min_words:
            current_chunk.append(line)
            current_word_count += line_word_count
        else:
            # 达到最小单词数，添加这一行后结束当前块
            current_chunk.append(line)
            current_word_count += line_word_count
            
            # 保存当前块
            chunk_text = '\n'.join(current_chunk).strip()
            if chunk_text:  # 确保块不为空
                chunks.append(chunk_text)
            
            # 开始新的块
            current_chunk = []
            current_word_count = 0
    
    # 处理最后一个块
    if current_chunk:
        chunk_text = '\n'.join(current_chunk).strip()
        if chunk_text:
            chunks.append(chunk_text)
    
    return chunks


def process_single_story(input_file, output_base_dir, min_words=400):
    """
    处理单个故事文件，分割成块并保存
    
    Args:
        input_file (str): 输入故事文件路径
        output_base_dir (str): 输出基础目录
        min_words (int): 每个块的最小单词数
        
    Returns:
        tuple: (成功标志, 块数量)
    """
    try:
        # 读取故事文件
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            print(f"⚠️  文件为空: {os.path.basename(input_file)}")
            return False, 0
        
        # 从文件名提取故事索引
        filename = os.path.basename(input_file)
        story_index = filename.split('.')[0]  # 假设文件名格式为 "数字.txt"
        
        # 创建故事专用目录
        story_output_dir = os.path.join(output_base_dir, story_index)
        os.makedirs(story_output_dir, exist_ok=True)
        
        # 分割故事
        chunks = split_story_into_chunks(content, min_words)
        
        if not chunks:
            print(f"⚠️  无法分割文件: {filename}")
            return False, 0
        
        # 保存每个块
        for chunk_index, chunk_content in enumerate(chunks, 1):
            chunk_filename = f"{chunk_index}.txt"
            chunk_filepath = os.path.join(story_output_dir, chunk_filename)
            
            with open(chunk_filepath, 'w', encoding='utf-8') as f:
                f.write(chunk_content)
        
        word_count = count_words(content)
        print(f"✅ {filename}: {len(chunks)} 个块 (总计 {word_count} 词)")
        
        return True, len(chunks)
        
    except Exception as e:
        print(f"❌ 处理文件 {input_file} 时出错: {e}")
        return False, 0


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
    parser = argparse.ArgumentParser(description="故事分块器 - 将故事分割成指定单词数的块")
    parser.add_argument(
        "--input-dir", 
        default="/mnt/dhl/audio/scifi/full_story_refine",
        help="输入目录路径 (默认: /mnt/dhl/audio/scifi/full_story_refine)"
    )
    parser.add_argument(
        "--output-dir",
        default="/mnt/dhl/audio/scifi/story_chunks",
        help="输出目录路径 (默认: /mnt/dhl/audio/scifi/story_chunks)"
    )
    parser.add_argument(
        "--min-words",
        type=int,
        default=400,
        help="每个块的最小单词数 (默认: 400)"
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
    min_words = args.min_words
    
    print(f"🎯 故事分块器")
    print(f"📁 输入目录: {input_dir}")
    print(f"📁 输出目录: {output_dir}")
    print(f"📊 最小单词数: {min_words} 词/块")
    
    if args.file:
        # 处理单个文件
        input_file = args.file
        if not os.path.exists(input_file):
            print(f"❌ 指定的文件不存在: {input_file}")
            return
        
        if args.preview:
            print(f"\n📋 预览模式 - 将要处理的文件:")
            print(f"  输入: {input_file}")
            filename = os.path.basename(input_file)
            story_index = filename.split('.')[0]
            story_output_dir = os.path.join(output_dir, story_index)
            print(f"  输出目录: {story_output_dir}")
            return
        
        print(f"\n🔄 开始处理单个文件...")
        success, chunk_count = process_single_story(input_file, output_dir, min_words)
        
        if success:
            print(f"✅ 文件处理完成! 生成了 {chunk_count} 个块")
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
            story_index = filename.split('.')[0]
            story_output_dir = os.path.join(output_dir, story_index)
            print(f"  {i:2d}. {filename}")
            print(f"      输入: {input_file}")
            print(f"      输出目录: {story_output_dir}")
        return
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n🔄 开始批量处理...")
    
    successful_count = 0
    failed_count = 0
    total_chunks = 0
    
    for i, input_file in enumerate(story_files, 1):
        filename = os.path.basename(input_file)
        
        print(f"\n处理第 {i}/{len(story_files)} 个文件: {filename}")
        
        success, chunk_count = process_single_story(input_file, output_dir, min_words)
        
        if success:
            successful_count += 1
            total_chunks += chunk_count
        else:
            failed_count += 1
    
    # 统计结果
    print(f"\n=== 🎉 处理完成 ===")
    print(f"✅ 成功处理: {successful_count} 个故事文件")
    print(f"❌ 处理失败: {failed_count} 个故事文件")
    print(f"📊 总共生成: {total_chunks} 个文本块")
    print(f"📊 成功率: {successful_count/(successful_count+failed_count)*100:.1f}%")
    print(f"📁 输出目录: {output_dir}")
    
    if successful_count > 0:
        print(f"\n📝 分块后的文件已保存到: {output_dir}")
        print(f"📁 目录结构: story_chunks/story_index/chunk_index.txt")


if __name__ == "__main__":
    main() 