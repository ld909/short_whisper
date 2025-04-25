import os
import re
import sys
from tqdm import tqdm
from openai import OpenAI


def read_srt_file(file_path):
    """读取SRT文件并返回内容"""
    with open(file_path, "r") as f:
        srt_content = f.read()
    return srt_content


def parse_srt_with_re(srt_content):
    """使用正则表达式解析SRT字幕内容"""
    timestamps = []
    subtitles = []

    # 定义一个正则表达式来匹配字幕块：序号、时间戳和字幕文本
    pattern = re.compile(
        r"\d+\s+(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\s+(.*?)(?=\n\n|\Z)",
        re.DOTALL,
    )

    matches = pattern.findall(srt_content)

    for match in matches:
        start_time, end_time, subtitle = match
        timestamps.append((start_time, end_time))
        subtitle = subtitle.replace("\n", " ").strip()
        subtitles.append(subtitle)

    return timestamps, subtitles


def save_srt(ts_list, txt_list, output_path):
    """将时间戳和文本保存为SRT格式"""
    with open(output_path, "w") as f:
        for i in range(len(txt_list)):
            f.write(str(i + 1) + "\n")
            f.write(ts_list[i][0] + " --> " + ts_list[i][1] + "\n")
            f.write(txt_list[i] + "\n\n")


def fix_typos_with_qwen(subtitle):
    """使用阿里云千问大模型检查并修复字幕中的错别字"""
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    tyro_dict = {"元气": "缘起"}

    try:
        completion = client.chat.completions.create(
            model="qwen-max-0125",
            messages=[
                {
                    "role": "system",
                    "content": f'你是一个字幕错别字检查专家，只对错别字进行修正,内容是佛教/佛学的主题，\
                        文字来自于一个语音转文字的模型，有些字是发音对了，但字没有对，需特别注意。\
                            有些词发音对了，但不是佛教名词，修改为专业的佛教名、人名、地名、专有名词，比如参考{tyro_dict}\
                                注意专业词汇。如果句子没有错别字，仅回复数字"111"；\
                                    如果有错别字，请返回修复后的完整句子，直接返回新句子,不要返回修改前的句子，不要返回类似于：【原句】，修改后：【新句】这样的错误结构。不要对任何其他作修改，不要修改标点、引号等内容，不要增加任何内容。\
                                        ',
                },
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


def process_srt_file(input_path, output_path):
    """处理单个SRT文件，修复错别字并保存"""
    print(f"正在处理：{input_path}")

    # 读取SRT文件内容
    srt_content = read_srt_file(input_path)

    # 解析SRT内容
    timestamps, subtitles = parse_srt_with_re(srt_content)

    # 修复错别字
    fixed_subtitles = []
    for i, subtitle in enumerate(tqdm(subtitles, desc="修复错别字")):
        print(f"\n字幕 #{i+1}:")
        fixed_subtitle = fix_typos_with_qwen(subtitle)
        fixed_subtitles.append(fixed_subtitle)
        print("-" * 50)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 保存修复后的SRT文件
    save_srt(timestamps, fixed_subtitles, output_path)

    print(f"已保存修复后的文件：{output_path}")


def main(input_folder, output_folder):
    """处理输入文件夹中的所有SRT文件"""
    # 确保输出文件夹存在
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 获取输入文件夹中的所有SRT文件
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.endswith(".srt"):
                # 构建输入和输出文件路径
                input_path = os.path.join(root, file)

                # 计算相对路径，以保持文件夹结构
                rel_path = os.path.relpath(root, input_folder)
                if rel_path == ".":
                    output_path = os.path.join(output_folder, file)
                else:
                    output_path = os.path.join(output_folder, rel_path, file)

                # 确保输出目录存在
                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                # 处理文件
                process_srt_file(input_path, output_path)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python fix_srt_typos.py <输入文件夹> <输出文件夹>")
        sys.exit(1)

    input_folder = sys.argv[1]
    output_folder = sys.argv[2]

    main(input_folder, output_folder)
