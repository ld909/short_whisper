#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Beauty视频合并工具

功能说明：
此脚本用于将face_sr_frames.py生成的人脸超分辨率帧合并为标准4K分辨率的MP4视频。

主要功能：
1. 只支持Ubuntu系统运行
2. 将分散的jpg帧文件合并为MP4视频
3. 自动转换为标准4K分辨率（3840x2160）
4. 使用硬件加速提高处理速度
5. 上下边沿顶格，左右居中并补充黑边（如需要）
6. 支持单个index处理或批量处理所有可用index
7. 支持断点续传，自动跳过已处理的视频
8. 自动排除Mac系统产生的点文件

输入路径：
- Ubuntu: /mnt/dhl/beauty/face_sr_frames/[index]/*.jpg

输出路径：
- Ubuntu: /mnt/dhl/beauty/mp4_silent/[index].mp4

分辨率转换：
- 输入分辨率：4992x2816
- 输出分辨率：3840x2160 (标准4K)
- 处理方式：缩放至合适尺寸，上下顶格，左右居中补黑边

依赖环境：
- Ubuntu操作系统
- ffmpeg（支持硬件加速更佳）

使用方法：
# 处理单个index
python merge_beauty_clips.py --index 1
python merge_beauty_clips.py --index 2 --force

# 处理所有可用的index（默认模式）
python merge_beauty_clips.py
python merge_beauty_clips.py --force --fps 25
"""

import os
import sys
import platform
import argparse
import subprocess
from pathlib import Path
import re


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


def check_gpu_availability():
    """检查GPU可用性"""
    gpu_info = {
        'nvidia_gpu': False,
        'nvidia_driver': False,
        'cuda_available': False,
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
            gpu_info['nvidia_driver'] = True
            
            # 解析GPU信息
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
        print(f"⚠️ 未检测到NVIDIA GPU或驱动")
    
    # 检查CUDA可用性
    # 对于NVENC编码，主要需要NVIDIA驱动，不一定需要nvcc编译器
    if gpu_info['nvidia_gpu']:
        # 首先尝试检查nvcc（CUDA开发工具包）
        nvcc_available = False
        try:
            result = subprocess.run(
                ["nvcc", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            if result.returncode == 0:
                nvcc_available = True
                # 提取CUDA版本
                import re
                version_match = re.search(r'release (\d+\.\d+)', result.stdout)
                if version_match:
                    cuda_version = version_match.group(1)
                    print(f"✅ CUDA开发工具包可用，版本: {cuda_version}")
                else:
                    print(f"✅ CUDA开发工具包可用")
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # 检查CUDA运行时库（更重要的是这个）
        cuda_runtime_available = False
        try:
            # 检查常见的CUDA运行时库路径
            cuda_paths = [
                "/usr/local/cuda/lib64/libcudart.so",
                "/usr/lib/x86_64-linux-gnu/libcudart.so",
                "/opt/cuda/lib64/libcudart.so"
            ]
            
            for cuda_path in cuda_paths:
                if os.path.exists(cuda_path):
                    cuda_runtime_available = True
                    print(f"✅ CUDA运行时库可用: {cuda_path}")
                    break
        except:
            pass
        
        # 对于NVENC，有NVIDIA GPU就基本可用
        if nvcc_available or cuda_runtime_available:
            gpu_info['cuda_available'] = True
            print(f"✅ CUDA环境完整，NVENC编码完全可用")
        else:
            # 即使没检测到CUDA，NVENC仍然可能可用（现代NVIDIA驱动包含）
            gpu_info['cuda_available'] = True  # 假设可用
            print(f"✅ NVIDIA GPU可用，NVENC编码应该可用")
            print(f"   注意：未检测到CUDA开发工具包，但NVENC仍可正常工作")
    else:
        print(f"⚠️ 无NVIDIA GPU，CUDA不适用")
    
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
            print(f"   建议安装支持硬件加速的ffmpeg版本")
        
        return True, has_nvenc, has_vaapi, has_qsv
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"❌ 错误：未找到ffmpeg命令")
        print(f"   请安装ffmpeg: sudo apt update && sudo apt install ffmpeg")
        return False, False, False, False


def get_available_indices(base_path: str) -> list:
    """获取所有可用的index（从face_sr_frames目录扫描）"""
    face_sr_frames_dir = os.path.join(base_path, "face_sr_frames")
    
    if not os.path.exists(face_sr_frames_dir):
        print(f"❌ 错误：face_sr_frames目录不存在 {face_sr_frames_dir}")
        return []
    
    indices = []
    for dirname in os.listdir(face_sr_frames_dir):
        # 排除Mac产生的点文件
        if dirname.startswith("."):
            continue
            
        dir_path = os.path.join(face_sr_frames_dir, dirname)
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


def check_input_frames(input_dir: str) -> tuple:
    """检查输入帧文件，返回(文件列表, 帧数量)"""
    if not os.path.exists(input_dir):
        print(f"❌ 错误：输入目录不存在 {input_dir}")
        return [], 0
    
    jpg_files = []
    for filename in os.listdir(input_dir):
        # 排除Mac产生的点文件
        if filename.startswith("."):
            continue
            
        if filename.endswith(".jpg"):
            jpg_files.append(filename)
    
    if not jpg_files:
        print(f"❌ 错误：输入目录中未找到jpg文件 {input_dir}")
        return [], 0
    
    # 按数字顺序排序
    def extract_number(filename):
        match = re.search(r'(\d+)', filename)
        return int(match.group(1)) if match else 0
    
    jpg_files.sort(key=extract_number)
    
    print(f"✅ 输入帧文件检查通过")
    print(f"📁 输入目录: {input_dir}")
    print(f"📊 jpg文件数量: {len(jpg_files)}")
    print(f"📝 首个文件: {jpg_files[0]}")
    print(f"📝 最后文件: {jpg_files[-1]}")
    
    return jpg_files, len(jpg_files)


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


def create_mp4_video(input_dir: str, output_file: str, fps: int = 30, 
                     has_nvenc: bool = False, has_vaapi: bool = False, 
                     has_qsv: bool = False, gpu_info: dict = None) -> bool:
    """使用ffmpeg创建MP4视频，优化GPU使用"""
    try:
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        print(f"🎬 开始创建MP4视频...")
        print(f"📁 输入目录: {input_dir}")
        print(f"📤 输出文件: {output_file}")
        print(f"🎞️ 帧率: {fps} fps")
        
        # 检查输入文件模式
        jpg_files = [f for f in os.listdir(input_dir) 
                    if f.endswith(".jpg") and not f.startswith(".")]
        if not jpg_files:
            print(f"❌ 错误：未找到输入文件")
            return False
        
        # 尝试不同的文件名模式
        first_file = sorted(jpg_files, key=lambda x: int(re.search(r'(\d+)', x).group(1)))[0]
        
        # 构建ffmpeg命令
        cmd = ["ffmpeg", "-y"]  # -y 覆盖输出文件
        
        # 输入参数
        cmd.extend(["-framerate", str(fps)])
        
        # 尝试不同的输入模式
        if re.match(r'^\d+\.jpg$', first_file):
            # 文件名格式：1.jpg, 2.jpg, ...
            input_pattern = os.path.join(input_dir, "%d.jpg")
        elif re.match(r'^.*_\d+\.jpg$', first_file):
            # 文件名格式：prefix_1.jpg, prefix_2.jpg, ...
            cmd.extend(["-pattern_type", "glob"])
            input_pattern = os.path.join(input_dir, "*.jpg")
        else:
            # 通用模式
            cmd.extend(["-pattern_type", "glob"])
            input_pattern = os.path.join(input_dir, "*.jpg")
        
        cmd.extend(["-i", input_pattern])
        
        # 根据硬件加速类型优化视频滤镜
        # 简化GPU选择逻辑：优先使用NVIDIA GPU，如果没有就使用Intel GPU
        # 如果检测到GPU，直接使用，不依赖ffmpeg硬件加速检查
        if gpu_info and gpu_info.get('nvidia_gpu', False):
            # NVIDIA GPU加速：使用CPU滤镜 + NVENC编码器（更稳定）
            print(f"🚀 使用NVIDIA GPU加速处理")
            video_filter = "scale=3840:2160:force_original_aspect_ratio=decrease,pad=3840:2160:(ow-iw)/2:(oh-ih)/2:black"
            cmd.extend(["-vf", video_filter])
            
            # NVIDIA编码器优化参数
            cmd.extend(["-c:v", "h264_nvenc"])
            cmd.extend(["-preset", "fast"])     # 使用标准预设
            cmd.extend(["-tune", "hq"])         # 高质量调优
            cmd.extend(["-rc", "vbr"])          # 可变比特率
            cmd.extend(["-cq", "18"])           # 质量参数
            cmd.extend(["-b:v", "50M"])         # 目标比特率（4K需要更高）
            cmd.extend(["-maxrate", "75M"])     # 最大比特率
            cmd.extend(["-bufsize", "150M"])    # 缓冲区大小
            
        elif gpu_info and gpu_info.get('intel_gpu', False):
            # Intel GPU加速：优先使用Quick Sync，回退到VAAPI
            print(f"🚀 使用Intel GPU加速处理")
            # 先尝试Quick Sync
            video_filter = "scale=3840:2160:force_original_aspect_ratio=decrease,pad=3840:2160:(ow-iw)/2:(oh-ih)/2:black"
            cmd.extend(["-vf", video_filter])
            cmd.extend(["-c:v", "h264_qsv"])
            cmd.extend(["-preset", "fast"])
            cmd.extend(["-global_quality", "18"])
            
        else:
            # 软件编码（fallback）
            print(f"⚠️ 使用CPU软件编码")
            video_filter = "scale=3840:2160:force_original_aspect_ratio=decrease,pad=3840:2160:(ow-iw)/2:(oh-ih)/2:black"
            cmd.extend(["-vf", video_filter])
            cmd.extend(["-c:v", "libx264"])
            cmd.extend(["-preset", "fast"])
            cmd.extend(["-crf", "18"])
        
        # 通用输出参数
        cmd.extend(["-pix_fmt", "yuv420p"])  # 兼容性
        cmd.extend(["-movflags", "+faststart"])  # 优化流媒体播放
        
        # 针对4K视频的额外优化
        if gpu_info and gpu_info.get('nvidia_gpu', False):
            cmd.extend(["-profile:v", "high"])
            cmd.extend(["-level", "5.1"])  # 支持4K的级别
        
        cmd.append(output_file)
        
        print(f"🔧 执行命令: {' '.join(cmd)}")
        
        # 执行ffmpeg命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        print(f"✅ MP4视频创建完成!")
        
        # 检查输出文件
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"📊 输出文件大小: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
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
            return create_mp4_video(input_dir, output_file, fps, False, False, False, None)
        
        return False
    except Exception as e:
        print(f"❌ 视频创建过程出错: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Beauty视频合并工具",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  # 处理单个index
  python merge_beauty_clips.py --index 1
  python merge_beauty_clips.py --index 2 --force --fps 25
  
  # 处理所有可用的index（默认模式）
  python merge_beauty_clips.py
  python merge_beauty_clips.py --force --fps 30
  
 功能说明:
   1. 将face_sr_frames.py生成的帧合并为MP4视频
   2. 自动转换为标准4K分辨率（3840x2160）
   3. 上下边沿顶格，左右居中并补充黑边
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
        "--fps", 
        type=int, 
        default=24,
        help="视频帧率 (默认: 24)"
    )
    
    args = parser.parse_args()
    
    print("🚀 Beauty视频合并工具")
    print("=" * 50)
    
    # 检查操作系统
    if not check_ubuntu_system():
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
        print(f"   建议安装支持的GPU以提高处理速度")
    
    # 验证帧率参数
    if args.fps <= 0 or args.fps > 120:
        print("❌ 错误：帧率必须在1-120之间")
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
            print("❌ 未找到任何可处理的face_sr_frames目录")
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
        input_dir = os.path.join(base_path, "face_sr_frames", str(index))
        output_dir = os.path.join(base_path, "mp4_silent")
        output_file = os.path.join(output_dir, f"{index}.mp4")
        
        print(f"📁 输入目录: {input_dir}")
        print(f"📤 输出文件: {output_file}")
        
        # 检查输入文件
        input_files, frame_count = check_input_frames(input_dir)
        if not input_files:
            print(f"❌ 跳过index {index}：输入文件检查失败")
            failed_indices.append(index)
            continue
        
        # 检查输出状态（断点续传）
        if not args.force:
            if check_output_status(output_file):
                print(f"✅ 跳过index {index}：视频已存在")
                success_count += 1
                continue
        
        # 创建MP4视频
        success = create_mp4_video(
            input_dir, output_file, args.fps, has_nvenc, has_vaapi, has_qsv, gpu_info
        )
        
        if success:
            print(f"✅ index {index} 处理成功! ({frame_count} 帧)")
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
        print(f"🎉 所有视频处理成功!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
