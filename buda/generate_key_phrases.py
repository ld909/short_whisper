"""
多语种视频标题关键词/短语生成工具

功能说明:
此脚本用于从视频脚本内容中生成多语种的标题和重点关键词或短语。
脚本使用UNI API，GPT-4.1-mini生成：
1. 简短吸引人的视频标题
2. 简短有力的关键词或短语，以吸引观众点击观看视频
支持并发处理和断点续传功能。

输入:
- 视频脚本内容
- 已翻译的JSON文件 (来自title_translator_multi_lang.py的输出)

输出:
- 标题文件: [媒体路径]/multi_lang_title_shorten/[频道名称]/[语言代码]/[视频名称].txt
- 关键词JSON文件，包含各语言的重点关键词/短语: [媒体路径]/key_words/[频道名称]/[语言代码]/[视频名称].json

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


def generate_title(client, script_content, language, max_retries=3):
    """使用OpenAI的GPT模型根据视频脚本生成标题，失败时自动重试"""
    if not script_content.strip():
        print(f"警告: {language}的脚本内容为空，无法生成标题")
        return ""  # 如果脚本内容为空，则直接返回空字符串

    for attempt in range(max_retries):
        try:
            # 根据语言选择适当的系统提示
            system_prompt = f"你是一个标题生成大师，精通多语种标题生成，生成的标题非常具有吸引力，别人一看就想点进来看，生成标题的具有很强的吸引力。给出你视频的全部脚本，返回一个精炼的标题，不要太长，返回内容使用python length(标题）不超过100, 稳当点，别超长了。直接返回{language}的精妙的标题，返回的内容是对应{language}。"

            completion = client.chat.completions.create(
                model="gpt-4.1-mini",
                max_tokens=200,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": script_content},
                ],
                timeout=30,  # 增加超时时间为30秒
            )
            result = completion.choices[0].message.content
            # 将换行符替换为空格
            result = result.replace("\n", " ")
            # 检查标题长度
            if len(result) > 100:
                print(
                    f"警告: 生成的{language}标题长度超过100 ({len(result)}字符)，将被截断"
                )
                result = result[:97] + "..."

            print(f"已成功生成{language}标题: {result}")
            return result
        except Exception as e:
            print(f"生成标题出错 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                retry_delay = (attempt + 1) * 3  # 逐步增加延迟时间
                print(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)  # 添加延迟，避免过快请求
            else:
                print(f"达到最大重试次数 ({max_retries})，返回空结果")
                return ""  # 如果所有尝试都失败，返回空字符串


def get_script_content(video_name, channel):
    """获取视频脚本内容"""
    # 假设脚本文件的位置在特定目录下
    script_path = os.path.join(BASE_MEDIA_PATH, "scripts", channel, f"{video_name}.txt")

    print(f"尝试读取脚本文件: {script_path}")

    # 确保scripts/channel目录存在
    script_dir = os.path.dirname(script_path)
    if not os.path.exists(script_dir):
        try:
            os.makedirs(script_dir, exist_ok=True)
            print(f"创建脚本目录: {script_dir}")
        except Exception as e:
            print(f"创建脚本目录失败: {e}")

    if not os.path.exists(script_path):
        print(f"警告: 未找到视频脚本文件: {script_path}")
        # 尝试查找其他可能的位置
        alternative_paths = [
            os.path.join(
                BASE_MEDIA_PATH, "zh_subtitle_split_txt", channel, f"{video_name}.txt"
            ),
            os.path.join(
                BASE_MEDIA_PATH, "multi_lang_txt", channel, "en", f"{video_name}.txt"
            ),
        ]

        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                print(f"找到替代脚本文件: {alt_path}")
                try:
                    with open(alt_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    # 可选：复制到正确位置
                    try:
                        with open(script_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        print(f"已将替代脚本复制到标准位置: {script_path}")
                    except Exception as e:
                        print(f"复制脚本文件失败: {e}")
                    return content
                except Exception as e:
                    print(f"读取替代脚本文件出错: {e}")
                    continue

        return ""  # 如果找不到任何脚本文件，返回空字符串

    try:
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()
            print(f"成功读取脚本文件，字符数: {len(content)}")
            return content
    except Exception as e:
        print(f"读取脚本文件出错: {e}")
        return ""


def process_title_file(
    client, channel, video_name, title_file, languages=None, force=False
):
    """处理单个标题文件，为每种语言生成标题和关键词/短语"""
    if languages is None:
        languages = LANGUAGES

    try:
        # 读取已翻译的标题文件
        with open(title_file, "r", encoding="utf-8") as f:
            translations = json.load(f)

        # 获取视频脚本内容
        script_content = get_script_content(video_name, channel)
        if not script_content.strip():
            print(f"警告: 未找到视频脚本内容: {video_name}，将使用已翻译标题代替")

        # 初始化结果字典
        result = {}

        # 为每种语言生成标题和关键词/短语
        for lang in languages:
            lang_code = LANGUAGE_CODES[lang]

            # 检查标题文件中是否包含此语言的翻译
            if lang_code not in translations:
                print(f"警告: 标题文件中没有 {lang} 翻译，跳过")
                continue

            # 获取此语言的已翻译标题
            translated_title = translations[lang_code]

            # 为关键词/短语创建输出目录
            keywords_dir = os.path.join(
                BASE_MEDIA_PATH, "key_words", channel, lang_code
            )
            os.makedirs(keywords_dir, exist_ok=True)

            # 为自动生成标题创建输出目录
            title_dir = os.path.join(
                BASE_MEDIA_PATH, "multi_lang_title_shorten", channel, lang_code
            )
            os.makedirs(title_dir, exist_ok=True)

            # 定义输出文件路径
            keywords_file = os.path.join(keywords_dir, f"{video_name}.json")
            title_file_output = os.path.join(title_dir, f"{video_name}.txt")

            # 检查是否需要生成关键词/短语
            keywords_generated = False
            if os.path.exists(keywords_file) and not force:
                try:
                    with open(keywords_file, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                    if existing_data:  # 如果文件存在且有内容，跳过
                        print(f"跳过已处理的 {lang} 关键词/短语: {video_name}")
                        keywords_generated = True
                except (json.JSONDecodeError, FileNotFoundError):
                    # 文件损坏或不完整，需要重新处理
                    pass

            # 检查是否需要生成标题
            title_generated = False
            if os.path.exists(title_file_output) and not force:
                try:
                    with open(title_file_output, "r", encoding="utf-8") as f:
                        existing_title = f.read().strip()
                    if existing_title:  # 如果文件存在且有内容，跳过
                        print(f"跳过已处理的 {lang} 标题: {video_name}")
                        title_generated = True
                except FileNotFoundError:
                    # 文件不存在，需要生成
                    pass

            # 生成关键词/短语（如果需要）
            if not keywords_generated:
                print(f"为 {video_name} 生成 {lang} 关键词/短语...")
                key_phrases = generate_key_phrases(client, translated_title, lang)

                # 保存关键词/短语结果
                result[f"{lang_code}_keywords"] = key_phrases

                # 单独保存到每种语言的目录
                with open(keywords_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {"key_phrases": key_phrases, "title": translated_title},
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )
                print(f"已保存 {lang} 关键词/短语到: {keywords_file}")

            # 生成标题（如果需要）
            if not title_generated:
                print(f"为 {video_name} 生成 {lang} 标题...")
                # 如果有脚本内容，则使用脚本生成标题，否则使用已翻译标题
                content_for_title = (
                    script_content if script_content.strip() else translated_title
                )
                new_title = generate_title(client, content_for_title, lang)

                # 如果生成的标题为空，则使用已翻译的标题
                if not new_title:
                    print(f"警告: 生成的{lang}标题为空，将使用已翻译标题")
                    new_title = translated_title

                # 保存标题结果
                result[f"{lang_code}_title"] = new_title

                # 保存到每种语言的目录
                try:
                    with open(title_file_output, "w", encoding="utf-8") as f:
                        f.write(new_title)
                    print(f"已保存 {lang} 标题到: {title_file_output}")
                except Exception as e:
                    print(f"保存{lang}标题到{title_file_output}时出错: {e}")

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
        print(f"提示: 频道 '{channel}' 的已翻译标题目录不存在: {input_path}")
        os.makedirs(input_path, exist_ok=True)
        return

    # 获取所有JSON标题文件，过滤掉点开头的文件
    title_files = [
        f
        for f in os.listdir(input_path)
        if f.endswith(".json") and not f.startswith(".")
    ]

    if not title_files:
        print(f"在频道 '{channel}' 中未找到任何已翻译的标题文件，跳过")
        return

    # 确保所有输出目录存在
    for lang in languages:
        lang_code = LANGUAGE_CODES[lang]
        # 创建关键词输出目录
        keywords_dir = os.path.join(BASE_MEDIA_PATH, "key_words", channel, lang_code)
        if not os.path.exists(keywords_dir):
            os.makedirs(keywords_dir, exist_ok=True)
            print(f"已创建关键词目录: {keywords_dir}")

        # 创建标题输出目录
        title_dir = os.path.join(
            BASE_MEDIA_PATH, "multi_lang_title_shorten", channel, lang_code
        )
        if not os.path.exists(title_dir):
            os.makedirs(title_dir, exist_ok=True)
            print(f"已创建标题目录: {title_dir}")

    print(f"\n处理频道: {channel}，找到 {len(title_files)} 个已翻译标题文件")

    # 收集需要处理的文件
    files_to_process = []
    for title_file in title_files:
        video_name = os.path.splitext(title_file)[0]  # 去掉.json扩展名
        full_title_path = os.path.join(input_path, title_file)

        # 标记是否需要处理此文件
        need_processing = force  # 如果强制重新生成，则肯定需要处理

        if not need_processing:
            # 检查是否所有语言的关键词/短语都已存在
            for lang in languages:
                lang_code = LANGUAGE_CODES[lang]
                keywords_file = os.path.join(
                    BASE_MEDIA_PATH,
                    "key_words",
                    channel,
                    lang_code,
                    f"{video_name}.json",
                )
                title_file_output = os.path.join(
                    BASE_MEDIA_PATH,
                    "multi_lang_title_shorten",
                    channel,
                    lang_code,
                    f"{video_name}.txt",
                )

                if not os.path.exists(keywords_file) or not os.path.exists(
                    title_file_output
                ):
                    need_processing = True
                    break

        if need_processing:
            files_to_process.append((video_name, full_title_path))

    # 如果没有需要处理的文件，返回
    if not files_to_process:
        print(f"频道 '{channel}' 中的所有标题文件都已处理完毕")
        return

    print(f"需要处理 {len(files_to_process)} 个文件")

    # 批量处理文件
    with tqdm(total=len(files_to_process), desc="生成标题和关键词/短语进度") as pbar:
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

    # 检查输入路径是否存在，如果不存在则创建
    if not os.path.exists(input_base_path):
        print(f"提示: 已翻译标题的基础路径 '{input_base_path}' 不存在，将创建此目录")
        os.makedirs(input_base_path, exist_ok=True)
        print(f"已创建目录: {input_base_path}")
        return

    # 获取所有频道目录，过滤掉点开头的目录
    channels = [
        d
        for d in os.listdir(input_base_path)
        if os.path.isdir(os.path.join(input_base_path, d)) and not d.startswith(".")
    ]

    if not channels:
        print(f"在 '{input_base_path}' 中未找到任何频道目录")
        return

    print(f"找到 {len(channels)} 个频道目录")

    # 处理每个频道
    for channel in channels:
        process_channel(client, channel, languages, force, batch_size)


def ensure_base_directories():
    """确保所有基础目录都存在"""
    # 创建多语种标题基础目录
    titles_base_dir = os.path.join(BASE_MEDIA_PATH, "multi_lang_titles")
    if not os.path.exists(titles_base_dir):
        os.makedirs(titles_base_dir, exist_ok=True)
        print(f"已创建多语种标题基础目录: {titles_base_dir}")

    # 为每种语言创建频道子目录，过滤掉点开头的目录
    for channel in [d for d in os.listdir(titles_base_dir) if not d.startswith(".")]:
        channel_path = os.path.join(titles_base_dir, channel)
        if os.path.isdir(channel_path):
            # 创建多语种生成标题目录结构
            for lang in LANGUAGES:
                lang_code = LANGUAGE_CODES[lang]

                # 创建生成标题目录
                shorten_title_dir = os.path.join(
                    BASE_MEDIA_PATH, "multi_lang_title_shorten", channel, lang_code
                )
                if not os.path.exists(shorten_title_dir):
                    os.makedirs(shorten_title_dir, exist_ok=True)
                    print(
                        f"已创建{channel}频道的{lang}生成标题目录: {shorten_title_dir}"
                    )

                # 创建关键词目录
                keywords_dir = os.path.join(
                    BASE_MEDIA_PATH, "key_words", channel, lang_code
                )
                if not os.path.exists(keywords_dir):
                    os.makedirs(keywords_dir, exist_ok=True)
                    print(f"已创建{channel}频道的{lang}关键词目录: {keywords_dir}")

    # 创建多语种生成标题基础目录
    generated_titles_base_dir = os.path.join(
        BASE_MEDIA_PATH, "multi_lang_title_shorten"
    )
    if not os.path.exists(generated_titles_base_dir):
        os.makedirs(generated_titles_base_dir, exist_ok=True)
        print(f"已创建生成标题基础目录: {generated_titles_base_dir}")

    # 创建关键词基础目录
    keywords_base_dir = os.path.join(BASE_MEDIA_PATH, "key_words")
    if not os.path.exists(keywords_base_dir):
        os.makedirs(keywords_base_dir, exist_ok=True)
        print(f"已创建关键词基础目录: {keywords_base_dir}")

    # 创建脚本基础目录
    scripts_base_dir = os.path.join(BASE_MEDIA_PATH, "scripts")
    if not os.path.exists(scripts_base_dir):
        os.makedirs(scripts_base_dir, exist_ok=True)
        print(f"已创建脚本基础目录: {scripts_base_dir}")

    # 检查所有目录的写入权限
    all_dirs = [
        titles_base_dir,
        generated_titles_base_dir,
        keywords_base_dir,
        scripts_base_dir,
    ]

    for directory in all_dirs:
        if os.path.exists(directory):
            if not os.access(directory, os.W_OK):
                print(f"警告: 无法写入目录 {directory}，请检查权限")
        else:
            print(f"警告: 目录不存在 {directory}，已尝试创建但可能失败")


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description="从视频脚本内容中生成多语种标题和关键词/短语"
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
        help="强制重新生成标题和关键词/短语，忽略已有文件",
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

    # 确保基础目录存在
    ensure_base_directories()

    # 处理所有频道和标题
    process_all_channels(client, valid_languages, args.force, args.batch_size)

    print("所有标题和关键词/短语生成任务完成!")


if __name__ == "__main__":
    main()
