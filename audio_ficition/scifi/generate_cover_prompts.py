"""
科幻故事封面图片生成提示词工具

功能说明:
此脚本用于根据科幻故事内容生成文生图的封面页提示词。
脚本使用UNI API，GPT-4.1-mini模型生成：
1. 体现女主角（外星人，性感年轻，大胸身材，人形面貌，特殊肤色）的魅力
2. 体现男主角的特征
3. 根据故事情节设计的背景和场景
4. 动人且具有吸引力的视觉元素

输入:
- 故事文本内容（来自ai_studio_bot.py的输出）

输出:
- 封面提示词文件: /Volumes/dhl/audio/scifi/cover_prompts/[故事索引].txt

使用方法:
1. 基本使用: python generate_cover_prompts.py
2. 强制重新生成: python generate_cover_prompts.py -f
3. 指定故事索引范围: python generate_cover_prompts.py --start 1 --end 10

注意:
- 需要设置环境变量UNI_API_KEY以提供OpenAI API密钥
- 脚本支持断点续传，中断后可从上次停止的位置继续处理
"""

import os
import sys
import time
import argparse
import platform
from openai import OpenAI
import glob
import re
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


def generate_cover_prompt(client, story_content, story_index, max_retries=3):
    """使用OpenAI的GPT模型生成封面图片提示词，失败时自动重试"""
    if not story_content.strip():
        print(f"警告: 故事 {story_index} 的内容为空，无法生成封面提示词")
        return ""

    for attempt in range(max_retries):
        try:
            system_prompt = """你是一个伟大的文生图提示词大师，能够根据一个故事，生成文生图的提示词。提示词一定要体现女主和男主，女主是外星人，性感年轻，大胸身材，人形面貌，就是肤色不太一样。背景等都是根据故事和情节进行设计哈，一定要体现女主的魅力和动人。

请根据给出的科幻故事内容，生成一个详细的文生图提示词，用于创建故事封面。提示词应该包含：
1. 女主角：外星人，穿着性感年轻，沙漏身形，人形面貌，漂亮的脸蛋，20岁，特殊肤色（非人类肤色），五官和人类一样，不要出现密集器官或和人不一样的五官结构
2. 男主角：根据故事内容描述其特征
3. 背景场景：根据故事情节设计，体现科幻元素
4. 整体氛围：非常真实，8k，科幻大片，细节要求到位，浪漫、神秘、具有视觉冲击力
5. 总体不要过长，2～3 句话即可

直接返回英文的文生图提示词，不要添加其他解释文字。"""

            completion = client.chat.completions.create(
                model="gpt-4.1-mini",
                max_tokens=500,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"故事内容：\n\n{story_content}"},
                ],
                timeout=30,
            )
            result = completion.choices[0].message.content.strip()
            print(f"✅ 已成功生成故事 {story_index} 的封面提示词")
            return result
        except Exception as e:
            print(f"生成封面提示词出错 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                retry_delay = (attempt + 1) * 3
                print(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                print(f"达到最大重试次数 ({max_retries})，返回空结果")
                return ""


def get_existing_stories():
    """获取已经生成的故事文件列表"""
    story_dir = "/Volumes/dhl/audio/scifi/full_story/language_code"

    if not os.path.exists(story_dir):
        print(f"故事目录不存在: {story_dir}")
        return {}

    story_files = glob.glob(os.path.join(story_dir, "*.txt"))
    stories = {}

    for file_path in story_files:
        basename = os.path.basename(file_path)
        match = re.match(r"(\d+)\.txt", basename)
        if match:
            story_index = int(match.group(1))
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:  # 只包含有内容的故事
                    stories[story_index] = content
            except Exception as e:
                print(f"读取故事文件 {file_path} 时出错: {e}")

    return stories


def get_existing_cover_prompts():
    """获取已经生成的封面提示词列表"""
    cover_dir = "/Volumes/dhl/audio/scifi/cover_prompts"

    if not os.path.exists(cover_dir):
        os.makedirs(cover_dir, exist_ok=True)
        return set()

    existing_files = glob.glob(os.path.join(cover_dir, "*.txt"))
    existing_indices = set()

    for file_path in existing_files:
        basename = os.path.basename(file_path)
        match = re.match(r"(\d+)\.txt", basename)
        if match:
            existing_indices.add(int(match.group(1)))

    return existing_indices


def save_cover_prompt(story_index, prompt_content):
    """保存封面提示词到文件"""
    cover_dir = "/Volumes/dhl/audio/scifi/cover_prompts"

    # 检查并创建目录
    try:
        os.makedirs(cover_dir, exist_ok=True)
        print(f"📂 确保目录存在: {cover_dir}")
    except Exception as e:
        print(f"❌ 创建目录失败: {e}")
        return False

    file_path = os.path.join(cover_dir, f"{story_index}.txt")

    # 检查提示词内容是否为空
    if not prompt_content or not prompt_content.strip():
        print(f"⚠️ 警告: 故事 {story_index} 的提示词内容为空，跳过保存")
        return False

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(prompt_content)

        # 验证文件是否成功写入
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"📁 已保存封面提示词到: {file_path} (大小: {file_size} 字节)")
            return True
        else:
            print(f"❌ 文件保存后未找到: {file_path}")
            return False

    except Exception as e:
        print(f"❌ 保存封面提示词到 {file_path} 时出错: {e}")
        return False


def process_stories(client, force=False, start_index=None, end_index=None):
    """处理所有故事，生成封面提示词"""
    # 获取所有已存在的故事
    stories = get_existing_stories()

    if not stories:
        print("未找到任何故事文件")
        return

    # 获取已存在的封面提示词
    existing_prompts = get_existing_cover_prompts()

    # 过滤需要处理的故事
    stories_to_process = {}

    for story_index, content in stories.items():
        # 应用索引范围过滤
        if start_index is not None and story_index < start_index:
            continue
        if end_index is not None and story_index > end_index:
            continue

        # 检查是否需要重新生成
        if force or story_index not in existing_prompts:
            stories_to_process[story_index] = content

    if not stories_to_process:
        print("所有指定范围内的故事都已有封面提示词")
        return

    print(f"\n=== 📊 封面提示词生成分析 ===")
    print(f"总故事数量: {len(stories)}")
    print(f"已有封面提示词: {len(existing_prompts)}")
    print(f"需要处理的故事: {len(stories_to_process)}")
    print(f"处理的故事索引: {sorted(stories_to_process.keys())}")

    # 统计变量
    success_count = 0
    failure_count = 0

    # 处理每个故事
    with tqdm(total=len(stories_to_process), desc="生成封面提示词进度") as pbar:
        for story_index in sorted(stories_to_process.keys()):
            content = stories_to_process[story_index]

            print(f"\n=== 处理故事 {story_index} ===")
            print(f"故事内容长度: {len(content)} 字符")

            # 生成封面提示词
            prompt = generate_cover_prompt(client, content, story_index)

            if prompt:
                # 保存提示词
                if save_cover_prompt(story_index, prompt):
                    success_count += 1
                    print(f"✅ 故事 {story_index} 封面提示词生成成功")
                    # 显示部分提示词内容作为预览
                    preview = prompt[:200] + "..." if len(prompt) > 200 else prompt
                    print(f"💡 提示词预览: {preview}")
                else:
                    failure_count += 1
                    print(f"❌ 故事 {story_index} 封面提示词保存失败")
            else:
                failure_count += 1
                print(f"❌ 故事 {story_index} 封面提示词生成失败")

            pbar.update(1)

            # 短暂延迟，避免API请求过快
            time.sleep(1)

    # 输出最终统计
    print(f"\n=== 📈 处理完成统计 ===")
    print(f"✅ 成功生成: {success_count}/{len(stories_to_process)} 个封面提示词")
    print(f"❌ 生成失败: {failure_count}/{len(stories_to_process)} 个封面提示词")
    print(f"📊 成功率: {success_count/len(stories_to_process)*100:.1f}%")


def main():
    """主函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="根据科幻故事内容生成文生图封面提示词")

    # 添加命令行参数
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="强制重新生成封面提示词，忽略已有文件",
    )
    parser.add_argument(
        "--start",
        type=int,
        help="指定开始处理的故事索引",
    )
    parser.add_argument(
        "--end",
        type=int,
        help="指定结束处理的故事索引",
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 验证参数
    if args.start is not None and args.end is not None:
        if args.start > args.end:
            print("❌ 错误：开始索引不能大于结束索引")
            return
        if args.start <= 0 or args.end <= 0:
            print("❌ 错误：索引必须大于 0")
            return

    print("🎨 科幻故事封面提示词生成器")
    print("=" * 50)

    # 设置OpenAI客户端
    client = setup_openai_client()
    print("✅ OpenAI客户端初始化成功")

    # 处理故事
    process_stories(client, args.force, args.start, args.end)

    print("\n🎉 封面提示词生成任务完成!")


if __name__ == "__main__":
    main()
