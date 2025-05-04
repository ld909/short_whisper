#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查并重新生成MP3文件脚本
=======================

此脚本用于检查生成的MP3文件是否完好，若文件大小为0或损坏则删除并重新生成。

使用方法:
python check_and_regenerate_mp3.py [选项]

选项:
  -d, --mp3_dir        MP3文件目录 (默认为generate_mp3_clips.py的输出目录)
  -f, --force          强制检查所有文件，即使之前已检查过
  -b, --batch_size     设置并发处理的批量大小
  -v, --verbose        输出详细的检查信息
"""

import os
import sys
import argparse
import tempfile
import subprocess
import platform
from tqdm import tqdm
import concurrent.futures
import mutagen
from mutagen.mp3 import MP3
import shutil


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# 获取媒体基础路径
BASE_MEDIA_PATH = get_base_media_path()
# MP3输出目录
MP3_OUTPUT_PATH = os.path.join(BASE_MEDIA_PATH, "multi_lang_mp3")


def is_mp3_valid(file_path, verbose=False):
    """检查MP3文件是否有效"""
    # 检查文件是否存在
    if not os.path.exists(file_path):
        if verbose:
            print(f"文件不存在: {file_path}")
        return False

    # 检查文件大小是否为0
    if os.path.getsize(file_path) == 0:
        if verbose:
            print(f"文件大小为0: {file_path}")
        return False

    # 尝试使用mutagen读取MP3文件以检查完整性
    try:
        audio = MP3(file_path)
        # 尝试访问音频属性以验证文件是否可读
        duration = audio.info.length
        if duration <= 0:
            if verbose:
                print(f"文件时长异常: {file_path}, 时长: {duration}秒")
            return False
        return True
    except Exception as e:
        if verbose:
            print(f"检查文件时出错: {file_path}, 错误: {e}")
        return False


def find_txt_source_for_mp3(mp3_path):
    """根据MP3文件路径找到对应的源TXT文件"""
    # MP3路径格式: <BASE_MEDIA_PATH>/multi_lang_mp3/<频道>/<视频名>/<语言>/<行号>.mp3
    # TXT路径格式: <BASE_MEDIA_PATH>/multi_lang_txt_split/<频道>/<语言>/<视频名>.txt

    # 从MP3路径中提取各个组件
    parts = mp3_path.split(os.sep)
    relative_path_parts = []

    # 找到multi_lang_mp3在路径中的位置
    for i, part in enumerate(parts):
        if part == "multi_lang_mp3":
            relative_path_parts = parts[i + 1 :]
            break

    if len(relative_path_parts) < 4:
        print(f"无法解析MP3路径: {mp3_path}")
        return None

    channel = relative_path_parts[0]
    video_name = relative_path_parts[1]
    language = relative_path_parts[2]
    line_num = os.path.splitext(relative_path_parts[3])[0]  # 去除.mp3后缀，得到行号

    # 构建对应的TXT文件路径
    txt_path = os.path.join(
        BASE_MEDIA_PATH, "multi_lang_txt_split", channel, language, f"{video_name}.txt"
    )

    if not os.path.exists(txt_path):
        print(f"找不到对应的TXT文件: {txt_path}")
        return None

    return {
        "txt_path": txt_path,
        "mp3_dir": os.path.dirname(mp3_path),
        "line_num": int(line_num),
        "language": language,
    }


def regenerate_mp3(mp3_path, verbose=False, batch_size=5):
    """重新生成损坏的MP3文件"""
    # 删除损坏的文件
    if os.path.exists(mp3_path):
        try:
            os.remove(mp3_path)
            if verbose:
                print(f"已删除损坏的文件: {mp3_path}")
        except Exception as e:
            print(f"删除文件时出错: {mp3_path}, 错误: {e}")
            return False

    # 查找源TXT文件
    source_info = find_txt_source_for_mp3(mp3_path)
    if not source_info:
        print(f"无法找到源文件信息，无法重新生成: {mp3_path}")
        return False

    txt_path = source_info["txt_path"]
    mp3_dir = source_info["mp3_dir"]
    line_num = source_info["line_num"]
    language = source_info["language"]

    # 读取TXT文件的特定行
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if line_num > len(lines) or line_num <= 0:
            print(f"行号超出范围: {line_num}, 文件总行数: {len(lines)}")
            return False

        # 创建临时TXT文件，只包含需要重新生成的那一行
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".txt", delete=False
        ) as temp:
            temp_txt_path = temp.name
            temp.write(lines[line_num - 1])

        # 调用generate_mp3_clips.py生成单个MP3文件
        cmd = [
            sys.executable,
            "generate_mp3_clips.py",
            "-s",
            temp_txt_path,
            "-o",
            mp3_dir,
            "-l",
            language,
            "-b",
            str(batch_size),
            "-f",  # 强制重新生成
        ]

        if verbose:
            print(f"执行命令: {' '.join(cmd)}")

        # 执行命令
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # 重命名生成的MP3文件为正确的行号
                new_mp3 = os.path.join(
                    mp3_dir, "1.mp3"
                )  # 临时文件只有一行，所以生成的是1.mp3
                target_mp3 = os.path.join(mp3_dir, f"{line_num}.mp3")

                if os.path.exists(new_mp3):
                    shutil.move(new_mp3, target_mp3)
                    if verbose:
                        print(f"成功重新生成: {target_mp3}")

                    # 删除临时文件
                    if os.path.exists(temp_txt_path):
                        os.remove(temp_txt_path)

                    return True
                else:
                    print(f"未找到新生成的MP3文件: {new_mp3}")
            else:
                print(f"重新生成时出错，返回码: {result.returncode}")
                print(f"标准输出: {result.stdout}")
                print(f"标准错误: {result.stderr}")
        except Exception as e:
            print(f"执行重新生成命令时出错: {e}")

        # 删除临时文件
        if os.path.exists(temp_txt_path):
            os.remove(temp_txt_path)

        return False
    except Exception as e:
        print(f"处理源文件时出错: {e}")
        return False


def check_directory(directory, force=False, verbose=False, batch_size=5):
    """检查目录中的所有MP3文件"""
    if not os.path.exists(directory):
        print(f"目录不存在: {directory}")
        return

    # 获取所有MP3文件
    mp3_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".mp3"):
                mp3_files.append(os.path.join(root, file))

    if not mp3_files:
        print(f"在目录 {directory} 中未找到MP3文件")
        return

    print(f"发现 {len(mp3_files)} 个MP3文件待检查")

    # 跟踪统计信息
    stats = {
        "total": len(mp3_files),
        "checked": 0,
        "valid": 0,
        "invalid": 0,
        "regenerated": 0,
        "failed": 0,
    }

    # 创建进度条
    with tqdm(total=len(mp3_files), desc="检查MP3文件") as pbar:
        # 定义检查和修复单个文件的函数
        def process_file(mp3_file):
            result = {
                "file": mp3_file,
                "valid": True,
                "regenerated": False,
                "error": None,
            }

            # 检查文件是否有效
            if not is_mp3_valid(mp3_file, verbose):
                result["valid"] = False

                # 尝试重新生成
                if regenerate_mp3(mp3_file, verbose, batch_size):
                    result["regenerated"] = True
                else:
                    result["error"] = "重新生成失败"

            return result

        # 并发处理文件
        with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
            for result in executor.map(process_file, mp3_files):
                stats["checked"] += 1

                if result["valid"]:
                    stats["valid"] += 1
                else:
                    stats["invalid"] += 1

                    if result["regenerated"]:
                        stats["regenerated"] += 1
                    else:
                        stats["failed"] += 1
                        if verbose:
                            print(
                                f"无法修复文件: {result['file']}, 错误: {result['error']}"
                            )

                pbar.update(1)

    # 输出统计结果
    print("\n检查完成，统计结果:")
    print(f"总文件数: {stats['total']}")
    print(f"有效文件数: {stats['valid']}")
    print(f"无效文件数: {stats['invalid']}")
    print(f"已重新生成: {stats['regenerated']}")
    print(f"修复失败: {stats['failed']}")


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="检查并重新生成损坏的MP3文件")

    # 添加命令行参数
    parser.add_argument(
        "-d",
        "--mp3_dir",
        type=str,
        default=MP3_OUTPUT_PATH,
        help=f"MP3文件目录 (默认: {MP3_OUTPUT_PATH})",
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="强制检查所有文件，即使之前已检查过"
    )
    parser.add_argument(
        "-b", "--batch_size", type=int, default=5, help="并发处理的批量大小，默认为5"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="输出详细的检查信息"
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 检查目录中的MP3文件
    check_directory(args.mp3_dir, args.force, args.verbose, args.batch_size)


if __name__ == "__main__":
    main()
