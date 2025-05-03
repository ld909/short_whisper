#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
使用说明
--------
这个脚本用于根据多语言音频文件的时长，自动从视频片段库中随机选取并合并MP4片段，
然后裁剪生成与音频时长相匹配的无声视频文件。主要用于批量处理不同频道和语言的
音频文件，生成可用于后续视频制作的素材。

输入目录:
- 音频文件目录: /Volumes/dhl/buda_videos_youtube/merge_multi_lange_mp3/频道名/语言/
- 视频片段目录: /Volumes/dhl/buda_videos_youtube/mp4_clips/

输出目录:
- 合并视频目录: /Volumes/dhl/buda_videos_youtube/mp4_merge_silient/频道名/语言/

注: 在Linux系统上，基础路径为/media/dhl/buda_videos_youtube

命令行参数:
  -c, --channel     指定要处理的频道名
  -l, --language    指定要处理的语言
  -f, --file        指定要处理的音频文件名
  --list-channels   列出所有可用频道
  --list-languages  列出指定频道的所有可用语言
  --base-path       指定自定义的基础路径，覆盖默认路径

示例:
  # 列出所有频道
  python merge_mp4_clips_by_audio_duration.py --list-channels

  # 列出频道'buddha'的所有语言
  python merge_mp4_clips_by_audio_duration.py --list-languages buddha

  # 处理频道'buddha'下语言'chinese'的所有音频文件
  python merge_mp4_clips_by_audio_duration.py -c buddha -l chinese

  # 处理频道'buddha'下语言'chinese'中的特定音频文件
  python merge_mp4_clips_by_audio_duration.py -c buddha -l chinese -f audio_file.mp3

  # 使用自定义基础路径
  python merge_mp4_clips_by_audio_duration.py --base-path /path/to/custom/base
"""

import os
import time
import subprocess
import glob
import random
import json
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
MP3_BASE_DIR = f"{BASE_PATH}/merge_multi_lange_mp3"
MP4_CLIPS_DIR = f"{BASE_PATH}/mp4_clips"
OUTPUT_BASE_DIR = f"{BASE_PATH}/mp4_merge_silient"

# 每个视频片段的时长(秒)
CLIP_DURATION = 8

# 退出控制
exit_flag = False
exit_queue = queue.Queue()
processing_lock = threading.Lock()


def get_audio_duration(audio_file):
    """获取音频文件的时长(秒)"""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            audio_file,
        ]
        duration = float(subprocess.check_output(cmd).decode().strip())
        return duration
    except Exception as e:
        print(f"获取音频时长出错: {e}")
        return 0


def create_concat_file(clip_files, concat_file_path):
    """创建ffmpeg合并列表文件"""
    with open(concat_file_path, "w") as f:
        for clip_file in clip_files:
            # 使用file协议和转义路径
            f.write(f"file '{clip_file.replace('\'', '\\\'')}'\n")
    return concat_file_path


def merge_with_ffmpeg_concat(clip_files, output_path):
    """使用ffmpeg的concat demuxer合并视频"""
    # 创建临时合并文件列表
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    concat_file = os.path.join(output_dir, "concat_list.txt")
    create_concat_file(clip_files, concat_file)

    # 使用ffmpeg合并
    try:
        start_time = time.time()
        cmd = [
            "ffmpeg",
            "-v",
            "warning",  # 只显示警告和错误
            "-f",
            "concat",
            "-safe",
            "0",  # 允许不安全的文件路径
            "-i",
            concat_file,
            "-c",
            "copy",  # 复制流而不重新编码，速度最快
            "-y",  # 覆盖已有文件
            output_path,
        ]
        print(f"执行合并命令: {' '.join(cmd)}")

        # 执行ffmpeg命令
        subprocess.run(cmd, check=True)

        # 计算耗时
        end_time = time.time()
        print(f"使用ffmpeg concat合并完成，耗时: {end_time - start_time:.2f}秒")

        # 检查输出文件
        if os.path.exists(output_path):
            filesize = os.path.getsize(output_path) / (1024 * 1024)  # MB
            print(f"输出文件: {output_path}")
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
                output_path,
            ]
            duration = subprocess.check_output(duration_cmd).decode().strip()
            print(f"合并视频时长: {float(duration):.2f}秒")

            return True
        else:
            print(f"错误: 未能找到输出文件 {output_path}")
            return False
    except Exception as e:
        print(f"合并视频时出错: {e}")
        return False
    finally:
        # 删除临时concat文件
        if os.path.exists(concat_file):
            os.remove(concat_file)


def trim_video(input_path, output_path, target_duration):
    """裁剪视频到指定长度"""
    try:
        cmd = [
            "ffmpeg",
            "-v",
            "warning",  # 只显示警告和错误
            "-i",
            input_path,
            "-t",
            str(target_duration),  # 设置目标时长
            "-c",
            "copy",  # 复制流而不重新编码
            "-y",  # 覆盖已有文件
            output_path,
        ]
        print(f"执行裁剪命令: {' '.join(cmd)}")

        # 执行ffmpeg命令
        subprocess.run(cmd, check=True)

        if os.path.exists(output_path):
            filesize = os.path.getsize(output_path) / (1024 * 1024)  # MB
            print(f"裁剪后的文件: {output_path}")
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
                output_path,
            ]
            duration = subprocess.check_output(duration_cmd).decode().strip()
            print(f"裁剪后视频时长: {float(duration):.2f}秒")

            return True
        else:
            print(f"错误: 未能找到裁剪后的文件 {output_path}")
            return False
    except Exception as e:
        print(f"裁剪视频时出错: {e}")
        return False


def process_channel_audio(channel_name, specific_language=None, specific_file=None):
    """处理指定频道下所有语言的音频文件"""
    channel_dir = os.path.join(MP3_BASE_DIR, channel_name)
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

    for language in language_dirs:
        # 检查是否应该退出
        if exit_flag:
            print(f"接收到退出信号，停止处理新文件")
            return

        lang_dir = os.path.join(channel_dir, language)

        if specific_file:
            # 处理特定文件
            mp3_file = os.path.join(lang_dir, specific_file)
            if os.path.exists(mp3_file):
                process_audio_file(mp3_file, channel_name, language)
            else:
                print(f"错误: 指定的音频文件不存在 {mp3_file}")
        else:
            # 处理目录下所有mp3文件
            mp3_files = glob.glob(os.path.join(lang_dir, "*.mp3"))
            for mp3_file in mp3_files:
                # 检查是否应该退出
                if exit_flag:
                    print(f"接收到退出信号，停止处理新文件")
                    return
                process_audio_file(mp3_file, channel_name, language)


def process_audio_file(mp3_file, channel_name, language):
    """处理单个音频文件，生成对应的视频"""
    # 获取处理锁，表示正在处理文件
    with processing_lock:
        # 获取音频时长
        audio_duration = get_audio_duration(mp3_file)
        if audio_duration <= 0:
            print(f"无法获取音频时长，跳过处理: {mp3_file}")
            return

        print(f"正在处理音频文件: {mp3_file}")
        print(f"音频时长: {audio_duration:.2f}秒")

        # 获取视频文件名（不带扩展名）
        base_filename = os.path.basename(mp3_file).rsplit(".", 1)[0]

        # 创建输出目录
        output_dir = os.path.join(OUTPUT_BASE_DIR, channel_name, language)
        os.makedirs(output_dir, exist_ok=True)

        # 设置最终输出路径
        final_output_path = os.path.join(output_dir, f"{base_filename}.mp4")

        # 检查目标MP4文件是否已存在
        if os.path.exists(final_output_path):
            try:
                existing_video_duration = get_audio_duration(final_output_path)
                if existing_video_duration >= audio_duration:
                    print(
                        f"已存在的视频时长({existing_video_duration:.2f}秒)大于等于音频时长({audio_duration:.2f}秒)，跳过处理"
                    )
                    return
                else:
                    print(
                        f"已存在的视频时长({existing_video_duration:.2f}秒)小于音频时长({audio_duration:.2f}秒)，将删除并重新生成"
                    )
                    os.remove(final_output_path)
            except Exception as e:
                print(f"检查已存在视频时长时出错: {e}，将删除并重新生成")
                os.remove(final_output_path)

        # 计算需要的视频片段数量（向上取整）
        needed_clips = int((audio_duration + CLIP_DURATION - 1) // CLIP_DURATION)
        print(f"需要 {needed_clips} 个视频片段来匹配音频时长")

        # 获取所有可用的视频片段
        all_clips = glob.glob(os.path.join(MP4_CLIPS_DIR, "clip_*.mp4"))
        if len(all_clips) == 0:
            print(f"错误: 未找到任何视频片段在 {MP4_CLIPS_DIR}")
            return

        print(f"找到 {len(all_clips)} 个可用视频片段")

        # 随机采样needed_clips次（允许重复采样）
        selected_clips = []
        for _ in range(needed_clips):
            selected_clips.append(random.choice(all_clips))

        # 设置临时输出路径
        temp_output_path = os.path.join(output_dir, f"{base_filename}_temp.mp4")

        # 合并视频片段
        if merge_with_ffmpeg_concat(selected_clips, temp_output_path):
            # 裁剪视频以匹配音频时长
            if trim_video(temp_output_path, final_output_path, audio_duration):
                print(f"成功生成视频: {final_output_path}")

                # 获取裁剪后视频的实际时长
                final_duration = get_audio_duration(final_output_path)
                print(f"对比时长:")
                print(f"  - 音频文件时长: {audio_duration:.2f}秒")
                print(f"  - 裁剪后视频时长: {final_duration:.2f}秒")
                print(f"  - 差异: {final_duration - audio_duration:.2f}秒")

                if (
                    abs(final_duration - audio_duration) > 0.5
                ):  # 如果差异大于0.5秒则警告
                    print(f"警告: 视频与音频时长差异较大!")

                # 清理临时文件
                if os.path.exists(temp_output_path):
                    os.remove(temp_output_path)
            else:
                print(f"裁剪视频失败: {temp_output_path}")
        else:
            print(f"合并视频片段失败")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="根据音频时长合并MP4片段")
    parser.add_argument("-c", "--channel", help="指定要处理的频道名")
    parser.add_argument("-l", "--language", help="指定要处理的语言")
    parser.add_argument("-f", "--file", help="指定要处理的音频文件名")
    parser.add_argument("--list-channels", action="store_true", help="列出所有可用频道")
    parser.add_argument(
        "--list-languages", metavar="CHANNEL", help="列出指定频道的所有可用语言"
    )
    parser.add_argument("--base-path", help="指定自定义的基础路径，覆盖默认路径")
    return parser.parse_args()


def list_channels():
    """列出所有可用频道"""
    if not os.path.exists(MP3_BASE_DIR):
        print(f"错误: 音频基础目录不存在 {MP3_BASE_DIR}")
        return

    channel_dirs = [
        d
        for d in os.listdir(MP3_BASE_DIR)
        if os.path.isdir(os.path.join(MP3_BASE_DIR, d))
    ]
    if not channel_dirs:
        print("未找到任何频道目录")
        return

    print("可用频道列表:")
    for channel in channel_dirs:
        print(f"- {channel}")


def list_languages(channel_name):
    """列出指定频道的所有可用语言"""
    channel_dir = os.path.join(MP3_BASE_DIR, channel_name)
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
    global MP3_BASE_DIR, MP4_CLIPS_DIR, OUTPUT_BASE_DIR
    if args.base_path:
        custom_base_path = args.base_path
        MP3_BASE_DIR = f"{custom_base_path}/merge_multi_lange_mp3"
        MP4_CLIPS_DIR = f"{custom_base_path}/mp4_clips"
        OUTPUT_BASE_DIR = f"{custom_base_path}/mp4_merge_silient"
        print(f"使用自定义基础路径: {custom_base_path}")
    else:
        # 打印系统信息和基础路径
        print(f"检测到系统: {platform.system()}")
        print(f"使用基础路径: {BASE_PATH}")

    # 确保输出根目录存在
    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)

    # 启动键盘监听线程
    key_thread = threading.Thread(target=read_key, daemon=True)
    key_thread.start()

    # 启动按键监控线程
    monitor_thread = threading.Thread(target=key_monitor, daemon=True)
    monitor_thread.start()

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
        process_channel_audio(args.channel, args.language, args.file)
    else:
        # 获取所有频道目录
        channel_dirs = [
            d
            for d in os.listdir(MP3_BASE_DIR)
            if os.path.isdir(os.path.join(MP3_BASE_DIR, d))
        ]

        if not channel_dirs:
            print(f"错误: 未找到任何频道目录在 {MP3_BASE_DIR}")
            return

        print(f"找到以下频道: {', '.join(channel_dirs)}")

        # 处理每个频道
        for channel_name in channel_dirs:
            # 检查是否应该退出
            if exit_flag:
                break

            print(f"\n开始处理频道: {channel_name}")
            process_channel_audio(channel_name)

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
