#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频片段合并脚本
将 synthesize_audio.py 生成的音频片段按故事合并为完整的故事音频文件
支持断点续传功能，自动检测操作系统选择合适的输出路径
"""

import os
import glob
import argparse
import subprocess
import time
import platform
from pathlib import Path


# ============ 配置参数 ============
# 输入目录：根据操作系统自动选择
def get_input_dir():
    """根据操作系统返回合适的输入目录"""
    if platform.system() == "Darwin":  # macOS
        return "/Volumes/dhl/audio/scifi/mp3_clips"
    else:  # Linux 和其他系统
        return "/media/dhl/audio/scifi/mp3_clips"


# 输出目录：根据操作系统自动选择
def get_output_dir():
    """根据操作系统返回合适的输出目录"""
    if platform.system() == "Darwin":  # macOS
        return "/Volumes/dhl/audio/scifi/mp3_merge"
    else:  # Linux 和其他系统
        return "/media/dhl/audio/scifi/mp3_merge"


# 默认输入和输出目录
INPUT_DIR = get_input_dir()
OUTPUT_DIR = get_output_dir()

# 合并后的文件名
OUTPUT_FILENAME = "story.mp3"
# ===================================


def get_story_directories(input_dir):
    """
    获取所有故事目录，排除Mac生成的隐藏文件

    Args:
        input_dir (str): 输入目录路径

    Returns:
        list: 排序后的故事目录列表
    """
    if not os.path.exists(input_dir):
        print(f"❌ 输入目录不存在: {input_dir}")
        return []

    story_dirs = []

    # 遍历所有子目录
    for item in os.listdir(input_dir):
        item_path = os.path.join(input_dir, item)

        # 排除隐藏文件和目录
        if item.startswith("."):
            print(f"⏭️  跳过隐藏目录: {item}")
            continue

        # 只处理目录
        if os.path.isdir(item_path):
            story_dirs.append((item, item_path))

    # 按故事索引排序
    def extract_story_number(item):
        story_index = item[0]
        try:
            return int(story_index)
        except:
            return 0

    story_dirs.sort(key=extract_story_number)

    print(f"📊 找到 {len(story_dirs)} 个故事目录")
    return story_dirs


def get_audio_clips(story_dir):
    """
    获取故事目录下的所有音频片段，按块索引排序

    Args:
        story_dir (str): 故事目录路径

    Returns:
        list: 排序后的音频文件路径列表
    """
    audio_files = []

    # 获取所有 mp3 文件
    mp3_pattern = os.path.join(story_dir, "*.mp3")
    found_files = glob.glob(mp3_pattern)

    # 过滤掉隐藏文件和临时文件
    for audio_file in found_files:
        filename = os.path.basename(audio_file)

        # 排除隐藏文件和临时文件
        if filename.startswith(".") or filename.startswith("._"):
            print(f"⏭️  跳过隐藏/临时文件: {audio_file}")
            continue

        audio_files.append(audio_file)

    # 按块索引排序
    def extract_chunk_number(filepath):
        basename = os.path.basename(filepath)
        try:
            return int(basename.split(".")[0])
        except:
            return 0

    audio_files.sort(key=extract_chunk_number)

    return audio_files


def is_valid_audio_file(file_path, min_size_bytes=1024):
    """
    检查音频文件是否有效

    Args:
        file_path (str): 音频文件路径
        min_size_bytes (int): 最小文件大小（字节）

    Returns:
        bool: 文件是否有效
    """
    if not os.path.exists(file_path):
        return False

    try:
        file_size = os.path.getsize(file_path)
        if file_size < min_size_bytes:
            print(f"⚠️  文件过小，可能损坏: {file_path} ({file_size} 字节)")
            return False
        return True
    except Exception as e:
        print(f"⚠️  检查文件时出错: {file_path}, 错误: {e}")
        return False


def merge_audio_clips(audio_files, output_file):
    """
    使用 ffmpeg 合并音频片段

    Args:
        audio_files (list): 音频文件路径列表
        output_file (str): 输出文件路径

    Returns:
        bool: 合并是否成功
    """
    if not audio_files:
        print(f"❌ 没有音频文件需要合并")
        return False

    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)

        # 创建临时文件列表
        temp_file_list = os.path.join(output_dir, "temp_file_list.txt")

        # 写入文件列表
        with open(temp_file_list, "w", encoding="utf-8") as f:
            for audio_file in audio_files:
                # 使用相对路径或绝对路径，确保路径中的特殊字符被正确处理
                escaped_path = audio_file.replace("'", "'\"'\"'")
                f.write(f"file '{escaped_path}'\n")

        print(f"📝 创建临时文件列表: {temp_file_list}")
        print(f"🔗 准备合并 {len(audio_files)} 个音频片段")

        # 构建 ffmpeg 命令 - 使用重新编码而不是直接复制
        cmd = [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            temp_file_list,
            "-acodec",
            "libmp3lame",  # 使用MP3编码器
            "-b:a",
            "192k",  # 设置比特率
            "-ar",
            "44100",  # 设置采样率
            "-ac",
            "1",  # 单声道
            "-y",  # 覆盖输出文件
            output_file,
        ]

        print(f"🔄 执行合并命令...")

        # 执行命令
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=3600  # 60分钟超时
        )

        # 清理临时文件
        try:
            os.remove(temp_file_list)
        except:
            pass

        if result.returncode == 0:
            print(f"✅ 音频合并成功: {output_file}")

            # 检查输出文件
            if is_valid_audio_file(output_file, min_size_bytes=10240):  # 至少10KB
                file_size = os.path.getsize(output_file)
                print(
                    f"📊 输出文件大小: {file_size:,} 字节 ({file_size/1024/1024:.1f} MB)"
                )
                return True
            else:
                print(f"❌ 输出文件无效或过小")
                return False
        else:
            print(f"❌ 音频合并失败:")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print(f"❌ 音频合并超时: {output_file}")
        return False
    except Exception as e:
        print(f"❌ 音频合并出错: {e}")
        return False


def scan_existing_merged_files(output_dir):
    """
    扫描已存在的合并音频文件

    Args:
        output_dir (str): 输出目录路径

    Returns:
        set: 已存在的故事索引集合
    """
    existing_stories = set()

    if not os.path.exists(output_dir):
        return existing_stories

    print(f"🔍 扫描已存在的合并音频文件...")

    # 遍历所有故事目录
    for item in os.listdir(output_dir):
        if item.startswith("."):
            continue

        story_path = os.path.join(output_dir, item)
        if os.path.isdir(story_path):
            story_file = os.path.join(story_path, OUTPUT_FILENAME)

            if is_valid_audio_file(story_file, min_size_bytes=10240):
                existing_stories.add(item)
                file_size = os.path.getsize(story_file)
                print(f"✅ 已存在: 故事 {item} ({file_size:,} 字节)")
            else:
                print(f"🗑️  发现无效文件，将重新生成: {story_file}")
                try:
                    if os.path.exists(story_file):
                        os.remove(story_file)
                        print(f"✅ 已删除无效文件: {story_file}")
                except Exception as e:
                    print(f"❌ 删除无效文件失败: {e}")

    print(f"📊 找到 {len(existing_stories)} 个有效的合并音频文件")
    return existing_stories


def get_progress_stats(story_dirs, existing_stories):
    """
    获取进度统计信息

    Args:
        story_dirs (list): 所有故事目录列表
        existing_stories (set): 已存在的故事索引集合

    Returns:
        dict: 进度统计信息
    """
    total_stories = len(story_dirs)
    completed_stories = 0
    pending_stories = []

    for story_index, story_dir in story_dirs:
        if story_index in existing_stories:
            completed_stories += 1
        else:
            pending_stories.append((story_index, story_dir))

    remaining_stories = total_stories - completed_stories
    completion_rate = (
        (completed_stories / total_stories * 100) if total_stories > 0 else 0
    )

    return {
        "total_stories": total_stories,
        "completed_stories": completed_stories,
        "remaining_stories": remaining_stories,
        "pending_stories": pending_stories,
        "completion_rate": completion_rate,
    }


def process_story(story_index, story_dir, output_base_dir, force_regenerate=False):
    """
    处理单个故事，合并其所有音频片段

    Args:
        story_index (str): 故事索引
        story_dir (str): 故事目录路径
        output_base_dir (str): 输出基础目录
        force_regenerate (bool): 是否强制重新生成

    Returns:
        bool: 处理是否成功
    """
    print(f"\n📚 处理故事: {story_index}")
    print(f"   输入目录: {story_dir}")

    # 构建输出文件路径
    output_story_dir = os.path.join(output_base_dir, story_index)
    output_file = os.path.join(output_story_dir, OUTPUT_FILENAME)

    print(f"   输出文件: {output_file}")

    # 检查是否已存在且有效（除非强制重新生成）
    if not force_regenerate and is_valid_audio_file(output_file, min_size_bytes=10240):
        file_size = os.path.getsize(output_file)
        print(f"⏭️  文件已存在且有效，跳过: {output_file} ({file_size:,} 字节)")
        return True

    # 获取所有音频片段
    audio_clips = get_audio_clips(story_dir)

    if not audio_clips:
        print(f"❌ 故事 {story_index} 没有找到音频片段")
        return False

    print(f"📊 找到 {len(audio_clips)} 个音频片段")

    # 检查所有片段是否有效
    valid_clips = []
    for clip in audio_clips:
        if is_valid_audio_file(clip):
            valid_clips.append(clip)
        else:
            print(f"⚠️  跳过无效音频片段: {clip}")

    if not valid_clips:
        print(f"❌ 故事 {story_index} 没有有效的音频片段")
        return False

    if len(valid_clips) != len(audio_clips):
        print(f"⚠️  有 {len(audio_clips) - len(valid_clips)} 个无效片段被跳过")

    # 显示将要合并的片段
    print(f"🔗 将合并以下 {len(valid_clips)} 个片段:")
    for i, clip in enumerate(valid_clips, 1):
        filename = os.path.basename(clip)
        file_size = os.path.getsize(clip)
        print(f"     {i:2d}. {filename} ({file_size:,} 字节)")

    # 合并音频片段
    success = merge_audio_clips(valid_clips, output_file)

    if success:
        print(f"✅ 故事 {story_index} 合并完成")
        return True
    else:
        print(f"❌ 故事 {story_index} 合并失败")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="音频片段合并器 - 将音频片段合并为完整故事（支持断点续传）"
    )
    parser.add_argument(
        "--input-dir",
        default=INPUT_DIR,
        help=f"输入目录路径 (默认: 根据操作系统自动选择)",
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        help=f"输出目录路径 (默认: 根据操作系统自动选择)",
    )
    parser.add_argument("--story", help="只处理指定故事索引（可选）")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="预览模式，只显示会处理哪些故事，不实际处理",
    )
    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        help="强制重新生成所有文件，忽略已存在的文件",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="断点续传模式，跳过已存在的有效音频文件 (默认: True)",
    )

    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir

    print(f"🎵 音频片段合并器 (支持断点续传)")
    print(f"🖥️  运行平台: {platform.system()}")
    print(f"📁 输入目录: {input_dir}")
    print(f"📁 输出目录: {output_dir}")
    print(f"📄 输出文件名: {OUTPUT_FILENAME}")

    if args.force_regenerate:
        print(f"🔄 强制重新生成模式: 将重新生成所有文件")
    elif args.resume:
        print(f"⚡ 断点续传模式: 将跳过已存在的有效文件")

    # 检查 ffmpeg 是否可用
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print(f"✅ ffmpeg 可用")
    except:
        print(f"❌ ffmpeg 不可用，请确保已安装 ffmpeg")
        return

    # 获取所有故事目录
    story_dirs = get_story_directories(input_dir)

    if not story_dirs:
        print(f"❌ 在目录 {input_dir} 中未找到任何故事目录")
        return

    # 过滤故事（如果指定了特定故事）
    if args.story:
        story_dirs = [
            (story_idx, story_dir)
            for story_idx, story_dir in story_dirs
            if story_idx == args.story
        ]

    if not story_dirs:
        print(f"❌ 根据指定条件未找到匹配的故事")
        return

    print(f"\n📊 找到 {len(story_dirs)} 个故事目录")

    # 扫描已存在的文件（除非强制重新生成）
    existing_stories = set()
    if not args.force_regenerate:
        existing_stories = scan_existing_merged_files(output_dir)

    # 获取进度统计
    stats = get_progress_stats(story_dirs, existing_stories)

    print(f"\n📈 进度统计:")
    print(f"   总故事数: {stats['total_stories']}")
    print(f"   已完成: {stats['completed_stories']} ({stats['completion_rate']:.1f}%)")
    print(f"   待处理: {stats['remaining_stories']}")

    if args.preview:
        print(f"\n📋 预览模式 - 将要处理的故事:")
        for i, (story_index, story_dir) in enumerate(stats["pending_stories"], 1):
            output_file = os.path.join(output_dir, story_index, OUTPUT_FILENAME)

            # 统计音频片段数量
            audio_clips = get_audio_clips(story_dir)
            clip_count = len(
                [clip for clip in audio_clips if is_valid_audio_file(clip)]
            )

            print(f"  {i:3d}. 故事 {story_index}")
            print(f"       输入: {story_dir} ({clip_count} 个片段)")
            print(f"       输出: {output_file}")
            print(f"       状态: 🆕 需要合并")

        if stats["completed_stories"] > 0:
            print(f"\n✅ 已完成的故事: {stats['completed_stories']} 个")

        return

    # 如果没有待处理的故事
    if not stats["pending_stories"]:
        print(f"\n🎉 所有故事都已完成！无需处理。")
        print(f"📁 输出目录: {output_dir}")
        return

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n🔄 开始音频合并...")
    print(f"📝 本次将处理 {len(stats['pending_stories'])} 个故事")

    successful_count = 0
    failed_count = 0

    try:
        start_time = time.time()

        for i, (story_index, story_dir) in enumerate(stats["pending_stories"], 1):
            print(f"\n处理第 {i}/{len(stats['pending_stories'])} 个故事: {story_index}")
            print(
                f"总体进度: {stats['completed_stories'] + i}/{stats['total_stories']} ({(stats['completed_stories'] + i)/stats['total_stories']*100:.1f}%)"
            )

            success = process_story(
                story_index, story_dir, output_dir, args.force_regenerate
            )

            if success:
                successful_count += 1
            else:
                failed_count += 1

        end_time = time.time()
        total_time = end_time - start_time

        # 统计结果
        print(f"\n=== 🎉 处理完成 ===")
        print(f"✅ 本次成功合并: {successful_count} 个故事")
        print(f"❌ 本次合并失败: {failed_count} 个故事")
        print(f"⏭️  之前已完成: {stats['completed_stories']} 个故事")
        print(
            f"📊 总体完成: {stats['completed_stories'] + successful_count}/{stats['total_stories']} ({(stats['completed_stories'] + successful_count)/stats['total_stories']*100:.1f}%)"
        )
        print(f"⏱️  本次耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")

        if successful_count > 0:
            avg_time = total_time / successful_count
            print(f"📊 平均每个故事: {avg_time:.1f} 秒")

        total_processed = successful_count + failed_count
        if total_processed > 0:
            success_rate = successful_count / total_processed * 100
            print(f"📊 本次成功率: {success_rate:.1f}%")

        print(f"📁 输出目录: {output_dir}")

        # 检查是否还有未完成的故事
        remaining = stats["remaining_stories"] - successful_count - failed_count
        if remaining > 0:
            print(f"\n⚠️  还有 {remaining} 个故事未处理，可以重新运行程序继续处理")
        elif failed_count > 0:
            print(f"\n⚠️  有 {failed_count} 个故事处理失败，可以重新运行程序重试")
        else:
            print(f"\n🎉 所有故事处理完成！")

        if successful_count > 0:
            print(f"\n📝 合并的音频文件已保存到: {output_dir}")
            print(f"📁 目录结构: mp3_merge/[故事索引]/story.mp3")

    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断了程序执行")
        print(f"✅ 已成功处理: {successful_count} 个故事")
        print(f"❌ 处理失败: {failed_count} 个故事")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        print(f"✅ 已成功处理: {successful_count} 个故事")
        print(f"❌ 处理失败: {failed_count} 个故事")


if __name__ == "__main__":
    main()
