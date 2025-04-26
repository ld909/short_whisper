import os
import re
import time
import argparse
import sys
from openai import OpenAI
import glob


def setup_openai_client():
    """设置OpenAI客户端并验证API密钥"""
    api_key = os.environ.get("UNI_API_KEY")

    if not api_key:
        print("错误: 未找到OpenAI API密钥")
        print("请设置环境变量OPENAI_API_KEY或在脚本中提供API密钥")
        print("例如: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)

    try:
        client = OpenAI(base_url="https://api.uniapi.io/v1", api_key=api_key)
        return client
    except Exception as e:
        print(f"初始化OpenAI客户端时出错: {e}")
        sys.exit(1)


# 初始化OpenAI客户端
client = None  # 将在main函数中初始化


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


def translate_text(text, target_language="English"):
    """使用OpenAI的GPT模型翻译文本"""
    if not text.strip():
        return ""  # 如果文本为空，则直接返回空字符串

    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            max_tokens=1000,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个翻译大师，佛学大师，佛教专家。精通佛教各种术语在不同文化中对应的词汇，我需要你将中文佛教内容翻译为英文，直接返回翻译后的结果，不要夹带其他内容。不要以翻译后这样的内容开头作为返回。",
                },
                {"role": "user", "content": text},
            ],
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"翻译出错: {e}")
        print(f"原文: {text}")
        return text  # 如果翻译失败，返回原文


def check_progress(output_file):
    """检查输出文件中已翻译的条目数量"""
    if not os.path.exists(output_file):
        return 0

    try:
        with open(output_file, "r", encoding="utf-8") as file:
            content = file.read()

        # 计算已翻译的条目数
        pattern = r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}\s-->\s\d{2}:\d{2}:\d{2},\d{3})\n"
        matches = re.findall(pattern, content)
        return len(matches)
    except Exception as e:
        print(f"检查翻译进度时出错: {e}")
        return 0


def translate_srt_file(input_file, output_file, target_language="English"):
    """翻译整个SRT文件，逐条翻译并即时写入输出文件"""
    entries = parse_srt(input_file)

    if not entries:
        print("错误: 未解析到任何字幕条目")
        return

    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")

    # 检查是否有已翻译的进度
    already_translated = check_progress(output_file)
    print(f"检测到已翻译 {already_translated}/{len(entries)} 条字幕")

    # 确定从哪个索引开始翻译
    start_index = already_translated
    total_entries = len(entries)

    # 如果全部翻译完成，直接返回
    if start_index >= total_entries:
        print("所有字幕都已翻译完成，无需重新翻译")
        return

    print(f"从第 {start_index+1} 条开始翻译，共 {total_entries} 条字幕...")

    # 确定写入模式：如果已有翻译内容，追加模式；否则，写入模式
    write_mode = "a" if already_translated > 0 else "w"

    try:
        with open(output_file, write_mode, encoding="utf-8") as file:
            for i in range(start_index, total_entries):
                entry = entries[i]
                print(f"正在翻译第 {i+1}/{total_entries} 条字幕...")
                original_text = entry["text"]
                print(f"翻译前: {original_text}")

                translated_text = translate_text(original_text, target_language)
                print(f"翻译后: {translated_text}")

                # 即时写入翻译结果到文件
                file.write(f"{entry['index']}\n")
                file.write(f"{entry['timestamp']}\n")
                file.write(f"{translated_text}\n\n")
                # 确保立即写入磁盘
                file.flush()
                os.fsync(file.fileno())

                print(f"已写入第 {i+1} 条字幕")
                print("-" * 50)  # 分隔线，使输出更清晰

                # 添加延迟，避免API请求过于频繁
                if i < total_entries - 1:  # 最后一项不需要延迟
                    time.sleep(0.5)

        print(f"翻译完成! 所有内容已保存到 {output_file}")

    except KeyboardInterrupt:
        print("\n翻译被用户中断")
        print(f"已翻译并保存到第 {i+1} 条字幕")
        print(f"下次运行时将从第 {i+2} 条开始继续翻译")

    except Exception as e:
        print(f"翻译过程中出错: {e}")
        print(f"已翻译并保存部分内容，下次可继续从断点处翻译")


def process_directory(input_path, output_path, target_language="English", force=False):
    """处理目录中的所有SRT文件"""
    # 确保输出目录存在
    if not os.path.exists(output_path):
        os.makedirs(output_path)
        print(f"创建输出目录: {output_path}")

    # 获取所有SRT文件
    srt_files = glob.glob(os.path.join(input_path, "*.srt"))

    if not srt_files:
        print(f"在目录 '{input_path}' 中未找到任何SRT文件")
        return

    print(f"在目录 '{input_path}' 中找到 {len(srt_files)} 个SRT文件")

    for input_file in srt_files:
        # 生成输出文件路径
        file_name = os.path.basename(input_file)
        base_name = os.path.splitext(file_name)[0]
        output_file = os.path.join(
            output_path, f"{base_name}_{target_language.lower()}.srt"
        )

        print(f"\n处理文件: {file_name}")
        print(f"输出到: {output_file}")

        # 如果强制重新翻译且输出文件存在，则删除输出文件
        if force and os.path.exists(output_file):
            os.remove(output_file)
            print(f"已删除现有输出文件 '{output_file}'，将重新翻译")

        # 翻译文件
        translate_srt_file(input_file, output_file, target_language)


def main():
    global client

    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="使用OpenAI GPT模型翻译SRT字幕文件")

    # 添加命令行参数
    parser.add_argument("-i", "--input", default="o.srt", help="输入SRT文件或目录路径")
    parser.add_argument("-o", "--output", help="输出SRT文件或目录路径")
    parser.add_argument(
        "-l", "--language", default="English", help="目标语言 (默认: English)"
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="强制重新翻译，忽略已有翻译进度"
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 设置OpenAI客户端
    client = setup_openai_client()

    # 检查输入路径是文件还是目录
    if os.path.isdir(args.input):
        # 如果是目录，需要指定输出目录
        if not args.output:
            args.output = os.path.join(
                os.path.dirname(args.input), f"translated_{args.language.lower()}"
            )

        # 处理目录
        process_directory(args.input, args.output, args.language, args.force)
    else:
        # 如果是单个文件
        # 如果未指定输出文件，则根据输入文件名生成
        if not args.output:
            input_name = os.path.splitext(args.input)[0]
            args.output = f"{input_name}_{args.language.lower()}.srt"

        # 确保输入文件存在
        if not os.path.exists(args.input):
            print(f"错误: 找不到输入文件 '{args.input}'")
            sys.exit(1)

        # 如果指定了强制重新翻译，且输出文件存在，则删除输出文件
        if args.force and os.path.exists(args.output):
            os.remove(args.output)
            print(f"已删除现有输出文件 '{args.output}'，将重新翻译")

        # 执行翻译
        translate_srt_file(args.input, args.output, args.language)


if __name__ == "__main__":
    main()
