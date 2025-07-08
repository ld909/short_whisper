#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Beauty 2K视频合并工具

功能说明：
此脚本用于将realesrgan_upscale_frames.py输出的超分辨率帧合并为2K MP4视频。

主要功能：
1. 支持Ubuntu系统（GPU加速）和其他系统（CPU模式）
2. 使用ffmpeg将帧序列合并为MP4视频
3. 输出分辨率：2560x1440 (2K)
4. 帧率：24fps
5. 智能分辨率调整：图像上下顶格，左右添加等宽黑边
6. 支持单个index处理或批量处理所有可用index
7. 支持断点续传，自动跳过已处理的视频
8. 自动排除Mac系统产生的点文件

输入路径：
- Ubuntu: /mnt/dhl/beauty/face_sr_frames/[index]/*.jpg
- Mac: /Volumes/dhl/beauty/face_sr_frames/[index]/*.jpg 
- 其他: /media/dhl/beauty/face_sr_frames/[index]/*.jpg

输出路径：
- Ubuntu: /mnt/dhl/beauty/merged_2k_videos/[index].mp4
- Mac: /Volumes/dhl/beauty/merged_2k_videos/[index].mp4
- 其他: /media/dhl/beauty/merged_2k_videos/[index].mp4

依赖环境：
- ffmpeg (必须)
- Ubuntu系统需要NVIDIA GPU和驱动支持GPU加速
- 其他系统使用CPU模式

使用方法：
# 处理单个index
python merge_2k_frames.py --index 1
python merge_2k_frames.py --index 2 --force

# 处理所有可用的index（默认模式）
python merge_2k_frames.py
python merge_2k_frames.py --force

# 使用不同的编码速度
python merge_2k_frames.py --speed fastest  # 最快模式，质量稍差但速度最快
python merge_2k_frames.py --speed fast     # 快速模式（默认）
python merge_2k_frames.py --speed balanced # 平衡模式，质量最好但速度较慢

# 查看ffmpeg命令但不执行
python merge_2k_frames.py --index 1 --dry-run
"""

import os
import sys
import platform
import argparse
import subprocess
from pathlib import Path


def check_system_type():
    """检查系统类型并返回相关信息"""
    system = platform.system()
    
    if system == "Linux":
        # 检查是否为Ubuntu
        try:
            with open("/etc/os-release", "r") as f:
                content = f.read()
                if "Ubuntu" in content:
                    print(f"✅ 系统检查：Ubuntu Linux (GPU加速模式)")
                    return "ubuntu", True  # Ubuntu, 支持GPU
                else:
                    print(f"✅ 系统检查：Linux (CPU模式)")
                    return "linux", False  # 其他Linux, CPU模式
        except FileNotFoundError:
            print(f"✅ 系统检查：Linux (CPU模式)")
            return "linux", False
    
    elif system == "Darwin":
        # Mac系统，检查芯片类型
        machine = platform.machine()
        if machine == "arm64":
            print(f"✅ 系统检查：macOS Apple Silicon (CPU模式)")
        else:
            print(f"✅ 系统检查：macOS Intel (CPU模式)")
        return "mac", False  # Mac, CPU模式
    
    else:
        print(f"✅ 系统检查：{system} (CPU模式)")
        return "other", False  # 其他系统, CPU模式


def get_base_media_path(system_type: str) -> str:
    """根据系统类型返回媒体基础路径"""
    if system_type == "ubuntu":
        return "/mnt/dhl/beauty"
    elif system_type == "mac":
        return "/Volumes/dhl/beauty"
    else:
        return "/media/dhl/beauty"


def check_ffmpeg():
    """检查ffmpeg是否可用"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        # 获取ffmpeg版本信息的第一行
        version_line = result.stdout.split('\n')[0]
        print(f"✅ ffmpeg 已安装: {version_line}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"❌ 错误：未找到ffmpeg命令")
        print(f"   请安装ffmpeg: sudo apt install ffmpeg")
        return False


def check_gpu_support(use_gpu: bool) -> bool:
    """检查GPU支持情况"""
    if not use_gpu:
        print(f"ℹ️ 使用CPU模式进行视频编码")
        return True
    
    try:
        # 检查nvidia-smi命令
        result = subprocess.run(
            ["nvidia-smi"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        print(f"✅ NVIDIA GPU 可用，将使用GPU加速")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"⚠️ 警告：未检测到NVIDIA GPU，将回退到CPU模式")
        return False


def get_available_indices(base_path: str) -> list:
    """获取所有可用的index（从face_sr_frames目录扫描）"""
    frames_dir = os.path.join(base_path, "face_sr_frames")
    
    if not os.path.exists(frames_dir):
        print(f"❌ 错误：face_sr_frames目录不存在 {frames_dir}")
        return []
    
    indices = []
    for dirname in os.listdir(frames_dir):
        # 排除Mac产生的点文件
        if dirname.startswith("."):
            continue
            
        dir_path = os.path.join(frames_dir, dirname)
        if os.path.isdir(dir_path):
            try:
                index = int(dirname)
                # 检查是否有jpg文件
                jpg_files = [f for f in os.listdir(dir_path) 
                            if f.endswith(".jpg") and not f.startswith(".")]
                if jpg_files:
                    indices.append(index)
                else:
                    print(f"⚠️ 跳过空目录: {dirname}")
            except ValueError:
                print(f"⚠️ 跳过非数字命名的目录: {dirname}")
                continue
    
    indices.sort()
    return indices


def check_input_frames(input_dir: str) -> dict:
    """检查输入帧文件"""
    if not os.path.exists(input_dir):
        print(f"❌ 错误：输入目录不存在 {input_dir}")
        return {"valid": False}
    
    jpg_files = []
    for filename in os.listdir(input_dir):
        # 排除Mac产生的点文件
        if filename.startswith("."):
            continue
            
        if filename.endswith(".jpg"):
            jpg_files.append(filename)
    
    if not jpg_files:
        print(f"❌ 错误：输入目录中未找到jpg文件 {input_dir}")
        return {"valid": False}
    
    jpg_files.sort()
    
    # 获取第一张图片的分辨率信息
    first_image = os.path.join(input_dir, jpg_files[0])
    try:
        result = subprocess.run([
            "ffprobe", "-v", "quiet", "-print_format", "json", 
            "-show_streams", first_image
        ], capture_output=True, text=True, check=True)
        
        import json
        probe_data = json.loads(result.stdout)
        width = probe_data["streams"][0]["width"]
        height = probe_data["streams"][0]["height"]
        
        print(f"✅ 输入帧文件检查通过")
        print(f"📁 输入目录: {input_dir}")
        print(f"📊 jpg文件数量: {len(jpg_files)}")
        print(f"📏 图像分辨率: {width}x{height}")
        print(f"📝 首个文件: {jpg_files[0]}")
        print(f"📝 最后文件: {jpg_files[-1]}")
        
        return {
            "valid": True,
            "files": jpg_files,
            "count": len(jpg_files),
            "width": width,
            "height": height
        }
        
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
        print(f"⚠️ 无法获取图像分辨率信息，继续处理: {e}")
        print(f"✅ 输入帧文件检查通过")
        print(f"📁 输入目录: {input_dir}")
        print(f"📊 jpg文件数量: {len(jpg_files)}")
        print(f"📝 首个文件: {jpg_files[0]}")
        print(f"📝 最后文件: {jpg_files[-1]}")
        
        return {
            "valid": True,
            "files": jpg_files,
            "count": len(jpg_files),
            "width": None,
            "height": None
        }


def check_output_status(output_file: str) -> bool:
    """检查输出视频是否已存在（用于断点续传）"""
    if os.path.exists(output_file):
        # 检查文件大小，确保不是空文件
        file_size = os.path.getsize(output_file)
        if file_size > 1024:  # 至少1KB
            return True
    return False


def build_ffmpeg_command(input_dir: str, output_file: str, use_gpu: bool, frame_info: dict, speed_level: str = "fast") -> list:
    """构建ffmpeg命令"""
    
    # 基础命令
    cmd = ["ffmpeg"]
    
    # GPU加速参数
    if use_gpu:
        cmd.extend(["-hwaccel", "cuda"])
    
    # 检查文件命名模式并确定最佳输入方式
    files = frame_info.get("files", [])
    use_sequence = False
    
    if files:
        # 检查是否为连续数字命名
        try:
            # 提取文件名（不含扩展名）并检查是否为数字
            file_numbers = []
            for f in files:
                name_without_ext = os.path.splitext(f)[0]
                if name_without_ext.isdigit():
                    file_numbers.append(int(name_without_ext))
                else:
                    break
            
            if len(file_numbers) == len(files):
                # 所有文件都是数字命名，检查是否连续
                file_numbers.sort()
                if file_numbers == list(range(file_numbers[0], file_numbers[-1] + 1)):
                    use_sequence = True
                    start_number = file_numbers[0]
        except:
            pass
    
    # 构建输入参数
    if use_sequence:
        # 使用数字序列模式（最高效）
        cmd.extend([
            "-framerate", "24",
            "-start_number", str(start_number),
            "-i", os.path.join(input_dir, "%d.jpg"),
            "-r", "24",
        ])
        print(f"📋 使用数字序列模式：%d.jpg (起始: {start_number})")
    else:
        # 使用glob模式（兼容性最好）
        cmd.extend([
            "-framerate", "24",
            "-pattern_type", "glob",
            "-i", os.path.join(input_dir, "*.jpg"),
            "-r", "24",
        ])
        print(f"📋 使用glob模式：*.jpg")
    
    # 视频滤镜：调整分辨率为2560x1440，保持宽高比，添加黑边
    # scale: 缩放到最大能容纳在2560x1440内的尺寸
    # pad: 添加黑边到2560x1440
    video_filter = "scale=2560:1440:force_original_aspect_ratio=decrease,pad=2560:1440:(ow-iw)/2:(oh-ih)/2:black"
    cmd.extend(["-vf", video_filter])
    
    # 编码参数 - 根据速度级别选择不同的优化策略
    if use_gpu:
        if speed_level == "fastest":
            # 最激进的速度优化
            cmd.extend([
                "-c:v", "h264_nvenc",     # NVIDIA GPU编码器
                "-preset", "p1",          # NVENC最快预设
                "-tune", "ll",            # 低延迟调优 (比hq更快)
                "-rc", "cbr",             # 恒定比特率 (更快但文件更大)
                "-b:v", "30M",            # 固定30M比特率
                "-maxrate", "30M",        # 最大比特率
                "-bufsize", "60M",        # 缓冲区大小
                "-spatial_aq", "0",       # 禁用空间AQ (更快)
                "-temporal_aq", "0",      # 禁用时间AQ (更快)
                "-gpu", "0",              # 指定GPU 0
                "-2pass", "0",            # 禁用两步编码
            ])
            print(f"🚀 GPU最快模式: p1预设 + 低延迟调优 + 恒定比特率")
        elif speed_level == "fast":
            # 平衡速度和质量
            cmd.extend([
                "-c:v", "h264_nvenc",     # NVIDIA GPU编码器
                "-preset", "p1",          # NVENC最快预设
                "-tune", "hq",            # 高质量调优
                "-rc", "vbr",             # 可变比特率模式
                "-cq", "28",              # 恒定质量 (稍微降低质量换取速度)
                "-b:v", "0",              # 禁用目标比特率限制
                "-maxrate", "40M",        # 最大比特率40M
                "-bufsize", "80M",        # 缓冲区大小
                "-spatial_aq", "1",       # 启用空间自适应量化
                "-temporal_aq", "1",      # 启用时间自适应量化
                "-gpu", "0",              # 指定GPU 0
            ])
            print(f"🚀 GPU快速模式: p1预设 + 高质量调优 + 可变比特率")
        else:  # balanced
            # 原来的设置，平衡质量和速度
            cmd.extend([
                "-c:v", "h264_nvenc",     # NVIDIA GPU编码器
                "-preset", "p2",          # 稍慢但质量更好的预设
                "-tune", "hq",            # 高质量调优
                "-rc", "vbr",             # 可变比特率模式
                "-cq", "25",              # 恒定质量模式
                "-b:v", "0",              # 禁用目标比特率限制
                "-maxrate", "50M",        # 最大比特率50M
                "-bufsize", "100M",       # 缓冲区大小
                "-spatial_aq", "1",       # 空间自适应量化
                "-temporal_aq", "1",      # 时间自适应量化
                "-gpu", "0",              # 指定GPU 0
            ])
            print(f"🚀 GPU平衡模式: p2预设 + 高质量调优 + VBR")
    else:
        if speed_level == "fastest":
            cmd.extend([
                "-c:v", "libx264",        # CPU编码器  
                "-preset", "ultrafast",   # 最快的x264预设
                "-crf", "30",             # 降低质量要求
                "-tune", "zerolatency",   # 零延迟调优
            ])
        elif speed_level == "fast":
            cmd.extend([
                "-c:v", "libx264",        # CPU编码器  
                "-preset", "faster",      # 更快的x264预设
                "-crf", "28",             # 稍微放宽质量要求
            ])
        else:  # balanced
            cmd.extend([
                "-c:v", "libx264",        # CPU编码器  
                "-preset", "fast",        # 快速x264预设
                "-crf", "25",             # 平衡质量设置
            ])
    
    # 输出参数
    cmd.extend([
        "-pix_fmt", "yuv420p",     # 像素格式
        "-y",                      # 覆盖输出文件
        output_file
    ])
    
    return cmd


def run_ffmpeg_merge(input_dir: str, output_file: str, use_gpu: bool, frame_info: dict, speed_level: str = "fast", dry_run: bool = False) -> bool:
    """运行ffmpeg合并视频"""
    try:
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 构建ffmpeg命令
        cmd = build_ffmpeg_command(input_dir, output_file, use_gpu, frame_info, speed_level)
        
        print(f"🔧 ffmpeg命令:")
        print(f"   {' '.join(cmd)}")
        
        if dry_run:
            print(f"🔍 干运行模式：仅显示命令，不执行")
            return True
        
        print(f"🚀 开始合并视频...")
        print(f"📁 输入目录: {input_dir}")
        print(f"📤 输出文件: {output_file}")
        print(f"🎯 目标分辨率: 2560x1440")
        print(f"🎬 帧率: 24fps")
        print(f"⚙️ 编码模式: {'GPU (NVENC)' if use_gpu else 'CPU (x264)'}")
        
        # 执行ffmpeg命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        print(f"✅ 视频合并完成!")
        
        # 检查输出文件
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            file_size_mb = file_size / (1024 * 1024)
            print(f"📊 输出文件大小: {file_size_mb:.2f} MB")
            
            # 获取视频信息
            try:
                probe_result = subprocess.run([
                    "ffprobe", "-v", "quiet", "-print_format", "json",
                    "-show_streams", output_file
                ], capture_output=True, text=True, check=True)
                
                import json
                probe_data = json.loads(probe_result.stdout)
                video_stream = next((s for s in probe_data["streams"] if s["codec_type"] == "video"), None)
                
                if video_stream:
                    duration = float(video_stream.get("duration", 0))
                    width = video_stream.get("width", 0)
                    height = video_stream.get("height", 0)
                    print(f"📹 视频信息: {width}x{height}, 时长: {duration:.2f}秒")
                
            except Exception as e:
                print(f"⚠️ 无法获取视频详细信息: {e}")
            
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
        return False
    except Exception as e:
        print(f"❌ 视频合并过程出错: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Beauty 2K视频合并工具",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  # 处理单个index
  python merge_2k_frames.py --index 1
  python merge_2k_frames.py --index 2 --force
  
  # 处理所有可用的index（默认模式）
  python merge_2k_frames.py
  python merge_2k_frames.py --force
  
  # 使用不同的编码速度
  python merge_2k_frames.py --speed fastest  # 最快模式
  python merge_2k_frames.py --speed fast     # 快速模式（默认）
  python merge_2k_frames.py --speed balanced # 平衡模式
  
  # 查看ffmpeg命令但不执行
  python merge_2k_frames.py --index 1 --dry-run
  
功能说明:
  1. 将RealESRGAN处理后的帧合并为2K MP4视频
  2. 智能系统检测：Ubuntu使用GPU加速，其他系统使用CPU
  3. 自动分辨率调整：上下顶格，左右添加等宽黑边到2560x1440
  4. 支持断点续传，自动跳过已处理的视频
  5. 输出24fps的高质量MP4视频
  6. 三种编码速度级别：
     - fastest: 最快编码，适合大批量处理
     - fast: 快速编码（默认），速度与质量平衡
     - balanced: 平衡编码，质量最好但速度较慢
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
        "--dry-run", 
        action="store_true", 
        help="查看ffmpeg命令但不执行（用于调试）"
    )
    
    parser.add_argument(
        "--speed", 
        choices=["fastest", "fast", "balanced"], 
        default="fast",
        help="编码速度级别：fastest(最快，质量稍差，文件稍大), fast(快速，默认), balanced(平衡质量和速度)"
    )
    
    args = parser.parse_args()
    
    print("🚀 Beauty 2K视频合并工具")
    print("=" * 50)
    
    # 显示速度级别设置
    speed_descriptions = {
        "fastest": "最快模式 (p1预设 + 低延迟调优，质量稍差但速度最快)",
        "fast": "快速模式 (p1预设 + 高质量调优，速度与质量平衡)",
        "balanced": "平衡模式 (p2预设 + 高质量调优，质量最好但速度较慢)"
    }
    print(f"⚡ 编码速度级别: {args.speed} - {speed_descriptions[args.speed]}")
    
    # 检查系统类型
    system_type, gpu_capable = check_system_type()
    
    # 检查ffmpeg
    if not check_ffmpeg():
        return 1
    
    # 检查GPU支持
    use_gpu = gpu_capable and check_gpu_support(gpu_capable)
    
    # 获取基础路径
    base_path = get_base_media_path(system_type)
    
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
            print("❌ 未找到任何可处理的face_sr_frames目录")
            return 1
        print(f"📂 自动发现 {len(indices_to_process)} 个index: {indices_to_process}")
    
    # 统计变量
    total_count = len(indices_to_process)
    success_count = 0
    failed_indices = []
    
    print(f"🎯 开始处理 {total_count} 个帧目录...")
    
    # 逐个处理每个index
    for i, index in enumerate(indices_to_process, 1):
        print(f"\n{'='*20} 处理 {i}/{total_count}: index {index} {'='*20}")
        
        # 构建路径
        input_dir = os.path.join(base_path, "face_sr_frames", str(index))
        output_dir = os.path.join(base_path, "merged_2k_videos")
        output_file = os.path.join(output_dir, f"{index}.mp4")
        
        print(f"📁 输入目录: {input_dir}")
        print(f"📤 输出文件: {output_file}")
        
        # 检查输入文件
        frame_info = check_input_frames(input_dir)
        if not frame_info["valid"]:
            print(f"❌ 跳过index {index}：输入文件检查失败")
            failed_indices.append(index)
            continue
        
        # 检查输出状态（断点续传）
        if not args.force and not args.dry_run:
            if check_output_status(output_file):
                print(f"✅ 跳过index {index}：视频已存在")
                success_count += 1
                continue
        
        # 运行ffmpeg合并
        success = run_ffmpeg_merge(input_dir, output_file, use_gpu, frame_info, args.speed, args.dry_run)
        
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
        print(f"🎉 所有视频合并成功!")
        print(f"📁 输出目录: {os.path.join(base_path, 'merged_2k_videos')}")
        return 0


if __name__ == "__main__":
    sys.exit(main()) 