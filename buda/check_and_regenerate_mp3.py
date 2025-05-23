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
  --debug              启用调试模式，输出最详细的信息
"""

import os
import sys
import argparse
import tempfile
import subprocess
import platform
import time
from tqdm import tqdm
import concurrent.futures
import mutagen
from mutagen.mp3 import MP3
import shutil
import traceback


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

# 定义语言和对应的语音名称
VOICE_NAMES = {
    "en": "en-US-AndrewMultilingualNeural",
    "ja": "ja-JP-KeitaNeural",
    "vi": "vi-VN-NamMinhNeural",
    "ko": "ko-KR-InJoonNeural",
}


# 新增：调试日志函数
def debug_log(message, debug_mode=False):
    """输出调试日志，仅在debug_mode为True时输出"""
    if debug_mode:
        print(f"[DEBUG] {message}")


def is_mp3_valid(file_path, verbose=False, debug=False):
    """检查MP3文件是否有效"""
    # 检查文件是否存在
    if not os.path.exists(file_path):
        debug_log(f"文件不存在: {file_path}", debug)
        if verbose:
            print(f"文件不存在: {file_path}")
        return False

    # 检查文件大小是否为0
    if os.path.getsize(file_path) == 0:
        debug_log(f"文件大小为0: {file_path}", debug)
        if verbose:
            print(f"文件大小为0: {file_path}")
        return False

    # 尝试使用mutagen读取MP3文件以检查完整性
    try:
        audio = MP3(file_path)
        # 尝试访问音频属性以验证文件是否可读
        duration = audio.info.length
        if duration <= 0:
            debug_log(f"文件时长异常: {file_path}, 时长: {duration}秒", debug)
            if verbose:
                print(f"文件时长异常: {file_path}, 时长: {duration}秒")
            return False
        return True
    except Exception as e:
        debug_log(f"检查文件时出错: {file_path}, 错误: {str(e)}", debug)
        if verbose:
            print(f"检查文件时出错: {file_path}, 错误: {e}")
        return False


def find_txt_source_for_mp3(mp3_path, debug=False):
    """根据MP3文件路径找到对应的源TXT文件"""
    debug_log(f"尝试为MP3文件找到源TXT: {mp3_path}", debug)

    # MP3路径格式: <BASE_MEDIA_PATH>/multi_lang_mp3/<频道>/<视频名>/<语言>/<行号>.mp3
    # TXT路径格式: <BASE_MEDIA_PATH>/multi_lang_txt/<频道>/<语言>/<视频名>.txt

    # 从MP3路径中提取各个组件
    parts = mp3_path.split(os.sep)
    relative_path_parts = []

    debug_log(f"MP3路径分解: {parts}", debug)

    # 找到multi_lang_mp3在路径中的位置
    for i, part in enumerate(parts):
        if part == "multi_lang_mp3":
            relative_path_parts = parts[i + 1 :]
            debug_log(f"找到相对路径部分: {relative_path_parts}", debug)
            break

    if len(relative_path_parts) < 4:
        print(f"错误: 无法解析MP3路径: {mp3_path}")
        debug_log(f"路径组件不足，无法解析: {relative_path_parts}", debug)
        return None

    channel = relative_path_parts[0]
    video_name = relative_path_parts[1]
    language = relative_path_parts[2]
    line_num = os.path.splitext(relative_path_parts[3])[0]  # 去除.mp3后缀，得到行号

    debug_log(
        f"提取的组件 - 频道: {channel}, 视频: {video_name}, 语言: {language}, 行号: {line_num}",
        debug,
    )

    # 构建对应的TXT文件路径
    txt_path = os.path.join(
        BASE_MEDIA_PATH, "multi_lang_txt", channel, language, f"{video_name}.txt"
    )

    debug_log(f"构建的TXT路径: {txt_path}", debug)
    debug_log(f"TXT文件是否存在: {os.path.exists(txt_path)}", debug)

    if not os.path.exists(txt_path):
        print(f"错误: 找不到对应的TXT文件: {txt_path}")
        return None

    return {
        "txt_path": txt_path,
        "mp3_dir": os.path.dirname(mp3_path),
        "line_num": int(line_num),
        "language": language,
    }


def text_to_mp3(text, output_file, language_code, max_retries=5, debug=False):
    """使用Edge TTS将文本转换为MP3文件"""
    if not text.strip():
        print("警告: 空文本，跳过")
        return False

    voice = VOICE_NAMES.get(language_code)
    if not voice:
        print(f"错误: 不支持的语言代码 {language_code}")
        return False

    debug_log(f"准备生成MP3 - 语言: {language_code}, 声音: {voice}", debug)
    debug_log(f"文本内容: '{text}'", debug)
    debug_log(f"输出文件: {output_file}", debug)

    for attempt in range(max_retries):
        try:
            # 使用subprocess调用edge-tts命令
            cmd = [
                "edge-tts",
                "--voice",
                voice,
                "--text",
                text,
                "--write-media",
                output_file,
            ]
            debug_log(f"执行命令: {' '.join(cmd)}", debug)

            result = subprocess.run(cmd, capture_output=True, text=True)

            debug_log(f"命令返回码: {result.returncode}", debug)
            if debug:
                if result.stdout:
                    debug_log(f"命令标准输出: {result.stdout}", True)
                if result.stderr:
                    debug_log(f"命令错误输出: {result.stderr}", True)

            if result.returncode == 0:
                # 验证生成的文件是否存在且有效
                if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    print(f"语音合成成功: {output_file}")
                    return True
                else:
                    debug_log(f"命令执行成功但文件无效: {output_file}", debug)
                    if attempt < max_retries - 1:
                        print(
                            f"文件生成似乎有问题，等待2秒后重试 (尝试 {attempt+1}/{max_retries})..."
                        )
                        time.sleep(2)
                    else:
                        print(f"达到最大重试次数 ({max_retries})，无法生成有效文件")
                        return False
            else:
                print(f"语音合成失败: {result.stderr}")
                debug_log(f"完整的错误信息: {result.stderr}", debug)

                if attempt < max_retries - 1:
                    print(f"等待2秒后重试 (尝试 {attempt+1}/{max_retries})...")
                    time.sleep(2)
                else:
                    print(f"达到最大重试次数 ({max_retries})，跳过")
                    return False
        except Exception as e:
            print(f"语音合成时出错: {e}")
            debug_log(f"异常详情: {traceback.format_exc()}", debug)

            if attempt < max_retries - 1:
                print(f"等待2秒后重试 (尝试 {attempt+1}/{max_retries})...")
                time.sleep(2)
            else:
                print(f"达到最大重试次数 ({max_retries})，跳过")
                return False

    return False


def regenerate_mp3(mp3_path, verbose=False, batch_size=5, debug=False):
    """重新生成损坏的MP3文件"""
    debug_log(f"==== 开始重新生成MP3: {mp3_path} ====", debug)

    # 删除损坏的文件
    if os.path.exists(mp3_path):
        try:
            os.remove(mp3_path)
            debug_log(f"已删除损坏的文件: {mp3_path}", debug)
            if verbose:
                print(f"已删除损坏的文件: {mp3_path}")
        except Exception as e:
            print(f"删除文件时出错: {mp3_path}, 错误: {e}")
            debug_log(f"删除文件异常: {traceback.format_exc()}", debug)
            return False

    # 查找源TXT文件
    source_info = find_txt_source_for_mp3(mp3_path, debug)
    if not source_info:
        print(f"无法找到源文件信息，无法重新生成: {mp3_path}")
        return False

    txt_path = source_info["txt_path"]
    mp3_dir = source_info["mp3_dir"]
    line_num = source_info["line_num"]
    language = source_info["language"]

    debug_log(
        f"找到源信息 - TXT: {txt_path}, MP3目录: {mp3_dir}, 行号: {line_num}, 语言: {language}",
        debug,
    )

    # 读取TXT文件的特定行
    try:
        debug_log(f"尝试读取TXT文件: {txt_path}", debug)
        if not os.path.exists(txt_path):
            print(f"错误: TXT文件不存在: {txt_path}")
            return False

        with open(txt_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        debug_log(f"TXT文件总行数: {len(lines)}", debug)

        if line_num > len(lines) or line_num <= 0:
            print(f"行号超出范围: {line_num}, 文件总行数: {len(lines)}")
            return False

        # 获取需要转换的文本
        text = lines[line_num - 1].strip()
        if verbose or debug:
            print(f"从文件 {txt_path} 中提取了第 {line_num} 行: {text}")

        # 检查文本是否为空
        if not text:
            print(f"警告: 第 {line_num} 行文本为空，跳过生成")
            return False

        # 确保输出目录存在
        if not os.path.exists(mp3_dir):
            debug_log(f"创建输出目录: {mp3_dir}", debug)
            try:
                os.makedirs(mp3_dir)
                if verbose:
                    print(f"创建输出目录: {mp3_dir}")
            except Exception as e:
                print(f"创建目录时出错: {mp3_dir}, 错误: {e}")
                debug_log(f"创建目录异常: {traceback.format_exc()}", debug)
                return False

        # 生成目标MP3文件路径
        target_mp3 = os.path.join(mp3_dir, f"{line_num}.mp3")
        debug_log(f"目标MP3文件: {target_mp3}", debug)

        # 检查目录是否可写
        if not os.access(os.path.dirname(target_mp3), os.W_OK):
            print(f"错误: 目录不可写: {os.path.dirname(target_mp3)}")
            return False

        # 直接使用Edge TTS生成MP3文件
        if text_to_mp3(text, target_mp3, language, debug=debug):
            if verbose:
                print(f"成功重新生成: {target_mp3}")
            return True
        else:
            print(f"无法生成MP3文件: {target_mp3}")
            return False
    except Exception as e:
        print(f"处理源文件时出错: {e}")
        debug_log(f"异常详情: {traceback.format_exc()}", debug)
        return False


def check_directory(directory, force=False, verbose=False, batch_size=5, debug=False):
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
    debug_log(f"准备检查 {len(mp3_files)} 个MP3文件", debug)

    # 跟踪统计信息
    stats = {
        "total": len(mp3_files),
        "checked": 0,
        "valid": 0,
        "invalid": 0,
        "regenerated": 0,
        "failed": 0,
    }

    # 测试edge-tts是否正常工作
    if debug:
        print("测试edge-tts是否正常工作...")
        test_text = "This is a test."
        test_file = os.path.join(tempfile.gettempdir(), "edge_tts_test.mp3")
        test_result = text_to_mp3(test_text, test_file, "en", debug=debug)
        print(f"edge-tts测试结果: {'成功' if test_result else '失败'}")
        if os.path.exists(test_file):
            os.remove(test_file)

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
            if not is_mp3_valid(mp3_file, verbose, debug):
                result["valid"] = False
                debug_log(f"发现无效文件: {mp3_file}", debug)

                # 尝试重新生成
                if regenerate_mp3(mp3_file, verbose, batch_size, debug):
                    result["regenerated"] = True
                    debug_log(f"成功重新生成文件: {mp3_file}", debug)
                else:
                    result["error"] = "重新生成失败"
                    debug_log(f"重新生成失败: {mp3_file}", debug)

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
    # 新增：调试模式参数
    parser.add_argument(
        "--debug", action="store_true", help="启用调试模式，输出最详细的信息"
    )
    # 新增：测试模式参数，只处理少量文件
    parser.add_argument(
        "--test", action="store_true", help="测试模式，只处理前10个无效文件"
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 检查edge-tts是否已安装
    try:
        result = subprocess.run(
            ["edge-tts", "--version"], capture_output=True, text=True
        )
        print(f"已安装的edge-tts版本: {result.stdout.strip()}")

        if args.debug:
            # 显示edge-tts可用的声音列表
            voices_result = subprocess.run(
                ["edge-tts", "--list-voices"], capture_output=True, text=True
            )
            if voices_result.returncode == 0:
                print("可用的edge-tts声音列表（前5个）:")
                voice_lines = voices_result.stdout.strip().split("\n")
                for line in voice_lines[:5]:
                    print(f"  {line}")
                print(f"  ... 共 {len(voice_lines)} 个声音")
            else:
                print(f"获取声音列表失败: {voices_result.stderr}")
    except FileNotFoundError:
        print("错误: 未找到edge-tts命令。请先安装edge-tts: pip install edge-tts")
        return

    # 检查并创建必要的目录
    if not os.path.exists(args.mp3_dir):
        print(f"目录不存在: {args.mp3_dir}")
        print("正在创建目录结构...")
        try:
            os.makedirs(args.mp3_dir, exist_ok=True)
            print(f"✅ 已创建目录: {args.mp3_dir}")

            # 同时创建一些基本的子目录结构示例
            print("提示: 目录已创建，但可能为空。请确保您有相应的多语言文本文件。")
            print(
                f"文本文件应该位于: {os.path.join(BASE_MEDIA_PATH, 'multi_lang_txt')}"
            )
        except Exception as e:
            print(f"❌ 创建目录失败: {e}")
            return

    # 如果目录存在但为空，给出提示
    elif not any(
        os.path.exists(os.path.join(args.mp3_dir, item))
        for item in os.listdir(args.mp3_dir)
        if not item.startswith(".")
    ):
        print(f"⚠️  目录存在但为空: {args.mp3_dir}")
        print(
            f"请确保您有相应的多语言文本文件位于: {os.path.join(BASE_MEDIA_PATH, 'multi_lang_txt')}"
        )
        print("或者使用 generate_mp3_clips.py 脚本先生成MP3文件")

    # 如果是测试模式，只处理少量文件
    if args.test:
        test_dir = os.path.join(tempfile.gettempdir(), "mp3_regenerate_test")
        os.makedirs(test_dir, exist_ok=True)
        print(f"测试模式：使用临时目录 {test_dir}")

        # 找出前10个无效文件
        test_files = []
        for root, _, files in os.walk(args.mp3_dir):
            for file in files:
                if file.endswith(".mp3"):
                    full_path = os.path.join(root, file)
                    if not is_mp3_valid(full_path, args.verbose, args.debug):
                        test_files.append(full_path)
                        if len(test_files) >= 10:
                            break
            if len(test_files) >= 10:
                break

        print(f"找到 {len(test_files)} 个无效文件用于测试")
        for test_file in test_files:
            print(f"测试重新生成: {test_file}")
            regenerate_mp3(test_file, True, args.batch_size, True)
    else:
        # 正常模式，检查整个目录
        check_directory(
            args.mp3_dir, args.force, args.verbose, args.batch_size, args.debug
        )


if __name__ == "__main__":
    main()
