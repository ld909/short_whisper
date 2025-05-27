#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除今天创建的视频对应的mp3文件脚本
"""

import os
import shutil
from datetime import datetime
from pathlib import Path


def find_today_created_videos():
    """查找今天创建的视频文件夹"""
    txt_base_path = Path("/Volumes/dhl/buda_videos_youtube/multi_lang_txt")
    mp3_base_path = Path("/Volumes/dhl/buda_videos_youtube/multi_lang_mp3")

    today = datetime.now().strftime("%Y-%m-%d")
    today_videos = []

    print(f"正在查找 {today} 创建的视频...")

    # 遍历txt目录下的所有子目录
    for item in txt_base_path.iterdir():
        if item.is_dir() and item.name != "." and item.name != "..":
            # 检查目录的创建时间
            creation_time = datetime.fromtimestamp(item.stat().st_ctime)
            if creation_time.strftime("%Y-%m-%d") == today:
                today_videos.append(item.name)
                print(f"找到今天创建的视频: {item.name}")

    return today_videos, mp3_base_path


def delete_mp3_folders(video_names, mp3_base_path):
    """删除对应的mp3文件夹"""
    deleted_count = 0

    for video_name in video_names:
        mp3_video_path = mp3_base_path / video_name

        if mp3_video_path.exists():
            try:
                print(f"正在删除: {mp3_video_path}")
                shutil.rmtree(mp3_video_path)
                print(f"✅ 成功删除: {video_name}")
                deleted_count += 1
            except Exception as e:
                print(f"❌ 删除失败 {video_name}: {e}")
        else:
            print(f"⚠️  mp3目录不存在: {video_name}")

    return deleted_count


def main():
    """主函数"""
    print("=" * 60)
    print("删除今天创建的视频对应的mp3文件")
    print("=" * 60)

    try:
        # 查找今天创建的视频
        today_videos, mp3_base_path = find_today_created_videos()

        if not today_videos:
            print("没有找到今天创建的视频文件夹")
            return

        print(f"\n找到 {len(today_videos)} 个今天创建的视频:")
        for i, video in enumerate(today_videos, 1):
            print(f"{i}. {video}")

        # 确认删除
        confirm = input(
            f"\n确认要删除这 {len(today_videos)} 个视频的所有mp3文件吗? (y/N): "
        )
        if confirm.lower() != "y":
            print("操作已取消")
            return

        # 删除mp3文件夹
        print("\n开始删除mp3文件...")
        deleted_count = delete_mp3_folders(today_videos, mp3_base_path)

        print(f"\n删除完成! 共删除了 {deleted_count} 个视频的mp3文件")

    except Exception as e:
        print(f"脚本执行出错: {e}")


if __name__ == "__main__":
    main()
