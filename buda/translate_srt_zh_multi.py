"""
多语言字幕/文本翻译工具

功能说明:
此脚本用于将中文SRT字幕文件或纯文本文件批量翻译成多种语言（英语、日语、越南语、韩语）。
脚本使用OpenAI API进行翻译，特别针对佛教内容优化，支持并发处理和断点续传。

输入目录:
- SRT模式: [媒体路径]/zh_subtitle_split_txt/[频道名称]/
- TXT模式: [媒体路径]/pure_sentence/[频道名称]/

输出目录:
- SRT模式: [媒体路径]/multi_lang_txt/[频道名称]/[语言代码]/ (纯文本格式，每行一句话)
- TXT模式: [媒体路径]/multi_lang_txt/[频道名称]/[语言代码]/

使用方法:
1. 基本使用: python translate_srt_zh_multi.py
2. 指定目标语言: python translate_srt_zh_multi.py -l English Japanese
3. 强制重新翻译: python translate_srt_zh_multi.py -f
4. 设置批处理大小: python translate_srt_zh_multi.py -b 30
5. 单文件处理: python translate_srt_zh_multi.py -s /path/to/file.txt
6. TXT模式: python translate_srt_zh_multi.py --txt_mode

注意:
- 需要设置环境变量UNI_API_KEY以提供OpenAI API密钥
- 脚本支持断点续传，中断后可从上次停止的位置继续翻译
"""

import os
import re
import time
import argparse
import sys
import platform
from openai import OpenAI
import glob
import concurrent.futures
from threading import Lock
from tqdm import tqdm


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# 获取媒体基础路径
BASE_MEDIA_PATH = get_base_media_path()
# 输入TXT目录
INPUT_SRT_PATH = os.path.join(BASE_MEDIA_PATH, "zh_subtitle_split_txt")


def setup_openai_client():
    """设置OpenAI客户端并验证API密钥"""
    api_key = os.environ.get("UNI_API_KEY")

    if not api_key:
        print("错误: 未找到OpenAI API密钥")
        print("请设置环境变量UNI_API_KEY或在脚本中提供API密钥")
        print("例如: export UNI_API_KEY='your-api-key'")
        sys.exit(1)

    try:
        client = OpenAI(base_url="https://api.uniapi.io/v1", api_key=api_key)
        return client
    except Exception as e:
        print(f"初始化OpenAI客户端时出错: {e}")
        sys.exit(1)


# 初始化OpenAI客户端
client = None  # 将在main函数中初始化

# 定义支持的语言列表
LANGUAGES = ["English", "Japanese", "Vietnamese", "Korean"]
LANGUAGE_CODES = {"English": "en", "Japanese": "ja", "Vietnamese": "vi", "Korean": "ko"}


def parse_srt(file_path):
    """解析TXT文件，返回文本条目列表"""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        entries = []
        for i, line in enumerate(lines):
            text = line.strip()
            if text:  # 只有非空行才处理
                entries.append(
                    {
                        "index": str(i + 1),  # 为每行分配索引号
                        "timestamp": "00:00:00,000 --> 00:00:00,000",  # 虚拟时间戳
                        "text": text,
                    }
                )

        return entries
    except UnicodeDecodeError:
        print("错误: 文件编码错误，请确保文件是UTF-8编码")
        sys.exit(1)
    except Exception as e:
        print(f"解析TXT文件时出错: {e}")
        sys.exit(1)


def translate_text(text, target_language="English", max_retries=3):
    """使用OpenAI的GPT模型翻译文本，失败时自动重试"""
    if not text.strip():
        return ""  # 如果文本为空，则直接返回空字符串

    # 检测是否为中文文本（如果是中文且目标语言不是中文，则需要翻译）
    is_chinese = any("\u4e00" <= char <= "\u9fff" for char in text)
    need_translation = is_chinese and target_language != "Chinese"

    if not need_translation:
        return text  # 如果不需要翻译，直接返回原文

    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model="gpt-4.1-mini",
                max_tokens=1000,
                messages=[
                    {
                        "role": "system",
                        "content": f"你是一个翻译大师，佛学大师，佛教专家。精通佛教各种术语在不同文化中对应的词汇，我需要你将中文佛教内容翻译为{target_language}，直接返回翻译后的结果，不要夹带其他内容,返回结果不要出现中文，只能出现{target_language}。不要以翻译后这样的内容开头作为返回。",
                    },
                    {"role": "user", "content": text},
                ],
            )
            result = completion.choices[0].message.content
            # 清理翻译结果中的空行
            result = "\n".join([line for line in result.split("\n") if line.strip()])
            return result
        except Exception as e:
            print(f"翻译出错 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("等待2秒后重试...")
                time.sleep(2)  # 添加延迟，避免过快请求
            else:
                print(f"达到最大重试次数 ({max_retries})，返回原文")
                return text  # 如果所有尝试都失败，返回原文


def check_progress(output_file):
    """检查输出文件中已翻译的条目数量"""
    if not os.path.exists(output_file):
        return 0

    try:
        with open(output_file, "r", encoding="utf-8") as file:
            content = file.read()

        # 计算已翻译的条目数
        # 每三行为一个条目：索引行、时间戳行、翻译内容行
        pattern = r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}\s-->\s\d{2}:\d{2}:\d{2},\d{3})\n"
        matches = re.findall(pattern, content)
        return len(matches)
    except Exception as e:
        print(f"检查翻译进度时出错: {e}")
        return 0


def translate_txt_file_concurrent(
    input_file, output_file, target_language="English", batch_size=20
):
    """并发翻译整个TXT文件，保持文本顺序并即时写入输出文件（真正并发批量处理）"""
    entries = parse_srt(input_file)

    if not entries:
        print("错误: 未解析到任何文本条目")
        return False

    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")

    # 检查是否有已翻译的进度
    already_translated = check_txt_progress(output_file)
    print(f"检测到已翻译 {already_translated}/{len(entries)} 条文本")

    # 如果所有条目都已翻译完成，直接返回
    if already_translated >= len(entries):
        print("所有文本都已翻译完成，无需重新翻译")
        return True

    # 确定从哪个索引开始翻译
    start_index = already_translated
    total_entries = len(entries)

    print(f"从第 {start_index+1} 条开始翻译，共 {total_entries} 条文本...")

    # 确定写入模式：如果已有翻译内容，追加模式；否则，写入模式
    write_mode = "a" if already_translated > 0 else "w"

    def translate_entry(entry):
        """翻译单个文本条目的函数（不带索引）"""
        try:
            original_text = entry["text"]
            print(f"翻译前: {original_text}")
            translated_text = translate_text(
                original_text, target_language, max_retries=3
            )
            print(f"翻译后: {translated_text}")
            return translated_text
        except Exception as e:
            print(f"翻译文本时出错: {e}")
            return entry["text"]  # 出错时返回原文

    try:
        with open(output_file, write_mode, encoding="utf-8") as file:
            with tqdm(total=total_entries - start_index, desc="翻译进度") as pbar:
                for batch_start in range(start_index, total_entries, batch_size):
                    batch_end = min(batch_start + batch_size, total_entries)
                    batch_entries = entries[batch_start:batch_end]
                    # 并发翻译本批次
                    with concurrent.futures.ThreadPoolExecutor(
                        max_workers=batch_size
                    ) as executor:
                        results = list(executor.map(translate_entry, batch_entries))
                    # 按顺序写入本批次
                    for idx, translated_text in enumerate(results):
                        # 直接写入翻译后的文本，每行一句话
                        file.write(f"{translated_text}\n")
                        file.flush()
                        os.fsync(file.fileno())
                        print(f"已写入第 {batch_start + idx + 1} 条文本")
                        pbar.update(1)
        print(f"翻译完成! 所有内容已保存到 {output_file}")
        return True
    except KeyboardInterrupt:
        print("\n翻译被用户中断")
        print(f"已翻译并保存部分内容，下次可继续从断点处翻译")
        return False
    except Exception as e:
        print(f"翻译过程中出错: {e}")
        print(f"已翻译并保存部分内容，下次可继续从断点处翻译")
        return False


def process_all_channels(languages=None, force=False, batch_size=20, check_only=False):
    """处理zh_subtitle_split_txt目录下的所有频道和TXT文件"""
    if languages is None:
        languages = LANGUAGES

    # 检查输入路径是否存在
    if not os.path.exists(INPUT_SRT_PATH):
        print(f"错误: 输入路径 '{INPUT_SRT_PATH}' 不存在")
        return

    # 获取所有频道目录
    channels = [
        d
        for d in os.listdir(INPUT_SRT_PATH)
        if os.path.isdir(os.path.join(INPUT_SRT_PATH, d)) and not d.startswith(".")
    ]

    if not channels:
        print(f"在 '{INPUT_SRT_PATH}' 中未找到任何频道目录")
        return

    print(f"找到 {len(channels)} 个频道目录")

    for channel in channels:
        channel_input_path = os.path.join(INPUT_SRT_PATH, channel)

        # 获取当前频道中的所有TXT文件，过滤掉点开头的文件
        txt_files = [
            f
            for f in os.listdir(channel_input_path)
            if f.endswith(".txt") and not f.startswith(".")
        ]

        if not txt_files:
            print(f"在频道 '{channel}' 中未找到任何TXT文件，跳过")
            continue

        print(f"\n处理频道: {channel}，找到 {len(txt_files)} 个TXT文件")

        for language in languages:
            # 为每种语言创建输出目录
            language_output_path = os.path.join(
                BASE_MEDIA_PATH,
                "multi_lang_txt",
                channel,
                LANGUAGE_CODES[language],
            )

            if not os.path.exists(language_output_path):
                os.makedirs(language_output_path)
                print(f"创建输出目录: {language_output_path}")

            print(f"\n开始为频道 {channel} 翻译为 {language}...")

            for txt_file in txt_files:
                input_file_path = os.path.join(channel_input_path, txt_file)
                output_file_path = os.path.join(language_output_path, txt_file)

                print(f"\n处理文件: {txt_file}")
                print(f"从 {input_file_path}")
                print(f"到 {output_file_path}")

                # 如果强制重新翻译且输出文件存在，则删除输出文件
                if force and os.path.exists(output_file_path):
                    os.remove(output_file_path)
                    print(f"已删除现有输出文件 '{output_file_path}'，将重新翻译")

                # 使用并发翻译文件
                success = translate_txt_file_concurrent(
                    input_file_path, output_file_path, language, batch_size
                )

                if success:
                    print(f"成功完成 {txt_file} 到 {language} 的翻译!")
                else:
                    print(
                        f"{txt_file} 到 {language} 的翻译未完全完成，将继续下一个文件"
                    )


def check_txt_progress(output_file):
    """检查txt输出文件中已翻译的行数"""
    if not os.path.exists(output_file):
        return 0
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except Exception as e:
        print(f"检查txt翻译进度时出错: {e}")
        return 0


def translate_txt_files_multi_lang(languages=None, force=False, batch_size=20):
    """
    批量翻译pure_sentence下所有频道的所有txt文件为多语言，输出到multi_lang_txt，支持断点续传
    """
    if languages is None:
        languages = LANGUAGES
    input_base = os.path.join(BASE_MEDIA_PATH, "pure_sentence")
    output_base = os.path.join(BASE_MEDIA_PATH, "multi_lang_txt")
    if not os.path.exists(input_base):
        print(f"错误: 输入目录不存在: {input_base}")
        return
    channels = [
        d
        for d in os.listdir(input_base)
        if os.path.isdir(os.path.join(input_base, d)) and not d.startswith(".")
    ]
    print(f"找到 {len(channels)} 个频道目录")
    for channel in channels:
        input_channel_dir = os.path.join(input_base, channel)
        txt_files = [
            f
            for f in os.listdir(input_channel_dir)
            if f.endswith(".txt") and not f.startswith(".")
        ]
        print(f"频道 {channel} 下找到 {len(txt_files)} 个txt文件")
        for language in languages:
            lang_code = LANGUAGE_CODES[language]
            output_channel_dir = os.path.join(output_base, channel, lang_code)
            if not os.path.exists(output_channel_dir):
                os.makedirs(output_channel_dir)
                print(f"创建输出目录: {output_channel_dir}")
            print(f"\n开始为频道 {channel} 翻译为 {language}...")
            for txt_file in txt_files:
                input_file = os.path.join(input_channel_dir, txt_file)
                output_file = os.path.join(output_channel_dir, txt_file)
                print(f"\n处理文件: {txt_file}")
                print(f"从 {input_file}")
                print(f"到 {output_file}")
                if force and os.path.exists(output_file):
                    os.remove(output_file)
                    print(f"已删除现有输出文件 '{output_file}'，将重新翻译")
                # 断点续传：统计已翻译行数
                already_translated = check_txt_progress(output_file)
                print(f"检测到已翻译 {already_translated} 行")
                # 读取所有行
                with open(input_file, "r", encoding="utf-8") as fin:
                    lines = [line for line in fin.readlines() if line.strip()]
                total_lines = len(lines)
                print(f"文件包含 {total_lines} 行有效内容")
                if already_translated >= total_lines:
                    print("所有行都已翻译完成，无需重新翻译")
                    continue

                write_mode = "a" if already_translated > 0 else "w"

                # 为翻译单行文本定义一个函数
                def translate_line(line_info):
                    idx, line = line_info
                    src_line = line.rstrip("\n")
                    # 跳过空行
                    if not src_line.strip():
                        print(f"跳过第 {idx+1}/{total_lines} 行: [空行]")
                        return idx, ""  # 返回空字符串，将在写入逻辑中处理
                    print(f"正在翻译第 {idx+1}/{total_lines} 行: {src_line}")
                    translated = translate_text(src_line, language)
                    # 确保翻译结果不是空字符串
                    if not translated.strip():
                        translated = src_line  # 如果翻译结果为空，使用原文
                    print(f"翻译后: {translated}")
                    return idx, translated

                try:
                    with open(output_file, write_mode, encoding="utf-8") as fout:
                        with tqdm(
                            total=total_lines - already_translated, desc="翻译进度"
                        ) as pbar:
                            # 从上次翻译结束的位置开始，批量处理
                            for batch_start in range(
                                already_translated, total_lines, batch_size
                            ):
                                batch_end = min(batch_start + batch_size, total_lines)
                                batch_lines = [
                                    (i, lines[i]) for i in range(batch_start, batch_end)
                                ]

                                # 并发翻译本批次
                                with concurrent.futures.ThreadPoolExecutor(
                                    max_workers=batch_size
                                ) as executor:
                                    results = list(
                                        executor.map(translate_line, batch_lines)
                                    )

                                # 按顺序写入本批次
                                for idx, translated_text in sorted(
                                    results
                                ):  # 确保按原始顺序写入
                                    # 跳过空行，不写入文件
                                    if not translated_text.strip():
                                        print(f"跳过写入第 {idx+1} 行 (空行)")
                                        pbar.update(1)
                                        continue
                                    fout.write(translated_text + "\n")
                                    fout.flush()
                                    os.fsync(fout.fileno())
                                    print(f"已写入第 {idx+1} 行")
                                    pbar.update(1)

                    print(f"翻译完成! 所有内容已保存到 {output_file}")
                except KeyboardInterrupt:
                    print("\n翻译被用户中断")
                    print(f"已翻译并保存部分内容，下次可继续从断点处翻译")
                except Exception as e:
                    print(f"翻译过程中出错: {e}")
                    print(f"已翻译并保存部分内容，下次可继续从断点处翻译")


def main():
    global client

    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description="使用OpenAI GPT模型将中文SRT字幕文件翻译为多种语言"
    )

    # 添加命令行参数
    parser.add_argument(
        "-l",
        "--languages",
        nargs="+",
        default=LANGUAGES,
        help=f"目标语言列表 (默认: {' '.join(LANGUAGES)})",
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="强制重新翻译，忽略已有翻译进度"
    )
    parser.add_argument(
        "-b",
        "--batch_size",
        type=int,
        default=10,
        help="并发处理的批量大小，默认为20",
    )
    parser.add_argument(
        "-s", "--single_file", type=str, help="指定单独处理一个SRT文件路径"
    )
    parser.add_argument(
        "--txt_mode",
        action="store_true",
        help="处理pure_sentence下所有txt批量翻译为多语言txt",
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 设置OpenAI客户端
    client = setup_openai_client()

    if args.txt_mode:
        translate_txt_files_multi_lang(args.languages, args.force, args.batch_size)
        return

    # 处理单个文件模式
    if args.single_file:
        if not os.path.exists(args.single_file):
            print(f"错误: 指定的文件 '{args.single_file}' 不存在")
            return

        # 提取文件名和目录
        file_dir = os.path.dirname(args.single_file)
        file_name = os.path.basename(args.single_file)

        # 确定输出目录
        channel = os.path.basename(os.path.dirname(args.single_file))

        for language in args.languages:
            output_dir = os.path.join(
                BASE_MEDIA_PATH,
                "multi_lang_txt",
                channel,
                LANGUAGE_CODES[language],
            )

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            output_file = os.path.join(output_dir, file_name)

            print(f"\n处理单个文件: {file_name}")
            print(f"从 {args.single_file}")
            print(f"到 {output_file}")

            # 如果强制重新翻译
            if args.force and os.path.exists(output_file):
                os.remove(output_file)
                print(f"已删除现有输出文件 '{output_file}'，将重新翻译")

            success = translate_txt_file_concurrent(
                args.single_file, output_file, language, args.batch_size
            )

            if success:
                print(f"成功完成 {file_name} 到 {language} 的翻译!")
            else:
                print(f"{file_name} 到 {language} 的翻译未完全完成")
    else:
        # 处理所有频道和SRT文件
        process_all_channels(args.languages, args.force, args.batch_size)


if __name__ == "__main__":
    main()
