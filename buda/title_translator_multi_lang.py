"""
多语言视频标题翻译工具

功能说明:
此脚本用于将视频标题中文内容（去除标签）批量翻译成多种语言（英语、日语、韩语、越南语）。
脚本使用OpenAI API进行翻译，特别针对佛教内容优化，支持并发处理和断点续传。

输入:
- MP3文件名（从mp3tofineEngsrt.py的mp3路径）

输出:
- JSON文件，包含原始标题（去除标签）和四种语言的翻译
- 输出路径: [媒体路径]/multi_lang_titles/[频道名称]/[视频名称].json

使用方法:
1. 基本使用: python title_translator_multi_lang.py [主题名称]
2. 指定目标语言: python title_translator_multi_lang.py [主题名称] -l English Japanese
3. 强制重新翻译: python title_translator_multi_lang.py [主题名称] -f
4. 设置批处理大小: python title_translator_multi_lang.py [主题名称] -b 20

注意:
- 需要设置环境变量UNI_API_KEY以提供OpenAI API密钥
- 脚本支持断点续传，中断后可从上次停止的位置继续翻译
"""

import os
import re
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


def remove_tags(title):
    """去除标题中的标签 (#tag)"""
    # 匹配 #tag 格式的标签并删除
    cleaned_title = re.sub(r"#\w+\b", "", title).strip()
    # 处理可能的多余空格
    cleaned_title = re.sub(r"\s+", " ", cleaned_title)
    return cleaned_title


def translate_text(client, text, target_language="English", max_retries=3):
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
                max_tokens=500,
                messages=[
                    {
                        "role": "system",
                        "content": f"你是一个翻译大师、佛学大师、佛教专家。精通佛教各种术语在不同文化中对应的词汇，我需要你将中文佛教内容翻译为{target_language}，直接返回翻译后的结果，不要夹带其他内容。不要以翻译后这样的内容开头作为返回。",
                    },
                    {"role": "user", "content": text},
                ],
            )
            result = completion.choices[0].message.content
            return result
        except Exception as e:
            print(f"翻译出错 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("等待2秒后重试...")
                time.sleep(2)  # 添加延迟，避免过快请求
            else:
                print(f"达到最大重试次数 ({max_retries})，返回原文")
                return text  # 如果所有尝试都失败，返回原文


def translate_title_to_all_languages(client, title, languages=None):
    """将标题翻译为所有指定语言"""
    if languages is None:
        languages = LANGUAGES

    # 去除标签
    cleaned_title = remove_tags(title)

    # 初始化结果字典，包含原始清理后的标题
    result = {"original": cleaned_title}

    # 并发翻译到所有语言
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(languages)) as executor:
        # 为每种语言创建翻译任务
        future_to_lang = {
            executor.submit(translate_text, client, cleaned_title, lang): lang
            for lang in languages
        }

        for future in concurrent.futures.as_completed(future_to_lang):
            lang = future_to_lang[future]
            try:
                translation = future.result()
                result[LANGUAGE_CODES[lang]] = translation
                print(f"完成 {lang} 翻译: {translation}")
            except Exception as e:
                print(f"翻译到 {lang} 时出错: {e}")
                result[LANGUAGE_CODES[lang]] = cleaned_title  # 出错时使用原文

    return result


def process_channel_titles(
    client, topic, channel, languages=None, force=False, batch_size=20
):
    """处理单个频道的所有视频标题"""
    if languages is None:
        languages = LANGUAGES

    # 定义输入和输出路径
    mp3_input_path = os.path.join(BASE_MEDIA_PATH, topic, channel)
    output_base_path = os.path.join(BASE_MEDIA_PATH, "multi_lang_titles", channel)

    # 确保输出目录存在
    if not os.path.exists(output_base_path):
        os.makedirs(output_base_path)
        print(f"创建输出目录: {output_base_path}")

    # 获取所有MP3文件，过滤掉点开头的文件
    mp3_files = [
        f
        for f in os.listdir(mp3_input_path)
        if f.endswith(".mp3") and not f.startswith(".")
    ]

    if not mp3_files:
        print(f"在频道 '{channel}' 中未找到任何MP3文件，跳过")
        return

    print(f"\n处理频道: {channel}，找到 {len(mp3_files)} 个MP3文件")

    # 收集需要处理的文件
    files_to_process = []
    for mp3_file in mp3_files:
        video_name = os.path.splitext(mp3_file)[0]  # 去掉.mp3扩展名
        output_file = os.path.join(output_base_path, f"{video_name}.json")

        # 检查是否需要处理此文件
        if os.path.exists(output_file) and not force:
            # 检查文件是否包含所有语言翻译
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    all_langs_present = all(
                        LANGUAGE_CODES[lang] in data for lang in languages
                    )
                    if all_langs_present:
                        print(f"跳过已处理的文件: {video_name}")
                        continue
            except (json.JSONDecodeError, FileNotFoundError):
                # 文件损坏或不完整，需要重新处理
                pass

        files_to_process.append((video_name, mp3_file))

    # 如果没有需要处理的文件，返回
    if not files_to_process:
        print(f"频道 '{channel}' 中的所有文件都已处理完毕")
        return

    print(f"需要处理 {len(files_to_process)} 个文件")

    # 批量处理文件
    with tqdm(total=len(files_to_process), desc="翻译进度") as pbar:
        for i in range(0, len(files_to_process), batch_size):
            batch = files_to_process[i : i + batch_size]

            def process_file(file_info):
                video_name, mp3_file = file_info
                title = video_name  # 使用文件名作为标题

                try:
                    # 翻译标题到所有语言
                    translations = translate_title_to_all_languages(
                        client, title, languages
                    )

                    # 保存到JSON文件
                    output_file = os.path.join(output_base_path, f"{video_name}.json")
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(translations, f, ensure_ascii=False, indent=2)

                    print(f"已保存翻译结果到: {output_file}")
                    return True
                except Exception as e:
                    print(f"处理 {video_name} 时出错: {e}")
                    return False

            # 并发处理批次
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=batch_size
            ) as executor:
                results = list(executor.map(process_file, batch))

            # 更新进度条
            pbar.update(len(batch))

            # 统计成功率
            success_count = sum(1 for r in results if r)
            print(f"批次处理完成: {success_count}/{len(batch)} 成功")


def process_all_channels(client, topic, languages=None, force=False, batch_size=20):
    """处理指定主题下的所有频道"""
    if languages is None:
        languages = LANGUAGES

    # 检查输入路径是否存在
    topic_path = os.path.join(BASE_MEDIA_PATH, topic)
    if not os.path.exists(topic_path):
        print(f"错误: 主题路径 '{topic_path}' 不存在")
        return

    # 获取所有频道目录，过滤掉点开头的目录
    channels = [
        d
        for d in os.listdir(topic_path)
        if os.path.isdir(os.path.join(topic_path, d)) and not d.startswith(".")
    ]

    if not channels:
        print(f"在 '{topic_path}' 中未找到任何频道目录")
        return

    print(f"找到 {len(channels)} 个频道目录")

    # 处理每个频道
    for channel in channels:
        process_channel_titles(client, topic, channel, languages, force, batch_size)


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="将视频标题翻译为多种语言并保存为JSON")

    # 添加命令行参数
    parser.add_argument("topic", help="主题名称，对应视频的顶级目录名称")
    parser.add_argument(
        "-l",
        "--languages",
        nargs="+",
        default=LANGUAGES,
        help=f"目标语言列表 (默认: {' '.join(LANGUAGES)})",
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="强制重新翻译，忽略已有翻译"
    )
    parser.add_argument(
        "-b", "--batch_size", type=int, default=5, help="并发处理的批量大小，默认为20"
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
    process_all_channels(
        client, args.topic, valid_languages, args.force, args.batch_size
    )

    print("所有标题翻译任务完成!")


if __name__ == "__main__":
    main()
