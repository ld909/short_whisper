#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASR识别和字幕合并脚本
对 synthesize_audio.py 生成的 mp3 clip 进行 ASR 识别，生成字幕并合并

功能说明:
1. 使用 nvidia/parakeet-tdt-0.6b-v2 模型对 mp3 clip 进行 ASR 识别
2. 生成 word level 和 segment level 的字幕文件
3. 通过 padding 时间戳的方式合并不同 clip 的字幕
4. 支持断点续传，避免重复处理
5. 智能跳过数据不一致的故事，只处理完整的故事
6. 只在 Ubuntu 系统下运行
7. 支持多个主题: scifi, thriller, horror, fantasy, romance

路径说明:
输入:
- MP3 clip: /media/dhl/audio/{theme}/mp3_clips/[故事索引]/[块索引].mp3

输出:
- Word level 字幕: /mnt/dhl/audio/{theme}/word_level_srt/[故事索引]/[块索引].srt
- Segment level 字幕: /mnt/dhl/audio/{theme}/seg_level_srt/[故事索引]/[块索引].srt
- 合并字幕: /mnt/dhl/audio/{theme}/srt_merge/[故事索引].srt

使用方法:
1. 基本使用: python asr_and_merge_subtitles.py --theme scifi
2. 强制重新处理: python asr_and_merge_subtitles.py --theme scifi -f
3. 指定故事范围: python asr_and_merge_subtitles.py --theme scifi --start 1 --end 10
4. 只处理指定故事: python asr_and_merge_subtitles.py --theme scifi --story 5
5. 预览模式: python asr_and_merge_subtitles.py --theme scifi --preview
6. 跳过一致性检查: python asr_and_merge_subtitles.py --theme scifi --skip-consistency-check

注意:
- 需要GPU支持和NeMo ASR环境
- 只在Ubuntu系统下运行，Mac系统会自动退出
- 脚本会自动检查文本块和音频文件数量一致性，确保数据完整
- 如果部分故事数据不一致，会跳过这些故事，只处理完整的故事
- 被跳过的故事可以在修复数据问题后重新运行脚本进行处理
"""

import os
import sys
import time
import glob
import argparse
import platform
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from tqdm import tqdm

# 检查操作系统
if platform.system() == "Darwin":
    print("❌ 该脚本需要GPU支持，只能在Ubuntu系统下运行")
    print("💡 请在Ubuntu系统下重新运行此脚本")
    sys.exit(1)

print("✅ 检测到Ubuntu系统，继续执行...")

# 导入ASR相关依赖
try:
    import nemo.collections.asr as nemo_asr
    print("✅ NeMo ASR 导入成功")
except ImportError as e:
    print("❌ 无法导入 NeMo ASR，请确保已正确安装")
    print("💡 安装命令: pip install nemo-toolkit[asr]")
    sys.exit(1)

# ============ 配置参数 ============
# 支持的主题列表
SUPPORTED_THEMES = ["scifi", "thriller", "horror", "fantasy", "romance"]

# 根据主题获取路径
def get_theme_paths(theme: str) -> Dict[str, str]:
    """根据主题获取相关路径"""
    if theme not in SUPPORTED_THEMES:
        raise ValueError(f"不支持的主题: {theme}，支持的主题: {', '.join(SUPPORTED_THEMES)}")
    
    return {
        "input_dir": f"/media/dhl/audio/{theme}/mp3_clips",
        "text_chunks_dir": f"/mnt/dhl/audio/{theme}/story_chunks",
        "word_level_srt_dir": f"/mnt/dhl/audio/{theme}/word_level_srt",
        "seg_level_srt_dir": f"/mnt/dhl/audio/{theme}/seg_level_srt",
        "merge_srt_dir": f"/mnt/dhl/audio/{theme}/srt_merge"
    }

# ASR 模型
ASR_MODEL_NAME = "nvidia/parakeet-tdt-0.6b-v2"
# ===================================


def get_text_chunks_count(chunks_dir: str) -> Dict[str, Dict]:
    """
    统计文本块目录中每个故事的文本块数量和索引列表
    排除Mac系统产生的以点开头的文件
    
    Args:
        chunks_dir (str): 文本块目录路径
        
    Returns:
        Dict[str, Dict]: {story_index: {"count": int, "indices": List[str]}}
    """
    chunks_info = {}
    
    if not os.path.exists(chunks_dir):
        print(f"❌ 文本块目录不存在: {chunks_dir}")
        return chunks_info
    
    # 遍历所有故事目录
    for story_dir in glob.glob(os.path.join(chunks_dir, "*")):
        if os.path.isdir(story_dir):
            story_index = os.path.basename(story_dir)
            
            # 排除以点开头的目录
            if story_index.startswith("."):
                continue
            
            # 统计该故事的txt文件数量和索引
            txt_files = glob.glob(os.path.join(story_dir, "*.txt"))
            
            # 过滤掉以点开头的文件和临时文件，并提取索引
            valid_indices = []
            for txt_file in txt_files:
                filename = os.path.basename(txt_file)
                if not filename.startswith(".") and not filename.startswith("._") and filename.endswith(".txt"):
                    # 提取文件索引（去掉.txt扩展名）
                    file_index = filename[:-4]  # 去掉 .txt
                    valid_indices.append(file_index)
            
            # 排序索引
            try:
                valid_indices.sort(key=lambda x: int(x) if x.isdigit() else 0)
            except:
                valid_indices.sort()
            
            chunks_info[story_index] = {
                "count": len(valid_indices),
                "indices": valid_indices
            }
    
    return chunks_info


def get_audio_clips_count(clips_dir: str) -> Dict[str, Dict]:
    """
    统计音频文件目录中每个故事的音频文件数量和索引列表
    排除Mac系统产生的以点开头的文件
    
    Args:
        clips_dir (str): 音频文件目录路径
        
    Returns:
        Dict[str, Dict]: {story_index: {"count": int, "indices": List[str]}}
    """
    audio_info = {}
    
    if not os.path.exists(clips_dir):
        print(f"❌ 音频文件目录不存在: {clips_dir}")
        return audio_info
    
    # 遍历所有故事目录
    for story_dir in glob.glob(os.path.join(clips_dir, "*")):
        if os.path.isdir(story_dir):
            story_index = os.path.basename(story_dir)
            
            # 排除以点开头的目录
            if story_index.startswith("."):
                continue
            
            # 统计该故事的mp3文件数量和索引
            mp3_files = glob.glob(os.path.join(story_dir, "*.mp3"))
            
            # 过滤掉以点开头的文件和临时文件，并提取索引
            valid_indices = []
            for mp3_file in mp3_files:
                filename = os.path.basename(mp3_file)
                if not filename.startswith(".") and not filename.startswith("._") and filename.endswith(".mp3"):
                    # 提取文件索引（去掉.mp3扩展名）
                    file_index = filename[:-4]  # 去掉 .mp3
                    valid_indices.append(file_index)
            
            # 排序索引
            try:
                valid_indices.sort(key=lambda x: int(x) if x.isdigit() else 0)
            except:
                valid_indices.sort()
            
            audio_info[story_index] = {
                "count": len(valid_indices),
                "indices": valid_indices
            }
    
    return audio_info


def check_chunks_audio_consistency(chunks_dir: str, audio_dir: str) -> Tuple[bool, Dict]:
    """
    检查文本块和音频文件的数量和索引是否完全一致
    
    Args:
        chunks_dir (str): 文本块目录路径
        audio_dir (str): 音频文件目录路径
        
    Returns:
        Tuple[bool, Dict]: (是否一致, 详细统计信息)
    """
    print("🔍 开始检查文本块和音频文件的数量和索引一致性...")
    
    # 统计文本块信息
    chunks_info = get_text_chunks_count(chunks_dir)
    print(f"📄 文本块统计: 找到 {len(chunks_info)} 个故事")
    
    # 统计音频文件信息
    audio_info = get_audio_clips_count(audio_dir)
    print(f"🎵 音频文件统计: 找到 {len(audio_info)} 个故事")
    
    # 比较结果
    all_stories = set(chunks_info.keys()) | set(audio_info.keys())
    
    consistent = True
    inconsistent_stories = []
    missing_chunks = []
    missing_audio = []
    mismatched_counts = []
    mismatched_indices = []
    
    check_details = {
        'total_stories': len(all_stories),
        'chunks_stories': len(chunks_info),
        'audio_stories': len(audio_info),
        'consistent_stories': [],
        'inconsistent_stories': [],
        'missing_chunks_stories': [],
        'missing_audio_stories': [],
        'mismatched_count_stories': [],
        'mismatched_indices_stories': []
    }
    
    for story_index in sorted(all_stories, key=lambda x: int(x) if x.isdigit() else 0):
        chunks_data = chunks_info.get(story_index, {"count": 0, "indices": []})
        audio_data = audio_info.get(story_index, {"count": 0, "indices": []})
        
        chunks_num = chunks_data["count"]
        audio_num = audio_data["count"]
        chunks_indices = set(chunks_data["indices"])
        audio_indices = set(audio_data["indices"])
        
        if story_index not in chunks_info:
            # 缺少文本块
            missing_chunks.append(story_index)
            check_details['missing_chunks_stories'].append({
                'story': story_index,
                'audio_count': audio_num,
                'audio_indices': sorted(audio_data["indices"], key=lambda x: int(x) if x.isdigit() else 0)
            })
            consistent = False
        elif story_index not in audio_info:
            # 缺少音频文件
            missing_audio.append(story_index)
            check_details['missing_audio_stories'].append({
                'story': story_index,
                'chunks_count': chunks_num,
                'chunks_indices': sorted(chunks_data["indices"], key=lambda x: int(x) if x.isdigit() else 0)
            })
            consistent = False
        elif chunks_num != audio_num:
            # 数量不匹配
            mismatched_counts.append(story_index)
            check_details['mismatched_count_stories'].append({
                'story': story_index,
                'chunks_count': chunks_num,
                'audio_count': audio_num,
                'difference': chunks_num - audio_num,
                'chunks_indices': sorted(chunks_data["indices"], key=lambda x: int(x) if x.isdigit() else 0),
                'audio_indices': sorted(audio_data["indices"], key=lambda x: int(x) if x.isdigit() else 0)
            })
            consistent = False
        elif chunks_indices != audio_indices:
            # 索引不匹配
            mismatched_indices.append(story_index)
            missing_in_audio = chunks_indices - audio_indices
            missing_in_chunks = audio_indices - chunks_indices
            check_details['mismatched_indices_stories'].append({
                'story': story_index,
                'count': chunks_num,
                'missing_in_audio': sorted(missing_in_audio, key=lambda x: int(x) if x.isdigit() else 0),
                'missing_in_chunks': sorted(missing_in_chunks, key=lambda x: int(x) if x.isdigit() else 0),
                'chunks_indices': sorted(chunks_data["indices"], key=lambda x: int(x) if x.isdigit() else 0),
                'audio_indices': sorted(audio_data["indices"], key=lambda x: int(x) if x.isdigit() else 0)
            })
            consistent = False
        else:
            # 数量和索引都一致
            check_details['consistent_stories'].append({
                'story': story_index,
                'count': chunks_num,
                'indices': sorted(chunks_data["indices"], key=lambda x: int(x) if x.isdigit() else 0)
            })
    
    # 输出检查结果
    print(f"\n📊 一致性检查结果:")
    print(f"   总故事数: {len(all_stories)}")
    print(f"   有文本块: {len(chunks_info)} 个故事")
    print(f"   有音频文件: {len(audio_info)} 个故事")
    print(f"   完全一致: {len(check_details['consistent_stories'])} 个故事")
    
    if consistent:
        print(f"✅ 所有故事的文本块和音频文件数量和索引都完全一致！")
        print(f"📝 一致的故事: {', '.join([item['story'] for item in check_details['consistent_stories']])}")
        
        # 显示一些统计信息
        if check_details['consistent_stories']:
            total_files = sum(item['count'] for item in check_details['consistent_stories'])
            print(f"📊 共有 {total_files} 个文本块/音频文件对")
    else:
        print(f"❌ 发现不一致的故事！")
        
        if missing_chunks:
            print(f"   缺少文本块的故事: {', '.join(missing_chunks)}")
            for item in check_details['missing_chunks_stories']:
                indices_str = ', '.join(item['audio_indices']) if item['audio_indices'] else '无'
                print(f"     - 故事 {item['story']}: 只有 {item['audio_count']} 个音频文件 (索引: {indices_str})，缺少对应文本块")
        
        if missing_audio:
            print(f"   缺少音频文件的故事: {', '.join(missing_audio)}")
            for item in check_details['missing_audio_stories']:
                indices_str = ', '.join(item['chunks_indices']) if item['chunks_indices'] else '无'
                print(f"     - 故事 {item['story']}: 只有 {item['chunks_count']} 个文本块 (索引: {indices_str})，缺少对应音频文件")
        
        if mismatched_counts:
            print(f"   数量不匹配的故事: {', '.join(mismatched_counts)}")
            for item in check_details['mismatched_count_stories']:
                diff_str = f"多{item['difference']}个" if item['difference'] > 0 else f"少{abs(item['difference'])}个"
                chunks_indices_str = ', '.join(item['chunks_indices']) if item['chunks_indices'] else '无'
                audio_indices_str = ', '.join(item['audio_indices']) if item['audio_indices'] else '无'
                print(f"     - 故事 {item['story']}: 文本块 {item['chunks_count']} 个, 音频文件 {item['audio_count']} 个 (文本块{diff_str})")
                print(f"       文本块索引: {chunks_indices_str}")
                print(f"       音频文件索引: {audio_indices_str}")
        
        if mismatched_indices:
            print(f"   索引不匹配的故事: {', '.join(mismatched_indices)}")
            for item in check_details['mismatched_indices_stories']:
                print(f"     - 故事 {item['story']}: 文件数量相同 ({item['count']} 个) 但索引不匹配")
                if item['missing_in_audio']:
                    missing_audio_str = ', '.join(item['missing_in_audio'])
                    print(f"       缺少音频文件的索引: {missing_audio_str}")
                if item['missing_in_chunks']:
                    missing_chunks_str = ', '.join(item['missing_in_chunks'])
                    print(f"       缺少文本块的索引: {missing_chunks_str}")
                chunks_indices_str = ', '.join(item['chunks_indices']) if item['chunks_indices'] else '无'
                audio_indices_str = ', '.join(item['audio_indices']) if item['audio_indices'] else '无'
                print(f"       文本块索引: {chunks_indices_str}")
                print(f"       音频文件索引: {audio_indices_str}")
    
    return consistent, check_details


def load_asr_model():
    """加载ASR模型"""
    try:
        print(f"🤖 加载ASR模型: {ASR_MODEL_NAME}")
        print("⏳ 首次运行可能需要下载模型，请耐心等待...")
        
        asr_model = nemo_asr.models.ASRModel.from_pretrained(model_name=ASR_MODEL_NAME)
        print("✅ ASR模型加载成功")
        return asr_model
    except Exception as e:
        print(f"❌ ASR模型加载失败: {e}")
        return None


def get_audio_duration(audio_file: str) -> Optional[float]:
    """获取音频文件时长"""
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json", 
            "-show_format",
            audio_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            duration = float(data["format"]["duration"])
            return duration
        else:
            print(f"❌ 获取音频时长失败: {audio_file}")
            return None
    except Exception as e:
        print(f"❌ 获取音频时长出错: {e}")
        return None


def format_timestamp(seconds: float) -> str:
    """将秒数转换为SRT时间戳格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def create_srt_content(timestamps: List[Dict], srt_type: str = "word") -> str:
    """创建SRT字幕内容"""
    srt_lines = []
    
    for i, item in enumerate(timestamps, 1):
        start_time = format_timestamp(item['start'])
        end_time = format_timestamp(item['end'])
        
        if srt_type == "word":
            text = item['word']
        else:  # segment
            text = item['segment']
        
        srt_lines.append(f"{i}")
        srt_lines.append(f"{start_time} --> {end_time}")
        srt_lines.append(text)
        srt_lines.append("")  # 空行
    
    return "\n".join(srt_lines)


def save_srt_file(content: str, output_path: str) -> bool:
    """保存SRT文件"""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"❌ 保存SRT文件失败 {output_path}: {e}")
        return False


def transcribe_audio_clip(asr_model, audio_file: str, story_index: str, clip_index: str, force: bool = False) -> bool:
    """对单个音频片段进行ASR识别并保存字幕"""
    
    # 检查输出文件是否已存在
    word_srt_path = os.path.join(WORD_LEVEL_SRT_DIR, story_index, f"{clip_index}.srt")
    seg_srt_path = os.path.join(SEG_LEVEL_SRT_DIR, story_index, f"{clip_index}.srt")
    
    if not force and os.path.exists(word_srt_path) and os.path.exists(seg_srt_path):
        print(f"⏭️  跳过已存在的字幕: 故事 {story_index}, 片段 {clip_index}")
        return True
    
    try:
        print(f"🎤 ASR识别: 故事 {story_index}, 片段 {clip_index}")
        print(f"   音频文件: {audio_file}")
        
        # 执行ASR识别
        output = asr_model.transcribe([audio_file], timestamps=True)
        
        if not output or len(output) == 0:
            print(f"❌ ASR识别失败，无输出结果")
            return False
        
        result = output[0]
        
        # 获取时间戳
        word_timestamps = result.timestamp.get('word', [])
        segment_timestamps = result.timestamp.get('segment', [])
        
        print(f"   识别到 {len(word_timestamps)} 个词，{len(segment_timestamps)} 个片段")
        
        # 生成并保存 word level 字幕
        if word_timestamps:
            word_srt_content = create_srt_content(word_timestamps, "word")
            if save_srt_file(word_srt_content, word_srt_path):
                print(f"✅ Word level 字幕已保存: {word_srt_path}")
            else:
                return False
        
        # 生成并保存 segment level 字幕  
        if segment_timestamps:
            seg_srt_content = create_srt_content(segment_timestamps, "segment")
            if save_srt_file(seg_srt_content, seg_srt_path):
                print(f"✅ Segment level 字幕已保存: {seg_srt_path}")
            else:
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ ASR识别出错: {e}")
        return False


def parse_srt_file(srt_path: str) -> List[Dict]:
    """解析SRT文件，返回时间戳和文本信息"""
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        entries = []
        blocks = content.split('\n\n')
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                # 第1行：序号
                # 第2行：时间戳
                # 第3行及后续：文本
                timestamp_line = lines[1]
                text = '\n'.join(lines[2:])
                
                # 解析时间戳 "00:00:01,234 --> 00:00:02,567"
                if ' --> ' in timestamp_line:
                    start_str, end_str = timestamp_line.split(' --> ')
                    
                    def parse_timestamp(ts_str):
                        # "00:00:01,234" -> 1.234
                        time_part, millis_part = ts_str.split(',')
                        h, m, s = map(int, time_part.split(':'))
                        millis = int(millis_part)
                        return h * 3600 + m * 60 + s + millis / 1000
                    
                    start_time = parse_timestamp(start_str)
                    end_time = parse_timestamp(end_str)
                    
                    entries.append({
                        'start': start_time,
                        'end': end_time, 
                        'text': text
                    })
        
        return entries
        
    except Exception as e:
        print(f"❌ 解析SRT文件失败 {srt_path}: {e}")
        return []


def pad_srt_timestamps(entries: List[Dict], offset: float) -> List[Dict]:
    """给SRT条目的时间戳添加偏移量"""
    padded_entries = []
    
    for entry in entries:
        padded_entry = {
            'start': entry['start'] + offset,
            'end': entry['end'] + offset,
            'text': entry['text']
        }
        padded_entries.append(padded_entry)
    
    return padded_entries


def merge_srt_entries(all_entries: List[Dict]) -> str:
    """合并多个SRT条目为完整的SRT内容"""
    merged_lines = []
    
    for i, entry in enumerate(all_entries, 1):
        start_time = format_timestamp(entry['start'])
        end_time = format_timestamp(entry['end'])
        
        merged_lines.append(f"{i}")
        merged_lines.append(f"{start_time} --> {end_time}")
        merged_lines.append(entry['text'])
        merged_lines.append("")  # 空行
    
    return "\n".join(merged_lines)


def get_story_clips(input_dir: str) -> Dict[str, List[str]]:
    """获取所有故事的音频片段文件"""
    story_clips = {}
    
    if not os.path.exists(input_dir):
        print(f"❌ 输入目录不存在: {input_dir}")
        return story_clips
    
    # 遍历所有故事目录
    for story_dir in glob.glob(os.path.join(input_dir, "*")):
        if os.path.isdir(story_dir):
            story_index = os.path.basename(story_dir)
            
            # 排除隐藏目录
            if story_index.startswith("."):
                continue
            
            # 获取该故事的所有mp3文件
            mp3_files = glob.glob(os.path.join(story_dir, "*.mp3"))
            
            # 过滤和排序
            valid_clips = []
            for mp3_file in mp3_files:
                filename = os.path.basename(mp3_file)
                if not filename.startswith(".") and filename.endswith(".mp3"):
                    valid_clips.append(mp3_file)
            
            # 按片段索引排序
            def extract_clip_number(filepath):
                basename = os.path.basename(filepath)
                try:
                    return int(basename.split(".")[0])
                except:
                    return 0
            
            valid_clips.sort(key=extract_clip_number)
            
            if valid_clips:
                story_clips[story_index] = valid_clips
    
    return story_clips


def merge_story_subtitles(story_index: str, force: bool = False) -> bool:
    """合并单个故事的所有字幕片段"""
    
    print(f"🔗 合并故事 {story_index} 的字幕...")
    
    # 检查输出文件是否已存在
    word_output_path = os.path.join(MERGE_SRT_DIR, f"{story_index}_word.srt")
    seg_output_path = os.path.join(MERGE_SRT_DIR, f"{story_index}_segment.srt")
    
    if not force and os.path.exists(word_output_path) and os.path.exists(seg_output_path):
        print(f"⏭️  跳过已存在的合并字幕: 故事 {story_index}")
        return True
    
    try:
        # 获取该故事的所有片段
        story_word_dir = os.path.join(WORD_LEVEL_SRT_DIR, story_index)
        story_seg_dir = os.path.join(SEG_LEVEL_SRT_DIR, story_index)
        
        if not os.path.exists(story_word_dir) or not os.path.exists(story_seg_dir):
            print(f"❌ 故事 {story_index} 的字幕目录不存在")
            return False
        
        # 获取所有字幕文件并排序
        word_srt_files = glob.glob(os.path.join(story_word_dir, "*.srt"))
        seg_srt_files = glob.glob(os.path.join(story_seg_dir, "*.srt"))
        
        def extract_clip_number(filepath):
            basename = os.path.basename(filepath)
            try:
                return int(basename.split(".")[0])
            except:
                return 0
        
        word_srt_files.sort(key=extract_clip_number)
        seg_srt_files.sort(key=extract_clip_number)
        
        if not word_srt_files or not seg_srt_files:
            print(f"❌ 故事 {story_index} 没有找到字幕文件")
            return False
        
        print(f"   找到 {len(word_srt_files)} 个 word level 字幕文件")
        print(f"   找到 {len(seg_srt_files)} 个 segment level 字幕文件")
        
        # 处理 word level 字幕合并
        all_word_entries = []
        cumulative_offset = 0.0
        
        for i, srt_file in enumerate(word_srt_files):
            clip_index = os.path.basename(srt_file).split(".")[0]
            
            # 获取对应音频文件的时长
            audio_file = os.path.join(INPUT_DIR, story_index, f"{clip_index}.mp3")
            duration = get_audio_duration(audio_file)
            
            if duration is None:
                print(f"❌ 无法获取音频时长: {audio_file}")
                return False
            
            # 解析当前字幕文件
            entries = parse_srt_file(srt_file)
            if not entries:
                print(f"⚠️  字幕文件为空: {srt_file}")
                continue
            
            # 添加时间偏移
            if i > 0:  # 第一个文件不需要偏移
                padded_entries = pad_srt_timestamps(entries, cumulative_offset)
            else:
                padded_entries = entries
            
            all_word_entries.extend(padded_entries)
            
            # 累加偏移量
            cumulative_offset += duration
            
            print(f"   片段 {clip_index}: {len(entries)} 个词, 时长 {duration:.2f}s, 累计偏移 {cumulative_offset:.2f}s")
        
        # 处理 segment level 字幕合并
        all_seg_entries = []
        cumulative_offset = 0.0
        
        for i, srt_file in enumerate(seg_srt_files):
            clip_index = os.path.basename(srt_file).split(".")[0]
            
            # 获取对应音频文件的时长
            audio_file = os.path.join(INPUT_DIR, story_index, f"{clip_index}.mp3")
            duration = get_audio_duration(audio_file)
            
            if duration is None:
                print(f"❌ 无法获取音频时长: {audio_file}")
                return False
            
            # 解析当前字幕文件
            entries = parse_srt_file(srt_file)
            if not entries:
                continue
            
            # 添加时间偏移
            if i > 0:  # 第一个文件不需要偏移
                padded_entries = pad_srt_timestamps(entries, cumulative_offset)
            else:
                padded_entries = entries
            
            all_seg_entries.extend(padded_entries)
            
            # 累加偏移量
            cumulative_offset += duration
        
        # 生成合并后的SRT内容
        if all_word_entries:
            word_srt_content = merge_srt_entries(all_word_entries)
            if save_srt_file(word_srt_content, word_output_path):
                print(f"✅ Word level 合并字幕已保存: {word_output_path} ({len(all_word_entries)} 个词)")
        
        if all_seg_entries:
            seg_srt_content = merge_srt_entries(all_seg_entries)
            if save_srt_file(seg_srt_content, seg_output_path):
                print(f"✅ Segment level 合并字幕已保存: {seg_output_path} ({len(all_seg_entries)} 个片段)")
        
        return True
        
    except Exception as e:
        print(f"❌ 合并字幕出错: {e}")
        return False


def scan_existing_files(word_dir: str, seg_dir: str, merge_dir: str) -> Dict:
    """扫描已存在的字幕文件"""
    existing = {
        'clips': {},  # {story_index: {clip_index: True}}
        'merged': set()  # {story_index}
    }
    
    # 扫描 clip 级别的字幕
    for srt_dir, level in [(word_dir, 'word'), (seg_dir, 'segment')]:
        if os.path.exists(srt_dir):
            for story_dir in glob.glob(os.path.join(srt_dir, "*")):
                if os.path.isdir(story_dir):
                    story_index = os.path.basename(story_dir)
                    if story_index.startswith("."):
                        continue
                    
                    if story_index not in existing['clips']:
                        existing['clips'][story_index] = {}
                    
                    for srt_file in glob.glob(os.path.join(story_dir, "*.srt")):
                        clip_index = os.path.basename(srt_file).split(".")[0]
                        if clip_index not in existing['clips'][story_index]:
                            existing['clips'][story_index][clip_index] = {'word': False, 'segment': False}
                        existing['clips'][story_index][clip_index][level] = True
    
    # 扫描合并字幕
    if os.path.exists(merge_dir):
        for srt_file in glob.glob(os.path.join(merge_dir, "*_word.srt")):
            basename = os.path.basename(srt_file)
            story_index = basename.replace("_word.srt", "")
            
            # 检查对应的segment文件是否也存在
            seg_file = os.path.join(merge_dir, f"{story_index}_segment.srt")
            if os.path.exists(seg_file):
                existing['merged'].add(story_index)
    
    return existing


def save_progress_log(stats: Dict):
    """保存进度日志"""
    try:
        log_file = os.path.join(MERGE_SRT_DIR, "asr_progress.json")
        
        log_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            **stats
        }
        
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        print(f"📝 进度日志已保存: {log_file}")
        
    except Exception as e:
        print(f"⚠️  保存进度日志失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="ASR识别和字幕合并器 - 对mp3 clip进行ASR识别并合并字幕"
    )
    
    parser.add_argument("-f", "--force", action="store_true", help="强制重新处理，忽略已有文件")
    parser.add_argument("--start", type=int, help="指定开始处理的故事索引")
    parser.add_argument("--end", type=int, help="指定结束处理的故事索引")  
    parser.add_argument("--story", help="只处理指定的故事索引")
    parser.add_argument("--preview", action="store_true", help="预览模式，只显示会处理哪些文件")
    parser.add_argument("--theme", required=True, choices=SUPPORTED_THEMES, help=f"指定要处理的主题 ({', '.join(SUPPORTED_THEMES)})")
    parser.add_argument("--skip-consistency-check", action="store_true", help="跳过文本块和音频文件的一致性检查（慎用）")
    
    args = parser.parse_args()
    
    # 获取主题相关路径
    try:
        paths = get_theme_paths(args.theme)
        INPUT_DIR = paths["input_dir"]
        TEXT_CHUNKS_DIR = paths["text_chunks_dir"]
        WORD_LEVEL_SRT_DIR = paths["word_level_srt_dir"]
        SEG_LEVEL_SRT_DIR = paths["seg_level_srt_dir"]
        MERGE_SRT_DIR = paths["merge_srt_dir"]
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    print("🎤 ASR识别和字幕合并器")
    print("=" * 50)
    print(f"🎭 处理主题: {args.theme}")
    print(f"📁 输入目录: {INPUT_DIR}")
    print(f"📁 文本块目录: {TEXT_CHUNKS_DIR}")
    print(f"📁 Word level 输出: {WORD_LEVEL_SRT_DIR}")
    print(f"📁 Segment level 输出: {SEG_LEVEL_SRT_DIR}")
    print(f"📁 合并字幕输出: {MERGE_SRT_DIR}")
    
    # 安全检查：验证文本块和音频文件数量一致性
    valid_stories = set()  # 通过安全检查的故事集合
    
    if args.skip_consistency_check:
        print(f"\n⚠️  已跳过一致性检查（用户指定 --skip-consistency-check）")
        print(f"🚨 注意：可能会处理不完整的数据，请确保您知道在做什么")
        # 跳过检查时，假设所有故事都有效
        story_clips_temp = get_story_clips(args.input_dir)
        valid_stories = set(story_clips_temp.keys())
    else:
        print(f"\n🛡️  执行安全检查...")
        consistency_ok, check_details = check_chunks_audio_consistency(TEXT_CHUNKS_DIR, args.input_dir)
        
        # 提取通过检查的故事
        consistent_stories = [item['story'] for item in check_details['consistent_stories']]
        valid_stories = set(consistent_stories)
        
        if consistency_ok:
            print(f"✅ 安全检查通过：所有故事的文本块和音频文件数量都一致")
            print(f"📊 共有 {len(valid_stories)} 个故事可以进行ASR处理")
        else:
            print(f"\n⚠️  安全检查发现部分故事数据不一致")
            print(f"🔄 将跳过不一致的故事，只处理数据完整的故事")
            
            # 统计各种不一致情况的故事数量
            inconsistent_count = (len(check_details['missing_chunks_stories']) + 
                                len(check_details['missing_audio_stories']) + 
                                len(check_details['mismatched_count_stories']) + 
                                len(check_details['mismatched_indices_stories']))
            
            print(f"📊 故事状态统计:")
            print(f"   ✅ 数据一致可处理: {len(valid_stories)} 个故事")
            print(f"   ❌ 数据不一致跳过: {inconsistent_count} 个故事")
            
            if len(valid_stories) == 0:
                print(f"\n❌ 没有任何故事通过安全检查！")
                print(f"💡 请先确保以下操作完成且结果一致：")
                print(f"   1. chunk_stories.py 已正确分割所有故事")
                print(f"   2. synthesize_audio.py 已为所有文本块生成音频文件")
                print(f"   3. 两个目录中的文件数量完全匹配")
                print(f"\n⏹️  程序已停止，请修复数据不一致问题后再次运行")
                return
            
            # 详细输出跳过的故事信息
            print(f"\n📋 跳过的故事详情:")
            
            if check_details['missing_chunks_stories']:
                missing_chunks_stories = [item['story'] for item in check_details['missing_chunks_stories']]
                print(f"   缺少文本块 ({len(missing_chunks_stories)} 个): {', '.join(missing_chunks_stories)}")
            
            if check_details['missing_audio_stories']:
                missing_audio_stories = [item['story'] for item in check_details['missing_audio_stories']]
                print(f"   缺少音频文件 ({len(missing_audio_stories)} 个): {', '.join(missing_audio_stories)}")
            
            if check_details['mismatched_count_stories']:
                mismatched_count_stories = [item['story'] for item in check_details['mismatched_count_stories']]
                print(f"   文件数量不匹配 ({len(mismatched_count_stories)} 个): {', '.join(mismatched_count_stories)}")
            
            if check_details['mismatched_indices_stories']:
                mismatched_indices_stories = [item['story'] for item in check_details['mismatched_indices_stories']]
                print(f"   文件索引不匹配 ({len(mismatched_indices_stories)} 个): {', '.join(mismatched_indices_stories)}")
            
            if len(valid_stories) > 0:
                valid_stories_list = sorted(valid_stories, key=lambda x: int(x) if x.isdigit() else 0)
                print(f"\n✅ 将处理的故事 ({len(valid_stories)} 个): {', '.join(valid_stories_list[:10])}")
                if len(valid_stories) > 10:
                    print(f"    ... 还有 {len(valid_stories) - 10} 个故事")
                
                print(f"\n💡 提示：被跳过的故事可以在修复数据问题后重新运行此脚本进行处理")
    
    # 获取所有故事的音频片段
    print(f"\n🔍 扫描音频片段...")
    all_story_clips = get_story_clips(args.input_dir)
    
    if not all_story_clips:
        print("❌ 未找到任何音频片段文件")
        return
    
    # 只保留通过安全检查的故事
    story_clips = {}
    for story_index, clips in all_story_clips.items():
        if story_index in valid_stories:
            story_clips[story_index] = clips
    
    if not story_clips:
        print("❌ 没有通过安全检查的故事包含音频片段文件")
        return
    
    skipped_stories = set(all_story_clips.keys()) - set(story_clips.keys())
    print(f"📊 音频片段扫描结果:")
    print(f"   找到音频文件: {len(all_story_clips)} 个故事")
    print(f"   通过安全检查: {len(story_clips)} 个故事")
    if skipped_stories:
        skipped_list = sorted(skipped_stories, key=lambda x: int(x) if x.isdigit() else 0)
        print(f"   因安全检查跳过: {len(skipped_stories)} 个故事 ({', '.join(skipped_list[:5])}{'...' if len(skipped_list) > 5 else ''})")
    
    # 过滤指定故事
    if args.story:
        if args.story in story_clips:
            story_clips = {args.story: story_clips[args.story]}
            print(f"🎯 只处理故事: {args.story}")
        else:
            print(f"❌ 未找到指定的故事: {args.story}")
            return
    
    # 应用索引范围过滤
    if args.start is not None or args.end is not None:
        filtered_stories = {}
        for story_index, clips in story_clips.items():
            try:
                story_num = int(story_index)
                if args.start is not None and story_num < args.start:
                    continue
                if args.end is not None and story_num > args.end:
                    continue
                filtered_stories[story_index] = clips
            except ValueError:
                continue
        story_clips = filtered_stories
        print(f"🎯 范围过滤后剩余 {len(story_clips)} 个故事")
    
    if not story_clips:
        print("❌ 根据指定条件未找到匹配的故事")
        return
    
    # 扫描已存在的文件
    existing = scan_existing_files(WORD_LEVEL_SRT_DIR, SEG_LEVEL_SRT_DIR, MERGE_SRT_DIR)
    
    # 统计需要处理的任务
    clips_to_process = []
    stories_to_merge = []
    
    total_clips = 0
    for story_index, clips in story_clips.items():
        total_clips += len(clips)
        
        for clip_file in clips:
            clip_index = os.path.basename(clip_file).split(".")[0]
            
            # 检查是否需要处理ASR
            need_asr = args.force
            if not need_asr:
                existing_clips = existing['clips'].get(story_index, {})
                clip_status = existing_clips.get(clip_index, {'word': False, 'segment': False})
                if not (clip_status['word'] and clip_status['segment']):
                    need_asr = True
            
            if need_asr:
                clips_to_process.append((story_index, clip_index, clip_file))
        
        # 检查是否需要合并字幕
        if args.force or story_index not in existing['merged']:
            stories_to_merge.append(story_index)
    
    # 统计信息
    stats = {
        "total_stories_found": len(all_story_clips),
        "total_stories_valid": len(story_clips),
        "total_stories_skipped": len(all_story_clips) - len(story_clips),
        "total_clips": total_clips,
        "clips_to_process": len(clips_to_process),
        "stories_to_merge": len(stories_to_merge),
        "existing_clip_srts": sum(len(clips) for clips in existing['clips'].values()),
        "existing_merged_srts": len(existing['merged'])
    }
    
    print(f"\n📈 处理统计:")
    print(f"   扫描到故事: {stats['total_stories_found']}")
    print(f"   有效故事数: {stats['total_stories_valid']}")
    if stats['total_stories_skipped'] > 0:
        print(f"   跳过故事数: {stats['total_stories_skipped']} (数据不一致)")
    print(f"   总片段数: {stats['total_clips']}")
    print(f"   需ASR处理: {stats['clips_to_process']}")
    print(f"   需合并字幕: {stats['stories_to_merge']}")
    print(f"   已有片段字幕: {stats['existing_clip_srts']}")
    print(f"   已有合并字幕: {stats['existing_merged_srts']}")
    
    # 预览模式
    if args.preview:
        print(f"\n📋 预览模式 - 需要ASR处理的片段:")
        for i, (story_index, clip_index, clip_file) in enumerate(clips_to_process[:20], 1):
            print(f"  {i:3d}. 故事 {story_index}, 片段 {clip_index}")
            print(f"       文件: {clip_file}")
        
        if len(clips_to_process) > 20:
            print(f"       ... 还有 {len(clips_to_process) - 20} 个片段")
        
        print(f"\n📋 需要合并字幕的故事: {', '.join(stories_to_merge)}")
        return
    
    if stats['clips_to_process'] == 0 and stats['stories_to_merge'] == 0:
        print(f"\n🎉 所有任务都已完成！")
        return
    
    # 确保输出目录存在
    for output_dir in [WORD_LEVEL_SRT_DIR, SEG_LEVEL_SRT_DIR, MERGE_SRT_DIR]:
        os.makedirs(output_dir, exist_ok=True)
    
    # 开始处理
    session_stats = {
        "successful_asr": 0,
        "failed_asr": 0, 
        "successful_merge": 0,
        "failed_merge": 0
    }
    
    try:
        start_time = time.time()
        
        # 第一阶段：ASR识别
        if clips_to_process:
            print(f"\n🎤 第一阶段：ASR识别 ({len(clips_to_process)} 个片段)")
            
            # 加载ASR模型
            asr_model = load_asr_model()
            if asr_model is None:
                print("❌ ASR模型加载失败，无法继续")
                return
            
            with tqdm(total=len(clips_to_process), desc="ASR识别进度") as pbar:
                for i, (story_index, clip_index, clip_file) in enumerate(clips_to_process, 1):
                    print(f"\n--- 处理第 {i}/{len(clips_to_process)} 个片段 ---")
                    
                    success = transcribe_audio_clip(
                        asr_model, clip_file, story_index, clip_index, args.force
                    )
                    
                    if success:
                        session_stats["successful_asr"] += 1
                    else:
                        session_stats["failed_asr"] += 1
                    
                    pbar.update(1)
                    pbar.set_postfix({
                        "成功": session_stats["successful_asr"],
                        "失败": session_stats["failed_asr"]
                    })
        
        # 第二阶段：合并字幕
        if stories_to_merge:
            print(f"\n🔗 第二阶段：合并字幕 ({len(stories_to_merge)} 个故事)")
            
            with tqdm(total=len(stories_to_merge), desc="字幕合并进度") as pbar:
                for i, story_index in enumerate(sorted(stories_to_merge, key=int), 1):
                    print(f"\n--- 合并第 {i}/{len(stories_to_merge)} 个故事: {story_index} ---")
                    
                    success = merge_story_subtitles(story_index, args.force)
                    
                    if success:
                        session_stats["successful_merge"] += 1
                    else:
                        session_stats["failed_merge"] += 1
                    
                    pbar.update(1)
                    pbar.set_postfix({
                        "成功": session_stats["successful_merge"],
                        "失败": session_stats["failed_merge"]
                    })
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 更新统计并保存日志
        final_stats = {
            **stats,
            "session_successful_asr": session_stats["successful_asr"],
            "session_failed_asr": session_stats["failed_asr"],
            "session_successful_merge": session_stats["successful_merge"],
            "session_failed_merge": session_stats["failed_merge"],
            "total_time_seconds": total_time
        }
        
        save_progress_log(final_stats)
        
        # 结果统计
        print(f"\n=== 🎉 处理完成 ===")
        print(f"📊 故事处理统计:")
        print(f"   扫描到故事: {final_stats['total_stories_found']} 个")
        print(f"   处理的故事: {final_stats['total_stories_valid']} 个")
        if final_stats['total_stories_skipped'] > 0:
            print(f"   跳过的故事: {final_stats['total_stories_skipped']} 个 (数据不一致)")
        print(f"📊 任务执行统计:")
        print(f"   ✅ ASR识别成功: {session_stats['successful_asr']} 个片段")
        print(f"   ❌ ASR识别失败: {session_stats['failed_asr']} 个片段")
        print(f"   ✅ 字幕合并成功: {session_stats['successful_merge']} 个故事")
        print(f"   ❌ 字幕合并失败: {session_stats['failed_merge']} 个故事")
        print(f"⏱️  总耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")
        
        if session_stats["successful_asr"] > 0:
            avg_asr_time = total_time / (session_stats["successful_asr"] + session_stats["successful_merge"])
            print(f"📊 平均处理时间: {avg_asr_time:.1f} 秒/任务")
        
        total_successful = session_stats["successful_asr"] + session_stats["successful_merge"]
        total_failed = session_stats["failed_asr"] + session_stats["failed_merge"]
        total_processed = total_successful + total_failed
        
        if total_processed > 0:
            success_rate = total_successful / total_processed * 100
            print(f"📊 总体成功率: {success_rate:.1f}%")
        
        print(f"📁 字幕文件已保存到:")
        print(f"   Word level: {WORD_LEVEL_SRT_DIR}")
        print(f"   Segment level: {SEG_LEVEL_SRT_DIR}")
        print(f"   合并字幕: {MERGE_SRT_DIR}")
        
        if total_failed > 0:
            print(f"\n⚠️  有 {total_failed} 个任务处理失败，可以重新运行程序重试")
        else:
            print(f"\n🎉 所有有效故事的任务都处理完成！")
        
        if final_stats['total_stories_skipped'] > 0:
            print(f"\n💡 跳过了 {final_stats['total_stories_skipped']} 个数据不一致的故事")
            print(f"   修复这些故事的数据问题后，可以重新运行此脚本进行处理")
    
    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断了程序执行")
        print(f"📊 中断前的处理结果:")
        print(f"   ✅ ASR识别成功: {session_stats['successful_asr']} 个")
        print(f"   ❌ ASR识别失败: {session_stats['failed_asr']} 个")
        print(f"   ✅ 字幕合并成功: {session_stats['successful_merge']} 个")
        print(f"   ❌ 字幕合并失败: {session_stats['failed_merge']} 个")
        if stats['total_stories_skipped'] > 0:
            print(f"   ⏭️  跳过故事: {stats['total_stories_skipped']} 个 (数据不一致)")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        print(f"📊 错误前的处理结果:")
        print(f"   ✅ ASR识别成功: {session_stats['successful_asr']} 个")
        print(f"   ❌ ASR识别失败: {session_stats['failed_asr']} 个")
        print(f"   ✅ 字幕合并成功: {session_stats['successful_merge']} 个")
        print(f"   ❌ 字幕合并失败: {session_stats['failed_merge']} 个")
        if stats['total_stories_skipped'] > 0:
            print(f"   ⏭️  跳过故事: {stats['total_stories_skipped']} 个 (数据不一致)")


if __name__ == "__main__":
    main() 