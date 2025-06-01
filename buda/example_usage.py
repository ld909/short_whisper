#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自动发布系统使用示例

演示如何使用auto_publish_system.py进行视频发布
"""

import os
import sys
from auto_publish_system import AutoPublishSystem


def example_dry_run():
    """示例1: 试运行模式，测试系统功能"""
    print("=== 示例1: 试运行模式 ===")

    # 创建发布系统实例
    system = AutoPublishSystem(language="en")

    # 运行试运行模式，只处理1个视频
    system.run(max_count=1, dry_run=True)

    print("试运行完成，没有实际发布任何视频\n")


def example_check_status():
    """示例2: 检查当前发布状态"""
    print("=== 示例2: 检查发布状态 ===")

    for lang in ["en", "ko"]:
        system = AutoPublishSystem(language=lang)

        print(f"语言: {lang}")
        pending_videos = system.get_pending_videos()
        print(f"待发布视频数量: {len(pending_videos)}")

        if pending_videos:
            # 显示前3个待发布视频
            print("前3个待发布视频:")
            for i, video in enumerate(pending_videos[:3], 1):
                video_name = video["MP4名称"]
                # 截断长文件名
                display_name = (
                    video_name[:60] + "..." if len(video_name) > 60 else video_name
                )
                print(f"  {i}. {display_name}")
        print()


def example_time_planning():
    """示例3: 发布时间规划"""
    print("=== 示例3: 发布时间规划 ===")

    system = AutoPublishSystem(language="en")

    # 获取当前发布时间规划
    latest_time = system.get_latest_publish_time()
    next_time = system.calculate_next_publish_time()

    print(f"最远已发布时间: {latest_time}")
    print(f"下次发布时间: {next_time}")
    print(f"时间间隔: 6小时")

    print()


def example_single_video_info():
    """示例4: 单个视频信息查看"""
    print("=== 示例4: 单个视频信息 ===")

    system = AutoPublishSystem(language="en")

    # 获取第一个待发布视频
    pending_videos = system.get_pending_videos()
    if not pending_videos:
        print("没有待发布视频")
        return

    test_video = pending_videos[0]["MP4名称"]
    print(f"视频文件: {test_video[:60]}...")

    # 查找频道
    channel_name = system.find_channel_name(test_video)
    print(f"所属频道: {channel_name}")

    if channel_name:
        # 获取视频内容
        video_content = system.get_video_content(test_video, channel_name)

        print(f"标题: {video_content['title']}")
        print(f"描述长度: {len(video_content['description'])} 字符")
        print(f"描述预览: {video_content['description'][:100]}...")
        print(f"文件有效: {video_content['valid']}")

    print()


def main():
    """运行所有示例"""
    print("自动发布系统使用示例")
    print("=" * 50)
    print()

    try:
        # 检查必要文件
        if not os.path.exists("mp4_publish_tracker.xlsx"):
            print("错误: 未找到跟踪文件 mp4_publish_tracker.xlsx")
            print("请先运行 generate_mp4_publish_tracker.py")
            return

        # 运行各个示例
        example_check_status()
        example_time_planning()
        example_single_video_info()
        example_dry_run()

        print("所有示例运行完成！")
        print("\n使用提示:")
        print("1. 试运行: python auto_publish_system.py -d")
        print("2. 发布1个英语视频: python auto_publish_system.py")
        print("3. 发布3个韩语视频: python auto_publish_system.py -l ko -n 3")

    except Exception as e:
        print(f"示例运行出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
