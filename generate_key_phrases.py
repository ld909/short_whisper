"""
多语种视频标题关键词/短语生成工具

功能说明:
此脚本用于从已翻译的视频标题中提取多语种的重点关键词或短语。
脚本使用OpenAI API生成简短有力的关键词或短语，以吸引观众点击观看视频。
支持并发处理和断点续传功能。

输入:
- 已翻译的JSON文件 (来自title_translator_multi_lang.py的输出)

输出:
- JSON文件，包含各语言的重点关键词/短语
- 输出路径: /Volumes/dhl/buda_videos_youtube/key_words/[频道名称]/[语言代码]/[视频名称].json

使用方法:
1. 基本使用: python generate_key_phrases.py
2. 指定目标语言: python generate_key_phrases.py -l English Japanese
3. 强制重新生成: python generate_key_phrases.py -f
4. 设置批处理大小: python generate_key_phrases.py -b 20

注意:
- 需要设置环境变量UNI_API_KEY以提供OpenAI API密钥
- 脚本支持断点续传，中断后可从上次停止的位置继续处理
"""

import os
import sys
import json
import time
import argparse
import platform
from openai import OpenAI
import concurrent.futures
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

# 定义支持的语言列表
LANGUAGES = ["English", "Japanese", "Vietnamese", "Korean"]
LANGUAGE_CODES = {"English": "en", "Japanese": "ja", "Vietnamese": "vi", "Korean": "ko"}


def setup_openai_client():
    """设置OpenAI客户端并验证API密钥"""
    api_key = os.environ.get("UNI_API_KEY")

    if not api_key:
        print("错误: 未找到OpenAI API密钥")
        print("请设置环境变量UNI_API_KEY")
        print("例如: export UNI_API_KEY='your-api-key'")
        sys.exit(1)

    try:
        client = OpenAI(base_url="https://api.uniapi.io/v1", api_key=api_key)
        return client
    except Exception as e:
        print(f"初始化OpenAI客户端时出错: {e}")
        sys.exit(1)


def generate_key_phrases(client, title, language, max_retries=3):
    """使用OpenAI的GPT模型生成关键词/短语，失败时自动重试"""
    if not title.strip():
        return ""  # 如果标题为空，则直接返回空字符串

    for attempt in range(max_retries):
        try:
            # 根据语言选择适当的系统提示
            system_prompt = f"你是一个精通{language}的内容创作专家和佛学大师。请为以下标题提取2～3简短有力的关键词或短语，让观众想点击观看。直接返回{language}关键词/短语，不要夹带其他内容。"

            completion = client.chat.completions.create(
                model="gpt-4.1-mini",
                max_tokens=200,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": title},
                ],
                timeout=30,  # 增加超时时间为30秒
            )
            result = completion.choices[0].message.content
            # 将换行符替换为空格
            result = result.replace("\n", " ")
            return result
        except Exception as e:
            print(f"生成关键词/短语出错 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                retry_delay = (attempt + 1) * 3  # 逐步增加延迟时间
                print(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)  # 添加延迟，避免过快请求
            else:
                print(f"达到最大重试次数 ({max_retries})，返回空结果")
                return ""  # 如果所有尝试都失败，返回空字符串


def process_title_file(
    client, channel, video_name, title_file, languages=None, force=False
):
    """处理单个标题文件，为每种语言生成关键词/短语"""
    if languages is None:
        languages = LANGUAGES

    try:
        # 读取已翻译的标题文件
        with open(title_file, "r", encoding="utf-8") as f:
            translations = json.load(f)

        # 初始化结果字典
        result = {}

        # 为每种语言生成关键词/短语
        for lang in languages:
            lang_code = LANGUAGE_CODES[lang]

            # 检查标题文件中是否包含此语言的翻译
            if lang_code not in translations:
                print(f"警告: 标题文件中没有 {lang} 翻译，跳过")
                continue

            # 获取此语言的标题
            title = translations[lang_code]

            # 为此语言创建输出目录
            output_dir = os.path.join(BASE_MEDIA_PATH, "key_words", channel, lang_code)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # 定义输出文件路径
            output_file = os.path.join(output_dir, f"{video_name}.json")

            # 检查是否需要生成
            if os.path.exists(output_file) and not force:
                try:
                    with open(output_file, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                    if existing_data:  # 如果文件存在且有内容，跳过
                        print(f"跳过已处理的 {lang} 关键词/短语: {video_name}")
                        continue
                except (json.JSONDecodeError, FileNotFoundError):
                    # 文件损坏或不完整，需要重新处理
                    pass

            # 生成关键词/短语
            print(f"为 {video_name} 生成 {lang} 关键词/短语...")
            key_phrases = generate_key_phrases(client, title, lang)

            # 保存结果
            result[lang_code] = key_phrases

            # 单独保存到每种语言的目录
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"key_phrases": key_phrases, "title": title},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            print(f"已保存 {lang} 关键词/短语到: {output_file}")

        return result

    except Exception as e:
        print(f"处理 {video_name} 时出错: {e}")
        return None


def process_channel(client, channel, languages=None, force=False, batch_size=20):
    """处理单个频道的所有标题文件"""
    if languages is None:
        languages = LANGUAGES

    # 定义输入路径（已翻译的标题文件目录）
    input_path = os.path.join(BASE_MEDIA_PATH, "multi_lang_titles", channel)

    # 检查输入路径是否存在
    if not os.path.exists(input_path):
        print(f"错误: 频道 '{channel}' 的已翻译标题目录不存在: {input_path}")
        return

    # 获取所有JSON标题文件
    title_files = [f for f in os.listdir(input_path) if f.endswith(".json")]

    if not title_files:
        print(f"在频道 '{channel}' 中未找到任何已翻译的标题文件，跳过")
        return

    print(f"\n处理频道: {channel}，找到 {len(title_files)} 个已翻译标题文件")

    # 收集需要处理的文件
    files_to_process = []
    for title_file in title_files:
        video_name = os.path.splitext(title_file)[0]  # 去掉.json扩展名
        full_title_path = os.path.join(input_path, title_file)

        # 检查是否所有语言的关键词/短语都已存在
        all_exist = True
        for lang in languages:
            lang_code = LANGUAGE_CODES[lang]
            output_file = os.path.join(
                BASE_MEDIA_PATH, "key_words", channel, lang_code, f"{video_name}.json"
            )

            if not os.path.exists(output_file) or force:
                all_exist = False
                break

        if not all_exist:
            files_to_process.append((video_name, full_title_path))

    # 如果没有需要处理的文件，返回
    if not files_to_process:
        print(f"频道 '{channel}' 中的所有标题文件都已处理完毕")
        return

    print(f"需要处理 {len(files_to_process)} 个文件")

    # 批量处理文件
    with tqdm(total=len(files_to_process), desc="生成关键词/短语进度") as pbar:
        for i in range(0, len(files_to_process), batch_size):
            batch = files_to_process[i : i + batch_size]

            # 函数用于处理单个文件
            def process_file(file_info):
                video_name, title_file = file_info
                return process_title_file(
                    client, channel, video_name, title_file, languages, force
                )

            # 并发处理批次
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=batch_size
            ) as executor:
                results = list(executor.map(process_file, batch))

            # 更新进度条
            pbar.update(len(batch))

            # 统计成功率
            success_count = sum(1 for r in results if r is not None)
            print(f"批次处理完成: {success_count}/{len(batch)} 成功")


def process_all_channels(client, languages=None, force=False, batch_size=20):
    """处理所有频道的标题文件"""
    if languages is None:
        languages = LANGUAGES

    # 定义输入基础路径（已翻译的标题文件所在目录）
    input_base_path = os.path.join(BASE_MEDIA_PATH, "multi_lang_titles")

    # 检查输入路径是否存在
    if not os.path.exists(input_base_path):
        print(f"错误: 已翻译标题的基础路径 '{input_base_path}' 不存在")
        return

    # 获取所有频道目录
    channels = [
        d
        for d in os.listdir(input_base_path)
        if os.path.isdir(os.path.join(input_base_path, d))
    ]

    if not channels:
        print(f"在 '{input_base_path}' 中未找到任何频道目录")
        return

    print(f"找到 {len(channels)} 个频道目录")

    # 处理每个频道
    for channel in channels:
        process_channel(client, channel, languages, force, batch_size)


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description="从已翻译的标题中生成多语种关键词/短语"
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
        "-f",
        "--force",
        action="store_true",
        help="强制重新生成关键词/短语，忽略已有文件",
    )
    parser.add_argument(
        "-b", "--batch_size", type=int, default=20, help="并发处理的批量大小，默认为20"
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 设置OpenAI客户端
    client = setup_openai_client()

    # 验证和过滤语言参数
    valid_languages = [lang for lang in args.languages if lang in LANGUAGES]
    if not valid_languages:
        print(f"错误: 未提供有效的目标语言。支持的语言有: {', '.join(LANGUAGES)}")
        return
    if set(valid_languages) != set(args.languages):
        print(f"警告: 某些语言不受支持，将只处理: {', '.join(valid_languages)}")

    # 处理所有频道和标题
    process_all_channels(client, valid_languages, args.force, args.batch_size)

    print("所有关键词/短语生成任务完成!")


if __name__ == "__main__":
    main()
