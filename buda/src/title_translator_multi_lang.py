"""
多语言视频标题处理工具

功能说明:
此脚本用于处理视频标题的多语言版本。支持两种模式：
1. 直接提取：如果目标语言有对应的原始视频文件，直接从文件名提取标题
2. 翻译模式：如果目标语言没有原始视频，则从源语言（通常是中文）翻译标题

脚本使用OpenAI API进行翻译，特别针对佛教内容优化，支持并发处理和断点续传。

输入:
- MP4文件名（从merge_mp4_mp3.py的多语言视频路径）
- 支持的输入语言目录：chinese、english、korean

输出:
- JSON文件，为每种语言分别保存到对应目录
- 输出路径: [基础路径]/multi_lang_titles/[频道名称]/[语言代码]/[视频名称].json
- 每个JSON文件只包含对应语种的标题

处理逻辑:
1. 如果目标语言在输入路径中有对应的原始视频文件，直接从该文件名获取标题
2. 如果没有原始视频文件，则从源语言翻译到目标语言
3. 所有标题都会去除#tag格式的标签

使用方法:
1. 基本使用: python title_translator_multi_lang.py [频道名称]
2. 指定目标语言: python title_translator_multi_lang.py [频道名称] -l English Korean
3. 强制重新处理: python title_translator_multi_lang.py [频道名称] -f
4. 设置批处理大小: python title_translator_multi_lang.py [频道名称] -b 20

注意:
- 需要设置环境变量UNI_API_KEY以提供OpenAI API密钥（仅在需要翻译时）
- 脚本支持断点续传，中断后可从上次停止的位置继续处理
- 输入路径与merge_mp4_mp3.py的多语言视频路径保持一致
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


def get_base_path():
    """根据操作系统类型返回对应的基础路径"""
    if platform.system() == "Darwin":  # Mac OS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


def get_mp4_input_path():
    """返回多语言MP4文件的输入路径"""
    return f"{get_base_path()}/mp4_with_audio"


def get_output_base_path():
    """返回翻译结果的输出基础路径"""
    return f"{get_base_path()}/multi_lang_titles"


# 获取输入和输出路径
MP4_INPUT_PATH = get_mp4_input_path()
OUTPUT_BASE_PATH = get_output_base_path()

# 定义支持的语言列表
LANGUAGES = ["English", "Korean"]
LANGUAGE_CODES = {"English": "en", "Japanese": "ja", "Vietnamese": "vi", "Korean": "ko"}

# 语言代码到目录名的映射（用于从输入路径查找对应语言的原始视频）
LANGUAGE_DIR_MAPPING = {"English": "english", "Korean": "korean", "Chinese": "chinese"}


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


def get_title_for_language(
    client, video_name, channel, source_language, target_language
):
    """
    获取指定语言的标题
    - 如果目标语言有原始视频文件，直接从文件名获取
    - 如果没有原始视频文件，则从源语言翻译
    """
    # 检查目标语言是否有对应的原始视频目录
    target_dir = LANGUAGE_DIR_MAPPING.get(target_language)
    if target_dir:
        target_path = os.path.join(MP4_INPUT_PATH, channel, target_dir)
        if os.path.exists(target_path):
            # 查找对应的视频文件
            target_video_file = os.path.join(target_path, f"{video_name}.mp4")
            if os.path.exists(target_video_file):
                # 直接从文件名获取标题
                title = remove_tags(video_name)
                print(f"从原始 {target_language} 视频获取标题: {title}")
                return title

    # 如果没有找到原始视频，则进行翻译
    source_title = remove_tags(video_name)
    print(f"从 {source_language} 翻译到 {target_language}: {source_title}")
    return translate_text(client, source_title, target_language)


def process_channel_language_files(
    client, channel, language, languages=None, force=False, batch_size=20
):
    """处理单个频道和语言下的所有视频标题"""
    if languages is None:
        languages = LANGUAGES

    # 定义输入路径
    mp4_input_path = os.path.join(MP4_INPUT_PATH, channel, language)

    # 检查输入路径是否存在
    if not os.path.exists(mp4_input_path):
        print(f"警告: 输入路径 '{mp4_input_path}' 不存在，跳过")
        return

    # 获取所有MP4文件，过滤掉点开头的文件
    mp4_files = [
        f
        for f in os.listdir(mp4_input_path)
        if f.endswith(".mp4") and not f.startswith(".")
    ]

    if not mp4_files:
        print(f"在频道 '{channel}' 语言 '{language}' 中未找到任何MP4文件，跳过")
        return

    print(f"\n处理频道: {channel}，源语言: {language}，找到 {len(mp4_files)} 个MP4文件")

    # 为每种目标语言创建输出目录
    output_paths = {}
    for target_lang in languages:
        lang_code = LANGUAGE_CODES[target_lang]
        output_path = os.path.join(OUTPUT_BASE_PATH, channel, lang_code)
        if not os.path.exists(output_path):
            os.makedirs(output_path, exist_ok=True)
            print(f"创建输出目录: {output_path}")
        output_paths[target_lang] = output_path

    # 收集需要处理的文件
    files_to_process = []
    for mp4_file in mp4_files:
        video_name = os.path.splitext(mp4_file)[0]  # 去掉.mp4扩展名

        # 检查是否需要处理此文件（检查所有目标语言的输出文件）
        needs_processing = False
        if force:
            needs_processing = True
        else:
            for target_lang in languages:
                output_file = os.path.join(
                    output_paths[target_lang], f"{video_name}.json"
                )
                if not os.path.exists(output_file):
                    needs_processing = True
                    break

        if needs_processing:
            files_to_process.append((video_name, mp4_file))
        else:
            print(f"跳过已处理的文件: {video_name}")

    # 如果没有需要处理的文件，返回
    if not files_to_process:
        print(f"频道 '{channel}' 语言 '{language}' 中的所有文件都已处理完毕")
        return

    print(f"需要处理 {len(files_to_process)} 个文件")

    # 批量处理文件
    with tqdm(
        total=len(files_to_process), desc=f"翻译进度 {channel}/{language}"
    ) as pbar:
        for i in range(0, len(files_to_process), batch_size):
            batch = files_to_process[i : i + batch_size]

            def process_file(file_info):
                video_name, mp4_file = file_info

                try:
                    # 确定源语言
                    source_language = "Chinese"  # 默认为中文
                    if language.lower() == "english":
                        source_language = "English"
                    elif language.lower() == "korean":
                        source_language = "Korean"

                    # 为每种目标语言获取标题并保存单独的JSON文件
                    for target_lang in languages:
                        try:
                            # 获取目标语言的标题（可能是原始文件或翻译）
                            title = get_title_for_language(
                                client,
                                video_name,
                                channel,
                                source_language,
                                target_lang,
                            )

                            # 创建JSON数据（只包含对应语种的标题）
                            json_data = {"title": title}

                            # 保存到对应语言的目录
                            output_file = os.path.join(
                                output_paths[target_lang], f"{video_name}.json"
                            )
                            with open(output_file, "w", encoding="utf-8") as f:
                                json.dump(json_data, f, ensure_ascii=False, indent=2)

                            print(f"已保存 {target_lang} 标题到: {output_file}")

                        except Exception as e:
                            print(f"处理 {target_lang} 时出错: {e}")
                            # 出错时保存原始文件名（去除标签）
                            fallback_title = remove_tags(video_name)
                            json_data = {"title": fallback_title}
                            output_file = os.path.join(
                                output_paths[target_lang], f"{video_name}.json"
                            )
                            with open(output_file, "w", encoding="utf-8") as f:
                                json.dump(json_data, f, ensure_ascii=False, indent=2)

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


def process_channel_all_languages(
    client, channel, languages=None, force=False, batch_size=20
):
    """处理指定频道下的所有语言"""
    if languages is None:
        languages = LANGUAGES

    # 检查频道路径是否存在
    channel_path = os.path.join(MP4_INPUT_PATH, channel)
    if not os.path.exists(channel_path):
        print(f"错误: 频道路径 '{channel_path}' 不存在")
        return

    # 获取所有语言目录，过滤掉点开头的目录
    language_dirs = [
        d
        for d in os.listdir(channel_path)
        if os.path.isdir(os.path.join(channel_path, d)) and not d.startswith(".")
    ]

    if not language_dirs:
        print(f"在频道 '{channel}' 中未找到任何语言目录")
        return

    print(
        f"频道 '{channel}' 找到 {len(language_dirs)} 个语言目录: {', '.join(language_dirs)}"
    )

    # 处理每个语言
    for lang_dir in language_dirs:
        process_channel_language_files(
            client, channel, lang_dir, languages, force, batch_size
        )


def process_all_channels(client, languages=None, force=False, batch_size=20):
    """处理MP4_INPUT_PATH下的所有频道"""
    if languages is None:
        languages = LANGUAGES

    # 检查输入路径是否存在
    if not os.path.exists(MP4_INPUT_PATH):
        print(f"错误: 输入路径 '{MP4_INPUT_PATH}' 不存在")
        return

    # 获取所有频道目录，过滤掉点开头的目录
    channels = [
        d
        for d in os.listdir(MP4_INPUT_PATH)
        if os.path.isdir(os.path.join(MP4_INPUT_PATH, d)) and not d.startswith(".")
    ]

    if not channels:
        print(f"在 '{MP4_INPUT_PATH}' 中未找到任何频道目录")
        return

    print(f"找到 {len(channels)} 个频道目录: {', '.join(channels)}")

    # 处理每个频道
    for channel in channels:
        print(f"\n开始处理频道: {channel}")
        process_channel_all_languages(client, channel, languages, force, batch_size)
        print(f"频道 '{channel}' 处理完成")


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="将视频标题翻译为多种语言并保存为JSON")

    # 添加命令行参数
    parser.add_argument(
        "channel",
        nargs="?",
        help="频道名称，对应视频的频道目录名称（可选，不提供则处理所有频道）",
    )
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
        "-b", "--batch_size", type=int, default=5, help="并发处理的批量大小，默认为5"
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 打印系统信息和基础路径
    print(f"检测到系统: {platform.system()}")
    print(f"使用基础路径: {get_base_path()}")
    print(f"MP4输入路径: {MP4_INPUT_PATH}")
    print(f"输出路径: {OUTPUT_BASE_PATH}")

    # 设置OpenAI客户端
    client = setup_openai_client()

    # 验证和过滤语言参数
    valid_languages = [lang for lang in args.languages if lang in LANGUAGES]
    if not valid_languages:
        print(f"错误: 未提供有效的目标语言。支持的语言有: {', '.join(LANGUAGES)}")
        return
    if set(valid_languages) != set(args.languages):
        print(f"警告: 某些语言不受支持，将只处理: {', '.join(valid_languages)}")

    # 根据是否提供channel参数来处理
    if args.channel:
        print(f"处理指定频道: {args.channel}")
        process_channel_all_languages(
            client, args.channel, valid_languages, args.force, args.batch_size
        )
    else:
        print("未指定频道，将处理所有频道")
        process_all_channels(client, valid_languages, args.force, args.batch_size)

    print("所有标题翻译任务完成!")


if __name__ == "__main__":
    main()
