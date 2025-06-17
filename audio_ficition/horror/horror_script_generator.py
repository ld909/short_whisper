#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Horror Story Script Parameter Generator
恐怖故事脚本参数生成器

功能描述:
    自动生成恐怖小说的故事参数，用于创建有声书脚本。
    基于配置文件随机组合各种恐怖元素（主角、反派、超自然现象、心理要素等），
    生成完整的恐怖故事创作提示词模板。

支持的恐怖类型包括：
    - 超自然恐怖 (Supernatural Horror)
    - 心理恐怖 (Psychological Horror)
    - 哥特式恐怖 (Gothic Horror)
    - 宇宙恐怖 (Cosmic Horror)
    - 连环杀手/惊悚 (Serial Killer/Thriller)
    - 民俗恐怖 (Folk Horror)
    - 身体恐怖 (Body Horror)
    - 科幻恐怖 (Sci-Fi Horror)
    - 僵尸/末日恐怖 (Zombie/Apocalyptic Horror)

依赖文件:
    - config.json: 配置文件，包含所有可选的恐怖故事元素
      必须放在脚本同一目录下

输入:
    - config.json: 恐怖故事元素配置文件
    - 命令行参数: 可选的生成数量和输出目录

输出:
    - 默认目录: /Users/donghaoliu/Documents/audio/story_param/horror/ (macOS)
    - 备选目录: /media/dhl/audio/horror/story_param/ (Linux)
    - 文件格式: {索引号}.txt (如: 1.txt, 2.txt, 3.txt...)
    - 内容: 完整的恐怖故事创作提示词，可直接用于AI生成故事

使用方法:
    1. 基本使用（生成1个故事参数）:
       python horror_script_generator.py

    2. 批量生成（生成N个故事参数）:
       python horror_script_generator.py -n 5
       python horror_script_generator.py --number 10

    3. 指定输出目录:
       python horror_script_generator.py -o /custom/path

    4. 组合使用:
       python horror_script_generator.py -n 3 -o /custom/path

    5. 查看帮助:
       python horror_script_generator.py -h

注意事项:
    - 确保config.json文件存在且格式正确
    - 输出目录会自动创建（如果不存在）
    - 脚本会自动避免覆盖现有文件（从最大索引号+1开始）
    - 每个生成的故事参数包含完整的恐怖设定、角色配置、情节结构等
    - 支持macOS和Linux平台的默认路径
    - 生成内容为英文，固定时长120分钟

作者: 恐怖故事生成系统
版本: 2.0
创建时间: 2024
"""

import json
import random
import os
import re
import argparse
import platform
import glob

# Fixed target length in minutes
FIXED_TARGET_LENGTH = 120


def get_base_output_path():
    """获取正确的输出目录，支持Intel Mac和Apple Silicon"""
    # 首先尝试从环境变量获取（由multi_theme_story_generator.py设置）
    base_dir = os.environ.get("AUDIO_BASE_DIR")

    if base_dir:
        output_dir = f"{base_dir}/horror/story_param"
        print(f"📁 使用环境变量指定的输出目录: {output_dir}")
        return output_dir

    # 如果环境变量未设置，根据芯片类型自动判断
    system = platform.system()
    if system == "Darwin":  # macOS
        machine = platform.machine().lower()
        processor = platform.processor().lower()

        # Apple Silicon
        is_apple_silicon = (
            machine == "arm64"
            or "arm" in machine
            or "apple" in processor
            or "m1" in processor
            or "m2" in processor
            or "m3" in processor
        )

        if is_apple_silicon:
            output_dir = "/Users/donghaoliu/Documents/audio/horror/story_param"
            print(f"🍎 检测到Apple Silicon Mac，使用路径: {output_dir}")
        else:
            output_dir = "/Volumes/dhl/audio/horror/story_param"
            print(f"💻 检测到Intel Mac，使用路径: {output_dir}")

        return output_dir
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/audio/horror/story_param"


# 获取当前脚本的目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 配置文件路径
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
# 默认输出目录
DEFAULT_OUTPUT_DIR = get_base_output_path()


def load_config(filepath=CONFIG_FILE):
    """加载配置文件"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            config = json.load(f)
            print(
                f"Configuration loaded successfully, contains {len(config)} main configuration items"
            )
            return config
    except FileNotFoundError:
        print(f"Error: Configuration file '{filepath}' not found")
        print("Please ensure config.json file is in the same directory as the script")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Configuration file '{filepath}' contains invalid JSON format")
        print(f"JSON parsing error: {e}")
        exit(1)
    except Exception as e:
        print(f"Unknown error occurred while loading configuration file: {e}")
        exit(1)


def select_random_element(element_list):
    """从列表中随机选择一个元素"""
    if not element_list:
        return "[Empty List]"
    return random.choice(element_list)


def select_random_elements(element_list, count=None, min_count=1, max_count=3):
    """从列表中随机选择多个元素"""
    if not element_list:
        return []

    if count is None:
        count = random.randint(min_count, min(max_count, len(element_list)))

    actual_count = min(count, len(element_list))
    return random.sample(element_list, k=actual_count)


def select_random_name(name_config):
    """从名字配置中选择一个随机名字"""
    return select_random_element(name_config["options"])


def generate_horror_story_parameters(config):
    """生成恐怖故事参数"""
    params = {}

    # === 故事基本设定 - Fixed to 120 minutes ===
    params["target_audio_length_minutes"] = FIXED_TARGET_LENGTH
    params["suggested_chapter_count"] = 8  # 120 minutes / 15 minutes per chapter

    # 主要恐怖类型和次要元素
    params["primary_horror_subgenre"] = select_random_element(
        config["story_settings"]["primary_horror_subgenres"]
    )
    params["secondary_horror_elements"] = ", ".join(
        select_random_elements(
            config["story_settings"]["secondary_horror_elements"], count=2
        )
    )

    # 氛围和设定
    params["horror_atmosphere"] = select_random_element(
        config["story_settings"]["horror_atmospheres"]
    )
    params["primary_location"] = select_random_element(
        config["story_settings"]["settings_locations"]
    )
    params["time_period"] = select_random_element(
        config["story_settings"]["time_periods"]
    )

    # === 主角设定 ===
    params["protagonist_name"] = select_random_name(config["protagonist_names"])
    params["protagonist_archetype"] = select_random_element(
        config["protagonist_elements"]["archetypes"]
    )
    params["protagonist_background"] = select_random_element(
        config["protagonist_elements"]["backgrounds"]
    )
    params["protagonist_psychological_trait"] = select_random_element(
        config["protagonist_elements"]["psychological_traits"]
    )
    params["protagonist_fatal_flaw"] = select_random_element(
        config["protagonist_elements"]["fatal_flaws"]
    )

    # === 反派设定 ===
    params["antagonist_name"] = select_random_name(config["antagonist_names"])

    # 根据恐怖类型选择合适的反派类型
    if params["primary_horror_subgenre"] in [
        "Supernatural Horror",
        "Gothic Horror",
        "Cosmic Horror",
        "Folk Horror",
    ]:
        params["antagonist_type"] = select_random_element(
            config["antagonist_elements"]["supernatural_entities"]
        )
    else:
        params["antagonist_type"] = select_random_element(
            config["antagonist_elements"]["human_antagonists"]
        )

    params["antagonist_motivation"] = select_random_element(
        config["antagonist_elements"]["motivations"]
    )
    params["antagonist_methods"] = select_random_element(
        config["antagonist_elements"]["methods"]
    )

    # === 配角设定 ===
    # 怀疑论盟友
    skeptical_ally_template = next(
        (
            item
            for item in config["supporting_character_templates"]
            if item["role"] == "Skeptical Ally"
        ),
        {},
    )
    params["ally1_name"] = select_random_name(config["supporting_character_names"])
    params["ally1_role"] = "Skeptical Ally"
    params["ally1_archetype"] = select_random_element(
        skeptical_ally_template.get("archetypes", ["Rational Friend"])
    )
    params["ally1_function"] = select_random_element(
        skeptical_ally_template.get("functions", ["Provides emotional support"])
    )

    # 知识渊博的向导
    guide_template = next(
        (
            item
            for item in config["supporting_character_templates"]
            if item["role"] == "Knowledgeable Guide"
        ),
        {},
    )
    params["ally2_name"] = select_random_name(config["supporting_character_names"])
    params["ally2_role"] = "Knowledgeable Guide"
    params["ally2_archetype"] = select_random_element(
        guide_template.get("archetypes", ["Local Historian"])
    )
    params["ally2_function"] = select_random_element(
        guide_template.get("functions", ["Provides crucial background information"])
    )

    # 脆弱/无辜角色
    vulnerable_template = next(
        (
            item
            for item in config["supporting_character_templates"]
            if item["role"] == "Innocent/Vulnerable"
        ),
        {},
    )
    params["vulnerable_name"] = select_random_name(config["supporting_character_names"])
    params["vulnerable_role"] = "Innocent/Vulnerable"
    params["vulnerable_archetype"] = select_random_element(
        vulnerable_template.get("archetypes", ["Child in Danger"])
    )
    params["vulnerable_function"] = select_random_element(
        vulnerable_template.get("functions", ["Raises stakes through vulnerability"])
    )

    # 权威人物
    authority_template = next(
        (
            item
            for item in config["supporting_character_templates"]
            if item["role"] == "Authority Figure"
        ),
        {},
    )
    params["authority_name"] = select_random_name(config["supporting_character_names"])
    params["authority_role"] = "Authority Figure"
    params["authority_archetype"] = select_random_element(
        authority_template.get("archetypes", ["Police Detective"])
    )
    params["authority_function"] = select_random_element(
        authority_template.get("functions", ["Provides official resources"])
    )

    # === 恐怖特定元素 ===
    # 根据主要恐怖类型选择合适的恐怖元素
    if params["primary_horror_subgenre"] in [
        "Supernatural Horror",
        "Gothic Horror",
        "Folk Horror",
    ]:
        params["specific_horror_elements"] = "; ".join(
            select_random_elements(
                config["horror_specific_elements"]["supernatural_phenomena"], count=3
            )
        )
    elif params["primary_horror_subgenre"] == "Psychological Horror":
        params["specific_horror_elements"] = "; ".join(
            select_random_elements(
                config["horror_specific_elements"]["psychological_horror_elements"],
                count=3,
            )
        )
    elif params["primary_horror_subgenre"] == "Body Horror":
        params["specific_horror_elements"] = "; ".join(
            select_random_elements(
                config["horror_specific_elements"]["body_horror_elements"], count=3
            )
        )
    else:
        # 混合不同类型的恐怖元素
        all_horror_elements = (
            config["horror_specific_elements"]["supernatural_phenomena"]
            + config["horror_specific_elements"]["psychological_horror_elements"]
        )
        params["specific_horror_elements"] = "; ".join(
            select_random_elements(all_horror_elements, count=3)
        )

    # === 情节结构 ===
    # 根据恐怖类型选择合适的情节弧线
    if params["primary_horror_subgenre"] == "Psychological Horror":
        chosen_arc = "psychological_breakdown_arc"
    elif params["primary_horror_subgenre"] in [
        "Serial Killer/Thriller",
        "Sci-Fi Horror",
    ]:
        chosen_arc = "investigation_horror_arc"
    elif params["primary_horror_subgenre"] in [
        "Zombie/Apocalyptic Horror",
        "Body Horror",
    ]:
        chosen_arc = "survival_horror_arc"
    else:
        chosen_arc = "classic_horror_arc"

    params["story_arc_name"] = chosen_arc.replace("_", " ").title()
    params["story_arc_beats"] = "; ".join(config["plot_structures"][chosen_arc])

    # === 高潮和结局 ===
    params["climax_scenario"] = select_random_element(config["climax_scenarios"])
    params["ending_type"] = select_random_element(config["ending_types"])

    # === 主题元素 ===
    params["primary_theme"] = select_random_element(config["thematic_elements"])
    params["secondary_themes"] = ", ".join(
        select_random_elements(config["thematic_elements"], count=2)
    )

    return params


def create_horror_prompt_template():
    """创建恐怖故事提示词模板 - English Version"""
    return """You are a master horror novelist, specializing in creating captivating multi-chapter horror audiobooks. You have deep understanding of all branches of horror literature and can expertly craft terrifying atmospheres and build spine-chilling storylines. Your goal is to generate a complete audiobook script that is exactly 120 minutes long.

The story should be divided into exactly {suggested_chapter_count} chapters. Each chapter should have a clear beginning, rising action, climax, and resolution/hook for the next chapter. Maintain consistent narrative style (third-person limited perspective, mainly focusing on {protagonist_name}, unless specifically needed for dramatic effect).

Generate a horror audiobook script based on the following parameters:

I. Core Story Blueprint:
*   Primary Horror Type: {primary_horror_subgenre}
*   Secondary Horror Elements: {secondary_horror_elements}
*   Overall Horror Atmosphere: {horror_atmosphere}
*   Primary Theme to Explore: {primary_theme}
*   Secondary Themes: {secondary_themes}
*   Selected Story Arc: {story_arc_name} - Follow these beats: {story_arc_beats}

II. World Setting and Environment:
*   Primary Location: {primary_location}
*   Time Period: {time_period}
*   Specific Horror Elements (throughout story): {specific_horror_elements}

III. Character Setup:

*   Protagonist - {protagonist_name}:
    *   Archetype: {protagonist_archetype}
    *   Professional Background: {protagonist_background}
    *   Psychological Trait: {protagonist_psychological_trait}
    *   Fatal Flaw: {protagonist_fatal_flaw}

*   Antagonist - {antagonist_name}:
    *   Type: {antagonist_type}
    *   Core Motivation: {antagonist_motivation}
    *   Primary Methods/Strategy: {antagonist_methods}

*   Key Supporting Character 1 - {ally1_name}:
    *   Role: {ally1_role}
    *   Archetype: {ally1_archetype}
    *   Story Function: {ally1_function}

*   Key Supporting Character 2 - {ally2_name}:
    *   Role: {ally2_role}
    *   Archetype: {ally2_archetype}
    *   Story Function: {ally2_function}

*   Key Supporting Character 3 - {vulnerable_name}:
    *   Role: {vulnerable_role}
    *   Archetype: {vulnerable_archetype}
    *   Story Function: {vulnerable_function}

*   Key Supporting Character 4 - {authority_name}:
    *   Role: {authority_role}
    *   Archetype: {authority_archetype}
    *   Story Function: {authority_function}

IV. Plot and Narrative Elements:
*   Climactic Confrontation Style: {climax_scenario}
*   Expected Ending Type: {ending_type}

V. Audiobook Specific Requirements:
*   Target Duration: Exactly {target_audio_length_minutes} minutes
*   Suggested Chapter Count: {suggested_chapter_count} chapters

Return a single, continuous plain text block.
This text must be directly readable by audio engines without any further modification.
The output should NOT contain any of the following:
- Breaks or elements that would interrupt smooth reading
- Descriptions or explanations of background music
- Any other miscellaneous, formatting, or meta-commentary
Ensure the entire output is this kind of uninterrupted plain text, optimized for clear audio rendering.
Make sure the complete story reaches the target audio length and deeply explores the provided parameters to create a rich and engaging narrative.
100% ensure the story is long enough to be a complete audiobook of exactly 120 minutes.
*   Ensure the total word count is at least 14,000 words for 120 minutes.
*   Ensure the total word count is at least 14,000 words for 120 minutes.
*   Ensure the total word count is at least 14,000 words for 120 minutes.
**IMPORTANT:** Use the specified character names throughout the story: Do not change or modify these names during story generation."""


def fill_prompt_template(template, params):
    """填充提示词模板"""
    prompt = template
    for key, value in params.items():
        placeholder = "{" + key + "}"
        prompt = prompt.replace(placeholder, str(value))
    return prompt


def remove_markdown_formatting(text):
    """移除markdown格式标记"""
    # 移除星号标记（粗体和斜体）
    text = re.sub(r"\*\*\*(.*?)\*\*\*", r"\1", text)  # 粗斜体
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # 粗体
    text = re.sub(r"\*(.*?)\*", r"\1", text)  # 斜体

    # 移除其他markdown标记
    text = re.sub(r"#{1,6}\s*", "", text)  # 标题
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)  # 代码块
    text = re.sub(r"`(.*?)`", r"\1", text)  # 内联代码
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)  # 链接

    return text


def get_next_story_index(directory):
    """获取下一个可用的故事索引号"""
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        return 1

    # 查找现有的.txt文件，排除.开头的文件（mac系统文件）
    existing_files = []
    for f in os.listdir(directory):
        if f.endswith(".txt") and not f.startswith("."):
            # 提取文件名中的数字部分
            match = re.match(r"(\d+)\.txt", f)
            if match:
                existing_files.append(int(match.group(1)))

    if not existing_files:
        return 1

    return max(existing_files) + 1


def save_to_file(content, filepath, quiet=False):
    """保存内容到文件"""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        if not quiet:
            print(f"Horror story parameters saved to: {filepath}")
        return True
    except Exception as e:
        print(f"Error saving file: {e}")
        return False


def print_story_preview(params, index):
    """打印故事参数预览"""
    print(f"Horror Story {index} Parameters Preview:")
    print(f"  Primary Type: {params['primary_horror_subgenre']}")
    print(f"  Primary Location: {params['primary_location']}")
    print(f"  Time Period: {params['time_period']}")
    print(f"  Horror Atmosphere: {params['horror_atmosphere']}")
    print(
        f"  Protagonist: {params['protagonist_name']} ({params['protagonist_archetype']})"
    )
    print(f"  Antagonist: {params['antagonist_name']} ({params['antagonist_type']})")
    print(f"  Main Ally: {params['ally1_name']} ({params['ally1_role']})")
    print(f"  Knowledge Guide: {params['ally2_name']} ({params['ally2_role']})")
    print(
        f"  Vulnerable Character: {params['vulnerable_name']} ({params['vulnerable_role']})"
    )
    print(
        f"  Authority Figure: {params['authority_name']} ({params['authority_role']})"
    )
    print(f"  Story Arc: {params['story_arc_name']}")
    print(f"  Primary Theme: {params['primary_theme']}")
    print(f"  Target Length: {params['target_audio_length_minutes']} minutes (FIXED)")
    print(f"  Suggested Chapters: {params['suggested_chapter_count']}")
    print(f"  Climax Scenario: {params['climax_scenario']}")
    print(f"  Ending Type: {params['ending_type']}")


def main():
    """主函数"""
    # 添加命令行参数解析
    parser = argparse.ArgumentParser(
        description="Generate horror story script parameters (English, 120 minutes fixed)",
        epilog="Supported horror types: Supernatural Horror, Psychological Horror, Gothic Horror, Cosmic Horror, Serial Killer/Thriller, Folk Horror, Body Horror, Sci-Fi Horror, Zombie/Apocalyptic Horror",
    )
    parser.add_argument(
        "-n",
        "--number",
        type=int,
        default=1,
        help="Number of stories to generate (default: 1)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()

    try:
        # 加载配置
        config = load_config()

        # 获取起始故事索引
        starting_index = get_next_story_index(args.output)

        print(
            f"Starting to generate {args.number} horror story parameters (English, 120 minutes fixed)..."
        )
        print(f"Output directory: {args.output}")
        print(f"Starting index: {starting_index}")

        # 生成多个故事
        success_count = 0
        for i in range(args.number):
            current_index = starting_index + i
            print(
                f"\nGenerating horror story {i+1}/{args.number} (index: {current_index})..."
            )

            try:
                # 生成故事参数
                params = generate_horror_story_parameters(config)

                # 创建并填充模板
                template = create_horror_prompt_template()
                filled_prompt = fill_prompt_template(template, params)

                # 移除markdown格式
                clean_prompt = remove_markdown_formatting(filled_prompt)

                # 设置输出路径
                output_path = os.path.join(args.output, f"{current_index}.txt")

                # 保存到文件
                if save_to_file(clean_prompt, output_path, quiet=(args.number > 1)):
                    success_count += 1

                # 打印当前故事的预览
                if args.number <= 5:  # 只在生成少量故事时显示详细预览
                    print_story_preview(params, current_index)
                else:
                    # 批量生成时只显示简要信息
                    print(f"  Type: {params['primary_horror_subgenre']}")
                    print(f"  Protagonist: {params['protagonist_name']}")
                    print(f"  Antagonist: {params['antagonist_name']}")

            except Exception as e:
                print(f"Error generating story {current_index}: {e}")
                continue

        # 打印生成结果摘要
        print(f"\n=== Batch Generation Complete ===")
        print(
            f"Successfully generated {success_count}/{args.number} horror story parameters"
        )
        if success_count > 0:
            print(
                f"File range: {starting_index}.txt to {starting_index + success_count - 1}.txt"
            )
        print(f"Save directory: {args.output}")
        print(f"All stories are configured for exactly 120 minutes duration in English")

        if success_count != args.number:
            print(f"Note: {args.number - success_count} stories failed to generate")

    except KeyboardInterrupt:
        print("\nUser interrupted program execution")
    except Exception as e:
        print(f"Error occurred during program execution: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
