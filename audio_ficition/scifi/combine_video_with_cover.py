#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频封面组合脚本
将现有的MP4视频与高清封面图片组合，生成新的视频文件

功能说明:
1. 读取 upscale_cover_images.py 的输出（高清封面图片）
2. 遍历现有的MP4文件，排除以点开头的文件
3. 生成新视频：原MP4 + 静态封面图片
4. 新视频时长与对应的音频文件时长一致（可比音频长0.5秒）
5. 智能处理分辨率差异，最小化形变
6. 支持断点续传

路径说明:
输入:
- 高清封面图片: 
  * macOS: /Volumes/dhl/audio/scifi/cover_img_large/[故事索引].png
  * Linux: /media/dhl/audio/scifi/cover_img_large/[故事索引].png
- 原始MP4视频:
  * macOS: /Volumes/dhl/audio/scifi/mp4_upscaled/[故事索引].mp4
  * Linux: /media/dhl/audio/scifi/mp4_upscaled/[故事索引].mp4
- 音频文件:
  * macOS: /Volumes/dhl/audio/scifi/mp3_merge/[故事索引]/story.mp3
  * Linux: /media/dhl/audio/scifi/mp3_merge/[故事索引]/story.mp3

输出:
- 组合视频: /mnt/dhl/audio/scifi/mp4_full_silent/[故事索引].mp4

使用方法:
1. 基本使用: python combine_video_with_cover.py
2. 强制重新处理: python combine_video_with_cover.py -f
3. 指定故事索引范围: python combine_video_with_cover.py --start 1 --end 10
4. 只处理指定故事: python combine_video_with_cover.py --story 5
5. 16:9模式输出（推荐YouTube）: python combine_video_with_cover.py --16-9
6. 快速模式（最大速度）: python combine_video_with_cover.py --16-9 --fast
7. 组合使用: python combine_video_with_cover.py --16-9 --fast -f --start 1 --end 10

16:9模式特点:
- 自动选择最佳16:9分辨率（4K/1440p/1080p/720p）
- 智能裁剪策略，最大化保持画面清晰度
- 优先采用裁剪而非填充黑边，减少画质损失
- 完美适配YouTube等视频平台

性能优化特点:
- 自动检测硬件加速（NVIDIA/Intel/AMD）
- 智能编码参数优化，平衡速度与质量
- 快速模式可提升3-5倍处理速度
- 多线程并行处理，充分利用CPU资源

注意:
- 需要安装 ffmpeg
- 脚本会自动处理分辨率差异，采用最佳缩放策略
- 支持断点续传，中断后可从上次停止的位置继续处理
- 自动排除以点开头的meta文件（如.DS_Store等）
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
from pathlib import Path
from tqdm import tqdm
from typing import Dict, List, Optional, Tuple

# 检查OpenCV是否可用
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    print("⚠️  OpenCV未安装，将使用FFmpeg模式（推荐安装: pip install opencv-python）")


def combine_video_with_cover_opencv(
    mp4_files: List[str],
    cover_image: str,
    audio_file: str, 
    output_file: str,
    extra_duration: float = 0.5,
    force_16_9: bool = False
) -> bool:
    """使用OpenCV组合视频与封面图片 - 实时进度显示"""
    
    if not HAS_OPENCV:
        print("❌ OpenCV未安装，无法使用快速模式")
        return False
    
    try:
        import numpy as np
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 获取音频时长
        audio_duration = get_audio_duration(audio_file)
        if audio_duration is None:
            print(f"❌ 无法获取音频时长: {audio_file}")
            return False
        
        target_duration = audio_duration + extra_duration
        print(f"🎵 音频时长: {audio_duration:.2f}秒，目标视频时长: {target_duration:.2f}秒")
        print(f"🚀 OpenCV快速模式 - 实时进度显示")
        
        # 读取原始视频
        print(f"📖 读取原始视频...")
        cap = cv2.VideoCapture(mp4_files[0])
        
        if not cap.isOpened():
            print(f"❌ 无法打开视频文件: {mp4_files[0]}")
            return False
        
        # 获取视频信息
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        video_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_duration = video_frame_count / fps
        
        print(f"📹 原始视频: {video_width}x{video_height}, {fps}fps, {video_duration:.2f}秒")
        
        # 计算目标分辨率
        if force_16_9:
            target_16_9 = calculate_best_16_9_resolution((video_width, video_height), (video_width, video_height))
            target_width, target_height = target_16_9
            print(f"🎯 16:9模式 - 目标分辨率: {target_width}x{target_height}")
        else:
            target_width, target_height = video_width, video_height
            print(f"📺 保持原始分辨率: {target_width}x{target_height}")
        
        # 读取封面图片
        print(f"🖼️  读取封面图片...")
        cover_img = cv2.imread(cover_image)
        if cover_img is None:
            print(f"❌ 无法读取封面图片: {cover_image}")
            return False
        
        cover_height, cover_width = cover_img.shape[:2]
        print(f"🖼️  封面图片: {cover_width}x{cover_height}")
        
        # 调整封面图片大小
        cover_resized = cv2.resize(cover_img, (target_width, target_height))
        
        # 计算总帧数
        total_frames = int(target_duration * fps)
        cover_frames = total_frames - video_frame_count
        
        print(f"📊 视频帧数: {video_frame_count}, 封面帧数: {cover_frames}, 总帧数: {total_frames}")
        
        # 创建视频写入器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        temp_video_file = output_file + "_temp.mp4"
        out = cv2.VideoWriter(temp_video_file, fourcc, fps, (target_width, target_height))
        
        if not out.isOpened():
            print(f"❌ 无法创建输出视频文件")
            return False
        
        print(f"🎬 开始处理视频帧...")
        
        # 处理原始视频帧
        current_frame = 0
        with tqdm(total=total_frames, desc="处理进度", unit="帧") as pbar:
            
            # 写入原始视频帧
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            while current_frame < video_frame_count:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 调整帧大小
                if force_16_9 or frame.shape[:2] != (target_height, target_width):
                    frame_resized = cv2.resize(frame, (target_width, target_height))
                else:
                    frame_resized = frame
                
                out.write(frame_resized)
                current_frame += 1
                
                # 更新进度条
                pbar.update(1)
                if current_frame % 100 == 0:  # 每100帧更新一次显示
                    elapsed_time = current_frame / fps
                    pbar.set_postfix({
                        '阶段': '视频',
                        '时间': f'{elapsed_time:.1f}s/{video_duration:.1f}s'
                    })
            
            # 写入封面图片帧
            print(f"🖼️  添加封面图片帧...")
            for i in range(cover_frames):
                out.write(cover_resized)
                current_frame += 1
                
                # 更新进度条
                pbar.update(1)
                if i % 100 == 0:  # 每100帧更新一次显示
                    cover_time = i / fps
                    pbar.set_postfix({
                        '阶段': '封面',
                        '时间': f'{cover_time:.1f}s/{cover_frames/fps:.1f}s'
                    })
        
        # 释放资源
        cap.release()
        out.release()
        
        print(f"🎵 添加音频轨道...")
        
        # 使用FFmpeg添加音频
        final_cmd = [
            "ffmpeg", "-i", temp_video_file, "-i", audio_file,
            "-c:v", "copy", "-c:a", "aac", "-shortest",
            "-y", output_file
        ]
        
        result = subprocess.run(final_cmd, capture_output=True, text=True)
        
        # 清理临时文件
        try:
            os.unlink(temp_video_file)
        except Exception:
            pass
        
        if result.returncode != 0:
            print(f"❌ 添加音频失败: {result.stderr}")
            return False
        
        # 验证输出文件
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            final_info = get_video_info(output_file)
            if final_info:
                actual_duration = final_info["duration"]
                print(f"✅ 视频生成成功: {output_file}")
                print(f"📊 文件大小: {file_size / 1024 / 1024:.2f} MB")
                print(f"⏱️  实际时长: {actual_duration:.2f}秒 (目标: {target_duration:.2f}秒)")
                return True
            else:
                print(f"❌ 生成的视频文件无效")
                return False
        else:
            print(f"❌ 输出文件未生成")
            return False
    
    except Exception as e:
        print(f"❌ OpenCV视频处理出错: {e}")
        return False


def get_paths():
    """根据操作系统返回适当的路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return {
            "cover_img_dir": "/Volumes/dhl/audio/scifi/cover_img_large",
            "mp4_source_dir": "/Volumes/dhl/audio/scifi/mp4_upscaled", 
            "audio_merge_dir": "/Volumes/dhl/audio/scifi/mp3_merge",
            "output_dir": "/mnt/dhl/audio/scifi/mp4_full_silent"
        }
    else:  # 默认为Linux/Ubuntu
        return {
            "cover_img_dir": "/media/dhl/audio/scifi/cover_img_large",
            "mp4_source_dir": "/media/dhl/audio/scifi/mp4_upscaled",
            "audio_merge_dir": "/media/dhl/audio/scifi/mp3_merge", 
            "output_dir": "/mnt/dhl/audio/scifi/mp4_full_silent"
        }


def run_ffmpeg_with_progress(cmd: List[str], total_duration: float, description: str = "处理中") -> bool:
    """运行FFmpeg命令并显示进度"""
    import re
    import time
    
    try:
        # 添加进度输出参数
        progress_cmd = cmd + ["-progress", "pipe:1"]
        
        print(f"🎬 {description}...")
        start_time = time.time()
        
        process = subprocess.Popen(
            progress_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        last_time = 0
        with tqdm(total=100, desc=description, unit="%", ncols=80) as pbar:
            while True:
                output = process.stdout.readline()
                
                if output == '' and process.poll() is not None:
                    break
                
                if output:
                    # 解析时间进度
                    if output.startswith('out_time_ms='):
                        try:
                            time_ms = int(output.split('=')[1])
                            current_time = time_ms / 1000000.0  # 转换为秒
                            
                            if total_duration > 0:
                                progress = min((current_time / total_duration) * 100, 100)
                                update_amount = progress - pbar.n
                                if update_amount > 0:
                                    pbar.update(update_amount)
                            
                            # 显示处理时间
                            elapsed = time.time() - start_time
                            if current_time > last_time + 5:  # 每5秒更新一次
                                speed = current_time / max(1, elapsed)
                                pbar.set_postfix({
                                    '时间': f'{current_time:.1f}s/{total_duration:.1f}s',
                                    '速度': f'{speed:.1f}x'
                                })
                                last_time = current_time
                        except (ValueError, IndexError):
                            continue
        
        # 等待进程完成
        process.wait()
        
        if process.returncode == 0:
            print(f"✅ {description}完成")
            return True
        else:
            stderr_output = process.stderr.read()
            print(f"❌ {description}失败: {stderr_output}")
            return False
            
    except Exception as e:
        print(f"❌ {description}出错: {e}")
        return False


def detect_hardware_acceleration() -> Dict:
    """检测可用的硬件加速"""
    hw_options = {
        "encoder": "libx264",  # 默认软件编码
        "preset": "faster",    # 默认快速preset
        "extra_args": []
    }
    
    try:
        # 检测NVIDIA GPU (NVENC)
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"], 
            capture_output=True, text=True
        )
        
        if "h264_nvenc" in result.stdout:
            # 测试NVENC是否可用
            test_cmd = [
                "ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
                "-c:v", "h264_nvenc", "-f", "null", "-"
            ]
            test_result = subprocess.run(test_cmd, capture_output=True, text=True)
            
            if test_result.returncode == 0:
                print("🚀 检测到NVIDIA硬件加速 (NVENC)")
                hw_options.update({
                    "encoder": "h264_nvenc",
                    "preset": "fast",
                    "extra_args": ["-rc", "vbr", "-cq", "20"]
                })
                return hw_options
        
        # 检测Intel QuickSync (QSV)
        if "h264_qsv" in result.stdout:
            test_cmd = [
                "ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1", 
                "-c:v", "h264_qsv", "-f", "null", "-"
            ]
            test_result = subprocess.run(test_cmd, capture_output=True, text=True)
            
            if test_result.returncode == 0:
                print("🚀 检测到Intel硬件加速 (QuickSync)")
                hw_options.update({
                    "encoder": "h264_qsv",
                    "preset": "fast", 
                    "extra_args": ["-global_quality", "20"]
                })
                return hw_options
        
        # 检测AMD GPU (AMF)
        if "h264_amf" in result.stdout:
            test_cmd = [
                "ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
                "-c:v", "h264_amf", "-f", "null", "-"
            ]
            test_result = subprocess.run(test_cmd, capture_output=True, text=True)
            
            if test_result.returncode == 0:
                print("🚀 检测到AMD硬件加速 (AMF)")
                hw_options.update({
                    "encoder": "h264_amf",
                    "preset": "fast",
                    "extra_args": ["-rc", "vbr", "-qp_i", "20", "-qp_p", "22", "-qp_b", "24"]
                })
                return hw_options
                
    except Exception as e:
        print(f"⚠️  硬件加速检测失败: {e}")
    
    # 软件编码优化
    print("💻 使用软件编码 - 已优化速度")
    hw_options.update({
        "preset": "faster",  # 更快的preset
        "extra_args": ["-crf", "21"]  # 稍微降低质量但大幅提速
    })
    
    return hw_options


def check_dependencies():
    """检查必要的依赖"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            capture_output=True, 
            text=True
        )
        if result.returncode != 0:
            print("❌ 错误: 未找到 ffmpeg")
            print("请安装 ffmpeg: sudo apt install ffmpeg (Ubuntu) 或 brew install ffmpeg (macOS)")
            sys.exit(1)
        print("✅ ffmpeg 已安装")
        
        # 检测硬件加速
        return detect_hardware_acceleration()
    except FileNotFoundError:
        print("❌ 错误: 未找到 ffmpeg")
        print("请安装 ffmpeg: sudo apt install ffmpeg (Ubuntu) 或 brew install ffmpeg (macOS)")
        sys.exit(1)


def get_audio_duration(audio_file: str) -> Optional[float]:
    """获取音频文件的时长（秒）"""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json", 
            "-show_format", audio_file
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


def get_video_info(video_file: str) -> Optional[Dict]:
    """获取视频文件信息（分辨率、时长等）"""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", "-show_format", video_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            
            video_stream = None
            for stream in data["streams"]:
                if stream["codec_type"] == "video":
                    video_stream = stream
                    break
            
            if video_stream:
                return {
                    "width": int(video_stream["width"]),
                    "height": int(video_stream["height"]),
                    "duration": float(data["format"]["duration"]),
                    "fps": eval(video_stream.get("r_frame_rate", "25/1"))
                }
        
        print(f"❌ 获取视频信息失败: {video_file}")
        return None
    except Exception as e:
        print(f"❌ 获取视频信息出错: {e}")
        return None


def get_image_size(image_file: str) -> Optional[Tuple[int, int]]:
    """获取图片尺寸"""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", image_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            
            if data["streams"]:
                stream = data["streams"][0]
                return (int(stream["width"]), int(stream["height"]))
        
        return None
    except Exception as e:
        print(f"❌ 获取图片尺寸出错: {e}")
        return None


def calculate_best_16_9_resolution(video_size: Tuple[int, int], image_size: Tuple[int, int]) -> Tuple[int, int]:
    """计算最佳的16:9分辨率，最大化保持原始画质"""
    video_w, video_h = video_size
    image_w, image_h = image_size
    
    # 选择较小的尺寸作为基准（保证两种素材都能适应）
    base_w = min(video_w, image_w)
    base_h = min(video_h, image_h)
    
    # 常见的16:9分辨率（从高到低）
    resolutions_16_9 = [
        (3840, 2160),  # 4K
        (2560, 1440),  # 1440p
        (1920, 1080),  # 1080p
        (1280, 720),   # 720p
    ]
    
    # 选择最接近且不超过原始尺寸的16:9分辨率
    for target_w, target_h in resolutions_16_9:
        if target_w <= base_w and target_h <= base_h:
            print(f"🎯 选择16:9分辨率: {target_w}x{target_h}")
            return (target_w, target_h)
    
    # 如果原始分辨率都很小，使用720p
    print(f"🎯 使用默认16:9分辨率: 1280x720")
    return (1280, 720)


def create_video_filter_16_9(strategy: Dict) -> str:
    """根据16:9策略创建视频处理的FFmpeg过滤器"""
    method = strategy["method"]
    
    if method == "scale_and_crop_width":
        # 缩放后裁剪宽度
        return (f"scale={strategy['scale_width']}:{strategy['scale_height']},"
                f"crop={strategy['final_width']}:{strategy['final_height']}:"
                f"{strategy['crop_x']}:{strategy['crop_y']}")
    
    elif method == "scale_and_crop_height":
        # 缩放后裁剪高度
        return (f"scale={strategy['scale_width']}:{strategy['scale_height']},"
                f"crop={strategy['final_width']}:{strategy['final_height']}:"
                f"{strategy['crop_x']}:{strategy['crop_y']}")
    
    elif method == "scale_and_pad_width":
        # 缩放后左右填充黑边
        return (f"scale={strategy['scale_width']}:{strategy['scale_height']},"
                f"pad={strategy['final_width']}:{strategy['final_height']}:"
                f"{strategy['pad_x']}:{strategy['pad_y']}:black")
    
    elif method == "scale_and_pad_height":
        # 缩放后上下填充黑边
        return (f"scale={strategy['scale_width']}:{strategy['scale_height']},"
                f"pad={strategy['final_width']}:{strategy['final_height']}:"
                f"{strategy['pad_x']}:{strategy['pad_y']}:black")
    
    else:
        # 默认直接缩放
        return f"scale={strategy['final_width']}:{strategy['final_height']}"


def create_image_filter_16_9(strategy: Dict) -> str:
    """根据16:9策略创建图片处理的FFmpeg过滤器"""
    method = strategy["method"]
    
    if method == "scale_and_crop_width":
        # 缩放后裁剪宽度
        return (f"scale={strategy['scale_width']}:{strategy['scale_height']},"
                f"crop={strategy['final_width']}:{strategy['final_height']}:"
                f"{strategy['crop_x']}:{strategy['crop_y']}")
    
    elif method == "scale_and_crop_height":
        # 缩放后裁剪高度
        return (f"scale={strategy['scale_width']}:{strategy['scale_height']},"
                f"crop={strategy['final_width']}:{strategy['final_height']}:"
                f"{strategy['crop_x']}:{strategy['crop_y']}")
    
    elif method == "scale_and_pad_width":
        # 缩放后左右填充黑边
        return (f"scale={strategy['scale_width']}:{strategy['scale_height']},"
                f"pad={strategy['final_width']}:{strategy['final_height']}:"
                f"{strategy['pad_x']}:{strategy['pad_y']}:black")
    
    elif method == "scale_and_pad_height":
        # 缩放后上下填充黑边
        return (f"scale={strategy['scale_width']}:{strategy['scale_height']},"
                f"pad={strategy['final_width']}:{strategy['final_height']}:"
                f"{strategy['pad_x']}:{strategy['pad_y']}:black")
    
    else:
        # 默认直接缩放
        return f"scale={strategy['final_width']}:{strategy['final_height']}"


def calculate_best_scale_16_9(video_size: Tuple[int, int], image_size: Tuple[int, int], target_16_9: Tuple[int, int]) -> Dict:
    """计算16:9输出的最佳缩放策略，最小化清晰度损失"""
    video_w, video_h = video_size
    image_w, image_h = image_size
    target_w, target_h = target_16_9
    
    # 计算宽高比
    video_ratio = video_w / video_h
    image_ratio = image_w / image_h
    target_ratio = target_w / target_h  # 16:9 = 1.778
    
    print(f"📊 比例分析: 视频{video_ratio:.3f}, 图片{image_ratio:.3f}, 目标{target_ratio:.3f}")
    
    # 对于视频的处理策略
    if video_ratio > target_ratio:
        # 视频比16:9更宽，需要裁剪左右两边或缩小
        # 计算两种方案的损失
        
        # 方案1：按高度缩放（可能需要裁剪宽度）
        scale_by_height = target_h / video_h
        scaled_width = int(video_w * scale_by_height)
        
        if scaled_width >= target_w:
            # 缩放后宽度足够，居中裁剪
            crop_x = (scaled_width - target_w) // 2
            video_strategy = {
                "method": "scale_and_crop_width",
                "scale_width": scaled_width,
                "scale_height": target_h,
                "crop_x": crop_x,
                "crop_y": 0,
                "final_width": target_w,
                "final_height": target_h,
                "description": f"按高度缩放至{scaled_width}x{target_h}，然后裁剪宽度至{target_w}x{target_h}"
            }
        else:
            # 缩放后宽度不够，需要填充
            pad_x = (target_w - scaled_width) // 2
            video_strategy = {
                "method": "scale_and_pad_width", 
                "scale_width": scaled_width,
                "scale_height": target_h,
                "pad_x": pad_x,
                "pad_y": 0,
                "final_width": target_w,
                "final_height": target_h,
                "description": f"按高度缩放至{scaled_width}x{target_h}，然后左右填充黑边至{target_w}x{target_h}"
            }
    else:
        # 视频比16:9更高，需要裁剪上下两边或缩小
        # 按宽度缩放
        scale_by_width = target_w / video_w
        scaled_height = int(video_h * scale_by_width)
        
        if scaled_height >= target_h:
            # 缩放后高度足够，居中裁剪
            crop_y = (scaled_height - target_h) // 2
            video_strategy = {
                "method": "scale_and_crop_height",
                "scale_width": target_w,
                "scale_height": scaled_height,
                "crop_x": 0,
                "crop_y": crop_y,
                "final_width": target_w,
                "final_height": target_h,
                "description": f"按宽度缩放至{target_w}x{scaled_height}，然后裁剪高度至{target_w}x{target_h}"
            }
        else:
            # 缩放后高度不够，需要填充
            pad_y = (target_h - scaled_height) // 2
            video_strategy = {
                "method": "scale_and_pad_height",
                "scale_width": target_w,
                "scale_height": scaled_height,
                "pad_x": 0,
                "pad_y": pad_y,
                "final_width": target_w,
                "final_height": target_h,
                "description": f"按宽度缩放至{target_w}x{scaled_height}，然后上下填充黑边至{target_w}x{target_h}"
            }
    
    # 对于图片的处理策略（类似逻辑）
    if image_ratio > target_ratio:
        # 图片比16:9更宽
        scale_by_height = target_h / image_h
        scaled_width = int(image_w * scale_by_height)
        
        if scaled_width >= target_w:
            crop_x = (scaled_width - target_w) // 2
            image_strategy = {
                "method": "scale_and_crop_width",
                "scale_width": scaled_width,
                "scale_height": target_h,
                "crop_x": crop_x,
                "crop_y": 0,
                "final_width": target_w,
                "final_height": target_h,
                "description": f"按高度缩放至{scaled_width}x{target_h}，然后裁剪宽度至{target_w}x{target_h}"
            }
        else:
            pad_x = (target_w - scaled_width) // 2
            image_strategy = {
                "method": "scale_and_pad_width",
                "scale_width": scaled_width,
                "scale_height": target_h,
                "pad_x": pad_x,
                "pad_y": 0,
                "final_width": target_w,
                "final_height": target_h,
                "description": f"按高度缩放至{scaled_width}x{target_h}，然后左右填充黑边至{target_w}x{target_h}"
            }
    else:
        # 图片比16:9更高
        scale_by_width = target_w / image_w
        scaled_height = int(image_h * scale_by_width)
        
        if scaled_height >= target_h:
            crop_y = (scaled_height - target_h) // 2
            image_strategy = {
                "method": "scale_and_crop_height",
                "scale_width": target_w,
                "scale_height": scaled_height,
                "crop_x": 0,
                "crop_y": crop_y,
                "final_width": target_w,
                "final_height": target_h,
                "description": f"按宽度缩放至{target_w}x{scaled_height}，然后裁剪高度至{target_w}x{target_h}"
            }
        else:
            pad_y = (target_h - scaled_height) // 2
            image_strategy = {
                "method": "scale_and_pad_height",
                "scale_width": target_w,
                "scale_height": scaled_height,
                "pad_x": 0,
                "pad_y": pad_y,
                "final_width": target_w,
                "final_height": target_h,
                "description": f"按宽度缩放至{target_w}x{scaled_height}，然后上下填充黑边至{target_w}x{target_h}"
            }
    
    return {
        "target_width": target_w,
        "target_height": target_h,
        "video_strategy": video_strategy,
        "image_strategy": image_strategy
    }


def calculate_best_scale(video_size: Tuple[int, int], image_size: Tuple[int, int], force_16_9: bool = False) -> Dict:
    """计算最佳缩放策略，最小化形变"""
    video_w, video_h = video_size
    image_w, image_h = image_size
    
    # 如果强制16:9输出
    if force_16_9:
        target_16_9 = calculate_best_16_9_resolution(video_size, image_size)
        return calculate_best_scale_16_9(video_size, image_size, target_16_9)
    
    # 原有的缩放逻辑（保持原始比例）
    # 计算宽高比
    video_ratio = video_w / video_h
    image_ratio = image_w / image_h
    
    # 选择合适的缩放策略
    if abs(video_ratio - image_ratio) < 0.01:  # 宽高比相近
        # 直接缩放到视频尺寸
        return {
            "strategy": "direct_scale",
            "target_width": video_w,
            "target_height": video_h,
            "description": f"直接缩放到视频尺寸 {video_w}x{video_h}"
        }
    elif video_ratio > image_ratio:  # 视频更宽
        # 以高度为准缩放，左右填充黑边
        scale_height = video_h
        scale_width = int(image_w * scale_height / image_h)
        return {
            "strategy": "pad_horizontal",
            "target_width": video_w,
            "target_height": video_h,
            "scale_width": scale_width,
            "scale_height": scale_height,
            "description": f"按高度缩放到 {scale_width}x{scale_height}，左右填充黑边"
        }
    else:  # 图片更宽
        # 以宽度为准缩放，上下填充黑边
        scale_width = video_w
        scale_height = int(image_h * scale_width / image_w)
        return {
            "strategy": "pad_vertical", 
            "target_width": video_w,
            "target_height": video_h,
            "scale_width": scale_width,
            "scale_height": scale_height,
            "description": f"按宽度缩放到 {scale_width}x{scale_height}，上下填充黑边"
        }


def get_story_files(paths: Dict) -> Dict:
    """获取所有故事的相关文件信息"""
    story_info = {}
    
    # 扫描高清封面图片
    cover_dir = paths["cover_img_dir"]
    if os.path.exists(cover_dir):
        for cover_file in glob.glob(os.path.join(cover_dir, "*.png")):
            basename = os.path.basename(cover_file)
            # 排除以点开头的文件
            if basename.startswith('.'):
                continue
            
            match = re.match(r"(\d+)\.png", basename)
            if match:
                story_index = match.group(1)
                if story_index not in story_info:
                    story_info[story_index] = {}
                story_info[story_index]["cover_image"] = cover_file
    
    # 扫描MP4源文件（单个文件，不是片段）
    mp4_source_dir = paths["mp4_source_dir"]
    if os.path.exists(mp4_source_dir):
        for mp4_file in glob.glob(os.path.join(mp4_source_dir, "*.mp4")):
            basename = os.path.basename(mp4_file)
            # 排除以点开头的文件
            if basename.startswith('.'):
                continue
            
            match = re.match(r"(\d+)\.mp4", basename)
            if match:
                story_index = match.group(1)
                if story_index not in story_info:
                    story_info[story_index] = {}
                story_info[story_index]["source_mp4"] = mp4_file
    
    # 扫描音频文件
    audio_dir = paths["audio_merge_dir"]
    if os.path.exists(audio_dir):
        for story_dir in glob.glob(os.path.join(audio_dir, "*")):
            if os.path.isdir(story_dir):
                story_index = os.path.basename(story_dir)
                audio_file = os.path.join(story_dir, "story.mp3")
                
                if os.path.exists(audio_file):
                    if story_index not in story_info:
                        story_info[story_index] = {}
                    story_info[story_index]["audio_file"] = audio_file
    
    return story_info


def get_existing_combined_videos(output_dir: str) -> set:
    """获取已存在的组合视频文件"""
    existing_videos = set()
    
    if not os.path.exists(output_dir):
        return existing_videos
    
    for video_file in glob.glob(os.path.join(output_dir, "*.mp4")):
        basename = os.path.basename(video_file)
        # 排除以点开头的文件
        if basename.startswith('.'):
            continue
            
        match = re.match(r"(\d+)\.mp4", basename)
        if match:
            story_index = match.group(1)
            # 简单验证文件是否有效（大小大于1MB）
            try:
                file_size = os.path.getsize(video_file)
                if file_size > 1024 * 1024:  # 大于1MB
                    existing_videos.add(story_index)
                    print(f"✅ 发现有效组合视频: 故事 {story_index} ({file_size / 1024 / 1024:.2f} MB)")
            except Exception:
                pass
    
    return existing_videos


def combine_video_with_cover(
    mp4_files: List[str],
    cover_image: str, 
    audio_file: str,
    output_file: str,
    extra_duration: float = 0.5,
    force_16_9: bool = False,
    hw_options: Dict = None
) -> bool:
    """组合视频与封面图片"""
    
    if hw_options is None:
        hw_options = {
            "encoder": "libx264",
            "preset": "faster", 
            "extra_args": ["-crf", "21"]
        }
    
    try:
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 获取音频时长
        audio_duration = get_audio_duration(audio_file)
        if audio_duration is None:
            print(f"❌ 无法获取音频时长: {audio_file}")
            return False
        
        target_duration = audio_duration + extra_duration
        print(f"🎵 音频时长: {audio_duration:.2f}秒，目标视频时长: {target_duration:.2f}秒")
        print(f"⚡ 编码器: {hw_options['encoder']} (preset: {hw_options['preset']})")
        
        # 获取第一个视频文件的信息作为参考
        video_info = get_video_info(mp4_files[0])
        if video_info is None:
            print(f"❌ 无法获取视频信息: {mp4_files[0]}")
            return False
        
        video_size = (video_info["width"], video_info["height"])
        print(f"📹 视频分辨率: {video_size[0]}x{video_size[1]}")
        
        # 获取封面图片尺寸
        image_size = get_image_size(cover_image)
        if image_size is None:
            print(f"❌ 无法获取图片尺寸: {cover_image}")
            return False
        
        print(f"🖼️  封面图片尺寸: {image_size[0]}x{image_size[1]}")
        
        # 计算最佳缩放策略
        scale_info = calculate_best_scale(video_size, image_size, force_16_9)
        
        if force_16_9:
            print(f"🎯 16:9模式 - 目标分辨率: {scale_info['target_width']}x{scale_info['target_height']}")
            print(f"📹 视频策略: {scale_info['video_strategy']['description']}")
            print(f"🖼️  图片策略: {scale_info['image_strategy']['description']}")
        else:
            print(f"🔄 缩放策略: {scale_info['description']}")
        
        # 创建临时文件列表供ffmpeg使用
        import tempfile
        
        # 第一步：合并所有MP4片段
        print(f"🔗 第一步：合并 {len(mp4_files)} 个视频片段...")
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as temp_file:
            for mp4_file in mp4_files:
                temp_file.write(f"file '{mp4_file}'\n")
            temp_list_file = temp_file.name
        
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
            temp_video_file = temp_video.name
        
        try:
            # 合并视频片段并转换为目标分辨率（如果是16:9模式）
            if force_16_9:
                # 优化策略：先快速合并，再统一转换分辨率
                print("⚡ 快速合并模式 - 先合并后转换")
                
                # 第一阶段：快速合并视频片段（无重编码）
                temp_merged_file = temp_video_file + "_raw.mp4"
                quick_concat_cmd = [
                    "ffmpeg", "-f", "concat", "-safe", "0", "-i", temp_list_file,
                    "-c", "copy", "-y", temp_merged_file
                ]
                
                result = subprocess.run(quick_concat_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"❌ 快速合并失败: {result.stderr}")
                    return False
                
                # 第二阶段：转换为16:9分辨率
                video_strategy = scale_info['video_strategy']
                video_filter = create_video_filter_16_9(video_strategy)
                
                convert_cmd = [
                    "ffmpeg", "-i", temp_merged_file,
                    "-vf", video_filter,
                    "-c:v", hw_options["encoder"], 
                    "-preset", hw_options["preset"]
                ] + hw_options["extra_args"] + [
                    "-movflags", "+faststart",  # 优化流媒体播放
                    "-threads", "0",            # 使用所有CPU核心
                    "-y", temp_video_file
                ]
                
                result = subprocess.run(convert_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"❌ 分辨率转换失败: {result.stderr}")
                    return False
                
                # 清理临时文件
                try:
                    os.unlink(temp_merged_file)
                except Exception:
                    pass
            else:
                # 原有的简单合并
                concat_cmd = [
                    "ffmpeg", "-f", "concat", "-safe", "0", "-i", temp_list_file,
                    "-c", "copy", "-y", temp_video_file
                ]
                
                result = subprocess.run(concat_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"❌ 视频片段合并失败: {result.stderr}")
                    return False
            
            # 第二步：准备封面图片视频
            print(f"🖼️  第二步：处理封面图片...")
            
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_cover:
                temp_cover_file = temp_cover.name
            
            # 根据缩放策略创建封面图片视频
            if force_16_9:
                # 使用16:9模式的图片处理策略
                image_strategy = scale_info['image_strategy']
                image_filter = create_image_filter_16_9(image_strategy)
                
                cover_cmd = [
                    "ffmpeg", "-loop", "1", "-i", cover_image,
                    "-vf", image_filter,
                    "-c:v", hw_options["encoder"],
                    "-preset", hw_options["preset"]
                ] + hw_options["extra_args"] + [
                    "-t", str(target_duration),
                    "-pix_fmt", "yuv420p", "-r", "25",
                    "-movflags", "+faststart",
                    "-threads", "0",
                    "-y", temp_cover_file
                ]
            elif scale_info["strategy"] == "direct_scale":
                # 直接缩放
                cover_cmd = [
                    "ffmpeg", "-loop", "1", "-i", cover_image,
                    "-vf", f"scale={scale_info['target_width']}:{scale_info['target_height']}",
                    "-c:v", hw_options["encoder"], "-preset", hw_options["preset"]
                ] + hw_options["extra_args"] + [
                    "-t", str(target_duration),
                    "-pix_fmt", "yuv420p", "-r", "25",
                    "-movflags", "+faststart", "-threads", "0",
                    "-y", temp_cover_file
                ]
            elif scale_info["strategy"] == "pad_horizontal":
                # 按高度缩放，左右填充
                cover_cmd = [
                    "ffmpeg", "-loop", "1", "-i", cover_image,
                    "-vf", f"scale={scale_info['scale_width']}:{scale_info['scale_height']},"
                           f"pad={scale_info['target_width']}:{scale_info['target_height']}:"
                           f"({scale_info['target_width']}-{scale_info['scale_width']})/2:0:black",
                    "-c:v", hw_options["encoder"], "-preset", hw_options["preset"]
                ] + hw_options["extra_args"] + [
                    "-t", str(target_duration),
                    "-pix_fmt", "yuv420p", "-r", "25",
                    "-movflags", "+faststart", "-threads", "0",
                    "-y", temp_cover_file
                ]
            else:  # pad_vertical
                # 按宽度缩放，上下填充
                cover_cmd = [
                    "ffmpeg", "-loop", "1", "-i", cover_image,
                    "-vf", f"scale={scale_info['scale_width']}:{scale_info['scale_height']},"
                           f"pad={scale_info['target_width']}:{scale_info['target_height']}:"
                           f"0:({scale_info['target_height']}-{scale_info['scale_height']})/2:black",
                    "-c:v", hw_options["encoder"], "-preset", hw_options["preset"]
                ] + hw_options["extra_args"] + [
                    "-t", str(target_duration),
                    "-pix_fmt", "yuv420p", "-r", "25",
                    "-movflags", "+faststart", "-threads", "0",
                    "-y", temp_cover_file
                ]
            
            result = subprocess.run(cover_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ 封面图片处理失败: {result.stderr}")
                return False
            
            # 第三步：获取视频片段的总时长
            merged_video_info = get_video_info(temp_video_file)
            if merged_video_info is None:
                print(f"❌ 无法获取合并后视频信息")
                return False
            
            video_duration = merged_video_info["duration"]
            cover_duration = target_duration - video_duration
            
            print(f"📹 视频片段总时长: {video_duration:.2f}秒")
            print(f"🖼️  封面图片时长: {cover_duration:.2f}秒")
            
            if cover_duration <= 0:
                print(f"⚠️  视频时长已足够，不需要添加封面图片")
                # 直接使用视频片段，调整时长到目标时长
                final_cmd = [
                    "ffmpeg", "-i", temp_video_file,
                    "-t", str(target_duration),
                    "-c", "copy", "-y", output_file
                ]
            else:
                # 重新生成正确时长的封面图片视频
                cover_cmd[-4] = str(cover_duration)  # 更新时长参数
                result = subprocess.run(cover_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"❌ 重新生成封面图片失败: {result.stderr}")
                    return False
                
                # 第四步：连接视频片段和封面图片
                print(f"🔗 第三步：连接视频片段和封面图片...")
                
                with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as final_list:
                    final_list.write(f"file '{temp_video_file}'\n")
                    final_list.write(f"file '{temp_cover_file}'\n")
                    final_list_file = final_list.name
                
                final_cmd = [
                    "ffmpeg", "-f", "concat", "-safe", "0", "-i", final_list_file,
                    "-c", "copy", "-y", output_file
                ]
            
            result = subprocess.run(final_cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                print(f"❌ 最终视频生成失败: {result.stderr}")
                return False
            
            # 验证输出文件
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                final_info = get_video_info(output_file)
                if final_info:
                    actual_duration = final_info["duration"]
                    print(f"✅ 视频生成成功: {output_file}")
                    print(f"📊 文件大小: {file_size / 1024 / 1024:.2f} MB")
                    print(f"⏱️  实际时长: {actual_duration:.2f}秒 (目标: {target_duration:.2f}秒)")
                    return True
                else:
                    print(f"❌ 生成的视频文件无效")
                    return False
            else:
                print(f"❌ 输出文件未生成")
                return False
                
        finally:
            # 清理临时文件
            for temp_file in [temp_list_file, temp_video_file, temp_cover_file]:
                try:
                    if 'final_list_file' in locals():
                        os.unlink(final_list_file)
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except Exception:
                    pass
    
    except subprocess.TimeoutExpired:
        print(f"❌ 视频处理超时")
        return False
    except Exception as e:
        print(f"❌ 视频组合出错: {e}")
        return False


def save_progress_log(output_dir: str, stats: Dict, session_stats: Dict):
    """保存处理进度日志"""
    try:
        log_file = os.path.join(output_dir, "combine_progress.json")
        
        log_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_stories": stats["total_stories"],
            "complete_stories": stats["complete_stories"],
            "completed_combines": stats["completed_combines"] + session_stats["successful"],
            "pending_combines": stats["pending_combines"] - session_stats["successful"] - session_stats["failed"],
            "session_successful": session_stats["successful"],
            "session_failed": session_stats["failed"],
            "missing_files": stats["missing_files"]
        }
        
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        print(f"📝 进度日志已保存: {log_file}")
        
    except Exception as e:
        print(f"⚠️  保存进度日志失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="视频封面组合器 - 将MP4视频与高清封面图片组合")
    
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="强制重新处理，忽略已有文件"
    )
    parser.add_argument(
        "--start",
        type=int,
        help="指定开始处理的故事索引"
    )
    parser.add_argument(
        "--end", 
        type=int,
        help="指定结束处理的故事索引"
    )
    parser.add_argument(
        "--story",
        help="只处理指定的故事索引"
    )
    parser.add_argument(
        "--extra-duration",
        type=float,
        default=0.5,
        help="比音频多出的时长（秒），默认0.5秒"
    )
    parser.add_argument(
        "--16-9", "--youtube",
        action="store_true",
        dest="force_16_9",
        help="强制输出16:9比例视频，适合YouTube上传（推荐）"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="快速模式 - 使用最快编码设置，略微降低质量但大幅提升速度"
    )
    parser.add_argument(
        "--opencv", "--turbo",
        action="store_true",
        dest="use_opencv",
        help="OpenCV模式 - 实时进度显示，最快处理速度（需要opencv-python）"
    )
    
    args = parser.parse_args()
    
    # 验证参数
    if args.start is not None and args.end is not None:
        if args.start > args.end:
            print("❌ 错误：开始索引不能大于结束索引")
            return
        if args.start <= 0 or args.end <= 0:
            print("❌ 错误：索引必须大于 0")
            return
    
    print("🎬 视频封面组合器")
    print("=" * 50)
    print(f"🖥️  当前操作系统: {platform.system()}")
    
    if args.force_16_9:
        print("🎯 16:9模式已启用 - 输出YouTube友好的16:9比例视频")
        print("   - 智能裁剪/缩放以最大化保持画质")
        print("   - 自动选择最佳16:9分辨率")
    else:
        print("🔄 标准模式 - 保持原始视频比例")
    
    # 显示处理模式
    if hasattr(args, 'use_opencv') and args.use_opencv and HAS_OPENCV:
        print("🚀 OpenCV模式已启用 - 实时进度显示，最快处理速度")
    elif HAS_OPENCV:
        print("💻 FFmpeg模式 - 可用 --opencv 启用更快的OpenCV模式")
    else:
        print("💻 FFmpeg模式 - 安装opencv-python可启用更快的处理模式")
    
    # 检查依赖
    hw_options = check_dependencies()
    
    # 应用快速模式设置
    if args.fast:
        print("🚀 快速模式已启用 - 最大化编码速度")
        if hw_options["encoder"] == "libx264":
            hw_options["preset"] = "ultrafast"
            hw_options["extra_args"] = ["-crf", "23"]  # 稍微降低质量
        elif "nvenc" in hw_options["encoder"]:
            hw_options["preset"] = "fast"
            hw_options["extra_args"] = ["-rc", "vbr", "-cq", "23"]
        elif "qsv" in hw_options["encoder"]:
            hw_options["extra_args"] = ["-global_quality", "23"]
        elif "amf" in hw_options["encoder"]:
            hw_options["extra_args"] = ["-rc", "vbr", "-qp_i", "23", "-qp_p", "25", "-qp_b", "27"]
        print(f"⚡ 快速编码设置: {hw_options['encoder']} (preset: {hw_options['preset']})")
    
    # 获取路径配置
    paths = get_paths()
    print(f"📁 高清封面目录: {paths['cover_img_dir']}")
    print(f"📁 MP4源文件目录: {paths['mp4_source_dir']}")
    print(f"📁 音频文件目录: {paths['audio_merge_dir']}")
    print(f"📁 输出目录: {paths['output_dir']}")
    
    # 扫描故事文件
    print(f"\n🔍 扫描故事文件...")
    story_info = get_story_files(paths)
    
    if not story_info:
        print("❌ 未找到任何故事文件")
        return
    
    print(f"📊 找到 {len(story_info)} 个故事")
    
    # 过滤指定故事
    if args.story:
        if args.story in story_info:
            story_info = {args.story: story_info[args.story]}
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
        
        has_cover = "cover_image" in files
        has_mp4 = "source_mp4" in files
        has_audio = "audio_file" in files
        
        if has_cover and has_mp4 and has_audio:
            complete_stories[story_index] = files
            print(f"✅ 故事 {story_index}: 文件完整 (封面图+视频片段+音频)")
        else:
            missing = []
            if not has_cover:
                missing.append("封面图")
            if not has_mp4:
                missing.append("视频片段")
            if not has_audio:
                missing.append("音频文件")
            print(f"❌ 故事 {story_index}: 缺少 {', '.join(missing)}")
            missing_files.append(story_index)
    
    if not complete_stories:
        print("❌ 没有文件完整的故事可以处理")
        return
    
    # 扫描已存在的组合视频
    existing_combined = set()
    if not args.force:
        existing_combined = get_existing_combined_videos(paths["output_dir"])
    
    # 确定需要处理的故事
    stories_to_process = {}
    for story_index, files in complete_stories.items():
        if args.force or story_index not in existing_combined:
            stories_to_process[story_index] = files
    
    # 统计信息
    stats = {
        "total_stories": len(story_info),
        "complete_stories": len(complete_stories),
        "completed_combines": len(existing_combined & set(complete_stories.keys())),
        "pending_combines": len(stories_to_process),
        "missing_files": missing_files
    }
    
    print(f"\n📈 处理统计:")
    print(f"   总故事数: {stats['total_stories']}")
    print(f"   文件完整: {stats['complete_stories']}")
    print(f"   已完成组合: {stats['completed_combines']}")
    print(f"   待处理: {stats['pending_combines']}")
    print(f"   文件不完整: {len(stats['missing_files'])}")
    
    if stats["pending_combines"] == 0:
        print(f"\n🎉 所有文件完整的故事都已完成组合！")
        return
    
    # 确保输出目录存在
    os.makedirs(paths["output_dir"], exist_ok=True)
    
    # 开始处理
    print(f"\n🔄 开始视频组合处理...")
    print(f"📝 本次将处理 {stats['pending_combines']} 个故事")
    
    session_stats = {"successful": 0, "failed": 0}
    
    try:
        start_time = time.time()
        
        with tqdm(total=stats["pending_combines"], desc="视频组合进度") as pbar:
            for i, (story_index, files) in enumerate(sorted(stories_to_process.items(), key=lambda x: int(x[0])), 1):
                print(f"\n=== 处理第 {i}/{stats['pending_combines']} 个故事: {story_index} ===")
                
                # 输出文件路径
                output_file = os.path.join(paths["output_dir"], f"{story_index}.mp4")
                
                print(f"📝 封面图片: {os.path.basename(files['cover_image'])}")
                print(f"📝 视频片段: {os.path.basename(files['source_mp4'])}")
                print(f"📝 音频文件: {os.path.basename(files['audio_file'])}")
                print(f"📝 输出文件: {output_file}")
                
                # 执行组合 - 选择处理模式
                if hasattr(args, 'use_opencv') and args.use_opencv and HAS_OPENCV:
                    # 使用OpenCV模式
                    success = combine_video_with_cover_opencv(
                        [files['source_mp4']],
                        files['cover_image'],
                        files['audio_file'],
                        output_file,
                        args.extra_duration,
                        args.force_16_9
                    )
                else:
                    # 使用FFmpeg模式
                    success = combine_video_with_cover(
                        [files['source_mp4']],
                        files['cover_image'],
                        files['audio_file'],
                        output_file,
                        args.extra_duration,
                        args.force_16_9,
                        hw_options
                    )
                
                if success:
                    session_stats["successful"] += 1
                    print(f"✅ 故事 {story_index} 视频组合成功")
                else:
                    session_stats["failed"] += 1
                    print(f"❌ 故事 {story_index} 视频组合失败")
                
                pbar.update(1)
                
                # 处理间隔
                if i < stats["pending_combines"]:
                    time.sleep(1)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 保存进度日志
        save_progress_log(paths["output_dir"], stats, session_stats)
        
        # 结果统计
        print(f"\n=== 🎉 组合完成 ===")
        print(f"✅ 本次成功组合: {session_stats['successful']} 个故事")
        print(f"❌ 本次组合失败: {session_stats['failed']} 个故事")
        print(f"⏭️  之前已完成: {stats['completed_combines']} 个故事")
        print(f"📊 总体完成: {stats['completed_combines'] + session_stats['successful']}/{stats['complete_stories']} "
              f"({(stats['completed_combines'] + session_stats['successful'])/stats['complete_stories']*100:.1f}%)")
        print(f"⏱️  本次耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")
        
        if session_stats["successful"] > 0:
            avg_time = total_time / session_stats["successful"]
            print(f"📊 平均每个故事: {avg_time:.1f} 秒")
        
        if stats["pending_combines"] > 0:
            success_rate = session_stats["successful"] / stats["pending_combines"] * 100
            print(f"📊 本次成功率: {success_rate:.1f}%")
        
        print(f"📁 输出目录: {paths['output_dir']}")
        
        # 提醒处理不完整的故事
        if stats["missing_files"]:
            print(f"\n⚠️  有 {len(stats['missing_files'])} 个故事文件不完整，无法组合")
            print(f"   不完整的故事索引: {', '.join(stats['missing_files'])}")
        
        if session_stats["failed"] > 0:
            print(f"\n⚠️  有 {session_stats['failed']} 个故事组合失败，可以重新运行程序重试")
    
    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断了程序执行")
        print(f"✅ 已成功组合: {session_stats['successful']} 个故事")
        print(f"❌ 组合失败: {session_stats['failed']} 个故事")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        print(f"✅ 已成功组合: {session_stats['successful']} 个故事")
        print(f"❌ 组合失败: {session_stats['failed']} 个故事")


if __name__ == "__main__":
    main() 