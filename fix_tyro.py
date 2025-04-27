import os
import re
import sys
import json
import argparse
from tqdm import tqdm
from openai import OpenAI


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
        subtitles.append(
            {
                "index": int(index),
                "start_time": start_time,
                "end_time": end_time,
                "text": subtitle,
            }
        )

    return subtitles


def save_subtitle_item(subtitle_item, output_path, mode="a"):
    """保存单个字幕项到文件"""
    with open(output_path, mode, encoding="utf-8") as f:
        f.write(f"{subtitle_item['index']}\n")
        f.write(f"{subtitle_item['start_time']} --> {subtitle_item['end_time']}\n")
        f.write(f"{subtitle_item['text']}\n\n")


def setup_ali_client():
    """设置阿里云千问大模型客户端"""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("错误: 环境变量 DASHSCOPE_API_KEY 未设置！请设置API密钥。")
        print("设置方法: export DASHSCOPE_API_KEY=你的密钥")
        sys.exit(1)

    client = OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    return client


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


def fix_typos(subtitle, api_type="ali"):
    """使用指定的大模型检查并修复字幕中的错别字"""
    tyro_dict = {"元气": "缘起"}
    system_prompt = f'你是一个字幕错别字检查专家，只对错别字进行修正,内容是佛教/佛学的主题，\
        文字来自于一个语音转文字的模型，有些字是发音对了，但字没有对，需特别注意。\
            有些词发音对了，但不是佛教名词，修改为专业的佛教名、人名、地名、专有名词，比如参考{tyro_dict}\
                注意专业词汇。如果句子没有错别字，仅回复数字"111"；\
                    如果有错别字，请返回修复后的完整句子，直接返回新句子,不要返回修改前的句子，不要返回类似于：【原句】，修改后：【新句】这样的错误结构。不要对任何其他作修改，不要修改标点、引号等内容，不要增加任何内容。'

    try:
        if api_type == "ali":
            client = setup_ali_client()
            model = "qwen-max-0125"
        else:  # api_type == "uni"
            client = setup_uni_client()
            model = "gpt-4.1-mini"

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f'检查这个字幕是否有错别字："{subtitle}"'},
            ],
        )

        response = completion.choices[0].message.content.strip()

        # 去除可能添加的中英文引号
        response = response.strip('"\'""' "")

        # 打印原句和大模型返回的结果
        print(f"原句: {subtitle}")
        print(f"AI返回: {response}")

        # 如果回复是"111"，表示无错误，返回原句
        if response == "111":
            print("结果: 无需修改")
            return subtitle
        else:
            print(f"结果: 已修正为: {response}")
            return response
    except Exception as e:
        print(f"API调用错误：{e}")
        return subtitle  # 发生错误时返回原句


def get_progress_file_path():
    """获取进度文件路径"""
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "tyro_fix_progress.json"
    )


def load_progress():
    """加载处理进度"""
    progress_file = get_progress_file_path()
    if os.path.exists(progress_file):
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"读取进度文件时出错: {e}")
            return {}
    return {}


def save_progress(channel, srt_file, last_index):
    """保存处理进度"""
    progress_file = get_progress_file_path()
    progress = load_progress()

    if channel not in progress:
        progress[channel] = {}

    progress[channel][srt_file] = last_index

    try:
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存进度文件时出错: {e}")


def check_output_file_progress(output_file_path, total_subtitles):
    """检查输出文件的实际完成进度"""
    if not os.path.exists(output_file_path):
        return 0, False  # 文件不存在，进度为0，未完成

    try:
        with open(output_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 计算已处理的字幕条目数
        pattern = re.compile(
            r"(\d+)\s+(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})"
        )
        matches = pattern.findall(content)
        processed_count = len(matches)

        # 检查是否完全处理
        is_completed = processed_count >= total_subtitles

        return processed_count, is_completed
    except Exception as e:
        print(f"检查输出文件时出错: {e}")
        return 0, False


def process_srt_file(input_path, output_path, channel, srt_file, api_type):
    """处理单个SRT文件，逐句修复错别字并保存"""
    print(f"正在处理：{input_path}")

    try:
        # 读取SRT文件内容
        srt_content = read_srt_file(input_path)

        # 解析SRT内容
        subtitles = parse_srt_with_re(srt_content)

        if not subtitles:
            print(f"警告: 文件 {input_path} 似乎没有有效的字幕内容")
            return

        # 检查输出文件的实际进度
        file_progress, is_file_completed = check_output_file_progress(
            output_path, len(subtitles)
        )

        # 如果输出文件已完全处理，则跳过
        if is_file_completed:
            print(f"文件 {srt_file} 已完全处理（根据输出文件检查），跳过")
            # 同步JSON进度文件
            save_progress(channel, srt_file, len(subtitles))
            return

        # 如果输出文件存在但不完整，则从断点继续
        start_index = file_progress
        if file_progress > 0:
            print(f"检测到输出文件，从字幕 #{start_index+1} 继续处理")
            # 同步JSON进度文件
            save_progress(channel, srt_file, start_index)
        else:
            # 如果是新文件，先清空输出文件
            with open(output_path, "w", encoding="utf-8") as f:
                pass

        # 修复错别字 - 只处理未处理的部分
        for i, subtitle in enumerate(tqdm(subtitles[start_index:], desc="修复错别字")):
            real_index = i + start_index
            print(f"\n字幕 #{real_index+1}/{len(subtitles)}:")

            # 修复错别字
            fixed_text = fix_typos(subtitle["text"], api_type)
            subtitle["text"] = fixed_text

            # 立即写入单个字幕项
            save_subtitle_item(subtitle, output_path, "a")

            # 保存当前进度
            save_progress(channel, srt_file, real_index + 1)

            print("-" * 50)

        print(f"已完成文件处理：{output_path}")

    except Exception as e:
        print(f"处理文件时出错: {input_path}")
        print(f"错误信息: {str(e)}")


def main():
    """处理指定目录结构中的中文SRT文件"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="修复SRT字幕文件中的错别字")
    parser.add_argument(
        "-a",
        "--api",
        default="ali",
        choices=["ali", "uni"],
        help="选择使用的API服务（ali=阿里云千问模型，uni=uniapi）",
    )
    parser.add_argument(
        "-i",
        "--input",
        default="/media/dhl/buda_videos_youtube/format_srt_zh/mp3",
        help="输入SRT基础目录路径",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="/media/dhl/buda_videos_youtube/zh_srt_tyro_fix",
        help="输出SRT基础目录路径",
    )

    # 解析命令行参数
    args = parser.parse_args()
    input_base_dir = args.input
    output_base_dir = args.output
    api_type = args.api

    print(f"使用 {api_type} API 进行错别字修复")

    # 检查输入目录是否存在
    if not os.path.exists(input_base_dir):
        print(f"错误: 输入目录不存在: {input_base_dir}")
        return

    # 确保输出基础目录存在
    if not os.path.exists(output_base_dir):
        os.makedirs(output_base_dir)
        print(f"已创建输出基础目录: {output_base_dir}")

    # 检查API密钥是否设置
    if api_type == "ali" and not os.getenv("DASHSCOPE_API_KEY"):
        print("错误: 环境变量 DASHSCOPE_API_KEY 未设置！请设置API密钥。")
        print("设置方法: export DASHSCOPE_API_KEY=你的密钥")
        return
    elif api_type == "uni" and not os.getenv("UNI_API_KEY"):
        print("错误: 环境变量 UNI_API_KEY 未设置！请设置API密钥。")
        print("设置方法: export UNI_API_KEY=你的密钥")
        return

    # 获取所有频道目录
    try:
        channels = [
            d
            for d in os.listdir(input_base_dir)
            if os.path.isdir(os.path.join(input_base_dir, d))
        ]
        print(f"找到 {len(channels)} 个频道目录")

        if not channels:
            print(f"警告: 在 {input_base_dir} 中未找到任何频道目录")
            return
    except Exception as e:
        print(f"无法读取频道目录: {str(e)}")
        return

    for channel in channels:
        input_channel_dir = os.path.join(input_base_dir, channel)
        output_channel_dir = os.path.join(output_base_dir, channel)

        print(f"\n处理频道: {channel}")
        print(f"输入目录: {input_channel_dir}")
        print(f"输出目录: {output_channel_dir}")

        # 确保输出频道目录存在
        if not os.path.exists(output_channel_dir):
            os.makedirs(output_channel_dir)
            print(f"已创建频道输出目录: {output_channel_dir}")

        # 获取当前频道下的所有SRT文件
        try:
            srt_files = [f for f in os.listdir(input_channel_dir) if f.endswith(".srt")]
            print(f"找到 {len(srt_files)} 个SRT文件")

            if not srt_files:
                print(f"警告: 在频道 {channel} 中未找到任何SRT文件")
                continue
        except Exception as e:
            print(f"无法读取频道 {channel} 中的SRT文件: {str(e)}")
            continue

        for srt_file in srt_files:
            input_file_path = os.path.join(input_channel_dir, srt_file)
            output_file_path = os.path.join(output_channel_dir, srt_file)

            # 使用新的处理函数处理文件
            process_srt_file(
                input_file_path, output_file_path, channel, srt_file, api_type
            )


if __name__ == "__main__":
    main()
