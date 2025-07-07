#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Beauty视频帧提取工具

功能说明：
此脚本用于从Beauty项目中合并后的MP4视频文件提取每一帧并保存为JPG图片。

主要功能：
1. 自动检测操作系统并使用对应的硬盘根目录
2. 从merge_beauty_clips.py的输出文件中提取每一帧
3. 保持原始图像大小，不进行缩放
4. 自动创建输出目录结构
5. 支持单个index处理或批量处理所有可用index

输入路径：
- Mac: /Volumes/dhl/beauty/mp4_low_res/[index].mp4
- Ubuntu: /mnt/dhl/beauty/mp4_low_res/[index].mp4

输出路径：
- Mac: /Volumes/dhl/beauty/frames/[index]/frame%08d.jpg
- Ubuntu: /mnt/dhl/beauty/frames/[index]/frame%08d.jpg

使用方法：
# 处理单个index
python extract_video_frames.py --index 1
python extract_video_frames.py --index 2 --force

# 处理所有可用的index（默认模式）  
python extract_video_frames.py
python extract_video_frames.py --force
"""

import os
import sys
import platform
import argparse
import subprocess
from pathlib import Path


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/beauty"
    else:  # 默认为Linux/Ubuntu
        return "/mnt/dhl/beauty"


def check_input_video(video_path: str) -> bool:
    """检查输入视频文件是否存在"""
    if not os.path.exists(video_path):
        print(f"❌ 错误：输入视频文件不存在 {video_path}")
        return False
    
    if not os.path.isfile(video_path):
        print(f"❌ 错误：输入路径不是文件 {video_path}")
        return False
    
    file_size = os.path.getsize(video_path)
    if file_size == 0:
        print(f"❌ 错误：输入视频文件为空 {video_path}")
        return False
    
    print(f"✅ 输入视频文件检查通过")
    print(f"📁 文件路径: {video_path}")
    print(f"📏 文件大小: {file_size / (1024*1024):.2f} MB")
    return True


def get_video_info(video_path: str) -> dict:
    """获取视频文件信息"""
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        import json
        info = json.loads(result.stdout)
        
        # 查找视频流
        video_stream = None
        for stream in info.get('streams', []):
            if stream.get('codec_type') == 'video':
                video_stream = stream
                break
        
        if video_stream:
            width = video_stream.get('width', 0)
            height = video_stream.get('height', 0)
            duration = float(video_stream.get('duration', 0))
            fps = eval(video_stream.get('r_frame_rate', '0/1'))  # 分数形式的帧率
            
            print(f"📊 视频信息:")
            print(f"   🖼️  分辨率: {width}x{height}")
            print(f"   ⏱️  时长: {duration:.2f} 秒")
            print(f"   🎬 帧率: {fps:.2f} fps")
            print(f"   📊 预计帧数: {int(duration * fps)} 帧")
            
            return {
                'width': width,
                'height': height,
                'duration': duration,
                'fps': fps,
                'estimated_frames': int(duration * fps)
            }
        
    except (subprocess.CalledProcessError, json.JSONDecodeError, Exception) as e:
        print(f"⚠️ 无法获取视频详细信息: {e}")
    
    return {}


def extract_frames(video_path: str, output_dir: str) -> bool:
    """
    使用ffmpeg提取视频帧
    """
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 输出文件路径模式
        output_pattern = os.path.join(output_dir, "frame%08d.jpg")
        
        print(f"🎬 开始提取视频帧...")
        print(f"📤 输出目录: {output_dir}")
        print(f"📝 文件命名: frame%08d.jpg")
        
        # 构建ffmpeg命令
        cmd = [
            "ffmpeg",
            "-i", video_path,           # 输入视频文件
            "-vf", "scale=-1:-1",       # 保持原始尺寸（不缩放）
            "-q:v", "2",                # 高质量JPEG（1-31，数字越小质量越高）
            "-y",                       # 覆盖输出文件
            output_pattern
        ]
        
        print(f"🔧 执行命令: {' '.join(cmd)}")
        
        # 执行ffmpeg命令
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # 检查输出文件
        generated_files = []
        for filename in os.listdir(output_dir):
            if filename.startswith("frame") and filename.endswith(".jpg"):
                # 排除Mac产生的点文件
                if not filename.startswith("."):
                    generated_files.append(filename)
        
        if generated_files:
            generated_files.sort()  # 按文件名排序
            print(f"✅ 帧提取成功!")
            print(f"📁 输出目录: {output_dir}")
            print(f"📊 生成帧数: {len(generated_files)} 帧")
            print(f"📝 首帧: {generated_files[0]}")
            print(f"📝 末帧: {generated_files[-1]}")
            
            # 检查第一个文件的大小作为参考
            first_frame_path = os.path.join(output_dir, generated_files[0])
            first_frame_size = os.path.getsize(first_frame_path)
            print(f"📏 单帧大小: {first_frame_size / 1024:.2f} KB")
            
            return True
        else:
            print(f"❌ 提取失败：未生成任何帧文件")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ ffmpeg执行失败:")
        print(f"   错误代码: {e.returncode}")
        if e.stdout:
            print(f"   标准输出: {e.stdout}")
        if e.stderr:
            print(f"   错误输出: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"❌ 错误：未找到ffmpeg命令")
        print(f"   请确保已安装ffmpeg并添加到PATH环境变量")
        return False
    except Exception as e:
        print(f"❌ 提取过程出错: {e}")
        return False


def get_available_indices(base_path: str) -> list:
    """获取所有可用的index（从mp4_low_res目录扫描）"""
    mp4_dir = os.path.join(base_path, "mp4_low_res")
    
    if not os.path.exists(mp4_dir):
        print(f"❌ 错误：MP4目录不存在 {mp4_dir}")
        return []
    
    indices = []
    for filename in os.listdir(mp4_dir):
        # 排除Mac产生的点文件
        if filename.startswith("."):
            continue
            
        if filename.lower().endswith(".mp4"):
            # 提取文件名中的数字部分作为index
            name_without_ext = os.path.splitext(filename)[0]
            try:
                index = int(name_without_ext)
                indices.append(index)
            except ValueError:
                print(f"⚠️ 跳过非数字命名的文件: {filename}")
                continue
    
    indices.sort()
    return indices


def check_dependencies():
    """检查依赖项"""
    try:
        # 检查ffmpeg
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, check=True
        )
        print("✅ ffmpeg 已安装")
        
        # 检查ffprobe
        result = subprocess.run(
            ["ffprobe", "-version"], capture_output=True, text=True, check=True
        )
        print("✅ ffprobe 已安装")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ 错误：未找到ffmpeg或ffprobe")
        print("   请安装ffmpeg:")
        if platform.system() == "Darwin":
            print("   Mac: brew install ffmpeg")
        else:
            print("   Ubuntu: sudo apt install ffmpeg")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Beauty视频帧提取工具",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  # 处理单个index
  python extract_video_frames.py --index 1
  python extract_video_frames.py --index 2 --force
  
  # 处理所有可用的index（默认模式）
  python extract_video_frames.py
  python extract_video_frames.py --force
  
功能说明:
  1. 从merge_beauty_clips.py的输出视频中提取每一帧
  2. 保持原始图像大小，不进行缩放
  3. 输出格式：frame00000001.jpg, frame00000002.jpg, ...
  4. 自动排除Mac系统产生的点文件
  5. 不指定index时自动处理所有可用视频文件
        """
    )
    
    parser.add_argument(
        "--index", 
        type=int, 
        help="指定要处理的index（对应merge_beauty_clips.py的输出）。不指定时处理所有可用的index"
    )
    
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="强制覆盖已存在的输出目录"
    )
    
    args = parser.parse_args()
    
    print("🎬 Beauty视频帧提取工具")
    print("=" * 50)
    print(f"💻 操作系统: {platform.system()}")
    
    # 检查依赖
    if not check_dependencies():
        return 1
    
    # 获取基础路径
    base_path = get_base_media_path()
    
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
        indices_to_process = get_available_indices(base_path)
        if not indices_to_process:
            print("❌ 未找到任何可处理的视频文件")
            return 1
        print(f"📂 自动发现 {len(indices_to_process)} 个index: {indices_to_process}")
    
    # 统计变量
    total_count = len(indices_to_process)
    success_count = 0
    failed_indices = []
    
    print(f"🎯 开始处理 {total_count} 个视频文件...")
    
    # 逐个处理每个index
    for i, index in enumerate(indices_to_process, 1):
        print(f"\n{'='*20} 处理 {i}/{total_count}: index {index} {'='*20}")
        
        # 构建路径
        input_video = os.path.join(base_path, "mp4_low_res", f"{index}.mp4")
        output_dir = os.path.join(base_path, "frames", str(index))
        
        print(f"📁 输入视频: {input_video}")
        print(f"📤 输出目录: {output_dir}")
        
        # 检查输入文件
        if not check_input_video(input_video):
            print(f"❌ 跳过index {index}：输入文件检查失败")
            failed_indices.append(index)
            continue
        
        # 检查输出目录是否已存在
        skip_current = False
        if os.path.exists(output_dir):
            existing_files = [f for f in os.listdir(output_dir) 
                             if f.startswith("frame") and f.endswith(".jpg") and not f.startswith(".")]
            if existing_files and not args.force:
                print(f"⚠️ 跳过index {index}：输出目录已存在并包含 {len(existing_files)} 个帧文件")
                print(f"   使用 --force 参数强制覆盖")
                failed_indices.append(index)
                continue
            elif existing_files:
                print(f"🔄 强制模式：将覆盖已存在的 {len(existing_files)} 个帧文件")
        
        # 获取视频信息（可选，用于显示）
        get_video_info(input_video)
        
        # 提取帧
        success = extract_frames(input_video, output_dir)
        
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
    
    if failed_indices:
        print(f"❌ 失败的index: {failed_indices}")
        return 1
    else:
        print(f"🎉 所有视频文件处理成功!")
        return 0


if __name__ == "__main__":
    sys.exit(main()) 