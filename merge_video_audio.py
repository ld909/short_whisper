#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
这个脚本用于合并无声视频和音频文件，生成完整的多语言视频。
从merge_mp4_clips_by_audio_duration.py输出目录获取无声视频文件，
从merge_mp3.py输出目录获取对应的音频文件，
使用ffmpeg将它们合成，并输出到指定目录。

使用方法：通过命令行参数指定频道、语言或特定视频文件进行处理。
"""

import os
import argparse
import subprocess
import glob
import platform
import time
import threading
import sys
import termios
import fcntl
import queue


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
MP4_INPUT_DIR = f"{BASE_PATH}/mp4_merged"
MP3_INPUT_DIR = f"{BASE_PATH}/merge_multi_lange_mp3"
OUTPUT_DIR = f"{BASE_PATH}/full_video_multi_lang"

# 退出控制
exit_flag = False
exit_queue = queue.Queue()
processing_lock = threading.Lock()


def merge_video_audio(video_file, audio_file, output_file):
    """使用ffmpeg合并视频和音频"""
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)

        # 检查输入文件是否存在
        if not os.path.exists(video_file):
            print(f"错误: 视频文件不存在 {video_file}")
            return False
        if not os.path.exists(audio_file):
            print(f"错误: 音频文件不存在 {audio_file}")
            return False

        # 检查输出文件是否已存在
        if os.path.exists(output_file):
            # 动态检查文件有效性
            try:
                cmd = [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    output_file,
                ]
                duration = float(subprocess.check_output(cmd).decode().strip())

                # 获取音频文件时长作为参考
                audio_cmd = [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    audio_file,
                ]
                audio_duration = float(
                    subprocess.check_output(audio_cmd).decode().strip()
                )

                print(
                    f"已存在文件时长: {duration:.2f}秒, 音频文件时长: {audio_duration:.2f}秒"
                )

                # 检查文件是否完整（时长应接近音频时长）
                if duration > 0 and abs(duration - audio_duration) < 2.0:
                    print(
                        f"文件 {os.path.basename(output_file)} 已存在且有效，跳过处理"
                    )
                    return True
                else:
                    print(f"已存在文件无效或不完整，将重新生成")
                    os.remove(output_file)
            except Exception as e:
                print(f"检查已存在文件时出错: {e}，将重新生成")
                try:
                    os.remove(output_file)
                except:
                    pass

        # 使用ffmpeg合并视频和音频
        cmd = [
            "ffmpeg",
            "-v",
            "warning",  # 只显示警告和错误
            "-i",
            video_file,  # 视频输入
            "-i",
            audio_file,  # 音频输入
            "-c:v",
            "copy",  # 复制视频流
            "-c:a",
            "aac",  # 使用AAC编码音频
            "-b:a",
            "128k",  # 音频比特率
            "-map",
            "0:v",  # 使用第一个输入文件的视频
            "-map",
            "1:a",  # 使用第二个输入文件的音频
            "-shortest",  # 以最短的输入为准
            "-y",  # 覆盖已有文件
            output_file,
        ]

        print(f"执行合并命令: {' '.join(cmd)}")
        start_time = time.time()

        # 执行ffmpeg命令
        subprocess.run(cmd, check=True)

        # 计算耗时
        end_time = time.time()
        print(f"合并完成，耗时: {end_time - start_time:.2f}秒")

        # 检查输出文件
        if os.path.exists(output_file):
            filesize = os.path.getsize(output_file) / (1024 * 1024)  # MB
            print(f"输出文件: {output_file}")
            print(f"文件大小: {filesize:.2f} MB")

            # 获取视频时长
            duration_cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                output_file,
            ]
            duration = subprocess.check_output(duration_cmd).decode().strip()
            print(f"合并后视频时长: {float(duration):.2f}秒")

            return True
        else:
            print(f"错误: 未能找到输出文件 {output_file}")
            return False
    except Exception as e:
        print(f"合并视频和音频时出错: {e}")
        return False


def process_file(video_file, channel, language):
    """处理单个视频文件"""
    with processing_lock:
        # 从视频文件路径中提取基础文件名
        video_basename = os.path.basename(video_file)
        video_name = os.path.splitext(video_basename)[0]

        print(f"处理文件: {video_basename}")
        print(f"频道: {channel}, 语言: {language}")

        # 构建对应的音频文件路径
        audio_file = os.path.join(MP3_INPUT_DIR, channel, language, f"{video_name}.mp3")
        if not os.path.exists(audio_file):
            print(f"错误: 未找到对应的音频文件 {audio_file}")
            return False

        # 构建输出文件路径
        output_file = os.path.join(OUTPUT_DIR, channel, language, f"{video_name}.mp4")

        # 合并视频和音频
        return merge_video_audio(video_file, audio_file, output_file)


def process_channel_videos(channel_name, specific_language=None, specific_file=None):
    """处理指定频道下的视频文件"""
    channel_dir = os.path.join(MP4_INPUT_DIR, channel_name)
    if not os.path.exists(channel_dir):
        print(f"错误: 频道目录不存在 {channel_dir}")
        return

    # 获取所有语言目录或指定语言
    if specific_language:
        language_dirs = (
            [specific_language]
            if os.path.isdir(os.path.join(channel_dir, specific_language))
            else []
        )
        if not language_dirs:
            print(
                f"错误: 语言目录不存在 {os.path.join(channel_dir, specific_language)}"
            )
            return
    else:
        language_dirs = [
            d
            for d in os.listdir(channel_dir)
            if os.path.isdir(os.path.join(channel_dir, d))
        ]

    total_languages = len(language_dirs)
    for lang_idx, language in enumerate(language_dirs, 1):
        # 检查是否应该退出
        if exit_flag:
            print(f"接收到退出信号，停止处理新文件")
            return

        lang_dir = os.path.join(channel_dir, language)
        print(
            f"\n处理频道 {channel_name} 的语言 {language} ({lang_idx}/{total_languages})"
        )

        if specific_file:
            # 处理特定文件
            video_file = os.path.join(lang_dir, specific_file)
            if os.path.exists(video_file):
                process_file(video_file, channel_name, language)
            else:
                print(f"错误: 指定的视频文件不存在 {video_file}")
        else:
            # 处理目录下所有mp4文件
            video_files = glob.glob(os.path.join(lang_dir, "*.mp4"))
            total_files = len(video_files)
            print(f"找到 {total_files} 个视频文件需要处理")

            for file_idx, video_file in enumerate(video_files, 1):
                # 检查是否应该退出
                if exit_flag:
                    print(f"接收到退出信号，停止处理新文件")
                    return

                # 显示进度
                video_basename = os.path.basename(video_file)
                print(f"\n[{file_idx}/{total_files}] 处理: {video_basename}")

                process_file(video_file, channel_name, language)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="合并视频和音频文件")
    parser.add_argument("-c", "--channel", help="指定要处理的频道名")
    parser.add_argument("-l", "--language", help="指定要处理的语言")
    parser.add_argument("-f", "--file", help="指定要处理的视频文件名")
    parser.add_argument("--list-channels", action="store_true", help="列出所有可用频道")
    parser.add_argument(
        "--list-languages", metavar="CHANNEL", help="列出指定频道的所有可用语言"
    )
    parser.add_argument("--base-path", help="指定自定义的基础路径，覆盖默认路径")
    return parser.parse_args()


def list_channels():
    """列出所有可用频道"""
    if not os.path.exists(MP4_INPUT_DIR):
        print(f"错误: 视频基础目录不存在 {MP4_INPUT_DIR}")
        return

    channel_dirs = [
        d
        for d in os.listdir(MP4_INPUT_DIR)
        if os.path.isdir(os.path.join(MP4_INPUT_DIR, d))
    ]
    if not channel_dirs:
        print("未找到任何频道目录")
        return

    print("可用频道列表:")
    for channel in channel_dirs:
        print(f"- {channel}")


def list_languages(channel_name):
    """列出指定频道的所有可用语言"""
    channel_dir = os.path.join(MP4_INPUT_DIR, channel_name)
    if not os.path.exists(channel_dir):
        print(f"错误: 频道目录不存在 {channel_dir}")
        return

    language_dirs = [
        d
        for d in os.listdir(channel_dir)
        if os.path.isdir(os.path.join(channel_dir, d))
    ]
    if not language_dirs:
        print(f"未在频道 {channel_name} 中找到任何语言目录")
        return

    print(f"频道 {channel_name} 的可用语言列表:")
    for language in language_dirs:
        print(f"- {language}")


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


def main():
    """主函数"""
    args = parse_args()

    # 如果用户指定了自定义基础路径，则覆盖默认路径
    global MP4_INPUT_DIR, MP3_INPUT_DIR, OUTPUT_DIR
    if args.base_path:
        custom_base_path = args.base_path
        MP4_INPUT_DIR = f"{custom_base_path}/mp4_merged"
        MP3_INPUT_DIR = f"{custom_base_path}/merge_multi_lange_mp3"
        OUTPUT_DIR = f"{custom_base_path}/full_video_multi_lang"
        print(f"使用自定义基础路径: {custom_base_path}")
    else:
        # 打印系统信息和基础路径
        print(f"检测到系统: {platform.system()}")
        print(f"使用基础路径: {BASE_PATH}")

    # 确保输出根目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 80)
    print("视频音频合成工具")
    print("=" * 80)
    print("功能：合并无声视频和音频文件，生成完整的多语言视频")
    print("支持断点续传：已处理过的有效文件会自动跳过")
    print("按3次q键可以退出程序（会等待当前视频处理完成）")
    print("=" * 80)

    # 启动键盘监听线程
    key_thread = threading.Thread(target=read_key, daemon=True)
    key_thread.start()

    # 启动按键监控线程
    monitor_thread = threading.Thread(target=key_monitor, daemon=True)
    monitor_thread.start()

    start_time = time.time()

    # 处理列表命令
    if args.list_channels:
        list_channels()
        return

    if args.list_languages:
        list_languages(args.list_languages)
        return

    # 处理指定频道或所有频道
    if args.channel:
        print(f"\n开始处理频道: {args.channel}")
        process_channel_videos(args.channel, args.language, args.file)
    else:
        # 获取所有频道目录
        channel_dirs = [
            d
            for d in os.listdir(MP4_INPUT_DIR)
            if os.path.isdir(os.path.join(MP4_INPUT_DIR, d))
        ]

        if not channel_dirs:
            print(f"错误: 未找到任何频道目录在 {MP4_INPUT_DIR}")
            return

        print(f"找到 {len(channel_dirs)} 个频道: {', '.join(channel_dirs)}")

        # 处理每个频道
        for channel_idx, channel_name in enumerate(channel_dirs, 1):
            # 检查是否应该退出
            if exit_flag:
                break

            print(f"\n开始处理频道: {channel_name} ({channel_idx}/{len(channel_dirs)})")
            process_channel_videos(channel_name)

    # 等待可能存在的视频处理完成
    if exit_flag:
        print("正在等待当前视频处理完成...")

    # 等待线程结束
    if key_thread.is_alive():
        key_thread.join(1)
    if monitor_thread.is_alive():
        monitor_thread.join(1)

    end_time = time.time()
    total_minutes = (end_time - start_time) / 60
    print(
        f"\n所有处理完成！总耗时: {int(total_minutes)}分钟{int((total_minutes % 1) * 60)}秒"
    )


if __name__ == "__main__":
    main()
