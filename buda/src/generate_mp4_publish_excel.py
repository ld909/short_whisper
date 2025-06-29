#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MP4发布状态跟踪器
================
这个脚本用于扫描merge_mp4_mp3.py输出的MP4文件，并生成Excel跟踪表来管理视频发布状态。

功能:
- 扫描输出目录中的所有MP4文件
- 为每种语言创建一个Excel工作表
- 跟踪五个字段：频道名称、MP4名称、是否发布（默认1）、是否已经发布（默认0）、发布时间（默认空）
- 只添加新的MP4文件，不修改已存在的记录
- 支持多个频道和语言
- 自动处理旧版本跟踪文件的兼容性升级

输入目录:
- MP4文件目录: /media/dhl/buda_videos_youtube/mp4_with_audio/频道名/语言/ (Linux)
- MP4文件目录: /Volumes/dhl/buda_videos_youtube/mp4_with_audio/频道名/语言/ (Mac)

输出文件:
- Excel文件: mp4_publish_tracker.xlsx

命令行参数:
  -c, --channel     指定要处理的频道名（可选，默认处理所有频道）
  -o, --output      指定输出Excel文件名（默认：mp4_publish_tracker.xlsx）
  --base-path       指定自定义的基础路径，覆盖默认路径
  --list-channels   列出所有可用频道
  --list-languages  列出所有可用语言

示例:
  # 扫描所有频道的所有语言，生成跟踪表
  python generate_mp4_publish_tracker.py

  # 只处理特定频道
  python generate_mp4_publish_tracker.py -c buddha

  # 指定输出文件名
  python generate_mp4_publish_tracker.py -o my_tracker.xlsx

  # 列出所有频道
  python generate_mp4_publish_tracker.py --list-channels

  # 使用自定义基础路径
  python generate_mp4_publish_tracker.py --base-path /path/to/custom/base
"""

import os
import glob
import argparse
import platform
import pandas as pd
from pathlib import Path
from collections import defaultdict


def get_base_path():
    """根据操作系统类型返回对应的基础路径"""
    if platform.system() == "Darwin":  # Mac OS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# 基础路径和配置
BASE_PATH = get_base_path()
MP4_INPUT_DIR = f"{BASE_PATH}/mp4_with_audio"
DEFAULT_OUTPUT_FILE = "mp4_publish_tracker.xlsx"


def scan_mp4_files(base_dir, specific_channel=None):
    """
    扫描MP4文件并按语言分组

    返回格式:
    {
        'language1': [
            {'channel': 'channel1', 'filename': 'video1.mp4', 'filepath': '/path/to/video1.mp4'},
            {'channel': 'channel2', 'filename': 'video2.mp4', 'filepath': '/path/to/video2.mp4'},
        ],
        'language2': [...]
    }
    """
    if not os.path.exists(base_dir):
        print(f"错误: 输入目录不存在 {base_dir}")
        return {}

    language_files = defaultdict(list)

    # 获取所有频道目录
    if specific_channel:
        channel_dirs = (
            [specific_channel]
            if os.path.isdir(os.path.join(base_dir, specific_channel))
            else []
        )
        if not channel_dirs:
            print(
                f"错误: 指定的频道目录不存在 {os.path.join(base_dir, specific_channel)}"
            )
            return {}
    else:
        channel_dirs = [
            d
            for d in os.listdir(base_dir)
            if os.path.isdir(os.path.join(base_dir, d)) and not d.startswith(".")
        ]

    print(f"扫描频道: {', '.join(channel_dirs)}")

    # 遍历每个频道
    for channel in channel_dirs:
        channel_path = os.path.join(base_dir, channel)

        # 获取频道下的语言目录
        if os.path.isdir(channel_path):
            language_dirs = [
                d
                for d in os.listdir(channel_path)
                if os.path.isdir(os.path.join(channel_path, d))
                and not d.startswith(".")
            ]

            # 遍历每种语言
            for language in language_dirs:
                language_path = os.path.join(channel_path, language)

                # 扫描MP4文件
                mp4_pattern = os.path.join(language_path, "*.mp4")
                mp4_files = glob.glob(mp4_pattern)

                # 添加到对应语言的列表中
                for mp4_file in mp4_files:
                    filename = os.path.basename(mp4_file)
                    # 跳过隐藏文件
                    if not filename.startswith("."):
                        language_files[language].append(
                            {
                                "channel": channel,
                                "filename": filename,
                                "filepath": mp4_file,
                            }
                        )

    # 打印扫描结果统计
    total_files = sum(len(files) for files in language_files.values())
    print(f"\n扫描完成:")
    print(f"总计发现 {total_files} 个MP4文件")
    for language, files in language_files.items():
        print(f"- {language}: {len(files)} 个文件")

    return dict(language_files)


def load_existing_tracker(output_file):
    """
    加载现有的跟踪Excel文件

    返回格式:
    {
        'language1': DataFrame,
        'language2': DataFrame,
        ...
    }
    """
    existing_data = {}

    if os.path.exists(output_file):
        print(f"发现现有跟踪文件: {output_file}")
        try:
            # 读取所有工作表
            excel_file = pd.ExcelFile(output_file)
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(output_file, sheet_name=sheet_name)
                # 确保列名正确，兼容不同版本
                if len(df.columns) >= 3:
                    if len(df.columns) == 3:
                        # 旧版本，只有3列：MP4名称、是否发布、是否已经发布
                        df.columns = ["MP4名称", "是否发布", "是否已经发布"]
                        # 添加缺失的列
                        df.insert(0, "频道名称", "")  # 添加频道名称列
                        df["发布时间"] = ""  # 添加发布时间列
                    elif len(df.columns) == 4:
                        # 中间版本，有4列：MP4名称、是否发布、是否已经发布、发布时间
                        df.columns = ["MP4名称", "是否发布", "是否已经发布", "发布时间"]
                        # 添加频道名称列
                        df.insert(0, "频道名称", "")
                    else:
                        # 新版本，有5列或更多：频道名称、MP4名称、是否发布、是否已经发布、发布时间
                        df.columns = [
                            "频道名称",
                            "MP4名称",
                            "是否发布",
                            "是否已经发布",
                            "发布时间",
                        ] + list(df.columns[5:])

                    existing_data[sheet_name] = df
                    print(f"- 工作表 '{sheet_name}': {len(df)} 条现有记录")
        except Exception as e:
            print(f"读取现有文件时出错: {e}")
            print("将创建新的跟踪文件")
    else:
        print(f"未发现现有跟踪文件，将创建新文件: {output_file}")

    return existing_data


def update_tracker(language_files, existing_data, output_file):
    """
    更新跟踪器，只添加新的MP4文件
    """
    updated_data = {}
    new_files_count = 0

    # 处理每种语言
    for language, files in language_files.items():
        print(f"\n处理语言: {language}")

        # 获取现有数据或创建新的DataFrame
        if language in existing_data:
            df = existing_data[language].copy()

            # 检查并添加缺失的列
            if "频道名称" not in df.columns:
                # 如果没有频道名称列，添加到第一列
                df.insert(0, "频道名称", "")
            if "发布时间" not in df.columns:
                df["发布时间"] = ""

            # 确保列的顺序正确
            expected_columns = [
                "频道名称",
                "MP4名称",
                "是否发布",
                "是否已经发布",
                "发布时间",
            ]
            # 保留可能存在的额外列
            extra_columns = [col for col in df.columns if col not in expected_columns]
            df = df[expected_columns + extra_columns]

            existing_filenames = set(df["MP4名称"].values)
            print(f"- 现有记录: {len(existing_filenames)} 个")
        else:
            df = pd.DataFrame(
                columns=["频道名称", "MP4名称", "是否发布", "是否已经发布", "发布时间"]
            )
            existing_filenames = set()
            print(f"- 新建工作表")

        # 添加新文件
        new_files = []
        for file_info in files:
            filename = file_info["filename"]
            channel = file_info["channel"]
            if filename not in existing_filenames:
                new_files.append(
                    {
                        "频道名称": channel,
                        "MP4名称": filename,
                        "是否发布": 1,  # 默认值
                        "是否已经发布": 0,  # 默认值
                        "发布时间": "",  # 默认值为空
                    }
                )
                new_files_count += 1

        if new_files:
            print(f"- 发现新文件: {len(new_files)} 个")
            new_df = pd.DataFrame(new_files)
            df = pd.concat([df, new_df], ignore_index=True)
        else:
            print(f"- 没有新文件需要添加")

        # 按频道名称和文件名排序
        df = df.sort_values(["频道名称", "MP4名称"]).reset_index(drop=True)
        updated_data[language] = df

    # 保存到Excel文件
    if updated_data:
        try:
            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                for language, df in updated_data.items():
                    # 限制工作表名称长度（Excel限制31个字符）
                    sheet_name = language[:31] if len(language) > 31 else language
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    print(f"保存工作表 '{sheet_name}': {len(df)} 条记录")

            print(f"\n✅ 跟踪文件已更新: {output_file}")
            print(f"新增 {new_files_count} 个MP4文件记录")

        except Exception as e:
            print(f"❌ 保存文件时出错: {e}")
    else:
        print("没有数据需要保存")


def list_channels(base_dir):
    """列出所有可用频道"""
    if not os.path.exists(base_dir):
        print(f"错误: 输入目录不存在 {base_dir}")
        return []

    channels = [
        d
        for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d)) and not d.startswith(".")
    ]

    if not channels:
        print("未找到任何频道目录")
        return []

    print("可用频道列表:")
    for channel in sorted(channels):
        print(f"- {channel}")

    return sorted(channels)


def list_languages(base_dir):
    """列出所有可用语言"""
    if not os.path.exists(base_dir):
        print(f"错误: 输入目录不存在 {base_dir}")
        return []

    languages = set()

    # 遍历所有频道
    for channel in os.listdir(base_dir):
        channel_path = os.path.join(base_dir, channel)
        if os.path.isdir(channel_path) and not channel.startswith("."):
            # 获取频道下的语言目录
            for language in os.listdir(channel_path):
                language_path = os.path.join(channel_path, language)
                if os.path.isdir(language_path) and not language.startswith("."):
                    languages.add(language)

    if not languages:
        print("未找到任何语言目录")
        return []

    print("可用语言列表:")
    for language in sorted(languages):
        print(f"- {language}")

    return sorted(languages)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="MP4发布状态跟踪器")
    parser.add_argument(
        "-c", "--channel", help="指定要处理的频道名（可选，默认处理所有频道）"
    )
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_FILE,
        help=f"指定输出Excel文件名（默认：{DEFAULT_OUTPUT_FILE}）",
    )
    parser.add_argument("--base-path", help="指定自定义的基础路径，覆盖默认路径")
    parser.add_argument("--list-channels", action="store_true", help="列出所有可用频道")
    parser.add_argument(
        "--list-languages", action="store_true", help="列出所有可用语言"
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    # 如果用户指定了自定义基础路径，则覆盖默认路径
    global MP4_INPUT_DIR
    if args.base_path:
        custom_base_path = args.base_path
        MP4_INPUT_DIR = f"{custom_base_path}/mp4_with_audio"
        print(f"使用自定义基础路径: {custom_base_path}")
    else:
        # 打印系统信息和基础路径
        print(f"检测到系统: {platform.system()}")
        print(f"使用基础路径: {BASE_PATH}")

    print(f"MP4输入目录: {MP4_INPUT_DIR}")

    # 处理列表命令
    if args.list_channels:
        list_channels(MP4_INPUT_DIR)
        return

    if args.list_languages:
        list_languages(MP4_INPUT_DIR)
        return

    # 检查依赖库
    try:
        import pandas as pd
        import openpyxl
    except ImportError as e:
        print(f"错误: 缺少必要的Python库")
        print(f"请安装: pip install pandas openpyxl")
        print(f"详细错误: {e}")
        return

    # 扫描MP4文件
    print(f"\n开始扫描MP4文件...")
    language_files = scan_mp4_files(MP4_INPUT_DIR, args.channel)

    if not language_files:
        print("未发现任何MP4文件")
        return

    # 加载现有跟踪数据
    existing_data = load_existing_tracker(args.output)

    # 更新跟踪器
    update_tracker(language_files, existing_data, args.output)

    print(f"\n处理完成！")


if __name__ == "__main__":
    main()
