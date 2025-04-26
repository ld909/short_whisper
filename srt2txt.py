import os
import re
import argparse
import sys
import string


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


def process_srt_to_txt(input_file, output_file):
    """处理SRT文件，将其转换为按句子分割的TXT文件"""
    # 解析SRT文件
    entries = parse_srt(input_file)

    if not entries:
        print("错误: 未解析到任何字幕条目")
        return

    # 准备输出目录
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")

    # 处理每条字幕并写入TXT文件
    sentence_count = 0

    try:
        with open(output_file, "w", encoding="utf-8") as file:
            for entry in entries:
                text = entry["text"]
                sentences = split_sentences(text)

                # 写入每个句子
                for sentence in sentences:
                    # 跳过仅包含标点符号的句子
                    if is_only_punctuation(sentence):
                        continue

                    sentence_count += 1
                    file.write(f"{sentence_count}|{sentence}\n")

        print(f"处理完成! 共提取 {sentence_count} 个句子，已保存到 {output_file}")

    except Exception as e:
        print(f"处理过程中出错: {e}")


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description="将SRT字幕文件转换为按句子分割的TXT文件"
    )

    # 添加命令行参数
    parser.add_argument("-i", "--input", required=True, help="输入SRT文件路径")
    parser.add_argument("-o", "--output", help="输出TXT文件路径")

    # 解析命令行参数
    args = parser.parse_args()

    # 如果未指定输出文件，则根据输入文件名生成
    if not args.output:
        input_name = os.path.splitext(args.input)[0]
        args.output = f"{input_name}.txt"

    # 确保输入文件存在
    if not os.path.exists(args.input):
        print(f"错误: 找不到输入文件 '{args.input}'")
        sys.exit(1)

    # 执行转换
    process_srt_to_txt(args.input, args.output)


if __name__ == "__main__":
    main()
