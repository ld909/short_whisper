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
5. 检查生成视频的时长差异，如果超过阈值则自动重新生成
6. 顺序处理每个视频（一个处理完成后再处理下一个）

新增功能:
- 时长差异检查: 自动检查输入视频和输出视频的时长差异
- 自动重新生成: 如果时长差异超过5秒阈值，自动删除输出文件并重新生成
- 简化模式回退: 如果标准模式生成的视频仍有问题，自动使用简化模式重新生成

使用方法:
python add_subtitles_to_mp4.py [-l LANGUAGES] [-f] [-s CHANNEL/VIDEO] [--gpu]

参数说明:
- -l, --languages: 指定需要处理的语言，默认处理所有支持的语言
- -f, --force: 强制重新生成已存在的视频文件
- -s, --single: 指定只处理单个视频，格式为"频道名/视频名"
- --gpu: 使用GPU加速ffmpeg处理
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
import multiprocessing
import json


def get_base_path():
    """根据操作系统类型返回对应的基础路径"""
    if platform.system() == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


def get_fonts_dir():
    """根据操作系统类型返回对应的字体目录"""
    if platform.system() == "Darwin":  # macOS
        return "/Users/donghaoliu/doc/short_whisper/fonts"
    else:  # 默认为Linux/Ubuntu
        # 尝试多个可能的字体路径
        font_paths = [
            "/home/dhl/doc/short_whisper/fonts",  # 用户目录
            "/home/dhl/Documents/short_whisper/fonts",  # 文档目录
            "/usr/share/fonts",  # 系统字体目录
            "/usr/local/share/fonts",  # 本地字体目录
        ]
        
        for path in font_paths:
            if os.path.exists(path):
                return path
        
        # 如果都不存在，返回默认路径并创建
        default_path = "/home/dhl/Documents/short_whisper/fonts"
        os.makedirs(default_path, exist_ok=True)
        return default_path


# 定义全局路径变量
BASE_PATH = get_base_path()
# 输入MP4目录（来自merge_mp4_clips_by_audio_duration.py的输出）
INPUT_MP4_PATH = os.path.join(BASE_PATH, "mp4_merge_silient")
# 输入SRT目录（来自generate_subtitles.py的输出）
INPUT_SRT_PATH = os.path.join(BASE_PATH, "multi_lang_srt")
# 字体目录
FONTS_DIR = get_fonts_dir()
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

# 时长差异阈值（秒）
DURATION_DIFF_THRESHOLD = 5.0


def get_video_duration(video_path):
    """获取视频时长（秒）"""
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            logger.error(f"获取视频时长失败: {video_path}")
            logger.error(f"ffprobe错误: {result.stderr}")
            return None
            
        try:
            data = json.loads(result.stdout)
            duration = float(data['format']['duration'])
            return duration
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"解析视频时长数据失败: {str(e)}")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error(f"获取视频时长超时: {video_path}")
        return None
    except Exception as e:
        logger.error(f"获取视频时长时出错: {str(e)}")
        return None


def check_duration_difference(input_video_path, output_video_path):
    """检查输入视频和输出视频的时长差异"""
    try:
        # 获取输入视频时长
        input_duration = get_video_duration(input_video_path)
        if input_duration is None:
            logger.warning(f"无法获取输入视频时长: {input_video_path}")
            return False, 0
            
        # 获取输出视频时长
        output_duration = get_video_duration(output_video_path)
        if output_duration is None:
            logger.warning(f"无法获取输出视频时长: {output_video_path}")
            return False, 0
            
        # 计算时长差异
        duration_diff = abs(input_duration - output_duration)
        
        logger.info(f"视频时长比较:")
        logger.info(f"  输入视频: {input_duration:.2f}秒")
        logger.info(f"  输出视频: {output_duration:.2f}秒")
        logger.info(f"  时长差异: {duration_diff:.2f}秒")
        
        # 检查是否超过阈值
        if duration_diff > DURATION_DIFF_THRESHOLD:
            logger.warning(f"时长差异 {duration_diff:.2f}秒 超过阈值 {DURATION_DIFF_THRESHOLD}秒")
            return True, duration_diff
        else:
            logger.info(f"时长差异 {duration_diff:.2f}秒 在可接受范围内")
            return False, duration_diff
            
    except Exception as e:
        logger.error(f"检查时长差异时出错: {str(e)}")
        return False, 0


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


def check_nvidia_gpu():
    """检查系统是否有NVIDIA GPU可用，以及获取GPU内存信息"""
    if platform.system() != "Linux":
        return False, None

    try:
        # 检查nvidia-smi命令是否可用
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.total,memory.free",
                "--format=csv,noheader,nounits",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if result.returncode != 0:
            logger.warning("nvidia-smi命令不可用，无法使用NVIDIA GPU硬件加速")
            return False, None

        # 解析GPU内存信息
        lines = result.stdout.strip().split("\n")
        if not lines:
            return False, None

        # 获取第一个GPU的信息
        parts = lines[0].strip().split(",")
        if len(parts) >= 2:
            total_memory = int(parts[0].strip())
            free_memory = int(parts[1].strip())

            logger.info(
                f"检测到NVIDIA GPU，总内存: {total_memory}MB，可用内存: {free_memory}MB"
            )
            return True, {"total": total_memory, "free": free_memory}

        return False, None
    except Exception as e:
        logger.warning(f"检查NVIDIA GPU时出错: {str(e)}")
        return False, None


def add_subtitle_to_video(video_path, srt_path, output_path, language, use_gpu=False):
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

        # 基础ffmpeg命令
        cmd = ["ffmpeg"]

        # GPU加速相关变量
        hw_accel_used = False
        gpu_memory = None

        # 如果启用GPU，添加相应的硬件加速选项
        if use_gpu:
            system = platform.system()
            if system == "Linux":
                # 检查GPU是否可用
                has_gpu, memory_info = check_nvidia_gpu()
                if has_gpu:
                    gpu_memory = memory_info
                    # 使用CUDA硬件加速解码
                    cmd.extend(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])

                    # 根据GPU内存大小设置额外帧数
                    if (
                        memory_info and memory_info["free"] > 4000
                    ):  # 如果有超过4GB可用内存
                        cmd.extend(["-extra_hw_frames", "5"])
                    else:
                        cmd.extend(["-extra_hw_frames", "3"])

                    hw_accel_used = True
                    logger.info("已启用NVIDIA GPU硬件加速")
                else:
                    logger.warning("未检测到可用的NVIDIA GPU，将使用CPU处理")
                    # 如果GPU不可用，设置线程数以充分利用CPU
                    cpu_count = multiprocessing.cpu_count()
                    cmd.extend(["-threads", str(cpu_count)])
                    logger.info(f"设置CPU线程数为: {cpu_count}")
            elif system == "Darwin":  # macOS
                cmd.extend(["-hwaccel", "videotoolbox"])
                hw_accel_used = True
                logger.info("已启用macOS VideoToolbox硬件加速")

        # 添加输入文件
        cmd.extend(
            [
                "-i",
                video_path,
            ]
        )

        # 字幕滤镜设置
        if hw_accel_used and platform.system() == "Linux":
            # 对于GPU加速，需要在硬件和软件处理之间进行转换
            # 使用更高效的方式处理字幕，避免多次格式转换
            subtitle_filter = f"hwdownload,format=nv12,subtitles={srt_path}:fontsdir={fonts_dir}:force_style='Fontname={font_name},FontSize=16,FontWeight=500,PrimaryColour=&HFFFFFF,OutlineColour=&H383838,BorderStyle=1,Outline=0.6,MarginV=20',hwupload_cuda"

            # 添加额外的高效处理选项
            cmd.extend(
                [
                    "-rc-lookahead",
                    "20",  # 速率控制预测帧数
                    "-g",
                    "120",  # GOP大小，降低关键帧频率
                    "-strict",
                    "experimental",  # 允许使用实验性质的编码选项
                ]
            )
        else:
            subtitle_filter = f"subtitles={srt_path}:fontsdir={fonts_dir}:force_style='Fontname={font_name},FontSize=16,FontWeight=500,PrimaryColour=&HFFFFFF,OutlineColour=&H383838,BorderStyle=1,Outline=0.6,MarginV=20'"

        # 添加滤镜和音频复制设置
        cmd.extend(
            [
                "-vf",
                subtitle_filter,
                "-c:a",
                "copy",
                "-y",  # 覆盖已存在的文件
            ]
        )

        # 如果使用GPU，添加对应的视频编码器
        if hw_accel_used:
            system = platform.system()
            if system == "Linux":
                # 对于Linux，使用NVIDIA GPU硬件编码
                # 基础编码器设置
                encoder_params = ["-c:v", "h264_nvenc", "-preset", "p1"]

                if gpu_memory and gpu_memory["free"] > 5000:  # 如果有超过5GB可用内存
                    # 优化的设置，保持质量但减小文件大小
                    encoder_params.extend(
                        [
                            "-profile:v",
                            "high",
                            "-tune",
                            "hq",
                            "-b:v",
                            "2.5M",  # 更低的视频比特率
                            "-maxrate",
                            "128M",  # 降低最大比特率
                            "-bufsize",
                            "128M",  # 适当的缓冲区
                            "-rc",
                            "constqp",  # 使用恒定量化参数模式
                            "-qp",
                            "26",  # 量化参数 (较高=更小文件，较低=更高质量)
                            "-spatial_aq",
                            "1",
                            "-temporal_aq",
                            "1",
                            "-rc-lookahead",
                            "1000",
                        ]
                    )
                    logger.info("使用优化质量编码设置（平衡大小与质量）")
                else:
                    # 轻量级设置，适用于内存有限的情况
                    encoder_params.extend(
                        [
                            "-profile:v",
                            "main",
                            "-tune",
                            "ll",  # 低延迟模式
                            "-b:v",
                            "2M",
                            "-maxrate",
                            "3M",
                            "-bufsize",
                            "3M",
                            "-rc",
                            "constqp",
                            "-qp",
                            "26",
                            "-spatial_aq",
                            "1",
                            "-rc-lookahead",
                            "10",
                        ]
                    )
                    logger.info("使用轻量级编码设置（优化文件大小）")

                cmd.extend(encoder_params)
            elif system == "Darwin":  # macOS
                # 对于macOS，使用VideoToolbox硬件编码，优化大小
                cmd.extend(
                    [
                        "-c:v",
                        "h264_videotoolbox",
                        "-b:v",
                        "2.5M",  # 降低比特率
                        "-maxrate",
                        "3.5M",
                        "-q:v",
                        "75",  # 增加q值以减小文件大小 (VideoToolbox的q值范围为1-100)
                        "-allow_sw",
                        "1",  # 允许软件回退
                        "-profile:v",
                        "main",  # 使用main配置文件
                        "-pix_fmt",
                        "yuv420p",  # 使用更高效的像素格式
                    ]
                )
                logger.info("使用macOS VideoToolbox硬件加速（优化文件大小）")

        # 添加输出文件路径
        cmd.append(output_path)

        # 执行ffmpeg命令
        logger.info(f"正在处理视频: {os.path.basename(video_path)}")
        logger.info(f"使用字幕: {os.path.basename(srt_path)}")
        logger.info(f"使用字体: {font_name}")
        logger.info(f"FFmpeg命令: {' '.join(cmd)}")

        process = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        if process.returncode == 0:
            logger.info(f"成功生成带字幕的视频: {output_path}")
            return True
        else:
            logger.error(f"添加字幕失败: {process.stderr}")
            # 如果使用GPU加速失败，尝试回退到CPU模式
            if use_gpu:
                logger.warning("GPU加速失败，尝试使用CPU模式重新处理...")
                return add_subtitle_to_video(
                    video_path, srt_path, output_path, language, False
                )
            return False

    except Exception as e:
        logger.error(f"添加字幕时出错: {str(e)}")
        return False


def add_subtitle_to_video_simple(video_path, srt_path, output_path, language):
    """为视频添加字幕的简化版本（专用于修复损坏文件）"""
    try:
        # 创建输出目录
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 使用系统字体进行简单渲染
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", f"subtitles={srt_path}:force_style='FontSize=16,FontWeight=500,PrimaryColour=&Hffffff,OutlineColour=&H000000,BorderStyle=1,Outline=1,MarginV=20'",
            "-c:a", "copy",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-y",
            output_path
        ]
        
        logger.info(f"执行简化字幕添加命令: {' '.join(cmd)}")
        
        # 执行命令
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info(f"成功为视频添加字幕: {os.path.basename(output_path)}")
            return True
        else:
            logger.error(f"添加字幕失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"添加字幕超时: {video_path}")
        return False
    except Exception as e:
        logger.error(f"添加字幕时出错: {str(e)}")
        return False


def process_video(channel, video_name, language, force=False, use_gpu=False):
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

    # 检查输出文件是否已存在
    if os.path.exists(output_video_path) and not force:
        # 如果输出文件存在，检查时长差异
        logger.info(f"输出文件已存在，检查时长差异: {output_video_path}")
        
        needs_regeneration, duration_diff = check_duration_difference(
            input_video_path, output_video_path
        )
        
        if needs_regeneration:
            logger.warning(f"检测到时长差异过大 ({duration_diff:.2f}秒)，删除输出文件并重新生成")
            try:
                os.remove(output_video_path)
                logger.info(f"已删除输出文件: {output_video_path}")
            except Exception as e:
                logger.error(f"删除输出文件失败: {str(e)}")
                return False
        else:
            logger.info(f"时长差异在可接受范围内，跳过处理")
            return True

    # 为视频添加字幕
    success = add_subtitle_to_video(
        input_video_path, input_srt_path, output_video_path, language, use_gpu
    )
    
    # 如果成功生成，再次检查时长差异
    if success and os.path.exists(output_video_path):
        logger.info("字幕添加完成，进行时长验证...")
        
        needs_regeneration, duration_diff = check_duration_difference(
            input_video_path, output_video_path
        )
        
        if needs_regeneration:
            logger.error(f"生成的视频时长差异过大 ({duration_diff:.2f}秒)，尝试使用简化模式重新生成")
            
            # 删除有问题的输出文件
            try:
                os.remove(output_video_path)
                logger.info(f"已删除有问题的输出文件: {output_video_path}")
            except Exception as e:
                logger.error(f"删除输出文件失败: {str(e)}")
                return False
            
            # 使用简化模式重新生成
            logger.info("使用简化模式重新生成视频...")
            success = add_subtitle_to_video_simple(
                input_video_path, input_srt_path, output_video_path, language
            )
            
            # 再次检查简化模式生成的视频
            if success and os.path.exists(output_video_path):
                needs_regeneration_2, duration_diff_2 = check_duration_difference(
                    input_video_path, output_video_path
                )
                
                if needs_regeneration_2:
                    logger.error(f"简化模式生成的视频时长差异仍然过大 ({duration_diff_2:.2f}秒)")
                    return False
                else:
                    logger.info("简化模式生成的视频时长验证通过")
                    return True
            else:
                logger.error("简化模式重新生成失败")
                return False
        else:
            logger.info("生成的视频时长验证通过")
            return True
    
    return success


def process_all_videos(languages=None, force=False, use_gpu=False):
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
        if os.path.isdir(os.path.join(INPUT_MP4_PATH, d)) and not d.startswith(".")
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
            if os.path.isdir(os.path.join(channel_path, d))
            and d in languages
            and not d.startswith(".")
        ]

        if not lang_dirs:
            logger.warning(f"在频道 {channel} 中未找到任何支持的语言目录")
            continue

        # 处理每种语言
        for lang in lang_dirs:
            lang_path = os.path.join(channel_path, lang)

            # 获取该语言下的所有MP4文件，过滤掉点开头的文件
            video_files = [
                f
                for f in glob.glob(os.path.join(lang_path, "*.mp4"))
                if not os.path.basename(f).startswith(".")
            ]

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
            if process_video(channel, video_name, language, force, use_gpu):
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
    parser.add_argument("--gpu", action="store_true", help="使用GPU加速ffmpeg处理")

    # 解析命令行参数
    args = parser.parse_args()

    # 处理单个视频模式
    if args.single:
        if "/" not in args.single:
            logger.error("错误: 单个视频参数格式应为 '频道名/视频名'")
            return

        channel, video_name = args.single.split("/", 1)

        logger.info(f"处理单个视频: {channel}/{video_name}")
        if args.gpu:
            logger.info("已启用GPU加速")

        success_count = 0
        for language in args.languages:
            if process_video(channel, video_name, language, args.force, args.gpu):
                success_count += 1

        logger.info(
            f"处理完成，成功生成 {success_count}/{len(args.languages)} 个语言版本"
        )
    else:
        # 处理所有频道和视频
        start_time = time.time()
        if args.gpu:
            logger.info("已启用GPU加速")
        process_all_videos(args.languages, args.force, args.gpu)
        end_time = time.time()
        logger.info(f"所有处理完成，总耗时: {end_time - start_time:.2f}秒")


if __name__ == "__main__":
    main()
