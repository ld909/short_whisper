#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
优化版合并MP4和MP3文件脚本
-----------------------
相比原版本的主要优化：
1. 并行处理多个文件
2. 批量ffmpeg操作
3. 智能音频格式检测，避免不必要的重编码
4. 改进的GPU加速支持
5. 更好的内存管理和错误处理

新增参数:
  --workers     并行处理的worker数量 (默认为CPU核心数)
  --batch-size  批量处理的文件数量 (默认10)
  --no-audio-encode  如果MP3已经是AAC格式则跳过重编码
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
import concurrent.futures
import multiprocessing
from pathlib import Path
import json
import shutil
import math


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


# 进度显示
class SimpleProgressBar:
    """简单的进度条实现"""

    def __init__(self, total, desc="处理中", width=50):
        self.total = total
        self.current = 0
        self.desc = desc
        self.width = width
        self.start_time = time.time()

    def update(self, n=1):
        """更新进度"""
        self.current += n
        self._display()

    def _display(self):
        """显示进度条"""
        if self.total == 0:
            percent = 0
        else:
            percent = self.current / self.total

        filled = int(self.width * percent)
        bar = "█" * filled + "░" * (self.width - filled)

        # 计算时间信息
        elapsed = time.time() - self.start_time
        if self.current > 0:
            avg_time = elapsed / self.current
            eta = avg_time * (self.total - self.current)
            eta_str = f", ETA: {eta:.0f}s" if eta > 0 else ""
        else:
            eta_str = ""

        # 计算速度
        speed = self.current / elapsed if elapsed > 0 else 0

        print(
            f"\r{self.desc}: {bar} {self.current}/{self.total} ({percent:.1%}) "
            f"[{elapsed:.0f}s, {speed:.1f}files/s{eta_str}]",
            end="",
            flush=True,
        )

        if self.current >= self.total:
            print()  # 完成后换行

    def close(self):
        """结束进度条"""
        if self.current < self.total:
            self.current = self.total
            self._display()


def get_media_info(file_path):
    """获取媒体文件的详细信息"""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]
        result = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        return json.loads(result.decode())
    except Exception:
        return None


def get_duration_fast(file_path):
    """快速获取媒体文件的时长"""
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
        duration = float(
            subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        )
        return duration
    except Exception:
        return 0


def is_audio_aac(file_path):
    """检查音频文件是否已经是AAC格式"""
    info = get_media_info(file_path)
    if not info:
        return False

    for stream in info.get("streams", []):
        if stream.get("codec_type") == "audio":
            return stream.get("codec_name") == "aac"
    return False


def merge_mp4_mp3_optimized(
    mp4_file, mp3_file, output_file, force=False, use_gpu=False, skip_audio_encode=False
):
    """优化版合并MP4和MP3文件"""
    # 检查输出目录
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # 检查是否需要重新生成
    if os.path.exists(output_file) and not force:
        return True, "文件已存在，跳过"

    # 检查输入文件
    if not os.path.exists(mp4_file):
        return False, f"MP4文件不存在: {os.path.basename(mp4_file)}"

    if not os.path.exists(mp3_file):
        return False, f"MP3文件不存在: {os.path.basename(mp3_file)}"

    # 快速时长检查
    mp4_duration = get_duration_fast(mp4_file)
    mp3_duration = get_duration_fast(mp3_file)

    if mp4_duration <= 0 or mp3_duration <= 0:
        return False, "无法获取媒体时长"

    duration_diff = abs(mp4_duration - mp3_duration)
    if duration_diff > 2.0:  # 放宽到2秒误差
        return False, f"时长相差过大: {duration_diff:.2f}秒"

    # 智能音频编码选择
    audio_codec = "copy" if skip_audio_encode and is_audio_aac(mp3_file) else "aac"

    try:
        cmd = ["ffmpeg"]

        # GPU加速优化
        if use_gpu:
            cmd.extend(["-hwaccel", "auto", "-hwaccel_output_format", "auto"])

        cmd.extend(
            [
                "-v",
                "error",  # 只显示错误
                "-i",
                mp4_file,
                "-i",
                mp3_file,
                "-map",
                "0:v",
                "-map",
                "1:a",
                "-c:v",
                "copy",
                "-c:a",
                audio_codec,
                "-avoid_negative_ts",
                "make_zero",  # 避免时间戳问题
                "-shortest",
                "-y",
                output_file,
            ]
        )

        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        end_time = time.time()

        if os.path.exists(output_file):
            filesize = os.path.getsize(output_file) / (1024 * 1024)
            processing_time = end_time - start_time
            return True, f"完成: {filesize:.1f}MB, 耗时: {processing_time:.1f}秒"
        else:
            return False, "输出文件未生成"

    except subprocess.CalledProcessError as e:
        return False, f"ffmpeg错误: {e.stderr[:100]}"
    except Exception as e:
        return False, f"处理错误: {str(e)[:100]}"


def process_file_batch(
    file_jobs, use_gpu=False, skip_audio_encode=False, progress_callback=None
):
    """批量处理文件"""
    results = []

    for job in file_jobs:
        if exit_flag:
            break

        mp4_file, mp3_file, output_file, force = job
        filename = os.path.basename(output_file)

        success, message = merge_mp4_mp3_optimized(
            mp4_file, mp3_file, output_file, force, use_gpu, skip_audio_encode
        )

        results.append((filename, success, message))

        # 调用进度回调
        if progress_callback:
            progress_callback(filename, success, message)

    return results


def collect_file_jobs(channel, language=None, specific_file=None, force=False):
    """收集需要处理的文件作业"""
    jobs = []

    channel_dir = os.path.join(MP4_BASE_DIR, channel)
    if not os.path.exists(channel_dir):
        return jobs

    # 获取语言目录
    if language:
        language_dirs = (
            [language] if os.path.isdir(os.path.join(channel_dir, language)) else []
        )
    else:
        language_dirs = [
            d
            for d in os.listdir(channel_dir)
            if os.path.isdir(os.path.join(channel_dir, d)) and not d.startswith(".")
        ]

    for lang in language_dirs:
        lang_dir = os.path.join(channel_dir, lang)
        mp3_lang_dir = os.path.join(MP3_BASE_DIR, channel, lang)

        if not os.path.exists(mp3_lang_dir):
            continue

        if specific_file:
            # 处理特定文件
            file_base = (
                specific_file.rsplit(".", 1)[0]
                if "." in specific_file
                else specific_file
            )
            mp4_file = os.path.join(lang_dir, f"{file_base}.mp4")
            mp3_file = os.path.join(mp3_lang_dir, f"{file_base}.mp3")
            output_file = os.path.join(
                OUTPUT_BASE_DIR, channel, lang, f"{file_base}.mp4"
            )

            if os.path.exists(mp4_file) and os.path.exists(mp3_file):
                jobs.append((mp4_file, mp3_file, output_file, force))
        else:
            # 批量收集文件
            mp4_files = glob.glob(os.path.join(lang_dir, "*.mp4"))
            for mp4_file in mp4_files:
                if os.path.basename(mp4_file).startswith("."):
                    continue

                file_base = os.path.basename(mp4_file).rsplit(".", 1)[0]
                mp3_file = os.path.join(mp3_lang_dir, f"{file_base}.mp3")
                output_file = os.path.join(
                    OUTPUT_BASE_DIR, channel, lang, f"{file_base}.mp4"
                )

                if os.path.exists(mp3_file):
                    jobs.append((mp4_file, mp3_file, output_file, force))

    return jobs


def process_channel_language_parallel(
    channel,
    language=None,
    specific_file=None,
    force=False,
    use_gpu=False,
    workers=None,
    batch_size=10,
    skip_audio_encode=False,
):
    """并行处理频道语言"""

    # 收集所有需要处理的文件
    jobs = collect_file_jobs(channel, language, specific_file, force)

    if not jobs:
        print(f"频道 {channel} 中没有找到需要处理的文件")
        return

    print(f"找到 {len(jobs)} 个文件需要处理")

    # 确定worker数量
    if workers is None:
        workers = min(multiprocessing.cpu_count(), len(jobs))

    print(f"使用 {workers} 个并行处理器")

    # 初始化进度条
    progress_bar = SimpleProgressBar(len(jobs), f"合并 {channel}", width=40)

    # 进度回调函数
    def update_progress(filename, success, message):
        progress_bar.update(1)
        # 简化的状态显示，避免干扰进度条
        status = "✓" if success else "✗"
        if not success:
            print(
                f"\n{status} {filename[:40]}{'...' if len(filename) > 40 else ''}: {message}"
            )

    # 分批处理
    total_processed = 0
    total_success = 0
    start_time = time.time()

    # 将作业分成批次
    batches = [jobs[i : i + batch_size] for i in range(0, len(jobs), batch_size)]
    print(f"分成 {len(batches)} 个批次处理")

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_batch = {}

        for batch in batches:
            if exit_flag:
                break

            future = executor.submit(
                process_file_batch, batch, use_gpu, skip_audio_encode, update_progress
            )
            future_to_batch[future] = batch

        for future in concurrent.futures.as_completed(future_to_batch):
            if exit_flag:
                break

            try:
                results = future.get()
                for filename, success, message in results:
                    total_processed += 1
                    if success:
                        total_success += 1

            except Exception as e:
                print(f"\n批次处理错误: {e}")

    # 确保进度条完成
    progress_bar.close()

    end_time = time.time()
    total_time = end_time - start_time

    print(f"\n📊 处理完成统计:")
    print(f"总文件数: {total_processed}")
    print(f"成功: {total_success} (✓)")
    print(f"失败: {total_processed - total_success} (✗)")
    print(
        f"成功率: {(total_success/total_processed*100):.1f}%"
        if total_processed > 0
        else "0%"
    )
    print(f"总耗时: {total_time:.1f}秒")
    if total_processed > 0:
        print(f"平均每文件: {total_time/total_processed:.1f}秒")
        print(f"处理速度: {total_processed/total_time:.1f} 文件/秒")


# 保留原有的监控和列表功能
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

    print("按3次q键可以退出程序（会等待当前批次处理完成）")

    while True:
        try:
            key = exit_queue.get(timeout=1.0)

            if key == "q":
                current_time = time.time()
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
                    print(f"检测到连续按键q三次，程序将在当前批次处理完成后退出")
                    global exit_flag
                    exit_flag = True
                    break
            else:
                q_count = 0

        except queue.Empty:
            pass

        if exit_flag:
            break


def list_channels():
    """列出所有可用频道"""
    if not os.path.exists(MP4_BASE_DIR) or not os.path.exists(MP3_BASE_DIR):
        print(f"错误: 基础目录不存在")
        return []

    mp4_channels = set(
        [
            d
            for d in os.listdir(MP4_BASE_DIR)
            if os.path.isdir(os.path.join(MP4_BASE_DIR, d)) and not d.startswith(".")
        ]
    )
    mp3_channels = set(
        [
            d
            for d in os.listdir(MP3_BASE_DIR)
            if os.path.isdir(os.path.join(MP3_BASE_DIR, d)) and not d.startswith(".")
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
    mp4_channel_dir = os.path.join(MP4_BASE_DIR, channel_name)
    mp3_channel_dir = os.path.join(MP3_BASE_DIR, channel_name)

    if not os.path.exists(mp4_channel_dir) or not os.path.exists(mp3_channel_dir):
        print(f"错误: 频道目录不存在")
        return []

    mp4_languages = set(
        [
            d
            for d in os.listdir(mp4_channel_dir)
            if os.path.isdir(os.path.join(mp4_channel_dir, d)) and not d.startswith(".")
        ]
    )
    mp3_languages = set(
        [
            d
            for d in os.listdir(mp3_channel_dir)
            if os.path.isdir(os.path.join(mp3_channel_dir, d)) and not d.startswith(".")
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
    parser = argparse.ArgumentParser(description="优化版合并MP4和MP3文件")
    parser.add_argument("-c", "--channel", help="指定要处理的频道名")
    parser.add_argument("-l", "--language", help="指定要处理的语言")
    parser.add_argument("-f", "--file", help="指定要处理的文件名")
    parser.add_argument("--list-channels", action="store_true", help="列出所有可用频道")
    parser.add_argument(
        "--list-languages", metavar="CHANNEL", help="列出指定频道的所有可用语言"
    )
    parser.add_argument("--force", action="store_true", help="强制重新生成已存在的文件")
    parser.add_argument("--base-path", help="指定自定义的基础路径，覆盖默认路径")
    parser.add_argument("--gpu", action="store_true", help="启用GPU硬件加速")
    parser.add_argument(
        "--workers", type=int, help="并行处理的worker数量 (默认为CPU核心数)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=10, help="批量处理的文件数量 (默认10)"
    )
    parser.add_argument(
        "--no-audio-encode",
        action="store_true",
        help="如果音频已经是AAC格式则跳过重编码",
    )
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    # 设置基础路径
    global MP4_BASE_DIR, MP3_BASE_DIR, OUTPUT_BASE_DIR
    if args.base_path:
        custom_base_path = args.base_path
        MP4_BASE_DIR = f"{custom_base_path}/mp4_multi_with_subtitles"
        MP3_BASE_DIR = f"{custom_base_path}/merge_multi_lange_mp3"
        OUTPUT_BASE_DIR = f"{custom_base_path}/mp4_with_audio"
        print(f"使用自定义基础路径: {custom_base_path}")
    else:
        print(f"检测到系统: {platform.system()}")
        print(f"使用基础路径: {BASE_PATH}")

    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)

    # 处理列表命令
    if args.list_channels:
        list_channels()
        return

    if args.list_languages:
        list_languages(args.list_languages)
        return

    # 启动监控线程
    key_thread = threading.Thread(target=read_key, daemon=True)
    key_thread.start()

    monitor_thread = threading.Thread(target=key_monitor, daemon=True)
    monitor_thread.start()

    # 处理文件
    if args.channel:
        print(f"\n开始并行处理频道: {args.channel}")
        process_channel_language_parallel(
            args.channel,
            args.language,
            args.file,
            args.force,
            args.gpu,
            args.workers,
            args.batch_size,
            args.no_audio_encode,
        )
    else:
        channels = list_channels()
        if not channels:
            print("没有可用的频道，退出")
            return

        for channel in channels:
            if exit_flag:
                break
            print(f"\n开始并行处理频道: {channel}")
            process_channel_language_parallel(
                channel,
                args.language,
                args.file,
                args.force,
                args.gpu,
                args.workers,
                args.batch_size,
                args.no_audio_encode,
            )

    if exit_flag:
        print("正在等待当前批次处理完成...")

    # 等待线程结束
    if key_thread.is_alive():
        key_thread.join(1)
    if monitor_thread.is_alive():
        monitor_thread.join(1)

    print("\n所有处理完成！")


if __name__ == "__main__":
    main()
