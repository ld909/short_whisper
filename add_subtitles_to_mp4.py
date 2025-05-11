#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多语言视频字幕添加工具

功能说明:
此脚本用于为多语言视频自动添加对应语言的SRT字幕，并使用适合的字体进行渲染。
支持多种语言，包括英语(en)、日语(ja)、越南语(vi)和韩语(ko)等。

目录结构:
- 输入MP4目录: /Volumes/dhl/buda_videos_youtube/mp4_merge_silient/
- 输入SRT目录: /Volumes/dhl/buda_videos_youtube/multi_lang_srt/
- 字体目录: /Users/donghaoliu/doc/short_whisper/fonts/
- 输出MP4目录: /Volumes/dhl/buda_videos_youtube/mp4_multi_with_subtitles/

处理流程:
1. 遍历MP4目录，寻找所有需要处理的视频文件
2. 为每个视频查找对应的SRT字幕文件
3. 根据语言选择合适的字体
4. 使用ffmpeg为视频添加字幕
5. 顺序处理每个视频（一个处理完成后再处理下一个）

使用方法:
python add_subtitles_to_mp4.py [-l LANGUAGES] [-f] [-s CHANNEL/VIDEO]

参数说明:
- -l, --languages: 指定需要处理的语言，默认处理所有支持的语言
- -f, --force: 强制重新生成已存在的视频文件
- -s, --single: 指定只处理单个视频，格式为"频道名/视频名"
"""

import os
import argparse
import platform
import subprocess
import sys
from tqdm import tqdm
import logging
import time
import glob


def get_base_path():
    """根据操作系统类型返回对应的基础路径"""
    if platform.system() == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# 定义全局路径变量
BASE_PATH = get_base_path()
# 输入MP4目录（来自merge_mp4_clips_by_audio_duration.py的输出）
INPUT_MP4_PATH = os.path.join(BASE_PATH, "mp4_merge_silient")
# 输入SRT目录（来自generate_subtitles.py的输出）
INPUT_SRT_PATH = os.path.join(BASE_PATH, "multi_lang_srt")
# 字体目录
FONTS_DIR = "/Users/donghaoliu/doc/short_whisper/fonts"
# 输出MP4目录
OUTPUT_MP4_PATH = os.path.join(BASE_PATH, "mp4_multi_with_subtitles")

# 支持的语言
SUPPORTED_LANGUAGES = ["en", "ja", "vi", "ko"]

# 语言与字体映射
LANGUAGE_FONTS = {
    "en": "Noto_Sans_EN/NotoSans-VariableFont_wdth,wght.ttf",
    "ja": "Noto_Sans_JP/NotoSansJP-VariableFont_wght.ttf",
    "vi": "Noto_Sans_VI/NotoSans-VariableFont_wdth,wght.ttf",
    "ko": "Noto_Sans_KR/NotoSansKR-VariableFont_wght.ttf",
}

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def check_required_tools():
    """检查必要的工具是否安装"""
    try:
        subprocess.run(
            ["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return True
    except FileNotFoundError:
        logger.error("未找到ffmpeg，请先安装ffmpeg")
        return False


def add_subtitle_to_video(video_path, srt_path, output_path, language):
    """为单个视频添加字幕"""
    try:
        # 获取该语言对应的字体
        font_file = LANGUAGE_FONTS.get(language)
        if not font_file:
            logger.error(f"不支持的语言: {language}")
            return False

        font_path = os.path.join(FONTS_DIR, font_file)
        fonts_dir = os.path.dirname(font_path)

        # 根据语言选择合适的字体名称
        if language == "en":
            font_name = "notosans"
        elif language == "ja":
            font_name = "notosansjp"
        elif language == "vi":
            font_name = "notosans"  # 与英文使用相同字体名称
        elif language == "ko":
            font_name = "notosanskr"

        # 创建输出目录
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 构建ffmpeg命令
        cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-vf",
            f"subtitles={srt_path}:fontsdir={fonts_dir}:force_style='Fontname={font_name},FontSize=16,FontWeight=500,PrimaryColour=&HFFFFFF,OutlineColour=&H383838,BorderStyle=1,Outline=0.6,MarginV=20'",
            "-c:a",
            "copy",
            "-y",  # 覆盖已存在的文件
            output_path,
        ]

        # 执行ffmpeg命令
        logger.info(f"正在处理视频: {os.path.basename(video_path)}")
        logger.info(f"使用字幕: {os.path.basename(srt_path)}")
        logger.info(f"使用字体: {font_name}")

        process = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        if process.returncode == 0:
            logger.info(f"成功生成带字幕的视频: {output_path}")
            return True
        else:
            logger.error(f"添加字幕失败: {process.stderr}")
            return False

    except Exception as e:
        logger.error(f"添加字幕时出错: {str(e)}")
        return False


def process_video(channel, video_name, language, force=False):
    """处理单个视频的字幕添加"""
    # 构建输入视频文件路径
    input_video_path = os.path.join(
        INPUT_MP4_PATH, channel, language, f"{video_name}.mp4"
    )

    # 如果输入视频不存在，跳过处理
    if not os.path.exists(input_video_path):
        logger.warning(f"输入视频不存在，跳过: {input_video_path}")
        return False

    # 构建输入字幕文件路径
    input_srt_path = os.path.join(
        INPUT_SRT_PATH, channel, language, f"{video_name}.srt"
    )

    # 如果输入字幕不存在，跳过处理
    if not os.path.exists(input_srt_path):
        logger.warning(f"输入字幕不存在，跳过: {input_srt_path}")
        return False

    # 构建输出视频路径
    output_video_path = os.path.join(
        OUTPUT_MP4_PATH, channel, language, f"{video_name}.mp4"
    )

    # 如果输出文件已存在且不强制重新生成，则跳过
    if os.path.exists(output_video_path) and not force:
        logger.info(f"输出文件已存在，跳过: {output_video_path}")
        return True

    # 为视频添加字幕
    return add_subtitle_to_video(
        input_video_path, input_srt_path, output_video_path, language
    )


def process_all_videos(languages=None, force=False):
    """处理所有频道的所有视频（顺序处理）"""
    if languages is None:
        languages = SUPPORTED_LANGUAGES

    # 验证语言是否支持
    for lang in languages[:]:  # 创建一个副本以便在迭代时修改
        if lang not in SUPPORTED_LANGUAGES:
            logger.warning(f"不支持的语言 {lang}，将被忽略")
            languages.remove(lang)

    if not languages:
        logger.error("错误: 没有指定任何有效的语言")
        return

    # 检查输入路径是否存在
    if not os.path.exists(INPUT_MP4_PATH):
        logger.error(f"错误: 输入MP4路径不存在: {INPUT_MP4_PATH}")
        return

    # 获取所有频道目录
    channels = [
        d
        for d in os.listdir(INPUT_MP4_PATH)
        if os.path.isdir(os.path.join(INPUT_MP4_PATH, d))
    ]

    if not channels:
        logger.error(f"在 {INPUT_MP4_PATH} 中未找到任何频道目录")
        return

    logger.info(f"找到 {len(channels)} 个频道目录")

    # 处理每个频道
    tasks = []

    for channel in channels:
        channel_path = os.path.join(INPUT_MP4_PATH, channel)
        logger.info(f"\n处理频道: {channel}")

        # 获取当前频道下的所有语言目录
        lang_dirs = [
            d
            for d in os.listdir(channel_path)
            if os.path.isdir(os.path.join(channel_path, d)) and d in languages
        ]

        if not lang_dirs:
            logger.warning(f"在频道 {channel} 中未找到任何支持的语言目录")
            continue

        # 处理每种语言
        for lang in lang_dirs:
            lang_path = os.path.join(channel_path, lang)

            # 获取该语言下的所有MP4文件
            video_files = glob.glob(os.path.join(lang_path, "*.mp4"))

            for video_file in video_files:
                video_name = os.path.basename(video_file).split(".")[0]

                # 检查对应的SRT文件是否存在
                srt_file = os.path.join(
                    INPUT_SRT_PATH, channel, lang, f"{video_name}.srt"
                )
                if not os.path.exists(srt_file):
                    logger.warning(f"找不到对应的字幕文件，跳过: {srt_file}")
                    continue

                # 检查输出文件是否已存在
                output_file = os.path.join(
                    OUTPUT_MP4_PATH, channel, lang, f"{video_name}.mp4"
                )
                if os.path.exists(output_file) and not force:
                    logger.info(f"输出文件已存在，跳过: {output_file}")
                    continue

                # 添加到任务列表
                tasks.append((channel, video_name, lang))

    total_tasks = len(tasks)
    logger.info(f"找到 {total_tasks} 个待处理任务")

    # 顺序处理任务
    success_count = 0
    for i, (channel, video_name, language) in enumerate(tasks, 1):
        logger.info(f"处理任务 {i}/{total_tasks}: {channel}/{video_name}/{language}")

        try:
            if process_video(channel, video_name, language, force):
                logger.info(f"成功处理 {channel}/{video_name}/{language}")
                success_count += 1
            else:
                logger.error(f"处理失败 {channel}/{video_name}/{language}")
        except Exception as e:
            logger.error(f"处理 {channel}/{video_name}/{language} 时出错: {str(e)}")

    logger.info(f"所有任务处理完成，成功: {success_count}/{total_tasks}")


def main():
    # 检查必要工具
    if not check_required_tools():
        sys.exit(1)

    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="为多语言视频添加字幕")

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
        "-s", "--single", type=str, help="只处理指定的单个视频，格式: 频道名/视频名"
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 处理单个视频模式
    if args.single:
        if "/" not in args.single:
            logger.error("错误: 单个视频参数格式应为 '频道名/视频名'")
            return

        channel, video_name = args.single.split("/", 1)

        logger.info(f"处理单个视频: {channel}/{video_name}")

        success_count = 0
        for language in args.languages:
            if process_video(channel, video_name, language, args.force):
                success_count += 1

        logger.info(
            f"处理完成，成功生成 {success_count}/{len(args.languages)} 个语言版本"
        )
    else:
        # 处理所有频道和视频
        start_time = time.time()
        process_all_videos(args.languages, args.force)
        end_time = time.time()
        logger.info(f"所有处理完成，总耗时: {end_time - start_time:.2f}秒")


if __name__ == "__main__":
    main()
