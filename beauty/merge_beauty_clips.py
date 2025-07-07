#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Beauty MP4 Clips 合并工具

功能说明：
此脚本用于合并Beauty项目中的MP4视频片段。支持智能排序和随机合并两种模式。

主要功能：
1. 自动检测操作系统并使用对应的硬盘根目录
2. 智能识别文件命名方式并采用对应的合并策略
3. 支持有序合并和随机合并
4. 自动排除Mac系统产生的点文件

输入路径：
- Mac: /Volumes/dhl/beauty/clips/[index]/*.mp4
- Ubuntu: /mnt/dhl/beauty/clips/[index]/*.mp4

输出路径：
- Mac: /Volumes/dhl/beauty/mp4_low_res/index.mp4
- Ubuntu: /mnt/dhl/beauty/mp4_low_res/index.mp4

合并策略：
1. 检测到数字命名文件(1.mp4, 2.mp4, ...)时：
   - 按数字顺序合并：1.mp4+2.mp4+...
   - 其他不规则命名文件随机追加
2. 未检测到数字命名文件时：
   - 所有文件随机顺序合并

使用方法：
python merge_beauty_clips.py --index 1
python merge_beauty_clips.py --index 2 --force
"""

import os
import sys
import platform
import argparse
import subprocess
import tempfile
import random
import re
from pathlib import Path
from typing import List, Tuple, Optional


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/beauty"
    else:  # 默认为Linux/Ubuntu
        return "/mnt/dhl/beauty"


def get_mp4_files(clips_dir: str) -> List[str]:
    """
    获取目录中的所有MP4文件，排除Mac的点文件
    """
    if not os.path.exists(clips_dir):
        print(f"❌ 错误：输入目录不存在 {clips_dir}")
        return []

    mp4_files = []
    for filename in os.listdir(clips_dir):
        # 排除Mac产生的点文件
        if filename.startswith("."):
            continue

        if filename.lower().endswith(".mp4"):
            full_path = os.path.join(clips_dir, filename)
            if os.path.isfile(full_path):
                mp4_files.append(full_path)

    print(f"📁 找到 {len(mp4_files)} 个MP4文件")
    return mp4_files


def classify_files(mp4_files: List[str]) -> Tuple[List[str], List[str]]:
    """
    分类文件：数字命名文件 vs 不规则命名文件
    返回：(数字命名文件列表, 不规则命名文件列表)
    """
    numbered_files = []
    irregular_files = []

    # 正则表达式匹配数字命名：纯数字.mp4
    number_pattern = re.compile(r"^(\d+)\.mp4$", re.IGNORECASE)

    for file_path in mp4_files:
        filename = os.path.basename(file_path)
        match = number_pattern.match(filename)

        if match:
            number = int(match.group(1))
            numbered_files.append((number, file_path))
        else:
            irregular_files.append(file_path)

    # 按数字排序
    numbered_files.sort(key=lambda x: x[0])
    sorted_numbered_files = [file_path for _, file_path in numbered_files]

    print(f"📊 文件分类结果:")
    print(f"   🔢 数字命名文件: {len(sorted_numbered_files)} 个")
    print(f"   🎲 不规则命名文件: {len(irregular_files)} 个")

    if sorted_numbered_files:
        print(
            f"   📋 数字文件顺序: {[os.path.basename(f) for f in sorted_numbered_files]}"
        )

    return sorted_numbered_files, irregular_files


def create_file_list(ordered_files: List[str], random_files: List[str]) -> str:
    """
    创建ffmpeg需要的文件列表文件
    返回临时文件路径
    """
    # 随机打乱不规则文件
    shuffled_random = random_files.copy()
    random.shuffle(shuffled_random)

    # 合并文件列表
    all_files = ordered_files + shuffled_random

    if not all_files:
        print("❌ 错误：没有文件可以合并")
        return None

    print(f"📝 合并顺序:")
    for i, file_path in enumerate(all_files, 1):
        filename = os.path.basename(file_path)
        print(f"   {i:2d}. {filename}")

    # 创建临时文件列表
    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
    try:
        for file_path in all_files:
            # ffmpeg需要特殊转义路径中的特殊字符
            escaped_path = file_path.replace("'", "'\"'\"'")
            temp_file.write(f"file '{escaped_path}'\n")
        temp_file.flush()
        return temp_file.name
    finally:
        temp_file.close()


def merge_videos(file_list_path: str, output_path: str) -> bool:
    """
    使用ffmpeg合并视频文件
    """
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        print(f"🎬 开始合并视频...")
        print(f"📤 输出文件: {output_path}")

        # 构建ffmpeg命令
        cmd = [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            file_list_path,
            "-c",
            "copy",  # 使用流复制，速度快
            "-y",  # 覆盖输出文件
            output_path,
        ]

        print(f"🔧 执行命令: {' '.join(cmd)}")

        # 执行ffmpeg命令
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # 检查输出文件是否成功创建
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ 视频合并成功!")
            print(f"📁 输出文件: {output_path}")
            print(f"📏 文件大小: {file_size / (1024*1024):.2f} MB")
            return True
        else:
            print(f"❌ 合并失败：输出文件未生成")
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
        print(f"❌ 合并过程出错: {e}")
        return False


def check_dependencies():
    """检查依赖项"""
    try:
        # 检查ffmpeg
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, check=True
        )
        print("✅ ffmpeg 已安装")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ 错误：未找到ffmpeg")
        print("   请安装ffmpeg:")
        if platform.system() == "Darwin":
            print("   Mac: brew install ffmpeg")
        else:
            print("   Ubuntu: sudo apt install ffmpeg")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Beauty MP4 Clips 合并工具",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  python merge_beauty_clips.py --index 1
  python merge_beauty_clips.py --index 2 --force
  
合并策略说明:
  1. 检测到数字命名文件(1.mp4, 2.mp4, ...)时：
     - 按数字顺序合并：1.mp4+2.mp4+...
     - 其他不规则命名文件随机追加
  2. 未检测到数字命名文件时：
     - 所有文件随机顺序合并
        """,
    )

    parser.add_argument(
        "--index", type=int, required=True, help="指定要处理的index目录（必填）"
    )

    parser.add_argument("--force", action="store_true", help="强制覆盖已存在的输出文件")

    args = parser.parse_args()

    # 验证参数
    if args.index <= 0:
        print("❌ 错误：index必须大于0")
        return 1

    print("🎬 Beauty MP4 Clips 合并工具")
    print("=" * 50)
    print(f"📂 处理目录: index {args.index}")
    print(f"💻 操作系统: {platform.system()}")

    # 检查依赖
    if not check_dependencies():
        return 1

    # 获取路径
    base_path = get_base_media_path()
    clips_dir = os.path.join(base_path, "clips", str(args.index))
    output_dir = os.path.join(base_path, "mp4_low_res")
    output_file = os.path.join(output_dir, f"{args.index}.mp4")

    print(f"📁 输入目录: {clips_dir}")
    print(f"📤 输出文件: {output_file}")

    # 检查输出文件是否已存在
    if os.path.exists(output_file) and not args.force:
        print(f"⚠️ 输出文件已存在: {output_file}")
        print(f"   使用 --force 参数强制覆盖")
        return 1

    # 获取MP4文件
    mp4_files = get_mp4_files(clips_dir)
    if not mp4_files:
        print("❌ 未找到任何MP4文件")
        return 1

    # 分类文件
    numbered_files, irregular_files = classify_files(mp4_files)

    # 确定合并策略
    if numbered_files:
        print(f"🎯 合并策略: 有序合并 (数字文件 + 随机文件)")
    else:
        print(f"🎯 合并策略: 随机合并 (所有文件随机顺序)")
        # 如果没有数字文件，将所有文件视为不规则文件
        irregular_files = mp4_files
        numbered_files = []

    # 创建文件列表
    file_list_path = create_file_list(numbered_files, irregular_files)
    if not file_list_path:
        return 1

    try:
        # 合并视频
        success = merge_videos(file_list_path, output_file)

        if success:
            print(f"\n🎉 合并完成!")
            print(f"📁 输出文件: {output_file}")
            return 0
        else:
            print(f"\n❌ 合并失败")
            return 1

    finally:
        # 清理临时文件
        try:
            if file_list_path and os.path.exists(file_list_path):
                os.unlink(file_list_path)
        except Exception as e:
            print(f"⚠️ 清理临时文件失败: {e}")


if __name__ == "__main__":
    sys.exit(main())
