"""
优化版MP3合并脚本 - 更简单、更高效的MP3片段合并工具
主要改进：
1. 简化验证流程 - 只检查文件大小，不进行复杂的格式验证
2. 直接合并MP3 - 避免转换为WAV的额外步骤
3. 减少临时文件 - 使用更直接的合并方法
4. 简化错误处理 - 快速跳过问题文件，不强制修复
5. 并行优化 - 更好的并发处理

输入路径：
- MP3源文件路径：/Volumes/dhl/buda_videos_youtube/multi_lang_mp3 (macOS)
                /media/dhl/buda_videos_youtube/multi_lang_mp3 (Linux)

输出路径：
- 合并后MP3文件：/Volumes/dhl/buda_videos_youtube/merge_multi_lange_mp3 (macOS)
                /media/dhl/buda_videos_youtube/merge_multi_lange_mp3 (Linux)

使用方法:
python merge_mp3_optimized.py [-l 语言列表] [-f] [-w 工作线程数] [-s 频道名/视频名]
"""

import os
import argparse
import platform
import subprocess
import concurrent.futures
from pathlib import Path
from tqdm import tqdm


def get_base_path():
    """根据操作系统类型返回对应的基础路径"""
    if platform.system() == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# 定义全局路径变量
BASE_PATH = get_base_path()
INPUT_MP3_PATH = os.path.join(BASE_PATH, "multi_lang_mp3")
OUTPUT_MERGE_PATH = os.path.join(BASE_PATH, "merge_multi_lange_mp3")
SUPPORTED_LANGUAGES = ["en", "ja", "vi", "ko"]


def is_valid_mp3(file_path):
    """简单快速的MP3文件验证 - 只检查文件大小"""
    try:
        return (
            os.path.exists(file_path) and os.path.getsize(file_path) > 1024
        )  # 至少1KB
    except:
        return False


def merge_mp3_files_optimized(input_dir, output_file, force=False):
    """优化版MP3合并函数 - 直接使用ffmpeg concat"""

    # 检查输出文件是否已存在
    if os.path.exists(output_file) and not force:
        return True

    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    os.makedirs(output_dir, exist_ok=True)

    # 获取所有MP3文件
    mp3_files = [
        f for f in os.listdir(input_dir) if f.endswith(".mp3") and not f.startswith(".")
    ]

    if not mp3_files:
        return False

    # 按数字排序
    mp3_files.sort(key=lambda f: int(os.path.splitext(f)[0]))

    # 快速过滤有效文件
    valid_files = []
    for mp3_file in mp3_files:
        file_path = os.path.join(input_dir, mp3_file)
        if is_valid_mp3(file_path):
            valid_files.append(file_path)

    if not valid_files:
        return False

    # 如果只有一个文件，直接复制
    if len(valid_files) == 1:
        try:
            import shutil

            shutil.copy2(valid_files[0], output_file)
            return True
        except:
            return False

    # 使用ffmpeg的concat协议直接合并MP3
    try:
        # 创建临时的文件列表
        concat_list = os.path.join(
            output_dir, f".concat_{os.path.basename(output_file)}.txt"
        )

        with open(concat_list, "w", encoding="utf-8") as f:
            for file_path in valid_files:
                # 转义路径中的特殊字符
                escaped_path = file_path.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

        # 执行ffmpeg合并命令
        cmd = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list,
            "-c",
            "copy",  # 直接复制，不重新编码
            output_file,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # 清理临时文件
        try:
            os.remove(concat_list)
        except:
            pass

        # 检查结果
        if result.returncode == 0 and is_valid_mp3(output_file):
            return True
        else:
            # 如果直接复制失败，尝试重新编码
            return merge_with_reencoding(valid_files, output_file)

    except Exception as e:
        # 清理可能的临时文件
        try:
            os.remove(concat_list)
        except:
            pass
        return False


def merge_with_reencoding(valid_files, output_file):
    """如果直接复制失败，使用重新编码的方法"""
    try:
        # 使用filter_complex进行合并和重新编码
        cmd = ["ffmpeg", "-y", "-v", "error"]

        # 添加所有输入文件
        for file_path in valid_files:
            cmd.extend(["-i", file_path])

        # 构建filter_complex
        filter_inputs = "".join(f"[{i}:a]" for i in range(len(valid_files)))
        filter_concat = f"{filter_inputs}concat=n={len(valid_files)}:v=0:a=1[out]"

        cmd.extend(
            [
                "-filter_complex",
                filter_concat,
                "-map",
                "[out]",
                "-codec:a",
                "libmp3lame",
                "-b:a",
                "128k",
                output_file,
            ]
        )

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0 and is_valid_mp3(output_file)

    except:
        return False


def process_single_task(args):
    """处理单个合并任务"""
    channel, video_name, language, force = args

    input_dir = os.path.join(INPUT_MP3_PATH, channel, video_name, language)

    if not os.path.exists(input_dir):
        return False

    output_dir = os.path.join(OUTPUT_MERGE_PATH, channel, language)
    output_file = os.path.join(output_dir, f"{video_name}.mp3")

    return merge_mp3_files_optimized(input_dir, output_file, force)


def process_all_channels(languages=None, force=False, max_workers=4):
    """处理所有频道的所有视频"""
    if languages is None:
        languages = SUPPORTED_LANGUAGES

    # 验证语言支持
    languages = [lang for lang in languages if lang in SUPPORTED_LANGUAGES]
    if not languages:
        print("❌ 没有指定任何有效的语言")
        return

    # 检查输入路径
    if not os.path.exists(INPUT_MP3_PATH):
        print(f"❌ 输入路径不存在: {INPUT_MP3_PATH}")
        return

    # 收集所有任务
    tasks = []
    channels = [
        d
        for d in os.listdir(INPUT_MP3_PATH)
        if os.path.isdir(os.path.join(INPUT_MP3_PATH, d))
    ]

    for channel in channels:
        channel_path = os.path.join(INPUT_MP3_PATH, channel)
        videos = [
            d
            for d in os.listdir(channel_path)
            if os.path.isdir(os.path.join(channel_path, d))
        ]

        for video_name in videos:
            for language in languages:
                input_dir = os.path.join(channel_path, video_name, language)
                if not os.path.exists(input_dir):
                    continue

                output_file = os.path.join(
                    OUTPUT_MERGE_PATH, channel, language, f"{video_name}.mp3"
                )
                if os.path.exists(output_file) and not force:
                    continue

                tasks.append((channel, video_name, language, force))

    if not tasks:
        print("✅ 没有需要处理的任务")
        return

    print(f"🚀 开始处理 {len(tasks)} 个合并任务，使用 {max_workers} 个并发线程")

    # 并发执行任务
    success_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        with tqdm(total=len(tasks), desc="合并进度") as pbar:
            future_to_task = {
                executor.submit(process_single_task, task): task for task in tasks
            }

            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    if future.result():
                        success_count += 1
                except Exception as exc:
                    channel, video_name, language, _ = task
                    print(f"⚠️  任务失败: {channel}/{video_name} ({language}) - {exc}")
                finally:
                    pbar.update(1)

    print(f"✅ 处理完成：成功 {success_count}/{len(tasks)} 个任务")


def process_single_video(channel, video_name, languages, force=False):
    """处理单个视频的所有语言版本"""
    success_count = 0

    for language in languages:
        input_dir = os.path.join(INPUT_MP3_PATH, channel, video_name, language)

        if not os.path.exists(input_dir):
            print(f"⚠️  目录不存在，跳过: {input_dir}")
            continue

        output_dir = os.path.join(OUTPUT_MERGE_PATH, channel, language)
        output_file = os.path.join(output_dir, f"{video_name}.mp3")

        print(f"🔄 处理: {channel}/{video_name} ({language})")

        if merge_mp3_files_optimized(input_dir, output_file, force):
            success_count += 1
            print(f"✅ 成功: {output_file}")
        else:
            print(f"❌ 失败: {output_file}")

    return success_count


def main():
    parser = argparse.ArgumentParser(description="优化版多语言MP3文件合并工具")

    parser.add_argument(
        "-l",
        "--languages",
        nargs="+",
        choices=SUPPORTED_LANGUAGES,
        default=SUPPORTED_LANGUAGES,
        help=f"目标语言列表 (默认: {' '.join(SUPPORTED_LANGUAGES)})",
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="强制重新合并，即使输出文件已存在"
    )
    parser.add_argument(
        "-w", "--workers", type=int, default=4, help="并发处理的工作线程数，默认为4"
    )
    parser.add_argument(
        "-s", "--single", type=str, help="只处理指定的单个视频，格式: 频道名/视频名"
    )

    args = parser.parse_args()

    print("🎵 优化版MP3合并工具启动")
    print(f"📂 输入目录: {INPUT_MP3_PATH}")
    print(f"📂 输出目录: {OUTPUT_MERGE_PATH}")
    print(f"🌐 处理语言: {', '.join(args.languages)}")
    print(f"🔧 并发线程: {args.workers}")

    if args.single:
        if "/" not in args.single:
            print("❌ 单个视频参数格式应为 '频道名/视频名'")
            return

        channel, video_name = args.single.split("/", 1)
        video_path = os.path.join(INPUT_MP3_PATH, channel, video_name)

        if not os.path.exists(video_path):
            print(f"❌ 指定的视频路径不存在: {video_path}")
            return

        print(f"🎯 处理单个视频: {channel}/{video_name}")
        success_count = process_single_video(
            channel, video_name, args.languages, args.force
        )
        print(f"✅ 处理完成，成功合并 {success_count}/{len(args.languages)} 个语言版本")
    else:
        process_all_channels(args.languages, args.force, args.workers)


if __name__ == "__main__":
    main()
