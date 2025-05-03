"""
多语言文本句子拆分工具

功能说明:
此脚本用于处理已翻译的多语种TXT文件，将每行可能包含的多个句子拆分成每句一行的格式。
脚本会检测不同语言的句子结束标点，对文本进行合理的分割。

输入目录:
- [媒体路径]/multi_lang_txt/[频道名称]/[语言代码]/

输出目录:
- [媒体路径]/multi_lang_txt_split/[频道名称]/[语言代码]/

使用方法:
1. 基本使用: python split_sentences_multi_lang.py
2. 指定目标语言: python split_sentences_multi_lang.py -l English Japanese
3. 强制重新处理: python split_sentences_multi_lang.py -f
4. 单文件处理: python split_sentences_multi_lang.py -s /path/to/file.txt
"""

import os
import re
import argparse
import platform
import glob
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
INPUT_TXT_PATH = os.path.join(BASE_MEDIA_PATH, "multi_lang_txt")
# 输出TXT目录
OUTPUT_TXT_PATH = os.path.join(BASE_MEDIA_PATH, "multi_lang_txt_split")

# 定义支持的语言列表
LANGUAGES = ["English", "Japanese", "Vietnamese", "Korean"]
LANGUAGE_CODES = {"English": "en", "Japanese": "ja", "Vietnamese": "vi", "Korean": "ko"}

# 调试模式标志
DEBUG_MODE = False

# 各语言句子结束标点
SENTENCE_ENDINGS = {
    "en": r"[.!?]",  # 英语: 句号、感叹号、问号
    "ja": r"[。！？]",  # 日语: 句号、感叹号、问号
    "vi": r"[.!?]",  # 越南语: 句号、感叹号、问号
    "ko": r"[.!?。！？]",  # 韩语: 可能使用英文或中日文标点
}


def split_sentences(text, lang_code):
    """
    根据语言特定的句子结束标点，将文本拆分为多个句子

    Args:
        text: 要拆分的文本
        lang_code: 语言代码 (en, ja, vi, ko)

    Returns:
        list: 拆分后的句子列表
    """
    global DEBUG_MODE

    # 移除文本开头和结尾的空白字符
    text = text.strip()

    # 如果文本为空，返回空列表
    if not text:
        return []

    # 获取语言对应的句子结束标点模式
    ending_pattern = SENTENCE_ENDINGS.get(lang_code, r"[.!?]")

    # 根据语言选择不同的正则表达式模式
    if lang_code == "ja":
        # 日语句子拆分：句号、感叹号或问号，考虑可能的引号、括号、空格等
        pattern = rf"([。！？]+)(?=[^。！？]|$)"
    elif lang_code == "ko" and "。" in ending_pattern:
        # 韩语也可能使用日文句号
        pattern = rf"(?<!\.)([.!?])(?!\.)(?=\s|$)|([。！？]+)(?=[^。！？]|$)"
    else:
        # 其他语言：句号、感叹号或问号，后面跟着空格或行尾，但不分割省略号
        pattern = rf"(?<!\.)({ending_pattern})(?!\.)(?=\s|$)"

    if DEBUG_MODE:
        print(f"语言: {lang_code}, 使用正则表达式: {pattern}")
        print(f"处理文本: {text[:50]}..." if len(text) > 50 else f"处理文本: {text}")

    # 拆分文本
    parts = re.split(pattern, text)

    if DEBUG_MODE:
        print(f"拆分后部分: {parts}")

    # 过滤掉None值（正则表达式中的捕获组可能导致None值）
    parts = [part for part in parts if part is not None]

    # 初始化结果列表和当前句子
    sentences = []
    current_sentence = ""

    # 处理拆分后的部分，重新组合句子和标点
    if lang_code == "ja" or (lang_code == "ko" and "。" in ending_pattern):
        # 日语和包含日文标点的韩语处理
        for i in range(0, len(parts), 2):
            if i < len(parts):
                current_sentence = parts[i]

                # 如果有对应的句子结束标点，添加到当前句子
                if i + 1 < len(parts):
                    current_sentence += parts[i + 1]
                    sentences.append(current_sentence.strip())
                else:
                    # 最后一部分如果不为空，添加到结果
                    if current_sentence.strip():
                        sentences.append(current_sentence.strip())
    else:
        # 其他语言处理（原有逻辑）
        for i, part in enumerate(parts):
            current_sentence += part

            # 如果这部分是句子结束标点，完成当前句子并添加到结果列表
            if i % 2 == 1:
                sentences.append(current_sentence.strip())
                current_sentence = ""

        # 添加最后可能的不完整句子
        if current_sentence:
            sentences.append(current_sentence.strip())

    # 过滤掉空句子
    return [s for s in sentences if s]


def process_txt_file(input_file, output_file, lang_code):
    """
    处理单个TXT文件，拆分每行中的多个句子

    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
        lang_code: 语言代码

    Returns:
        bool: 处理是否成功
    """
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 读取输入文件
        with open(input_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 处理每一行，拆分句子
        processed_lines = []
        for line_idx, line in enumerate(lines, 1):
            # 移除换行符和首尾空格
            line = line.strip()
            if line:
                try:
                    # 拆分句子
                    sentences = split_sentences(line, lang_code)
                    processed_lines.extend(sentences)
                except Exception as e:
                    print(f"处理第 {line_idx} 行时出错: {e}")
                    print(
                        f"行内容: {line[:50]}..."
                        if len(line) > 50
                        else f"行内容: {line}"
                    )
                    processed_lines.append(line)  # 添加未处理的原始行
            else:
                # 保留空行
                processed_lines.append("")

        # 写入输出文件
        with open(output_file, "w", encoding="utf-8") as f:
            for line in processed_lines:
                f.write(line + "\n")

        return True

    except Exception as e:
        print(f"处理文件 {input_file} 时出错: {e}")
        import traceback

        traceback.print_exc()
        return False


def process_all_channels(languages=None, force=False):
    """
    处理multi_lang_txt目录下的所有频道和TXT文件

    Args:
        languages: 要处理的语言列表，默认为所有支持的语言
        force: 是否强制重新处理已存在的文件
    """
    if languages is None:
        languages = LANGUAGES

    # 检查输入路径是否存在
    if not os.path.exists(INPUT_TXT_PATH):
        print(f"错误: 输入路径 '{INPUT_TXT_PATH}' 不存在")
        return

    # 获取所有频道目录
    channels = [
        d
        for d in os.listdir(INPUT_TXT_PATH)
        if os.path.isdir(os.path.join(INPUT_TXT_PATH, d))
    ]

    if not channels:
        print(f"在 '{INPUT_TXT_PATH}' 中未找到任何频道目录")
        return

    print(f"找到 {len(channels)} 个频道目录")

    for channel in channels:
        channel_input_path = os.path.join(INPUT_TXT_PATH, channel)

        for language in languages:
            lang_code = LANGUAGE_CODES[language]
            language_input_path = os.path.join(channel_input_path, lang_code)

            # 检查语言目录是否存在
            if not os.path.exists(language_input_path):
                print(f"语言目录不存在: {language_input_path}，跳过")
                continue

            # 获取所有TXT文件
            txt_files = glob.glob(os.path.join(language_input_path, "*.txt"))

            if not txt_files:
                print(f"在 {language_input_path} 中未找到任何TXT文件，跳过")
                continue

            print(
                f"\n处理频道: {channel}，语言: {language}，找到 {len(txt_files)} 个TXT文件"
            )

            # 创建输出目录
            language_output_path = os.path.join(OUTPUT_TXT_PATH, channel, lang_code)

            if not os.path.exists(language_output_path):
                os.makedirs(language_output_path)
                print(f"创建输出目录: {language_output_path}")

            # 处理每个TXT文件
            for txt_file in tqdm(txt_files, desc=f"处理 {language} 文件"):
                file_name = os.path.basename(txt_file)
                output_file = os.path.join(language_output_path, file_name)

                # 如果输出文件已存在且不强制重新处理，则跳过
                if os.path.exists(output_file) and not force:
                    print(f"文件 {file_name} 已存在，跳过 (使用 -f 强制重新处理)")
                    continue

                # 处理文件
                success = process_txt_file(txt_file, output_file, lang_code)

                if success:
                    print(f"成功处理文件: {file_name}")
                else:
                    print(f"处理文件失败: {file_name}")


def process_single_file(file_path, force=False):
    """
    处理单个TXT文件

    Args:
        file_path: 文件路径
        force: 是否强制重新处理
    """
    if not os.path.exists(file_path):
        print(f"错误: 文件 '{file_path}' 不存在")
        return

    # 从文件路径提取频道和语言代码
    file_dir = os.path.dirname(file_path)
    parts = file_dir.split(os.sep)

    # 尝试找到语言代码和频道名称
    lang_code = None
    channel = None

    for code in LANGUAGE_CODES.values():
        if code in parts:
            lang_code = code
            idx = parts.index(code)
            if idx > 0:
                channel = parts[idx - 1]
            break

    if not lang_code or not channel:
        print(f"错误: 无法从路径确定语言代码和频道: {file_path}")
        return

    file_name = os.path.basename(file_path)
    output_file = os.path.join(OUTPUT_TXT_PATH, channel, lang_code, file_name)

    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 如果输出文件已存在且不强制重新处理，则跳过
    if os.path.exists(output_file) and not force:
        print(f"文件 {file_name} 已存在，跳过 (使用 -f 强制重新处理)")
        return

    # 处理文件
    success = process_txt_file(file_path, output_file, lang_code)

    if success:
        print(f"成功处理文件: {file_name}")
    else:
        print(f"处理文件失败: {file_name}")


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description="将多语种TXT文件中的句子拆分为每句一行"
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
        "-f", "--force", action="store_true", help="强制重新处理，覆盖已有文件"
    )
    parser.add_argument(
        "-s", "--single_file", type=str, help="指定单独处理一个TXT文件路径"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="启用调试模式，显示详细处理信息"
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 设置调试模式
    global DEBUG_MODE
    DEBUG_MODE = args.debug

    if DEBUG_MODE:
        print("调试模式已启用")
        print(f"处理语言: {args.languages}")
        if args.single_file:
            print(f"处理单个文件: {args.single_file}")

    # 处理单个文件模式
    if args.single_file:
        process_single_file(args.single_file, args.force)
    else:
        # 处理所有频道和TXT文件
        process_all_channels(args.languages, args.force)


if __name__ == "__main__":
    main()
