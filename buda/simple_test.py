#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from embed_subtitles import embed_subtitle


def main():
    """简单测试脚本，直接调用embed_subtitle函数将字幕嵌入到视频中"""

    # 定义输入和输出文件路径
    input_video = "./clip_1.mp4"
    input_srt = "./test_srt_out/o_en.srt"
    output_dir = "./test_output"
    output_video = os.path.join(output_dir, "clip_1_with_subtitles.mp4")

    # 确保输入文件存在
    if not os.path.exists(input_video):
        print(f"错误: 输入视频文件不存在: {input_video}")
        return 1

    if not os.path.exists(input_srt):
        print(f"错误: 输入字幕文件不存在: {input_srt}")
        return 1

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 设置测试模式环境变量
    os.environ["TEST_MODE"] = "1"

    # 直接调用embed_subtitle函数
    print(f"开始嵌入字幕 - 视频: {input_video}, 字幕: {input_srt}")
    success = embed_subtitle(input_video, input_srt, output_video, "en")

    if success:
        print(f"成功! 输出文件: {output_video}")
        filesize = os.path.getsize(output_video) / (1024 * 1024)  # MB
        print(f"文件大小: {filesize:.2f} MB")
        return 0
    else:
        print("嵌入字幕失败!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
