"""
YouTube封面AI绘图提示词生成工具

功能说明:
此脚本基于故事描述内容，使用Google Gemini 2.5 Flash模型生成专业的YouTube视频封面AI绘图提示词。
脚本采用病毒式封面设计理念，专注于创造高点击率的视觉元素。

核心特性:
• 支持的主题：scifi（科幻）、thriller（惊悚）、horror（恐怖）、fantasy（奇幻）、romance（浪漫）
• 采用YouTube封面策略：极端情绪表达、关键戏剧瞬间、简洁有力的视觉语言
• 模型：Google Gemini 2.5 Flash Preview (gemini-2.5-flash-preview-04-17)
• 智能系统指令：根据不同主题调整视觉风格和重点元素
• 生成简洁高效的提示词（3-4句话），避免系统报错

输入源文件:
• 故事描述文件（由story_description_generator.py生成）
• 文件路径结构:
  - Intel Mac: /Volumes/dhl/audio/{theme}/description/{索引}.txt
  - Apple Silicon: /Users/donghaoliu/Documents/audio/{theme}/description/{索引}.txt
  - Linux/Ubuntu: /media/dhl/audio/{theme}/description/{索引}.txt

输出目标文件:
• 封面提示词文件:
  - Intel Mac: /Volumes/dhl/audio/{theme}/cover_prompts/{索引}.txt
  - Apple Silicon: /Users/donghaoliu/Documents/audio/{theme}/cover_prompts/{索引}.txt
  - Linux/Ubuntu: /media/dhl/audio/{theme}/cover_prompts/{索引}.txt

使用方法:
1. 处理所有主题: python generate_cover_prompts.py
2. 指定单个主题: python generate_cover_prompts.py --theme scifi
3. 指定多个主题: python generate_cover_prompts.py --theme scifi thriller horror
4. 强制重新生成: python generate_cover_prompts.py --theme fantasy -f
5. 指定索引范围: python generate_cover_prompts.py --theme romance --start 5 --end 15
6. 组合参数使用: python generate_cover_prompts.py --theme scifi thriller -f --start 1 --end 20

前置条件:
• 环境变量UNI_API_KEY: 必须设置有效的API密钥
• 先决脚本: 需要运行story_description_generator.py生成故事描述文件
• 网络环境: 需要稳定的网络连接访问Gemini API

特性说明:
• 断点续传: 支持中断后继续处理，自动跳过已生成的文件
• 智能重试: API调用失败时自动重试，最多3次
• 进度显示: 使用tqdm显示处理进度和状态
• 错误处理: 详细的错误日志和异常处理机制
• 跨平台: 自动识别Mac芯片类型和操作系统，适配路径结构
"""

import os
import sys
import time
import argparse
import platform
from google import genai
from google.genai import types
import glob
import re
from tqdm import tqdm


# 支持的主题列表
SUPPORTED_THEMES = ["scifi", "thriller", "horror", "fantasy", "romance"]


def get_chip_type():
    """检测Mac芯片类型"""
    try:
        import subprocess

        result = subprocess.run(["uname", "-m"], capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return "unknown"


def get_base_paths(theme):
    """根据操作系统和主题获取基础路径"""
    if theme not in SUPPORTED_THEMES:
        raise ValueError(
            f"不支持的主题: {theme}。支持的主题: {', '.join(SUPPORTED_THEMES)}"
        )

    system = platform.system().lower()

    if system == "darwin":  # Mac
        chip_type = get_chip_type()
        if chip_type == "x86_64":  # Intel Mac
            base_path = f"/Volumes/dhl/audio/{theme}"
        else:  # Apple Silicon
            base_path = f"/Users/donghaoliu/Documents/audio/{theme}"
    else:  # Linux/Ubuntu
        base_path = f"/media/dhl/audio/{theme}"

    return {
        "description_dir": os.path.join(base_path, "description"),
        "cover_dir": os.path.join(base_path, "cover_prompts"),
    }


def setup_gemini_client():
    """设置Google Gemini客户端并验证API密钥"""
    api_key = os.environ.get("UNI_API_KEY")

    if not api_key:
        print("错误: 未找到API密钥")
        print("请设置环境变量UNI_API_KEY")
        print("例如: export UNI_API_KEY='your-api-key'")
        sys.exit(1)

    try:
        client = genai.Client(
            http_options=types.HttpOptions(base_url="https://api.uniapi.io/gemini"),
            api_key=api_key,
        )
        return client
    except Exception as e:
        print(f"初始化Gemini客户端时出错: {e}")
        print("这可能是由于以下原因:")
        print("1. Google GenAI库版本不兼容，请尝试: pip install google-genai")
        print("2. API密钥格式不正确")
        print("3. 网络连接问题")
        sys.exit(1)


def generate_cover_prompt(client, description_content, story_index, max_retries=3):
    """使用Google Gemini模型生成封面图片提示词，失败时自动重试"""
    if not description_content.strip():
        print(f"警告: 故事 {story_index} 的描述为空，无法生成封面提示词")
        return ""

    budget = 1024  # Thinking budget for Gemini

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-pro-preview-06-05",
                contents=f"故事描述：\n\n{description_content}",
                config=types.GenerateContentConfig(
                    system_instruction=[
                        "你是一位顶级的YouTube内容策略专家和病毒式封面设计大师。你的核心任务是，根据我提供的故事描述，创作一个用于AI文生图的、能够生成极具吸引力的YouTube视频封面的提示词。你创作的提示词必须严格遵循以下四大原则，以确保封面能够获得最高点击率：",
                        "第一，极端情绪与冲突：画面必须捕捉并放大一个极端的情绪，例如极度的震惊、狂喜、恐惧或悲伤。或者，画面要展现一个强烈的视觉冲突，比如巨大与渺小、光明与黑暗、整洁与混乱的强烈对比。",
                        "第二，聚焦关键瞬间：从故事描述中，精准提炼出最具戏剧张力、悬念最强或最出人意料的一瞬间。这个瞬间应该让观众立刻好奇接下来发生了什么，而不是故事的结局。永远展示问题或过程，而不是答案。",
                        "第三，视觉语言简洁有力：构图必须简洁，有一个绝对的视觉焦点，通常是一个人物的面部特写或一个关键物体。背景要服务于主体，避免不必要的元素分散注意力。色彩要鲜艳、饱和度高，光线要有戏剧感，比如强烈的逆光、聚光灯效果或神秘的环境光。",
                        "提示词不能太长，不然系统会报错，建议3-4句话就行了，就足够好了。信息密度增加。直接返回你的提示词，不用多余信息，不用添加其他说明。",
                    ],
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=budget, include_thoughts=True
                    ),
                ),
            )
            result = response.text.strip()
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


def get_existing_stories(theme):
    """获取已经生成的故事描述文件列表"""
    paths = get_base_paths(theme)
    description_dir = paths["description_dir"]

    if not os.path.exists(description_dir):
        print(f"故事描述目录不存在: {description_dir}")
        return {}

    description_files = glob.glob(os.path.join(description_dir, "*.txt"))
    descriptions = {}

    for file_path in description_files:
        basename = os.path.basename(file_path)
        # 排除以点开头的文件（如.DS_Store等）
        if basename.startswith("."):
            continue
        match = re.match(r"(\d+)\.txt", basename)
        if match:
            story_index = int(match.group(1))
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:  # 只包含有内容的描述
                    descriptions[story_index] = content
            except Exception as e:
                print(f"读取故事描述文件 {file_path} 时出错: {e}")

    return descriptions


def get_existing_cover_prompts(theme):
    """获取已经生成的封面提示词列表"""
    paths = get_base_paths(theme)
    cover_dir = paths["cover_dir"]

    if not os.path.exists(cover_dir):
        os.makedirs(cover_dir, exist_ok=True)
        return set()

    existing_files = glob.glob(os.path.join(cover_dir, "*.txt"))
    existing_indices = set()

    for file_path in existing_files:
        basename = os.path.basename(file_path)
        # 排除以点开头的文件（如.DS_Store等）
        if basename.startswith("."):
            continue
        match = re.match(r"(\d+)\.txt", basename)
        if match:
            existing_indices.add(int(match.group(1)))

    return existing_indices


def save_cover_prompt(theme, story_index, prompt_content):
    """保存封面提示词到文件"""
    paths = get_base_paths(theme)
    cover_dir = paths["cover_dir"]

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


def get_theme_system_instruction(theme):
    """根据主题获取相应的系统指令"""
    base_instruction = [
        "你是一位顶级的YouTube内容策略专家和病毒式封面设计大师。你的核心任务是，根据我提供的故事描述，创作一个用于AI文生图的、能够生成极具吸引力的YouTube视频封面的提示词。你创作的提示词必须严格遵循以下原则，以确保封面能够获得最高点击率：",
        "第一，极端情绪与冲突：画面必须捕捉并放大一个极端的情绪，例如极度的震惊、狂喜、恐惧或悲伤。或者，画面要展现一个强烈的视觉冲突，比如巨大与渺小、光明与黑暗、整洁与混乱的强烈对比。",
        "第二，聚焦关键瞬间：从故事描述中，精准提炼出最具戏剧张力、悬念最强或最出人意料的一瞬间。这个瞬间应该让观众立刻好奇接下来发生了什么，而不是故事的结局。永远展示问题或过程，而不是答案。",
        "第三，视觉语言简洁有力：构图必须简洁，有一个绝对的视觉焦点，通常是一个人物的面部特写或一个关键物体。背景要服务于主体，避免不必要的元素分散注意力。色彩要鲜艳、饱和度高，光线要有戏剧感，比如强烈的逆光、聚光灯效果或神秘的环境光。",
    ]

    theme_specific = {
        "scifi": "特别针对科幻主题：重点突出未来科技、外星元素、太空场景等科幻视觉元素，体现女主角（外星人，性感年轻，大胸身材，人形面貌，特殊肤色）的魅力。",
        "thriller": "特别针对惊悚主题：重点营造紧张氛围、悬疑元素、阴暗环境、危险情境等惊悚视觉元素。",
        "horror": "特别针对恐怖主题：重点营造恐怖氛围、诡异元素、黑暗环境、恐怖生物等恐怖视觉元素。",
        "fantasy": "特别针对奇幻主题：重点突出魔法元素、奇幻生物、神秘环境、魔法装备等奇幻视觉元素。",
        "romance": "特别针对浪漫主题：重点营造浪漫氛围、优美环境、情感表达、温馨场景等浪漫视觉元素。",
    }

    instruction = base_instruction.copy()
    instruction.append(theme_specific.get(theme, theme_specific["scifi"]))
    instruction.append(
        "提示词不能太长，不然系统会报错，建议3-4句话就行了，就足够好了，信息密度增加。直接返回你的提示词，不用多余信息。"
    )

    return instruction


def process_stories_for_theme(
    client, theme, force=False, start_index=None, end_index=None
):
    """处理指定主题的所有故事，生成封面提示词"""
    print(f"\n=== 🎨 开始处理 {theme.upper()} 主题 ===")

    # 获取所有已存在的故事描述
    descriptions = get_existing_stories(theme)

    if not descriptions:
        print(f"未找到 {theme} 主题的任何故事描述文件")
        print(f"请先运行 story_description_generator.py 生成故事描述")
        return {"success": 0, "failure": 0, "total": 0}

    # 获取已存在的封面提示词
    existing_prompts = get_existing_cover_prompts(theme)

    # 过滤需要处理的故事
    descriptions_to_process = {}

    for story_index, content in descriptions.items():
        # 应用索引范围过滤
        if start_index is not None and story_index < start_index:
            continue
        if end_index is not None and story_index > end_index:
            continue

        # 检查是否需要重新生成
        if force or story_index not in existing_prompts:
            descriptions_to_process[story_index] = content

    if not descriptions_to_process:
        print(f"{theme} 主题：所有指定范围内的故事都已有封面提示词")
        return {"success": 0, "failure": 0, "total": 0}

    print(f"\n=== 📊 {theme} 主题封面提示词生成分析 ===")
    print(f"总故事描述数量: {len(descriptions)}")
    print(f"已有封面提示词: {len(existing_prompts)}")
    print(f"需要处理的故事: {len(descriptions_to_process)}")
    print(f"处理的故事索引: {sorted(descriptions_to_process.keys())}")

    # 统计变量
    success_count = 0
    failure_count = 0

    # 获取主题相关的系统指令
    system_instruction = get_theme_system_instruction(theme)

    # 处理每个故事
    with tqdm(
        total=len(descriptions_to_process), desc=f"生成{theme}封面提示词"
    ) as pbar:
        for story_index in sorted(descriptions_to_process.keys()):
            content = descriptions_to_process[story_index]

            print(f"\n=== 处理 {theme} 故事 {story_index} ===")
            print(f"故事描述长度: {len(content)} 字符")

            # 生成封面提示词
            prompt = generate_cover_prompt_with_theme(
                client, content, story_index, system_instruction
            )

            if prompt:
                # 保存提示词
                if save_cover_prompt(theme, story_index, prompt):
                    success_count += 1
                    print(f"✅ {theme} 故事 {story_index} 封面提示词生成成功")
                    # 显示部分提示词内容作为预览
                    preview = prompt[:200] + "..." if len(prompt) > 200 else prompt
                    print(f"💡 提示词预览: {preview}")
                else:
                    failure_count += 1
                    print(f"❌ {theme} 故事 {story_index} 封面提示词保存失败")
            else:
                failure_count += 1
                print(f"❌ {theme} 故事 {story_index} 封面提示词生成失败")

            pbar.update(1)

            # 短暂延迟，避免API请求过快
            time.sleep(1)

    return {
        "success": success_count,
        "failure": failure_count,
        "total": len(descriptions_to_process),
    }


def generate_cover_prompt_with_theme(
    client, description_content, story_index, system_instruction, max_retries=3
):
    """使用Google Gemini模型生成封面图片提示词，失败时自动重试"""
    if not description_content.strip():
        print(f"警告: 故事 {story_index} 的描述为空，无法生成封面提示词")
        return ""

    budget = 1024  # Thinking budget for Gemini

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-preview-04-17",
                contents=f"故事描述：\n\n{description_content}",
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=budget, include_thoughts=True
                    ),
                ),
            )
            result = response.text.strip()
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


def process_stories(client, themes, force=False, start_index=None, end_index=None):
    """处理所有指定主题的故事，生成封面提示词"""
    total_stats = {"success": 0, "failure": 0, "total": 0}

    for theme in themes:
        try:
            stats = process_stories_for_theme(
                client, theme, force, start_index, end_index
            )
            total_stats["success"] += stats["success"]
            total_stats["failure"] += stats["failure"]
            total_stats["total"] += stats["total"]
        except Exception as e:
            print(f"❌ 处理 {theme} 主题时出错: {e}")

    # 输出最终统计
    print(f"\n=== 📈 所有主题处理完成统计 ===")
    print(f"处理的主题: {', '.join(themes)}")
    print(
        f"✅ 总共成功生成: {total_stats['success']}/{total_stats['total']} 个封面提示词"
    )
    print(
        f"❌ 总共生成失败: {total_stats['failure']}/{total_stats['total']} 个封面提示词"
    )
    if total_stats["total"] > 0:
        print(f"📊 总体成功率: {total_stats['success']/total_stats['total']*100:.1f}%")


def main():
    """主函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description="根据多主题故事描述生成文生图封面提示词"
    )

    # 添加命令行参数
    parser.add_argument(
        "--theme",
        nargs="+",
        choices=SUPPORTED_THEMES,
        default=SUPPORTED_THEMES,
        help=f"指定要处理的主题，可选: {', '.join(SUPPORTED_THEMES)}。默认处理所有主题。",
    )
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

    print("🎨 多主题故事封面提示词生成器 (Google Gemini)")
    print("=" * 50)
    print(f"支持的主题: {', '.join(SUPPORTED_THEMES)}")
    print(f"本次处理的主题: {', '.join(args.theme)}")
    print("💡 注意：请确保已运行 story_description_generator.py 生成故事描述")

    # 设置Gemini客户端
    client = setup_gemini_client()
    print("✅ Google Gemini客户端初始化成功")

    # 处理故事
    process_stories(client, args.theme, args.force, args.start, args.end)

    print("\n🎉 封面提示词生成任务完成!")


if __name__ == "__main__":
    main()
