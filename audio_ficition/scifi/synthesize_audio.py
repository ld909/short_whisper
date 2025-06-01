#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频合成脚本
使用 f5-tts CLI 将 chunk_stories.py 输出的文本块合成为音频文件
支持断点续传功能
"""

import os
import glob
import argparse
import subprocess
import time
import tempfile
import shutil
import json
from pathlib import Path

# ============ 配置参数 ============
# 输入目录：存放文本块的目录
INPUT_DIR = "/mnt/dhl/audio/scifi/story_chunks"

# 输出目录：生成的音频文件保存目录
OUTPUT_DIR = "/media/dhl/audio/scifi/mp3_clips"

# 参考音频文件：用于语音克隆的参考音频
REF_AUDIO = "/home/dhl/Documents/short_whisper/audio_ficition/audio_ref/11_normalized_2.mp3"

# 默认使用的模型
DEFAULT_MODEL = "F5TTS_v1_Base"

# 代理设置
PROXY_HTTP = "http://127.0.0.1:7897"
PROXY_HTTPS = "http://127.0.0.1:7897"
# ===================================


def set_clash_proxy():
    """设置代理环境变量，用于下载模型文件"""
    os.environ["http_proxy"] = PROXY_HTTP
    os.environ["https_proxy"] = PROXY_HTTPS
    # os.environ["all_proxy"] = "socks5://127.0.0.1:7891"
    print("🌐 成功设定clash环境proxy...")


def unset_clash_proxy():
    """取消代理环境变量"""
    os.environ.pop("http_proxy", None)
    os.environ.pop("https_proxy", None)
    # os.environ.pop("all_proxy", None)
    print("🌐 成功取消clash环境proxy...")


def get_chunk_files(input_dir):
    """
    获取所有文本块文件，按故事索引和块索引排序
    排除Mac生成的以点开头的meta文件
    
    Args:
        input_dir (str): 输入目录路径
        
    Returns:
        list: 排序后的文本块文件路径列表
    """
    if not os.path.exists(input_dir):
        print(f"❌ 输入目录不存在: {input_dir}")
        return []
    
    chunk_files = []
    
    # 遍历所有故事目录
    for story_dir in glob.glob(os.path.join(input_dir, "*")):
        if os.path.isdir(story_dir):
            story_index = os.path.basename(story_dir)
            
            # 排除以点开头的目录（如.DS_Store等）
            if story_index.startswith('.'):
                print(f"⏭️  跳过隐藏目录: {story_dir}")
                continue
            
            # 获取该故事的所有txt文件
            chunk_pattern = os.path.join(story_dir, "*.txt")
            story_chunks = glob.glob(chunk_pattern)
            
            # 过滤掉以点开头的文件
            filtered_chunks = []
            for chunk_file in story_chunks:
                filename = os.path.basename(chunk_file)
                if filename.startswith('.'):
                    print(f"⏭️  跳过隐藏文件: {chunk_file}")
                    continue
                # 确保文件确实是txt文件且不是临时文件
                if filename.endswith('.txt') and not filename.startswith('._'):
                    filtered_chunks.append(chunk_file)
                else:
                    print(f"⏭️  跳过非txt文件或临时文件: {chunk_file}")
            
            # 按块索引排序
            def extract_chunk_number(filepath):
                basename = os.path.basename(filepath)
                try:
                    return int(basename.split('.')[0])
                except:
                    return 0
            
            filtered_chunks.sort(key=extract_chunk_number)
            
            # 添加到总列表
            for chunk_file in filtered_chunks:
                chunk_files.append((story_index, chunk_file))
    
    # 按故事索引排序
    def extract_story_number(item):
        story_index = item[0]
        try:
            return int(story_index)
        except:
            return 0
    
    chunk_files.sort(key=extract_story_number)
    
    return chunk_files


def read_text_content(file_path):
    """
    读取文本文件内容
    
    Args:
        file_path (str): 文件路径
        
    Returns:
        str: 文件内容，如果读取失败返回 None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        return content
    except Exception as e:
        print(f"❌ 读取文件失败 {file_path}: {e}")
        return None


def clean_text_for_tts(text_content):
    """
    清理文本内容，避免CLI参数冲突
    
    Args:
        text_content (str): 原始文本内容
        
    Returns:
        str: 清理后的文本内容
    """
    if not text_content:
        return ""
    
    # 移除或替换可能导致CLI参数问题的字符
    cleaned_text = text_content
    
    # 替换双引号为中文引号，避免CLI参数冲突
    cleaned_text = cleaned_text.replace('"', '"').replace('"', '"')
    
    # 替换单引号为中文引号
    cleaned_text = cleaned_text.replace("'", "'").replace("'", "'")
    
    # 移除可能的控制字符
    cleaned_text = ''.join(char for char in cleaned_text if ord(char) >= 32 or char in '\n\r\t')
    
    # 确保文本不为空
    cleaned_text = cleaned_text.strip()
    if not cleaned_text:
        return "无内容"
    
    return cleaned_text


def synthesize_audio(text_content, ref_audio, output_file, model="F5TTS_v1_Base"):
    """
    使用 f5-tts CLI 合成音频
    
    Args:
        text_content (str): 要合成的文本内容
        ref_audio (str): 参考音频文件路径
        output_file (str): 输出音频文件路径
        model (str): 使用的模型名称
        
    Returns:
        bool: 合成是否成功
    """
    temp_text_file = None
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)
        
        # 清理文本内容
        cleaned_text = clean_text_for_tts(text_content)
        
        # 创建临时文本文件来避免CLI参数中的特殊字符问题
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as temp_file:
            temp_file.write(cleaned_text)
            temp_text_file = temp_file.name
        
        print(f"📝 文本长度: {len(text_content)} -> {len(cleaned_text)} 字符")
        print(f"📄 临时文本文件: {temp_text_file}")
        
        # 构建 f5-tts 命令，使用临时文件
        cmd = [
            "f5-tts_infer-cli",
            "--model", model,
            "--ref_audio", ref_audio,
            "--ref_text", "",  # 总是空的，但必须提供
            "--gen_file", temp_text_file,  # 使用文件而不是直接传递文本
            "--remove_silence",
            "--output_dir", output_dir,
            "--output_file", os.path.basename(output_file)
        ]
        
        print(f"🔄 执行命令: {' '.join(cmd)}")
        
        # 执行命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0:
            print(f"✅ 音频合成成功: {output_file}")
            return True
        else:
            print(f"❌ 音频合成失败:")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")
            
            # 如果 --gen_file 参数不支持，回退到 --gen_text 方式
            if "--gen_file" in result.stderr or "gen_file" in result.stderr:
                print(f"⚠️  --gen_file 参数不支持，回退到 --gen_text 方式")
                return synthesize_audio_fallback(cleaned_text, ref_audio, output_file, model)
            
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ 音频合成超时: {output_file}")
        return False
    except Exception as e:
        print(f"❌ 音频合成出错: {e}")
        return False
    finally:
        # 清理临时文件
        if temp_text_file and os.path.exists(temp_text_file):
            try:
                os.unlink(temp_text_file)
                print(f"🗑️  已删除临时文件: {temp_text_file}")
            except Exception as e:
                print(f"⚠️  删除临时文件失败: {e}")


def synthesize_audio_fallback(text_content, ref_audio, output_file, model="F5TTS_v1_Base"):
    """
    回退方案：直接使用 --gen_text 参数，但对文本进行更严格的转义
    
    Args:
        text_content (str): 要合成的文本内容（已清理）
        ref_audio (str): 参考音频文件路径
        output_file (str): 输出音频文件路径
        model (str): 使用的模型名称
        
    Returns:
        bool: 合成是否成功
    """
    try:
        output_dir = os.path.dirname(output_file)
        
        # 进一步转义文本，确保在命令行中安全
        escaped_text = text_content.replace('\\', '\\\\').replace('\n', ' ').replace('\r', ' ')
        
        # 限制文本长度，避免命令行参数过长
        if len(escaped_text) > 1000:
            escaped_text = escaped_text[:1000] + "..."
            print(f"⚠️  文本过长，已截断到1000字符")
        
        # 构建 f5-tts 命令
        cmd = [
            "f5-tts_infer-cli",
            "--model", model,
            "--ref_audio", ref_audio,
            "--ref_text", "",
            "--gen_text", escaped_text,
            "--remove_silence",
            "--output_dir", output_dir,
            "--output_file", os.path.basename(output_file)
        ]
        
        print(f"🔄 回退方案执行命令")
        
        # 执行命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print(f"✅ 音频合成成功（回退方案）: {output_file}")
            return True
        else:
            print(f"❌ 音频合成失败（回退方案）:")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 回退方案出错: {e}")
        return False


def is_valid_audio_file(file_path, min_size_bytes=1024):
    """
    检查音频文件是否有效
    
    Args:
        file_path (str): 音频文件路径
        min_size_bytes (int): 最小文件大小（字节）
        
    Returns:
        bool: 文件是否有效
    """
    if not os.path.exists(file_path):
        return False
    
    try:
        file_size = os.path.getsize(file_path)
        if file_size < min_size_bytes:
            print(f"⚠️  文件过小，可能损坏: {file_path} ({file_size} 字节)")
            return False
        return True
    except Exception as e:
        print(f"⚠️  检查文件时出错: {file_path}, 错误: {e}")
        return False


def scan_existing_files(output_dir):
    """
    扫描输出目录中已存在的音频文件
    
    Args:
        output_dir (str): 输出目录路径
        
    Returns:
        dict: 已存在文件的字典 {(story_index, chunk_index): file_path}
    """
    existing_files = {}
    
    if not os.path.exists(output_dir):
        return existing_files
    
    print(f"🔍 扫描已存在的音频文件...")
    
    # 遍历所有故事目录
    for story_dir in glob.glob(os.path.join(output_dir, "*")):
        if os.path.isdir(story_dir):
            story_index = os.path.basename(story_dir)
            
            # 获取该故事的所有音频文件
            audio_pattern = os.path.join(story_dir, "*.mp3")
            audio_files = glob.glob(audio_pattern)
            
            for audio_file in audio_files:
                chunk_filename = os.path.basename(audio_file)
                chunk_index = chunk_filename.split('.')[0]
                
                # 检查文件是否有效
                if is_valid_audio_file(audio_file):
                    existing_files[(story_index, chunk_index)] = audio_file
                else:
                    print(f"🗑️  发现无效文件，将重新生成: {audio_file}")
                    try:
                        os.remove(audio_file)
                        print(f"✅ 已删除无效文件: {audio_file}")
                    except Exception as e:
                        print(f"❌ 删除无效文件失败: {e}")
    
    print(f"📊 找到 {len(existing_files)} 个有效的音频文件")
    return existing_files


def get_progress_stats(chunk_files, existing_files):
    """
    获取进度统计信息
    
    Args:
        chunk_files (list): 所有文本块文件列表
        existing_files (dict): 已存在的音频文件字典
        
    Returns:
        dict: 进度统计信息
    """
    total_files = len(chunk_files)
    completed_files = 0
    pending_files = []
    
    for story_index, chunk_file in chunk_files:
        chunk_filename = os.path.basename(chunk_file)
        chunk_index = chunk_filename.split('.')[0]
        
        if (story_index, chunk_index) in existing_files:
            completed_files += 1
        else:
            pending_files.append((story_index, chunk_file))
    
    remaining_files = total_files - completed_files
    completion_rate = (completed_files / total_files * 100) if total_files > 0 else 0
    
    return {
        'total_files': total_files,
        'completed_files': completed_files,
        'remaining_files': remaining_files,
        'pending_files': pending_files,
        'completion_rate': completion_rate
    }


def save_progress_log(output_dir, stats, successful_count=0, failed_count=0):
    """
    保存进度日志
    
    Args:
        output_dir (str): 输出目录
        stats (dict): 统计信息
        successful_count (int): 本次成功处理的文件数
        failed_count (int): 本次失败的文件数
    """
    try:
        log_file = os.path.join(output_dir, "synthesis_progress.json")
        
        progress_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_files': stats['total_files'],
            'completed_files': stats['completed_files'] + successful_count,
            'remaining_files': stats['remaining_files'] - successful_count - failed_count,
            'completion_rate': ((stats['completed_files'] + successful_count) / stats['total_files'] * 100) if stats['total_files'] > 0 else 0,
            'session_successful': successful_count,
            'session_failed': failed_count
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2, ensure_ascii=False)
        
        print(f"📝 进度日志已保存: {log_file}")
        
    except Exception as e:
        print(f"⚠️  保存进度日志失败: {e}")


def process_chunk(story_index, chunk_file, ref_audio, output_base_dir, model="F5TTS_v1_Base", force_regenerate=False):
    """
    处理单个文本块，合成音频
    
    Args:
        story_index (str): 故事索引
        chunk_file (str): 文本块文件路径
        ref_audio (str): 参考音频文件路径
        output_base_dir (str): 输出基础目录
        model (str): 使用的模型名称
        force_regenerate (bool): 是否强制重新生成（忽略已存在的文件）
        
    Returns:
        bool: 处理是否成功
    """
    # 读取文本内容
    text_content = read_text_content(chunk_file)
    if not text_content:
        return False
    
    # 获取块索引
    chunk_filename = os.path.basename(chunk_file)
    chunk_index = chunk_filename.split('.')[0]
    
    # 构建输出文件路径
    output_file = os.path.join(output_base_dir, story_index, f"{chunk_index}.mp3")
    
    # 检查文件是否已存在且有效（除非强制重新生成）
    if not force_regenerate and is_valid_audio_file(output_file):
        file_size = os.path.getsize(output_file)
        print(f"⏭️  文件已存在且有效，跳过: {output_file} ({file_size} 字节)")
        return True
    
    print(f"📝 处理文本块: 故事 {story_index}, 块 {chunk_index}")
    print(f"   输入: {chunk_file}")
    print(f"   输出: {output_file}")
    print(f"   文本长度: {len(text_content)} 字符")
    
    # 合成音频
    success = synthesize_audio(text_content, ref_audio, output_file, model)
    
    if success:
        # 检查输出文件是否真的生成了且有效
        if is_valid_audio_file(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ 音频文件生成成功: {output_file} ({file_size} 字节)")
            return True
        else:
            print(f"❌ 音频文件未生成或无效: {output_file}")
            return False
    else:
        return False


def cleanup_and_exit(use_proxy):
    """清理代理设置并退出"""
    if use_proxy:
        unset_clash_proxy()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="音频合成器 - 使用 f5-tts 将文本块合成为音频（支持断点续传）")
    parser.add_argument(
        "--input-dir",
        default=INPUT_DIR,
        help=f"输入目录路径 (默认: {INPUT_DIR})"
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        help=f"输出目录路径 (默认: {OUTPUT_DIR})"
    )
    parser.add_argument(
        "--ref-audio",
        default=REF_AUDIO,
        help=f"参考音频文件路径 (默认: {REF_AUDIO})"
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"使用的 f5-tts 模型 (默认: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--story",
        help="只处理指定故事索引的文本块（可选）"
    )
    parser.add_argument(
        "--chunk",
        help="只处理指定块索引的文本块（需要同时指定 --story）"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="预览模式，只显示会处理哪些文件，不实际处理"
    )
    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        help="强制重新生成所有文件，忽略已存在的文件"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="断点续传模式，跳过已存在的有效音频文件 (默认: True)"
    )
    parser.add_argument(
        "--proxy",
        action="store_true",
        default=True,
        help="启用代理设置，用于下载模型文件 (默认: True)"
    )
    parser.add_argument(
        "--no-proxy",
        action="store_true",
        help="禁用代理设置"
    )
    
    args = parser.parse_args()
    
    # 设置代理（如果需要）
    use_proxy = args.proxy and not args.no_proxy
    if use_proxy:
        set_clash_proxy()
    else:
        print("🌐 未启用代理设置")
    
    input_dir = args.input_dir
    output_dir = args.output_dir
    ref_audio = args.ref_audio
    model = args.model
    
    print(f"🎵 音频合成器 (支持断点续传)")
    print(f"📁 输入目录: {input_dir}")
    print(f"📁 输出目录: {output_dir}")
    print(f"🎤 参考音频: {ref_audio}")
    print(f"🤖 使用模型: {model}")
    
    if args.force_regenerate:
        print(f"🔄 强制重新生成模式: 将重新生成所有文件")
    elif args.resume:
        print(f"⚡ 断点续传模式: 将跳过已存在的有效文件")
    
    # 检查参考音频文件是否存在
    if not os.path.exists(ref_audio):
        print(f"❌ 参考音频文件不存在: {ref_audio}")
        cleanup_and_exit(use_proxy)
        return
    
    # 获取所有文本块文件
    chunk_files = get_chunk_files(input_dir)
    
    if not chunk_files:
        print(f"❌ 在目录 {input_dir} 中未找到任何文本块文件")
        cleanup_and_exit(use_proxy)
        return
    
    # 过滤文件（如果指定了特定故事或块）
    if args.story:
        chunk_files = [(story_idx, chunk_file) for story_idx, chunk_file in chunk_files 
                      if story_idx == args.story]
        
        if args.chunk:
            chunk_files = [(story_idx, chunk_file) for story_idx, chunk_file in chunk_files 
                          if os.path.basename(chunk_file).split('.')[0] == args.chunk]
    
    if not chunk_files:
        print(f"❌ 根据指定条件未找到匹配的文件")
        cleanup_and_exit(use_proxy)
        return
    
    print(f"\n📊 找到 {len(chunk_files)} 个文本块文件")
    
    # 扫描已存在的文件（除非强制重新生成）
    existing_files = {}
    if not args.force_regenerate:
        existing_files = scan_existing_files(output_dir)
    
    # 获取进度统计
    stats = get_progress_stats(chunk_files, existing_files)
    
    print(f"\n📈 进度统计:")
    print(f"   总文件数: {stats['total_files']}")
    print(f"   已完成: {stats['completed_files']} ({stats['completion_rate']:.1f}%)")
    print(f"   待处理: {stats['remaining_files']}")
    
    if args.preview:
        print(f"\n📋 预览模式 - 将要处理的文件:")
        for i, (story_index, chunk_file) in enumerate(stats['pending_files'], 1):
            chunk_filename = os.path.basename(chunk_file)
            chunk_index = chunk_filename.split('.')[0]
            output_file = os.path.join(output_dir, story_index, f"{chunk_index}.mp3")
            
            print(f"  {i:3d}. 故事 {story_index}, 块 {chunk_index}")
            print(f"       输入: {chunk_file}")
            print(f"       输出: {output_file}")
            print(f"       状态: 🆕 需要生成")
        
        if stats['completed_files'] > 0:
            print(f"\n✅ 已完成的文件: {stats['completed_files']} 个")
        
        cleanup_and_exit(use_proxy)
        return
    
    # 如果没有待处理的文件
    if not stats['pending_files']:
        print(f"\n🎉 所有文件都已完成！无需处理。")
        print(f"📁 输出目录: {output_dir}")
        cleanup_and_exit(use_proxy)
        return
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n🔄 开始音频合成...")
    print(f"⚠️  注意: 为避免显卡冲突，将顺序处理每个文件")
    print(f"📝 本次将处理 {len(stats['pending_files'])} 个文件")
    
    successful_count = 0
    failed_count = 0
    
    try:
        start_time = time.time()
        
        for i, (story_index, chunk_file) in enumerate(stats['pending_files'], 1):
            chunk_filename = os.path.basename(chunk_file)
            chunk_index = chunk_filename.split('.')[0]
            
            print(f"\n处理第 {i}/{len(stats['pending_files'])} 个文件: 故事 {story_index}, 块 {chunk_index}")
            print(f"总体进度: {stats['completed_files'] + i}/{stats['total_files']} ({(stats['completed_files'] + i)/stats['total_files']*100:.1f}%)")
            
            success = process_chunk(story_index, chunk_file, ref_audio, output_dir, model, args.force_regenerate)
            
            if success:
                successful_count += 1
            else:
                failed_count += 1
            
            # 在每个文件处理后稍作停顿，让显卡休息一下
            if i < len(stats['pending_files']):
                print("⏳ 等待 2 秒...")
                time.sleep(2)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 保存进度日志
        save_progress_log(output_dir, stats, successful_count, failed_count)
        
        # 统计结果
        print(f"\n=== 🎉 处理完成 ===")
        print(f"✅ 本次成功合成: {successful_count} 个音频文件")
        print(f"❌ 本次合成失败: {failed_count} 个音频文件")
        print(f"⏭️  之前已完成: {stats['completed_files']} 个音频文件")
        print(f"📊 总体完成: {stats['completed_files'] + successful_count}/{stats['total_files']} ({(stats['completed_files'] + successful_count)/stats['total_files']*100:.1f}%)")
        print(f"⏱️  本次耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")
        
        if successful_count > 0:
            avg_time = total_time / successful_count
            print(f"📊 平均每个文件: {avg_time:.1f} 秒")
        
        total_processed = successful_count + failed_count
        if total_processed > 0:
            success_rate = successful_count / total_processed * 100
            print(f"📊 本次成功率: {success_rate:.1f}%")
        
        print(f"📁 输出目录: {output_dir}")
        
        # 检查是否还有未完成的文件
        remaining = stats['remaining_files'] - successful_count - failed_count
        if remaining > 0:
            print(f"\n⚠️  还有 {remaining} 个文件未处理，可以重新运行程序继续处理")
        elif failed_count > 0:
            print(f"\n⚠️  有 {failed_count} 个文件处理失败，可以重新运行程序重试")
        else:
            print(f"\n🎉 所有文件处理完成！")
        
        if successful_count > 0:
            print(f"\n📝 音频文件已保存到: {output_dir}")
            print(f"📁 目录结构: mp3_clips/story_index/chunk_index.mp3")
    
    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断了程序执行")
        print(f"✅ 已成功处理: {successful_count} 个文件")
        print(f"❌ 处理失败: {failed_count} 个文件")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        print(f"✅ 已成功处理: {successful_count} 个文件")
        print(f"❌ 处理失败: {failed_count} 个文件")
    finally:
        # 清理代理设置
        if use_proxy:
            unset_clash_proxy()


if __name__ == "__main__":
    main() 