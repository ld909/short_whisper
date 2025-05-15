"""
中文字幕句子拆分工具

功能说明:
此脚本用于处理中文SRT字幕文件，将每个字幕行的文本拆分成句子，如果句子长度超过260字符，
则使用GPT-4.1-mini对标点符号进行修正，然后再次拆分成句子。

输入目录:
- [媒体路径]/zh_srt_tyro_fix/[频道名称]/

输出目录:
- [媒体路径]/zh_subtitle_split_txt/[频道名称]/

使用方法:
1. 基本使用: python split_sentences_zh_srt.py
2. 强制重新处理: python split_sentences_zh_srt.py -f
3. 单文件处理: python split_sentences_zh_srt.py -s /path/to/file.srt
"""

import os
import re
import sys
import argparse
import platform
import glob
from tqdm import tqdm
from openai import OpenAI
import concurrent.futures
from threading import Lock


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# 获取媒体基础路径
BASE_MEDIA_PATH = get_base_media_path()
# 输入SRT目录 (来自fix_tyro.py的输出)
INPUT_SRT_PATH = os.path.join(BASE_MEDIA_PATH, "zh_srt_tyro_fix")
# 输出TXT目录
OUTPUT_TXT_PATH = os.path.join(BASE_MEDIA_PATH, "zh_subtitle_split_txt")

# 调试模式标志
DEBUG_MODE = False
# 中文句子结束标点
SENTENCE_ENDINGS = r"[。！？]"
# 最大句子长度限制
MAX_SENTENCE_LENGTH = 200


def read_srt_file(file_path):
    """读取SRT文件并返回内容"""
    with open(file_path, "r", encoding="utf-8") as f:
        srt_content = f.read()
    return srt_content


def parse_srt_with_re(srt_content):
    """使用正则表达式解析SRT字幕内容"""
    # 定义一个正则表达式来匹配字幕块：序号、时间戳和字幕文本
    pattern = re.compile(
        r"(\d+)\s+(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\s+(.*?)(?=\n\n|\Z)",
        re.DOTALL,
    )

    matches = pattern.findall(srt_content)
    subtitles = []

    for match in matches:
        index, start_time, end_time, subtitle = match
        subtitle = subtitle.replace("\n", " ").strip()
        # 移除「」符号
        subtitle = subtitle.replace("「", "").replace("」", "")
        subtitles.append(
            {
                "index": int(index),
                "start_time": start_time,
                "end_time": end_time,
                "text": subtitle,
            }
        )

    return subtitles


def clean_text(text):
    """清理文本，移除「」符号"""
    return text.replace("「", "").replace("」", "")


def split_sentences(text):
    """
    根据中文句子结束标点，将文本拆分为多个句子

    Args:
        text: 要拆分的文本

    Returns:
        list: 拆分后的句子列表
    """
    global DEBUG_MODE

    # 移除「」符号
    text = clean_text(text)

    # 替换文本中的所有换行符为空格
    text = re.sub(r"\s+", " ", text)

    # 移除文本开头和结尾的空白字符
    text = text.strip()

    # 如果文本为空，返回空列表
    if not text:
        return []

    # 改进中文句子拆分模式，确保每个句子结束标点都成为分隔点
    sentences = []
    current = ""

    for char in text:
        current += char
        if char in "。！？":
            sentences.append(current)
            current = ""

    # 处理最后可能没有结束标点的文本
    if current:
        sentences.append(current)

    # 过滤掉空句子和只包含空白字符的句子
    return [s.strip() for s in sentences if s.strip()]


def setup_uni_client():
    """设置uniapi大模型客户端"""
    api_key = os.getenv("UNI_API_KEY")
    if not api_key:
        print("错误: 环境变量 UNI_API_KEY 未设置！请设置API密钥。")
        print("设置方法: export UNI_API_KEY=你的密钥")
        sys.exit(1)

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.uniapi.io/v1",
    )
    return client


def fix_long_sentence_punctuation(sentence):
    """
    使用GPT-4.1-mini修复长句子的标点符号

    Args:
        sentence: 需要修复标点的长句子

    Returns:
        str: 修复标点后的句子
    """
    global MAX_SENTENCE_LENGTH

    # 移除「」符号
    sentence = clean_text(sentence)

    # 清理输入句子中的空白字符
    sentence = re.sub(r"\s+", " ", sentence.strip())

    if len(sentence) <= MAX_SENTENCE_LENGTH:
        return sentence

    system_prompt = "你是一个标点符号专家，有一个很长的中文句子但没有句号，希望你能在适当位置把非句号标点替换为句号，让新的文字更连贯并有意义。你直接返回你修改后的内容，不要返回内容其他无关内容。"

    try:
        client = setup_uni_client()
        model = "gpt-4.1-mini"

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"{sentence}",
                },
            ],
        )

        response = completion.choices[0].message.content.strip()

        if DEBUG_MODE:
            print(f"原句: {sentence}")
            print(f"AI修复标点后: {response}")

        # 确保返回结果也经过了空白字符清理
        return re.sub(r"\s+", " ", response.strip())
    except Exception as e:
        print(f"API调用错误：{e}")
        return sentence  # 发生错误时返回原句


def ensure_sentence_length(sentences):
    """
    确保每个句子的长度不超过MAX_SENTENCE_LENGTH
    如果句子长度超过限制，则使用GPT-4.1-mini修复标点，然后拆分

    Args:
        sentences: 句子列表

    Returns:
        list: 处理后的句子列表
    """
    global MAX_SENTENCE_LENGTH
    result = []

    for sentence in sentences:
        # 移除「」符号
        sentence = clean_text(sentence)

        # 清理句子中的空白字符
        clean_sentence = re.sub(r"\s+", " ", sentence.strip())

        # 跳过空句子
        if not clean_sentence:
            continue

        if len(clean_sentence) <= MAX_SENTENCE_LENGTH:
            result.append(clean_sentence)
        else:
            # 对长句进行标点修复
            fixed_sentence = fix_long_sentence_punctuation(clean_sentence)

            # 确保修复后的句子被彻底分句
            # 首先尝试按句号、感叹号、问号分割
            sub_sentences = split_sentences(fixed_sentence)

            # 检查分割后的每个子句是否仍然过长
            final_sentences = []
            for sub_sent in sub_sentences:
                # 跳过空子句
                if not sub_sent.strip():
                    continue

                if len(sub_sent) > MAX_SENTENCE_LENGTH:
                    # 如果子句仍然过长，再次修复并分割
                    fixed_sub = fix_long_sentence_punctuation(sub_sent)
                    # 对修复后的子句再次分句
                    sub_sub_sentences = split_sentences(fixed_sub)
                    # 只添加非空的子句
                    final_sentences.extend([s for s in sub_sub_sentences if s.strip()])
                else:
                    final_sentences.append(sub_sent)

            # 添加所有拆分后的句子到结果
            result.extend(final_sentences)

    return result


def process_srt_file(input_file, output_file):
    """
    处理单个SRT文件，拆分每行中的多个句子

    Args:
        input_file: 输入SRT文件路径
        output_file: 输出TXT文件路径

    Returns:
        bool: 处理是否成功
    """
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 读取SRT文件内容
        srt_content = read_srt_file(input_file)

        # 解析SRT内容
        subtitles = parse_srt_with_re(srt_content)

        if not subtitles:
            print(f"警告: 文件 {input_file} 似乎没有有效的字幕内容")
            return False

        # 处理字幕文本并写入输出文件
        all_sentences = []
        for subtitle in tqdm(subtitles, desc="处理字幕"):
            text = subtitle["text"]
            # 拆分句子
            sentences = split_sentences(text)

            # 确保每个句子长度不超过限制
            processed_sentences = ensure_sentence_length(sentences)

            # 收集所有有效句子，确保清理掉句子内的换行符和多余空格
            for sentence in processed_sentences:
                # 清理句子：去除换行符并规范化空格
                cleaned_sentence = re.sub(r"\s+", " ", sentence.strip())
                if cleaned_sentence:  # 确保句子非空
                    all_sentences.append(cleaned_sentence)

        # 写入所有收集到的有效句子，每个句子一行，没有空行
        if all_sentences:
            # 过滤掉空句子，确保只有非空句子被写入
            valid_sentences = [s for s in all_sentences if s.strip()]
            # 确保每行只有一个句子，每个句子后都有换行符
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(valid_sentences))

        return True

    except Exception as e:
        print(f"处理文件 {input_file} 时出错: {e}")
        import traceback

        traceback.print_exc()
        return False


def process_all_channels(force=False):
    """
    处理zh_srt_tyro_fix目录下的所有频道和SRT文件

    Args:
        force: 是否强制重新处理已存在的文件
    """
    # 检查输入路径是否存在
    if not os.path.exists(INPUT_SRT_PATH):
        print(f"错误: 输入路径 '{INPUT_SRT_PATH}' 不存在")
        return

    # 获取所有频道目录
    channels = [
        d
        for d in os.listdir(INPUT_SRT_PATH)
        if os.path.isdir(os.path.join(INPUT_SRT_PATH, d))
    ]

    if not channels:
        print(f"在 '{INPUT_SRT_PATH}' 中未找到任何频道目录")
        return

    print(f"找到 {len(channels)} 个频道目录")

    for channel in channels:
        channel_input_path = os.path.join(INPUT_SRT_PATH, channel)
        channel_output_path = os.path.join(OUTPUT_TXT_PATH, channel)

        # 获取所有SRT文件
        srt_files = glob.glob(os.path.join(channel_input_path, "*.srt"))

        if not srt_files:
            print(f"在 {channel_input_path} 中未找到任何SRT文件，跳过")
            continue

        print(f"\n处理频道: {channel}，找到 {len(srt_files)} 个SRT文件")

        # 创建输出目录
        if not os.path.exists(channel_output_path):
            os.makedirs(channel_output_path)
            print(f"创建输出目录: {channel_output_path}")

        # 处理每个SRT文件
        for srt_file in tqdm(srt_files, desc=f"处理 {channel} 文件"):
            file_name = os.path.basename(srt_file)
            # 将输出文件扩展名从.srt改为.txt
            output_file = os.path.join(
                channel_output_path, file_name.replace(".srt", ".txt")
            )

            # 如果输出文件已存在且不强制重新处理，则跳过
            if os.path.exists(output_file) and not force:
                print(f"文件 {file_name} 已存在，跳过 (使用 -f 强制重新处理)")
                continue

            # 处理文件
            success = process_srt_file(srt_file, output_file)

            if success:
                print(f"成功处理文件: {file_name}")
            else:
                print(f"处理文件失败: {file_name}")


def process_single_file(file_path, force=False):
    """
    处理单个SRT文件

    Args:
        file_path: 文件路径
        force: 是否强制重新处理
    """
    if not os.path.exists(file_path):
        print(f"错误: 文件 '{file_path}' 不存在")
        return

    # 从文件路径提取频道
    file_dir = os.path.dirname(file_path)
    parts = file_dir.split(os.sep)

    # 尝试找到频道名称
    channel = parts[-1] if parts else "unknown"

    # 如果路径中包含 zh_srt_tyro_fix 目录，则获取其后的部分作为频道名
    if "zh_srt_tyro_fix" in parts:
        idx = parts.index("zh_srt_tyro_fix")
        if idx + 1 < len(parts):
            channel = parts[idx + 1]

    file_name = os.path.basename(file_path)
    output_file = os.path.join(
        OUTPUT_TXT_PATH, channel, file_name.replace(".srt", ".txt")
    )

    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 如果输出文件已存在且不强制重新处理，则跳过
    if os.path.exists(output_file) and not force:
        print(f"文件 {file_name} 已存在，跳过 (使用 -f 强制重新处理)")
        return

    # 处理文件
    success = process_srt_file(file_path, output_file)

    if success:
        print(f"成功处理文件: {file_name}")
    else:
        print(f"处理文件失败: {file_name}")


def main():
    global MAX_SENTENCE_LENGTH

    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description="将中文SRT文件中的字幕拆分为句子，并处理长句"
    )

    # 添加命令行参数
    parser.add_argument(
        "-f", "--force", action="store_true", help="强制重新处理，覆盖已有文件"
    )
    parser.add_argument(
        "-s", "--single_file", type=str, help="指定单独处理一个SRT文件路径"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="启用调试模式，显示详细处理信息"
    )
    parser.add_argument(
        "-m", "--max_length", type=int, default=200, help="最大句子长度限制 (默认: 200)"
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 设置调试模式
    global DEBUG_MODE
    DEBUG_MODE = args.debug
    MAX_SENTENCE_LENGTH = args.max_length

    if DEBUG_MODE:
        print("调试模式已启用")
        print(f"最大句子长度: {MAX_SENTENCE_LENGTH}")
        if args.single_file:
            print(f"处理单个文件: {args.single_file}")

    # 检查API密钥是否设置
    if not os.getenv("UNI_API_KEY"):
        print("错误: 环境变量 UNI_API_KEY 未设置！请设置API密钥。")
        print("设置方法: export UNI_API_KEY=你的密钥")
        return

    # 处理单个文件模式
    if args.single_file:
        process_single_file(args.single_file, args.force)
    else:
        # 处理所有频道和SRT文件
        process_all_channels(args.force)


if __name__ == "__main__":
    main()
