#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成MP3脚本
===========

此脚本用于将多语言的文本文件转换为MP3音频文件，使用Azure语音合成服务。

输入目录: /Volumes/dhl/buda_videos_youtube/multi_lang_txt (macOS)
         /media/dhl/buda_videos_youtube/multi_lang_txt (Linux)

输出目录: /Volumes/dhl/buda_videos_youtube/multi_lang_mp3 (macOS)
         /media/dhl/buda_videos_youtube/multi_lang_mp3 (Linux)

目录结构:
- 输入: <基础媒体路径>/multi_lang_txt/<频道>/<语言>/<视频名>.txt
- 输出: <基础媒体路径>/multi_lang_mp3/<频道>/<视频名>/<语言>/<行号>.mp3

支持的语言:
- en: 英语 (en-US-AndrewMultilingualNeural)
- ja: 日语 (ja-JP-MasaruMultilingualNeural)
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
import azure.cognitiveservices.speech as speechsdk


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

# Azure语音合成配置
# SPEECH_KEY = "cba10589e21e48dfb986f493e276b833"
# SERVICE_REGION = "eastasia"
SPEECH_KEY = "7ce9bde9dc744a4c9cb603bb74761c4d"
SERVICE_REGION = "eastus"

# 定义语言和对应的语音名称
VOICE_NAMES = {
    "en": "en-US-AndrewMultilingualNeural",
    "ja": "ja-JP-MasaruMultilingualNeural",
    "vi": "vi-VN-NamMinhNeural",
    "ko": "ko-KR-InJoonNeural",
}


def setup_speech_synthesizer(language_code):
    """设置语音合成器"""
    if language_code not in VOICE_NAMES:
        print(f"错误: 不支持的语言代码 {language_code}")
        return None

    try:
        speech_config = speechsdk.SpeechConfig(
            subscription=SPEECH_KEY, region=SERVICE_REGION
        )
        speech_config.speech_synthesis_voice_name = VOICE_NAMES[language_code]
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
        return speech_synthesizer
    except Exception as e:
        print(f"初始化语音合成器时出错: {e}")
        return None


def text_to_mp3(text, output_file, language_code, max_retries=3):
    """将文本转换为MP3文件"""
    if not text.strip():
        print("警告: 空文本，跳过")
        return False

    # 设置音频配置
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)

    # 获取语音合成器
    speech_config = speechsdk.SpeechConfig(
        subscription=SPEECH_KEY, region=SERVICE_REGION
    )
    speech_config.speech_synthesis_voice_name = VOICE_NAMES[language_code]
    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=audio_config
    )

    for attempt in range(max_retries):
        try:
            # 合成语音
            result = speech_synthesizer.speak_text_async(text).get()

            # 检查结果
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                print(f"语音合成成功: {output_file}")
                return True
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                print(f"语音合成被取消: {cancellation_details.reason}")
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    print(f"错误详情: {cancellation_details.error_details}")

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
        return 0

    mp3_files = [f for f in os.listdir(output_dir) if f.endswith(".mp3")]
    return len(mp3_files)


def process_txt_file(input_file, output_dir, language_code, force=False, batch_size=5):
    """处理一个TXT文件，为每行文本生成对应的MP3文件"""
    if not os.path.exists(input_file):
        print(f"错误: 输入文件 '{input_file}' 不存在")
        return False

    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")

    # 检查是否有已生成的MP3文件
    already_generated = check_mp3_progress(output_dir)

    # 读取所有行
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    total_lines = len(lines)
    print(f"共有 {total_lines} 行文本，已生成 {already_generated} 个MP3文件")

    # 如果所有行都已处理完成，直接返回
    if already_generated >= total_lines and not force:
        print("所有MP3文件都已生成完成，无需重新生成")
        return True

    # 定义处理单行的函数
    def process_line(line_info):
        idx, line = line_info
        line_num = idx + 1
        output_file = os.path.join(output_dir, f"{line_num}.mp3")

        # 如果强制重新生成或文件不存在，则处理该行
        if force or not os.path.exists(output_file):
            text = line.strip()
            print(f"正在处理第 {line_num}/{total_lines} 行: {text}")
            return idx, text_to_mp3(text, output_file, language_code)
        else:
            print(f"MP3文件已存在，跳过: {output_file}")
            return idx, True

    try:
        with tqdm(total=total_lines, desc="生成MP3进度") as pbar:
            # 更新已完成的进度
            pbar.update(already_generated)

            # 处理未完成的行
            for batch_start in range(0, total_lines, batch_size):
                batch_end = min(batch_start + batch_size, total_lines)
                batch_lines = [
                    (i, lines[i])
                    for i in range(batch_start, batch_end)
                    if force
                    or not os.path.exists(os.path.join(output_dir, f"{i+1}.mp3"))
                ]

                if not batch_lines:
                    continue

                # 并发处理本批次
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=batch_size
                ) as executor:
                    results = list(executor.map(process_line, batch_lines))

                # 更新进度条
                for _, success in results:
                    if success:
                        pbar.update(1)

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

    for channel in channels:
        channel_path = os.path.join(INPUT_TXT_PATH, channel)

        # 检查频道下的所有语言目录
        for language in languages:
            lang_path = os.path.join(channel_path, language)

            if not os.path.exists(lang_path):
                print(f"语言目录不存在，跳过: {lang_path}")
                continue

            # 获取当前语言目录中的所有TXT文件
            txt_files = [f for f in os.listdir(lang_path) if f.endswith(".txt")]

            if not txt_files:
                print(f"在 '{lang_path}' 中未找到任何TXT文件，跳过")
                continue

            print(
                f"\n处理频道: {channel}，语言: {language}，找到 {len(txt_files)} 个TXT文件"
            )

            for txt_file in txt_files:
                input_file_path = os.path.join(lang_path, txt_file)

                # 提取视频名称（去除.txt后缀）
                video_name = os.path.splitext(txt_file)[0]

                # 构建输出目录路径
                output_dir = os.path.join(
                    OUTPUT_MP3_PATH, channel, video_name, language
                )

                print(f"\n处理文件: {txt_file}")
                print(f"从 {input_file_path}")
                print(f"到 {output_dir}")

                # 处理TXT文件
                success = process_txt_file(
                    input_file_path, output_dir, language, force, batch_size
                )

                if success:
                    print(f"成功完成 {txt_file} 的MP3生成!")
                else:
                    print(f"{txt_file} 的MP3生成未完全完成，将继续下一个文件")


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
        "-b", "--batch_size", type=int, default=5, help="并发处理的批量大小，默认为5"
    )
    parser.add_argument(
        "-s", "--single_file", type=str, help="指定单独处理一个TXT文件路径"
    )
    parser.add_argument("-o", "--output_dir", type=str, help="单独处理模式下的输出目录")

    # 解析命令行参数
    args = parser.parse_args()

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


if __name__ == "__main__":
    main()
