#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import subprocess
import glob
from pathlib import Path

# 源目录（包含所有视频片段）
SOURCE_DIR = "/Volumes/dhl/buda_videos_youtube/temp_clips/temp_1745917963_71891"
# 输出目录
OUTPUT_DIR = "/Volumes/dhl/buda_videos_youtube/temp_clips"
# 输出文件名
OUTPUT_FILE = "ffmpeg_concatenated.mp4"


def create_concat_file(clip_files, concat_file_path):
    """创建ffmpeg合并列表文件"""
    with open(concat_file_path, "w") as f:
        for clip_file in clip_files:
            # 使用file协议和转义路径
            f.write(f"file '{clip_file.replace('\'', '\\\'')}'\n")
    return concat_file_path


def merge_with_ffmpeg_concat(clip_files, output_path):
    """使用ffmpeg的concat demuxer合并视频"""
    # 创建临时合并文件列表
    concat_file = os.path.join(OUTPUT_DIR, "concat_list.txt")
    create_concat_file(clip_files, concat_file)

    # 使用ffmpeg合并
    try:
        start_time = time.time()
        cmd = [
            "ffmpeg",
            "-v",
            "error",  # 只显示错误信息，不显示警告和进度
            "-f",
            "concat",
            "-safe",
            "0",  # 允许不安全的文件路径
            "-i",
            concat_file,
            "-c",
            "copy",  # 复制流而不重新编码，速度最快
            "-y",  # 覆盖已有文件
            output_path,
        ]
        print(f"执行命令: {' '.join(cmd)}")

        # 执行ffmpeg命令
        subprocess.run(cmd, check=True)

        # 计算耗时
        end_time = time.time()
        print(f"使用ffmpeg concat合并完成，耗时: {end_time - start_time:.2f}秒")

        # 检查输出文件
        if os.path.exists(output_path):
            filesize = os.path.getsize(output_path) / (1024 * 1024)  # MB
            print(f"输出文件: {output_path}")
            print(f"文件大小: {filesize:.2f} MB")

            # 获取视频时长
            duration_cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                output_path,
            ]
            duration = subprocess.check_output(duration_cmd).decode().strip()
            print(f"视频时长: {float(duration):.2f}秒")

            return True
        else:
            print(f"错误: 未能找到输出文件 {output_path}")
            return False
    except Exception as e:
        print(f"合并视频时出错: {e}")
        return False
    finally:
        # 删除临时concat文件
        if os.path.exists(concat_file):
            os.remove(concat_file)


def main():
    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 获取所有视频片段并按数字排序
    print(f"查找目录 {SOURCE_DIR} 中的视频片段...")

    # 查找所有clip_*.mp4文件并排序
    clip_files = glob.glob(os.path.join(SOURCE_DIR, "clip_*.mp4"))

    # 按数字排序（clip_1.mp4, clip_2.mp4, ..., clip_10.mp4, ...）
    clip_files.sort(key=lambda x: int(os.path.basename(x).split("_")[1].split(".")[0]))

    print(f"找到 {len(clip_files)} 个视频片段")

    if not clip_files:
        print(f"错误: 在 {SOURCE_DIR} 中未找到任何视频片段")
        return

    # 合并视频
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
    print(f"开始合并视频到 {output_path}...")
    merge_with_ffmpeg_concat(clip_files, output_path)


if __name__ == "__main__":
    main()
