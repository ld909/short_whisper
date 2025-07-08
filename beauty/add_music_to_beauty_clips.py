#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Beauty视频音乐添加工具

功能说明：
此脚本用于为merge_beauty_clips.py生成的静音视频添加背景音乐。

主要功能：
1. 只支持Ubuntu系统运行
2. 随机选择assets目录中的MP3文件作为背景音乐
3. 自动匹配音频长度到视频长度（循环拼接或裁剪）
4. 使用ffmpeg合并音视频
5. 支持单个index处理或批量处理所有可用index
6. 支持断点续传，自动跳过已处理的视频
7. 自动排除Mac系统产生的点文件
8. 支持硬件加速提高处理速度

输入路径：
- 视频文件：/mnt/dhl/beauty/merged_2k_videos/[index].mp4
- 音乐文件：/home/dhl/Documents/short_whisper/beauty/assets/*.mp3

输出路径：
- Ubuntu: /mnt/dhl/beauty/mp4_music/[index].mp4

音频处理策略：
- 如果音频短于视频：循环拼接音频直到匹配视频长度
- 如果音频长于视频：裁剪音频到视频长度
- 保持原视频长度不变

依赖环境：
- Ubuntu操作系统
- ffmpeg（支持硬件加速更佳）

使用方法：
# 处理单个index
python add_music_to_beauty_clips.py --index 1
python add_music_to_beauty_clips.py --index 2 --force

# 处理所有可用的index（默认模式）
python add_music_to_beauty_clips.py
python add_music_to_beauty_clips.py --force --volume 0.3
"""

import os
import sys
import platform
import argparse
import subprocess
from pathlib import Path
import re
import random
import json


def check_ubuntu_system():
    """检查是否为Ubuntu系统"""
    system = platform.system()
    if system != "Linux":
        print(f"❌ 错误：此脚本只支持Ubuntu系统")
        print(f"   当前系统：{system}")
        return False
    
    # 进一步检查是否为Ubuntu
    try:
        with open("/etc/os-release", "r") as f:
            content = f.read()
            if "Ubuntu" not in content:
                print(f"❌ 错误：此脚本只支持Ubuntu系统")
                print(f"   当前Linux发行版不是Ubuntu")
                return False
    except FileNotFoundError:
        # 尝试检查另一个文件
        try:
            with open("/etc/lsb-release", "r") as f:
                content = f.read()
                if "Ubuntu" not in content:
                    print(f"❌ 错误：此脚本只支持Ubuntu系统")
                    return False
        except FileNotFoundError:
            print(f"⚠️ 警告：无法确定Linux发行版，假设为Ubuntu继续执行")
    
    print(f"✅ 系统检查通过：Ubuntu")
    return True


def get_base_media_path():
    """返回Ubuntu的媒体路径"""
    return "/mnt/dhl/beauty"


def get_assets_path():
    """返回assets目录路径"""
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "assets")


def get_available_mp3_files(assets_path: str) -> list:
    """获取所有可用的MP3文件（排除Mac产生的点文件）"""
    if not os.path.exists(assets_path):
        print(f"❌ 错误：assets目录不存在 {assets_path}")
        return []
    
    mp3_files = []
    for filename in os.listdir(assets_path):
        # 排除Mac产生的点文件
        if filename.startswith("."):
            continue
            
        if filename.lower().endswith(".mp3"):
            file_path = os.path.join(assets_path, filename)
            if os.path.isfile(file_path):
                mp3_files.append(file_path)
    
    if not mp3_files:
        print(f"❌ 错误：assets目录中未找到MP3文件 {assets_path}")
        return []
    
    print(f"✅ 发现 {len(mp3_files)} 个MP3文件:")
    for mp3_file in mp3_files:
        print(f"   🎵 {os.path.basename(mp3_file)}")
    
    return mp3_files


def get_available_video_indices(base_path: str) -> list:
    """获取所有可用的video index（从merged_2k_videos目录扫描）"""
    merged_2k_videos_dir = os.path.join(base_path, "merged_2k_videos")
    
    if not os.path.exists(merged_2k_videos_dir):
        print(f"❌ 错误：merged_2k_videos目录不存在 {merged_2k_videos_dir}")
        return []
    
    indices = []
    for filename in os.listdir(merged_2k_videos_dir):
        # 排除Mac产生的点文件
        if filename.startswith("."):
            continue
            
        if filename.endswith(".mp4"):
            try:
                # 提取文件名中的数字作为index
                name_without_ext = os.path.splitext(filename)[0]
                index = int(name_without_ext)
                
                # 检查文件是否有效
                file_path = os.path.join(merged_2k_videos_dir, filename)
                file_size = os.path.getsize(file_path)
                if file_size > 1024:  # 至少1KB
                    indices.append(index)
                else:
                    print(f"⚠️ 跳过太小的文件: {filename}")
            except ValueError:
                print(f"⚠️ 跳过非数字命名的文件: {filename}")
                continue
    
    indices.sort()
    return indices


def get_video_duration(video_file: str) -> float:
    """获取视频文件的时长（秒）"""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", video_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        # 从format或video stream中获取时长
        duration = None
        if 'format' in data and 'duration' in data['format']:
            duration = float(data['format']['duration'])
        else:
            # 从视频流中获取时长
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    if 'duration' in stream:
                        duration = float(stream['duration'])
                        break
        
        if duration is None:
            print(f"❌ 无法获取视频时长: {video_file}")
            return 0.0
        
        print(f"📊 视频时长: {duration:.2f} 秒")
        return duration
        
    except subprocess.CalledProcessError as e:
        print(f"❌ ffprobe执行失败: {e}")
        return 0.0
    except json.JSONDecodeError as e:
        print(f"❌ 解析ffprobe输出失败: {e}")
        return 0.0
    except Exception as e:
        print(f"❌ 获取视频时长时出错: {e}")
        return 0.0


def get_audio_duration(audio_file: str) -> float:
    """获取音频文件的时长（秒）"""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", audio_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        duration = float(data['format']['duration'])
        print(f"🎵 音频时长: {duration:.2f} 秒")
        return duration
        
    except subprocess.CalledProcessError as e:
        print(f"❌ ffprobe执行失败: {e}")
        return 0.0
    except json.JSONDecodeError as e:
        print(f"❌ 解析ffprobe输出失败: {e}")
        return 0.0
    except Exception as e:
        print(f"❌ 获取音频时长时出错: {e}")
        return 0.0


def check_output_status(output_file: str) -> bool:
    """检查输出文件是否已存在（断点续传）"""
    if os.path.exists(output_file):
        try:
            # 检查文件大小，确保不是空文件
            file_size = os.path.getsize(output_file)
            if file_size > 1024:  # 至少1KB
                print(f"✅ 输出文件已存在: {output_file} ({file_size:,} bytes)")
                return True
            else:
                print(f"⚠️ 输出文件太小，可能损坏: {output_file}")
                os.remove(output_file)
                return False
        except Exception as e:
            print(f"⚠️ 检查输出文件时出错: {e}")
            return False
    
    return False


def check_ffmpeg_installation():
    """检查ffmpeg是否已安装以及硬件加速支持"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        # 检查是否支持硬件加速
        has_nvenc = "h264_nvenc" in result.stdout
        has_vaapi = "vaapi" in result.stdout
        has_qsv = "h264_qsv" in result.stdout  # Intel Quick Sync
        
        print(f"✅ ffmpeg 已安装")
        
        # 详细的硬件加速检查
        if has_nvenc:
            print(f"✅ 支持NVIDIA硬件加速 (NVENC)")
        if has_vaapi:
            print(f"✅ 支持Intel硬件加速 (VAAPI)")
        if has_qsv:
            print(f"✅ 支持Intel Quick Sync (QSV)")
        
        if not (has_nvenc or has_vaapi or has_qsv):
            print(f"⚠️ 未检测到硬件加速支持，将使用软件编码")
        
        return True, has_nvenc, has_vaapi, has_qsv
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"❌ 错误：未找到ffmpeg命令")
        print(f"   请安装ffmpeg: sudo apt update && sudo apt install ffmpeg")
        return False, False, False, False


def check_gpu_availability():
    """检查GPU可用性"""
    gpu_info = {
        'nvidia_gpu': False,
        'intel_gpu': False,
        'gpu_count': 0,
        'gpu_names': []
    }
    
    # 检查NVIDIA GPU
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            gpu_info['nvidia_gpu'] = True
            lines = result.stdout.strip().split('\n')
            gpu_info['gpu_count'] = len(lines)
            for line in lines:
                parts = line.split(',')
                if len(parts) >= 2:
                    gpu_name = parts[0].strip()
                    gpu_memory = parts[1].strip()
                    gpu_info['gpu_names'].append(f"{gpu_name} ({gpu_memory}MB)")
            
            print(f"✅ 检测到 {gpu_info['gpu_count']} 个NVIDIA GPU:")
            for i, gpu_name in enumerate(gpu_info['gpu_names'], 1):
                print(f"   GPU {i}: {gpu_name}")
                
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # 检查Intel GPU
    try:
        result = subprocess.run(
            ["lspci"],
            capture_output=True,
            text=True,
            check=True
        )
        if "Intel" in result.stdout and ("VGA" in result.stdout or "Display" in result.stdout):
            gpu_info['intel_gpu'] = True
            print(f"✅ 检测到Intel集成显卡")
    except:
        pass
    
    return gpu_info


def add_music_to_video(video_file: str, music_file: str, output_file: str, 
                      volume: float = 0.2, has_nvenc: bool = False, 
                      has_vaapi: bool = False, has_qsv: bool = False, 
                      gpu_info: dict = None) -> bool:
    """使用ffmpeg为视频添加背景音乐"""
    try:
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        print(f"🎬 开始为视频添加背景音乐...")
        print(f"🎞️ 输入视频: {video_file}")
        print(f"🎵 背景音乐: {os.path.basename(music_file)}")
        print(f"📤 输出文件: {output_file}")
        print(f"🔊 音量: {volume}")
        
        # 获取视频和音频时长
        video_duration = get_video_duration(video_file)
        audio_duration = get_audio_duration(music_file)
        
        if video_duration <= 0:
            print(f"❌ 无法获取视频时长")
            return False
        
        if audio_duration <= 0:
            print(f"❌ 无法获取音频时长")
            return False
        
        # 构建ffmpeg命令
        cmd = ["ffmpeg", "-y"]  # -y 覆盖输出文件
        
        # 输入文件
        cmd.extend(["-i", video_file])
        cmd.extend(["-i", music_file])
        
        # 音频处理策略
        if audio_duration < video_duration:
            # 音频短于视频：循环拼接音频
            loop_count = int(video_duration / audio_duration) + 1
            print(f"🔄 音频循环策略：循环 {loop_count} 次以匹配视频长度")
            
            # 使用复杂滤镜实现音频循环和时长裁剪
            audio_filter = f"[1:a]aloop=loop={loop_count-1}:size={int(audio_duration * 48000)}[looped];" \
                          f"[looped]atrim=0:{video_duration},volume={volume}[audio]"
        else:
            # 音频长于或等于视频：裁剪音频
            print(f"✂️ 音频裁剪策略：裁剪到 {video_duration:.2f} 秒")
            audio_filter = f"[1:a]atrim=0:{video_duration},volume={volume}[audio]"
        
        # 使用复杂滤镜
        cmd.extend(["-filter_complex", audio_filter])
        
        # 映射视频流和处理后的音频流
        cmd.extend(["-map", "0:v"])    # 使用第一个输入的视频流
        cmd.extend(["-map", "[audio]"]) # 使用滤镜处理后的音频流
        
        # 根据GPU类型选择编码器
        if gpu_info and gpu_info.get('nvidia_gpu', False):
            print(f"🚀 使用NVIDIA GPU加速编码")
            cmd.extend(["-c:v", "h264_nvenc"])
            cmd.extend(["-preset", "fast"])
            cmd.extend(["-cq", "18"])
        elif gpu_info and gpu_info.get('intel_gpu', False):
            print(f"🚀 使用Intel GPU加速编码")
            cmd.extend(["-c:v", "h264_qsv"])
            cmd.extend(["-preset", "fast"])
            cmd.extend(["-global_quality", "18"])
        else:
            print(f"⚠️ 使用CPU软件编码")
            cmd.extend(["-c:v", "libx264"])
            cmd.extend(["-preset", "fast"])
            cmd.extend(["-crf", "18"])
        
        # 音频编码参数
        cmd.extend(["-c:a", "aac"])
        cmd.extend(["-b:a", "128k"])
        
        # 确保视频时长精确匹配
        cmd.extend(["-t", str(video_duration)])
        
        # 通用输出参数
        cmd.extend(["-pix_fmt", "yuv420p"])
        cmd.extend(["-movflags", "+faststart"])
        
        cmd.append(output_file)
        
        print(f"🔧 执行命令: {' '.join(cmd)}")
        
        # 执行ffmpeg命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        print(f"✅ 背景音乐添加完成!")
        
        # 检查输出文件
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"📊 输出文件大小: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
            
            # 验证输出视频时长
            output_duration = get_video_duration(output_file)
            if abs(output_duration - video_duration) < 0.1:  # 允许0.1秒误差
                print(f"✅ 输出视频时长验证通过: {output_duration:.2f} 秒")
            else:
                print(f"⚠️ 输出视频时长不匹配: 期望 {video_duration:.2f} 秒，实际 {output_duration:.2f} 秒")
            
            return True
        else:
            print(f"❌ 输出文件未创建")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ ffmpeg执行失败:")
        print(f"   错误代码: {e.returncode}")
        if e.stdout:
            print(f"   标准输出: {e.stdout}")
        if e.stderr:
            print(f"   错误输出: {e.stderr}")
        
        # 如果GPU加速失败，尝试回退到软件编码
        if (has_nvenc or has_vaapi or has_qsv) and "not supported" in str(e.stderr).lower():
            print(f"⚠️ GPU加速失败，尝试软件编码...")
            return add_music_to_video(video_file, music_file, output_file, volume, False, False, False, None)
        
        return False
    except Exception as e:
        print(f"❌ 添加背景音乐过程出错: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Beauty视频音乐添加工具",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  # 处理单个index
  python add_music_to_beauty_clips.py --index 1
  python add_music_to_beauty_clips.py --index 2 --force --volume 0.3
  
  # 处理所有可用的index（默认模式）
  python add_music_to_beauty_clips.py
  python add_music_to_beauty_clips.py --force --volume 0.2
  
功能说明:
   1. 随机选择assets目录中的MP3文件作为背景音乐
   2. 自动匹配音频长度到视频长度（循环拼接或裁剪）
   3. 使用ffmpeg合并音视频，保持原视频长度
   4. 支持硬件加速，提高处理速度
   5. 支持断点续传，自动跳过已处理的视频
   6. 只支持Ubuntu系统运行
        """
    )
    
    parser.add_argument(
        "--index", 
        type=int, 
        help="指定要处理的index。不指定时处理所有可用的index"
    )
    
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="强制重新处理（忽略断点续传）"
    )
    
    parser.add_argument(
        "--volume", 
        type=float, 
        default=0.2,
        help="背景音乐音量 (0.0-1.0, 默认: 0.2)"
    )
    
    args = parser.parse_args()
    
    print("🎵 Beauty视频音乐添加工具")
    print("=" * 50)
    
    # 检查操作系统
    if not check_ubuntu_system():
        return 1
    
    # 验证音量参数
    if args.volume < 0.0 or args.volume > 1.0:
        print("❌ 错误：音量必须在0.0-1.0之间")
        return 1
    
    # 检查GPU可用性
    print(f"\n🎮 GPU状态检查:")
    gpu_info = check_gpu_availability()
    
    # 检查ffmpeg
    print(f"\n🔧 FFmpeg检查:")
    ffmpeg_ok, has_nvenc, has_vaapi, has_qsv = check_ffmpeg_installation()
    if not ffmpeg_ok:
        return 1
    
    # 显示推荐的处理方式
    print(f"\n💡 处理方式:")
    if gpu_info.get('nvidia_gpu', False):
        print(f"✅ 将使用NVIDIA GPU硬件加速（推荐）")
    elif gpu_info.get('intel_gpu', False):
        print(f"✅ 将使用Intel GPU硬件加速")
    else:
        print(f"⚠️ 将使用CPU软件编码（较慢）")
    
    # 获取基础路径
    base_path = get_base_media_path()
    assets_path = get_assets_path()
    
    # 获取可用的MP3文件
    print(f"\n🎵 音乐文件检查:")
    mp3_files = get_available_mp3_files(assets_path)
    if not mp3_files:
        return 1
    
    # 确定要处理的index列表
    if args.index is not None:
        # 验证单个index参数
        if args.index <= 0:
            print("❌ 错误：index必须大于0")
            return 1
        indices_to_process = [args.index]
        print(f"📂 指定处理index: {args.index}")
    else:
        # 获取所有可用的index
        indices_to_process = get_available_video_indices(base_path)
        if not indices_to_process:
            print("❌ 未找到任何可处理的merged_2k_videos视频文件")
            return 1
        print(f"📂 自动发现 {len(indices_to_process)} 个index: {indices_to_process}")
    
    # 统计变量
    total_count = len(indices_to_process)
    success_count = 0
    failed_indices = []
    
    print(f"🎯 开始处理 {total_count} 个视频...")
    
    # 逐个处理每个index
    for i, index in enumerate(indices_to_process, 1):
        print(f"\n{'='*20} 处理 {i}/{total_count}: index {index} {'='*20}")
        
        # 构建路径
        input_video = os.path.join(base_path, "merged_2k_videos", f"{index}.mp4")
        output_dir = os.path.join(base_path, "mp4_music")
        output_file = os.path.join(output_dir, f"{index}.mp4")
        
        # 检查输入视频文件
        if not os.path.exists(input_video):
            print(f"❌ 跳过index {index}：输入视频文件不存在 {input_video}")
            failed_indices.append(index)
            continue
        
        print(f"🎞️ 输入视频: {input_video}")
        print(f"📤 输出文件: {output_file}")
        
        # 检查输出状态（断点续传）
        if not args.force:
            if check_output_status(output_file):
                print(f"✅ 跳过index {index}：视频已存在")
                success_count += 1
                continue
        
        # 随机选择一个MP3文件
        selected_music = random.choice(mp3_files)
        print(f"🎵 随机选择音乐: {os.path.basename(selected_music)}")
        
        # 添加背景音乐
        success = add_music_to_video(
            input_video, selected_music, output_file, args.volume,
            has_nvenc, has_vaapi, has_qsv, gpu_info
        )
        
        if success:
            print(f"✅ index {index} 处理成功!")
            success_count += 1
        else:
            print(f"❌ index {index} 处理失败!")
            failed_indices.append(index)
    
    # 显示最终结果
    print(f"\n{'='*50}")
    print(f"🎉 批量处理完成!")
    print(f"📊 总计: {total_count} 个")
    print(f"✅ 成功: {success_count} 个")
    print(f"❌ 失败: {len(failed_indices)} 个")
    print(f"🔊 使用音量: {args.volume}")
    
    if failed_indices:
        print(f"❌ 失败的index: {failed_indices}")
        return 1
    else:
        print(f"🎉 所有视频处理成功!")
        return 0


if __name__ == "__main__":
    sys.exit(main()) 