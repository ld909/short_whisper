#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
from srt_format import (
    parse_srt_with_re,
    format_srt,
    break_srt_txt_into_sentences,
    read_srt_file,
)


def process_srt_file(input_file, output_file, break_sentences=False):
    """
    处理SRT文件：读取、格式化、输出

    Args:
        input_file: 输入SRT文件路径
        output_file: 输出SRT文件路径
        break_sentences: 是否执行句子拆分
    """
    print(f"正在处理文件: {input_file}")

    # 读取SRT文件内容
    srt_content = read_srt_file(input_file)

    # 解析SRT内容
    timestamps, subtitles = parse_srt_with_re(srt_content)

    # 格式化字幕
    ts_list, txt_list = format_srt(timestamps, subtitles)

    # 如果需要，拆分句子
    if break_sentences:
        ts_list, txt_list = break_srt_txt_into_sentences(ts_list, txt_list)

    # 检查时间戳和字幕数量是否一致
    assert len(ts_list) == len(txt_list), "时间戳和字幕数量不一致"

    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 处理后的字幕写入文件
    print(f"正在写入格式化后的字幕到: {output_file}")
    with open(output_file, "w", encoding="utf-8") as f:
        for i in range(len(txt_list)):
            f.write(str(i + 1) + "\n")
            f.write(ts_list[i][0] + " --> " + ts_list[i][1] + "\n")
            f.write(txt_list[i] + "\n\n")

    print(f"处理完成。共处理 {len(txt_list)} 个字幕条目。")


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="测试format_srt函数")
    parser.add_argument("input_file", help="输入SRT文件路径")
    parser.add_argument("output_file", help="输出SRT文件路径")
    args = parser.parse_args()

    # 检查输入文件是否存在
    if not os.path.exists(args.input_file):
        print(f"错误：输入文件 {args.input_file} 不存在")
        return

    # 读取SRT文件
    print(f"读取SRT文件: {args.input_file}")
    srt_content = read_srt_file(args.input_file)

    # 解析SRT内容
    print("解析SRT内容...")
    timestamps, subtitles = parse_srt_with_re(srt_content)

    # 格式化SRT内容
    print("格式化SRT内容...")
    formatted_ts, formatted_txt = format_srt(timestamps, subtitles)

    # 检查格式化后的时间戳和文本是否一致
    if len(formatted_ts) != len(formatted_txt):
        print("警告：格式化后的时间戳和文本数量不一致")

    # 创建输出目录（如果不存在）
    output_dir = os.path.dirname(args.output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 将格式化后的内容写入输出文件
    print(f"保存格式化后的SRT文件: {args.output_file}")
    with open(args.output_file, "w", encoding="utf-8") as f:
        for i in range(len(formatted_txt)):
            f.write(f"{i + 1}\n")
            f.write(f"{formatted_ts[i][0]} --> {formatted_ts[i][1]}\n")
            f.write(f"{formatted_txt[i]}\n\n")

    print("完成！")


if __name__ == "__main__":
    main()
