#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍音频文件一致性检查脚本
检查 synthesize_book_audio.py 生成的 MP3 文件和输入文本块文件的数量是否一致
支持多语言处理，自动排除Mac系统点文件

📊 功能说明:
- 检查每个UUID书籍的输入txt文件和输出mp3文件数量是否一致
- 识别缺失的音频文件或多余的音频文件
- 支持英文(en)和中文(zh)两种语言
- 自动排除Mac系统产生的点文件（.DS_Store、._*等）
- 提供详细的统计报告和修复建议

📥 输入路径结构:
- 输入目录: /home/dhl/Documents/book/{lang}/{uuid}/{chunk_index}.txt
- 输出目录: 
  * 中文: /home/dhl/Documents/audio/mp3_clips/book/book_zh/{uuid}/{chunk_index}.mp3
  * 英文: /home/dhl/Documents/audio/mp3_clips/book/book_en/{uuid}/{chunk_index}.mp3

💡 使用示例:
# 检查英文书籍
python check_audio_chunks_consistency.py --lang en

# 检查中文书籍
python check_audio_chunks_consistency.py --lang zh

# 检查指定UUID的书籍
python check_audio_chunks_consistency.py --lang en --uuid 12345678-abcd-efgh-ijkl-123456789012

# 详细模式（显示每个文件）
python check_audio_chunks_consistency.py --lang zh --verbose

# 修复模式（删除多余的音频文件）
python check_audio_chunks_consistency.py --lang en --fix-orphaned
"""

import os
import glob
import argparse
import platform
from pathlib import Path
from collections import defaultdict


def get_paths_for_language(lang="en"):
    """根据语言获取输入和输出路径"""
    # 输入目录：chunk_book_summaries.py的输出目录
    input_dir = f"/home/dhl/Documents/book/{lang}"
    
    # 输出目录：synthesize_book_audio.py的输出目录
    if lang == "zh":
        output_dir = "/home/dhl/Documents/audio/mp3_clips/book/book_zh"
    else:  # lang == "en"
        output_dir = "/home/dhl/Documents/audio/mp3_clips/book/book_en"
    
    return input_dir, output_dir


def is_mac_system_file(filename):
    """
    检查是否为Mac系统产生的文件
    
    Args:
        filename (str): 文件名
        
    Returns:
        bool: 是否为系统文件
    """
    if filename.startswith('.'):
        return True
    if filename.startswith('._'):
        return True
    if filename == '.DS_Store':
        return True
    if filename == '.localized':
        return True
    return False


def get_chunk_files_in_directory(directory_path, uuid):
    """
    获取指定目录中的所有文本块文件，排除Mac系统文件
    
    Args:
        directory_path (str): 目录路径
        uuid (str): 书籍UUID
        
    Returns:
        dict: {chunk_index: file_path}
    """
    if not os.path.exists(directory_path):
        return {}
    
    chunk_files = {}
    skipped_files = []
    
    try:
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            
            # 跳过目录
            if os.path.isdir(file_path):
                continue
                
            # 跳过Mac系统文件
            if is_mac_system_file(filename):
                skipped_files.append(filename)
                continue
                
            # 只处理txt文件
            if filename.endswith('.txt'):
                chunk_index = filename.split('.')[0]
                chunk_files[chunk_index] = file_path
                
        if skipped_files:
            print(f"🚫 [UUID:{uuid[:8]}...] 跳过Mac系统文件: {', '.join(skipped_files)}")
            
    except Exception as e:
        print(f"❌ [UUID:{uuid[:8]}...] 读取目录失败 {directory_path}: {e}")
        
    return chunk_files


def get_audio_files_in_directory(directory_path, uuid):
    """
    获取指定目录中的所有音频文件，排除Mac系统文件
    
    Args:
        directory_path (str): 目录路径
        uuid (str): 书籍UUID
        
    Returns:
        dict: {chunk_index: file_path}
    """
    if not os.path.exists(directory_path):
        return {}
    
    audio_files = {}
    skipped_files = []
    
    try:
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            
            # 跳过目录
            if os.path.isdir(file_path):
                continue
                
            # 跳过Mac系统文件
            if is_mac_system_file(filename):
                skipped_files.append(filename)
                continue
                
            # 只处理mp3文件
            if filename.endswith('.mp3'):
                chunk_index = filename.split('.')[0]
                
                # 检查文件是否有效（大于1KB）
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size > 1024:  # 大于1KB认为是有效文件
                        audio_files[chunk_index] = file_path
                    else:
                        print(f"⚠️  [UUID:{uuid[:8]}...] 音频文件过小，可能损坏: {filename} ({file_size} 字节)")
                except Exception as e:
                    print(f"⚠️  [UUID:{uuid[:8]}...] 无法检查音频文件: {filename}, 错误: {e}")
                    
        if skipped_files:
            print(f"🚫 [UUID:{uuid[:8]}...] 跳过Mac系统音频文件: {', '.join(skipped_files)}")
            
    except Exception as e:
        print(f"❌ [UUID:{uuid[:8]}...] 读取音频目录失败 {directory_path}: {e}")
        
    return audio_files


def get_all_book_uuids(input_base_dir):
    """
    获取所有书籍的UUID列表
    
    Args:
        input_base_dir (str): 输入基础目录
        
    Returns:
        list: UUID列表
    """
    if not os.path.exists(input_base_dir):
        return []
    
    uuids = []
    skipped_dirs = []
    
    try:
        for item in os.listdir(input_base_dir):
            item_path = os.path.join(input_base_dir, item)
            
            # 只处理目录
            if not os.path.isdir(item_path):
                continue
                
            # 跳过Mac系统目录
            if is_mac_system_file(item):
                skipped_dirs.append(item)
                continue
                
            # 简单验证UUID格式（36字符，包含4个连字符）
            if len(item) == 36 and item.count('-') == 4:
                uuids.append(item)
            else:
                print(f"⚠️  跳过非UUID格式目录: {item}")
                
        if skipped_dirs:
            print(f"🚫 跳过Mac系统目录: {', '.join(skipped_dirs)}")
            
    except Exception as e:
        print(f"❌ 读取UUID目录失败 {input_base_dir}: {e}")
        
    return sorted(uuids)


def check_book_consistency(uuid, input_dir, output_dir, verbose=False):
    """
    检查单个书籍的文件一致性
    
    Args:
        uuid (str): 书籍UUID
        input_dir (str): 输入基础目录
        output_dir (str): 输出基础目录
        verbose (bool): 是否显示详细信息
        
    Returns:
        dict: 检查结果
    """
    print(f"\n=== 📚 检查书籍 UUID: {uuid[:8]}...{uuid[-8:]} ===")
    
    # 获取输入文本块文件
    input_book_dir = os.path.join(input_dir, uuid)
    chunk_files = get_chunk_files_in_directory(input_book_dir, uuid)
    
    # 获取输出音频文件
    output_book_dir = os.path.join(output_dir, uuid)
    audio_files = get_audio_files_in_directory(output_book_dir, uuid)
    
    # 分析结果
    chunk_indices = set(chunk_files.keys())
    audio_indices = set(audio_files.keys())
    
    missing_audio = chunk_indices - audio_indices  # 有文本块但没有音频
    orphaned_audio = audio_indices - chunk_indices  # 有音频但没有文本块
    matched_indices = chunk_indices & audio_indices  # 匹配的文件
    
    result = {
        'uuid': uuid,
        'total_chunks': len(chunk_files),
        'total_audio': len(audio_files),
        'matched': len(matched_indices),
        'missing_audio': len(missing_audio),
        'orphaned_audio': len(orphaned_audio),
        'consistent': len(missing_audio) == 0 and len(orphaned_audio) == 0,
        'missing_audio_list': sorted(missing_audio, key=lambda x: int(x) if x.isdigit() else 0),
        'orphaned_audio_list': sorted(orphaned_audio, key=lambda x: int(x) if x.isdigit() else 0),
        'chunk_files': chunk_files,
        'audio_files': audio_files
    }
    
    # 显示结果
    print(f"📁 输入目录: {input_book_dir}")
    print(f"📁 输出目录: {output_book_dir}")
    print(f"📊 文本块数量: {result['total_chunks']}")
    print(f"🎵 音频文件数量: {result['total_audio']}")
    print(f"✅ 匹配文件数量: {result['matched']}")
    
    if result['consistent']:
        print(f"🎉 状态: ✅ 一致")
    else:
        print(f"⚠️  状态: ❌ 不一致")
        
        if missing_audio:
            print(f"🔍 缺失音频文件: {len(missing_audio)} 个")
            if verbose:
                for idx in result['missing_audio_list']:
                    chunk_file = chunk_files.get(idx, 'unknown')
                    print(f"   - 块 {idx}: {chunk_file}")
        
        if orphaned_audio:
            print(f"🗑️  多余音频文件: {len(orphaned_audio)} 个")
            if verbose:
                for idx in result['orphaned_audio_list']:
                    audio_file = audio_files.get(idx, 'unknown')
                    print(f"   - 块 {idx}: {audio_file}")
    
    return result


def fix_orphaned_audio_files(results, confirm=True):
    """
    删除多余的音频文件
    
    Args:
        results (list): 检查结果列表
        confirm (bool): 是否需要确认
        
    Returns:
        int: 删除的文件数量
    """
    orphaned_files = []
    
    # 收集所有多余的音频文件
    for result in results:
        if result['orphaned_audio']:
            for idx in result['orphaned_audio_list']:
                audio_file = result['audio_files'].get(idx)
                if audio_file and os.path.exists(audio_file):
                    orphaned_files.append((result['uuid'], idx, audio_file))
    
    if not orphaned_files:
        print("✅ 没有发现多余的音频文件")
        return 0
    
    print(f"\n🗑️  发现 {len(orphaned_files)} 个多余的音频文件:")
    for uuid, idx, audio_file in orphaned_files:
        print(f"   - UUID:{uuid[:8]}... 块{idx}: {audio_file}")
    
    if confirm:
        response = input(f"\n❓ 是否删除这 {len(orphaned_files)} 个多余的音频文件? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ 用户取消了删除操作")
            return 0
    
    # 删除文件
    deleted_count = 0
    for uuid, idx, audio_file in orphaned_files:
        try:
            os.remove(audio_file)
            print(f"✅ 删除成功: UUID:{uuid[:8]}... 块{idx}")
            deleted_count += 1
        except Exception as e:
            print(f"❌ 删除失败: UUID:{uuid[:8]}... 块{idx}, 错误: {e}")
    
    print(f"\n🎉 成功删除 {deleted_count} 个多余的音频文件")
    return deleted_count


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="书籍音频文件一致性检查器 - 检查文本块和音频文件数量是否一致",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  # 基本检查
  python check_audio_chunks_consistency.py --lang en          # 检查英文书籍
  python check_audio_chunks_consistency.py --lang zh          # 检查中文书籍
  
  # 指定UUID检查
  python check_audio_chunks_consistency.py --lang en --uuid 12345678-abcd-efgh-ijkl-123456789012
  
  # 详细模式
  python check_audio_chunks_consistency.py --lang zh --verbose
  
  # 修复模式（删除多余音频文件）
  python check_audio_chunks_consistency.py --lang en --fix-orphaned
        """,
    )
    
    parser.add_argument(
        "--lang", "-l",
        required=True,
        choices=["en", "zh"],
        help="语言类型: en=英文, zh=中文"
    )
    parser.add_argument(
        "--uuid", "-u",
        help="要检查的书籍UUID，不指定则检查所有书籍"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细信息，包括每个缺失/多余的文件"
    )
    parser.add_argument(
        "--fix-orphaned",
        action="store_true",
        help="删除多余的音频文件（没有对应文本块的音频文件）"
    )
    parser.add_argument(
        "--no-confirm",
        action="store_true",
        help="修复时不需要确认（慎用）"
    )
    
    args = parser.parse_args()
    
    lang = args.lang
    lang_name = "中文" if lang == "zh" else "英文"
    
    # 获取路径
    input_dir, output_dir = get_paths_for_language(lang)
    
    print(f"🔍 书籍音频文件一致性检查器")
    print(f"🌐 检查语言: {lang_name} ({lang})")
    print(f"📁 输入目录: {input_dir}")
    print(f"📁 输出目录: {output_dir}")
    print(f"🚫 自动排除Mac系统文件")
    
    # 检查目录是否存在
    if not os.path.exists(input_dir):
        print(f"❌ 输入目录不存在: {input_dir}")
        return
    
    if not os.path.exists(output_dir):
        print(f"⚠️  输出目录不存在: {output_dir}")
        print("💡 可能还没有运行 synthesize_book_audio.py 生成音频文件")
    
    # 获取要检查的UUID列表
    if args.uuid:
        uuids = [args.uuid]
        print(f"📚 检查模式: 指定UUID ({args.uuid[:8]}...{args.uuid[-8:]})")
    else:
        uuids = get_all_book_uuids(input_dir)
        print(f"📚 检查模式: 所有书籍 (共 {len(uuids)} 本)")
    
    if not uuids:
        print("❌ 没有找到任何书籍UUID")
        return
    
    # 检查所有书籍
    results = []
    for uuid in uuids:
        result = check_book_consistency(uuid, input_dir, output_dir, args.verbose)
        results.append(result)
    
    # 生成总结报告
    print(f"\n=== 📊 检查结果总结 ===")
    
    total_books = len(results)
    consistent_books = sum(1 for r in results if r['consistent'])
    inconsistent_books = total_books - consistent_books
    
    total_chunks = sum(r['total_chunks'] for r in results)
    total_audio = sum(r['total_audio'] for r in results)
    total_missing = sum(r['missing_audio'] for r in results)
    total_orphaned = sum(r['orphaned_audio'] for r in results)
    
    print(f"📚 书籍总数: {total_books}")
    print(f"✅ 一致书籍: {consistent_books}")
    print(f"❌ 不一致书籍: {inconsistent_books}")
    print(f"📄 文本块总数: {total_chunks}")
    print(f"🎵 音频文件总数: {total_audio}")
    
    if total_missing > 0:
        print(f"🔍 缺失音频文件: {total_missing} 个")
    
    if total_orphaned > 0:
        print(f"🗑️  多余音频文件: {total_orphaned} 个")
    
    # 显示不一致的书籍详情
    if inconsistent_books > 0:
        print(f"\n❌ 不一致的书籍详情:")
        for result in results:
            if not result['consistent']:
                uuid = result['uuid']
                print(f"   - UUID:{uuid[:8]}...{uuid[-8:]}: "
                      f"文本块={result['total_chunks']}, "
                      f"音频={result['total_audio']}, "
                      f"缺失={result['missing_audio']}, "
                      f"多余={result['orphaned_audio']}")
    
    # 修复建议
    if inconsistent_books > 0:
        print(f"\n💡 修复建议:")
        
        if total_missing > 0:
            print(f"   - 有 {total_missing} 个音频文件缺失，建议重新运行:")
            print(f"     python synthesize_book_audio.py --lang {lang}")
        
        if total_orphaned > 0:
            print(f"   - 有 {total_orphaned} 个多余音频文件，可以使用以下命令删除:")
            print(f"     python check_audio_chunks_consistency.py --lang {lang} --fix-orphaned")
    
    # 执行修复（如果需要）
    if args.fix_orphaned and total_orphaned > 0:
        print(f"\n🔧 执行修复操作...")
        deleted_count = fix_orphaned_audio_files(results, not args.no_confirm)
        
        if deleted_count > 0:
            print(f"\n🎉 修复完成，删除了 {deleted_count} 个多余的音频文件")
        else:
            print(f"\n❌ 修复失败或用户取消")


if __name__ == "__main__":
    main() 