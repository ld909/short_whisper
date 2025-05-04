#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
合并MP4和MP3文件脚本
-----------------
这个脚本用于将带字幕的MP4视频和MP3音频合并成完整的视频文件。

输入目录:
- MP4文件目录: /Volumes/dhl/buda_videos_youtube/mp4_multi_with_subtitles/频道名/语言/
- MP3文件目录: /Volumes/dhl/buda_videos_youtube/merge_multi_lange_mp3/频道名/语言/

输出目录:
- 合并后的视频: /Volumes/dhl/buda_videos_youtube/mp4_with_audio/频道名/语言/

注: 在Linux系统上，基础路径为/media/dhl/buda_videos_youtube

命令行参数:
  -c, --channel     指定要处理的频道名
  -l, --language    指定要处理的语言
  -f, --file        指定要处理的文件名
  --list-channels   列出所有可用频道
  --list-languages  列出指定频道的所有可用语言
  --force           强制重新生成已存在的文件
  --base-path       指定自定义的基础路径，覆盖默认路径

示例:
  # 列出所有频道
  python merge_mp4_mp3.py --list-channels

  # 列出频道'buddha'的所有语言
  python merge_mp4_mp3.py --list-languages buddha

  # 处理频道'buddha'下语言'chinese'的所有文件
  python merge_mp4_mp3.py -c buddha -l chinese

  # 处理频道'buddha'下语言'chinese'中的特定文件
  python merge_mp4_mp3.py -c buddha -l chinese -f video_name

  # 强制重新生成已存在的文件
  python merge_mp4_mp3.py -c buddha -l chinese --force

  # 使用自定义基础路径
  python merge_mp4_mp3.py --base-path /path/to/custom/base
"""

import os
import time
import subprocess
import glob
import argparse
import threading
import sys
import termios
import fcntl
import queue
import platform
from pathlib import Path


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
MP4_BASE_DIR = f"{BASE_PATH}/mp4_multi_with_subtitles"
MP3_BASE_DIR = f"{BASE_PATH}/merge_multi_lange_mp3"
OUTPUT_BASE_DIR = f"{BASE_PATH}/mp4_with_audio"

# 退出控制
exit_flag = False
exit_queue = queue.Queue()
processing_lock = threading.Lock()


def get_duration(file_path):
    """获取媒体文件的时长(秒)"""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            file_path,
        ]
        duration = float(subprocess.check_output(cmd).decode().strip())
        return duration
    except Exception as e:
        print(f"获取媒体时长出错: {e}")
        return 0


def merge_mp4_mp3(mp4_file, mp3_file, output_file, force=False):
    """合并MP4和MP3文件"""
    # 检查输出目录是否存在，不存在则创建
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # 如果文件已存在且不强制重写，则跳过
    if os.path.exists(output_file) and not force:
        print(f"输出文件已存在，跳过: {os.path.basename(output_file)}")
        return True

    # 检查输入文件是否存在
    if not os.path.exists(mp4_file):
        print(f"错误: MP4文件不存在 {os.path.basename(mp4_file)}")
        return False

    if not os.path.exists(mp3_file):
        print(f"错误: MP3文件不存在 {os.path.basename(mp3_file)}")
        return False

    # 获取MP4和MP3的时长
    mp4_duration = get_duration(mp4_file)
    mp3_duration = get_duration(mp3_file)

    if mp4_duration <= 0 or mp3_duration <= 0:
        print(f"错误: 无法获取媒体文件时长")
        return False

    # 检查时长是否匹配
    duration_diff = abs(mp4_duration - mp3_duration)
    if duration_diff > 1.0:  # 允许1秒的误差
        print(
            f"警告: MP4时长({mp4_duration:.2f}秒)与MP3时长({mp3_duration:.2f}秒)相差{duration_diff:.2f}秒"
        )

    # 使用ffmpeg合并MP4和MP3
    try:
        cmd = [
            "ffmpeg",
            "-v",
            "warning",  # 显示警告和错误
            "-i",
            mp4_file,  # 视频输入
            "-i",
            mp3_file,  # 音频输入
            "-map",
            "0:v",  # 使用第一个输入的视频流
            "-map",
            "1:a",  # 使用第二个输入的音频流
            "-c:v",
            "copy",  # 复制视频流
            "-c:a",
            "aac",  # 转换音频为AAC (兼容性更好)
            "-shortest",  # 使用最短的输入流长度
            "-y",  # 覆盖已有文件
            output_file,
        ]
        # 只打印简化版命令，避免文件路径过长
        print(f"执行合并命令: ffmpeg [输入视频] [输入音频] -> [输出文件]")

        # 执行ffmpeg命令
        start_time = time.time()
        subprocess.run(cmd, check=True)
        end_time = time.time()

        # 检查输出文件
        if os.path.exists(output_file):
            filesize = os.path.getsize(output_file) / (1024 * 1024)  # MB
            output_duration = get_duration(output_file)
            print(f"合并完成: {os.path.basename(output_file)}")
            print(f"文件大小: {filesize:.2f} MB")
            print(f"输出时长: {output_duration:.2f} 秒")
            print(f"处理耗时: {end_time - start_time:.2f} 秒")
            return True
        else:
            print(f"错误: 输出文件不存在 {os.path.basename(output_file)}")
            return False
    except Exception as e:
        print(f"合并出错: {e}")
        return False


def process_file(channel, language, file_name, force=False):
    """处理单个文件的合并"""
    # 获取处理锁，表示正在处理文件
    with processing_lock:
        if exit_flag:
            print("接收到退出信号，跳过处理")
            return False

        # 构建MP4和MP3文件路径
        mp4_file = os.path.join(MP4_BASE_DIR, channel, language, f"{file_name}.mp4")
        mp3_file = os.path.join(MP3_BASE_DIR, channel, language, f"{file_name}.mp3")

        # 检查文件是否存在
        if not os.path.exists(mp4_file):
            print(f"错误: MP4文件不存在 {mp4_file}")
            return False

        if not os.path.exists(mp3_file):
            print(f"错误: MP3文件不存在 {mp3_file}")
            return False

        # 构建输出文件路径
        output_file = os.path.join(
            OUTPUT_BASE_DIR, channel, language, f"{file_name}.mp4"
        )

        # 为避免打印过长的文件名导致阻塞，限制打印长度
        max_path_length = 100
        print(f"\n处理文件: {file_name[:100]}{'...' if len(file_name) > 100 else ''}")

        mp4_display = mp4_file
        if len(mp4_display) > max_path_length:
            mp4_display = mp4_display[:max_path_length] + "..."
        print(f"MP4源文件: {mp4_display}")

        mp3_display = mp3_file
        if len(mp3_display) > max_path_length:
            mp3_display = mp3_display[:max_path_length] + "..."
        print(f"MP3源文件: {mp3_display}")

        output_display = output_file
        if len(output_display) > max_path_length:
            output_display = output_display[:max_path_length] + "..."
        print(f"输出文件: {output_display}")

        # 合并文件
        return merge_mp4_mp3(mp4_file, mp3_file, output_file, force)


def process_channel_language(channel, language=None, specific_file=None, force=False):
    """处理指定频道和语言的所有文件"""
    channel_dir = os.path.join(MP4_BASE_DIR, channel)
    if not os.path.exists(channel_dir):
        print(f"错误: 频道目录不存在 {channel_dir}")
        return

    # 获取语言目录
    if language:
        language_dirs = (
            [language] if os.path.isdir(os.path.join(channel_dir, language)) else []
        )
        if not language_dirs:
            print(f"错误: 语言目录不存在 {os.path.join(channel_dir, language)}")
            return
    else:
        language_dirs = [
            d
            for d in os.listdir(channel_dir)
            if os.path.isdir(os.path.join(channel_dir, d))
        ]

    for lang in language_dirs:
        if exit_flag:
            print(f"接收到退出信号，停止处理新文件")
            return

        lang_dir = os.path.join(channel_dir, lang)

        # 确保MP3语言目录存在
        mp3_lang_dir = os.path.join(MP3_BASE_DIR, channel, lang)
        if not os.path.exists(mp3_lang_dir):
            print(f"警告: MP3语言目录不存在 {mp3_lang_dir}，跳过")
            continue

        if specific_file:
            # 处理特定文件
            file_base = (
                specific_file.rsplit(".", 1)[0]
                if "." in specific_file
                else specific_file
            )
            process_file(channel, lang, file_base, force)
        else:
            # 处理所有匹配的文件
            mp4_files = glob.glob(os.path.join(lang_dir, "*.mp4"))
            for mp4_file in mp4_files:
                if exit_flag:
                    print(f"接收到退出信号，停止处理新文件")
                    return

                file_base = os.path.basename(mp4_file).rsplit(".", 1)[0]
                mp3_file = os.path.join(mp3_lang_dir, f"{file_base}.mp3")

                # 检查对应的MP3文件是否存在
                if not os.path.exists(mp3_file):
                    # 仅打印文件名，避免完整路径导致阻塞
                    print(
                        f"警告: 找不到对应的MP3文件 {os.path.basename(mp3_file)}，跳过"
                    )
                    continue

                process_file(channel, lang, file_base, force)


def read_key():
    """非阻塞读取键盘输入"""
    try:
        fd = sys.stdin.fileno()
        oldterm = termios.tcgetattr(fd)
        newattr = termios.tcgetattr(fd)
        newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, newattr)

        oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

        try:
            while True:
                try:
                    c = sys.stdin.read(1)
                    if c:
                        exit_queue.put(c)
                except IOError:
                    pass

                # 检查是否应该退出
                if exit_flag:
                    break

                time.sleep(0.1)
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
            fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)
    except Exception as e:
        print(f"键盘监听错误: {e}")


def key_monitor():
    """监控按键并检测三个连续的q退出"""
    q_count = 0
    last_q_time = 0

    print("按3次q键可以退出程序（会等待当前视频处理完成）")

    while True:
        try:
            key = exit_queue.get(timeout=1.0)

            if key == "q":
                current_time = time.time()
                # 如果距离上次按q超过2秒，重置计数
                if current_time - last_q_time > 2.0:
                    q_count = 1
                else:
                    q_count += 1

                last_q_time = current_time

                if q_count == 1:
                    print(f"检测到按键q，再按2次退出 (1/3)")
                elif q_count == 2:
                    print(f"检测到按键q，再按1次退出 (2/3)")
                elif q_count >= 3:
                    print(f"检测到连续按键q三次，程序将在当前视频处理完成后退出")
                    global exit_flag
                    exit_flag = True
                    break
            else:
                # 如果按了其他键，重置计数
                q_count = 0

        except queue.Empty:
            # 队列为空，继续循环
            pass

        # 检查是否应该退出
        if exit_flag:
            break


def list_channels():
    """列出所有可用频道"""
    # 检查MP4和MP3基础目录是否存在
    if not os.path.exists(MP4_BASE_DIR):
        print(f"错误: MP4基础目录不存在 {MP4_BASE_DIR}")
        return []

    if not os.path.exists(MP3_BASE_DIR):
        print(f"错误: MP3基础目录不存在 {MP3_BASE_DIR}")
        return []

    # 获取两个目录中的交集频道
    mp4_channels = set(
        [
            d
            for d in os.listdir(MP4_BASE_DIR)
            if os.path.isdir(os.path.join(MP4_BASE_DIR, d))
        ]
    )
    mp3_channels = set(
        [
            d
            for d in os.listdir(MP3_BASE_DIR)
            if os.path.isdir(os.path.join(MP3_BASE_DIR, d))
        ]
    )

    common_channels = mp4_channels.intersection(mp3_channels)

    if not common_channels:
        print("未找到任何共同的频道目录")
        return []

    print("可用频道列表:")
    for channel in sorted(common_channels):
        print(f"- {channel}")

    return sorted(common_channels)


def list_languages(channel_name):
    """列出指定频道的所有可用语言"""
    # 检查频道目录是否存在
    mp4_channel_dir = os.path.join(MP4_BASE_DIR, channel_name)
    mp3_channel_dir = os.path.join(MP3_BASE_DIR, channel_name)

    if not os.path.exists(mp4_channel_dir):
        print(f"错误: MP4频道目录不存在 {mp4_channel_dir}")
        return []

    if not os.path.exists(mp3_channel_dir):
        print(f"错误: MP3频道目录不存在 {mp3_channel_dir}")
        return []

    # 获取两个目录中的交集语言
    mp4_languages = set(
        [
            d
            for d in os.listdir(mp4_channel_dir)
            if os.path.isdir(os.path.join(mp4_channel_dir, d))
        ]
    )
    mp3_languages = set(
        [
            d
            for d in os.listdir(mp3_channel_dir)
            if os.path.isdir(os.path.join(mp3_channel_dir, d))
        ]
    )

    common_languages = mp4_languages.intersection(mp3_languages)

    if not common_languages:
        print(f"未在频道 {channel_name} 中找到任何共同的语言目录")
        return []

    print(f"频道 {channel_name} 的可用语言列表:")
    for language in sorted(common_languages):
        print(f"- {language}")

    return sorted(common_languages)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="合并MP4和MP3文件")
    parser.add_argument("-c", "--channel", help="指定要处理的频道名")
    parser.add_argument("-l", "--language", help="指定要处理的语言")
    parser.add_argument("-f", "--file", help="指定要处理的文件名")
    parser.add_argument("--list-channels", action="store_true", help="列出所有可用频道")
    parser.add_argument(
        "--list-languages", metavar="CHANNEL", help="列出指定频道的所有可用语言"
    )
    parser.add_argument("--force", action="store_true", help="强制重新生成已存在的文件")
    parser.add_argument("--base-path", help="指定自定义的基础路径，覆盖默认路径")
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    # 如果用户指定了自定义基础路径，则覆盖默认路径
    global MP4_BASE_DIR, MP3_BASE_DIR, OUTPUT_BASE_DIR
    if args.base_path:
        custom_base_path = args.base_path
        MP4_BASE_DIR = f"{custom_base_path}/mp4_multi_with_subtitles"
        MP3_BASE_DIR = f"{custom_base_path}/merge_multi_lange_mp3"
        OUTPUT_BASE_DIR = f"{custom_base_path}/mp4_with_audio"
        print(f"使用自定义基础路径: {custom_base_path}")
    else:
        # 打印系统信息和基础路径
        print(f"检测到系统: {platform.system()}")
        print(f"使用基础路径: {BASE_PATH}")

    # 确保输出根目录存在
    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)

    # 处理列表命令
    if args.list_channels:
        list_channels()
        return

    if args.list_languages:
        list_languages(args.list_languages)
        return

    # 启动键盘监听线程
    key_thread = threading.Thread(target=read_key, daemon=True)
    key_thread.start()

    # 启动按键监控线程
    monitor_thread = threading.Thread(target=key_monitor, daemon=True)
    monitor_thread.start()

    # 处理指定频道或所有频道
    if args.channel:
        print(f"\n开始处理频道: {args.channel}")
        process_channel_language(args.channel, args.language, args.file, args.force)
    else:
        # 获取所有频道
        channels = list_channels()

        if not channels:
            print("没有可用的频道，退出")
            return

        # 处理每个频道
        for channel in channels:
            # 检查是否应该退出
            if exit_flag:
                break

            print(f"\n开始处理频道: {channel}")
            process_channel_language(channel, args.language, args.file, args.force)

    # 等待可能存在的视频处理完成
    if exit_flag:
        print("正在等待当前视频处理完成...")

    # 等待线程结束
    if key_thread.is_alive():
        key_thread.join(1)
    if monitor_thread.is_alive():
        monitor_thread.join(1)

    print("\n所有处理完成！")


if __name__ == "__main__":
    main()
