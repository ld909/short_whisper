#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Thriller Story Script Parameter Generator
惊悚故事脚本参数生成器

功能描述:
    自动生成惊悚小说的故事参数，用于创建有声书脚本。
    基于配置文件随机组合各种元素（角色、情节设定、悬念机制等），
    生成完整的故事创作提示词模板。

依赖文件:
    - config.json: 配置文件，包含所有可选的故事元素
      必须放在脚本同一目录下

输入:
    - config.json: 故事元素配置文件
    - 命令行参数: 可选的生成数量

输出:
    - 固定目录: /Users/donghaoliu/Documents/audio/story_param/thriller/
    - 文件格式: {索引号}.txt (如: 1.txt, 2.txt, 3.txt...)
    - 内容: 完整的故事创作提示词，可直接用于AI生成故事

使用方法:
    1. 基本使用（生成1个故事参数）:
       python thriller_script_generator.py

    2. 批量生成（生成N个故事参数）:
       python thriller_script_generator.py -n 5
       python thriller_script_generator.py --number 10

    3. 查看帮助:
       python thriller_script_generator.py -h

支持的惊悚子类型:
    - Psychological Thriller (心理惊悚)
    - Legal Thriller (法律惊悚)
    - Action/Adventure Thriller (动作/冒险惊悚)
    - Spy/Espionage Thriller (间谍惊悚)
    - Crime Thriller (犯罪惊悚)
    - Techno-Thriller (科技惊悚)

注意事项:
    - 确保config.json文件存在且格式正确
    - 输出目录会自动创建（如果不存在）
    - 脚本会自动避免覆盖现有文件（从最大索引号+1开始）
    - 每个生成的故事参数包含完整的悬念设定、角色配置、情节结构等

作者: 惊悚故事生成系统
版本: 1.0
"""

import json
import random
import os
import re
import argparse


def load_config(filepath="config.json"):
    """Load configuration file"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def select_random_element(element_list):
    """Randomly select an element from a list"""
    return random.choice(element_list)


def select_random_elements(element_list, count=None):
    """Randomly select multiple elements from a list"""
    if count is None:
        count = random.randint(1, min(3, len(element_list)))
    return random.sample(element_list, k=min(count, len(element_list)))


def select_random_name(name_config):
    """Select a random name from name configuration"""
    return select_random_element(name_config["options"])


def generate_story_parameters(config):
    """Generate story parameters"""
    params = {}

    # === Story Settings ===
    target_length = select_random_element(
        config["story_settings"]["target_audio_length_minutes"]
    )
    params["target_audio_length_minutes_min"] = target_length[0]
    params["target_audio_length_minutes_max"] = target_length[1]
    params["suggested_chapter_count"] = max(
        8, target_length[1] // 12
    )  # About 12 minutes per chapter

    params["primary_thriller_subgenre"] = select_random_element(
        config["story_settings"]["primary_thriller_subgenres"]
    )
    params["secondary_elements"] = ", ".join(
        select_random_elements(
            config["story_settings"]["secondary_thriller_elements"], 2
        )
    )
    params["setting_type"] = select_random_element(
        config["story_settings"]["setting_types"]
    )

    # Suspense mechanisms
    params["primary_suspense_mechanism"] = select_random_element(
        config["story_settings"]["suspense_mechanisms"]
    )
    params["pacing_technique"] = select_random_element(
        config["story_settings"]["pacing_techniques"]
    )
    params["information_control_strategy"] = select_random_element(
        config["story_settings"]["information_control_strategies"]
    )

    # === Themes and Tone ===
    params["themes"] = select_random_element(config["thematic_cores_catalogue"])

    # Generate tone and atmosphere
    params["overall_tone"] = select_random_element(
        config["additional_story_elements"]["tone_options"]
    )
    params["atmosphere_keywords"] = select_random_element(
        config["additional_story_elements"]["atmosphere_options"]
    )

    # Core hooks and conflicts
    params["core_concept_hook"] = select_random_element(
        config["additional_story_elements"]["core_concept_hooks"]
    )
    params["central_mystery_question"] = select_random_element(
        config["additional_story_elements"]["central_mystery_questions"]
    )

    # === Character Names ===
    params["protagonist_name"] = select_random_name(config["protagonist_names"])
    params["antagonist_name"] = select_random_name(config["antagonist_names"])
    params["ally_name"] = select_random_name(config["ally_names"])
    params["authority_figure_name"] = select_random_name(
        config["authority_figure_names"]
    )
    params["victim_witness_name"] = select_random_name(config["victim_witness_names"])

    # === Protagonist Elements ===
    params["protagonist_archetype"] = select_random_element(
        config["protagonist_elements"]["archetypes"]
    )
    params["protagonist_profession"] = select_random_element(
        config["protagonist_elements"]["professions"]
    )
    params["protagonist_skills"] = "; ".join(
        select_random_elements(config["protagonist_elements"]["skills"], 2)
    )
    params["protagonist_vulnerabilities"] = "; ".join(
        select_random_elements(config["protagonist_elements"]["vulnerabilities"], 2)
    )
    params["protagonist_initial_goal"] = select_random_element(
        config["protagonist_elements"]["initial_goals"]
    )
    params["protagonist_personal_stakes"] = select_random_element(
        config["protagonist_elements"]["personal_stakes"]
    )
    params["protagonist_psychological_state"] = select_random_element(
        config["additional_story_elements"]["protagonist_psychological_states"]
    )
    params["protagonist_backstory_secret"] = select_random_element(
        config["additional_story_elements"]["protagonist_backstory_secrets"]
    )

    # === Antagonist Elements ===
    params["antagonist_archetype"] = select_random_element(
        config["antagonist_elements"]["archetypes"]
    )
    params["antagonist_motivation"] = select_random_element(
        config["antagonist_elements"]["motivations"]
    )
    params["antagonist_methods"] = select_random_element(
        config["antagonist_elements"]["methods"]
    )
    params["antagonist_intelligence_level"] = select_random_element(
        config["antagonist_elements"]["intelligence_levels"]
    )
    params["antagonist_connection_to_protagonist"] = select_random_element(
        config["additional_story_elements"]["antagonist_protagonist_connections"]
    )
    params["antagonist_signature_trait"] = select_random_element(
        config["additional_story_elements"]["antagonist_signature_traits"]
    )

    # === Supporting Characters ===
    # Ally character
    ally_template = next(
        item
        for item in config["supporting_character_templates"]
        if item["role"] == "Ally/Partner"
    )
    params["supporting_char1_role"] = "Ally/Partner"
    params["supporting_char1_archetype"] = select_random_element(
        ally_template["archetypes"]
    )
    params["supporting_char1_expertise"] = select_random_element(
        config["additional_story_elements"]["supporting_character_expertise"]
    )
    params["supporting_char1_reliability"] = select_random_element(
        config["additional_story_elements"]["supporting_character_reliability"]
    )
    params["supporting_char1_hidden_agenda"] = select_random_element(
        config["additional_story_elements"]["supporting_character_hidden_agendas"]
    )

    # Authority Figure character
    authority_template = next(
        item
        for item in config["supporting_character_templates"]
        if item["role"] == "Authority Figure"
    )
    params["supporting_char2_role"] = "Authority Figure"
    params["supporting_char2_archetype"] = select_random_element(
        authority_template["archetypes"]
    )
    params["supporting_char2_expertise"] = select_random_element(
        config["additional_story_elements"]["supporting_character_expertise"]
    )
    params["supporting_char2_reliability"] = select_random_element(
        config["additional_story_elements"]["supporting_character_reliability"]
    )
    params["supporting_char2_hidden_agenda"] = select_random_element(
        config["additional_story_elements"]["supporting_character_hidden_agendas"]
    )

    # Victim/Witness character
    victim_template = next(
        item
        for item in config["supporting_character_templates"]
        if item["role"] == "Victim/Witness"
    )
    params["supporting_char3_role"] = "Victim/Witness"
    params["supporting_char3_archetype"] = select_random_element(
        victim_template["archetypes"]
    )
    params["supporting_char3_expertise"] = select_random_element(
        config["additional_story_elements"]["supporting_character_expertise"]
    )
    params["supporting_char3_reliability"] = select_random_element(
        config["additional_story_elements"]["supporting_character_reliability"]
    )
    params["supporting_char3_hidden_agenda"] = select_random_element(
        config["additional_story_elements"]["supporting_character_hidden_agendas"]
    )
    params["victim_witness_connection"] = select_random_element(
        victim_template["connection_to_case"]
    )

    # === Story Structure ===
    chosen_arc_name = select_random_element(list(config["story_arc_patterns"].keys()))
    params["story_arc_pattern_name"] = chosen_arc_name.replace("_", " ").title()
    params["story_arc_beats_description"] = "; ".join(
        config["story_arc_patterns"][chosen_arc_name]
    )

    # === Plot Elements ===
    params["inciting_incident"] = select_random_element(
        config["additional_story_elements"]["inciting_incidents"]
    )
    params["first_twist"] = select_random_element(config["plot_twist_catalogue"])
    remaining_twists = config["plot_twist_catalogue"].copy()
    remaining_twists.remove(params["first_twist"])
    params["second_twist"] = select_random_element(remaining_twists)

    params["red_herring_1"] = select_random_element(
        config["additional_story_elements"]["red_herrings"]
    )
    remaining_herrings = config["additional_story_elements"]["red_herrings"].copy()
    remaining_herrings.remove(params["red_herring_1"])
    params["red_herring_2"] = select_random_element(remaining_herrings)

    params["climax_confrontation_style"] = select_random_element(
        config["climax_confrontation_styles"]
    )
    params["resolution_type"] = select_random_element(
        config["additional_story_elements"]["resolution_types"]
    )

    # === Setting and Environment ===
    params["primary_location"] = select_random_element(
        config["additional_story_elements"]["primary_locations"]
    )
    params["secondary_location"] = select_random_element(
        config["additional_story_elements"]["secondary_locations"]
    )
    params["time_period"] = select_random_element(
        config["additional_story_elements"]["time_periods"]
    )
    params["environmental_pressure"] = select_random_element(
        config["additional_story_elements"]["environmental_pressures"]
    )

    # === Investigation/Revelation Elements ===
    params["clue_discovery_method"] = select_random_element(
        config["additional_story_elements"]["clue_discovery_methods"]
    )
    params["evidence_type"] = select_random_element(
        config["additional_story_elements"]["evidence_types"]
    )
    params["revelation_trigger"] = select_random_element(
        config["additional_story_elements"]["revelation_triggers"]
    )

    # === Genre-Specific Elements (based on subgenre) ===
    subgenre = params["primary_thriller_subgenre"]
    if "Psychological" in subgenre:
        params["psychological_element"] = select_random_element(
            config["subgenre_specific_elements"]["psychological_thriller"]
        )
    elif "Legal" in subgenre:
        params["legal_element"] = select_random_element(
            config["subgenre_specific_elements"]["legal_thriller"]
        )
    elif "Action" in subgenre or "Adventure" in subgenre:
        params["action_element"] = select_random_element(
            config["subgenre_specific_elements"]["action_thriller"]
        )
    elif "Spy" in subgenre or "Espionage" in subgenre:
        params["espionage_element"] = select_random_element(
            config["subgenre_specific_elements"]["spy_thriller"]
        )
    elif "Crime" in subgenre:
        params["crime_element"] = select_random_element(
            config["subgenre_specific_elements"]["crime_thriller"]
        )
    elif "Techno" in subgenre:
        params["techno_element"] = select_random_element(
            config["subgenre_specific_elements"]["techno_thriller"]
        )

    return params


def remove_markdown_formatting(text):
    """Remove markdown formatting marks"""
    # Remove asterisk marks (bold and italic)
    text = re.sub(r"\*\*\*(.*?)\*\*\*", r"\1", text)  # Bold italic
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # Bold
    text = re.sub(r"\*(.*?)\*", r"\1", text)  # Italic

    # Remove other markdown marks
    text = re.sub(r"#{1,6}\s*", "", text)  # Headers
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)  # Code blocks
    text = re.sub(r"`(.*?)`", r"\1", text)  # Inline code
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)  # Links

    return text


def create_prompt_template():
    """Create prompt template"""
    return """
You are a master of thriller storytelling, a ten-time Nobel laureate with unparalleled expertise in creating gripping, suspenseful narratives. Your mission is to craft a complete audiobook script of at least 100 minutes in length, expertly divided into approximately {suggested_chapter_count} chapters. Each chapter must deliver relentless tension, compelling character development, and masterful pacing that keeps listeners on the edge of their seats.

The narrative should employ third-person limited perspective, primarily focused on {protagonist_name}, with strategic shifts for maximum dramatic impact. Every chapter must end with a compelling hook that drives the listener to continue.

Generate a thriller audiobook script based on the following parameters:

I. Core Thriller Blueprint:
*   Primary Subgenre: {primary_thriller_subgenre}
*   Secondary Thriller Elements: {secondary_elements}
*   Core Concept Hook: {core_concept_hook}
*   Central Mystery Question: {central_mystery_question}
*   Primary Suspense Mechanism: {primary_suspense_mechanism}
*   Information Control Strategy: {information_control_strategy}
*   Pacing Technique: {pacing_technique}
*   Thematic Core: {themes}
*   Overall Tone: {overall_tone}
*   Atmospheric Keywords: {atmosphere_keywords}

II. Setting and Environment:
*   Setting Type: {setting_type}
*   Time Period: {time_period}
*   Primary Location: {primary_location}
*   Secondary Location: {secondary_location}
*   Environmental Pressure: {environmental_pressure}
*   Story Arc Pattern: {story_arc_pattern_name}
*   Arc Development Beats: {story_arc_beats_description}

III. Characters:

*   Protagonist - {protagonist_name}:
    *   Archetype: {protagonist_archetype}
    *   Profession: {protagonist_profession}
    *   Core Skills: {protagonist_skills}
    *   Vulnerabilities: {protagonist_vulnerabilities}
    *   Initial Goal: {protagonist_initial_goal}
    *   Personal Stakes: {protagonist_personal_stakes}
    *   Psychological State: {protagonist_psychological_state}
    *   Hidden Backstory: {protagonist_backstory_secret}

*   Antagonist - {antagonist_name}:
    *   Archetype: {antagonist_archetype}
    *   Core Motivation: {antagonist_motivation}
    *   Methods of Operation: {antagonist_methods}
    *   Intelligence Level: {antagonist_intelligence_level}
    *   Connection to Protagonist: {antagonist_connection_to_protagonist}
    *   Signature Trait: {antagonist_signature_trait}

*   Key Supporting Character 1 - {ally_name}:
    *   Role: {supporting_char1_role}
    *   Archetype: {supporting_char1_archetype}
    *   Area of Expertise: {supporting_char1_expertise}
    *   Reliability Level: {supporting_char1_reliability}
    *   Hidden Agenda: {supporting_char1_hidden_agenda}

*   Key Supporting Character 2 - {authority_figure_name}:
    *   Role: {supporting_char2_role}
    *   Archetype: {supporting_char2_archetype}
    *   Area of Expertise: {supporting_char2_expertise}
    *   Reliability Level: {supporting_char2_reliability}
    *   Hidden Agenda: {supporting_char2_hidden_agenda}

*   Key Supporting Character 3 - {victim_witness_name}:
    *   Role: {supporting_char3_role}
    *   Archetype: {supporting_char3_archetype}
    *   Area of Expertise: {supporting_char3_expertise}
    *   Reliability Level: {supporting_char3_reliability}
    *   Hidden Agenda: {supporting_char3_hidden_agenda}
    *   Connection to Case: {victim_witness_connection}

IV. Plot and Investigation Elements:
*   Inciting Incident: {inciting_incident}
*   Primary Clue Discovery Method: {clue_discovery_method}
*   Key Evidence Type: {evidence_type}
*   Revelation Trigger: {revelation_trigger}
*   Red Herring 1: {red_herring_1}
*   Red Herring 2: {red_herring_2}
*   First Major Twist: {first_twist}
*   Second Major Twist: {second_twist}
*   Climax Confrontation Style: {climax_confrontation_style}
*   Resolution Type: {resolution_type}

V. Audiobook Specific Requirements:
*   Create an immediate hook in the opening 30 seconds that establishes the central tension
*   Maintain relentless pacing with strategic moments of breathing room for character development
*   Build suspense through careful revelation of information and strategic misdirection
*   Each chapter must end with a compelling cliffhanger or revelation
*   Incorporate multiple layers of mystery that resolve at different points in the narrative
*   Use vivid, cinematic descriptions that enhance the audio experience
*   Dialogue must feel natural and authentic while advancing plot and character development

Return only a single, continuous block of plain text optimized for audio narration.
This text must be directly readable by an audio engine without any modifications.
The output should exclude:
- Any stage directions or production notes
- Background music descriptions
- Technical formatting or meta-comments
- Chapter break announcements (transitions should be seamless)

Ensure the complete story reaches the target audio length of 100 minutes and maintains thriller pacing throughout.
The story must contain at least 150,000 words to ensure proper audiobook length.


**CRITICAL:** Maintain character name consistency throughout. Use the specified names exactly as provided: {protagonist_name}, {antagonist_name}, {ally_name}, {authority_figure_name}, {victim_witness_name}.
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
        if f.endswith(".txt") and f[:-4].isdigit() and not f.startswith(".")
    ]
    if not existing_files:
        return 1

    existing_numbers = [int(f[:-4]) for f in existing_files]
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
    # Add command line argument parsing
    parser = argparse.ArgumentParser(description="生成惊悚故事脚本参数")
    parser.add_argument(
        "-n", "--number", type=int, default=1, help="要生成的故事数量 (默认: 1)"
    )
    args = parser.parse_args()

    try:
        # Load configuration
        config = load_config()
        print("配置文件加载成功")

        # Get starting story index
        story_directory = "/Users/donghaoliu/Documents/audio/story_param/thriller"
        starting_index = get_next_story_index(story_directory)

        print(f"开始生成 {args.number} 个惊悚故事参数...")

        # Generate multiple stories
        for i in range(args.number):
            current_index = starting_index + i
            print(f"\n正在生成第 {i+1}/{args.number} 个故事 (索引: {current_index})...")

            # Generate story parameters
            params = generate_story_parameters(config)

            # Create and fill template
            template = create_prompt_template()
            filled_prompt = fill_prompt_template(template, params)

            # Remove markdown formatting
            clean_prompt = remove_markdown_formatting(filled_prompt)

            # Set output path
            output_path = f"{story_directory}/{current_index}.txt"

            # Save to file
            save_to_file(clean_prompt, output_path, quiet=(args.number > 1))

            # Print preview for current story
            print(f"故事 {current_index} 参数预览:")
            print(f"  惊悚子类型: {params['primary_thriller_subgenre']}")
            print(f"  设定类型: {params['setting_type']}")
            print(
                f"  主角: {params['protagonist_name']} ({params['protagonist_archetype']})"
            )
            print(
                f"  反派: {params['antagonist_name']} ({params['antagonist_archetype']})"
            )
            print(f"  盟友: {params['ally_name']}")
            print(f"  权威人物: {params['authority_figure_name']}")
            print(f"  受害者/证人: {params['victim_witness_name']}")
            print(f"  悬念机制: {params['primary_suspense_mechanism']}")
            print(f"  主要地点: {params['primary_location']}")
            print(f"  故事弧线: {params['story_arc_pattern_name']}")
            print(
                f"  目标长度: {params['target_audio_length_minutes_min']}-{params['target_audio_length_minutes_max']} 分钟"
            )
            print(f"  建议章节数: {params['suggested_chapter_count']}")

        print(f"\n=== 批量生成完成 ===")
        print(f"总共生成了 {args.number} 个惊悚故事参数")
        print(
            f"文件保存范围: {starting_index}.txt 到 {starting_index + args.number - 1}.txt"
        )
        print(f"保存目录: {story_directory}")

    except FileNotFoundError:
        print("错误: 未找到配置文件 'config.json'")
        print("请确保 config.json 文件在当前目录中")
    except Exception as e:
        print(f"发生错误: {str(e)}")


if __name__ == "__main__":
    main()
