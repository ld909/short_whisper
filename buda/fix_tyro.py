#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SRT字幕错别字修复工具 - 简化版

功能描述：
    使用大模型API自动检查和修复SRT字幕文件中的错别字，特别针对佛教/佛学主题内容优化。
    支持并发处理、断点续传、多种API服务、智能重试机制。

默认路径：
    Linux系统输入路径：/media/dhl/buda_videos_youtube/format_srt_zh
    macOS系统输入路径：/Volumes/dhl/buda_videos_youtube/format_srt_zh

    Linux系统输出路径：/media/dhl/buda_videos_youtube/zh_srt_tyro_fix
    macOS系统输出路径：/Volumes/dhl/buda_videos_youtube/zh_srt_tyro_fix

使用方法：
    1. 基本使用（使用默认路径和uniapi）：
       python fix_tyro.py

    2. 使用阿里云千问API：
       python fix_tyro.py -a ali

    3. 自定义输入输出路径：
       python fix_tyro.py -i /path/to/input -o /path/to/output

    4. 使用本地目录输出（避免权限问题）：
       python fix_tyro.py -l

    5. 调整并发数量：
       python fix_tyro.py -b 10

    6. 调整重试次数（处理网络不稳定）：
       python fix_tyro.py -r 5

    7. 限制新处理文件数量（从未完成的文件中选择10个进行处理）：
       python fix_tyro.py -n 10

    8. 强制重新处理所有文件（忽略断点续传）：
       python fix_tyro.py -f

命令行参数：
    -a, --api {ali,uni}     选择API服务（ali=阿里云千问，uni=uniapi，默认uni）
    -i, --input PATH        输入SRT文件基础目录路径（默认使用系统对应的挂载路径）
    -o, --output PATH       输出SRT文件基础目录路径
    -l, --local             使用本地目录 ~/srt_fixed 作为输出（避免权限问题）
    -b, --batch_size NUM    并发处理批量大小（默认5）
    -r, --max_retries NUM   API调用失败时的最大重试次数（默认3次）
    -n, --max_files NUM     最大新处理文件数量（从未完成的文件中选择指定数量处理，默认处理所有未完成文件）
    -f, --force             强制重新处理所有文件，忽略断点续传
    -h, --help             显示帮助信息

环境变量设置：
    使用阿里云千问API时：
        export DASHSCOPE_API_KEY=你的阿里云API密钥

    使用uniapi时：
        export UNI_API_KEY=你的uniapi密钥

作者：dhl
版本：2.1 - 简化日志版本
"""

import os
import re
import sys
import argparse
import platform
import time
import datetime
from tqdm import tqdm
from openai import OpenAI
import concurrent.futures
from threading import Lock

# 全局统计变量
api_stats = {
    "total_calls": 0,
    "successful_calls": 0,
    "failed_calls": 0,
    "retry_calls": 0,
    "rate_limit_errors": 0,
    "network_errors": 0,
    "auth_errors": 0,
    "model_errors": 0,
    "unknown_errors": 0,
}
stats_lock = Lock()


def update_api_stats(stat_type):
    """线程安全地更新API统计信息"""
    with stats_lock:
        if stat_type in api_stats:
            api_stats[stat_type] += 1


def print_api_stats():
    """打印API调用统计信息"""
    with stats_lock:
        print(f"\n📊 API调用统计报告:")
        print(f"🔧 总调用次数: {api_stats['total_calls']}")
        print(f"✅ 成功调用: {api_stats['successful_calls']}")
        print(f"❌ 失败调用: {api_stats['failed_calls']}")
        print(f"🔄 重试次数: {api_stats['retry_calls']}")

        if api_stats["total_calls"] > 0:
            success_rate = (
                api_stats["successful_calls"] / api_stats["total_calls"]
            ) * 100
            print(f"📈 成功率: {success_rate:.1f}%")

        if api_stats["failed_calls"] > 0:
            print(f"⚠️  错误分类:")
            if api_stats["rate_limit_errors"] > 0:
                print(f"   💤 API限流: {api_stats['rate_limit_errors']}")
            if api_stats["network_errors"] > 0:
                print(f"   🌐 网络错误: {api_stats['network_errors']}")
            if api_stats["auth_errors"] > 0:
                print(f"   🔐 认证错误: {api_stats['auth_errors']}")
            if api_stats["model_errors"] > 0:
                print(f"   🤖 模型错误: {api_stats['model_errors']}")
            if api_stats["unknown_errors"] > 0:
                print(f"   ❓ 未知错误: {api_stats['unknown_errors']}")


def read_srt_file(file_path):
    """读取SRT文件并返回内容"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            srt_content = f.read()
        return srt_content
    except Exception as e:
        print(f"❌ 读取文件失败 {file_path}: {e}")
        raise


def parse_srt_with_re(srt_content):
    """使用正则表达式解析SRT字幕内容"""
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
    try:
        with open(output_path, mode, encoding="utf-8") as f:
            f.write(f"{subtitle_item['index']}\n")
            f.write(f"{subtitle_item['start_time']} --> {subtitle_item['end_time']}\n")
            f.write(f"{subtitle_item['text']}\n\n")
        return True
    except Exception as e:
        print(f"❌ 保存字幕失败: {e}")
        return False


def setup_ali_client():
    """设置阿里云千问大模型客户端"""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ 环境变量 DASHSCOPE_API_KEY 未设置！")
        print("💡 设置方法: export DASHSCOPE_API_KEY=你的密钥")
        sys.exit(1)

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        return client
    except Exception as e:
        print(f"❌ 设置阿里云千问API客户端失败: {e}")
        raise


def setup_uni_client():
    """设置uniapi大模型客户端"""
    api_key = os.getenv("UNI_API_KEY")
    if not api_key:
        print("❌ 环境变量 UNI_API_KEY 未设置！")
        print("💡 设置方法: export UNI_API_KEY=你的密钥")
        sys.exit(1)

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.uniapi.io/v1",
        )
        return client
    except Exception as e:
        print(f"❌ 设置uniapi客户端失败: {e}")
        raise


def fix_typos(subtitle, context="", api_type="ali", max_retries=3):
    """使用指定的大模型检查并修复字幕中的错别字，包含重试机制"""
    tyro_dict = {
        "元气": "缘起",
        "吟念": "淫念",
        "须云菩提": "须菩提",
        "师尊": "释尊",
        "世尊": "释尊",
    }

    system_prompt = f'你是一个字幕错别字检查专家，只对错别字进行修正,内容是佛教/佛学的主题，\
        文字来自于一个语音转文字的模型，有些字是发音对了，但字没有对，需特别注意。\
            有些词发音对了，但不是佛教名词，修改为专业的佛教名、人名、地名、经文名和专有名词，佛教中多用男他而非女她。常见错误参考{tyro_dict}\
                一定要注意专业词汇，要专业。如果句子没有错别字，仅回复数字"111"；\
                    如果有错别字，请返回修复后的完整句子，直接返回新句子,不要返回修改前的句子，不要返回类似于：【原句】，修改后：【新句】这样的错误结构。不要对任何其他作修改，不要修改标点、引号等内容，不要增加任何内容。'

    update_api_stats("total_calls")

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                wait_time = 2**attempt
                time.sleep(wait_time)
                update_api_stats("retry_calls")

            if api_type == "ali":
                client = setup_ali_client()
                model = "qwen-max-0125"
            else:  # api_type == "uni"
                client = setup_uni_client()
                model = "doubao-seed-1-6-250615"

            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f'检查这个句子是否有错别字："{subtitle}"。',
                    },
                ],
            )

            response = completion.choices[0].message.content.strip()
            update_api_stats("successful_calls")

            # 去除可能添加的中英文引号
            response = response.strip('"\'""' "")

            # 打印原句和大模型返回的结果
            print(f"📝 原句: {subtitle}")
            print(f"🤖 AI返回: {response}")

            # 如果回复是"111"，表示无错误，返回原句
            if response == "111":
                print("✅ 无需修改")
                print("─" * 50)  # 添加分割线
                return subtitle
            else:
                print("🔧 已修正")
                print("─" * 50)  # 添加分割线
                return response

        except Exception as e:
            error_message = str(e).lower()

            # 分类处理不同类型的错误
            if "rate limit" in error_message or "limit exceeded" in error_message:
                update_api_stats("rate_limit_errors")
                if attempt < max_retries:
                    wait_time = 30 + (attempt * 10)
                    print(f"💤 API限流，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue

            elif (
                "connection" in error_message
                or "timeout" in error_message
                or "network" in error_message
            ):
                update_api_stats("network_errors")
                if attempt < max_retries:
                    continue

            elif (
                "unauthorized" in error_message
                or "authentication" in error_message
                or "api_key" in error_message
            ):
                update_api_stats("auth_errors")
                print(f"🔐 API认证错误，请检查API密钥: {e}")
                break

            elif "not found" in error_message or "invalid model" in error_message:
                update_api_stats("model_errors")
                print(f"🤖 模型配置错误: {e}")
                break

            else:
                update_api_stats("unknown_errors")
                if attempt < max_retries:
                    continue

    # 所有重试都失败了
    update_api_stats("failed_calls")
    print(f"❌ API调用失败：{e}")
    print("⚠️ 保持原句不变")
    print("─" * 50)  # 添加分割线
    return subtitle


def check_output_file_progress(output_file_path, total_subtitles):
    """检查输出文件的实际完成进度"""
    if not os.path.exists(output_file_path):
        return 0, False

    try:
        with open(output_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        pattern = re.compile(
            r"(\d+)\s+(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})"
        )
        matches = pattern.findall(content)
        processed_count = len(matches)
        is_completed = processed_count >= total_subtitles

        return processed_count, is_completed
    except Exception as e:
        return 0, False


def process_subtitles_concurrently(
    subtitles, fixed_subtitles, api_type, output_path, batch_size=5, max_retries=3
):
    """并发处理字幕，同时保持顺序并实时写入文件"""
    results = {}
    lock = Lock()

    def process_subtitle(index, subtitle):
        """处理单个字幕的函数"""
        fixed_text = fix_typos(subtitle["text"], "", api_type, max_retries)
        with lock:
            results[index] = fixed_text
        return index, fixed_text

    # 使用 ThreadPoolExecutor 进行并发处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
        # 提交所有任务
        future_to_index = {
            executor.submit(process_subtitle, i, subtitle): i
            for i, subtitle in enumerate(subtitles)
        }

        # 按顺序获取结果并实时写入文件
        for i in range(len(subtitles)):
            while i not in results:
                # 等待当前索引的结果
                completed, _ = concurrent.futures.wait(
                    [f for f, idx in future_to_index.items() if idx == i],
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )

            # 已获取当前索引的结果，更新字幕
            subtitles[i]["text"] = results[i]
            fixed_subtitles.append(results[i])

            # 立即将该字幕写入文件
            with lock:
                save_subtitle_item(subtitles[i], output_path)

    return subtitles


def process_srt_file(
    input_path,
    output_path,
    channel,
    srt_file,
    api_type,
    batch_size=5,
    max_retries=3,
    force_reprocess=False,
):
    """处理单个SRT文件，并发修复错别字并保存"""
    print(f"\n🎬 处理文件: {channel}/{srt_file}")

    try:
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            print(f"❌ 输入文件不存在: {input_path}")
            return

        # 检查输出目录权限
        output_dir = os.path.dirname(output_path)
        if not os.access(output_dir, os.W_OK):
            print(f"❌ 没有权限写入目录 {output_dir}")
            return

        # 读取和解析SRT文件
        srt_content = read_srt_file(input_path)
        subtitles = parse_srt_with_re(srt_content)

        if not subtitles:
            print(f"⚠️  文件似乎没有有效的字幕内容")
            return

        print(f"📚 找到 {len(subtitles)} 个字幕条目")

        # 检查输出文件的实际进度
        file_progress, is_file_completed = check_output_file_progress(
            output_path, len(subtitles)
        )

        # 如果输出文件已完全处理且不是强制重新处理，则跳过
        if is_file_completed and not force_reprocess:
            print(f"✅ 文件已完全处理，跳过")
            return
        elif force_reprocess and is_file_completed:
            print(f"🔄 强制重新处理文件")
            file_progress = 0

        # 处理逻辑
        start_index = file_progress
        if file_progress > 0 and not force_reprocess:
            print(f"⚡ 断点续传，从第 {start_index+1} 个字幕继续")
        else:
            # 创建新的输出文件
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    pass
            except PermissionError:
                print(f"❌ 没有权限创建文件 {output_path}")
                return

        # 用于保存已修复的字幕，作为上下文
        fixed_subtitles = []

        # 如果从中间继续处理，读取已处理的字幕
        if start_index > 0:
            with open(output_path, "r", encoding="utf-8") as f:
                output_content = f.read()
            processed_subtitles = parse_srt_with_re(output_content)
            fixed_subtitles.extend(
                [subtitle["text"] for subtitle in processed_subtitles]
            )

        # 并发修复错别字 - 只处理未处理的部分
        remaining_subtitles = subtitles[start_index:]
        print(f"🚀 开始处理剩余的 {len(remaining_subtitles)} 个字幕")

        if remaining_subtitles:
            with tqdm(
                total=len(remaining_subtitles), desc="🔧 修复错别字", ncols=80
            ) as pbar:
                processed_subtitles = process_subtitles_concurrently(
                    remaining_subtitles,
                    fixed_subtitles,
                    api_type,
                    output_path,
                    batch_size,
                    max_retries,
                )

                # 更新进度条
                for _ in range(len(remaining_subtitles)):
                    pbar.update(1)

        print(f"✅ 文件处理完成: {srt_file}")

    except PermissionError as e:
        print(f"❌ 权限错误: {e}")
    except Exception as e:
        print(f"❌ 处理文件时出错: {e}")


def get_transcription_base_path():
    """获取转录文件的基础路径（实际SRT文件位置）"""
    if platform.system() == "Darwin":  # Mac OS
        return "/Volumes/dhl/buda_videos_youtube/format_srt_zh"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube/format_srt_zh"


def get_base_path():
    """根据操作系统类型返回对应的基础路径（用于输出）"""
    if platform.system() == "Darwin":  # Mac OS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


def main():
    """处理指定目录结构中的中文SRT文件"""
    print("🎯 SRT字幕错别字修复工具启动")

    # 获取基础路径
    base_path = get_base_path()
    transcription_base_path = get_transcription_base_path()
    home_path = os.path.expanduser("~")

    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="修复SRT字幕文件中的错别字")
    parser.add_argument(
        "-a",
        "--api",
        default="uni",
        choices=["ali", "uni"],
        help="选择使用的API服务（ali=阿里云千问模型，uni=uniapi）",
    )

    parser.add_argument(
        "-i",
        "--input",
        default=None,
        help="输入SRT基础目录路径（默认使用mp3toscripts_faster.py的输出路径）",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=f"{base_path}/zh_srt_tyro_fix",
        help="输出SRT基础目录路径",
    )
    parser.add_argument(
        "-l",
        "--local",
        action="store_true",
        help="使用本地目录作为输出（避免权限问题）",
    )
    parser.add_argument(
        "-b",
        "--batch_size",
        type=int,
        default=5,
        help="并发处理的批量大小",
    )
    parser.add_argument(
        "-r",
        "--max_retries",
        type=int,
        default=3,
        help="API调用失败时的最大重试次数（默认3次）",
    )
    parser.add_argument(
        "-n",
        "--max_files",
        type=int,
        default=None,
        help="最大新处理文件数量（从未完成的文件中选择指定数量处理，默认处理所有未完成文件）",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="强制重新处理所有文件，忽略断点续传",
    )

    # 解析命令行参数
    args = parser.parse_args()
    api_type = args.api
    batch_size = args.batch_size
    max_retries = args.max_retries
    max_files = args.max_files
    force_reprocess = args.force

    print(f"🔧 配置: API={api_type}, 并发={batch_size}, 重试={max_retries}")

    # 设置输入路径
    if args.input is None:
        input_base_dir = transcription_base_path
    else:
        input_base_dir = args.input

    output_base_dir = args.output

    # 如果选择使用本地目录
    if args.local:
        local_output_dir = os.path.join(home_path, "srt_fixed")
        output_base_dir = local_output_dir
        print(f"📁 使用本地输出目录: {output_base_dir}")

    print(f"📂 输入目录: {input_base_dir}")
    print(f"📂 输出目录: {output_base_dir}")

    # 检查输入目录是否存在
    if not os.path.exists(input_base_dir):
        print(f"❌ 输入目录不存在: {input_base_dir}")
        return

    # 检查输出目录权限
    try:
        if not os.path.exists(output_base_dir):
            os.makedirs(output_base_dir)
            print(f"✅ 创建输出目录: {output_base_dir}")
    except PermissionError:
        print(f"❌ 没有权限创建输出目录: {output_base_dir}")
        print("💡 建议使用 -l 选项使用本地目录")
        return

    # 检查API密钥是否设置
    if api_type == "ali" and not os.getenv("DASHSCOPE_API_KEY"):
        print("❌ 环境变量 DASHSCOPE_API_KEY 未设置！")
        print("💡 设置方法: export DASHSCOPE_API_KEY=你的密钥")
        return
    elif api_type == "uni" and not os.getenv("UNI_API_KEY"):
        print("❌ 环境变量 UNI_API_KEY 未设置！")
        print("💡 设置方法: export UNI_API_KEY=你的密钥")
        return

    # 获取所有频道目录
    try:
        all_items = os.listdir(input_base_dir)
        channels = [
            d
            for d in all_items
            if os.path.isdir(os.path.join(input_base_dir, d)) and not d.startswith(".")
        ]

        print(f"📺 找到 {len(channels)} 个频道目录")

        if not channels:
            print(f"⚠️  未找到任何频道目录")
            return
    except Exception as e:
        print(f"❌ 无法读取频道目录: {e}")
        return

    total_files_processed = 0
    total_files_found = 0
    total_files_skipped = 0

    for channel_idx, channel in enumerate(channels, 1):
        # 检查是否已达到最大新处理文件数限制
        if max_files and total_files_processed >= max_files:
            print(f"🔒 已达到最大新处理文件数限制 ({max_files})，停止处理")
            break

        input_channel_dir = os.path.join(input_base_dir, channel)
        output_channel_dir = os.path.join(output_base_dir, channel)

        print(f"\n📺 处理频道 {channel_idx}/{len(channels)}: {channel}")

        # 确保输出频道目录存在
        try:
            if not os.path.exists(output_channel_dir):
                os.makedirs(output_channel_dir)
        except PermissionError:
            print(f"❌ 没有权限创建频道输出目录: {output_channel_dir}")
            continue

        # 检查是否为双层目录结构 (format_srt_zh/channel/channel/XXX.srt)
        inner_channel_dir = os.path.join(input_channel_dir, channel)
        if os.path.exists(inner_channel_dir) and os.path.isdir(inner_channel_dir):
            actual_input_dir = inner_channel_dir
        else:
            actual_input_dir = input_channel_dir

        # 获取所有SRT文件
        try:
            all_files = os.listdir(actual_input_dir)
            srt_files = [
                f for f in all_files if f.endswith(".srt") and not f.startswith(".")
            ]
            total_files_found += len(srt_files)

            if not srt_files:
                print(f"⚠️  频道 {channel} 中未找到SRT文件")
                continue

            print(f"📄 找到 {len(srt_files)} 个SRT文件")
        except Exception as e:
            print(f"❌ 无法读取频道 {channel} 中的SRT文件: {e}")
            continue

        channel_files_processed = 0
        channel_files_skipped = 0

        for file_idx, srt_file in enumerate(srt_files, 1):
            # 检查是否已达到最大新处理文件数限制
            if max_files and total_files_processed >= max_files:
                print(f"🔒 已达到最大新处理文件数限制 ({max_files})")
                break

            input_file_path = os.path.join(actual_input_dir, srt_file)
            output_file_path = os.path.join(output_channel_dir, srt_file)

            # 检查文件是否已经完成处理
            if not force_reprocess:
                try:
                    srt_content = read_srt_file(input_file_path)
                    subtitles = parse_srt_with_re(srt_content)
                    total_subtitles = len(subtitles)

                    _, is_completed = check_output_file_progress(
                        output_file_path, total_subtitles
                    )

                    if is_completed:
                        print(
                            f"⏭️  跳过已完成文件 {file_idx}/{len(srt_files)}: {srt_file}"
                        )
                        channel_files_skipped += 1
                        total_files_skipped += 1
                        continue

                except Exception as e:
                    pass  # 检查出错时继续处理该文件

            print(f"\n⚡ 处理文件 {file_idx}/{len(srt_files)} 在频道 {channel}")

            # 处理文件
            process_srt_file(
                input_file_path,
                output_file_path,
                channel,
                srt_file,
                api_type,
                batch_size,
                max_retries,
                force_reprocess,
            )

            total_files_processed += 1
            channel_files_processed += 1

        print(
            f"✅ 频道 {channel} 完成: 跳过{channel_files_skipped}个，新处理{channel_files_processed}个"
        )

    print(f"\n🎉 所有处理完成！")
    print(f"📊 总共找到: {total_files_found} 个文件")
    print(f"⏭️  跳过已完成: {total_files_skipped} 个文件")
    print(f"🆕 新处理: {total_files_processed} 个文件")

    # 打印API调用统计信息
    print_api_stats()


if __name__ == "__main__":
    main()
