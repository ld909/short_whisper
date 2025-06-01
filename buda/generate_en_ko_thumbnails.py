#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
英语和韩语视频封面批量生成脚本
针对merge_mp4_mp3.py输出的mp4_with_audio目录中的英语和韩语视频
从对应语种的视频中提取帧作为背景图片生成封面

使用方法:
1. 批量生成所有频道: python generate_en_ko_thumbnails.py
2. 指定频道: python generate_en_ko_thumbnails.py --channel "频道名称"
3. 测试单个视频: python generate_en_ko_thumbnails.py --channel "频道名称" --video "视频名称"
"""

import subprocess
import sys
import argparse
import os


def run_thumbnail_generation(channel=None, video=None):
    """运行封面生成"""
    cmd = [sys.executable, "generate_multilingual_thumbnails.py"]

    if channel:
        cmd.extend(["-c", channel])

    if video:
        cmd.extend(["-v", video])

    # 使用默认参数：字体大小60，白色字体，黑色描边
    cmd.extend(
        [
            "--font_size",
            "60",
            "--font_color",
            "white",
            "--stroke_width",
            "2",
            "--stroke_color",
            "black",
            "--font_weight",
            "500",
        ]
    )

    print(f"执行命令: {' '.join(cmd)}")
    print("=" * 50)

    try:
        result = subprocess.run(cmd, check=True)
        print("=" * 50)
        print("✅ 封面生成完成！")
        return True
    except subprocess.CalledProcessError as e:
        print("=" * 50)
        print(f"❌ 封面生成失败，退出码: {e.returncode}")
        return False
    except KeyboardInterrupt:
        print("\n🛑 用户中断操作")
        return False


def main():
    parser = argparse.ArgumentParser(description="批量生成英语和韩语视频封面")
    parser.add_argument("--channel", "-c", help="指定要处理的频道名称")
    parser.add_argument("--video", "-v", help="指定要处理的视频名称（不含扩展名）")

    args = parser.parse_args()

    print("🎬 英语和韩语视频封面生成器")
    print("=" * 50)

    if args.channel:
        print(f"📺 处理频道: {args.channel}")
    else:
        print("📺 处理所有频道")

    if args.video:
        print(f"🎥 处理视频: {args.video}")
    else:
        print("🎥 处理所有视频")

    print("🎨 生成语言: 英语(en) + 韩语(ko)")
    print("🎯 背景来源: 对应语种视频帧")

    # 确认操作
    confirm = input("\n继续执行吗？(y/N): ").lower().strip()
    if confirm not in ["y", "yes"]:
        print("❌ 操作已取消")
        return

    success = run_thumbnail_generation(args.channel, args.video)

    if success:
        print("\n🎉 所有操作完成！")
        print("📁 输出目录: /Volumes/dhl/buda_videos_youtube/thumbnail/")
    else:
        print("\n💥 操作未完全成功，请检查错误信息")


if __name__ == "__main__":
    main()
