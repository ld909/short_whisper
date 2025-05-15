#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
视频发布状态跟踪表生成器
-----------------
此脚本用于检查合并视频文件，并生成一个Excel表格，追踪各个语种视频的发布状态。

功能：
1. 为每个频道创建一个Excel表格
2. 每个语种创建一个子表(sheet)
3. 记录每个视频的原始文件名、翻译标题、视频描述和发布状态
4. 支持追加模式，不会覆盖已有信息

使用方法：
  python video_status_tracker.py [参数]

参数：
  -c, --channel      指定要处理的频道名称 (默认：处理所有频道)
  -l, --languages    指定要处理的语言 (默认：处理所有语言)
  --base-path        指定自定义的基础路径，覆盖默认路径

示例：
  # 处理所有频道和语言
  python video_status_tracker.py

  # 只处理频道'buddha'
  python video_status_tracker.py -c buddha

  # 只处理特定语言
  python video_status_tracker.py -l en ja

  # 指定自定义基础路径
  python video_status_tracker.py --base-path /path/to/custom/base
"""

import os
import json
import argparse
import platform
import pandas as pd
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException


# 获取基础路径函数
def get_base_path():
    """根据操作系统类型返回对应的基础路径"""
    if platform.system() == "Darwin":  # Mac OS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# 基础路径
BASE_PATH = get_base_path()

# 目录配置
MP4_WITH_AUDIO_DIR = f"{BASE_PATH}/mp4_with_audio"
TITLES_DIR = f"{BASE_PATH}/multi_lang_titles"
DESC_DIR = f"{BASE_PATH}/multi_lang_desc"
OUTPUT_DIR = f"{BASE_PATH}/video_status_excel"
SHORTENED_TITLES_DIR = f"{BASE_PATH}/title_shorten_multi_lang"  # 添加简化标题目录

# 语言映射
LANGUAGE_CODES = {"en": "English", "ja": "Japanese", "vi": "Vietnamese", "ko": "Korean"}


def ensure_dir_exists(directory):
    """确保目录存在，不存在则创建"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"已创建目录: {directory}")


def get_channels(base_dir):
    """获取所有频道目录"""
    if not os.path.exists(base_dir):
        print(f"错误: 目录不存在 {base_dir}")
        return []

    return [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]


def get_languages(channel_dir):
    """获取频道的所有语言目录"""
    if not os.path.exists(channel_dir):
        print(f"错误: 频道目录不存在 {channel_dir}")
        return []

    return [
        d
        for d in os.listdir(channel_dir)
        if os.path.isdir(os.path.join(channel_dir, d))
    ]


def get_videos_in_language(mp4_lang_dir):
    """获取特定语言目录下的所有视频文件"""
    if not os.path.exists(mp4_lang_dir):
        print(f"错误: 语言目录不存在 {mp4_lang_dir}")
        return []

    return [f.split(".")[0] for f in os.listdir(mp4_lang_dir) if f.endswith(".mp4")]


def get_translated_title(channel, video_name, lang_code):
    """获取翻译后的视频标题（从简化标题目录获取）"""
    # 从简化标题目录获取标题
    shortened_title_file = os.path.join(SHORTENED_TITLES_DIR, channel, lang_code, f"{video_name}.txt")
    if os.path.exists(shortened_title_file):
        try:
            with open(shortened_title_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            print(f"读取简化标题文件出错 {shortened_title_file}: {e}")
    
    # 如果简化标题不存在，回退到原来的方法
    title_file = os.path.join(TITLES_DIR, channel, f"{video_name}.json")
    if os.path.exists(title_file):
        try:
            with open(title_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 返回特定语言的标题，如果不存在则返回原始标题
                return data.get(lang_code, data.get("original", video_name))
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"读取标题文件出错 {title_file}: {e}")

    return video_name


def get_video_description(channel, video_name, lang_code):
    """获取视频描述"""
    desc_file = os.path.join(DESC_DIR, channel, lang_code, f"{video_name}.txt")
    if os.path.exists(desc_file):
        try:
            with open(desc_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            print(f"读取描述文件出错 {desc_file}: {e}")

    return ""


def create_or_update_excel(channel, languages=None):
    """为指定频道创建或更新Excel文件"""
    # 如果没有指定语言，则使用所有可用语言
    if languages is None:
        channel_dir = os.path.join(MP4_WITH_AUDIO_DIR, channel)
        languages = get_languages(channel_dir)

    excel_file = os.path.join(OUTPUT_DIR, f"{channel}.xlsx")
    print(f"\n处理频道: {channel}")
    print(f"输出文件: {excel_file}")

    # 确保输出目录存在
    ensure_dir_exists(OUTPUT_DIR)

    # 检查是否已存在Excel文件
    existing_data = {}
    if os.path.exists(excel_file):
        try:
            # 读取现有Excel文件中的所有sheets数据
            existing_data = pd.read_excel(excel_file, sheet_name=None)
            print(f"已加载现有Excel文件: {excel_file}")
        except Exception as e:
            print(f"读取现有Excel文件出错: {e}")
            existing_data = {}

    # 创建新的Excel写入器
    excel_writer = pd.ExcelWriter(excel_file, engine="openpyxl")

    # 处理每个语言
    for lang_code in languages:
        if lang_code not in LANGUAGE_CODES:
            print(f"跳过未知语言代码: {lang_code}")
            continue

        lang_name = LANGUAGE_CODES[lang_code]
        print(f"处理语言: {lang_name} ({lang_code})")

        mp4_lang_dir = os.path.join(MP4_WITH_AUDIO_DIR, channel, lang_code)
        videos = get_videos_in_language(mp4_lang_dir)

        if not videos:
            print(f"在 {channel}/{lang_code} 中未找到视频，跳过")
            continue

        # 准备数据
        data = []
        for video_name in videos:
            title = get_translated_title(channel, video_name, lang_code)
            description = get_video_description(channel, video_name, lang_code)

            data.append(
                {
                    "原始文件名": video_name,
                    "翻译标题": title,
                    "视频描述": description,
                    "已发布": 0,  # 默认未发布
                    "发布日期": 0,  # 默认发布日期为0
                }
            )

        # 创建新DataFrame
        df = pd.DataFrame(data)

        # 如果该语言的sheet已存在，合并现有数据和新数据
        if lang_code in existing_data:
            existing_df = existing_data[lang_code]

            # 找出现有DataFrame中不存在的视频
            existing_files = set(existing_df["原始文件名"])
            new_entries = [
                row for row in data if row["原始文件名"] not in existing_files
            ]

            if new_entries:
                # 将新条目添加到现有DataFrame
                new_df = pd.DataFrame(new_entries)
                # 合并现有和新数据
                df = pd.concat([existing_df, new_df], ignore_index=True)
                print(f"已添加 {len(new_entries)} 个新视频到 {lang_name} sheet")
            else:
                # 如果没有新条目，直接使用现有数据
                df = existing_df
                print(f"{lang_name} sheet 中没有新视频需要添加")
        else:
            print(f"已创建新的 {lang_name} sheet 包含 {len(data)} 个视频")

        # 将数据写入Excel
        df.to_excel(excel_writer, sheet_name=lang_code, index=False)

    # 保存Excel文件
    excel_writer.close()
    print(f"已成功更新Excel文件: {excel_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="生成视频发布状态跟踪Excel表格")
    parser.add_argument("-c", "--channel", help="指定要处理的频道名称")
    parser.add_argument(
        "-l", "--languages", nargs="+", help="指定要处理的语言代码，例如 en ja vi ko"
    )
    parser.add_argument("--base-path", help="指定自定义的基础路径，覆盖默认路径")

    args = parser.parse_args()

    # 如果用户指定了自定义基础路径，则覆盖默认路径
    global BASE_PATH, MP4_WITH_AUDIO_DIR, TITLES_DIR, DESC_DIR, OUTPUT_DIR
    if args.base_path:
        custom_base_path = args.base_path
        BASE_PATH = custom_base_path
        MP4_WITH_AUDIO_DIR = f"{BASE_PATH}/mp4_with_audio"
        TITLES_DIR = f"{BASE_PATH}/multi_lang_titles"
        DESC_DIR = f"{BASE_PATH}/multi_lang_desc"
        OUTPUT_DIR = f"{BASE_PATH}/video_status_excel"
        print(f"使用自定义基础路径: {custom_base_path}")
    else:
        print(f"使用默认基础路径: {BASE_PATH}")

    # 处理指定频道或所有频道
    if args.channel:
        channels = [args.channel]
        print(f"处理指定频道: {args.channel}")
    else:
        channels = get_channels(MP4_WITH_AUDIO_DIR)
        print(f"找到 {len(channels)} 个频道目录: {', '.join(channels)}")

    # 验证语言代码
    if args.languages:
        invalid_langs = [l for l in args.languages if l not in LANGUAGE_CODES]
        if invalid_langs:
            print(f"警告: 未知语言代码 {', '.join(invalid_langs)}，将被忽略")
        languages = [l for l in args.languages if l in LANGUAGE_CODES]
    else:
        languages = None  # 处理全部语言

    # 处理每个频道
    for channel in channels:
        try:
            create_or_update_excel(channel, languages)
        except Exception as e:
            print(f"处理频道 {channel} 时出错: {e}")

    print("\n所有Excel表格已生成完成！")


if __name__ == "__main__":
    main()
