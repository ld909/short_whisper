import os
import re
import argparse
import sys
import string
import platform


def is_only_punctuation(text):
    """检查文本是否只包含标点符号"""
    if not text:
        return True

    # 去除空白字符后检查
    text = text.strip()
    if not text:
        return True

    # 检查是否只有标点符号
    punctuation_chars = set(string.punctuation + "，。！？；：" "''「」【】《》…—")
    return all(char in punctuation_chars or char.isspace() for char in text)


def parse_srt(file_path):
    """解析SRT文件，返回字幕条目列表"""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # 使用正则表达式匹配SRT条目
        pattern = r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}\s-->\s\d{2}:\d{2}:\d{2},\d{3})\n([\s\S]*?)(?=\n\d+\n|$)"
        matches = re.findall(pattern, content)

        if not matches:
            print("警告: 未找到匹配的SRT条目格式，请检查SRT文件格式是否正确")

        entries = []
        for match in matches:
            index = match[0]
            timestamp = match[1]
            text = match[2].strip()
            entries.append({"index": index, "timestamp": timestamp, "text": text})

        return entries
    except UnicodeDecodeError:
        print("错误: 文件编码错误，请确保文件是UTF-8编码")
        sys.exit(1)
    except Exception as e:
        print(f"解析SRT文件时出错: {e}")
        sys.exit(1)


def split_sentences(text):
    """将文本按英文句号分割成多个句子"""
    if not text:
        return []

    # 如果文本中有句号，则按句号分割
    if "." in text:
        # 使用正则表达式分割句子，保留句号
        sentences = re.findall(r"[^.]*\.", text)

        # 处理可能的剩余文本（没有以句号结尾的部分）
        remaining = re.sub(r".*\.", "", text).strip()
        if remaining:
            sentences.append(remaining)

        # 去除每个句子前后的空白字符
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    else:
        # 如果没有句号，返回原文本作为一个句子
        return [text]


def get_base_path():
    """根据操作系统类型返回对应的基础路径"""
    if platform.system() == "Darwin":  # Mac OS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


def process_srt_to_txt(input_file, output_file):
    """处理SRT文件，将其转换为按句子分割的TXT文件"""
    entries = parse_srt(input_file)
    if not entries:
        print(f"错误: 未解析到任何字幕条目: {input_file}")
        return
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")
    try:
        with open(output_file, "w", encoding="utf-8") as file:
            for entry in entries:
                text = entry["text"]
                sentences = split_sentences(text)
                for sentence in sentences:
                    if is_only_punctuation(sentence):
                        continue
                    file.write(f"{sentence}\n")
        print(f"处理完成! 已保存到 {output_file}")
    except Exception as e:
        print(f"处理过程中出错: {e}")


def main():
    base_path = get_base_path()
    parser = argparse.ArgumentParser(
        description="批量将SRT字幕文件转换为按句子分割的TXT文件"
    )
    parser.add_argument(
        "-i",
        "--input",
        default=f"{base_path}/zh_srt_tyro_fix",
        help="输入SRT基础目录路径（通常为fix_tyro.py输出目录）",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=f"{base_path}/pure_sentence",
        help="输出TXT基础目录路径",
    )
    args = parser.parse_args()
    input_base_dir = args.input
    output_base_dir = args.output
    if not os.path.exists(input_base_dir):
        print(f"错误: 输入目录不存在: {input_base_dir}")
        return
    if not os.path.exists(output_base_dir):
        os.makedirs(output_base_dir)
        print(f"已创建输出基础目录: {output_base_dir}")
    channels = [
        d
        for d in os.listdir(input_base_dir)
        if os.path.isdir(os.path.join(input_base_dir, d))
    ]
    print(f"找到 {len(channels)} 个频道目录")
    for channel in channels:
        input_channel_dir = os.path.join(input_base_dir, channel)
        output_channel_dir = os.path.join(output_base_dir, channel)
        if not os.path.exists(output_channel_dir):
            os.makedirs(output_channel_dir)
            print(f"已创建频道输出目录: {output_channel_dir}")
        srt_files = [f for f in os.listdir(input_channel_dir) if f.endswith(".srt")]
        print(f"频道 {channel} 下找到 {len(srt_files)} 个SRT文件")
        for srt_file in srt_files:
            input_file_path = os.path.join(input_channel_dir, srt_file)
            txt_file_name = os.path.splitext(srt_file)[0] + ".txt"
            output_file_path = os.path.join(output_channel_dir, txt_file_name)
            process_srt_to_txt(input_file_path, output_file_path)


if __name__ == "__main__":
    main()
