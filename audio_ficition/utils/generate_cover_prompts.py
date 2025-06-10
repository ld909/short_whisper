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
            system_prompt = """你是一个顶级的文生图提示词幻想家，擅长将科幻故事的精髓转化为引人入胜的图像提示词，尤其注重男女主角之间生动的互动和丰富的情感表达。目标是为Youtube视频封面创作出既符合故事内核，又极具视觉吸引力和多样性的图像。

请根据提供的科幻故事文本，生成一个详细的、用于图像生成的英文提示词。提示词应严格遵循以下结构和要求：

1.  女主角 (Female Protagonist):
    -   种族：外星人。
    -   外貌：视觉年龄约20岁，拥有令人惊叹的完美脸蛋和黄金比例的S 形的丰满身材。五官精致且符合人类审美标准，严格保持人形五官结构，不要出现任何非人或令人不适的器官增多/变形（例如多个眼睛、鼻子等）。
    -   外星特征：鼓励体现其独特的、迷人的外星特征，例如：特殊的肤色（如水晶般、金属光泽、星云色彩等，非地球人类肤色）、独特的发色/发型、奇异但美丽的瞳色等。这些特征应增强其魅力，而非制造怪异感。
    -   衣着：穿着时尚、性感或符合其身份/故事情节的未来感服饰，能够突显其身材和魅力。

2.  男主角 (Male Protagonist):
    -   根据故事内容描述其年龄、外貌、衣着及气质特征。

3.  核心互动与情感 (Crucial Interaction & Emotion):
    -   互动场景与姿态 (MUST BE VARIED): 必避免所有场景都是男女主角紧靠站立的静态画面。 充分发挥想象力，根据故事基调和人物关系，设计丰富多样的互动。即使故事本身缺乏明显互动描写，也请主动创造合理的互动情景。
        -   参考场景（请灵活运用并创造更多）：
            -   日常生活：在充满异星风情的餐厅或家中共同进餐、在未来都市的街头漫步、一起逛充满奇珍异宝的外星跳蚤市场或高科技购物中心、共同观看全息电影、在飞船的休息室里放松交谈。
            -   冒险与合作：共同驾驶未来飞行器穿越星际、并肩探索神秘的古代遗迹、在紧张的追逐中互相掩护、在外星的奇特自然环境中露营或徒步。
            -   浪漫与情感：在星空下牵手、深情拥抱（可以是温馨的、也可以是充满张力的）、在异星的独特节日里共舞、享受蜜月般的旅行时光（如在外星度假胜地）、互相依偎着看窗外的宇宙奇观。
            -   趣味与探索：一起参与某种未来风格的运动或游戏、共同研究一个神秘的外星装置、在外星宠物店挑选奇特的宠物。
    -   表情与情绪 (MUST BE EXPRESSIVE): 摒弃单一冷酷或面无表情的设定。 为男女主角赋予丰富且符合情境的表情和情绪，以增强画面的故事性和感染力。
        -   参考情绪（请灵活组合）： 开心、喜悦、甜蜜、好奇、惊喜、期待、深情、专注、沉思、警惕、暧昧、惊讶、悲伤、担忧、紧张等。
        -   目标： 通过表情和肢体语言生动展现角色的内心世界以及他们之间的化学反应。

4.  背景环境 (Background & Setting):
    -   根据故事情节设计，力求多样化、富有想象力并充满科幻细节。
    -   可以是：繁华的未来都市天际线、奇异的外星自然风光（如发光森林、水晶洞穴）、高科技飞船的舰桥或内部、神秘的古代外星遗迹、热闹的星际港口、宇宙深处的壮丽星云等。
    -   鼓励在背景中融入独特的外星文化元素或科技装置，以增强世界的真实感和吸引力。

5.  整体艺术风格与氛围 (Overall Art Style & Atmosphere):
    -   风格：电影级真实感 (cinematic realism)，8K分辨率，细节丰富，光影效果出色。
    -   氛围：根据具体情节可以是浪漫的、神秘的、惊险的、温馨的、史诗感的等，但总体应具有强烈的视觉冲击力和故事性，能够迅速吸引观众的注意力并引发其好奇心。

6.  输出格式 (Output Format):
    -   直接返回英文的文生图提示词。
    -   提示词长度适中，一般控制在2-4句话，确保关键信息全面且不冗余。
    -   严格控制提示词长度，不要太长，精炼，并且表达完全。
    -   不要出现任何非英文的单词。
    -   言简意赅，不要太长，这点一定要重视和满足。
    -   不要添加任何中文解释或其他无关文字。

角色魅力：在所有设计中，始终要突出女主角的魅力、美丽与动人之处，以及男女主角之间互动和能传递各种情感的关系。"""

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
        # 排除以点开头的文件（如.DS_Store等）
        if basename.startswith("."):
            continue
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
