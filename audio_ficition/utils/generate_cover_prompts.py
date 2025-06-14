"""
多主题故事封面图片生成提示词工具

功能说明:
此脚本用于根据不同主题故事内容生成文生图的封面页提示词。
支持的主题：scifi、thriller、horror、fantasy、romance
脚本使用UNI API，GPT-4.1-mini模型生成：
1. 体现女主角（外星人，性感年轻，大胸身材，人形面貌，特殊肤色）的魅力
2. 体现男主角的特征
3. 根据故事情节设计的背景和场景
4. 动人且具有吸引力的视觉元素

输入:
- 故事文本内容（来自ai_studio_bot.py的输出）
- 故事文件路径:
  * Intel Mac: /Volumes/dhl/audio/{theme}/full_story/[故事索引].txt
  * Apple Silicon: /Users/donghaoliu/Documents/audio/{theme}/full_story/[故事索引].txt

输出:
- 封面提示词文件:
  * Intel Mac: /Volumes/dhl/audio/{theme}/cover_prompts/[故事索引].txt
  * Apple Silicon: /Users/donghaoliu/Documents/audio/{theme}/cover_prompts/[故事索引].txt

使用方法:
1. 处理所有主题: python generate_cover_prompts.py
2. 处理指定主题: python generate_cover_prompts.py --theme scifi
3. 处理多个主题: python generate_cover_prompts.py --theme scifi thriller
4. 强制重新生成: python generate_cover_prompts.py --theme scifi -f
5. 指定故事索引范围: python generate_cover_prompts.py --theme scifi --start 1 --end 10

注意:
- 需要设置环境变量UNI_API_KEY以提供OpenAI API密钥
- 脚本支持断点续传，中断后可从上次停止的位置继续处理
- 支持的主题：scifi、thriller、horror、fantasy、romance
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
        "story_dir": os.path.join(base_path, "full_story"),
        "cover_dir": os.path.join(base_path, "cover_prompts"),
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


def generate_cover_prompt(client, story_content, story_index, max_retries=3):
    """使用OpenAI的GPT模型生成封面图片提示词，失败时自动重试"""
    if not story_content.strip():
        print(f"警告: 故事 {story_index} 的内容为空，无法生成封面提示词")
        return ""

    for attempt in range(max_retries):
        try:
            system_prompt = """你是一位专业的视觉故事叙述师和 AI 艺术总监，深谙 YouTube 平台的用户心理。你的核心任务是阅读我提供的完整故事（科幻、恐怖、惊悚、奇幻等类型），并为其创作一个能作为 YouTube 视频封面的"文生图"（Text-to-Image）提示词。
你的输出必须严格遵守以下原则和格式：
一、核心目标：
生成的提示词必须旨在创造一个**"高点击率"**的封面。这意味着图像需要具备以下特质：
视觉冲击力 (抓眼球): 画面要有强烈的戏剧性、动态感或神秘感。使用高对比度的光影、鲜明的色彩或引人注目的构图。
激发好奇心 (悬念感): 聚焦于故事中最具悬念、最不寻常或最关键的"一瞬间"。只展示问题或危机，不展示答案或结局，引诱观众点击一探究竟。
高度美学 (好看): 追求电影级的画面质感、专业的艺术风格和精致的细节，让封面看起来高质量、不廉价。
焦点清晰: 图像必须有一个明确的视觉焦点（一个角色、一个物体或一个奇观），避免画面元素过于杂乱。
贴合类型: 提示词的风格必须与故事类型（Sci-fi, Horror, Thriller, Fantasy）的经典视觉元素高度一致。
二、提示词构成要素：
你的提示词必须像一位导演在给特效团队下达指令。请包含以下部分的关键描述：
主体与动作 (Subject & Action): 描述画面的核心人物/怪物/物体，以及他们正在做的、或即将发生的关键动作。
场景与环境 (Setting & Environment): 描绘故事发生的标志性环境，突出其氛围。
光影与色彩 (Lighting & Color): 这是营造氛围的灵魂。明确指出光线来源（如霓虹灯、手电筒光束、诡异的月光）、色调（如赛博朋克的蓝紫色、恐怖片的阴冷色调）。
构图与视角 (Composition & Angle): 指定镜头视角，例如"特写镜头(close-up shot)"、"广角镜头(wide-angle shot)"、"从低角度仰视(low-angle shot)"，以增强戏剧性。
艺术风格与细节 (Art Style & Details): 指定最终图像的风格。例如："照片级真实感(photorealistic)"、"电影感(cinematic)"、"数字绘画(digital painting)"、"概念艺术(concept art)"、"虚幻引擎渲染(unreal engine)"、"8K"、"细节丰富(intricate details)"。
三、输出格式：
针对每一个故事，只生成一个最终的提示词。
这个提示词由 2 到 3 个连贯的描述性句子组成。
不要对故事进行任何总结或分析。
不要在提示词前后添加任何解释性文字，如"这是给你的提示词："。
直接输出最终可用于 AI 绘画工具的提示词文本。
你的使命是： 运用你的创造力，将文字故事的灵魂，精准地转化为一幅能瞬间捕获观众眼球的视觉杰作。"""

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


def get_existing_stories(theme):
    """获取已经生成的故事文件列表"""
    paths = get_base_paths(theme)
    story_dir = paths["story_dir"]

    if not os.path.exists(story_dir):
        print(f"故事目录不存在: {story_dir}")
        return {}

    story_files = glob.glob(os.path.join(story_dir, "*.txt"))
    stories = {}

    for file_path in story_files:
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
                if content:  # 只包含有内容的故事
                    stories[story_index] = content
            except Exception as e:
                print(f"读取故事文件 {file_path} 时出错: {e}")

    return stories


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


def get_theme_system_prompt(theme):
    """根据主题获取相应的系统提示词"""
    base_prompt = """你是一位专业的视觉故事叙述师和 AI 艺术总监，深谙 YouTube 平台的用户心理。你的核心任务是阅读我提供的完整故事，并为其创作一个能作为 YouTube 视频封面的"文生图"（Text-to-Image）提示词。
你的输出必须严格遵守以下原则和格式：
一、核心目标：
生成的提示词必须旨在创造一个**"高点击率"**的封面。这意味着图像需要具备以下特质：
视觉冲击力 (抓眼球): 画面要有强烈的戏剧性、动态感或神秘感。使用高对比度的光影、鲜明的色彩或引人注目的构图。
激发好奇心 (悬念感): 聚焦于故事中最具悬念、最不寻常或最关键的"一瞬间"。只展示问题或危机，不展示答案或结局，引诱观众点击一探究竟。
高度美学 (好看): 追求电影级的画面质感、专业的艺术风格和精致的细节，让封面看起来高质量、不廉价。
焦点清晰: 图像必须有一个明确的视觉焦点（一个角色、一个物体或一个奇观），避免画面元素过于杂乱。"""

    theme_specific = {
        "scifi": "贴合科幻类型: 提示词必须包含未来科技、外星元素、太空场景、机器人、高科技装备等科幻视觉元素。体现女主角（外星人，性感年轻，大胸身材，人形面貌，特殊肤色）的魅力。",
        "thriller": "贴合惊悚类型: 提示词必须包含紧张氛围、悬疑元素、阴暗环境、危险情境等惊悚视觉元素。重点营造紧张和不安的氛围。",
        "horror": "贴合恐怖类型: 提示词必须包含恐怖氛围、诡异元素、黑暗环境、恐怖生物等恐怖视觉元素。重点营造恐惧和惊悚的氛围。",
        "fantasy": "贴合奇幻类型: 提示词必须包含魔法元素、奇幻生物、神秘环境、魔法装备等奇幻视觉元素。重点营造神秘和奇幻的氛围。",
        "romance": "贴合浪漫类型: 提示词必须包含浪漫氛围、优美环境、情感表达、温馨场景等浪漫视觉元素。重点营造温馨和浪漫的氛围。",
    }

    continuation = """
二、提示词构成要素：
你的提示词必须像一位导演在给特效团队下达指令。请包含以下部分的关键描述：
主体与动作 (Subject & Action): 描述画面的核心人物/怪物/物体，以及他们正在做的、或即将发生的关键动作。
场景与环境 (Setting & Environment): 描绘故事发生的标志性环境，突出其氛围。
光影与色彩 (Lighting & Color): 这是营造氛围的灵魂。明确指出光线来源、色调搭配。
构图与视角 (Composition & Angle): 指定镜头视角，例如"特写镜头(close-up shot)"、"广角镜头(wide-angle shot)"、"从低角度仰视(low-angle shot)"，以增强戏剧性。
艺术风格与细节 (Art Style & Details): 指定最终图像的风格。例如："照片级真实感(photorealistic)"、"电影感(cinematic)"、"数字绘画(digital painting)"、"概念艺术(concept art)"、"虚幻引擎渲染(unreal engine)"、"8K"、"细节丰富(intricate details)"。
三、输出格式：
针对每一个故事，只生成一个最终的提示词。
这个提示词由 2 到 3 个连贯的描述性句子组成。
不要对故事进行任何总结或分析。
不要在提示词前后添加任何解释性文字，如"这是给你的提示词："。
直接输出最终可用于 AI 绘画工具的提示词文本。
你的使命是： 运用你的创造力，将文字故事的灵魂，精准地转化为一幅能瞬间捕获观众眼球的视觉杰作。"""

    return (
        base_prompt
        + "\n"
        + theme_specific.get(theme, theme_specific["scifi"])
        + continuation
    )


def process_stories_for_theme(
    client, theme, force=False, start_index=None, end_index=None
):
    """处理指定主题的所有故事，生成封面提示词"""
    print(f"\n=== 🎨 开始处理 {theme.upper()} 主题 ===")

    # 获取所有已存在的故事
    stories = get_existing_stories(theme)

    if not stories:
        print(f"未找到 {theme} 主题的任何故事文件")
        return {"success": 0, "failure": 0, "total": 0}

    # 获取已存在的封面提示词
    existing_prompts = get_existing_cover_prompts(theme)

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
        print(f"{theme} 主题：所有指定范围内的故事都已有封面提示词")
        return {"success": 0, "failure": 0, "total": 0}

    print(f"\n=== 📊 {theme} 主题封面提示词生成分析 ===")
    print(f"总故事数量: {len(stories)}")
    print(f"已有封面提示词: {len(existing_prompts)}")
    print(f"需要处理的故事: {len(stories_to_process)}")
    print(f"处理的故事索引: {sorted(stories_to_process.keys())}")

    # 统计变量
    success_count = 0
    failure_count = 0

    # 获取主题相关的系统提示词
    system_prompt = get_theme_system_prompt(theme)

    # 处理每个故事
    with tqdm(total=len(stories_to_process), desc=f"生成{theme}封面提示词") as pbar:
        for story_index in sorted(stories_to_process.keys()):
            content = stories_to_process[story_index]

            print(f"\n=== 处理 {theme} 故事 {story_index} ===")
            print(f"故事内容长度: {len(content)} 字符")

            # 生成封面提示词
            prompt = generate_cover_prompt_with_theme(
                client, content, story_index, system_prompt
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
        "total": len(stories_to_process),
    }


def generate_cover_prompt_with_theme(
    client, story_content, story_index, system_prompt, max_retries=3
):
    """使用OpenAI的GPT模型生成封面图片提示词，失败时自动重试"""
    if not story_content.strip():
        print(f"警告: 故事 {story_index} 的内容为空，无法生成封面提示词")
        return ""

    for attempt in range(max_retries):
        try:
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
        description="根据多主题故事内容生成文生图封面提示词"
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

    print("🎨 多主题故事封面提示词生成器")
    print("=" * 50)
    print(f"支持的主题: {', '.join(SUPPORTED_THEMES)}")
    print(f"本次处理的主题: {', '.join(args.theme)}")

    # 设置OpenAI客户端
    client = setup_openai_client()
    print("✅ OpenAI客户端初始化成功")

    # 处理故事
    process_stories(client, args.theme, args.force, args.start, args.end)

    print("\n🎉 封面提示词生成任务完成!")


if __name__ == "__main__":
    main()
