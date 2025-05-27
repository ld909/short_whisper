#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理纯标点符号文件工具

功能说明:
此脚本用于检查 split_sentences_zh_srt.py 输出的 txt 文件，如果发现有单行全是标点符号的文件，
则删除该文件以及对应的多语种 srt 和 txt 文件。

检查路径:
- [媒体路径]/zh_subtitle_split_txt/[频道名称]/

删除路径:
- [媒体路径]/multi_lang_srt/[频道名称]/[语种]/
- [媒体路径]/multi_lang_txt/[频道名称]/[语种]/

使用方法:
1. 基本使用: python clean_punctuation_only_files.py
2. 调试模式: python clean_punctuation_only_files.py -d
3. 预览模式（不实际删除）: python clean_punctuation_only_files.py -p
"""

import os
import re
import sys
import argparse
import platform
import glob
from tqdm import tqdm


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# 获取媒体基础路径
BASE_MEDIA_PATH = get_base_media_path()
# 中文分句txt目录 (来自split_sentences_zh_srt.py的输出)
ZH_SPLIT_TXT_PATH = os.path.join(BASE_MEDIA_PATH, "zh_subtitle_split_txt")
# 多语种srt目录
MULTI_LANG_SRT_PATH = os.path.join(BASE_MEDIA_PATH, "multi_lang_srt")
# 多语种txt目录
MULTI_LANG_TXT_PATH = os.path.join(BASE_MEDIA_PATH, "multi_lang_txt")

# 调试模式标志
DEBUG_MODE = False
# 预览模式标志（不实际删除文件）
PREVIEW_MODE = False


def is_all_punctuation(text):
    """
    检查文本是否全部由标点符号组成（包括中英文标点符号）

    Args:
        text: 要检查的文本

    Returns:
        bool: 如果文本全部由标点符号组成返回True，否则返回False
    """
    if not text or not text.strip():
        return True

    # 移除所有空白字符
    text = text.strip()

    # 定义中英文标点符号集合
    punctuation_chars = set(
        '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~。！？，、；：""'
        "（）【】《》〈〉「」『』〔〕…—–‚„‹›«»‰′″‴※‼⁇⁈⁉⁏⁗"
    )

    # 检查每个字符是否都是标点符号
    for char in text:
        if char not in punctuation_chars and not char.isspace():
            return False

    return True


def has_punctuation_only_lines(file_path):
    """
    检查文件是否包含只有标点符号的行

    Args:
        file_path: 文件路径

    Returns:
        tuple: (是否包含纯标点行, 纯标点行列表)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        punctuation_only_lines = []
        for i, line in enumerate(lines, 1):
            line_content = line.strip()
            if line_content and is_all_punctuation(line_content):
                punctuation_only_lines.append((i, line_content))

        return len(punctuation_only_lines) > 0, punctuation_only_lines

    except Exception as e:
        if DEBUG_MODE:
            print(f"读取文件 {file_path} 时出错: {e}")
        return False, []


def get_corresponding_files(zh_txt_file, channel):
    """
    根据中文txt文件路径，获取对应的多语种文件路径

    Args:
        zh_txt_file: 中文txt文件路径
        channel: 频道名称

    Returns:
        tuple: (多语种srt文件列表, 多语种txt文件列表)
    """
    # 获取文件名（不含扩展名）
    base_name = os.path.splitext(os.path.basename(zh_txt_file))[0]

    multi_lang_srt_files = []
    multi_lang_txt_files = []

    # 检查多语种srt目录
    channel_srt_path = os.path.join(MULTI_LANG_SRT_PATH, channel)
    if os.path.exists(channel_srt_path):
        # 遍历所有语种目录
        for lang_dir in os.listdir(channel_srt_path):
            lang_path = os.path.join(channel_srt_path, lang_dir)
            if os.path.isdir(lang_path):
                srt_file = os.path.join(lang_path, f"{base_name}.srt")
                if os.path.exists(srt_file):
                    multi_lang_srt_files.append(srt_file)

    # 检查多语种txt目录
    channel_txt_path = os.path.join(MULTI_LANG_TXT_PATH, channel)
    if os.path.exists(channel_txt_path):
        # 遍历所有语种目录
        for lang_dir in os.listdir(channel_txt_path):
            lang_path = os.path.join(channel_txt_path, lang_dir)
            if os.path.isdir(lang_path):
                txt_file = os.path.join(lang_path, f"{base_name}.txt")
                if os.path.exists(txt_file):
                    multi_lang_txt_files.append(txt_file)

    return multi_lang_srt_files, multi_lang_txt_files


def delete_file_safely(file_path):
    """
    安全删除文件

    Args:
        file_path: 要删除的文件路径

    Returns:
        bool: 删除是否成功
    """
    try:
        if PREVIEW_MODE:
            print(f"  [预览] 将删除: {file_path}")
            return True
        else:
            os.remove(file_path)
            if DEBUG_MODE:
                print(f"  已删除: {file_path}")
            return True
    except Exception as e:
        print(f"  删除失败 {file_path}: {e}")
        return False


def process_channel(channel_path):
    """
    处理单个频道目录

    Args:
        channel_path: 频道目录路径

    Returns:
        tuple: (处理的文件数, 删除的文件组数, 删除的中文txt数, 删除的srt数, 删除的多语种txt数)
    """
    channel = os.path.basename(channel_path)

    # 获取所有txt文件
    txt_files = glob.glob(os.path.join(channel_path, "*.txt"))
    txt_files = [f for f in txt_files if not os.path.basename(f).startswith(".")]

    if not txt_files:
        if DEBUG_MODE:
            print(f"频道 {channel} 中没有找到txt文件")
        return 0, 0, 0, 0, 0

    processed_count = 0
    deleted_groups = 0
    deleted_zh_txt = 0
    deleted_srt = 0
    deleted_multi_txt = 0

    print(f"\n处理频道: {channel} ({len(txt_files)} 个文件)")

    for txt_file in tqdm(txt_files, desc=f"检查 {channel}"):
        processed_count += 1

        # 检查是否包含纯标点行
        has_punct_lines, punct_lines = has_punctuation_only_lines(txt_file)

        if has_punct_lines:
            file_name = os.path.basename(txt_file)
            print(f"\n发现包含纯标点行的文件: {file_name}")

            if DEBUG_MODE:
                print(f"  纯标点行:")
                for line_num, line_content in punct_lines:
                    print(f"    第{line_num}行: '{line_content}'")

            # 获取对应的多语种文件
            srt_files, multi_txt_files = get_corresponding_files(txt_file, channel)

            # 统计要删除的文件
            files_to_delete = [txt_file] + srt_files + multi_txt_files

            print(f"  将删除 {len(files_to_delete)} 个相关文件:")
            print(f"    - 中文txt: 1 个")
            print(f"    - 多语种srt: {len(srt_files)} 个")
            print(f"    - 多语种txt: {len(multi_txt_files)} 个")

            # 删除所有相关文件并统计各类型
            zh_txt_deleted = 0
            srt_deleted = 0
            multi_txt_deleted = 0

            # 删除中文txt文件
            if delete_file_safely(txt_file):
                zh_txt_deleted = 1

            # 删除srt文件
            for srt_file in srt_files:
                if delete_file_safely(srt_file):
                    srt_deleted += 1

            # 删除多语种txt文件
            for multi_txt_file in multi_txt_files:
                if delete_file_safely(multi_txt_file):
                    multi_txt_deleted += 1

            total_deleted_this_group = zh_txt_deleted + srt_deleted + multi_txt_deleted
            expected_total = 1 + len(srt_files) + len(multi_txt_files)

            if total_deleted_this_group == expected_total:
                deleted_groups += 1
                deleted_zh_txt += zh_txt_deleted
                deleted_srt += srt_deleted
                deleted_multi_txt += multi_txt_deleted
                print(f"  ✅ 成功删除所有 {total_deleted_this_group} 个相关文件")
            else:
                deleted_zh_txt += zh_txt_deleted
                deleted_srt += srt_deleted
                deleted_multi_txt += multi_txt_deleted
                print(
                    f"  ⚠️ 部分删除失败，成功删除 {total_deleted_this_group}/{expected_total} 个文件"
                )

    return (
        processed_count,
        deleted_groups,
        deleted_zh_txt,
        deleted_srt,
        deleted_multi_txt,
    )


def main():
    """主函数"""
    global DEBUG_MODE, PREVIEW_MODE

    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description="清理包含纯标点符号行的txt文件及其对应的多语种文件"
    )

    parser.add_argument(
        "-d", "--debug", action="store_true", help="启用调试模式，显示详细处理信息"
    )
    parser.add_argument(
        "-p",
        "--preview",
        action="store_true",
        help="预览模式，只显示将要删除的文件，不实际删除",
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 设置模式标志
    DEBUG_MODE = args.debug
    PREVIEW_MODE = args.preview

    if DEBUG_MODE:
        print("调试模式已启用")
    if PREVIEW_MODE:
        print("预览模式已启用 - 不会实际删除文件")

    print(f"🔍 检查路径: {ZH_SPLIT_TXT_PATH}")
    print(f"🗑️  多语种srt路径: {MULTI_LANG_SRT_PATH}")
    print(f"🗑️  多语种txt路径: {MULTI_LANG_TXT_PATH}")

    # 检查输入路径是否存在
    if not os.path.exists(ZH_SPLIT_TXT_PATH):
        print(f"❌ 错误: 输入路径 '{ZH_SPLIT_TXT_PATH}' 不存在")
        return

    # 获取所有频道目录
    channels = [
        d
        for d in os.listdir(ZH_SPLIT_TXT_PATH)
        if os.path.isdir(os.path.join(ZH_SPLIT_TXT_PATH, d)) and not d.startswith(".")
    ]

    if not channels:
        print(f"在 '{ZH_SPLIT_TXT_PATH}' 中未找到任何频道目录")
        return

    print(f"找到 {len(channels)} 个频道目录")

    # 统计信息
    total_processed = 0
    total_deleted_groups = 0
    total_deleted_zh_txt = 0
    total_deleted_srt = 0
    total_deleted_multi_txt = 0

    # 处理每个频道
    for channel in channels:
        channel_path = os.path.join(ZH_SPLIT_TXT_PATH, channel)
        processed, deleted_groups, deleted_zh_txt, deleted_srt, deleted_multi_txt = (
            process_channel(channel_path)
        )

        total_processed += processed
        total_deleted_groups += deleted_groups
        total_deleted_zh_txt += deleted_zh_txt
        total_deleted_srt += deleted_srt
        total_deleted_multi_txt += deleted_multi_txt

    # 计算总删除文件数
    total_deleted_files = (
        total_deleted_zh_txt + total_deleted_srt + total_deleted_multi_txt
    )

    # 显示总结
    print(f"\n{'='*60}")
    print(f"🎯 处理完成！")
    print(f"📊 总计处理文件: {total_processed}")
    print(f"🗑️  删除的文件组: {total_deleted_groups}")
    print(f"🗑️  删除的总文件数: {total_deleted_files}")
    print(f"   ├─ zh_subtitle_split_txt: {total_deleted_zh_txt} 个")
    print(f"   ├─ multi_lang_srt: {total_deleted_srt} 个")
    print(f"   └─ multi_lang_txt: {total_deleted_multi_txt} 个")

    if PREVIEW_MODE:
        print(f"💡 这是预览模式，没有实际删除文件")
        print(f"💡 要实际执行删除，请运行: python {os.path.basename(__file__)}")
    elif total_deleted_groups > 0:
        print(f"✅ 成功清理了 {total_deleted_groups} 组包含纯标点行的文件")
    else:
        print(f"✅ 没有发现包含纯标点行的文件")


if __name__ == "__main__":
    main()
