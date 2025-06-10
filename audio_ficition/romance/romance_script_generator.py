#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爱情故事脚本参数生成器
Romance Story Script Parameter Generator

功能描述:
    自动生成浪漫爱情小说的故事参数，用于创建有声书脚本。
    基于配置文件随机组合各种元素（角色、设定、情节桥段等），
    生成完整的故事创作提示词模板。

依赖文件:
    - config.json: 配置文件，包含所有可选的故事元素
      必须放在脚本同一目录下

输入:
    - config.json: 故事元素配置文件
    - 命令行参数: 可选的生成数量

输出:
    - 固定目录: /Volumes/dhl/audio/romance/story_params/
    - 文件格式: {索引号}.txt (如: 1.txt, 2.txt, 3.txt...)
    - 内容: 完整的故事创作提示词，可直接用于AI生成故事

使用方法:
    1. 基本使用（生成1个故事参数）:
       python romance_script_generator.py

    2. 批量生成（生成N个故事参数）:
       python romance_script_generator.py -n 5
       python romance_script_generator.py --number 10

    3. 查看帮助:
       python romance_script_generator.py -h

注意事项:
    - 确保config.json文件存在且格式正确
    - 输出目录会自动创建（如果不存在）
    - 脚本会自动避免覆盖现有文件（从最大索引号+1开始）
    - 每个生成的故事参数包含完整的世界设定、角色配置、情节结构等

作者: 浪漫故事生成系统
版本: 1.0
"""

import json
import random
import os
import re
import argparse
import copy


def load_config(filepath="config.json"):
    """Load configuration file"""
    script_dir = os.path.dirname(os.path.realpath(__file__))
    full_path = os.path.join(script_dir, filepath)
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)


def select_random_element(element_list):
    """Randomly select an element from a list"""
    return copy.deepcopy(random.choice(element_list))


def select_random_elements(element_list, count=None):
    """Randomly select multiple elements from a list"""
    if count is None:
        count = random.randint(1, min(3, len(element_list)))
    return copy.deepcopy(random.sample(element_list, k=min(count, len(element_list))))


def generate_story_parameters(config):
    """Generate story parameters"""
    params = {}

    # === Protagonist and Love Interest Gender and Names ===
    protagonist_gender = random.choice(["male", "female"])
    if protagonist_gender == "female":
        params["protagonist_name"] = select_random_element(
            config["protagonist_names_female"]["options"]
        )
        params["love_interest_name"] = select_random_element(
            config["protagonist_names_male"]["options"]
        )
        params["protagonist_archetype"] = select_random_element(
            config["protagonist_archetypes_female"]["options"]
        )
        params["love_interest_archetype"] = select_random_element(
            config["protagonist_archetypes_male"]["options"]
        )
        params["protagonist_visual_keywords"] = select_random_element(
            config["character_visual_keywords"]["female"]
        )
        params["love_interest_visual_keywords"] = select_random_element(
            config["character_visual_keywords"]["male"]
        )
        params["rival_name"] = select_random_element(
            config["rival_names_female"]["options"]
        )
        params["best_friend_name"] = select_random_element(
            config["best_friend_names_female"]["options"]
        )
    else:
        params["protagonist_name"] = select_random_element(
            config["protagonist_names_male"]["options"]
        )
        params["love_interest_name"] = select_random_element(
            config["protagonist_names_female"]["options"]
        )
        params["protagonist_archetype"] = select_random_element(
            config["protagonist_archetypes_male"]["options"]
        )
        params["love_interest_archetype"] = select_random_element(
            config["protagonist_archetypes_female"]["options"]
        )
        params["protagonist_visual_keywords"] = select_random_element(
            config["character_visual_keywords"]["male"]
        )
        params["love_interest_visual_keywords"] = select_random_element(
            config["character_visual_keywords"]["female"]
        )
        params["rival_name"] = select_random_element(
            config["rival_names_male"]["options"]
        )
        params["best_friend_name"] = select_random_element(
            config["best_friend_names_male"]["options"]
        )

    # === Core Story Settings ===
    trope = select_random_element(config["romance_tropes_and_subgenres"]["options"])
    params["primary_romance_trope"] = trope["name"]
    params["trope_description"] = trope["description"]

    params["secondary_elements"] = ", ".join(
        select_random_elements(config["secondary_romance_elements"]["options"], 2)
    )

    params["setting_era"] = select_random_element(config["setting_details"]["eras"])
    params["setting_location"] = select_random_element(
        config["setting_details"]["locations"]
    )
    params["key_event"] = select_random_element(config["setting_details"]["events"])

    params["central_conflict"] = select_random_element(
        config["relationship_dynamics"]["central_conflict_catalysts"]
    )
    params["relationship_obstacles"] = "; ".join(
        select_random_elements(
            config["relationship_dynamics"]["relationship_obstacles"], 2
        )
    )

    # === Themes and Tone ===
    params["thematic_core"] = select_random_element(
        config["story_structure"]["thematic_cores"]
    )

    # === Character Elements ===
    params["protagonist_positive_traits"] = "; ".join(
        select_random_elements(config["character_traits"]["positive"], 2)
    )
    params["protagonist_flaws"] = "; ".join(
        select_random_elements(config["character_traits"]["flaws"], 2)
    )
    params["protagonist_initial_goal"] = select_random_element(
        config["character_goals_and_motivations"]["initial_goals"]
    )
    params["protagonist_core_motivation"] = select_random_element(
        config["character_goals_and_motivations"]["core_motivations_for_growth"]
    )
    params["love_interest_positive_traits"] = "; ".join(
        select_random_elements(config["character_traits"]["positive"], 2)
    )
    params["love_interest_flaws"] = "; ".join(
        select_random_elements(config["character_traits"]["flaws"], 2)
    )

    params["protagonist_love_interest_connection"] = select_random_element(
        config["love_interest_protagonist_connections"]["options"]
    )

    # === Supporting Characters ===
    # Best Friend
    params["best_friend_archetype"] = select_random_element(
        config["supporting_character_templates"]["best_friend"]["archetypes"]
    )
    params["best_friend_secret"] = select_random_element(
        config["supporting_character_templates"]["best_friend"]["secrets"]
    )

    # Rival/Antagonist
    params["rival_archetype"] = select_random_element(
        config["supporting_character_templates"]["rival_antagonist"]["archetypes"]
    )
    params["rival_motivation"] = select_random_element(
        config["supporting_character_templates"]["rival_antagonist"]["motivations"]
    )

    # === Story Structure ===
    chosen_arc_name = select_random_element(
        list(config["story_structure"]["story_arc_patterns"].keys())
    )
    params["story_arc_pattern_name"] = chosen_arc_name
    params["story_arc_beats_description"] = "; ".join(
        config["story_structure"]["story_arc_patterns"][chosen_arc_name]
    )

    # === Plot Elements ===
    params["plot_twist"] = select_random_element(config["plot_elements"]["plot_twists"])
    params["inciting_incident"] = select_random_element(
        config["plot_elements"]["inciting_incidents"]
    )
    params["climactic_moment"] = select_random_element(
        config["plot_elements"]["climactic_moments"]
    )
    params["ending_tone"] = select_random_element(
        config["story_structure"]["ending_tones"]
    )

    # Static elements
    params["target_audio_length_minutes"] = "90-120"
    params["suggested_chapter_count"] = "10-15"

    return params


def remove_markdown_formatting(text):
    """Remove markdown formatting marks"""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # Bold
    text = re.sub(r"\*(.*?)\*", r"\1", text)  # Italic
    text = re.sub(r"#{1,6}\s*", "", text)  # Headers
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)  # Links
    return text


def create_prompt_template():
    """Create prompt template for romance stories"""
    return """
You are a bestselling romance author, a master of creating emotionally charged, multi-chapter love stories for audiobooks. Your talent is crafting narratives filled with tension, passion, and unforgettable characters that resonate deeply with listeners.

Your task is to generate a complete, immersive script for a romance audiobook of approximately {target_audio_length_minutes} minutes. The story should be divided into {suggested_chapter_count} chapters, each with a compelling arc. The narrative should be in the third-person limited perspective, primarily switching between the viewpoints of {protagonist_name} and {love_interest_name} to maximize emotional insight and romantic tension.

Generate a romance audiobook script based on the following detailed parameters:

I. Core Romance Blueprint:
*   Primary Trope: {primary_romance_trope} ({trope_description})
*   Secondary Elements: {secondary_elements}
*   Thematic Core: {thematic_core}
*   Story Arc Pattern: {story_arc_pattern_name}
*   Arc Beats to Follow: {story_arc_beats_description}

II. Setting and Atmosphere:
*   Era: {setting_era}
*   Primary Location: {setting_location}
*   Key Event That Forces Interaction: {key_event}

III. Main Characters:

*   Protagonist: {protagonist_name}
    *   Archetype: {protagonist_archetype}
    *   Positive Traits: {protagonist_positive_traits}
    *   Flaws/Weaknesses: {protagonist_flaws}
    *   Initial Goal: {protagonist_initial_goal}
    *   Core Motivation for Change: {protagonist_core_motivation}
    *   Visual Keywords: {protagonist_visual_keywords}

*   Love Interest: {love_interest_name}
    *   Archetype: {love_interest_archetype}
    *   Positive Traits: {love_interest_positive_traits}
    *   Flaws/Weaknesses: {love_interest_flaws}
    *   Visual Keywords: {love_interest_visual_keywords}

IV. Relationship Dynamics:
*   Initial Connection/Hook: {protagonist_love_interest_connection}
*   Central Conflict Catalyst: {central_conflict}
*   Major Relationship Obstacles: {relationship_obstacles}

V. Supporting Characters:

*   The Best Friend: {best_friend_name}
    *   Archetype: {best_friend_archetype}
    *   Secret Subplot: {best_friend_secret}

*   The Rival/Antagonist: {rival_name}
    *   Archetype: {rival_archetype}
    *   Motivation: {rival_motivation}

VI. Plot and Narrative Structure:
*   Inciting Incident: {inciting_incident}
*   Major Plot Twist: {plot_twist}
*   Climactic Moment Style: {climactic_moment}
*   Ending Tone: {ending_tone}

VII. Audiobook Script Requirements:
*   Introduction: Start directly with the inciting incident. Create a compelling hook that immediately draws the listener into the protagonist's world and the story's central conflict.
*   Format: Generate a single, continuous block of plain text. The entire output must be directly readable by a text-to-speech engine.
*   Exclusions: Do not include chapter headings (e.g., "Chapter 1"), scene breaks, sound effect cues, or any meta-commentary. The narrative flow must be uninterrupted.
*   Length and Depth: The final story must be substantial, aiming for a word count that would equate to a 90-120 minute audiobook (approximately 15,000 - 20,000 words). Deeply explore the character arcs, emotional development, and romantic tension outlined in the parameters.
*   IMPORTANT: Use the specified character names ({protagonist_name}, {love_interest_name}, {best_friend_name}, {rival_name}) consistently throughout the story. Do not change them.
Make 100% sure the story is long enough to be a full audiobook, which is at least 100 minutes long.
The total word count should be at least 100,000 words.
**IMPORTANT:** Use the specified role names throughout the story: Do not change or modify these names during the story generation.

"""


def fill_prompt_template(template, params):
    """Fill prompt template"""
    prompt = template
    for key, value in params.items():
        placeholder = "{" + key + "}"
        prompt = prompt.replace(placeholder, str(value))
    return prompt


def get_next_story_index(directory):
    """Get the next available story index"""
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        return 1

    existing_files = [
        f
        for f in os.listdir(directory)
        if f.startswith("story_")
        and f.endswith(".txt")
        and f.split("_")[1].split(".")[0].isdigit()
    ]
    if not existing_files:
        return 1

    existing_numbers = [int(f.split("_")[1].split(".")[0]) for f in existing_files]
    return max(existing_numbers) + 1


def save_to_file(content, filepath, quiet=False):
    """Save content to file"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    if not quiet:
        print(f"故事参数已保存到: {filepath}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="生成爱情故事脚本参数")
    parser.add_argument(
        "-n", "--number", type=int, default=1, help="要生成的故事数量 (默认: 1)"
    )
    args = parser.parse_args()

    try:
        config = load_config()
        print("爱情故事配置文件加载成功")

        story_directory = "/Volumes/dhl/audio/romance/story_params"
        starting_index = get_next_story_index(story_directory)

        print(f"开始生成 {args.number} 个故事参数...")

        for i in range(args.number):
            current_index = starting_index + i
            print(f"\n正在生成第 {i+1}/{args.number} 个故事 (索引: {current_index})...")

            params = generate_story_parameters(config)
            template = create_prompt_template()
            filled_prompt = fill_prompt_template(template, params)
            clean_prompt = remove_markdown_formatting(filled_prompt)

            output_path = f"{story_directory}/story_{current_index}.txt"
            save_to_file(clean_prompt, output_path, quiet=(args.number > 1))

            print(f"故事 {current_index} 参数预览:")
            print(f"  主要类型: {params['primary_romance_trope']}")
            print(
                f"  主角: {params['protagonist_name']} ({params['protagonist_archetype']})"
            )
            print(
                f"  恋爱对象: {params['love_interest_name']} ({params['love_interest_archetype']})"
            )
            print(f"  设定: {params['setting_location']}, {params['setting_era']}")
            print(f"  核心冲突: {params['central_conflict']}")
            print(f"  故事弧线: {params['story_arc_pattern_name']}")
            print(f"  结局基调: {params['ending_tone']}")

        print(f"\n=== 批量生成完成 ===")
        print(f"总共生成了 {args.number} 个故事参数")
        print(
            f"文件保存范围: story_{starting_index}.txt 到 story_{starting_index + args.number - 1}.txt"
        )
        print(f"保存目录: {story_directory}")

    except FileNotFoundError:
        print("错误: 未找到配置文件 'config.json'")
        print("请确保 config.json 文件与脚本在同一目录中")
    except Exception as e:
        print(f"发生错误: {str(e)}")


if __name__ == "__main__":
    main()
