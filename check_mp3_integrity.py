#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MP3文件完整性检查脚本
检查指定目录中所有MP3文件的完整性，找出损坏的文件
"""

import os
import sys
import platform
import argparse
from pathlib import Path
from mutagen.mp3 import MP3
from mutagen.mp3 import HeaderNotFoundError


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# 获取媒体基础路径
BASE_MEDIA_PATH = get_base_media_path()

# 默认检查目录（与下载脚本的输出目录一致）
DEFAULT_DIR = os.path.join(BASE_MEDIA_PATH, "channel_mp3_raw")


def check_mp3_integrity_mutagen(filepath, verbose=False):
    """检查单个MP3文件的完整性"""
    try:
        audio = MP3(filepath)
        # 检查时长和比特率是否合理
        if audio.info.length <= 0:
            print(f"❌ 损坏文件: {filepath} (时长为0或负数)")
            return False

        # 检查比特率是否异常低
        if audio.info.bitrate < 32000:  # 32kbps以下认为异常
            print(
                f"⚠️  疑似损坏: {filepath} (比特率异常低: {audio.info.bitrate // 1000} kbps)"
            )
            return False

        if verbose:
            print(
                f"✅ 文件正常: {os.path.basename(filepath)} (时长: {audio.info.length:.1f}s, 比特率: {audio.info.bitrate // 1000} kbps)"
            )
        return True

    except HeaderNotFoundError:
        print(f"❌ 损坏文件: {filepath} (找不到有效的MP3帧头)")
        return False
    except Exception as e:
        print(f"❌ 读取错误: {filepath} (错误: {e})")
        return False


def scan_directory_for_mp3(directory, skip_hidden=True):
    """扫描目录中的所有MP3文件"""
    mp3_files = []

    if not os.path.exists(directory):
        print(f"❌ 目录不存在: {directory}")
        return mp3_files

    print(f"🔍 正在扫描目录: {directory}")
    if skip_hidden:
        print("📝 跳过以 ._ 开头的隐藏文件")

    # 递归查找所有MP3文件
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".mp3"):
                # 如果启用跳过隐藏文件选项，则过滤掉以._开头的文件
                if skip_hidden and file.startswith("._"):
                    continue
                mp3_files.append(os.path.join(root, file))

    print(f"📁 找到 {len(mp3_files)} 个MP3文件待检查")
    return mp3_files


def main():
    """主函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="MP3文件完整性检查工具")
    parser.add_argument(
        "directory",
        nargs="?",
        default=DEFAULT_DIR,
        help=f"要检查的目录路径 (默认: {DEFAULT_DIR})",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="显示完整文件的详细信息"
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="包含以._开头的隐藏文件（默认跳过）",
    )

    args = parser.parse_args()

    # 获取要检查的目录
    check_dir = args.directory

    print("=" * 60)
    print("🎵 MP3文件完整性检查工具")
    print("=" * 60)

    # 扫描所有MP3文件
    mp3_files = scan_directory_for_mp3(check_dir, skip_hidden=not args.include_hidden)

    if not mp3_files:
        print("❌ 没有找到MP3文件")
        return

    print("\n🔧 开始检查文件完整性...")
    print("-" * 60)

    # 统计信息
    total_files = len(mp3_files)
    corrupted_files = []
    valid_files = 0

    # 检查每个文件
    for i, filepath in enumerate(mp3_files, 1):
        if args.verbose:
            print(f"[{i}/{total_files}] ", end="")

        if check_mp3_integrity_mutagen(filepath, args.verbose):
            valid_files += 1
        else:
            corrupted_files.append(filepath)

    # 输出总结
    print("\n" + "=" * 60)
    print("📊 检查完成 - 总结报告")
    print("=" * 60)
    print(f"总文件数: {total_files}")
    print(f"正常文件: {valid_files}")
    print(f"损坏文件: {len(corrupted_files)}")

    if corrupted_files:
        print(f"\n❌ 发现 {len(corrupted_files)} 个损坏文件:")
        print("建议重新下载这些文件。")
    else:
        print("\n🎉 所有MP3文件都完整无损！")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断检查")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        sys.exit(1)
