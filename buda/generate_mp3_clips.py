#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成MP3脚本
===========

此脚本用于将多语言的文本文件转换为MP3音频文件，使用Edge TTS服务。

输入目录: /Volumes/dhl/buda_videos_youtube/multi_lang_txt (macOS)
         /media/dhl/buda_videos_youtube/multi_lang_txt (Linux)

输出目录: /Volumes/dhl/buda_videos_youtube/multi_lang_mp3 (macOS)
         /media/dhl/buda_videos_youtube/multi_lang_mp3 (Linux)

目录结构:
- 输入: <基础媒体路径>/multi_lang_txt/<频道>/<语言>/<视频名>.txt
- 输出: <基础媒体路径>/multi_lang_mp3/<频道>/<视频名>/<语言>/<行号>.mp3

支持的语言:
- en: 英语 (en-US-AndrewMultilingualNeural)
- ja: 日语 (ja-JP-KeitaNeural)
- vi: 越南语 (vi-VN-NamMinhNeural)
- ko: 韩语 (ko-KR-InJoonNeural)

使用方法:
python generate_mp3.py [选项]

选项:
  -l, --languages     指定要处理的语言代码列表
  -f, --force         强制重新生成已有的MP3文件
  -b, --batch_size    设置并发处理的批量大小
  -s, --single_file   指定单独处理一个TXT文件
  -o, --output_dir    单独处理模式下的输出目录
"""

import os
import re
import time
import argparse
import sys
import platform
import concurrent.futures
from tqdm import tqdm
import threading
import signal
import subprocess


# 注册信号处理器，用于捕获Ctrl+C
def signal_handler(sig, frame):
    print("\n检测到中断信号，将在当前任务完成后退出...")


# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# 获取媒体基础路径
BASE_MEDIA_PATH = get_base_media_path()
# 输入TXT目录
INPUT_TXT_PATH = os.path.join(BASE_MEDIA_PATH, "multi_lang_txt")
# 输出MP3目录
OUTPUT_MP3_PATH = os.path.join(BASE_MEDIA_PATH, "multi_lang_mp3")

# 定义语言和对应的语音名称
VOICE_NAMES = {
    "en": "en-US-AndrewMultilingualNeural",
    "ja": "ja-JP-KeitaNeural",
    "vi": "vi-VN-NamMinhNeural",
    "ko": "ko-KR-InJoonNeural",
}


def text_to_mp3(text, output_file, language_code, max_retries=5):
    """使用Edge TTS将文本转换为MP3文件"""
    if not text.strip():
        print("警告: 空文本，跳过")
        return False

    voice = VOICE_NAMES.get(language_code)
    if not voice:
        print(f"错误: 不支持的语言代码 {language_code}")
        return False

    for attempt in range(max_retries):
        try:
            # 使用subprocess调用edge-tts命令
            cmd = [
                "edge-tts",
                "--voice",
                voice,
                "--text",
                text,
                "--write-media",
                output_file,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"语音合成成功: {output_file}")
                return True
            else:
                print(f"语音合成失败: {result.stderr}")

                if attempt < max_retries - 1:
                    print(f"等待2秒后重试 (尝试 {attempt+1}/{max_retries})...")
                    time.sleep(2)
                else:
                    print(f"达到最大重试次数 ({max_retries})，跳过")
                    return False
        except Exception as e:
            print(f"语音合成时出错: {e}")
            if attempt < max_retries - 1:
                print(f"等待2秒后重试 (尝试 {attempt+1}/{max_retries})...")
                time.sleep(2)
            else:
                print(f"达到最大重试次数 ({max_retries})，跳过")
                return False

    return False


def check_mp3_progress(output_dir):
    """检查输出目录中已生成的MP3文件数量"""
    if not os.path.exists(output_dir):
        return 0, []

    mp3_files = [f for f in os.listdir(output_dir) if f.endswith(".mp3")]
    # 获取已生成的MP3文件的行号索引
    existing_indices = set(int(os.path.splitext(f)[0]) for f in mp3_files)
    return len(mp3_files), existing_indices


def find_missing_indices(total_lines, existing_indices):
    """高效查找缺失的索引"""
    all_indices = set(range(1, total_lines + 1))
    return sorted(all_indices - existing_indices)


def process_txt_file(input_file, output_dir, language_code, force=False, batch_size=5):
    """处理一个TXT文件，为每行文本生成对应的MP3文件"""
    if not os.path.exists(input_file):
        print(f"错误: 输入文件 '{input_file}' 不存在")
        return False

    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")

    # 读取所有行，确定总行数
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    total_lines = len(lines)

    # 检查是否有已生成的MP3文件及缺失的索引
    already_generated, existing_indices = check_mp3_progress(output_dir)

    # 查找缺失的索引
    missing_indices = find_missing_indices(total_lines, existing_indices)

    print(f"共有 {total_lines} 行文本，已生成 {already_generated} 个MP3文件")

    if missing_indices:
        print(
            f"发现 {len(missing_indices)} 个缺失的索引: {missing_indices[:10]}{'...' if len(missing_indices) > 10 else ''}"
        )

    # 如果MP3数量与TXT行数不一致或强制重新生成，则处理
    need_process = (already_generated != total_lines) or force

    if not need_process:
        print("所有MP3文件都已生成完成，无需重新生成")
        return True

    # 定义处理单行的函数
    def process_line(line_info):
        idx, line = line_info
        line_num = idx + 1
        output_file = os.path.join(output_dir, f"{line_num}.mp3")

        # 如果强制重新生成、文件不存在或索引在缺失列表中，则处理该行
        if force or not os.path.exists(output_file) or line_num in missing_indices:
            text = line.strip()
            print(f"正在处理第 {line_num}/{total_lines} 行: {text}")
            return idx, text_to_mp3(text, output_file, language_code)
        else:
            # print(f"MP3文件已存在，跳过: {output_file}")
            return idx, True

    try:
        # 确定需要处理的行索引
        if force:
            # 如果强制重新生成，处理所有行
            lines_to_process = [(i, lines[i]) for i in range(total_lines)]
        else:
            # 否则，只处理缺失的或未生成的行
            lines_to_process = [
                (i, lines[i])
                for i in range(total_lines)
                if (i + 1) in missing_indices
                or not os.path.exists(os.path.join(output_dir, f"{i+1}.mp3"))
            ]

        total_to_process = len(lines_to_process)

        if total_to_process == 0:
            print("没有需要处理的行，所有文件都已生成")
            return True

        print(f"需要处理 {total_to_process} 行文本")

        with tqdm(total=total_to_process, desc="生成MP3进度") as pbar:
            # 批量处理需处理的行
            for batch_start in range(0, total_to_process, batch_size):
                batch_end = min(batch_start + batch_size, total_to_process)
                batch_lines = lines_to_process[batch_start:batch_end]

                # 并发处理本批次
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=batch_size
                ) as executor:
                    results = list(executor.map(process_line, batch_lines))

                # 更新进度条
                for _, success in results:
                    if success:
                        pbar.update(1)

        # 再次检查是否有缺失的索引
        _, existing_indices = check_mp3_progress(output_dir)
        missing_indices = find_missing_indices(total_lines, existing_indices)

        if missing_indices:
            print(
                f"处理完成后仍有 {len(missing_indices)} 个缺失的索引: {missing_indices[:10]}{'...' if len(missing_indices) > 10 else ''}"
            )
            return False
        else:
            print(f"处理完成! 所有MP3文件已保存到 {output_dir}")
            return True
    except KeyboardInterrupt:
        print("\n处理被用户中断")
        print("已处理部分内容，下次可继续从断点处处理")
        return False
    except Exception as e:
        print(f"处理过程中出错: {e}")
        print("已处理部分内容，下次可继续从断点处处理")
        return False


def process_all_channels(languages=None, force=False, batch_size=5):
    """处理multi_lang_txt目录下的所有频道和TXT文件"""
    if languages is None:
        languages = list(VOICE_NAMES.keys())

    # 检查输入路径是否存在
    if not os.path.exists(INPUT_TXT_PATH):
        print(f"错误: 输入路径 '{INPUT_TXT_PATH}' 不存在")
        return

    # 获取所有频道目录
    channels = [
        d
        for d in os.listdir(INPUT_TXT_PATH)
        if os.path.isdir(os.path.join(INPUT_TXT_PATH, d))
    ]

    if not channels:
        print(f"在 '{INPUT_TXT_PATH}' 中未找到任何频道目录")
        return

    print(f"找到 {len(channels)} 个频道目录")

    # 记录所有需要处理的视频信息
    video_tasks = []
    partially_complete_tasks = []

    # 首先扫描所有频道和视频，查找哪些是部分完成的
    for channel in channels:
        channel_path = os.path.join(INPUT_TXT_PATH, channel)

        # 收集该频道下所有视频
        all_videos = set()
        for language in languages:
            lang_path = os.path.join(channel_path, language)
            if not os.path.exists(lang_path):
                continue

            # 获取当前语言目录中的所有TXT文件（视频）
            txt_files = [f for f in os.listdir(lang_path) if f.endswith(".txt")]
            for txt_file in txt_files:
                video_name = os.path.splitext(txt_file)[0]
                all_videos.add(video_name)

        # 对每个视频，检查是否有部分完成的语言
        for video_name in all_videos:
            video_info = {
                "channel": channel,
                "video_name": video_name,
                "langs_status": {},
            }

            for language in languages:
                lang_path = os.path.join(channel_path, language)
                if not os.path.exists(lang_path):
                    continue

                input_file_path = os.path.join(lang_path, f"{video_name}.txt")
                if not os.path.exists(input_file_path):
                    continue

                # 检查输出目录中是否已有MP3文件
                output_dir = os.path.join(
                    OUTPUT_MP3_PATH, channel, video_name, language
                )

                # 读取输入文件的总行数
                with open(input_file_path, "r", encoding="utf-8") as f:
                    total_lines = len(f.readlines())

                if os.path.exists(output_dir):
                    # 检查已生成的MP3文件数量
                    mp3_count, existing_indices = check_mp3_progress(output_dir)

                    # 判断完成状态
                    if mp3_count < total_lines:
                        video_info["langs_status"][language] = {
                            "status": "partial",
                            "path": input_file_path,
                            "output_dir": output_dir,
                        }
                    elif mp3_count > total_lines:
                        video_info["langs_status"][language] = {
                            "status": "excess",
                            "path": input_file_path,
                            "output_dir": output_dir,
                        }
                    else:  # mp3_count == total_lines
                        video_info["langs_status"][language] = {
                            "status": "complete",
                            "path": input_file_path,
                            "output_dir": output_dir,
                        }
                else:
                    video_info["langs_status"][language] = {
                        "status": "not_started",
                        "path": input_file_path,
                        "output_dir": output_dir,
                    }

            # 优先处理的情况：部分完成的视频、MP3数量与TXT行数不一致的视频
            if any(
                info["status"] in ["partial", "excess"]
                for info in video_info["langs_status"].values()
            ):
                partially_complete_tasks.append(video_info)
            else:
                video_tasks.append(video_info)

    # 优先处理部分完成或有问题的视频
    print(f"\n发现 {len(partially_complete_tasks)} 个需要优先处理的视频")
    all_tasks = partially_complete_tasks + video_tasks

    # 开始处理所有视频任务
    for task_idx, task in enumerate(all_tasks):
        channel = task["channel"]
        video_name = task["video_name"]

        print(
            f"\n========= 处理视频: {channel}/{video_name} ({task_idx+1}/{len(all_tasks)}) ========="
        )

        # 按照语言顺序处理每个语言版本
        for language in languages:
            if language not in task["langs_status"]:
                print(f"语言 {language} 不存在对应的文本文件，跳过")
                continue

            lang_info = task["langs_status"][language]
            input_file_path = lang_info["path"]
            output_dir = lang_info["output_dir"]
            status = lang_info["status"]

            print(f"\n处理语言: {language} (状态: {status})")
            print(f"从 {input_file_path}")
            print(f"到 {output_dir}")

            # 处理TXT文件
            success = process_txt_file(
                input_file_path, output_dir, language, force, batch_size
            )

            if success:
                print(f"成功完成 {video_name} 的 {language} 语言MP3生成!")
            else:
                print(f"{video_name} 的 {language} 语言MP3生成未完全完成")


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="将多语言TXT文件转换为MP3音频文件")

    # 添加命令行参数
    parser.add_argument(
        "-l",
        "--languages",
        nargs="+",
        choices=VOICE_NAMES.keys(),
        default=list(VOICE_NAMES.keys()),
        help=f"目标语言列表 (默认: {' '.join(VOICE_NAMES.keys())})",
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="强制重新生成，忽略已有MP3文件"
    )
    parser.add_argument(
        "-b", "--batch_size", type=int, default=10, help="并发处理的批量大小，默认为10"
    )
    parser.add_argument(
        "-s", "--single_file", type=str, help="指定单独处理一个TXT文件路径"
    )
    parser.add_argument("-o", "--output_dir", type=str, help="单独处理模式下的输出目录")

    # 解析命令行参数
    args = parser.parse_args()

    # 检查edge-tts是否已安装
    try:
        subprocess.run(["edge-tts", "--version"], capture_output=True, text=True)
    except FileNotFoundError:
        print("错误: 未找到edge-tts命令。请先安装edge-tts: pip install edge-tts")
        return

    try:
        # 处理单个文件模式
        if args.single_file:
            if not os.path.exists(args.single_file):
                print(f"错误: 指定的文件 '{args.single_file}' 不存在")
                return

            if not args.output_dir:
                print("错误: 单独处理模式下必须指定输出目录 (-o/--output_dir)")
                return

            # 从文件路径中提取语言代码
            # 假设路径格式为 .../channel/language/video.txt
            path_parts = args.single_file.split(os.sep)
            language = None

            for lang in VOICE_NAMES.keys():
                if lang in path_parts:
                    language = lang
                    break

            if not language:
                print("错误: 无法从文件路径中提取语言代码，请确保文件路径包含语言代码")
                return

            # 处理单个文件
            success = process_txt_file(
                args.single_file, args.output_dir, language, args.force, args.batch_size
            )

            if success:
                print(f"成功完成 {args.single_file} 的MP3生成!")
            else:
                print(f"{args.single_file} 的MP3生成未完全完成")
        else:
            # 处理所有频道和TXT文件
            process_all_channels(args.languages, args.force, args.batch_size)
            print("所有任务已处理完成")

    except KeyboardInterrupt:
        print("\n处理被用户中断")
    except Exception as e:
        print(f"\n程序运行时发生错误: {e}")
    finally:
        print("程序已退出。")


if __name__ == "__main__":
    main()
