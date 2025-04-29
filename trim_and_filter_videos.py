#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频处理脚本：删除小于8秒的MP4视频，并将大于8秒的视频截断为前8秒
用法: python trim_and_filter_videos.py
"""

import os
import subprocess
import json
from pathlib import Path
import shutil
import tempfile

# 视频源目录
VIDEO_DIR = "/Volumes/dhl/buda_videos_youtube/mp4_clips"
# 输出目录，处理后的视频将保存在这里
OUTPUT_DIR = "/Volumes/dhl/buda_videos_youtube/mp4_clips_processed"
# 视频长度阈值（秒）
THRESHOLD_SECONDS = 8


def get_video_duration(video_path):
    """使用ffprobe获取视频时长"""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        video_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except (subprocess.SubprocessError, json.JSONDecodeError, KeyError) as e:
        print(f"获取视频 {video_path} 时长时出错: {e}")
        return None


def trim_video(input_path, output_path, duration=THRESHOLD_SECONDS):
    """截取视频前N秒"""
    # 创建临时目录用于处理
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_output = os.path.join(temp_dir, "temp_output.mp4")

        cmd = [
            "ffmpeg",
            "-i",
            input_path,
            "-t",
            str(duration),
            "-c:v",
            "copy",  # 复制视频流（不重新编码）
            "-c:a",
            "copy",  # 复制音频流
            "-y",  # 自动覆盖输出文件
            temp_output,
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            # 将临时文件移动到最终位置
            shutil.move(temp_output, output_path)
            return True
        except subprocess.SubprocessError as e:
            print(f"截取视频 {input_path} 时出错: {e}")
            return False


def main():
    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 获取所有MP4文件
    video_files = list(Path(VIDEO_DIR).glob("*.mp4"))
    total_videos = len(video_files)

    print(f"找到 {total_videos} 个MP4文件")

    deleted_count = 0
    trimmed_count = 0
    error_count = 0

    for i, video_path in enumerate(video_files, 1):
        print(f"处理进度: [{i}/{total_videos}] {video_path.name}")

        # 获取视频时长
        duration = get_video_duration(str(video_path))
        if duration is None:
            error_count += 1
            continue

        if duration < THRESHOLD_SECONDS:
            # 视频小于阈值，直接跳过（不复制到输出目录）
            print(f"  视频时长 {duration:.2f}秒 < {THRESHOLD_SECONDS}秒，跳过")
            deleted_count += 1
        else:
            # 视频长度超过阈值，截取前8秒
            output_path = os.path.join(OUTPUT_DIR, video_path.name)

            print(
                f"  视频时长 {duration:.2f}秒 > {THRESHOLD_SECONDS}秒，截取前{THRESHOLD_SECONDS}秒"
            )
            if trim_video(str(video_path), output_path):
                trimmed_count += 1
            else:
                error_count += 1

    print("\n处理完成!")
    print(f"总视频数: {total_videos}")
    print(f"已删除 (< {THRESHOLD_SECONDS}秒): {deleted_count}")
    print(f"已截断 (> {THRESHOLD_SECONDS}秒): {trimmed_count}")
    print(f"处理出错: {error_count}")


if __name__ == "__main__":
    main()
