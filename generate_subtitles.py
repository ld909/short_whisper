#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多语言字幕生成工具

功能说明:
此脚本用于从文本文件自动生成SRT格式的字幕文件，可以使用对应的MP3音频文件来提高时间戳的准确性。
支持多语言处理，包括英语(en)、日语(ja)、越南语(vi)和韩语(ko)。

目录结构:
- 输入文本目录: /Volumes/dhl/buda_videos_youtube/multi_lang_txt_split/ (macOS) 或
              /media/dhl/buda_videos_youtube/multi_lang_txt_split/ (Linux)
 - 输入MP3目录: /Volumes/dhl/buda_videos_youtube/multi_lang_mp3/
- 合并MP3目录: /Volumes/dhl/buda_videos_youtube/merge_multi_lange_mp3/
- 输出SRT目录: /Volumes/dhl/buda_videos_youtube/multi_lang_srt/

处理流程:
1. 读取文本文件内容
2. 尝试找到对应的MP3文件获取准确时长
3. 根据文本内容和语言特性计算每行字幕的显示时间
4. 生成标准SRT格式字幕文件
5. 支持并发处理多个视频和多种语言

使用方法:
python generate_subtitles.py [-l LANGUAGES] [-f] [-w WORKERS] [-s CHANNEL/VIDEO]

参数说明:
- -l, --languages: 指定需要处理的语言，默认处理所有支持的语言
- -f, --force: 强制重新生成已存在的字幕文件
- -w, --workers: 设置并发处理线程数，默认为3
- -s, --single: 指定只处理单个视频，格式为"频道名/视频名"
"""

import os
import argparse
import platform
import subprocess
import concurrent.futures
import sys
from tqdm import tqdm
import re
import datetime
from datetime import time, timedelta


def get_base_path():
    """根据操作系统类型返回对应的基础路径"""
    if platform.system() == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# 定义全局路径变量
BASE_PATH = get_base_path()
# 输入MP3目录
INPUT_MP3_PATH = os.path.join(BASE_PATH, "multi_lang_mp3")
# 合并后的MP3目录
MERGED_MP3_PATH = os.path.join(BASE_PATH, "merge_multi_lange_mp3")
# 输入TXT目录
INPUT_TXT_PATH = os.path.join(BASE_PATH, "multi_lang_txt_split")
# 输出SRT目录
OUTPUT_SRT_PATH = os.path.join(BASE_PATH, "multi_lang_srt")
# 支持的语言
SUPPORTED_LANGUAGES = ["en", "ja", "vi", "ko"]


def time_str_to_obj(time_str):
    """将时间戳字符串转换为 timedelta 对象。"""
    # 将时间戳拆分成小时、分钟、秒和毫秒
    hours, minutes, seconds = time_str.split(":")
    seconds, milliseconds = seconds.split(",")

    # 计算总秒数
    total_seconds = (
        int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000
    )

    # 创建 timedelta 对象
    time_obj = timedelta(seconds=total_seconds)

    return time_obj


def timedelta_to_srt(timedelta_obj):
    """Convert timedelta object to SRT format time string."""
    # 获取总的秒数
    total_seconds = int(timedelta_obj.total_seconds())
    # 计算小时、分钟和秒
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    # 计算毫秒，确保精度
    milliseconds = int((timedelta_obj.total_seconds() - total_seconds) * 1000)

    # 格式化时间字符串，确保小时、分钟和秒是2位数，毫秒是3位数
    srt_time_string = f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

    return srt_time_string


def get_mp3_duration(mp3_file):
    """获取MP3文件的持续时间（以秒为单位）"""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            mp3_file,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return duration
    except subprocess.CalledProcessError as e:
        print(f"获取MP3持续时间时出错: {e}")
        return None
    except Exception as e:
        print(f"获取MP3持续时间时出现意外错误: {e}")
        return None


def generate_srt_from_txt(txt_file_path, srt_file_path, language, mp3_file_path=None):
    """从文本文件生成SRT字幕文件，可选择使用MP3文件来获取准确时长"""
    try:
        # 读取文本文件
        with open(txt_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 过滤空行并去除首尾空白
        lines = [line.strip() for line in lines if line.strip()]

        if not lines:
            print(f"警告: 文本文件为空: {txt_file_path}")
            return False

        # 获取MP3文件的总持续时间（如果提供）
        total_duration = None
        if mp3_file_path and os.path.exists(mp3_file_path):
            total_duration = get_mp3_duration(mp3_file_path)
            if total_duration:
                print(f"MP3文件总时长: {total_duration:.2f}秒")
            else:
                print(f"无法获取MP3文件时长，将使用估算时长")

        # 计算每段文字的估计时长
        durations = []
        total_chars = 0

        for line in lines:
            # 去除文本中的标点符号和空格，计算字符数
            clean_text = re.sub(r"[^\w\s]", "", line)
            clean_text = clean_text.replace(" ", "")
            chars = len(clean_text)
            total_chars += chars
            durations.append(chars)

        # 如果有MP3文件时长，按比例分配时间
        if total_duration:
            # 将字符数转换为时间（按比例）
            for i in range(len(durations)):
                if total_chars > 0:  # 避免除以零
                    durations[i] = (durations[i] / total_chars) * total_duration
                else:
                    durations[i] = 1.0  # 默认1秒
                # 确保最小时长
                durations[i] = max(0.8, durations[i])
        else:
            # 使用基于语言的估计时长
            speeds = {
                "en": 12,  # 英语阅读速度（字符/秒）
                "ja": 6,  # 日语阅读速度
                "vi": 10,  # 越南语阅读速度
                "ko": 7,  # 韩语阅读速度
            }
            speed = speeds.get(language, 8)
            for i in range(len(durations)):
                durations[i] = durations[i] / speed
                # 确保最小时长
                durations[i] = max(0.8, durations[i])

        # 生成SRT内容
        current_time = timedelta(seconds=0)
        srt_content = []

        for i, (line, duration) in enumerate(zip(lines, durations)):
            # 计算开始和结束时间
            start_time = current_time
            end_time = start_time + timedelta(seconds=duration)

            # 转换为SRT格式的时间戳
            start_time_str = timedelta_to_srt(start_time)
            end_time_str = timedelta_to_srt(end_time)

            # 添加到SRT内容中
            srt_content.append(f"{i+1}\n{start_time_str} --> {end_time_str}\n{line}\n")

            # 更新时间戳，添加小间隔
            current_time = end_time + timedelta(milliseconds=100)

        # 创建输出目录
        os.makedirs(os.path.dirname(srt_file_path), exist_ok=True)

        # 写入SRT文件
        with open(srt_file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_content))

        print(f"成功生成SRT文件: {srt_file_path}")
        return True
    except Exception as e:
        print(f"生成SRT文件时出错: {e}")
        return False


def process_language(channel, video_name, language, force=False):
    """处理单个语言的字幕生成"""
    # 构建输入文本文件路径
    txt_file_path = os.path.join(INPUT_TXT_PATH, channel, language, f"{video_name}.txt")

    # 如果输入文件不存在，跳过处理
    if not os.path.exists(txt_file_path):
        print(f"输入文件不存在，跳过: {txt_file_path}")
        return False

    # 构建输出SRT文件路径
    output_dir = os.path.join(OUTPUT_SRT_PATH, channel, language)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_file = os.path.join(output_dir, f"{video_name}.srt")

    # 如果输出文件已存在且不强制重新生成，则跳过
    if os.path.exists(output_file) and not force:
        print(f"输出文件已存在，跳过: {output_file}")
        return True

    print(f"处理视频: {video_name}, 语言: {language}")
    print(f"输入文件: {txt_file_path}")
    print(f"输出文件: {output_file}")

    # 尝试寻找对应的MP3文件
    mp3_file_path = os.path.join(
        MERGED_MP3_PATH, channel, language, f"{video_name}.mp3"
    )
    if not os.path.exists(mp3_file_path):
        print(f"找不到对应的MP3文件: {mp3_file_path}，将使用估算时长")
        mp3_file_path = None

    # 生成SRT字幕文件
    return generate_srt_from_txt(txt_file_path, output_file, language, mp3_file_path)


def process_video(channel, video_name, languages, force=False):
    """处理一个视频的所有语言版本"""
    success_count = 0

    for language in languages:
        if process_language(channel, video_name, language, force):
            success_count += 1

    return success_count


def process_all_channels(languages=None, force=False, max_workers=3):
    """处理所有频道的所有视频"""
    if languages is None:
        languages = SUPPORTED_LANGUAGES

    # 验证语言是否支持
    for lang in languages[:]:  # 创建一个副本以便在迭代时修改
        if lang not in SUPPORTED_LANGUAGES:
            print(f"警告: 不支持的语言 {lang}，将被忽略")
            languages.remove(lang)

    if not languages:
        print("错误: 没有指定任何有效的语言")
        return

    # 检查输入路径是否存在
    if not os.path.exists(INPUT_TXT_PATH):
        print(f"错误: 输入路径不存在: {INPUT_TXT_PATH}")
        return

    # 获取所有频道目录
    channels = [
        d
        for d in os.listdir(INPUT_TXT_PATH)
        if os.path.isdir(os.path.join(INPUT_TXT_PATH, d))
    ]

    if not channels:
        print(f"在 {INPUT_TXT_PATH} 中未找到任何频道目录")
        return

    print(f"找到 {len(channels)} 个频道目录")

    # 处理每个频道
    for channel in channels:
        channel_path = os.path.join(INPUT_TXT_PATH, channel)
        print(f"\n处理频道: {channel}")

        # 获取当前频道下的所有语言目录
        lang_dirs = [
            d
            for d in os.listdir(channel_path)
            if os.path.isdir(os.path.join(channel_path, d)) and d in languages
        ]

        if not lang_dirs:
            print(f"在频道 {channel} 中未找到任何支持的语言目录")
            continue

        # 获取所有视频名称（不考虑语言）
        all_videos = set()
        for lang in lang_dirs:
            lang_path = os.path.join(channel_path, lang)
            videos = [
                f[:-4]  # 去除.txt后缀
                for f in os.listdir(lang_path)
                if f.endswith(".txt") and os.path.isfile(os.path.join(lang_path, f))
            ]
            all_videos.update(videos)

        print(f"找到 {len(all_videos)} 个视频")

        # 为每个视频和语言创建任务
        tasks = []
        for video_name in all_videos:
            for lang in lang_dirs:
                # 检查该语言下是否有对应的TXT文件
                txt_path = os.path.join(channel_path, lang, f"{video_name}.txt")
                if not os.path.exists(txt_path):
                    print(f"跳过不存在的输入文件: {txt_path}")
                    continue

                # 构建输出SRT文件路径
                output_dir = os.path.join(OUTPUT_SRT_PATH, channel, lang)
                output_file = os.path.join(output_dir, f"{video_name}.srt")

                # 如果输出文件已存在且不强制重新生成，则跳过
                if os.path.exists(output_file) and not force:
                    print(f"输出文件已存在，跳过: {output_file}")
                    continue

                # 添加任务
                tasks.append((channel, video_name, lang))

        print(f"找到 {len(tasks)} 个待处理任务")

        # 并发处理任务
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    process_language, channel, video_name, language, force
                ): (channel, video_name, language)
                for channel, video_name, language in tasks
            }

            for future in tqdm(
                concurrent.futures.as_completed(futures),
                total=len(futures),
                desc=f"处理 {channel} 频道",
            ):
                channel, video_name, language = futures[future]
                try:
                    success = future.result()
                    if success:
                        print(f"成功生成 {channel}/{video_name}/{language}")
                    else:
                        print(f"生成失败 {channel}/{video_name}/{language}")
                except Exception as e:
                    print(f"处理 {channel}/{video_name}/{language} 时出错: {e}")


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="生成多语言SRT字幕文件")

    # 添加命令行参数
    parser.add_argument(
        "-l",
        "--languages",
        nargs="+",
        choices=SUPPORTED_LANGUAGES,
        default=SUPPORTED_LANGUAGES,
        help=f"目标语言列表 (默认: {' '.join(SUPPORTED_LANGUAGES)})",
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="强制重新生成，即使输出文件已存在"
    )
    parser.add_argument(
        "-w", "--workers", type=int, default=3, help="并发处理的工作线程数，默认为3"
    )
    parser.add_argument(
        "-s", "--single", type=str, help="只处理指定的单个视频，格式: 频道名/视频名"
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 处理单个视频模式
    if args.single:
        if "/" not in args.single:
            print("错误: 单个视频参数格式应为 '频道名/视频名'")
            return

        channel, video_name = args.single.split("/", 1)

        print(f"处理单个视频: {channel}/{video_name}")
        success_count = process_video(channel, video_name, args.languages, args.force)

        print(f"处理完成，成功生成 {success_count}/{len(args.languages)} 个语言版本")
    else:
        # 处理所有频道和视频
        process_all_channels(args.languages, args.force, args.workers)


if __name__ == "__main__":
    main()
