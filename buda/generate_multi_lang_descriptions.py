"""
多语种YouTube视频描述生成工具

功能说明:
此脚本用于将多语言TXT文件内容转换为精简的YouTube视频描述。
脚本使用阿里云Qwen模型通过OpenAI兼容接口生成描述，支持英语、日语、越南语、韩语。
脚本支持断点续传，中断后可从上次停止的位置继续生成。

输入目录:
- TXT模式: [媒体路径]/multi_lang_txt/[频道名称]/[语言代码]/

输出目录:
- 描述文件: [媒体路径]/multi_lang_desc/[频道名称]/[语言代码]/

使用方法:
1. 基本使用: python generate_multi_lang_descriptions.py
2. 指定目标语言: python generate_multi_lang_descriptions.py -l English Japanese
3. 强制重新生成: python generate_multi_lang_descriptions.py -f
4. 指定频道: python generate_multi_lang_descriptions.py -c [频道名称]
5. 单文件处理: python generate_multi_lang_descriptions.py -s /path/to/file.txt

注意:
- 需要设置环境变量DASHSCOPE_API_KEY以提供阿里云API密钥
- 脚本支持断点续传，中断后可从上次停止的位置继续生成描述
"""

import os
import re
import time
import argparse
import sys
import platform
from openai import OpenAI
import glob
from tqdm import tqdm

# 定义支持的语言列表
LANGUAGES = ["English", "Korean"]
LANGUAGE_CODES = {"English": "en", "Japanese": "ja", "Vietnamese": "vi", "Korean": "ko"}
LANGUAGE_PROMPTS = {
    "English": "你是一个 youtube 描述文字生成专家，给定一个音频脚本，你能够给出 120 字以内的高度凝练的总结，总结风格让观众一看就上头，并且有希望关注频道的欲望，语言简短有力，不要写成一坨，可以分段落。总结需要用「英语」给出，不要出现别的语言哈，直接返回你的总结，不要夹带任何内容，可是适当使用 emoji做强调但不要过多。",
    "Japanese": "你是一个 youtube 描述文字生成专家，给定一个音频脚本，你能够给出 120 字以内的高度凝练的总结，总结风格让观众一看就上头，并且有希望关注频道的欲望，语言简短有力，不要写成一坨，可以分段落。总结需要用「日语」给出，不要出现别的语言哈，直接返回你的总结，不要夹带任何内容，可是适当使用 emoji做强调但不要过多。",
    "Vietnamese": "你是一个 youtube 描述文字生成专家，给定一个音频脚本，你能够给出 120 字以内的高度凝练的总结，总结风格让观众一看就上头，并且有希望关注频道的欲望，语言简短有力，不要写成一坨，可以分段落。总结需要用「越南语」给出，不要出现别的语言哈，直接返回你的总结，不要夹带任何内容，可是适当使用 emoji做强调但不要过多。",
    "Korean": "你是一个 youtube 描述文字生成专家，给定一个音频脚本，你能够给出 120 字以内的高度凝练的总结，总结风格让观众一看就上头，并且有希望关注频道的欲望，语言简短有力，不要写成一坨，可以分段落。总结需要用「韩语」给出，不要出现别的语言哈，直接返回你的总结，不要夹带任何内容，可是适当使用 emoji做强调但不要过多。",
}


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# 获取媒体基础路径
BASE_MEDIA_PATH = get_base_media_path()


def setup_openai_client():
    """设置OpenAI客户端并验证API密钥"""
    api_key = os.environ.get("DASHSCOPE_API_KEY")

    if not api_key:
        print("错误: 未找到阿里云API密钥")
        print("请设置环境变量DASHSCOPE_API_KEY")
        print("例如: export DASHSCOPE_API_KEY='your-api-key'")
        sys.exit(1)

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        return client
    except Exception as e:
        print(f"初始化OpenAI客户端时出错: {e}")
        sys.exit(1)


def check_if_already_processed(output_file):
    """检查描述文件是否已经生成"""
    return os.path.exists(output_file) and os.path.getsize(output_file) > 0


def generate_description(input_file, language, client, max_retries=3):
    """使用阿里云Qwen模型生成视频描述"""
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()

        for attempt in range(max_retries):
            try:
                completion = client.chat.completions.create(
                    model="qwen-plus",
                    messages=[
                        {"role": "system", "content": LANGUAGE_PROMPTS[language]},
                        {"role": "user", "content": content},
                    ],
                    stream=False,
                )

                return completion.choices[0].message.content
            except Exception as e:
                print(f"生成描述出错 (尝试 {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print("等待3秒后重试...")
                    time.sleep(3)  # 添加延迟，避免过快请求
                else:
                    print(f"达到最大重试次数 ({max_retries})，返回空描述")
                    return "生成描述失败，请稍后重试。"
    except Exception as e:
        print(f"读取文件或生成描述时出错: {e}")
        return "生成描述失败，请稍后重试。"


def process_single_file(input_file, language, client, force=False):
    """处理单个文件，生成视频描述并保存"""
    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在: {input_file}")
        return False

    # 分析文件路径，构建输出路径
    input_parts = input_file.split(os.sep)
    try:
        # 尝试找到multi_lang_txt在路径中的位置
        txt_dir_index = input_parts.index("multi_lang_txt")
        channel_name = input_parts[txt_dir_index + 1]
        lang_code = input_parts[txt_dir_index + 2]
        file_name = input_parts[-1]

        output_dir = os.path.join(
            BASE_MEDIA_PATH, "multi_lang_desc", channel_name, lang_code
        )
    except ValueError:
        # 如果路径中没有multi_lang_txt，使用文件名和语言代码
        file_name = os.path.basename(input_file)
        output_dir = os.path.join(
            BASE_MEDIA_PATH,
            "multi_lang_desc",
            "unknown_channel",
            LANGUAGE_CODES[language],
        )

    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")

    output_file = os.path.join(output_dir, file_name)

    # 检查是否已处理
    if not force and check_if_already_processed(output_file):
        print(f"文件 {file_name} 已处理，跳过 (使用 -f 强制重新生成)")
        return True

    print(f"正在处理文件: {file_name}")
    print(f"从 {input_file}")
    print(f"到 {output_file}")

    # 生成描述
    description = generate_description(input_file, language, client)

    # 保存描述
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(description)
        print(f"成功保存描述到: {output_file}")
        return True
    except Exception as e:
        print(f"保存描述时出错: {e}")
        return False


def process_all_channels(languages=None, force=False, specific_channel=None):
    """处理所有频道的TXT文件，生成视频描述"""
    if languages is None:
        languages = LANGUAGES

    client = setup_openai_client()

    input_base = os.path.join(BASE_MEDIA_PATH, "multi_lang_txt")
    if not os.path.exists(input_base):
        print(f"错误: 输入目录不存在: {input_base}")
        return

    # 获取所有频道目录或指定频道
    if specific_channel:
        channel_dir = os.path.join(input_base, specific_channel)
        if not os.path.exists(channel_dir):
            print(f"错误: 指定的频道目录不存在: {channel_dir}")
            return
        channels = [specific_channel]
    else:
        channels = [
            d
            for d in os.listdir(input_base)
            if os.path.isdir(os.path.join(input_base, d)) and not d.startswith(".")
        ]

    print(f"找到 {len(channels)} 个频道目录")

    for channel in channels:
        channel_dir = os.path.join(input_base, channel)

        for language in languages:
            lang_code = LANGUAGE_CODES[language]
            language_dir = os.path.join(channel_dir, lang_code)

            if not os.path.exists(language_dir):
                print(f"跳过: 未找到语言目录 {language_dir}")
                continue

            txt_files = [
                f
                for f in os.listdir(language_dir)
                if f.endswith(".txt") and not f.startswith(".")
            ]

            if not txt_files:
                print(f"在 {channel}/{lang_code} 中未找到任何TXT文件，跳过")
                continue

            print(
                f"\n处理频道: {channel}, 语言: {language}, 找到 {len(txt_files)} 个TXT文件"
            )

            # 创建输出目录
            output_dir = os.path.join(
                BASE_MEDIA_PATH, "multi_lang_desc", channel, lang_code
            )
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            for txt_file in tqdm(txt_files, desc=f"{channel}/{lang_code}处理进度"):
                input_file = os.path.join(language_dir, txt_file)
                output_file = os.path.join(output_dir, txt_file)

                # 检查是否已处理
                if not force and check_if_already_processed(output_file):
                    continue

                # 生成并保存描述
                try:
                    process_single_file(input_file, language, client, force)
                except Exception as e:
                    print(f"处理文件 {txt_file} 时出错: {e}")


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description="使用阿里云Qwen模型将多语言TXT文件转换为YouTube视频描述"
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
        "-f", "--force", action="store_true", help="强制重新生成描述，覆盖已有文件"
    )
    parser.add_argument("-c", "--channel", type=str, help="指定处理单个频道")
    parser.add_argument(
        "-s", "--single_file", type=str, help="指定单独处理一个TXT文件路径"
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 验证语言参数
    for lang in args.languages:
        if lang not in LANGUAGES:
            print(f"错误: 不支持的语言 '{lang}'")
            print(f"支持的语言: {', '.join(LANGUAGES)}")
            sys.exit(1)

    # 设置OpenAI客户端
    client = setup_openai_client()

    # 处理单个文件模式
    if args.single_file:
        language = None
        # 尝试从文件路径推断语言
        for lang, code in LANGUAGE_CODES.items():
            if f"/{code}/" in args.single_file:
                language = lang
                break

        if not language and len(args.languages) == 1:
            language = args.languages[0]
        elif not language:
            print("无法从文件路径推断语言，请使用 -l 参数指定单一语言")
            sys.exit(1)

        process_single_file(args.single_file, language, client, args.force)
    else:
        # 处理所有频道和TXT文件或指定频道
        process_all_channels(args.languages, args.force, args.channel)


if __name__ == "__main__":
    main()
