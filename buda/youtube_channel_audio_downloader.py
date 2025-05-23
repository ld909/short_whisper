#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube频道音频下载脚本
从channel.txt文件读取YouTube频道URL，下载所有频道的最高质量音频
支持断点续传，不重复下载已存在的文件
处理中文频道名和视频名
"""

import os
import sys
from pathlib import Path
import time
import re
import logging
from yt_dlp import YoutubeDL

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("youtube_download.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# 输出目录
OUTPUT_DIR = "/Volumes/dhl/buda_videos_youtube/channel_mp3_raw"


def cleanup_non_mp3_files(directory):
    """清理目录中的非mp3文件和以点开头的meta类型文件"""
    logger.info(f"开始清理目录: {directory}")

    if not os.path.exists(directory):
        logger.info(f"目录不存在，跳过清理: {directory}")
        return

    total_deleted = 0

    # 遍历所有子目录
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            should_delete = False

            # 删除以点开头的文件（meta文件等）
            if file.startswith("."):
                should_delete = True
                logger.info(f"删除meta文件: {file_path}")

            # 删除非mp3文件
            elif not file.lower().endswith(".mp3"):
                should_delete = True
                logger.info(f"删除非mp3文件: {file_path}")

            if should_delete:
                try:
                    os.remove(file_path)
                    total_deleted += 1
                except Exception as e:
                    logger.error(f"删除文件失败 {file_path}: {str(e)}")

    logger.info(f"清理完成，共删除 {total_deleted} 个文件")


def sanitize_filename(filename):
    """清理文件名，保留中文字符但去除非法字符"""
    # 替换Windows和Unix系统中不允许的文件名字符
    illegal_chars = r'[<>:"/\\|?*]'
    return re.sub(illegal_chars, "_", filename)


def create_output_dir(channel_name):
    """创建输出目录"""
    channel_dir = os.path.join(OUTPUT_DIR, sanitize_filename(channel_name))
    os.makedirs(channel_dir, exist_ok=True)
    return channel_dir


def my_hook(d):
    """下载进度回调函数"""
    if d["status"] == "downloading":
        try:
            percent = d["_percent_str"]
            speed = d["_speed_str"]
            eta = d["_eta_str"]
            logger.info(f"下载进度: {percent} 速度: {speed} 预计剩余时间: {eta}")
        except Exception as e:
            logger.debug(f"处理进度信息时出错: {str(e)}")
    elif d["status"] == "finished":
        logger.info("下载完成，开始提取音频...")


def get_channel_info(url):
    """获取频道信息"""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            logger.info(f"正在获取频道信息: {url}")
            result = ydl.extract_info(url, download=False)
            return result.get("channel", result.get("uploader", url.split("/")[-1]))
    except Exception as e:
        logger.error(f"获取频道信息失败: {str(e)}")
        return url.split("/")[-1]


def download_channel_audio(channel_url):
    """下载频道的所有音频"""
    try:
        # 获取频道名称
        channel_name = get_channel_info(channel_url)
        logger.info(f"开始处理频道: {channel_name} ({channel_url})")

        # 创建输出目录
        channel_dir = create_output_dir(channel_name)

        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "outtmpl": f"{channel_dir}/%(title)s.%(ext)s",
            "progress_hooks": [my_hook],
            "ignoreerrors": True,
            "no_overwrites": True,
            "addmetadata": True,
            "verbose": True,
            "extract_audio": True,
            "keepvideo": False,
        }

        with YoutubeDL(ydl_opts) as ydl:
            logger.info(f"开始下载频道: {channel_name}")
            error = ydl.download([channel_url])
            if error:
                logger.warning(f"下载过程中出现一些错误，但继续执行")
            else:
                logger.info(f"频道 {channel_name} 下载完成")
            return True

    except Exception as e:
        logger.error(f"下载频道时出错: {str(e)}", exc_info=True)
        return False


def process_channel_list(channel_list_file):
    """处理频道列表文件"""
    if not os.path.exists(channel_list_file):
        logger.error(f"频道列表文件不存在: {channel_list_file}")
        return False

    logger.info(f"创建输出目录: {OUTPUT_DIR}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 启动时清理非mp3文件和meta文件
    cleanup_non_mp3_files(OUTPUT_DIR)

    with open(channel_list_file, "r", encoding="utf-8") as f:
        channels = [line.strip() for line in f if line.strip()]

    total_channels = len(channels)
    successful_channels = 0
    logger.info(f"找到 {total_channels} 个频道")

    for i, channel_url in enumerate(channels, 1):
        logger.info(f"===== 处理频道 {i}/{total_channels} =====")
        logger.info(f"频道URL: {channel_url}")

        if download_channel_audio(channel_url):
            successful_channels += 1

        if i < total_channels:  # 如果不是最后一个频道，等待一下
            wait_time = 2
            logger.info(f"等待 {wait_time} 秒后继续下一个频道...")
            time.sleep(wait_time)

    logger.info(f"全部下载完成! 成功下载 {successful_channels}/{total_channels} 个频道")
    return True


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            channel_file = sys.argv[1]
        else:
            channel_file = "channel.txt"  # 默认文件名

        logger.info(f"开始处理频道列表: {channel_file}")
        process_channel_list(channel_file)
    except KeyboardInterrupt:
        logger.warning("用户中断下载")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}", exc_info=True)
        sys.exit(1)
