#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自动发布系统测试脚本

用于测试auto_publish_system.py的各个功能组件
"""

import os
import sys
import pandas as pd
from datetime import datetime
from auto_publish_system import AutoPublishSystem


def test_excel_reading():
    """测试Excel文件读取功能"""
    print("=== 测试Excel文件读取 ===")

    system = AutoPublishSystem(language="en")

    # 测试获取待发布视频
    pending_videos = system.get_pending_videos()
    print(f"找到 {len(pending_videos)} 个待发布视频")

    if pending_videos:
        print("前3个视频:")
        for i, video in enumerate(pending_videos[:3], 1):
            print(f"  {i}. {video['MP4名称']}")

    print()


def test_time_calculation():
    """测试发布时间计算功能"""
    print("=== 测试发布时间计算 ===")

    system = AutoPublishSystem(language="en")

    # 测试获取最远发布时间
    latest_time = system.get_latest_publish_time()
    print(f"最远发布时间: {latest_time}")

    # 测试计算下次发布时间
    next_time = system.calculate_next_publish_time()
    print(f"下次发布时间: {next_time}")

    print()


def test_file_finding():
    """测试文件查找功能"""
    print("=== 测试文件查找功能 ===")

    system = AutoPublishSystem(language="en")

    # 获取一个测试视频
    pending_videos = system.get_pending_videos()
    if not pending_videos:
        print("没有待发布视频可供测试")
        return

    test_video = pending_videos[0]["MP4名称"]
    print(f"测试视频: {test_video}")

    # 查找频道
    channel_name = system.find_channel_name(test_video)
    print(f"找到频道: {channel_name}")

    if channel_name:
        # 获取视频内容
        video_content = system.get_video_content(test_video, channel_name)
        print(f"MP4文件存在: {os.path.exists(video_content['mp4_path'])}")
        print(
            f"标题: {video_content['title'][:50]}..."
            if len(video_content["title"]) > 50
            else f"标题: {video_content['title']}"
        )
        print(f"描述长度: {len(video_content['description'])} 字符")
        print(f"内容有效: {video_content['valid']}")

    print()


def test_excel_update():
    """测试Excel更新功能（模拟）"""
    print("=== 测试Excel更新功能 ===")

    # 注意：这里只是模拟测试，不会实际修改Excel文件
    print("模拟更新发布状态...")
    print("功能: 将'是否已经发布'设为1，记录发布时间")
    print("注意: 此测试不会实际修改Excel文件")

    print()


def test_dry_run():
    """测试试运行模式"""
    print("=== 测试试运行模式 ===")

    system = AutoPublishSystem(language="en")

    print("启动试运行模式...")
    system.run(max_count=1, dry_run=True)

    print()


def test_path_validation():
    """测试路径验证"""
    print("=== 测试路径验证 ===")

    from auto_publish_system import (
        BASE_PATH,
        MP4_DIR,
        TITLE_DIR,
        DESC_DIR,
        TRACKER_FILE,
    )

    print(f"基础路径: {BASE_PATH}")
    print(f"MP4目录: {MP4_DIR} - 存在: {os.path.exists(MP4_DIR)}")
    print(f"标题目录: {TITLE_DIR} - 存在: {os.path.exists(TITLE_DIR)}")
    print(f"描述目录: {DESC_DIR} - 存在: {os.path.exists(DESC_DIR)}")
    print(f"跟踪文件: {TRACKER_FILE} - 存在: {os.path.exists(TRACKER_FILE)}")

    print()


def test_language_support():
    """测试多语言支持"""
    print("=== 测试多语言支持 ===")

    for lang in ["en", "ko"]:
        print(f"\n测试语言: {lang}")
        system = AutoPublishSystem(language=lang)

        try:
            pending_videos = system.get_pending_videos()
            print(f"  待发布视频数量: {len(pending_videos)}")
        except Exception as e:
            print(f"  错误: {e}")

    print()


def main():
    """运行所有测试"""
    print("自动发布系统功能测试")
    print("=" * 50)
    print()

    try:
        # 检查基本环境
        test_path_validation()

        # 测试各项功能
        test_excel_reading()
        test_time_calculation()
        test_file_finding()
        test_language_support()
        test_excel_update()

        # 最后运行试运行测试
        print("准备进行试运行测试...")
        choice = input("是否进行试运行测试？(y/n): ").strip().lower()
        if choice == "y":
            test_dry_run()

    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback

        traceback.print_exc()

    print("测试完成！")


if __name__ == "__main__":
    main()
