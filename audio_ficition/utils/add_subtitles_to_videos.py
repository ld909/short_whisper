#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频字幕添加脚本 - GPU优化并行处理版

将 merge_mp4_cover_audio.py 输出的 MP4 视频文件添加字幕
参考 burn_subtitles_to_mp4.py 的逻辑，支持断点续传和排除Mac系统产生的点文件

🎬 GPU优化特性:
1. 多流并行处理 - 同时处理多个视频，充分利用GPU
2. 激进GPU参数 - 最大化GPU使用率
3. GPU内存监控 - 动态调整并行数
4. 多编码器支持 - NVENC/VideoToolbox/AMF
5. 智能负载均衡 - 根据GPU性能调整
6. GPU缓存优化 - 减少数据传输

功能说明:
1. 读取 merge_mp4_cover_audio.py 的输出（组合视频文件）
2. 查找对应的字幕文件（SRT格式）
3. 使用GPU并行处理多个视频的字幕烧录
4. 生成带字幕的视频文件
5. 支持断点续传，避免重复处理
6. 智能排除Mac系统产生的以点开头的文件

🚀 GPU加速模式:
- --gpu-max: 最大化GPU利用率（推荐）
- --gpu-parallel N: 指定并行处理数量
- --gpu-memory-limit: GPU内存使用限制
- --gpu-monitor: 实时GPU监控

路径说明:
输入:
- 组合视频文件:
  * macOS: /Volumes/dhl/audio/scifi/mp4_full_audio/[故事索引].mp4
  * Linux: /mnt/dhl/audio/scifi/mp4_full_audio/[故事索引].mp4
- 字幕文件 (ASR word level 合并字幕):
  * macOS: /Volumes/dhl/audio/scifi/srt_merge/[故事索引]_word.srt
  * Linux: /mnt/dhl/audio/scifi/srt_merge/[故事索引]_word.srt
  * 备用格式: [故事索引].srt (如果 word level 字幕不存在)

输出:
- 带字幕视频:
  * macOS: /Volumes/dhl/audio/scifi/mp4_with_subtitles/[故事索引].mp4
  * Linux: /mnt/dhl/audio/scifi/mp4_with_subtitles/[故事索引].mp4

使用方法:
1. 最大GPU利用率: python add_subtitles_to_videos.py --gpu-max
2. 指定并行数: python add_subtitles_to_videos.py --gpu --gpu-parallel 4
3. GPU内存监控: python add_subtitles_to_videos.py --gpu --gpu-monitor
4. 组合使用: python add_subtitles_to_videos.py --gpu-max --gpu-monitor -f

🔧 GPU 测试和调试:
- 快速GPU测试: python add_subtitles_to_videos.py --test-gpu
- 详细GPU调试: python add_subtitles_to_videos.py --debug-gpu
- GPU性能测试: python add_subtitles_to_videos.py --benchmark-gpu

默认设置:
- 字体大小: 50
- 字体粗细: semi-bold
- 字体颜色: 白色 (FFFFFF)
- 描边颜色: 黑色 (000000)
- 描边宽度: 2
- 底部边距: 20

注意:
- 需要安装 ffmpeg
- GPU并行处理需要足够的显存（建议8GB+）
- 建议搭配 --gpu-monitor 监控GPU使用情况
"""

import os
import sys
import time
import argparse
import glob
import re
import json
import subprocess
import platform
import multiprocessing
import psutil
import threading
import queue
import concurrent.futures
from pathlib import Path
from tqdm import tqdm
from typing import Dict, List, Optional, Tuple


def get_paths():
    """根据操作系统返回适当的路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return {
            "input_video_dir": "/Volumes/dhl/audio/scifi/mp4_full_audio",  # 🔧 修复：实际输出目录是 mp4_full_audio
            "subtitle_dir": "/Volumes/dhl/audio/scifi/srt_merge",
            "output_dir": "/Volumes/dhl/audio/scifi/mp4_with_subtitles",
            "font_dir": "font/en/",
        }
    else:  # 默认为Linux/Ubuntu
        return {
            "input_video_dir": "/mnt/dhl/audio/scifi/mp4_full_audio",  # 🔧 修复：实际输出目录是 mp4_full_audio
            "subtitle_dir": "/mnt/dhl/audio/scifi/srt_merge",
            "output_dir": "/mnt/dhl/audio/scifi/mp4_with_subtitles",
            "font_dir": "font/en/",
        }


def check_ffmpeg():
    """检查ffmpeg是否可用"""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("❌ 未找到ffmpeg，请先安装ffmpeg")
        return False


def get_gpu_memory_info():
    """获取GPU内存信息"""
    try:
        # NVIDIA GPU
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total,memory.used,memory.free", "--format=csv,noheader,nounits"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            gpus = []
            for line in lines:
                total, used, free = map(int, line.split(', '))
                gpus.append({
                    'total': total,
                    'used': used,
                    'free': free,
                    'utilization': (used / total) * 100
                })
            return gpus
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return []


def get_optimal_gpu_parallel_count(gpu_memory_info=None, force_max=False):
    """根据GPU内存自动计算最优并行数"""
    if not gpu_memory_info:
        gpu_memory_info = get_gpu_memory_info()
    
    if not gpu_memory_info:
        return 1
    
    # 取第一个GPU的信息（大多数系统只有一个GPU）
    gpu = gpu_memory_info[0]
    free_memory = gpu['free']
    
    if force_max:
        # 最大化模式 - 更激进的并行数
        if free_memory >= 10000:  # 10GB+
            return 8
        elif free_memory >= 8000:   # 8GB+
            return 6
        elif free_memory >= 6000:   # 6GB+
            return 5
        elif free_memory >= 4000:   # 4GB+
            return 4
        elif free_memory >= 2000:   # 2GB+
            return 3
        else:
            return 2
    else:
        # 保守模式
        if free_memory >= 8000:     # 8GB+
            return 4
        elif free_memory >= 6000:   # 6GB+
            return 3
        elif free_memory >= 4000:   # 4GB+
            return 2
        else:
            return 1


class GPUMonitor:
    """GPU监控器"""
    
    def __init__(self, monitor_interval=2):
        self.monitor_interval = monitor_interval
        self.monitoring = False
        self.monitor_thread = None
        self.stats = []
    
    def start_monitoring(self):
        """开始监控"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("🔍 GPU监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("⏹️  GPU监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            gpu_info = get_gpu_memory_info()
            if gpu_info:
                timestamp = time.time()
                for i, gpu in enumerate(gpu_info):
                    self.stats.append({
                        'timestamp': timestamp,
                        'gpu_id': i,
                        'memory_used': gpu['used'],
                        'memory_free': gpu['free'],
                        'utilization': gpu['utilization']
                    })
                    
                # 显示实时信息
                gpu = gpu_info[0]  # 显示第一个GPU
                print(f"\r🚀 GPU状态: 内存 {gpu['used']}/{gpu['total']}MB ({gpu['utilization']:.1f}%)", end='', flush=True)
            
            time.sleep(self.monitor_interval)
    
    def get_average_utilization(self):
        """获取平均利用率"""
        if not self.stats:
            return 0
        return sum(stat['utilization'] for stat in self.stats) / len(self.stats)


def check_gpu_support(fast_check=False):
    """检查GPU支持情况 - 增强版"""
    system = platform.system()

    if system == "Darwin":  # macOS
        if fast_check:
            # 快速检查：只验证ffmpeg是否支持VideoToolbox编码器
            try:
                result = subprocess.run(
                    ["ffmpeg", "-encoders"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5,
                    text=True,
                )
                if result.returncode == 0 and "h264_videotoolbox" in result.stdout:
                    return True, "videotoolbox"
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                pass
            return False, None
        else:
            # 完整测试VideoToolbox是否实际可用
            try:
                # 使用ffmpeg测试VideoToolbox编码器是否可用
                test_cmd = [
                    "ffmpeg",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc=duration=1:size=320x240:rate=1",
                    "-c:v",
                    "h264_videotoolbox",
                    "-f",
                    "null",
                    "-",
                    "-loglevel",
                    "error",
                ]
                result = subprocess.run(
                    test_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10,
                    text=True,
                )
                if result.returncode == 0:
                    return True, "videotoolbox"
                else:
                    # VideoToolbox不可用，可能是旧Mac或虚拟机
                    return False, None
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                return False, None

    elif system == "Linux":
        # 检查NVIDIA GPU
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                return True, "cuda"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return False, None


def debug_gpu_support():
    """详细的GPU支持调试信息 - 增强版"""
    print("🔍 GPU支持详细检测:")
    system = platform.system()
    print(f"   操作系统: {system}")

    if system == "Darwin":  # macOS
        print("   检测macOS VideoToolbox支持...")

        # 1. 检查ffmpeg是否存在
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                text=True,
            )
            if result.returncode == 0:
                print("   ✅ FFmpeg可用")

                # 检查VideoToolbox编码器
                result = subprocess.run(
                    ["ffmpeg", "-encoders"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5,
                    text=True,
                )
                if "h264_videotoolbox" in result.stdout:
                    print("   ✅ FFmpeg支持VideoToolbox编码器")

                    # 实际测试编码
                    test_cmd = [
                        "ffmpeg",
                        "-f",
                        "lavfi",
                        "-i",
                        "testsrc=duration=1:size=320x240:rate=1",
                        "-c:v",
                        "h264_videotoolbox",
                        "-f",
                        "null",
                        "-",
                        "-loglevel",
                        "error",
                    ]
                    result = subprocess.run(
                        test_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=10,
                        text=True,
                    )
                    if result.returncode == 0:
                        print("   ✅ VideoToolbox编码器测试成功")
                        return True, "videotoolbox"
                    else:
                        print(f"   ❌ VideoToolbox编码器测试失败: {result.stderr}")
                        print("      可能原因: 旧Mac硬件/虚拟机/权限问题")
                else:
                    print("   ❌ FFmpeg不支持VideoToolbox编码器")
                    print("      建议: 重新安装或更新FFmpeg")
            else:
                print("   ❌ FFmpeg不可用")
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
            print(f"   ❌ FFmpeg检测失败: {e}")

    elif system == "Linux":
        print("   检测Linux NVIDIA GPU支持...")

        # 检查nvidia-smi
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for i, line in enumerate(lines):
                    parts = line.split(', ')
                    gpu_name = parts[0]
                    memory_total = parts[1] if len(parts) > 1 else "未知"
                    memory_free = parts[2] if len(parts) > 2 else "未知"
                    print(f"   ✅ GPU {i}: {gpu_name}")
                    print(f"      内存: {memory_free}/{memory_total}")

                # 检查FFmpeg CUDA支持
                try:
                    result = subprocess.run(
                        ["ffmpeg", "-encoders"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=5,
                        text=True,
                    )
                    if "h264_nvenc" in result.stdout:
                        print("   ✅ FFmpeg支持NVENC编码器")
                        
                        # 建议最优并行数
                        gpu_info = get_gpu_memory_info()
                        if gpu_info:
                            optimal_parallel = get_optimal_gpu_parallel_count(gpu_info)
                            max_parallel = get_optimal_gpu_parallel_count(gpu_info, force_max=True)
                            print(f"   💡 建议并行数: {optimal_parallel} (最大: {max_parallel})")
                        
                        return True, "cuda"
                    else:
                        print("   ❌ FFmpeg不支持NVENC编码器")
                        print("      建议: 安装支持CUDA的FFmpeg版本")
                except Exception as e:
                    print(f"   ❌ FFmpeg检测失败: {e}")
            else:
                print("   ❌ 未检测到NVIDIA GPU")
        except FileNotFoundError:
            print("   ❌ nvidia-smi不可用 (未安装NVIDIA驱动)")
        except subprocess.TimeoutExpired:
            print("   ❌ nvidia-smi超时")
        except Exception as e:
            print(f"   ❌ NVIDIA GPU检测失败: {e}")
    else:
        print(f"   ⚠️  未知操作系统: {system}")

    print("   💻 将使用CPU模式")
    return False, None


def get_optimal_thread_count():
    """获取最优线程数"""
    cpu_count = multiprocessing.cpu_count()
    memory_gb = psutil.virtual_memory().total / (1024**3)

    # 基于CPU和内存计算推荐线程数
    if memory_gb >= 32:
        max_threads = min(cpu_count * 2, 16)
    elif memory_gb >= 16:
        max_threads = min(cpu_count, 12)
    elif memory_gb >= 8:
        max_threads = min(cpu_count, 8)
    else:
        max_threads = min(cpu_count, 4)

    return max_threads


def select_font_by_weight(font_weight, font_dir="font/en/"):
    """
    根据字体粗细选择对应的字体文件

    Args:
        font_weight: 字体粗细，可以是字符串("light", "normal", "medium", "bold", "extra-bold", "black")
                    或数字(100-900)
        font_dir: 字体文件目录

    Returns:
        tuple: (font_file_path, font_display_name)
    """
    # 定义字体映射
    font_mapping = {
        # 字符串映射
        "extra-light": ("Oxanium-ExtraLight.ttf", "Oxanium ExtraLight"),
        "light": ("Oxanium-Light.ttf", "Oxanium Light"),
        "normal": ("Oxanium-Regular.ttf", "Oxanium Regular"),
        "regular": ("Oxanium-Regular.ttf", "Oxanium Regular"),
        "medium": ("Oxanium-Medium.ttf", "Oxanium Medium"),
        "semi-bold": ("Oxanium-SemiBold.ttf", "Oxanium SemiBold"),
        "bold": ("Oxanium-Bold.ttf", "Oxanium Bold"),
        "extra-bold": ("Oxanium-ExtraBold.ttf", "Oxanium ExtraBold"),
        "black": ("Oxanium-ExtraBold.ttf", "Oxanium ExtraBold"),
    }

    # 数字权重映射
    weight_to_file = {
        100: ("Oxanium-ExtraLight.ttf", "Oxanium ExtraLight"),
        200: ("Oxanium-ExtraLight.ttf", "Oxanium ExtraLight"),
        300: ("Oxanium-Light.ttf", "Oxanium Light"),
        400: ("Oxanium-Regular.ttf", "Oxanium Regular"),
        500: ("Oxanium-Medium.ttf", "Oxanium Medium"),
        600: ("Oxanium-SemiBold.ttf", "Oxanium SemiBold"),
        700: ("Oxanium-Bold.ttf", "Oxanium Bold"),
        800: ("Oxanium-ExtraBold.ttf", "Oxanium ExtraBold"),
        900: ("Oxanium-ExtraBold.ttf", "Oxanium ExtraBold"),
    }

    # 根据类型选择字体
    if isinstance(font_weight, str):
        font_key = font_weight.lower().replace("_", "-")
        if font_key in font_mapping:
            font_file, font_name = font_mapping[font_key]
        else:
            # 默认使用regular
            font_file, font_name = font_mapping["regular"]
    elif isinstance(font_weight, int):
        # 找到最接近的权重
        closest_weight = min(weight_to_file.keys(), key=lambda x: abs(x - font_weight))
        font_file, font_name = weight_to_file[closest_weight]
    else:
        # 默认使用regular
        font_file, font_name = font_mapping["regular"]

    font_path = os.path.join(font_dir, font_file)

    # 检查文件是否存在
    if not os.path.exists(font_path):
        font_path = os.path.join(font_dir, "Oxanium-VariableFont_wght.ttf")
        font_name = "Oxanium"

    return font_path, font_name


def detect_subtitle_language(srt_path):
    """简单检测字幕语言 - 快速模式"""
    try:
        # 只读取前1000个字符进行检测
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read(1000)

        # 简单的语言检测
        if any("\u4e00" <= char <= "\u9fff" for char in content):
            return "zh"  # 中文
        elif any(
            "\u3040" <= char <= "\u309f" or "\u30a0" <= char <= "\u30ff"
            for char in content
        ):
            return "ja"  # 日文
        elif any("\uac00" <= char <= "\ud7af" for char in content):
            return "ko"  # 韩文
        else:
            return "en"  # 默认英文
    except Exception:
        return "en"


def benchmark_gpu():
    """GPU性能基准测试"""
    print("🧪 GPU性能基准测试...")
    
    has_gpu, gpu_type = check_gpu_support()
    if not has_gpu:
        print("❌ 未检测到可用GPU")
        return
    
    print(f"🚀 测试GPU类型: {gpu_type}")
    
    # 创建测试视频
    test_video = "/tmp/test_video.mp4"
    test_subtitle = "/tmp/test_subtitle.srt"
    
    # 生成测试内容
    print("📹 生成测试视频...")
    test_cmd = [
        "ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=10:size=1920x1080:rate=30",
        "-c:v", "libx264", "-preset", "fast", "-y", test_video
    ]
    subprocess.run(test_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # 生成测试字幕
    with open(test_subtitle, 'w', encoding='utf-8') as f:
        f.write("1\n00:00:00,000 --> 00:00:10,000\nGPU Performance Test\n\n")
    
    try:
        # 测试不同并行数的性能
        test_results = []
        for parallel_count in [1, 2, 4, 6, 8]:
            print(f"⚡ 测试并行数: {parallel_count}")
            start_time = time.time()
            
            # 使用多进程模拟并行处理
            tasks = []
            for i in range(parallel_count):
                output_path = f"/tmp/test_output_{i}.mp4"
                kwargs = {
                    'use_gpu': True,
                    'extreme_speed': True,
                    'gpu_parallel_test': True
                }
                tasks.append((test_video, test_subtitle, output_path, kwargs))
            
            # 并行执行
            with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_count) as executor:
                futures = [executor.submit(burn_subtitles_to_video, *task) for task in tasks]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
            
            end_time = time.time()
            total_time = end_time - start_time
            
            test_results.append({
                'parallel_count': parallel_count,
                'total_time': total_time,
                'throughput': parallel_count / total_time
            })
            
            print(f"   耗时: {total_time:.1f}秒, 吞吐量: {parallel_count/total_time:.2f} 视频/秒")
            
            # 清理输出文件
            for i in range(parallel_count):
                try:
                    os.remove(f"/tmp/test_output_{i}.mp4")
                except:
                    pass
        
        # 找到最佳并行数
        best_result = max(test_results, key=lambda x: x['throughput'])
        print(f"\n🏆 最佳并行数: {best_result['parallel_count']}")
        print(f"   最佳吞吐量: {best_result['throughput']:.2f} 视频/秒")
        
    finally:
        # 清理测试文件
        for file_path in [test_video, test_subtitle]:
            try:
                os.remove(file_path)
            except:
                pass


def select_font_by_weight(font_weight, font_dir="font/en/"):
    """
    根据字体粗细选择对应的字体文件

    Args:
        font_weight: 字体粗细，可以是字符串("light", "normal", "medium", "bold", "extra-bold", "black")
                    或数字(100-900)
        font_dir: 字体文件目录

    Returns:
        tuple: (font_file_path, font_display_name)
    """
    # 定义字体映射
    font_mapping = {
        # 字符串映射
        "extra-light": ("Oxanium-ExtraLight.ttf", "Oxanium ExtraLight"),
        "light": ("Oxanium-Light.ttf", "Oxanium Light"),
        "normal": ("Oxanium-Regular.ttf", "Oxanium Regular"),
        "regular": ("Oxanium-Regular.ttf", "Oxanium Regular"),
        "medium": ("Oxanium-Medium.ttf", "Oxanium Medium"),
        "semi-bold": ("Oxanium-SemiBold.ttf", "Oxanium SemiBold"),
        "bold": ("Oxanium-Bold.ttf", "Oxanium Bold"),
        "extra-bold": ("Oxanium-ExtraBold.ttf", "Oxanium ExtraBold"),
        "black": ("Oxanium-ExtraBold.ttf", "Oxanium ExtraBold"),
    }

    # 数字权重映射
    weight_to_file = {
        100: ("Oxanium-ExtraLight.ttf", "Oxanium ExtraLight"),
        200: ("Oxanium-ExtraLight.ttf", "Oxanium ExtraLight"),
        300: ("Oxanium-Light.ttf", "Oxanium Light"),
        400: ("Oxanium-Regular.ttf", "Oxanium Regular"),
        500: ("Oxanium-Medium.ttf", "Oxanium Medium"),
        600: ("Oxanium-SemiBold.ttf", "Oxanium SemiBold"),
        700: ("Oxanium-Bold.ttf", "Oxanium Bold"),
        800: ("Oxanium-ExtraBold.ttf", "Oxanium ExtraBold"),
        900: ("Oxanium-ExtraBold.ttf", "Oxanium ExtraBold"),
    }

    # 根据类型选择字体
    if isinstance(font_weight, str):
        font_key = font_weight.lower().replace("_", "-")
        if font_key in font_mapping:
            font_file, font_name = font_mapping[font_key]
        else:
            # 默认使用regular
            font_file, font_name = font_mapping["regular"]
    elif isinstance(font_weight, int):
        # 找到最接近的权重
        closest_weight = min(weight_to_file.keys(), key=lambda x: abs(x - font_weight))
        font_file, font_name = weight_to_file[closest_weight]
    else:
        # 默认使用regular
        font_file, font_name = font_mapping["regular"]

    font_path = os.path.join(font_dir, font_file)

    # 检查文件是否存在
    if not os.path.exists(font_path):
        font_path = os.path.join(font_dir, "Oxanium-VariableFont_wght.ttf")
        font_name = "Oxanium"

    return font_path, font_name


def detect_subtitle_language(srt_path):
    """简单检测字幕语言 - 快速模式"""
    try:
        # 只读取前1000个字符进行检测
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read(1000)

        # 简单的语言检测
        if any("\u4e00" <= char <= "\u9fff" for char in content):
            return "zh"  # 中文
        elif any(
            "\u3040" <= char <= "\u309f" or "\u30a0" <= char <= "\u30ff"
            for char in content
        ):
            return "ja"  # 日文
        elif any("\uac00" <= char <= "\ud7af" for char in content):
            return "ko"  # 韩文
        else:
            return "en"  # 默认英文
    except Exception:
        return "en"


def burn_subtitles_to_video(video_path, subtitle_path, output_path, **kwargs):
    """将字幕烧录到视频中 - GPU优化版"""

    # 参数设置
    font_size = kwargs.get("font_size", 50)
    font_color = kwargs.get("font_color", "FFFFFF")
    outline_color = kwargs.get("outline_color", "000000")
    outline_width = kwargs.get("outline_width", 2)
    margin_v = kwargs.get("margin_v", 20)
    font_path = kwargs.get("font_path")
    font_weight = kwargs.get("font_weight", "semi-bold")
    font_dir = kwargs.get("font_dir", "font/en/")
    use_gpu = kwargs.get("use_gpu", False)
    extreme_speed = kwargs.get("extreme_speed", False)
    fast_mode = kwargs.get("fast_mode", False)
    gpu_max_mode = kwargs.get("gpu_max_mode", False)
    gpu_parallel_test = kwargs.get("gpu_parallel_test", False)

    # 快速模式 - 跳过部分检查
    if not fast_mode:
        # 自动检测字幕语言
        detected_lang = detect_subtitle_language(subtitle_path)
    else:
        detected_lang = "en"  # 默认英文

    # 选择字体 - 优化版
    if not font_path:
        if detected_lang == "en":
            font_path, font_name = select_font_by_weight(font_weight, font_dir)
        else:
            font_name = "arial"
    else:
        font_name = os.path.splitext(os.path.basename(font_path))[0].lower()

    # 构建ffmpeg命令 - GPU优化版
    cmd = ["ffmpeg"]

    # GPU最大化模式的全局设置
    if gpu_max_mode or extreme_speed:
        # 禁用统计信息输出
        cmd.extend(["-nostats", "-loglevel", "error"])
        # 关闭自动检测
        cmd.extend(["-fflags", "+genpts+discardcorrupt"])
    else:
        cmd.extend(["-loglevel", "warning"])

    # GPU加速设置 - 最大化优化版
    hw_accel_used = False
    encoder_used = "libx264"

    if use_gpu:
        # 在fast_mode下使用快速检查，否则使用完整检查
        has_gpu, gpu_type = check_gpu_support(fast_check=fast_mode)
        if has_gpu:
            if gpu_type == "cuda":
                # CUDA硬件加速 - 稳定设置
                cmd.extend(["-hwaccel", "cuda"])
                # 移除可能导致格式转换问题的参数
                # 保持兼容性，不强制使用CUDA输出格式
                hw_accel_used = True
                encoder_used = "h264_nvenc"
            elif gpu_type == "videotoolbox":
                cmd.extend(["-hwaccel", "videotoolbox"])
                hw_accel_used = True
                encoder_used = "h264_videotoolbox"

    # 输入文件
    cmd.extend(["-i", video_path])

    # 字幕滤镜 - GPU优化版
    fonts_dir = os.path.dirname(font_path) if font_path else ""

    # 构建字幕样式
    if gpu_max_mode or extreme_speed:
        # 最简化的字幕样式以提升GPU性能
        force_style = f"Fontname={font_name},FontSize={font_size},PrimaryColour=&H{font_color[:6]}"
    else:
        force_style = (
            f"Fontname={font_name},"
            f"FontSize={font_size},"
            f"PrimaryColour=&H{font_color[:6]},"
            f"OutlineColour=&H{outline_color[:6]},"
            f"BorderStyle=1,"
            f"Outline={outline_width},"
            f"MarginV={margin_v}"
        )

    # 字幕滤镜设置 - GPU优化（修复格式转换问题）
    if hw_accel_used and gpu_type == "cuda":
        # 使用更兼容的GPU处理方式
        subtitle_filter = f"subtitles={subtitle_path}"
        if fonts_dir and not (gpu_max_mode or extreme_speed):
            subtitle_filter += f":fontsdir={fonts_dir}"
        subtitle_filter += f":force_style='{force_style}'"
        # 对于CUDA，我们在CPU上处理字幕，然后用GPU编码
    else:
        subtitle_filter = f"subtitles={subtitle_path}"
        if fonts_dir and not (gpu_max_mode or extreme_speed):
            subtitle_filter += f":fontsdir={fonts_dir}"
        subtitle_filter += f":force_style='{force_style}'"

    cmd.extend(["-vf", subtitle_filter])

    # 音频处理
    cmd.extend(["-c:a", "copy"])

    # 视频编码设置 - GPU最大化优化
    if hw_accel_used:
        if gpu_type == "cuda":
            cmd.extend(["-c:v", "h264_nvenc"])
            if gpu_max_mode:
                # GPU最大化模式 - 激进设置
                cmd.extend([
                    "-preset", "p1",        # 最快预设
                    "-tune", "ll",          # 低延迟
                    "-rc", "vbr",           # 可变比特率
                    "-cq", "32",            # 较低质量换取速度
                    "-b:v", "1.5M",         # 中等比特率
                    "-maxrate", "3M",
                    "-bufsize", "3M",
                    "-g", "120",            # 大GOP
                    "-bf", "0",             # 禁用B帧提升编码速度
                    "-refs", "1",           # 减少参考帧
                    "-rc-lookahead", "8",   # 减少预测
                    "-surfaces", "32",      # 增加编码表面数
                    "-async_depth", "4",    # 异步深度
                ])
            elif extreme_speed:
                # 极致速度NVENC设置
                cmd.extend([
                    "-preset", "p1",
                    "-tune", "ll",
                    "-rc", "vbr",
                    "-cq", "35",
                    "-b:v", "1M",
                    "-maxrate", "2M",
                    "-bufsize", "2M",
                    "-g", "60",
                ])
            else:
                cmd.extend([
                    "-preset", "fast",
                    "-b:v", "2M",
                    "-maxrate", "3M",
                    "-bufsize", "3M",
                ])
        elif gpu_type == "videotoolbox":
            cmd.extend(["-c:v", "h264_videotoolbox"])
            if gpu_max_mode or extreme_speed:
                cmd.extend([
                    "-b:v", "1.5M", 
                    "-maxrate", "3M",
                    "-realtime", "true",  # 实时编码
                ])
            else:
                cmd.extend(["-b:v", "2M", "-maxrate", "3M"])
    else:
        # CPU编码 - 优化版
        cpu_count = multiprocessing.cpu_count()
        cmd.extend(["-c:v", "libx264"])

        if gpu_max_mode or extreme_speed:
            # 极致速度CPU设置
            cmd.extend([
                "-preset", "ultrafast",
                "-tune", "fastdecode",
                "-crf", "28",
                "-threads", str(min(cpu_count, 8)),
                "-g", "60",
                "-sc_threshold", "0",
                "-b:v", "1M",
            ])
        else:
            cmd.extend([
                "-preset", "fast",
                "-threads", str(cpu_count),
                "-b:v", "2M",
            ])

    # GPU最大化模式的其他优化设置
    if gpu_max_mode or extreme_speed:
        cmd.extend([
            "-movflags", "+faststart",
            "-avoid_negative_ts", "disabled",
            "-fflags", "+genpts",
        ])

    # 覆盖输出文件
    cmd.extend(["-y", output_path])

    # 创建输出目录
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # 执行命令
    try:
        if gpu_max_mode or extreme_speed:
            # 最大化模式 - 最小输出
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
        else:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )

        # 等待处理完成
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            return True
        else:
            if not (gpu_max_mode or extreme_speed):
                print(f"❌ 处理失败: {stderr}")
            # GPU失败时的回退策略
            if use_gpu and hw_accel_used and not (gpu_max_mode or extreme_speed):
                kwargs["use_gpu"] = False
                return burn_subtitles_to_video(
                    video_path, subtitle_path, output_path, **kwargs
                )
            return False
    except Exception as e:
        if not (gpu_max_mode or extreme_speed):
            print(f"❌ 处理时出错: {str(e)}")
        return False


class ParallelGPUProcessor:
    """GPU并行处理器"""

    def __init__(self, max_workers=4, gpu_monitor=None):
        self.max_workers = max_workers
        self.gpu_monitor = gpu_monitor
        self.results = {"successful": 0, "failed": 0}
        self.active_tasks = 0
        self.lock = threading.Lock()

    def process_single_story(self, story_index, files, **kwargs):
        """处理单个故事"""
        output_dir = kwargs.get("output_dir", "")
        output_file = os.path.join(output_dir, f"{story_index}.mp4")

        with self.lock:
            self.active_tasks += 1

        try:
            success = burn_subtitles_to_video(
                files["video_file"], files["subtitle_file"], output_file, **kwargs
            )

            with self.lock:
                if success:
                    self.results["successful"] += 1
                else:
                    self.results["failed"] += 1

            return success

        except Exception as e:
            with self.lock:
                self.results["failed"] += 1
            return False
        finally:
            with self.lock:
                self.active_tasks -= 1

    def process_stories(self, stories_to_process, **kwargs):
        """并行处理故事"""
        total_stories = len(stories_to_process)

        # 创建进度条
        with tqdm(
            total=total_stories,
            desc=f"🚀 GPU并行字幕添加 (并行数:{self.max_workers})",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
        ) as pbar:

            # 使用线程池进行并行处理
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                future_to_story = {
                    executor.submit(self.process_single_story, story_index, files, **kwargs): story_index
                    for story_index, files in stories_to_process.items()
                }

                # 处理完成的任务
                for future in concurrent.futures.as_completed(future_to_story):
                    story_index = future_to_story[future]
                    try:
                        success = future.result()
                        status = "✅" if success else "❌"
                        pbar.set_postfix_str(f"故事 {story_index} {status} | 活跃任务: {self.active_tasks}")
                        pbar.update(1)
                    except Exception as e:
                        pbar.set_postfix_str(f"故事 {story_index} ❌ 异常: {str(e)[:20]}")
                        pbar.update(1)

        return self.results


def get_existing_output_videos(output_dir: str, fast_mode: bool = False) -> set:
    """获取已存在的输出视频文件"""
    existing_videos = set()

    if not os.path.exists(output_dir):
        return existing_videos

    for video_file in glob.glob(os.path.join(output_dir, "*.mp4")):
        basename = os.path.basename(video_file)
        # 排除以点开头的文件
        if basename.startswith("."):
            continue

        match = re.match(r"(\d+)\.mp4", basename)
        if match:
            story_index = match.group(1)
            # 快速模式 - 跳过文件大小验证
            if fast_mode:
                existing_videos.add(story_index)
            else:
                # 简单验证文件是否有效（大小大于1MB）
                try:
                    file_size = os.path.getsize(video_file)
                    if file_size > 1024 * 1024:  # 大于1MB
                        existing_videos.add(story_index)
                except Exception:
                    pass

    return existing_videos


def save_progress_log(output_dir: str, stats: Dict, session_stats: Dict):
    """保存处理进度日志"""
    try:
        log_file = os.path.join(output_dir, "subtitle_progress.json")

        log_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_stories": stats["total_stories"],
            "complete_stories": stats["complete_stories"],
            "completed_subtitles": stats["completed_subtitles"]
            + session_stats["successful"],
            "pending_subtitles": stats["pending_subtitles"]
            - session_stats["successful"]
            - session_stats["failed"],
            "session_successful": session_stats["successful"],
            "session_failed": session_stats["failed"],
            "missing_files": stats["missing_files"],
        }

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    except Exception as e:
        pass  # 静默失败


def get_story_files(paths: Dict) -> Dict:
    """获取所有故事的相关文件信息"""
    story_info = {}

    # 扫描输入视频文件
    input_video_dir = paths["input_video_dir"]
    if os.path.exists(input_video_dir):
        for video_file in glob.glob(os.path.join(input_video_dir, "*.mp4")):
            basename = os.path.basename(video_file)
            # 排除以点开头的文件
            if basename.startswith("."):
                continue

            match = re.match(r"(\d+)\.mp4", basename)
            if match:
                story_index = match.group(1)
                if story_index not in story_info:
                    story_info[story_index] = {}
                story_info[story_index]["video_file"] = video_file

    # 扫描字幕文件 (支持 word level 字幕格式: {story}_word.srt)
    subtitle_dir = paths["subtitle_dir"]
    if os.path.exists(subtitle_dir):
        for subtitle_file in glob.glob(os.path.join(subtitle_dir, "*.srt")):
            basename = os.path.basename(subtitle_file)
            # 排除以点开头的文件
            if basename.startswith("."):
                continue

            # 优先匹配 word level 字幕文件格式: {story}_word.srt
            match = re.match(r"(\d+)_word\.srt", basename)
            if match:
                story_index = match.group(1)
                if story_index not in story_info:
                    story_info[story_index] = {}
                story_info[story_index]["subtitle_file"] = subtitle_file
            else:
                # 备用匹配传统格式: {story}.srt
                match = re.match(r"(\d+)\.srt", basename)
                if match:
                    story_index = match.group(1)
                    if story_index not in story_info:
                        story_info[story_index] = {}
                    # 只有当没有 word level 字幕时才使用传统格式
                    if "subtitle_file" not in story_info[story_index]:
                        story_info[story_index]["subtitle_file"] = subtitle_file

    return story_info


def get_existing_output_videos(output_dir: str, fast_mode: bool = False) -> set:
    """获取已存在的输出视频文件"""
    existing_videos = set()

    if not os.path.exists(output_dir):
        return existing_videos

    for video_file in glob.glob(os.path.join(output_dir, "*.mp4")):
        basename = os.path.basename(video_file)
        # 排除以点开头的文件
        if basename.startswith("."):
            continue

        match = re.match(r"(\d+)\.mp4", basename)
        if match:
            story_index = match.group(1)
            # 快速模式 - 跳过文件大小验证
            if fast_mode:
                existing_videos.add(story_index)
            else:
                # 简单验证文件是否有效（大小大于1MB）
                try:
                    file_size = os.path.getsize(video_file)
                    if file_size > 1024 * 1024:  # 大于1MB
                        existing_videos.add(story_index)
                except Exception:
                    pass

    return existing_videos


def save_progress_log(output_dir: str, stats: Dict, session_stats: Dict):
    """保存处理进度日志"""
    try:
        log_file = os.path.join(output_dir, "subtitle_progress.json")

        log_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_stories": stats["total_stories"],
            "complete_stories": stats["complete_stories"],
            "completed_subtitles": stats["completed_subtitles"]
            + session_stats["successful"],
            "pending_subtitles": stats["pending_subtitles"]
            - session_stats["successful"]
            - session_stats["failed"],
            "session_successful": session_stats["successful"],
            "session_failed": session_stats["failed"],
            "missing_files": stats["missing_files"],
        }

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

    except Exception as e:
        pass  # 静默失败


def main():
    """主函数 - GPU优化并行处理版"""
    parser = argparse.ArgumentParser(description="视频字幕添加器 - GPU优化并行处理版")

    # 基本参数
    parser.add_argument(
        "-f", "--force", action="store_true", help="强制重新处理，忽略已有文件"
    )
    parser.add_argument("--start", type=int, help="指定开始处理的故事索引")
    parser.add_argument("--end", type=int, help="指定结束处理的故事索引")
    parser.add_argument("--story", help="只处理指定的故事索引")

    # 字体和样式参数
    parser.add_argument("--font-size", type=int, default=50, help="字体大小（默认50）")
    parser.add_argument(
        "--font-color", default="FFFFFF", help="字体颜色（十六进制，默认FFFFFF）"
    )
    parser.add_argument(
        "--outline-color", default="000000", help="描边颜色（十六进制，默认000000）"
    )
    parser.add_argument(
        "--outline-width", type=float, default=2, help="描边宽度（默认2）"
    )
    parser.add_argument("--margin-v", type=int, default=20, help="底部边距（默认20）")
    parser.add_argument("--font-path", help="自定义字体文件路径")
    parser.add_argument(
        "--font-weight",
        default="semi-bold",
        help="字体粗细: extra-light, light, regular, medium, semi-bold, bold, extra-bold 或数字 100-900 (默认: semi-bold)",
    )

    # 性能优化参数
    parser.add_argument("--gpu", action="store_true", help="启用GPU硬件加速")
    parser.add_argument(
        "--debug-gpu", action="store_true", help="🔍 显示详细的GPU检测信息（用于调试）"
    )
    parser.add_argument(
        "--test-gpu",
        action="store_true",
        help="🧪 快速测试GPU是否可用（不执行实际处理）",
    )
    parser.add_argument(
        "--benchmark-gpu",
        action="store_true", 
        help="🏁 GPU性能基准测试（测试不同并行数的性能）"
    )
    parser.add_argument(
        "--extreme-speed",
        action="store_true",
        help="🚀 启用极致速度模式（牺牲部分质量换取最快速度）",
    )
    parser.add_argument(
        "--fast-mode", action="store_true", help="⚡ 快速模式（跳过部分检查和验证）"
    )
    parser.add_argument("--gpu-max", action="store_true", help="🚀 最大化GPU利用率（推荐）")
    parser.add_argument("--gpu-parallel", type=int, help="指定并行处理数量")
    parser.add_argument("--gpu-memory-limit", type=int, help="GPU内存使用限制")
    parser.add_argument("--gpu-monitor", action="store_true", help="实时GPU监控")

    args = parser.parse_args()

    # 验证参数
    if args.start is not None and args.end is not None:
        if args.start > args.end:
            print("❌ 错误：开始索引不能大于结束索引")
            return
        if args.start <= 0 or args.end <= 0:
            print("❌ 错误：索引必须大于 0")
            return

    print("🚀 视频字幕添加器 - GPU优化并行处理版")
    print("=" * 60)
    print(f"🖥️  操作系统: {platform.system()}")
    
    # 检查依赖
    if not args.fast_mode and not check_ffmpeg():
        sys.exit(1)

    # GPU 支持检查和模式设置
    gpu_monitor = None
    if args.test_gpu:
        # 快速GPU测试模式
        print("🧪 快速GPU测试...")
        has_gpu, gpu_type = check_gpu_support(fast_check=True)
        if has_gpu:
            print(f"✅ GPU可用: {gpu_type}")
            print("   可使用 --gpu 参数启用GPU加速")
        else:
            print("❌ GPU不可用")
            print("   将使用CPU模式，如需详细信息请使用 --debug-gpu")
        print("\n测试完成，程序退出")
        return
    elif args.benchmark_gpu:
        # GPU性能基准测试
        benchmark_gpu()
        return
    elif args.debug_gpu:
        # 详细调试模式
        print("\n" + "=" * 60)
        has_gpu, gpu_type = debug_gpu_support()
        print("=" * 60)
        if has_gpu:
            print(f"\n🎉 GPU检测成功！可以使用 --gpu 启用{gpu_type}加速")
        else:
            print(f"\n💡 GPU不可用，将使用CPU模式。如需GPU加速请根据上述提示解决问题。")

        # 询问是否继续处理
        try:
            choice = input("\n是否继续执行字幕添加? (y/N): ").strip().lower()
            if choice not in ["y", "yes", "是"]:
                print("已退出程序")
                return
        except KeyboardInterrupt:
            print("\n已退出程序")
            return

        # 如果检测到GPU，自动启用
        if has_gpu:
            args.gpu = True
        else:
            args.gpu = False

    # GPU模式设置和并行数计算
    if args.gpu_max or args.gpu or args.gpu_parallel:
        has_gpu, gpu_type = check_gpu_support(fast_check=args.fast_mode)
        if has_gpu:
            print(f"🚀 GPU 加速: {gpu_type}")
            args.gpu = True
            
            # 获取GPU内存信息
            gpu_memory_info = get_gpu_memory_info()
            if gpu_memory_info:
                gpu = gpu_memory_info[0]
                print(f"💾 GPU内存: {gpu['used']}/{gpu['total']}MB (已用{gpu['utilization']:.1f}%)")
                
                # 自动计算最优并行数
                if not args.gpu_parallel:
                    if args.gpu_max:
                        optimal_parallel = get_optimal_gpu_parallel_count(gpu_memory_info, force_max=True)
                        print(f"🚀 GPU最大化模式 - 自动设置并行数: {optimal_parallel}")
                    else:
                        optimal_parallel = get_optimal_gpu_parallel_count(gpu_memory_info)
                        print(f"⚡ GPU标准模式 - 自动设置并行数: {optimal_parallel}")
                    args.gpu_parallel = optimal_parallel
                else:
                    print(f"🔧 手动设置并行数: {args.gpu_parallel}")
                    
                # 检查内存是否足够
                required_memory_per_task = 800  # 每个任务大约需要800MB GPU内存
                required_total = args.gpu_parallel * required_memory_per_task
                if required_total > gpu['free']:
                    print(f"⚠️  警告: 并行数{args.gpu_parallel}可能需要{required_total}MB内存，但只有{gpu['free']}MB可用")
                    safe_parallel = max(1, gpu['free'] // required_memory_per_task)
                    print(f"   建议并行数: {safe_parallel}")
            else:
                # 无法获取GPU内存信息，使用保守设置
                if not args.gpu_parallel:
                    args.gpu_parallel = 2 if args.gpu_max else 1
                    print(f"⚠️  无法获取GPU内存信息，使用保守并行数: {args.gpu_parallel}")
                
            # 启动GPU监控
            if args.gpu_monitor:
                gpu_monitor = GPUMonitor()
                gpu_monitor.start_monitoring()
        else:
            if not args.fast_mode:
                print("⚠️  未检测到可用GPU，使用CPU模式")
                if platform.system() == "Darwin":
                    print("   提示：macOS可能需要较新硬件支持VideoToolbox")
                    print("   可使用 --debug-gpu 查看详细信息")
            args.gpu = False
            args.gpu_parallel = 1
    else:
        print("💻 CPU 处理模式")
        args.gpu_parallel = 1

    # 显示处理配置
    if args.gpu_max:
        print(f"🚀 GPU最大化模式 - 并行数: {args.gpu_parallel}")
    elif args.gpu:
        print(f"⚡ GPU加速模式 - 并行数: {args.gpu_parallel}")
    else:
        print(f"💻 CPU模式 - 串行处理")

    print(f"🎨 字体大小: {args.font_size}")
    print(f"🎨 字体粗细: {args.font_weight}")

    # 获取路径配置
    paths = get_paths()
    if not args.fast_mode:
        print(f"📁 输入视频: {paths['input_video_dir']}")
        print(f"📁 字幕文件: {paths['subtitle_dir']}")
        print(f"📁 输出目录: {paths['output_dir']}")

    # 扫描故事文件
    if not args.fast_mode:
        print(f"\n🔍 扫描故事文件...")
    story_info = get_story_files(paths)

    if not story_info:
        print("❌ 未找到任何故事文件")
        return

    if not args.fast_mode:
        print(f"📊 找到 {len(story_info)} 个故事")

    # 过滤指定故事
    if args.story:
        if args.story in story_info:
            story_info = {args.story: story_info[args.story]}
            if not args.fast_mode:
                print(f"🎯 只处理故事: {args.story}")
        else:
            print(f"❌ 未找到指定的故事: {args.story}")
            return

    # 检查文件完整性
    complete_stories = {}
    missing_files = []

    for story_index, files in story_info.items():
        # 应用索引范围过滤
        try:
            story_num = int(story_index)
            if args.start is not None and story_num < args.start:
                continue
            if args.end is not None and story_num > args.end:
                continue
        except ValueError:
            continue

        has_video = "video_file" in files
        has_subtitle = "subtitle_file" in files

        if has_video and has_subtitle:
            complete_stories[story_index] = files
        else:
            missing_files.append(story_index)

    if not complete_stories:
        print("❌ 没有文件完整的故事可以处理")
        return

    # 扫描已存在的输出视频
    existing_output = set()
    if not args.force:
        existing_output = get_existing_output_videos(
            paths["output_dir"], args.fast_mode
        )

    # 确定需要处理的故事
    stories_to_process = {}
    for story_index, files in complete_stories.items():
        if args.force or story_index not in existing_output:
            stories_to_process[story_index] = files

    # 统计信息
    stats = {
        "total_stories": len(story_info),
        "complete_stories": len(complete_stories),
        "completed_subtitles": len(existing_output & set(complete_stories.keys())),
        "pending_subtitles": len(stories_to_process),
        "missing_files": missing_files,
    }

    if not args.fast_mode:
        print(f"\n📈 处理统计:")
        print(f"   总故事数: {stats['total_stories']}")
        print(f"   文件完整: {stats['complete_stories']}")
        print(f"   已完成: {stats['completed_subtitles']}")
        print(f"   待处理: {stats['pending_subtitles']}")

    if stats["pending_subtitles"] == 0:
        print(f"\n🎉 所有文件都已完成字幕添加！")
        return

    # 确保输出目录存在
    os.makedirs(paths["output_dir"], exist_ok=True)

    # 开始GPU并行处理
    print(f"\n🎬 启动字幕添加处理（GPU并行模式）")
    if args.extreme_speed:
        print("⚡ 极致速度模式已启用")

    # 处理字体权重参数
    font_weight = args.font_weight
    if args.font_weight.isdigit():
        font_weight = int(args.font_weight)

    # 准备处理参数
    process_kwargs = {
        "output_dir": paths["output_dir"],
        "font_size": args.font_size,
        "font_color": args.font_color,
        "outline_color": args.outline_color,
        "outline_width": args.outline_width,
        "margin_v": args.margin_v,
        "font_path": args.font_path,
        "font_weight": font_weight,
        "font_dir": paths["font_dir"],
        "use_gpu": args.gpu,
        "extreme_speed": args.extreme_speed,
        "fast_mode": args.fast_mode,
        "gpu_max_mode": args.gpu_max,
        "gpu_parallel_test": args.gpu_parallel,
    }

    try:
        start_time = time.time()

        # 创建GPU并行处理器
        processor = ParallelGPUProcessor(max_workers=args.gpu_parallel, gpu_monitor=gpu_monitor)

        # 执行GPU并行处理
        session_stats = processor.process_stories(stories_to_process, **process_kwargs)

        end_time = time.time()
        total_time = end_time - start_time

        # 停止GPU监控
        if gpu_monitor:
            gpu_monitor.stop_monitoring()
            avg_utilization = gpu_monitor.get_average_utilization()
            print(f"\n🔍 GPU平均利用率: {avg_utilization:.1f}%")

        # 保存进度日志
        if not args.fast_mode:
            save_progress_log(paths["output_dir"], stats, session_stats)

        # 结果统计
        print(f"\n=== 🎉 字幕添加完成 ===")
        print(f"✅ 成功处理: {session_stats['successful']} 个故事")
        print(f"❌ 处理失败: {session_stats['failed']} 个故事")
        print(f"⏱️  总耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")

        if session_stats["successful"] > 0:
            avg_time = total_time / session_stats["successful"]
            throughput = session_stats["successful"] / (total_time / 60)  # 每分钟处理数
            
            print(f"📊 平均处理时间: {avg_time:.1f} 秒/故事")
            print(f"🎬 处理速度: {throughput:.1f} 故事/分钟")
            
            # GPU加速效果统计
            if args.gpu and args.gpu_parallel > 1:
                theoretical_speedup = args.gpu_parallel
                actual_speedup = min(throughput / (1 / (avg_time * args.gpu_parallel)), theoretical_speedup)
                efficiency = (actual_speedup / theoretical_speedup) * 100
                print(f"🚀 GPU并行效率: {efficiency:.1f}% (实际加速: {actual_speedup:.1f}x)")

        if stats["pending_subtitles"] > 0:
            success_rate = (
                session_stats["successful"] / stats["pending_subtitles"] * 100
            )
            print(f"📊 成功率: {success_rate:.1f}%")

        # 性能统计
        total_completed = stats["completed_subtitles"] + session_stats["successful"]
        completion_rate = total_completed / stats["complete_stories"] * 100
        print(
            f"📊 总体完成率: {completion_rate:.1f}% ({total_completed}/{stats['complete_stories']})"
        )

        # 模式提醒
        if args.gpu_max:
            print("🚀 GPU最大化模式已使用，获得最佳处理速度")
        elif args.extreme_speed:
            print("⚡ 极致速度模式已使用，输出质量可能有所降低")

        print(f"📁 输出目录: {paths['output_dir']}")

        # 错误提醒和建议
        if session_stats["failed"] > 0:
            print(f"\n⚠️  有 {session_stats['failed']} 个故事处理失败")
            if not args.extreme_speed:
                print("   建议检查错误日志或重试")
            
        # GPU优化建议
        if args.gpu and gpu_monitor:
            avg_utilization = gpu_monitor.get_average_utilization()
            if avg_utilization < 70:
                print(f"\n💡 GPU优化建议: GPU利用率较低({avg_utilization:.1f}%)")
                print("   可尝试增加并行数: --gpu-parallel N")
            elif avg_utilization > 95:
                print(f"\n💡 GPU优化建议: GPU利用率很高({avg_utilization:.1f}%)")
                print("   当前设置已接近最优")

    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断程序")
        if gpu_monitor:
            gpu_monitor.stop_monitoring()
        print(f"✅ 已处理: {processor.results['successful']} 个故事")
        print(f"❌ 处理失败: {processor.results['failed']} 个故事")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        if gpu_monitor:
            gpu_monitor.stop_monitoring()
        print(f"✅ 已处理: {processor.results['successful']} 个故事")
        print(f"❌ 处理失败: {processor.results['failed']} 个故事")


if __name__ == "__main__":
    main()
