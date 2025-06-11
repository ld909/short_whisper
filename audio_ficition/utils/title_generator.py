"""
YouTube故事视频标题生成器

功能说明:
此脚本用于根据故事概要生成吸引人的YouTube视频标题。
脚本使用UNI API，GPT-4.1-mini模型生成：
1. 简短有力的视频标题，凸显主题
2. 让观众看了就想点击进来的标题

输入:
- 故事概要内容 (来自story_description_generator.py的输出)
- 路径: /mnt/dhl/audio/scifi/description/{story_index}.txt (Ubuntu)
       /Volumes/dhl/audio/scifi/description/{story_index}.txt (Mac)

输出:
- 标题文件: /mnt/dhl/audio/scifi/titles/{story_index}.txt

使用方法:
1. 基本使用: python title_generator.py
2. 强制重新生成: python title_generator.py -f
3. 设置批处理大小: python title_generator.py -b 5
4. 指定处理范围: python title_generator.py --start 1 --end 10

注意:
- 需要设置环境变量UNI_API_KEY以提供OpenAI API密钥
- 脚本支持断点续传，中断后可从上次停止的位置继续处理
- 自动检测操作系统并使用对应的路径格式
"""

import os
import sys
import json
import time
import argparse
import platform
import glob
import re
from openai import OpenAI
import concurrent.futures
from tqdm import tqdm


def get_base_paths():
    """根据操作系统获取基础路径"""
    system = platform.system().lower()

    if system == "darwin":  # Mac
        base_path = "/Volumes/dhl/audio/scifi"
    else:  # Linux/Ubuntu
        base_path = "/media/dhl/audio/scifi"

    return {
        "description_dir": os.path.join(base_path, "description"),
        "titles_dir": os.path.join(base_path, "titles"),
    }


def setup_openai_client():
    """设置OpenAI客户端并验证API密钥"""
    api_key = os.environ.get("UNI_API_KEY")

    if not api_key:
        print("错误: 未找到OpenAI API密钥")
        print("请设置环境变量UNI_API_KEY")
        print("例如: export UNI_API_KEY='your-api-key'")
        sys.exit(1)

    try:
        # 确保只传入支持的参数
        client = OpenAI(api_key=api_key, base_url="https://api.uniapi.io/v1")
        return client
    except Exception as e:
        print(f"初始化OpenAI客户端时出错: {e}")
        print("这可能是由于以下原因:")
        print("1. OpenAI库版本不兼容，请尝试: pip install openai --upgrade")
        print("2. API密钥格式不正确")
        print("3. 网络连接问题")
        sys.exit(1)


def generate_story_title(client, description_content, story_index, max_retries=3):
    """使用OpenAI的GPT模型生成YouTube视频标题，失败时自动重试"""
    if not description_content.strip():
        print(f"警告: 故事 {story_index} 的描述为空，无法生成标题")
        return ""

    for attempt in range(max_retries):
        try:
            system_prompt = """你是一个youtube视频标题大师，营销大师。\
            你可以根据一个故事的概述生成对应视频的标题，有创意，有传播力，让人看了想点进来。\
            使用英语，直接返回标题，不要太长，一句话最好！直接返回英文标题，不夹带其他内容。"""

            completion = client.chat.completions.create(
                model="gpt-4.1-mini",
                max_tokens=100,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"故事概述：\n\n{description_content}"},
                ],
                timeout=60,
            )
            result = completion.choices[0].message.content.strip()

            # 检查生成结果的质量
            if len(result) < 10:
                print(
                    f"警告: 故事 {story_index} 生成的标题过短 ({len(result)}字符)，重试..."
                )
                if attempt < max_retries - 1:
                    continue

            # 移除可能的引号
            result = result.strip("\"'")

            print(f"成功生成故事 {story_index} 的标题，长度: {len(result)} 字符")
            return result

        except Exception as e:
            print(
                f"生成故事 {story_index} 标题出错 (尝试 {attempt+1}/{max_retries}): {e}"
            )
            if attempt < max_retries - 1:
                retry_delay = (attempt + 1) * 3
                print(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                print(f"达到最大重试次数 ({max_retries})，返回空结果")
                return ""


def get_description_content(story_index, description_dir):
    """读取指定索引的故事描述内容"""
    description_file = os.path.join(description_dir, f"{story_index}.txt")

    if not os.path.exists(description_file):
        print(f"警告: 描述文件不存在: {description_file}")
        return ""

    try:
        with open(description_file, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            print(f"警告: 描述文件 {description_file} 为空")
            return ""

        print(f"成功读取故事 {story_index} 描述，内容长度: {len(content)} 字符")
        return content

    except Exception as e:
        print(f"读取描述文件 {description_file} 时出错: {e}")
        return ""


def get_existing_descriptions(description_dir):
    """获取已经生成的描述索引列表"""
    if not os.path.exists(description_dir):
        print(f"描述目录不存在: {description_dir}")
        return []

    desc_files = glob.glob(os.path.join(description_dir, "*.txt"))
    existing_numbers = []

    for file_path in desc_files:
        basename = os.path.basename(file_path)
        # 排除以点开头的meta文件（如.DS_Store等）
        if basename.startswith("."):
            continue
        match = re.match(r"(\d+)\.txt", basename)
        if match:
            existing_numbers.append(int(match.group(1)))

    return sorted(existing_numbers)


def get_existing_titles(titles_dir):
    """获取已经生成的标题索引列表"""
    if not os.path.exists(titles_dir):
        os.makedirs(titles_dir, exist_ok=True)
        return []

    title_files = glob.glob(os.path.join(titles_dir, "*.txt"))
    existing_numbers = []

    for file_path in title_files:
        basename = os.path.basename(file_path)
        # 排除以点开头的meta文件（如.DS_Store等）
        if basename.startswith("."):
            continue
        match = re.match(r"(\d+)\.txt", basename)
        if match:
            existing_numbers.append(int(match.group(1)))

    return sorted(existing_numbers)


def process_story_title(client, story_index, description_dir, titles_dir, force=False):
    """处理单个故事的标题生成"""
    try:
        # 检查是否已存在标题文件
        title_file = os.path.join(titles_dir, f"{story_index}.txt")

        if os.path.exists(title_file) and not force:
            try:
                with open(title_file, "r", encoding="utf-8") as f:
                    existing_content = f.read().strip()
                if existing_content:
                    print(f"跳过已处理的故事标题: {story_index}")
                    return True
            except:
                pass  # 文件损坏，重新生成

        # 读取描述内容
        description_content = get_description_content(story_index, description_dir)
        if not description_content:
            print(f"无法读取故事 {story_index} 的描述内容，跳过")
            return False

        # 生成标题
        print(f"正在为故事 {story_index} 生成标题...")
        title = generate_story_title(client, description_content, story_index)

        if not title:
            print(f"故事 {story_index} 标题生成失败")
            return False

        # 保存标题
        try:
            with open(title_file, "w", encoding="utf-8") as f:
                f.write(title)
            print(f"故事 {story_index} 标题已保存到: {title_file}")

            # 显示标题预览
            print(f"生成的标题: {title}")

            return True

        except Exception as e:
            print(f"保存故事 {story_index} 标题时出错: {e}")
            return False

    except Exception as e:
        print(f"处理故事 {story_index} 时出错: {e}")
        return False


def process_all_titles(
    client,
    description_dir,
    titles_dir,
    force=False,
    batch_size=5,
    start_index=None,
    end_index=None,
):
    """处理所有故事的标题生成"""

    # 检查描述目录是否存在
    if not os.path.exists(description_dir):
        print(f"错误: 描述目录不存在: {description_dir}")
        return

    # 确保标题目录存在
    os.makedirs(titles_dir, exist_ok=True)

    # 获取所有可用的描述
    existing_descriptions = get_existing_descriptions(description_dir)

    if not existing_descriptions:
        print(f"在 {description_dir} 中未找到任何描述文件")
        return

    # 筛选处理范围
    if start_index is not None:
        existing_descriptions = [s for s in existing_descriptions if s >= start_index]

    if end_index is not None:
        existing_descriptions = [s for s in existing_descriptions if s <= end_index]

    if not existing_descriptions:
        print("在指定范围内未找到任何描述文件")
        return

    print(f"找到 {len(existing_descriptions)} 个描述文件: {existing_descriptions}")

    # 获取已生成的标题
    existing_titles = get_existing_titles(titles_dir)

    # 确定需要处理的故事
    titles_to_process = []

    if force:
        titles_to_process = existing_descriptions
        print(f"强制重新生成模式：将处理所有 {len(titles_to_process)} 个故事")
    else:
        titles_to_process = [
            s for s in existing_descriptions if s not in existing_titles
        ]
        skipped_count = len(existing_descriptions) - len(titles_to_process)
        if skipped_count > 0:
            print(f"跳过已存在标题的 {skipped_count} 个故事")
        print(f"需要生成标题的故事: {len(titles_to_process)} 个")

    if not titles_to_process:
        print("所有故事标题都已生成完毕")
        return

    print(f"开始处理 {len(titles_to_process)} 个故事的标题生成...")

    # 批量处理
    with tqdm(total=len(titles_to_process), desc="标题生成进度") as pbar:
        for i in range(0, len(titles_to_process), batch_size):
            batch = titles_to_process[i : i + batch_size]

            # 函数用于处理单个故事
            def process_story(story_index):
                return process_story_title(
                    client, story_index, description_dir, titles_dir, force
                )

            # 并发处理批次
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=batch_size
            ) as executor:
                results = list(executor.map(process_story, batch))

            # 更新进度条
            pbar.update(len(batch))

            # 统计成功率
            success_count = sum(1 for r in results if r)
            print(f"批次处理完成: {success_count}/{len(batch)} 成功")

            # 批次间稍作等待，避免API限制
            if i + batch_size < len(titles_to_process):
                time.sleep(2)


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="YouTube故事视频标题生成器")

    # 添加命令行参数
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="强制重新生成标题，忽略已有文件",
    )
    parser.add_argument(
        "-b",
        "--batch_size",
        type=int,
        default=5,
        help="并发处理的批量大小，默认为5",
    )
    parser.add_argument(
        "--start",
        type=int,
        help="指定开始处理的故事索引（包含）",
    )
    parser.add_argument(
        "--end",
        type=int,
        help="指定结束处理的故事索引（包含）",
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 获取路径
    paths = get_base_paths()
    description_dir = paths["description_dir"]
    titles_dir = paths["titles_dir"]

    print("=== YouTube故事视频标题生成器 ===")
    print(f"操作系统: {platform.system()}")
    print(f"描述源目录: {description_dir}")
    print(f"标题输出目录: {titles_dir}")

    if args.start is not None or args.end is not None:
        range_info = f"处理范围: {args.start or '开始'} ~ {args.end or '结束'}"
        print(f"{range_info}")

    if args.force:
        print("模式: 强制重新生成")
    else:
        print("模式: 断点续传")

    print(f"批处理大小: {args.batch_size}")
    print()

    # 设置OpenAI客户端
    client = setup_openai_client()

    # 开始处理
    process_all_titles(
        client,
        description_dir,
        titles_dir,
        args.force,
        args.batch_size,
        args.start,
        args.end,
    )

    print("所有故事标题生成任务完成!")


if __name__ == "__main__":
    main()
