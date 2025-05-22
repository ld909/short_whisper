import os
import re
import sys
import argparse
import platform
from tqdm import tqdm
from openai import OpenAI
import concurrent.futures
from threading import Lock


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


def fix_typos(subtitle, context="", api_type="ali"):
    """使用指定的大模型检查并修复字幕中的错别字"""
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

    try:
        if api_type == "ali":
            client = setup_ali_client()
            model = "qwen-max-0125"
        else:  # api_type == "uni"
            client = setup_uni_client()
            # model = "gemini-2.5-pro-exp-03-25"
            model = "gpt-4.1-mini"

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


def process_subtitles_concurrently(
    subtitles, fixed_subtitles, api_type, output_path, batch_size=5
):
    """并发处理字幕，同时保持顺序并实时写入文件"""
    results = {}  # 存储处理结果，键为索引，值为修复后的文本
    lock = Lock()  # 用于保护对结果字典的访问和文件写入

    def process_subtitle(index, subtitle):
        """处理单个字幕的函数"""
        print(f"\n字幕 #{index+1}/{len(subtitles)}:")

        # 修复错别字
        fixed_text = fix_typos(subtitle["text"], "", api_type)

        with lock:
            results[index] = fixed_text

        return index, fixed_text

    def safe_save_subtitle(subtitle_item, path):
        """安全保存字幕到文件，处理可能的权限错误"""
        try:
            save_subtitle_item(subtitle_item, path, "a")
            return True
        except PermissionError as e:
            print(f"权限错误: 无法写入文件 {path}")
            print(f"错误信息: {str(e)}")
            return False
        except Exception as e:
            print(f"保存字幕时出错: {str(e)}")
            return False

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
                if not safe_save_subtitle(subtitles[i], output_path):
                    print(f"警告: 字幕 #{i+1} 无法保存到文件，但处理会继续")

            print(f"完成处理字幕 #{i+1}/{len(subtitles)}: {results[i]}")

    return subtitles


def process_srt_file(
    input_path, output_path, channel, srt_file, api_type, batch_size=5
):
    """处理单个SRT文件，并发修复错别字并保存"""
    print(f"正在处理：{input_path}")

    try:
        # 检查输出目录是否可写
        output_dir = os.path.dirname(output_path)
        if not os.access(output_dir, os.W_OK):
            print(f"警告: 没有权限写入目录 {output_dir}")
            print("解决方案: 请尝试以下命令为目录添加写入权限:")
            print(f"sudo chmod -R 775 {output_dir}")
            print("或者更改输出目录到本地可写目录:")
            print("python fix_tyro.py -o /home/$USER/srt_fixed")
            return

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
            return

        # 如果输出文件存在但不完整，则从断点继续
        start_index = file_progress
        if file_progress > 0:
            print(f"检测到输出文件，从字幕 #{start_index+1} 继续处理")
        else:
            # 如果是新文件，先清空输出文件
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    pass
            except PermissionError:
                print(f"错误: 没有权限创建或写入文件 {output_path}")
                print("解决方案: 请尝试以下命令为目录添加写入权限:")
                print(f"sudo chmod -R 775 {os.path.dirname(output_path)}")
                print("或者更改输出目录到本地可写目录:")
                print("python fix_tyro.py -o /home/$USER/srt_fixed")
                return

        # 用于保存已修复的字幕，作为上下文
        fixed_subtitles = []

        # 如果从中间继续处理，需要读取已经处理过的字幕作为上下文
        if start_index > 0:
            with open(output_path, "r", encoding="utf-8") as f:
                output_content = f.read()

            # 解析已处理的字幕文本
            processed_subtitles = parse_srt_with_re(output_content)
            # 添加到已修复字幕列表
            fixed_subtitles.extend(
                [subtitle["text"] for subtitle in processed_subtitles]
            )

        # 并发修复错别字 - 只处理未处理的部分
        remaining_subtitles = subtitles[start_index:]
        print(
            f"使用并发方式处理剩余的 {len(remaining_subtitles)} 个字幕，批量大小: {batch_size}"
        )

        # 处理剩余字幕
        with tqdm(total=len(remaining_subtitles), desc="修复错别字") as pbar:
            processed_subtitles = process_subtitles_concurrently(
                remaining_subtitles, fixed_subtitles, api_type, output_path, batch_size
            )

            # 更新进度条
            for _ in range(len(remaining_subtitles)):
                pbar.update(1)

        print(f"已完成文件处理：{output_path}")

    except PermissionError as e:
        print(f"权限错误: {input_path}")
        print(f"错误信息: {str(e)}")
        print("\n解决方案:")
        print(
            f"1. 确保挂载的设备有写入权限: sudo mount -o remount,rw {os.path.dirname(output_path)}"
        )
        print(
            f"2. 更改输出目录到本地可写目录: python fix_tyro.py -o /home/$USER/srt_fixed"
        )
    except Exception as e:
        print(f"处理文件时出错: {input_path}")
        print(f"错误信息: {str(e)}")


def get_base_path():
    """根据操作系统类型返回对应的基础路径"""
    if platform.system() == "Darwin":  # Mac OS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


def main():
    """处理指定目录结构中的中文SRT文件"""
    # 获取基础路径
    base_path = get_base_path()
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
        default=f"{base_path}/format_srt_zh/mp3",
        help="输入SRT基础目录路径",
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

    # 解析命令行参数
    args = parser.parse_args()
    input_base_dir = args.input
    output_base_dir = args.output
    api_type = args.api
    batch_size = args.batch_size

    # 如果选择使用本地目录
    if args.local:
        local_output_dir = os.path.join(home_path, "srt_fixed")
        output_base_dir = local_output_dir
        print(f"使用本地输出目录: {output_base_dir}")

    print(f"使用 {api_type} API 进行错别字修复")
    print(f"检测到系统: {platform.system()}")
    print(f"使用基础路径: {base_path}")
    print(f"输入目录: {input_base_dir}")
    print(f"输出目录: {output_base_dir}")
    print(f"并发批量大小: {batch_size}")

    # 检查输入目录是否存在
    if not os.path.exists(input_base_dir):
        print(f"错误: 输入目录不存在: {input_base_dir}")
        return

    # 检查输出目录权限
    try:
        # 确保输出基础目录存在
        if not os.path.exists(output_base_dir):
            os.makedirs(output_base_dir)
            print(f"已创建输出基础目录: {output_base_dir}")
    except PermissionError:
        print(f"错误: 没有权限创建输出目录: {output_base_dir}")
        print("建议使用 -l/--local 选项使用本地目录作为输出，或手动指定可写目录:")
        print("python fix_tyro.py -o /home/$USER/srt_fixed")
        return

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
            if os.path.isdir(os.path.join(input_base_dir, d)) and not d.startswith(".")
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
        try:
            if not os.path.exists(output_channel_dir):
                os.makedirs(output_channel_dir)
                print(f"已创建频道输出目录: {output_channel_dir}")
        except PermissionError:
            print(f"错误: 没有权限创建频道输出目录: {output_channel_dir}")
            continue

        # 获取当前频道下的所有SRT文件
        try:
            srt_files = [
                f
                for f in os.listdir(input_channel_dir)
                if f.endswith(".srt") and not f.startswith(".")
            ]
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
                input_file_path,
                output_file_path,
                channel,
                srt_file,
                api_type,
                batch_size,
            )


if __name__ == "__main__":
    main()
