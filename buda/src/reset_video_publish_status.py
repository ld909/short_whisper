#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
视频发布状态重置器
-----------------
此脚本用于重置指定视频之后的所有视频的发布状态。

功能：
1. 读取video_status_tracker.py生成的Excel文件
2. 指定语言和视频名称（支持带空格的名称）
3. 将该视频之后的所有视频的"已发布"状态设为0，"发布时间"设为空值
4. 保存更新后的Excel文件

使用方法：
  python reset_video_publish_status.py [参数]

参数：
  -c, --channel      指定频道名称 (必需)
  -l, --language     指定语言代码 (必需)
  -v, --video        指定视频名称，支持带空格的名称 (必需)
  --base-path        指定自定义的基础路径，覆盖默认路径

示例：
  # 重置buddha频道英文版本中"meditation basics"视频之后的发布状态
  python reset_video_publish_status.py -c buddha -l en -v "meditation basics"

  # 重置特定频道日语版本中某个视频之后的状态
  python reset_video_publish_status.py -c buddha -l ja -v "瞑想の基本"
"""

import os
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

# 目录配置 - 参考generate_mp4_publish_tracker.py的输出方式
# Excel文件直接放在基础路径下，文件名为mp4_publish_tracker.xlsx
EXCEL_FILE = f"{BASE_PATH}/mp4_publish_tracker.xlsx"

# 语言映射
LANGUAGE_CODES = {"en": "English", "ja": "Japanese", "vi": "Vietnamese", "ko": "Korean"}


def find_video_in_excel(excel_file, channel, language, video_name):
    """
    在Excel文件中查找指定视频的位置

    Args:
        excel_file: Excel文件路径
        channel: 频道名称
        language: 语言代码
        video_name: 视频名称（可能是MP4文件名）

    Returns:
        tuple: (找到的行索引, DataFrame) 或 (None, DataFrame)
    """
    if not os.path.exists(excel_file):
        print(f"错误: Excel文件不存在 {excel_file}")
        return None, None

    try:
        # 读取指定语言的sheet
        df = pd.read_excel(excel_file, sheet_name=language)

        # 确保必要的列存在 - 根据generate_mp4_publish_tracker.py的输出格式
        required_columns = ["频道名称", "MP4名称", "是否发布", "是否已经发布"]
        for col in required_columns:
            if col not in df.columns:
                print(f"错误: 缺少必要的列 '{col}'")
                return None, None

        # 如果没有"发布时间"列，则添加
        if "发布时间" not in df.columns:
            df["发布时间"] = ""
            print("已添加'发布时间'列")

        # 先按频道过滤
        channel_mask = df["频道名称"] == channel
        channel_df = df[channel_mask]

        if len(channel_df) == 0:
            print(f"错误: 在{language}语言中未找到频道'{channel}'的视频")
            return None, df

        # 在MP4文件名中查找 - 支持部分匹配
        mask_mp4 = channel_df["MP4名称"].str.contains(video_name, case=False, na=False)

        matches = channel_df[mask_mp4]

        if len(matches) == 0:
            print(
                f"错误: 在频道'{channel}'的{language}语言中未找到包含'{video_name}'的视频"
            )
            print(f"该频道在{language}语言中共有 {len(channel_df)} 个视频")
            return None, df
        elif len(matches) > 1:
            print(f"警告: 找到多个匹配的视频:")
            for idx, row in matches.iterrows():
                print(f"  - 行{idx+2}: {row['MP4名称']}")
            print("将使用第一个匹配的视频")

        # 返回第一个匹配的索引（在原始DataFrame中的索引）
        target_index = matches.index[0]
        print(f"找到目标视频: {df.loc[target_index, 'MP4名称']}")

        return target_index, df

    except Exception as e:
        print(f"读取Excel文件出错: {e}")
        return None, None


def reset_publish_status_after_video(excel_file, channel, language, video_name):
    """
    重置指定视频之后的所有视频的发布状态
    只重置发布时间存在且大于目标视频发布时间的视频

    Args:
        excel_file: Excel文件路径
        channel: 频道名称
        language: 语言代码
        video_name: 视频名称

    Returns:
        bool: 是否成功重置
    """
    # 查找目标视频
    target_index, df = find_video_in_excel(excel_file, channel, language, video_name)

    if target_index is None or df is None:
        return False

    # 获取目标视频的发布时间
    target_publish_time = df.loc[target_index, "发布时间"]

    # 如果目标视频没有发布时间，则无法进行比较
    if (
        pd.isna(target_publish_time)
        or target_publish_time == ""
        or target_publish_time is None
    ):
        print(f"警告: 目标视频没有发布时间，无法进行重置操作")
        return False

    print(f"目标视频发布时间: {target_publish_time}")

    # 获取该频道的所有视频
    channel_mask = df["频道名称"] == channel
    channel_df = df[channel_mask]

    # 筛选需要重置的视频：发布时间存在且大于目标视频发布时间的视频
    reset_indices = []

    for idx in channel_df.index:
        # 跳过目标视频本身
        if idx == target_index:
            continue

        video_publish_time = df.loc[idx, "发布时间"]

        # 检查发布时间是否存在且不为空
        if (
            pd.isna(video_publish_time)
            or video_publish_time == ""
            or video_publish_time is None
        ):
            continue  # 跳过没有发布时间的视频

        # 比较发布时间（字符串比较，假设时间格式一致）
        try:
            if str(video_publish_time) > str(target_publish_time):
                reset_indices.append(idx)
                print(
                    f"  将重置: {df.loc[idx, 'MP4名称']} (发布时间: {video_publish_time})"
                )
        except Exception as e:
            print(f"  比较时间出错 {df.loc[idx, 'MP4名称']}: {e}")
            continue

    if not reset_indices:
        print(f"提示: 没有找到发布时间晚于目标视频的视频需要重置")
        return True

    print(f"共找到 {len(reset_indices)} 个需要重置的视频")

    # 重置筛选出的视频状态
    df.loc[reset_indices, "是否已经发布"] = 0
    df.loc[reset_indices, "发布时间"] = ""

    try:
        # 读取现有Excel文件的所有sheets
        with pd.ExcelFile(excel_file) as xls:
            all_sheets = {
                sheet_name: pd.read_excel(xls, sheet_name)
                for sheet_name in xls.sheet_names
            }

        # 更新指定语言的sheet
        all_sheets[language] = df

        # 写回Excel文件
        with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
            for sheet_name, sheet_df in all_sheets.items():
                sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

        print(f"成功重置了 {len(reset_indices)} 个视频的发布状态")
        print(f"已保存更新到: {excel_file}")
        return True

    except Exception as e:
        print(f"保存Excel文件出错: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="重置视频发布状态")
    parser.add_argument("-c", "--channel", required=True, help="指定频道名称")
    parser.add_argument(
        "-l", "--language", required=True, help="指定语言代码 (en, ja, vi, ko)"
    )
    parser.add_argument(
        "-v", "--video", required=True, help="指定视频名称（支持部分匹配）"
    )
    parser.add_argument("--base-path", help="指定自定义的基础路径，覆盖默认路径")
    parser.add_argument("--excel-file", help="直接指定Excel文件路径")

    args = parser.parse_args()

    # 如果用户指定了自定义基础路径，则覆盖默认路径
    global BASE_PATH, EXCEL_FILE
    if args.base_path:
        custom_base_path = args.base_path
        BASE_PATH = custom_base_path
        EXCEL_FILE = f"{BASE_PATH}/mp4_publish_tracker.xlsx"
        print(f"使用自定义基础路径: {custom_base_path}")
    else:
        print(f"使用默认基础路径: {BASE_PATH}")

    # 验证语言代码
    if args.language not in LANGUAGE_CODES:
        print(f"错误: 不支持的语言代码 '{args.language}'")
        print(f"支持的语言代码: {', '.join(LANGUAGE_CODES.keys())}")
        return

        # 确定Excel文件路径
    if args.excel_file:
        # 用户直接指定了Excel文件路径
        excel_file = args.excel_file
        print(f"使用指定的Excel文件: {excel_file}")
    else:
        # 尝试多个可能的路径
        possible_paths = [
            EXCEL_FILE,  # 默认路径
            os.path.join(os.getcwd(), "mp4_publish_tracker.xlsx"),  # 当前目录
            os.path.join(
                os.getcwd(), "buda", "mp4_publish_tracker.xlsx"
            ),  # 当前目录的buda子目录
        ]

        excel_file = None
        for path in possible_paths:
            if os.path.exists(path):
                excel_file = path
                print(f"找到Excel文件: {excel_file}")
                break

        if not excel_file:
            print(f"错误: 在以下路径中都未找到Excel文件:")
            for path in possible_paths:
                print(f"  - {path}")
            print(f"请先运行 generate_mp4_publish_tracker.py 生成Excel文件")
            print(f"或使用 --excel-file 参数直接指定Excel文件路径")
            return

    print(f"目标频道: {args.channel}")
    print(f"目标语言: {LANGUAGE_CODES[args.language]} ({args.language})")
    print(f"目标视频: {args.video}")
    print(f"Excel文件: {excel_file}")
    print("-" * 50)

    # 执行重置操作
    success = reset_publish_status_after_video(
        excel_file, args.channel, args.language, args.video
    )

    if success:
        print("\n✅ 重置操作完成！")
    else:
        print("\n❌ 重置操作失败！")


if __name__ == "__main__":
    main()
