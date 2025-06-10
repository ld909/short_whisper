#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
故事分块脚本
将 process_stories.py 处理后的故事文件分割成3000字符以内的块
每个块保存为单独的文件，格式：/mnt/dhl/audio/scifi/story_chunks/story_index/chunk_index.txt

输入输出路径说明：
默认输入路径：/mnt/dhl/audio/scifi/full_story_refine
    - 包含经过 process_stories.py 处理后的故事文件
    - 文件格式：数字.txt (例如：1.txt, 2.txt, 3.txt...)
    
默认输出路径：/mnt/dhl/audio/scifi/story_chunks
    - 输出目录结构：story_chunks/story_index/chunk_index.txt
    - 例如：story_chunks/1/1.txt, story_chunks/1/2.txt...
    - 每个故事有自己的子目录，按故事索引命名
    - 每个子目录内的文件按块索引命名

使用方法：
    python chunk_stories.py                              # 使用默认路径处理所有文件
    python chunk_stories.py --input-dir /path/to/input   # 指定输入目录
    python chunk_stories.py --output-dir /path/to/output # 指定输出目录
    python chunk_stories.py --file /path/to/file.txt     # 处理单个文件
    python chunk_stories.py --max-chars 2500             # 设置最大字符数
    python chunk_stories.py --preview                    # 预览模式
"""

import os
import glob
import argparse
import re
from pathlib import Path


def split_story_into_chunks(content, max_chars=3000):
    """
    将故事内容分割成指定最大字符数的块，尽量让每个块长度相等
    
    Args:
        content (str): 故事内容
        max_chars (int): 每个块的最大字符数
        
    Returns:
        list: 分割后的文本块列表
    """
    content = content.strip()
    if not content:
        return []
    
    total_chars = len(content)
    
    # 计算需要多少个块
    estimated_chunks = max(1, (total_chars + max_chars - 1) // max_chars)
    
    # 计算理想的每个块大小（除了最后一个）
    ideal_chunk_size = min(max_chars, total_chars // estimated_chunks)
    
    chunks = []
    lines = content.split('\n')
    current_chunk = []
    current_char_count = 0
    
    for line in lines:
        line_with_newline = line + '\n' if line != lines[-1] else line
        line_char_count = len(line_with_newline)
        
        # 检查是否应该开始新的块
        should_start_new_chunk = False
        
        if current_char_count + line_char_count > max_chars:
            # 超过最大限制，必须开始新块
            should_start_new_chunk = True
        elif len(chunks) < estimated_chunks - 1:
            # 还没到最后一个块，检查是否接近理想大小
            if current_char_count + line_char_count >= ideal_chunk_size:
                should_start_new_chunk = True
        
        if should_start_new_chunk and current_chunk:
            # 保存当前块
            chunk_text = '\n'.join(current_chunk).strip()
            if chunk_text:
                chunks.append(chunk_text)
            
            # 开始新的块
            current_chunk = [line]
            current_char_count = len(line)
        else:
            # 继续当前块
            current_chunk.append(line)
            current_char_count += line_char_count
    
    # 处理最后一个块
    if current_chunk:
        chunk_text = '\n'.join(current_chunk).strip()
        if chunk_text:
            chunks.append(chunk_text)
    
    return chunks


def process_single_story(input_file, output_base_dir, max_chars=3000):
    """
    处理单个故事文件，分割成块并保存
    
    Args:
        input_file (str): 输入故事文件路径
        output_base_dir (str): 输出基础目录
        max_chars (int): 每个块的最大字符数
        
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
        chunks = split_story_into_chunks(content, max_chars)
        
        if not chunks:
            print(f"⚠️  无法分割文件: {filename}")
            return False, 0
        
        # 保存每个块并显示每个块的信息
        chunk_sizes = []
        for chunk_index, chunk_content in enumerate(chunks, 1):
            chunk_filename = f"{chunk_index}.txt"
            chunk_filepath = os.path.join(story_output_dir, chunk_filename)
            
            # 去掉换行符，变成一大段话
            chunk_content_no_newlines = chunk_content.replace('\n', ' ').strip()
            
            with open(chunk_filepath, 'w', encoding='utf-8') as f:
                f.write(chunk_content_no_newlines)
            
            chunk_sizes.append(len(chunk_content_no_newlines))
        
        total_chars = len(content)
        avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes)
        chunk_sizes_str = ', '.join([str(size) for size in chunk_sizes])
        
        print(f"✅ {filename}: {len(chunks)} 个块 (总计 {total_chars} 字符)")
        print(f"   块大小: [{chunk_sizes_str}] 字符, 平均: {avg_chunk_size:.0f} 字符")
        
        return True, len(chunks)
        
    except Exception as e:
        print(f"❌ 处理文件 {input_file} 时出错: {e}")
        return False, 0


def get_story_files(input_dir):
    """
    获取输入目录中的所有故事文件
    排除以点开头的Mac系统meta文件
    
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
    all_txt_files = glob.glob(pattern)
    
    # 过滤掉以点开头的文件（Mac系统meta文件）
    story_files = []
    for filepath in all_txt_files:
        basename = os.path.basename(filepath)
        if not basename.startswith('.'):
            story_files.append(filepath)
        else:
            print(f"🚫 跳过Meta文件: {basename}")
    
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
    parser = argparse.ArgumentParser(description="故事分块器 - 将故事分割成指定字符数的块")
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
        "--max-chars",
        type=int,
        default=3000,
        help="每个块的最大字符数 (默认: 3000)"
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
    max_chars = args.max_chars
    
    print(f"🎯 故事分块器")
    print(f"📁 输入目录: {input_dir}")
    print(f"📁 输出目录: {output_dir}")
    print(f"📊 最大字符数: {max_chars} 字符/块")
    
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
        success, chunk_count = process_single_story(input_file, output_dir, max_chars)
        
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
        
        success, chunk_count = process_single_story(input_file, output_dir, max_chars)
        
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