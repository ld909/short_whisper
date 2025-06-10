#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批量字幕烧录工具

自动查找项目中的视频和字幕文件，批量烧录字幕到视频中。
支持自动匹配字幕文件，自定义参数设置。

使用方法:
python batch_burn_subtitles.py [OPTIONS]

可选参数:
- --input-dir: 输入目录，默认为当前目录
- --output-dir: 输出目录，默认为当前目录下的output文件夹
- --font-size: 字体大小，默认18
- --gpu: 启用GPU硬件加速
- --force: 强制重新生成已存在的文件
"""

import os
import glob
import argparse
import subprocess
import sys
import logging
from pathlib import Path

# 导入字幕烧录功能
from burn_subtitles_to_mp4 import burn_subtitles, check_ffmpeg

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def find_video_subtitle_pairs(input_dir):
    """查找视频和字幕文件对"""
    video_extensions = [".mp4", ".avi", ".mov", ".mkv"]
    subtitle_extensions = [".srt", ".ass", ".vtt"]

    pairs = []

    # 获取所有视频文件（排除.DS_Store等隐藏文件）
    video_files = []
    for ext in video_extensions:
        pattern = os.path.join(input_dir, "**", f"*{ext}")
        files = glob.glob(pattern, recursive=True)
        # 过滤掉隐藏文件
        files = [
            f
            for f in files
            if not any(part.startswith(".") for part in f.split(os.sep))
        ]
        video_files.extend(files)

    logger.info(f"找到 {len(video_files)} 个视频文件")

    for video_file in video_files:
        video_path = Path(video_file)
        video_base_name = video_path.stem
        video_dir = video_path.parent

        # 查找匹配的字幕文件
        subtitle_file = None

        # 先在同一目录下查找
        for ext in subtitle_extensions:
            potential_subtitle = video_dir / f"{video_base_name}{ext}"
            if potential_subtitle.exists():
                subtitle_file = str(potential_subtitle)
                break

        # 如果没找到，在根目录查找
        if not subtitle_file:
            for ext in subtitle_extensions:
                potential_subtitle = Path(input_dir) / f"{video_base_name}{ext}"
                if potential_subtitle.exists():
                    subtitle_file = str(potential_subtitle)
                    break

        if subtitle_file:
            pairs.append((str(video_file), subtitle_file))
            logger.info(f"匹配：{video_path.name} -> {Path(subtitle_file).name}")
        else:
            logger.warning(f"未找到匹配的字幕文件：{video_path.name}")

    return pairs


def batch_burn_subtitles(input_dir, output_dir, **kwargs):
    """批量烧录字幕"""

    # 查找视频字幕对
    pairs = find_video_subtitle_pairs(input_dir)

    if not pairs:
        logger.error("未找到任何视频字幕配对")
        return

    logger.info(f"找到 {len(pairs)} 个视频字幕配对")

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    success_count = 0
    force = kwargs.get("force", False)

    for i, (video_file, subtitle_file) in enumerate(pairs, 1):
        logger.info(f"\n处理第 {i}/{len(pairs)} 个文件...")

        # 构建输出文件路径
        video_path = Path(video_file)
        relative_path = video_path.relative_to(input_dir)
        output_path = (
            Path(output_dir)
            / relative_path.parent
            / f"{video_path.stem}_with_subtitles{video_path.suffix}"
        )

        # 检查输出文件是否已存在
        if output_path.exists() and not force:
            logger.info(f"输出文件已存在，跳过：{output_path}")
            continue

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 烧录字幕
        try:
            success = burn_subtitles(
                video_file, subtitle_file, str(output_path), **kwargs
            )

            if success:
                success_count += 1
                logger.info(f"成功处理：{video_path.name}")
            else:
                logger.error(f"处理失败：{video_path.name}")

        except Exception as e:
            logger.error(f"处理 {video_path.name} 时出错：{str(e)}")

    logger.info(f"\n批量处理完成！成功处理 {success_count}/{len(pairs)} 个文件")


def main():
    parser = argparse.ArgumentParser(description="批量将SRT字幕烧录到MP4视频中")
    parser.add_argument("--input-dir", default=".", help="输入目录（默认当前目录）")
    parser.add_argument(
        "--output-dir", default="./output", help="输出目录（默认./output）"
    )
    parser.add_argument("--font-size", type=int, default=18, help="字体大小（默认18）")
    parser.add_argument(
        "--font-color", default="FFFFFF", help="字体颜色（十六进制，默认FFFFFF）"
    )
    parser.add_argument(
        "--outline-color", default="000000", help="描边颜色（十六进制，默认000000）"
    )
    parser.add_argument(
        "--outline-width", type=float, default=2, help="描边宽度（默认2）"
    )
    parser.add_argument("--margin-v", type=int, default=20, help="底部边距（默认20）")
    parser.add_argument("--font-path", help="自定义字体文件路径")
    parser.add_argument("--gpu", action="store_true", help="启用GPU硬件加速")
    parser.add_argument("--force", action="store_true", help="强制重新生成已存在的文件")

    args = parser.parse_args()

    # 检查ffmpeg
    if not check_ffmpeg():
        sys.exit(1)

    # 检查输入目录
    if not os.path.exists(args.input_dir):
        logger.error(f"输入目录不存在：{args.input_dir}")
        sys.exit(1)

    # 批量处理
    batch_burn_subtitles(
        args.input_dir,
        args.output_dir,
        font_size=args.font_size,
        font_color=args.font_color,
        outline_color=args.outline_color,
        outline_width=args.outline_width,
        margin_v=args.margin_v,
        font_path=args.font_path,
        use_gpu=args.gpu,
        force=args.force,
    )


if __name__ == "__main__":
    main()
