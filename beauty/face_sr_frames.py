#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Beauty人脸超分辨率处理工具

功能说明：
此脚本用于对extract_video_frames.py提取的帧图片进行人脸超分辨率处理。

主要功能：
1. 只支持Ubuntu系统运行
2. 使用conda base环境运行GFPGAN进行人脸超分辨率
3. 支持单个index处理或批量处理所有可用index
4. 支持断点续传，自动跳过已处理的帧
5. 自动排除Mac系统产生的点文件

输入路径：
- Ubuntu: /mnt/dhl/beauty/frames/[index]/frame*.jpg

输出路径：
- Ubuntu: /mnt/dhl/beauty/face_sr_frames/[index]/*.jpg

依赖环境：
- Ubuntu操作系统
- conda环境
- /home/dhl/Documents/GFPGAN/inference_gfpgan.py

使用方法：
# 处理单个index
python face_sr_frames.py --index 1
python face_sr_frames.py --index 2 --force

# 处理所有可用的index（默认模式）
python face_sr_frames.py
python face_sr_frames.py --force
"""

import os
import sys
import platform
import argparse
import subprocess
from pathlib import Path


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


def check_gfpgan_environment():
    """检查GFPGAN环境"""
    gfpgan_script = "/home/dhl/Documents/GFPGAN/inference_gfpgan.py"
    
    if not os.path.exists(gfpgan_script):
        print(f"❌ 错误：GFPGAN脚本不存在 {gfpgan_script}")
        return False
    
    print(f"✅ GFPGAN脚本存在: {gfpgan_script}")
    
    # 检查conda
    try:
        result = subprocess.run(
            ["conda", "--version"], capture_output=True, text=True, check=True
        )
        print(f"✅ conda 已安装: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"❌ 错误：未找到conda命令")
        print(f"   请确保已安装conda并添加到PATH环境变量")
        return False


def get_available_indices(base_path: str) -> list:
    """获取所有可用的index（从frames目录扫描）"""
    frames_dir = os.path.join(base_path, "frames")
    
    if not os.path.exists(frames_dir):
        print(f"❌ 错误：frames目录不存在 {frames_dir}")
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
                # 检查是否有frame文件
                frame_files = [f for f in os.listdir(dir_path) 
                              if f.startswith("frame") and f.endswith(".jpg") and not f.startswith(".")]
                if frame_files:
                    indices.append(index)
                else:
                    print(f"⚠️ 跳过空目录: {dirname}")
            except ValueError:
                print(f"⚠️ 跳过非数字命名的目录: {dirname}")
                continue
    
    indices.sort()
    return indices


def check_input_frames(input_dir: str) -> list:
    """检查输入帧文件"""
    if not os.path.exists(input_dir):
        print(f"❌ 错误：输入目录不存在 {input_dir}")
        return []
    
    frame_files = []
    for filename in os.listdir(input_dir):
        # 排除Mac产生的点文件
        if filename.startswith("."):
            continue
            
        if filename.startswith("frame") and filename.endswith(".jpg"):
            frame_files.append(filename)
    
    if not frame_files:
        print(f"❌ 错误：输入目录中未找到帧文件 {input_dir}")
        return []
    
    frame_files.sort()
    print(f"✅ 输入帧文件检查通过")
    print(f"📁 输入目录: {input_dir}")
    print(f"📊 帧文件数量: {len(frame_files)}")
    print(f"📝 首帧: {frame_files[0]}")
    print(f"📝 末帧: {frame_files[-1]}")
    
    return frame_files


def check_output_status(output_dir: str, input_files: list) -> dict:
    """检查输出状态，用于断点续传"""
    if not os.path.exists(output_dir):
        return {
            "completed": [], 
            "remaining": input_files,
            "completed_count": 0,
            "total_count": len(input_files)
        }
    
    completed_files = []
    for filename in os.listdir(output_dir):
        # 排除Mac产生的点文件
        if filename.startswith("."):
            continue
            
        if filename.endswith(".jpg"):
            completed_files.append(filename)
    
    # 找出还需要处理的文件
    # GFPGAN输出文件名可能与输入不完全一致，所以用简单的计数方式
    remaining_files = input_files[len(completed_files):]
    
    return {
        "completed": completed_files,
        "remaining": remaining_files,
        "completed_count": len(completed_files),
        "total_count": len(input_files)
    }


def run_gfpgan(input_dir: str, output_dir: str) -> bool:
    """运行GFPGAN进行人脸超分辨率处理"""
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        gfpgan_script = "/home/dhl/Documents/GFPGAN/inference_gfpgan.py"
        
        print(f"🔧 开始运行GFPGAN...")
        print(f"📁 输入目录: {input_dir}")
        print(f"📤 输出目录: {output_dir}")
        
        # 构建conda命令
        cmd = [
            "conda", "run", "-n", "base",  # 使用conda base环境
            "python", gfpgan_script,
            "-i", input_dir,
            "-o", output_dir,
            "-v", "1.4",      # GFPGAN版本
            "-s", "2"         # 放大倍数
        ]
        
        print(f"🔧 执行命令: {' '.join(cmd)}")
        
        # 切换到GFPGAN目录执行
        gfpgan_dir = "/home/dhl/Documents/GFPGAN"
        
        # 执行命令
        result = subprocess.run(
            cmd, 
            cwd=gfpgan_dir,
            capture_output=True, 
            text=True, 
            check=True
        )
        
        print(f"✅ GFPGAN处理完成!")
        
        # 检查输出文件
        if os.path.exists(output_dir):
            output_files = [f for f in os.listdir(output_dir) 
                           if f.endswith(".jpg") and not f.startswith(".")]
            print(f"📊 生成文件数量: {len(output_files)}")
            return len(output_files) > 0
        else:
            print(f"❌ 输出目录未创建")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ GFPGAN执行失败:")
        print(f"   错误代码: {e.returncode}")
        if e.stdout:
            print(f"   标准输出: {e.stdout}")
        if e.stderr:
            print(f"   错误输出: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ GFPGAN处理过程出错: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Beauty人脸超分辨率处理工具",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  # 处理单个index
  python face_sr_frames.py --index 1
  python face_sr_frames.py --index 2 --force
  
  # 处理所有可用的index（默认模式）
  python face_sr_frames.py
  python face_sr_frames.py --force
  
功能说明:
  1. 对extract_video_frames.py提取的帧进行人脸超分辨率处理
  2. 使用GFPGAN技术提升人脸清晰度
  3. 支持断点续传，自动跳过已处理的帧
  4. 只支持Ubuntu系统运行
  5. 需要conda环境和GFPGAN
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
    
    args = parser.parse_args()
    
    print("🎭 Beauty人脸超分辨率处理工具")
    print("=" * 50)
    
    # 检查操作系统
    if not check_ubuntu_system():
        return 1
    
    # 检查GFPGAN环境
    if not check_gfpgan_environment():
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
            print("❌ 未找到任何可处理的帧目录")
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
        input_dir = os.path.join(base_path, "frames", str(index))
        output_dir = os.path.join(base_path, "face_sr_frames", str(index))
        
        print(f"📁 输入目录: {input_dir}")
        print(f"📤 输出目录: {output_dir}")
        
        # 检查输入文件
        input_files = check_input_frames(input_dir)
        if not input_files:
            print(f"❌ 跳过index {index}：输入文件检查失败")
            failed_indices.append(index)
            continue
        
        # 检查输出状态（断点续传）
        if not args.force:
            status = check_output_status(output_dir, input_files)
            if status["completed_count"] > 0:
                if status["completed_count"] >= status["total_count"]:
                    print(f"✅ 跳过index {index}：已完全处理 ({status['completed_count']} 帧)")
                    success_count += 1
                    continue
                else:
                    print(f"🔄 断点续传：已处理 {status['completed_count']}/{status['total_count']} 帧")
        
        # 运行GFPGAN处理
        success = run_gfpgan(input_dir, output_dir)
        
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
        print(f"🎉 所有帧目录处理成功!")
        return 0


if __name__ == "__main__":
    sys.exit(main()) 