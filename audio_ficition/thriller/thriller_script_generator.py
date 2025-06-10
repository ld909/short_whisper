#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
惊悚故事脚本参数生成器
Thriller Story Script Parameter Generator

功能描述:
    自动生成惊悚小说的故事参数，用于创建有声书脚本。
    基于配置文件随机组合各种元素（角色、设定、情节元素等），
    生成完整的故事创作提示词模板。

支持的惊悚子类型:
    - Psychological Thriller (心理惊悚)
    - Crime Thriller (犯罪惊悚)
    - Action/Adventure Thriller (动作/冒险惊悚)
    - Legal Thriller (法律惊悚)
    - Domestic Noir/Domestic Suspense (家庭惊悚)
    - Spy Thriller/Espionage Thriller (间谍惊悚)
    - Political Thriller (政治惊悚)
    - Techno-Thriller (科技惊悚)
    - Medical Thriller (医疗惊悚)
    - Supernatural Thriller/Horror Thriller (超自然/恐怖惊悚)

依赖文件:
    - config.json: 配置文件，包含所有可选的故事元素
      必须放在脚本同一目录下

输入:
    - config.json: 故事元素配置文件
    - 命令行参数: 可选的生成数量

输出:
    - 固定目录: /Volumes/dhl/audio/thriller/story_params/
    - 文件格式: thriller_{索引号}.txt (如: thriller_1.txt, thriller_2.txt...)
    - 内容: 完整的故事创作提示词，可直接用于AI生成故事

使用方法:
    1. 基本使用（生成1个故事参数）:
       python thriller_script_generator.py

    2. 批量生成（生成N个故事参数）:
       python thriller_script_generator.py -n 5
       python thriller_script_generator.py --number 10

    3. 查看帮助:
       python thriller_script_generator.py -h

注意事项:
    - 确保config.json文件存在且格式正确
    - 输出目录会自动创建（如果不存在）
    - 脚本会自动避免覆盖现有文件（从最大索引号+1开始）
    - 每个生成的故事参数包含完整的世界设定、角色配置、情节结构等

作者: 惊悚故事生成系统
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
    """Generate thriller story parameters"""
    params = {}

    # === Protagonist Selection ===
    protagonist_gender = random.choice(["male", "female"])
    if protagonist_gender == "female":
        params["protagonist_name"] = select_random_element(
            config["protagonist_names_female"]["options"]
        )
        params["partner_name"] = select_random_element(
            config["supporting_character_names"]["partners"]
        )
    else:
        params["protagonist_name"] = select_random_element(
            config["protagonist_names_male"]["options"]
        )
        params["partner_name"] = select_random_element(
            config["supporting_character_names"]["partners"]
        )

    # === Core Thriller Elements ===
    subgenre = select_random_element(config["thriller_subgenres"]["options"])
    params["primary_subgenre"] = subgenre["name"]
    params["subgenre_description"] = subgenre["description"]

    params["secondary_elements"] = ", ".join(
        select_random_elements(config["secondary_thriller_elements"]["options"], 3)
    )

    # === Setting and Atmosphere ===
    params["primary_location"] = select_random_element(
        config["setting_details"]["locations"]
    )
    params["time_period"] = select_random_element(
        config["setting_details"]["time_periods"]
    )
    params["triggering_event"] = select_random_element(
        config["setting_details"]["triggering_events"]
    )

    # === Character Elements ===
    params["protagonist_archetype"] = select_random_element(
        config["character_archetypes"]["protagonists"]
    )
    params["antagonist_name"] = select_random_element(
        config["supporting_character_names"]["antagonists"]
    )
    params["antagonist_archetype"] = select_random_element(
        config["character_archetypes"]["antagonists"]
    )
    params["victim_name"] = select_random_element(
        config["supporting_character_names"]["victims"]
    )

    # === Psychological Elements ===
    params["mental_condition"] = select_random_element(
        config["psychological_elements"]["mental_conditions"]
    )
    params["manipulation_tactics"] = "; ".join(
        select_random_elements(
            config["psychological_elements"]["manipulation_tactics"], 2
        )
    )

    # === Crime and Investigation ===
    params["crime_type"] = select_random_element(config["crime_types"]["options"])
    params["investigation_methods"] = "; ".join(
        select_random_elements(config["investigation_methods"]["options"], 3)
    )

    # === Plot Structure ===
    params["red_herring"] = select_random_element(
        config["plot_devices"]["red_herrings"]
    )
    params["plot_twist"] = select_random_element(config["plot_devices"]["plot_twists"])
    params["climax_scenario"] = select_random_element(
        config["plot_devices"]["climax_scenarios"]
    )

    # === Theme ===
    params["core_theme"] = select_random_element(config["themes"]["core_themes"])

    # === Technical Elements ===
    params["primary_weapon"] = select_random_element(
        config["technical_elements"]["weapons"]
    )
    params["key_technology"] = select_random_element(
        config["technical_elements"]["technology"]
    )
    params["escape_vehicle"] = select_random_element(
        config["technical_elements"]["vehicles"]
    )

    # Static elements
    params["target_audio_length_minutes"] = "120"

    return params


def remove_markdown_formatting(text):
    """Remove markdown formatting marks"""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # Bold
    text = re.sub(r"\*(.*?)\*", r"\1", text)  # Italic
    text = re.sub(r"#{1,6}\s*", "", text)  # Headers
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)  # Links
    return text


def create_prompt_template():
    """Create prompt template for thriller stories"""
    return """
You are a master thriller writer, an expert in crafting heart-pounding, suspenseful narratives that keep readers on the edge of their seats. Your specialty is creating multi-layered plots filled with tension, unexpected twists, and complex characters that drive compelling audiobook experiences.

Your task is to generate a complete, immersive script for a thriller audiobook of approximately {target_audio_length_minutes} minutes. The narrative should primarily follow {protagonist_name}, with strategic perspective shifts to heighten tension and reveal crucial information at the perfect moments.

Generate a thriller audiobook script based on the following detailed parameters:

I. Core Thriller Framework:
*   Primary Subgenre: {primary_subgenre}
*   Subgenre Focus: {subgenre_description}
*   Secondary Elements: {secondary_elements}
*   Central Theme: {core_theme}

II. Setting and Atmosphere:
*   Time Period: {time_period}
*   Primary Location: {primary_location}
*   Triggering Event: {triggering_event}

III. Main Characters:

*   Protagonist: {protagonist_name}
    *   Character Type: {protagonist_archetype}
    *   Psychological Element: {mental_condition}

*   Primary Antagonist: {antagonist_name}
    *   Character Type: {antagonist_archetype}
    
*   Key Partner/Ally: {partner_name}

*   Victim/Target: {victim_name}

IV. Crime and Investigation Elements:
*   Central Crime: {crime_type}
*   Investigation Methods: {investigation_methods}
*   Manipulation Tactics Used: {manipulation_tactics}

V. Plot Structure and Devices:
*   Red Herring: {red_herring}
*   Major Plot Twist: {plot_twist}
*   Climactic Scenario: {climax_scenario}

VI. Technical Elements:
*   Primary Weapon: {primary_weapon}
*   Key Technology: {key_technology}
*   Escape/Chase Vehicle: {escape_vehicle}

VII. Audiobook Script Requirements:
*   Opening: Begin with a compelling hook that immediately establishes the threat or mystery. Create an atmosphere of tension and unease from the very first sentence.
*   Format: Generate a single, continuous block of plain text. The entire output must be directly readable by a text-to-speech engine without any formatting.
*   Exclusions: Do not include chapter headings (e.g., "Chapter 1"), scene breaks, sound effect cues, or any meta-commentary. The narrative flow must be seamless and uninterrupted.
*   Length and Depth: The final story must be substantial, aiming for a word count that would equate to a at least 100 minutes audiobook (approximately 15,000 - 20,000 words). Develop complex plot layers, escalating tension, and detailed character psychology.
*   Pacing: Maintain thriller pacing with alternating moments of high tension and brief respites that allow for character development and plot advancement.
*   Suspense Techniques: Use cliffhangers, red herrings, foreshadowing, and revelations to maintain constant reader engagement.
*   IMPORTANT: Use the specified character names ({protagonist_name}, {antagonist_name}, {partner_name}, {victim_name}) consistently throughout the story. Do not change them.

VIII. Thriller-Specific Elements to Include:
*   Establish immediate danger or threat
*   Create mounting tension and paranoia
*   Include at least one major misdirection
*   Build to multiple crisis points
*   Reveal the truth through escalating revelations
*   Conclude with a satisfying resolution that ties up all plot threads
*   Maintain psychological realism even in extreme situations
*   Use environmental details to enhance atmosphere and tension

The story should exemplify the best elements of the {primary_subgenre} genre while incorporating the specified technical and psychological elements in a natural, plot-driven way.

Make 100% sure the story is long enough to be a full audiobook, which is at least 100 minutes long.
The total word count should be at least 100,000 words.
**IMPORTANT:** Use the specified role names throughout the story: Do not change or modify these names during the story generation.
"""


def fill_prompt_template(template, params):
    """Fill prompt template with generated parameters"""
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

    # 排除mac产生的点开头文件
    existing_files = [
        f
        for f in os.listdir(directory)
        if not f.startswith(".")
        and f.startswith("thriller_")
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
        print(f"惊悚故事参数已保存到: {filepath}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="生成惊悚故事脚本参数")
    parser.add_argument(
        "-n", "--number", type=int, default=1, help="要生成的故事数量 (默认: 1)"
    )
    args = parser.parse_args()

    try:
        config = load_config()
        print("惊悚故事配置文件加载成功")

        story_directory = "/Volumes/dhl/audio/thriller/story_params"
        starting_index = get_next_story_index(story_directory)

        print(f"开始生成 {args.number} 个惊悚故事参数...")

        for i in range(args.number):
            current_index = starting_index + i
            print(f"\n正在生成第 {i+1}/{args.number} 个故事 (索引: {current_index})...")

            params = generate_story_parameters(config)
            template = create_prompt_template()
            filled_prompt = fill_prompt_template(template, params)
            clean_prompt = remove_markdown_formatting(filled_prompt)

            output_path = f"{story_directory}/thriller_{current_index}.txt"
            save_to_file(clean_prompt, output_path, quiet=(args.number > 1))

            print(f"故事 {current_index} 参数预览:")
            print(f"  主要类型: {params['primary_subgenre']}")
            print(f"  主角: {params['protagonist_name']}")
            print(f"  主角类型: {params['protagonist_archetype']}")
            print(f"  反派: {params['antagonist_name']}")
            print(f"  反派类型: {params['antagonist_archetype']}")
            print(f"  设定: {params['primary_location']}")
            print(f"  时期: {params['time_period']}")
            print(f"  核心犯罪: {params['crime_type']}")
            print(f"  触发事件: {params['triggering_event']}")
            print(f"  重大转折: {params['plot_twist']}")
            print(f"  核心主题: {params['core_theme']}")
            print(f"  高潮场景: {params['climax_scenario']}")

        print(f"\n=== 批量生成完成 ===")
        print(f"总共生成了 {args.number} 个惊悚故事参数")
        print(
            f"文件保存范围: thriller_{starting_index}.txt 到 thriller_{starting_index + args.number - 1}.txt"
        )
        print(f"保存目录: {story_directory}")

    except FileNotFoundError:
        print("错误: 未找到配置文件 'config.json'")
        print("请确保 config.json 文件与脚本在同一目录中")
    except Exception as e:
        print(f"发生错误: {str(e)}")


if __name__ == "__main__":
    main()
