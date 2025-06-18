#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ubuntu GPU 字幕处理问题诊断和修复工具

问题描述:
在Ubuntu系统使用GPU处理视频字幕时，长视频(一个多小时)的后面十多分钟字幕消失。
这个问题主要出现在thriller和fantasy主题的视频处理中。

可能的问题原因:
1. SRT字幕文件本身在时间戳上有问题或缺失
2. FFmpeg GPU编码器在处理长视频时的已知bug
3. GPU内存不足导致字幕滤镜失效
4. 字幕时间戳超出视频长度
5. NVENC编码器的B-frame处理问题
6. 字幕滤镜与GPU硬件解码的兼容性问题

修复方案:
1. 检查SRT文件完整性和时间戳
2. 使用CPU模式重新处理有问题的视频
3. 修复GPU编码参数，避免已知的NVENC问题
4. 分段处理长视频避免GPU内存问题
5. 使用更兼容的字幕处理方案

使用方法:
python fix_subtitle_issue.py --theme thriller --story 1 --diagnose
python fix_subtitle_issue.py --theme fantasy --story 2 --fix
python fix_subtitle_issue.py --theme thriller --batch-fix
"""

import os
import sys
import platform
import subprocess
import argparse
import time
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 确保只在Ubuntu系统运行
if platform.system() != "Linux":
    print("❌ 此修复脚本需要在Ubuntu系统上运行")
    sys.exit(1)

def get_paths(theme="thriller"):
    """获取主题相关路径"""
    return {
        "input_video_dir": f"/mnt/dhl/audio/{theme}/mp4_full_audio",
        "subtitle_dir": f"/mnt/dhl/audio/{theme}/srt_merge", 
        "output_dir": f"/mnt/dhl/audio/{theme}/mp4_with_subtitles",
        "font_dir": "audio_ficition/utils/font/en/",
    }

def check_srt_file_integrity(srt_path: str, video_path: str = None) -> Dict:
    """检查SRT文件的完整性和时间戳"""
    results = {
        "exists": False,
        "total_entries": 0,
        "max_timestamp": 0,
        "min_timestamp": 0,
        "video_duration": 0,
        "issues": [],
        "coverage": 0  # 字幕覆盖率
    }
    
    if not os.path.exists(srt_path):
        results["issues"].append("SRT文件不存在")
        return results
    
    results["exists"] = True
    
    try:
        # 获取视频时长
        if video_path and os.path.exists(video_path):
            cmd = [
                "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                results["video_duration"] = float(result.stdout.strip())
        
        # 解析SRT文件
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找所有时间戳
        timestamp_pattern = r'(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})'
        matches = re.findall(timestamp_pattern, content)
        
        if not matches:
            results["issues"].append("未找到有效的时间戳格式")
            return results
        
        results["total_entries"] = len(matches)
        
        # 转换时间戳为秒
        def timestamp_to_seconds(h, m, s, ms):
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
        
        timestamps = []
        for match in matches:
            start_time = timestamp_to_seconds(match[0], match[1], match[2], match[3])
            end_time = timestamp_to_seconds(match[4], match[5], match[6], match[7])
            timestamps.append((start_time, end_time))
        
        if timestamps:
            results["min_timestamp"] = min(t[0] for t in timestamps)
            results["max_timestamp"] = max(t[1] for t in timestamps)
            
            # 计算字幕覆盖率
            if results["video_duration"] > 0:
                results["coverage"] = (results["max_timestamp"] / results["video_duration"]) * 100
        
        # 检查时间戳连续性
        for i in range(1, len(timestamps)):
            gap = timestamps[i][0] - timestamps[i-1][1]
            if gap > 10:  # 超过10秒的空隙
                results["issues"].append(f"时间戳 {timestamps[i-1][1]:.1f}s 到 {timestamps[i][0]:.1f}s 之间有 {gap:.1f}s 空隙")
        
        # 检查是否有超出视频长度的字幕
        if results["video_duration"] > 0 and results["max_timestamp"] > results["video_duration"]:
            results["issues"].append(f"字幕时间戳({results['max_timestamp']:.1f}s)超出视频长度({results['video_duration']:.1f}s)")
        
        # 检查字幕是否过早结束
        if results["video_duration"] > 0:
            time_diff = results["video_duration"] - results["max_timestamp"]
            if time_diff > 600:  # 如果字幕比视频结束早10分钟以上
                results["issues"].append(f"字幕比视频提前 {time_diff:.1f}s ({time_diff/60:.1f}分钟) 结束")
    
    except Exception as e:
        results["issues"].append(f"解析SRT文件时出错: {str(e)}")
    
    return results

def diagnose_gpu_subtitle_issues(theme: str, story_index: str = None) -> Dict:
    """诊断GPU字幕处理问题"""
    paths = get_paths(theme)
    issues = []
    
    logger.info(f"🔍 开始诊断 {theme} 主题的GPU字幕问题...")
    
    # 检查基础路径
    for path_name, path_value in paths.items():
        if path_name != "font_dir" and not os.path.exists(path_value):
            issues.append(f"{path_name} 路径不存在: {path_value}")
    
    # 检查具体故事或所有故事
    stories_to_check = [story_index] if story_index else []
    if not story_index:
        # 获取所有视频文件
        video_files = []
        if os.path.exists(paths["input_video_dir"]):
            for f in os.listdir(paths["input_video_dir"]):
                if f.endswith('.mp4') and not f.startswith('.'):
                    story_idx = f.replace('.mp4', '')
                    stories_to_check.append(story_idx)
    
    story_issues = {}
    
    for story in stories_to_check:
        story_issues[story] = []
        
        # 检查文件存在性
        video_file = os.path.join(paths["input_video_dir"], f"{story}.mp4")
        subtitle_file_word = os.path.join(paths["subtitle_dir"], f"{story}_word.srt")
        subtitle_file_normal = os.path.join(paths["subtitle_dir"], f"{story}.srt") 
        output_file = os.path.join(paths["output_dir"], f"{story}.mp4")
        
        # 选择字幕文件
        subtitle_file = subtitle_file_word if os.path.exists(subtitle_file_word) else subtitle_file_normal
        
        if not os.path.exists(video_file):
            story_issues[story].append("视频文件不存在")
            continue
            
        if not os.path.exists(subtitle_file):
            story_issues[story].append("字幕文件不存在")
            continue
        
        # 检查SRT文件完整性
        srt_check = check_srt_file_integrity(subtitle_file, video_file)
        
        logger.info(f"📊 故事 {story} 字幕分析:")
        logger.info(f"   字幕条目数: {srt_check['total_entries']}")
        logger.info(f"   时间范围: {srt_check['min_timestamp']:.1f}s - {srt_check['max_timestamp']:.1f}s")
        logger.info(f"   视频时长: {srt_check['video_duration']:.1f}s")
        logger.info(f"   覆盖率: {srt_check['coverage']:.1f}%")
        
        if srt_check["issues"]:
            story_issues[story].extend(srt_check["issues"])
            logger.warning(f"❌ 故事 {story} 发现问题:")
            for issue in srt_check["issues"]:
                logger.warning(f"     - {issue}")
        else:
            logger.info(f"✅ 故事 {story} 字幕文件检查正常")
        
        # 检查输出文件是否已存在且有问题
        if os.path.exists(output_file):
            # 可以进一步检查输出视频的字幕是否正常
            story_issues[story].append("输出文件已存在，可能需要重新处理")
    
    return {
        "theme": theme,
        "general_issues": issues,
        "story_issues": story_issues,
        "paths": paths
    }

def fix_single_story_with_cpu(theme: str, story_index: str, force: bool = False) -> bool:
    """使用CPU模式修复单个故事的字幕问题"""
    paths = get_paths(theme)
    
    video_file = os.path.join(paths["input_video_dir"], f"{story_index}.mp4")
    subtitle_file_word = os.path.join(paths["subtitle_dir"], f"{story_index}_word.srt")
    subtitle_file_normal = os.path.join(paths["subtitle_dir"], f"{story_index}.srt")
    output_file = os.path.join(paths["output_dir"], f"{story_index}.mp4")
    
    # 选择字幕文件
    subtitle_file = subtitle_file_word if os.path.exists(subtitle_file_word) else subtitle_file_normal
    
    if not os.path.exists(video_file):
        logger.error(f"❌ 视频文件不存在: {video_file}")
        return False
        
    if not os.path.exists(subtitle_file):
        logger.error(f"❌ 字幕文件不存在: {subtitle_file}")
        return False
    
    if os.path.exists(output_file) and not force:
        logger.warning(f"⚠️  输出文件已存在: {output_file}")
        logger.warning("使用 --force 参数强制重新处理")
        return False
    
    logger.info(f"🔧 开始使用CPU模式修复故事 {story_index}")
    
    # 创建输出目录
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 构建ffmpeg命令 - 使用稳定的CPU模式
    cmd = [
        "ffmpeg",
        "-i", video_file,
        "-vf", f"subtitles={subtitle_file}:force_style='Fontname=Arial,FontSize=50,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BorderStyle=1,Outline=2,MarginV=20'",
        "-c:v", "libx264",
        "-preset", "medium",  # 平衡质量和速度
        "-crf", "23",  # 高质量编码
        "-c:a", "copy",
        "-y", output_file
    ]
    
    logger.info(f"执行命令: {' '.join(cmd)}")
    
    start_time = time.time()
    try:
        process = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        
        end_time = time.time()
        
        if process.returncode == 0:
            logger.info(f"✅ 成功修复故事 {story_index}，耗时 {end_time - start_time:.1f}秒")
            logger.info(f"输出文件: {output_file}")
            return True
        else:
            logger.error(f"❌ 修复失败: {process.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 执行过程中出错: {str(e)}")
        return False

def fix_with_improved_gpu_settings(theme: str, story_index: str, force: bool = False) -> bool:
    """使用改进的GPU设置修复字幕问题"""
    paths = get_paths(theme)
    
    video_file = os.path.join(paths["input_video_dir"], f"{story_index}.mp4")
    subtitle_file_word = os.path.join(paths["subtitle_dir"], f"{story_index}_word.srt")
    subtitle_file_normal = os.path.join(paths["subtitle_dir"], f"{story_index}.srt")
    output_file = os.path.join(paths["output_dir"], f"{story_index}_gpu_fixed.mp4")
    
    # 选择字幕文件
    subtitle_file = subtitle_file_word if os.path.exists(subtitle_file_word) else subtitle_file_normal
    
    if not os.path.exists(video_file):
        logger.error(f"❌ 视频文件不存在: {video_file}")
        return False
        
    if not os.path.exists(subtitle_file):
        logger.error(f"❌ 字幕文件不存在: {subtitle_file}")
        return False
    
    if os.path.exists(output_file) and not force:
        logger.warning(f"⚠️  输出文件已存在: {output_file}")
        return False
    
    logger.info(f"🚀 开始使用改进的GPU设置修复故事 {story_index}")
    
    # 创建输出目录
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 构建改进的GPU ffmpeg命令
    # 基于搜索结果，避免已知的NVENC问题
    cmd = [
        "ffmpeg",
        "-i", video_file,
        "-vf", f"subtitles={subtitle_file}:force_style='Fontname=Arial,FontSize=50,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BorderStyle=1,Outline=2,MarginV=20'",
        "-c:v", "h264_nvenc",
        "-preset", "slow",  # 使用慢预设确保稳定性
        "-b_ref_mode", "disabled",  # 关键：禁用B-frame引用模式，解决GTX 1650/1070等GPU的兼容性问题
        "-rc", "vbr",
        "-cq", "23",
        "-b:v", "3M",
        "-maxrate", "5M", 
        "-bufsize", "5M",
        "-c:a", "copy",
        "-y", output_file
    ]
    
    logger.info(f"执行命令: {' '.join(cmd)}")
    
    start_time = time.time()
    try:
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, 
            text=True
        )
        
        end_time = time.time()
        
        if process.returncode == 0:
            logger.info(f"✅ GPU修复成功 故事 {story_index}，耗时 {end_time - start_time:.1f}秒")
            logger.info(f"输出文件: {output_file}")
            return True
        else:
            logger.error(f"❌ GPU修复失败: {process.stderr}")
            logger.info("🔄 尝试回退到CPU模式...")
            return fix_single_story_with_cpu(theme, story_index, force)
            
    except Exception as e:
        logger.error(f"❌ 执行过程中出错: {str(e)}")
        return False

def batch_fix_issues(theme: str, method: str = "cpu", force: bool = False) -> Dict:
    """批量修复主题中的字幕问题"""
    logger.info(f"🔧 开始批量修复 {theme} 主题的字幕问题")
    
    # 先诊断问题
    diagnosis = diagnose_gpu_subtitle_issues(theme)
    
    results = {
        "theme": theme,
        "method": method,
        "total_stories": 0,
        "successful": 0,
        "failed": 0,
        "details": {}
    }
    
    # 处理有问题的故事
    for story, issues in diagnosis["story_issues"].items():
        if not issues or force:  # 如果没有问题或强制处理
            results["total_stories"] += 1
            
            if method == "cpu":
                success = fix_single_story_with_cpu(theme, story, force)
            elif method == "gpu":
                success = fix_with_improved_gpu_settings(theme, story, force)
            else:
                logger.error(f"❌ 未知的修复方法: {method}")
                continue
            
            if success:
                results["successful"] += 1
                results["details"][story] = "成功"
            else:
                results["failed"] += 1
                results["details"][story] = "失败"
        else:
            logger.warning(f"⚠️  跳过故事 {story}，原因: {issues}")
            results["details"][story] = f"跳过: {issues}"
    
    logger.info(f"📊 批量修复完成:")
    logger.info(f"   总计: {results['total_stories']}")
    logger.info(f"   成功: {results['successful']}")
    logger.info(f"   失败: {results['failed']}")
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Ubuntu GPU字幕处理问题诊断和修复工具")
    
    # 基本参数
    parser.add_argument("--theme", default="thriller", 
                       choices=["thriller", "fantasy", "horror", "scifi", "romance"],
                       help="指定主题 (默认: thriller)")
    parser.add_argument("--story", help="指定故事索引")
    
    # 操作模式
    parser.add_argument("--diagnose", action="store_true", help="诊断字幕问题")
    parser.add_argument("--fix", action="store_true", help="修复字幕问题")
    parser.add_argument("--batch-fix", action="store_true", help="批量修复")
    
    # 修复选项
    parser.add_argument("--method", default="cpu", choices=["cpu", "gpu"],
                       help="修复方法: cpu(稳定) 或 gpu(快速) (默认: cpu)")
    parser.add_argument("--force", action="store_true", help="强制重新处理已存在的文件")
    
    args = parser.parse_args()
    
    if not any([args.diagnose, args.fix, args.batch_fix]):
        parser.print_help()
        print("\n💡 请指定操作模式: --diagnose, --fix, 或 --batch-fix")
        return
    
    print("🛠️  Ubuntu GPU字幕处理问题修复工具")
    print("=" * 60)
    print(f"🎭 主题: {args.theme}")
    
    if args.diagnose:
        print("🔍 开始诊断...")
        diagnosis = diagnose_gpu_subtitle_issues(args.theme, args.story)
        
        print(f"\n📊 诊断结果 - {args.theme} 主题:")
        
        if diagnosis["general_issues"]:
            print("❌ 常规问题:")
            for issue in diagnosis["general_issues"]:
                print(f"   - {issue}")
        
        print(f"\n📝 故事问题分析:")
        for story, issues in diagnosis["story_issues"].items():
            if issues:
                print(f"❌ 故事 {story}:")
                for issue in issues:
                    print(f"     - {issue}")
            else:
                print(f"✅ 故事 {story}: 正常")
    
    elif args.fix:
        if not args.story:
            print("❌ 使用 --fix 时必须指定 --story 参数")
            return
        
        print(f"🔧 修复故事 {args.story} (方法: {args.method})")
        
        if args.method == "cpu":
            success = fix_single_story_with_cpu(args.theme, args.story, args.force)
        else:
            success = fix_with_improved_gpu_settings(args.theme, args.story, args.force)
        
        if success:
            print(f"✅ 故事 {args.story} 修复成功")
        else:
            print(f"❌ 故事 {args.story} 修复失败")
    
    elif args.batch_fix:
        print(f"🔧 批量修复 (方法: {args.method})")
        results = batch_fix_issues(args.theme, args.method, args.force)
        
        print(f"\n📊 批量修复结果:")
        print(f"   主题: {results['theme']}")
        print(f"   方法: {results['method']}")
        print(f"   成功: {results['successful']}/{results['total_stories']}")
        print(f"   失败: {results['failed']}")
        
        if results['failed'] > 0:
            print("\n❌ 失败的故事:")
            for story, status in results['details'].items():
                if "失败" in status:
                    print(f"   - 故事 {story}: {status}")

if __name__ == "__main__":
    main() 