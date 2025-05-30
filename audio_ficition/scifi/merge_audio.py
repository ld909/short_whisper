#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频合并脚本
检查 synthesize_audio.py 输出的 MP3 文件与对应的 TXT chunk 文件数量是否一致
如果一致则合并 MP3 文件为完整的故事音频，支持断点续传功能
"""

import os
import glob
import argparse
import subprocess
import time
import json
import platform
from pathlib import Path


def get_default_paths():
    """根据操作系统返回适当的默认路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return {
            "chunk_dir": "/Volumes/dhl/audio/scifi/story_chunks",
            "audio_dir": "/Volumes/dhl/audio/scifi/mp3_clips",
            "output_dir": "/Volumes/dhl/audio/scifi/mp3_merge",
        }
    else:  # 默认为Linux/Ubuntu
        return {
            "chunk_dir": "/mnt/dhl/audio/scifi/story_chunks",
            "audio_dir": "/media/dhl/audio/scifi/mp3_clips",
            "output_dir": "/media/dhl/audio/scifi/mp3_merge",
        }


# 获取默认路径
DEFAULT_PATHS = get_default_paths()


def get_story_files(chunk_dir, audio_dir):
    """
    获取所有故事的文本块和音频文件信息

    Args:
        chunk_dir (str): 文本块目录路径
        audio_dir (str): 音频文件目录路径

    Returns:
        dict: 故事文件信息字典 {story_index: {'txt_files': [], 'mp3_files': []}}
    """
    story_info = {}

    # 检查文本块目录
    if os.path.exists(chunk_dir):
        for story_dir in glob.glob(os.path.join(chunk_dir, "*")):
            if os.path.isdir(story_dir):
                story_index = os.path.basename(story_dir)
                txt_files = glob.glob(os.path.join(story_dir, "*.txt"))

                if story_index not in story_info:
                    story_info[story_index] = {"txt_files": [], "mp3_files": []}

                story_info[story_index]["txt_files"] = sorted(
                    txt_files, key=lambda x: int(os.path.basename(x).split(".")[0])
                )

    # 检查音频文件目录
    if os.path.exists(audio_dir):
        for story_dir in glob.glob(os.path.join(audio_dir, "*")):
            if os.path.isdir(story_dir):
                story_index = os.path.basename(story_dir)
                mp3_files = glob.glob(os.path.join(story_dir, "*.mp3"))

                if story_index not in story_info:
                    story_info[story_index] = {"txt_files": [], "mp3_files": []}

                story_info[story_index]["mp3_files"] = sorted(
                    mp3_files, key=lambda x: int(os.path.basename(x).split(".")[0])
                )

    return story_info


def check_file_consistency(story_info):
    """
    检查每个故事的文本块和音频文件数量是否一致

    Args:
        story_info (dict): 故事文件信息字典

    Returns:
        dict: 检查结果 {story_index: {'consistent': bool, 'txt_count': int, 'mp3_count': int, 'missing_files': []}}
    """
    check_results = {}

    for story_index, files in story_info.items():
        txt_count = len(files["txt_files"])
        mp3_count = len(files["mp3_files"])
        consistent = txt_count == mp3_count and txt_count > 0

        # 检查文件编号是否连续对应
        missing_files = []
        if txt_count > 0 and mp3_count > 0:
            txt_indices = set()
            mp3_indices = set()

            for txt_file in files["txt_files"]:
                txt_index = os.path.basename(txt_file).split(".")[0]
                txt_indices.add(txt_index)

            for mp3_file in files["mp3_files"]:
                mp3_index = os.path.basename(mp3_file).split(".")[0]
                mp3_indices.add(mp3_index)

            # 找出缺失的文件
            missing_mp3 = txt_indices - mp3_indices
            missing_txt = mp3_indices - txt_indices

            if missing_mp3:
                missing_files.extend(
                    [f"mp3: {idx}" for idx in sorted(missing_mp3, key=int)]
                )
            if missing_txt:
                missing_files.extend(
                    [f"txt: {idx}" for idx in sorted(missing_txt, key=int)]
                )

            if missing_files:
                consistent = False

        check_results[story_index] = {
            "consistent": consistent,
            "txt_count": txt_count,
            "mp3_count": mp3_count,
            "missing_files": missing_files,
        }

    return check_results


def is_valid_merged_audio(file_path, min_size_kb=100):
    """
    检查合并后的音频文件是否有效

    Args:
        file_path (str): 音频文件路径
        min_size_kb (int): 最小文件大小（KB）

    Returns:
        bool: 文件是否有效
    """
    if not os.path.exists(file_path):
        return False

    try:
        file_size = os.path.getsize(file_path)
        min_size_bytes = min_size_kb * 1024

        if file_size == 0:
            print(f"❌ 合并文件大小为0: {file_path}")
            return False

        if file_size < min_size_bytes:
            print(
                f"⚠️  合并文件较小，可能不完整: {file_path} ({file_size / 1024:.1f} KB)"
            )
            # 对于小文件，仍然认为是有效的，只是给出警告
            return True

        return True
    except Exception as e:
        print(f"⚠️  检查合并文件时出错: {file_path}, 错误: {e}")
        return False


def merge_audio_files(mp3_files, output_file):
    """
    使用 ffmpeg 合并音频文件

    Args:
        mp3_files (list): 要合并的 MP3 文件列表（按顺序）
        output_file (str): 输出文件路径

    Returns:
        bool: 合并是否成功
    """
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)

        print(f"🔄 开始合并 {len(mp3_files)} 个音频文件...")
        print(f"📁 输出文件: {output_file}")

        # 创建临时文件列表，供 ffmpeg 使用
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as temp_file:
            for mp3_file in mp3_files:
                # 使用相对路径或绝对路径，确保路径中的特殊字符被正确处理
                temp_file.write(f"file '{mp3_file}'\n")
            temp_list_file = temp_file.name

        try:
            # 使用 ffmpeg 合并音频文件
            # 注意：不使用 -c copy，因为源文件可能是 WAV 格式但扩展名为 MP3
            # 使用重新编码确保输出为正确的 MP3 格式
            cmd = [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                temp_list_file,
                "-acodec",
                "libmp3lame",
                "-b:a",
                "128k",  # 设置音频比特率
                "-ar",
                "44100",  # 设置采样率
                "-ac",
                "1",  # 单声道
                "-y",  # 覆盖输出文件
                output_file,
            ]

            print(f"🔄 执行 ffmpeg 命令... (重新编码为 MP3)")
            print(f"📝 命令: {' '.join(cmd)}")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600  # 10分钟超时
            )

            if result.returncode == 0:
                if is_valid_merged_audio(output_file):
                    file_size = os.path.getsize(output_file)
                    print(
                        f"✅ 音频合并成功: {output_file} ({file_size / 1024 / 1024:.2f} MB)"
                    )
                    return True
                else:
                    print(f"❌ 合并文件无效: {output_file}")
                    return False
            else:
                print(f"❌ ffmpeg 合并失败:")
                print(f"   stdout: {result.stdout}")
                print(f"   stderr: {result.stderr}")
                return False

        finally:
            # 清理临时文件
            try:
                os.unlink(temp_list_file)
            except Exception as e:
                print(f"⚠️  删除临时文件失败: {e}")

    except subprocess.TimeoutExpired:
        print(f"❌ 音频合并超时: {output_file}")
        return False
    except Exception as e:
        print(f"❌ 音频合并出错: {e}")
        return False


def scan_existing_merged_files(output_dir):
    """
    扫描输出目录中已存在的合并音频文件

    Args:
        output_dir (str): 输出目录路径

    Returns:
        set: 已存在文件的故事索引集合
    """
    existing_stories = set()

    if not os.path.exists(output_dir):
        return existing_stories

    print(f"🔍 扫描已存在的合并音频文件...")

    for story_dir in glob.glob(os.path.join(output_dir, "*")):
        if os.path.isdir(story_dir):
            story_index = os.path.basename(story_dir)
            story_file = os.path.join(story_dir, "story.mp3")

            if is_valid_merged_audio(story_file):
                existing_stories.add(story_index)
                file_size = os.path.getsize(story_file)
                print(
                    f"✅ 发现有效合并文件: 故事 {story_index} ({file_size / 1024 / 1024:.2f} MB)"
                )
            else:
                # 删除无效文件
                if os.path.exists(story_file):
                    try:
                        os.remove(story_file)
                        print(f"🗑️  已删除无效合并文件: {story_file}")
                    except Exception as e:
                        print(f"❌ 删除无效文件失败: {e}")

    print(f"📊 找到 {len(existing_stories)} 个有效的合并音频文件")
    return existing_stories


def save_merge_log(output_dir, stats, session_successful=0, session_failed=0):
    """
    保存合并日志

    Args:
        output_dir (str): 输出目录
        stats (dict): 统计信息
        session_successful (int): 本次成功合并的数量
        session_failed (int): 本次失败的数量
    """
    try:
        log_file = os.path.join(output_dir, "merge_progress.json")

        log_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_stories": stats["total_stories"],
            "consistent_stories": stats["consistent_stories"],
            "completed_merges": stats["completed_merges"] + session_successful,
            "pending_merges": stats["pending_merges"]
            - session_successful
            - session_failed,
            "session_successful": session_successful,
            "session_failed": session_failed,
            "inconsistent_stories": stats["inconsistent_stories"],
        }

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

        print(f"📝 合并日志已保存: {log_file}")

    except Exception as e:
        print(f"⚠️  保存合并日志失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="音频合并器 - 检查文件一致性并合并音频（支持断点续传）"
    )
    parser.add_argument(
        "--chunk-dir",
        default=DEFAULT_PATHS["chunk_dir"],
        help="文本块目录路径 (默认: {})".format(DEFAULT_PATHS["chunk_dir"]),
    )
    parser.add_argument(
        "--audio-dir",
        default=DEFAULT_PATHS["audio_dir"],
        help="音频文件目录路径 (默认: {})".format(DEFAULT_PATHS["audio_dir"]),
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_PATHS["output_dir"],
        help="合并音频输出目录路径 (默认: {})".format(DEFAULT_PATHS["output_dir"]),
    )
    parser.add_argument("--story", help="只处理指定故事索引（可选）")
    parser.add_argument(
        "--check-only", action="store_true", help="只检查文件一致性，不执行合并"
    )
    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        help="强制重新合并所有文件，忽略已存在的文件",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="断点续传模式，跳过已存在的有效合并文件 (默认: True)",
    )

    args = parser.parse_args()

    chunk_dir = args.chunk_dir
    audio_dir = args.audio_dir
    output_dir = args.output_dir

    print(f"🎵 音频合并器 (支持断点续传)")
    print(f"🖥️  当前操作系统: {platform.system()}")
    print(f"📁 文本块目录: {chunk_dir}")
    print(f"📁 音频文件目录: {audio_dir}")
    print(f"📁 输出目录: {output_dir}")

    if args.force_regenerate:
        print(f"🔄 强制重新合并模式: 将重新合并所有文件")
    elif args.resume:
        print(f"⚡ 断点续传模式: 将跳过已存在的有效文件")

    # 获取故事文件信息
    print(f"\n🔍 扫描故事文件...")
    story_info = get_story_files(chunk_dir, audio_dir)

    if not story_info:
        print(f"❌ 未找到任何故事文件")
        return

    print(f"📊 找到 {len(story_info)} 个故事")

    # 过滤指定故事
    if args.story:
        if args.story in story_info:
            story_info = {args.story: story_info[args.story]}
            print(f"🎯 只处理故事: {args.story}")
        else:
            print(f"❌ 未找到指定的故事: {args.story}")
            return

    # 检查文件一致性
    print(f"\n🔍 检查文件一致性...")
    check_results = check_file_consistency(story_info)

    # 统计信息
    total_stories = len(story_info)
    consistent_stories = sum(
        1 for result in check_results.values() if result["consistent"]
    )
    inconsistent_stories = total_stories - consistent_stories

    print(f"\n📊 一致性检查结果:")
    print(f"   总故事数: {total_stories}")
    print(f"   一致的故事: {consistent_stories}")
    print(f"   不一致的故事: {inconsistent_stories}")

    # 显示详细结果
    consistent_story_list = []
    for story_index, result in sorted(check_results.items(), key=lambda x: int(x[0])):
        if result["consistent"]:
            consistent_story_list.append(story_index)
            print(
                f"✅ 故事 {story_index}: TXT={result['txt_count']}, MP3={result['mp3_count']} (一致)"
            )
        else:
            print(
                f"❌ 故事 {story_index}: TXT={result['txt_count']}, MP3={result['mp3_count']} (不一致)"
            )
            if result["missing_files"]:
                print(f"   缺失文件: {', '.join(result['missing_files'])}")

    if args.check_only:
        print(f"\n📋 仅检查模式完成")
        return

    if consistent_stories == 0:
        print(f"\n❌ 没有一致的故事可以合并")
        return

    # 扫描已存在的合并文件
    existing_merged = set()
    if not args.force_regenerate:
        existing_merged = scan_existing_merged_files(output_dir)

    # 确定需要处理的故事
    pending_stories = []
    for story_index in consistent_story_list:
        if args.force_regenerate or story_index not in existing_merged:
            pending_stories.append(story_index)

    completed_merges = len(existing_merged & set(consistent_story_list))
    pending_merges = len(pending_stories)

    # 统计信息
    stats = {
        "total_stories": total_stories,
        "consistent_stories": consistent_stories,
        "inconsistent_stories": inconsistent_stories,
        "completed_merges": completed_merges,
        "pending_merges": pending_merges,
    }

    print(f"\n📈 合并统计:")
    print(f"   可合并故事: {consistent_stories}")
    print(f"   已完成合并: {completed_merges}")
    print(f"   待合并: {pending_merges}")

    if pending_merges == 0:
        print(f"\n🎉 所有可合并的故事都已完成！")
        return

    # 开始合并处理
    print(f"\n🔄 开始音频合并...")
    print(f"📝 本次将处理 {pending_merges} 个故事")

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    successful_count = 0
    failed_count = 0

    try:
        start_time = time.time()

        for i, story_index in enumerate(pending_stories, 1):
            print(f"\n处理第 {i}/{pending_merges} 个故事: {story_index}")
            print(
                f"总体进度: {completed_merges + i}/{consistent_stories} ({(completed_merges + i)/consistent_stories*100:.1f}%)"
            )

            # 获取该故事的所有 MP3 文件
            mp3_files = story_info[story_index]["mp3_files"]

            # 输出文件路径
            output_file = os.path.join(output_dir, story_index, "story.mp3")

            print(f"📝 故事 {story_index}: 合并 {len(mp3_files)} 个音频文件")

            # 执行合并
            success = merge_audio_files(mp3_files, output_file)

            if success:
                successful_count += 1
            else:
                failed_count += 1

            # 处理间隔
            if i < pending_merges:
                print("⏳ 等待 1 秒...")
                time.sleep(1)

        end_time = time.time()
        total_time = end_time - start_time

        # 保存合并日志
        save_merge_log(output_dir, stats, successful_count, failed_count)

        # 结果统计
        print(f"\n=== 🎉 合并完成 ===")
        print(f"✅ 本次成功合并: {successful_count} 个故事")
        print(f"❌ 本次合并失败: {failed_count} 个故事")
        print(f"⏭️  之前已完成: {completed_merges} 个故事")
        print(
            f"📊 总体完成: {completed_merges + successful_count}/{consistent_stories} ({(completed_merges + successful_count)/consistent_stories*100:.1f}%)"
        )
        print(f"⏱️  本次耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")

        if successful_count > 0:
            avg_time = total_time / successful_count
            print(f"📊 平均每个故事: {avg_time:.1f} 秒")

        if pending_merges > 0:
            success_rate = successful_count / pending_merges * 100
            print(f"📊 本次成功率: {success_rate:.1f}%")

        print(f"📁 输出目录: {output_dir}")
        print(f"📁 文件结构: mp3_merge/story_index/story.mp3")

        # 提醒处理不一致的故事
        if inconsistent_stories > 0:
            print(f"\n⚠️  有 {inconsistent_stories} 个故事文件不一致，无法合并")
            print(f"   请检查 synthesize_audio.py 的输出，确保所有音频文件都已生成")

        if failed_count > 0:
            print(f"\n⚠️  有 {failed_count} 个故事合并失败，可以重新运行程序重试")

    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断了程序执行")
        print(f"✅ 已成功合并: {successful_count} 个故事")
        print(f"❌ 合并失败: {failed_count} 个故事")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        print(f"✅ 已成功合并: {successful_count} 个故事")
        print(f"❌ 合并失败: {failed_count} 个故事")


if __name__ == "__main__":
    main()
