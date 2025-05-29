"""
YouTube故事视频概要生成器

功能说明:
此脚本用于根据完整的故事内容生成吸引人的YouTube视频概要。
脚本使用UNI API，GPT-4.1-mini模型生成：
1. 吸引人的视频概要，用词老道有风格
2. 让观众看了就想听完故事，想关注频道

输入:
- 故事全文内容 (来自ai_studio_bot.py的输出)
- 路径: /Volumes/dhl/audio/scifi/full_story/language_code/{story_index}.txt

输出:
- 概要文件: /Volumes/dhl/audio/scifi/description/{story_index}.txt

使用方法:
1. 基本使用: python story_description_generator.py
2. 强制重新生成: python story_description_generator.py -f
3. 设置批处理大小: python story_description_generator.py -b 5
4. 指定处理范围: python story_description_generator.py --start 1 --end 10

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
import glob
import re
from openai import OpenAI
import concurrent.futures
from tqdm import tqdm


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


def generate_story_description(client, story_content, story_index, max_retries=3):
    """使用OpenAI的GPT模型生成YouTube视频概要，失败时自动重试"""
    if not story_content.strip():
        print(f"警告: 故事 {story_index} 的内容为空，无法生成概要")
        return ""

    for attempt in range(max_retries):
        try:
            system_prompt = """你是一个 youtube 视频概要专家，大师，老炮。给你一段故事全文，\
                你可以根据全文生成 youtube 的视频概要，概要吸引人，用词老道有风格，\
                    让人看了就想听完故事，想关注频道哈。

要求：
1. 概要要抓住故事的核心亮点和悬念
2. 用词要有吸引力，营造神秘感和期待感
3. 长度控制在200-400字之间,可以使用适当但不多的 emoji 进行点缀。
4. 风格要老道，有经验丰富的storyteller感觉
5. 要让读者产生强烈的收听欲望和关注冲动
6. 直接返回概要内容，不要添加其他说明文字。
7. 直接返回英文概要，再说一次，使用英文，不要添加其他说明文字。

直接返回概要内容，不要添加其他说明文字。"""

            completion = client.chat.completions.create(
                model="gpt-4.1-mini",
                max_tokens=600,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"故事全文：\n\n{story_content}"},
                ],
                timeout=60,  # 增加超时时间为60秒
            )
            result = completion.choices[0].message.content.strip()

            # 检查生成结果的质量
            if len(result) < 50:
                print(
                    f"警告: 故事 {story_index} 生成的概要过短 ({len(result)}字符)，重试..."
                )
                if attempt < max_retries - 1:
                    continue

            print(f"成功生成故事 {story_index} 的概要，长度: {len(result)} 字符")
            return result

        except Exception as e:
            print(
                f"生成故事 {story_index} 概要出错 (尝试 {attempt+1}/{max_retries}): {e}"
            )
            if attempt < max_retries - 1:
                retry_delay = (attempt + 1) * 3
                print(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                print(f"达到最大重试次数 ({max_retries})，返回空结果")
                return ""


def get_story_content(story_index, story_dir):
    """读取指定索引的故事内容"""
    story_file = os.path.join(story_dir, f"{story_index}.txt")

    if not os.path.exists(story_file):
        print(f"警告: 故事文件不存在: {story_file}")
        return ""

    try:
        with open(story_file, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            print(f"警告: 故事文件 {story_file} 为空")
            return ""

        print(f"成功读取故事 {story_index}，内容长度: {len(content)} 字符")
        return content

    except Exception as e:
        print(f"读取故事文件 {story_file} 时出错: {e}")
        return ""


def get_existing_stories(story_dir):
    """获取已经生成的故事索引列表"""
    if not os.path.exists(story_dir):
        print(f"故事目录不存在: {story_dir}")
        return []

    story_files = glob.glob(os.path.join(story_dir, "*.txt"))
    existing_numbers = []

    for file_path in story_files:
        basename = os.path.basename(file_path)
        match = re.match(r"(\d+)\.txt", basename)
        if match:
            existing_numbers.append(int(match.group(1)))

    return sorted(existing_numbers)


def get_existing_descriptions(description_dir):
    """获取已经生成的概要索引列表"""
    if not os.path.exists(description_dir):
        os.makedirs(description_dir, exist_ok=True)
        return []

    desc_files = glob.glob(os.path.join(description_dir, "*.txt"))
    existing_numbers = []

    for file_path in desc_files:
        basename = os.path.basename(file_path)
        match = re.match(r"(\d+)\.txt", basename)
        if match:
            existing_numbers.append(int(match.group(1)))

    return sorted(existing_numbers)


def process_story_description(
    client, story_index, story_dir, description_dir, force=False
):
    """处理单个故事的概要生成"""
    try:
        # 检查是否已存在概要文件
        description_file = os.path.join(description_dir, f"{story_index}.txt")

        if os.path.exists(description_file) and not force:
            try:
                with open(description_file, "r", encoding="utf-8") as f:
                    existing_content = f.read().strip()
                if existing_content:
                    print(f"跳过已处理的故事概要: {story_index}")
                    return True
            except:
                pass  # 文件损坏，重新生成

        # 读取故事内容
        story_content = get_story_content(story_index, story_dir)
        if not story_content:
            print(f"无法读取故事 {story_index} 的内容，跳过")
            return False

        # 生成概要
        print(f"正在为故事 {story_index} 生成概要...")
        description = generate_story_description(client, story_content, story_index)

        if not description:
            print(f"故事 {story_index} 概要生成失败")
            return False

        # 保存概要
        try:
            with open(description_file, "w", encoding="utf-8") as f:
                f.write(description)
            print(f"故事 {story_index} 概要已保存到: {description_file}")

            # 显示概要预览
            preview = (
                description[:100] + "..." if len(description) > 100 else description
            )
            print(f"概要预览: {preview}")

            return True

        except Exception as e:
            print(f"保存故事 {story_index} 概要时出错: {e}")
            return False

    except Exception as e:
        print(f"处理故事 {story_index} 时出错: {e}")
        return False


def process_all_stories(
    client,
    story_dir,
    description_dir,
    force=False,
    batch_size=5,
    start_index=None,
    end_index=None,
):
    """处理所有故事的概要生成"""

    # 检查故事目录是否存在
    if not os.path.exists(story_dir):
        print(f"错误: 故事目录不存在: {story_dir}")
        return

    # 确保概要目录存在
    os.makedirs(description_dir, exist_ok=True)

    # 获取所有可用的故事
    existing_stories = get_existing_stories(story_dir)

    if not existing_stories:
        print(f"在 {story_dir} 中未找到任何故事文件")
        return

    # 筛选处理范围
    if start_index is not None:
        existing_stories = [s for s in existing_stories if s >= start_index]

    if end_index is not None:
        existing_stories = [s for s in existing_stories if s <= end_index]

    if not existing_stories:
        print("在指定范围内未找到任何故事文件")
        return

    print(f"找到 {len(existing_stories)} 个故事文件: {existing_stories}")

    # 获取已生成的概要
    existing_descriptions = get_existing_descriptions(description_dir)

    # 确定需要处理的故事
    stories_to_process = []

    if force:
        stories_to_process = existing_stories
        print(f"强制重新生成模式：将处理所有 {len(stories_to_process)} 个故事")
    else:
        stories_to_process = [
            s for s in existing_stories if s not in existing_descriptions
        ]
        skipped_count = len(existing_stories) - len(stories_to_process)
        if skipped_count > 0:
            print(f"跳过已存在概要的 {skipped_count} 个故事")
        print(f"需要生成概要的故事: {len(stories_to_process)} 个")

    if not stories_to_process:
        print("所有故事概要都已生成完毕")
        return

    print(f"开始处理 {len(stories_to_process)} 个故事的概要生成...")

    # 批量处理
    with tqdm(total=len(stories_to_process), desc="概要生成进度") as pbar:
        for i in range(0, len(stories_to_process), batch_size):
            batch = stories_to_process[i : i + batch_size]

            # 函数用于处理单个故事
            def process_story(story_index):
                return process_story_description(
                    client, story_index, story_dir, description_dir, force
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
            if i + batch_size < len(stories_to_process):
                time.sleep(2)


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="YouTube故事视频概要生成器")

    # 添加命令行参数
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="强制重新生成概要，忽略已有文件",
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

    # 设置路径
    story_dir = "/Volumes/dhl/audio/scifi/full_story/language_code"
    description_dir = "/Volumes/dhl/audio/scifi/description"

    print("=== YouTube故事视频概要生成器 ===")
    print(f"故事源目录: {story_dir}")
    print(f"概要输出目录: {description_dir}")

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
    process_all_stories(
        client,
        story_dir,
        description_dir,
        args.force,
        args.batch_size,
        args.start,
        args.end,
    )

    print("所有故事概要生成任务完成!")


if __name__ == "__main__":
    main()
