#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
科幻音频小说故事提示生成器 (Sci-Fi Audio Story Prompt Generator)

功能描述:
    这个脚本用于自动生成科幻爱情音频小说的故事提示（prompt），专门为AI创作90分钟以上的音频内容设计。
    生成的故事遵循特定的创作模板：人类男主角与外星女主角的科幻爱情故事，包含完整的故事结构和详细的情节发展指导。

主要特性:
    - 基于config.json配置文件随机组合故事参数
    - 支持批量生成多个不同的故事提示
    - 自动生成完整的故事结构大纲（90分钟音频时长）
    - 输出纯文本格式，适合直接用于音频引擎
    - 支持自定义输出目录
    - 自动编号避免文件覆盖

故事模板结构:
    1. 人类男主角 + 外星女主角的科幻爱情故事
    2. 包含9个主要情节段落（从开场到尾声）
    3. 预设时长90分钟，超过10000英文单词
    4. 遵循"意外结合，跨越星际，为爱与新生而战"的核心理念

使用方法:
    基本用法:
        python gen_prompt.py
        # 生成1个故事提示，保存到默认目录

    生成多个提示:
        python gen_prompt.py -n 5
        # 生成5个不同的故事提示

    指定输出目录:
        python gen_prompt.py -o /path/to/output
        # 将文件保存到指定目录

    组合使用:
        python gen_prompt.py -n 3 -o /custom/path
        # 生成3个提示并保存到自定义目录

参数说明:
    -n, --num       生成的提示数量（默认: 1）
    -o, --output    输出目录路径（默认: 根据操作系统自动选择）
    -h, --help      显示帮助信息

依赖文件:
    - config.json: 包含所有故事参数的配置文件（必需）

输出格式:
    - 文件名: 1.txt, 2.txt, 3.txt... （自动递增编号）
    - 内容: 纯文本格式的英文故事提示
    - 每个文件包含完整的故事生成指令和结构大纲

注意事项:
    1. 确保config.json文件存在且格式正确
    2. 输出目录会自动创建（如果不存在）
    3. 生成的内容为英文，针对音频小说优化
    4. 每次运行都会生成不同的随机组合

作者:
创建时间:
最后更新:
"""

import random
import json
import re
import os
import argparse
import glob
import platform

# 获取当前脚本的目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 配置文件路径
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")


def get_base_output_path():
    """获取正确的输出目录，支持Intel Mac和Apple Silicon"""
    # 首先尝试从环境变量获取（由multi_theme_story_generator.py设置）
    base_dir = os.environ.get("AUDIO_BASE_DIR")

    if base_dir:
        output_dir = f"{base_dir}/scifi/story_param"
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
            output_dir = "/Users/donghaoliu/Documents/audio/scifi/story_param"
            print(f"🍎 检测到Apple Silicon Mac，使用路径: {output_dir}")
        else:
            output_dir = "/Volumes/dhl/audio/scifi/story_param"
            print(f"💻 检测到Intel Mac，使用路径: {output_dir}")

        return output_dir
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/audio/scifi/story_param"


# 默认输出目录
DEFAULT_OUTPUT_DIR = get_base_output_path()


def load_config():
    """Loads the configuration from config.json."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            # 调试: 打印配置文件的键
            print(f"Config keys: {list(config.keys())}")
            return config
    except FileNotFoundError:
        print(f"Error: {CONFIG_FILE} not found. Please create it.")
        exit()
    except json.JSONDecodeError:
        print(f"Error: {CONFIG_FILE} contains invalid JSON.")
        exit()


def get_parameter_value(config_data, param_name):
    """
    Selects a value for a given parameter.
    If 'select_multiple' is true, selects a random number of options.
    """
    param_info = config_data.get(param_name)
    if not param_info:
        return f"[Missing parameter: {param_name} in config]"

    # 如果param_info是列表（如某些detail_type_item），需要检查是否有select_multiple等配置
    if isinstance(param_info, list):
        # 检查是否有对应的配置信息
        param_config = config_data.get(param_name + "_config", {})
        if param_config.get("select_multiple", False):
            min_s = param_config.get("min_select", 1)
            max_s = param_config.get("max_select", len(param_info))
            num_to_select = random.randint(min_s, min(max_s, len(param_info)))
            selected_values = random.sample(param_info, num_to_select)
            return ", ".join(selected_values)
        else:
            return random.choice(param_info)

    options = param_info.get("options", [])
    if not options:
        return f"[No options for {param_name} in config]"

    if param_info.get("select_multiple", False):
        min_s = param_info.get("min_select", 1)
        max_s = param_info.get("max_select", len(options))
        num_to_select = random.randint(min_s, min(max_s, len(options)))
        selected_values = random.sample(options, num_to_select)
        return ", ".join(selected_values)  # Join multiple selections with a comma
    else:
        return random.choice(options)


def generate_hook_elements(config_data, selected_params):
    """Generates a list of elements to include in the hook description."""
    elements = []
    possible_elements = []

    # Always include core roles
    possible_elements.append(
        f"Human (Male) Role Hint: {selected_params['Human_Protagonist_Role_Archetype']}"
    )
    possible_elements.append(
        f"Alien (Female) Role Hint: {selected_params['Alien_Protagonist_Species_Name']}"
    )

    # Add scenario hint, potentially with specific detail if applicable
    initial_scenario_text = selected_params["Initial_Scenario"]
    # The Initial_Scenario itself is already constructed with its detail in generate_prompt()

    possible_elements.append(f"Initial Scenario Hint: {initial_scenario_text}")

    # Add turning point hint
    possible_elements.append(
        f"Turning Point Hint: {selected_params['Turning_Point_Mechanism']}"
    )

    # Add hints about hidden depth or conflict
    alien_hidden_depth_value = selected_params.get(
        "Alien_Protagonist_Hidden_Depth", "a mysterious secret"
    )
    possible_elements.append(f"Alien Hidden Depth Hint: {alien_hidden_depth_value}")
    possible_elements.append(
        f"Conflict Hint: {selected_params['Main_Antagonist_Faction_Type']}"
    )

    # Randomly select a few elements (minimum 2, maximum 4)
    num_elements_to_select = random.randint(2, min(4, len(possible_elements)))
    elements = random.sample(possible_elements, num_elements_to_select)

    return elements


def generate_prompt():
    """Generates a single story prompt with randomly selected parameters from config.json."""
    config_data = load_config()
    selected_params = {}

    # Select main parameters using the helper function
    for param_name in [
        "Human_Protagonist_Role_Archetype",
        "Human_Protagonist_Key_Trait",
        "Alien_Protagonist_Species_Name",
        "Alien_Protagonist_Unique_Biology",
        "Alien_Protagonist_Cultural_Quirk",
        "Alien_Protagonist_Hidden_Depth",
        "Turning_Point_Mechanism",
        "Main_Antagonist_Faction_Type",
        "Core_Conflict_Goal",
        "Core_Plot_Element",
        "Climax_Setting",
        "Resolution_Focus",
        "Opening_Hook_Style",
        "male_human_protagonist_names",
        "female_alien_protagonist_names",
    ]:
        selected_params[param_name] = get_parameter_value(config_data, param_name)

    # Select Initial Scenario and specific detail if needed
    initial_scenario_template = random.choice(
        list(config_data["Initial_Scenario_Types"].keys())
    )
    detail_type_or_list = config_data["Initial_Scenario_Types"][
        initial_scenario_template
    ]

    specific_details_for_initial_scenario_str = ""

    if detail_type_or_list:
        if isinstance(detail_type_or_list, list):  # If it's a list of detail types
            details_list = []
            for detail_type_item in detail_type_or_list:
                selected_detail = get_parameter_value(config_data, detail_type_item)
                initial_scenario_template = initial_scenario_template.replace(
                    f"[{detail_type_item}]", selected_detail, 1
                )
                details_list.append(f"{detail_type_item}: {selected_detail}")
            specific_details_for_initial_scenario_str = ", ".join(details_list)
        else:  # Single detail type
            detail_type = detail_type_or_list
            selected_detail = get_parameter_value(config_data, detail_type)
            initial_scenario_template = initial_scenario_template.replace(
                f"[{detail_type}]", selected_detail
            )
            specific_details_for_initial_scenario_str = (
                f"{detail_type}: {selected_detail}"
            )

    selected_params["Initial_Scenario"] = initial_scenario_template
    selected_params["Specific_Details_for_Initial_Scenario"] = (
        specific_details_for_initial_scenario_str
    )

    # Generate hook elements based on selected parameters
    selected_params["Opening_Hook_Elements"] = generate_hook_elements(
        config_data, selected_params
    )

    prompt = f"""**Story Generation Request:**
Generate a science fiction romance audio script in English, targeting a runtime of 1 hour or more. The story must follow the channel's core DNA: "Unexpected Union, Across the Stars, Fighting for Love and New Life". It should feature a strong narrative hook, a central romance driven by conflict and unexpected circumstances, significant character growth (especially for the alien female), unique sci-fi elements (including alien biology/culture), and high stakes. Ensure the narrative pace builds effectively over the extended duration. **The human protagonist must be Male, and the alien protagonist must be Female.**

**Story Parameters:**
-   Human (Male) Protagonist: {selected_params["Human_Protagonist_Role_Archetype"]}, Key Trait(s): {selected_params["Human_Protagonist_Key_Trait"]}, Name: {selected_params["male_human_protagonist_names"]}.
-   Alien (Female) Protagonist: {selected_params["Alien_Protagonist_Species_Name"]} ({selected_params["Alien_Protagonist_Unique_Biology"]} biological feature(s)), Cultural Quirk(s): {selected_params["Alien_Protagonist_Cultural_Quirk"]}, Name: {selected_params["female_alien_protagonist_names"]}.
-   Initial Setup: {selected_params["Initial_Scenario"]} ({selected_params["Specific_Details_for_Initial_Scenario"] if selected_params["Specific_Details_for_Initial_Scenario"] else 'No specific sub-details for this scenario type'}). The alien female protagonist shows hints of {selected_params["Alien_Protagonist_Hidden_Depth"]} in this scenario.
-   Relationship & Plot Turning Point: A major shift occurs via the {selected_params["Turning_Point_Mechanism"]} mechanism.
-   Main Conflict: Confronting {selected_params["Main_Antagonist_Faction_Type"]}, whose goal is {selected_params["Core_Conflict_Goal"]}.
-   Core Driving Element: {selected_params["Core_Plot_Element"]}.
-   Climax Setting: Takes place at {selected_params["Climax_Setting"]}.
-   Resolution Focus: {selected_params["Resolution_Focus"]}.
-   Opening Hook Style: {selected_params["Opening_Hook_Style"]}, includes elements such as: {', '.join(selected_params["Opening_Hook_Elements"])}.

**Story Structure Outline (Guidance for AI over 90 mins duration):**
Introduction & Hook (Approx. 0-1 min): Create a compelling hook sentence based on the Opening Hook Style, incorporating some of the listed Opening Hook Elements, limited to 1-2 sentences. Immediately transition into vividly describing the setting and atmosphere of the Initial Scenario, introducing the human male protagonist and the alien female protagonist in their initial dynamic. Establish the initial conflict, misunderstanding, or tension. Hint at the alien female protagonist's unique nature or situation (Unique Biology, Cultural Quirk, or initial glimpses of Hidden Depth).
Initial Encounter & Immediate Consequences (Approx. 1-13 mins): Detail the events of the Initial Scenario. Explore the initial interactions between the human male protagonist, highlighting his Key Trait(s), and the alien female's initial status/behavior. Introduce the immediate consequences of the encounter – this could be the first sign of pursuit by the Main Antagonist Faction Type, the confusion arising from a Cultural Event/Ritual, or the immediate challenge posed by a Crash Reason. The alien female protagonist might reveal a bit more about her situation or capability.
Turning Point Event & Forced Proximity (Approx. 13-23 mins): Describe the Turning Point Mechanism event in detail. This event fundamentally changes their situation, forcing the protagonists into prolonged or intense proximity (e.g., escaping together, stranded, bound by a ritual, dealing with a biological change). The conflict with the Main Antagonist Faction Type intensifies, making cooperation essential for survival.
Developing Trust and Unveiling Depths (Approx. 23-43 mins): This is a significant section for character and relationship development. Through multiple scenes of shared challenges, difficult choices, and moments of vulnerability during their forced cooperation/escape, the protagonists begin to break down initial barriers and prejudices. The alien female protagonist reveals more about her Hidden Depth, often tied to the Core Plot Element. The human male protagonist's Key Trait(s) become evident in how he handles these situations. Explore cultural differences (Cultural Quirk(s)) and unique biological aspects (Unique Biology feature(s)) in detail, integrating them into problem-solving and interaction. Romantic tension begins to build through shared glances, physical proximity, and deeper conversations.
Escalating Stakes & Romantic Connection (Approx. 43-63 mins): The conflict with the Main Antagonist Faction Type reaches a critical point. The stakes surrounding the Core Plot Element become clearer and more dangerous. The emotional and romantic connection between the protagonists deepens significantly. This section should include one or more key romantic or intimate scenes that solidify their bond, potentially involving the unique aspects of the alien female's biology. They explicitly acknowledge their growing feelings or make a choice based on their connection.
Rising Action Towards Climax (Approx. 63-75 mins): The protagonists make a strategic move or are cornered, leading them directly towards the Climax Setting. They prepare for the final confrontation, relying on their combined skills and trust. New information about the antagonist or the stakes might be revealed.
Climax Sequence (Approx. 75-84 mins): The intense, multi-part climax takes place at the Climax Setting. The protagonists face the Main Antagonist Faction Type head-on. Detail the action, strategy, and how their unique abilities (Key Trait(s), Hidden Depth / Unique Biology feature(s)) combine effectively. This should be the peak of both the external conflict and their partnership.
Immediate Aftermath & Resolution (Approx. 84-88 mins): The external crisis is resolved. Detail the immediate consequences of the climax. The protagonists deal with injuries, aftermath, and the immediate reactions from allies or the wider galaxy. Their relationship is explicitly confirmed or demonstrated in a powerful way in the wake of the danger. Their personal choice has broader implications related to the Resolution Focus.
Epilogue & Future Outlook (Approx. 88-90 mins): A concluding section (potentially with a short time skip) showing the results of their actions and the Resolution Focus. Depict the protagonists building their new life together, how their relationship has impacted the wider galaxy (e.g., a new alliance, changing perceptions), and hinting at a hopeful future. End on a strong, romantic, or thematic note that reinforces the channel's core DNA. romantic, or thematic note that reinforces the channel's core DNA.

**Output Format:** Story script in English, including major sections and detailed narrative descriptions following the guidance above.
Return only a single, continuous block of plain text.
This text must be directly readable by an audio engine without requiring any further modification.
The output should not include any of the following:
Breakpoints or elements that would interrupt smooth reading
Descriptions or explanations of background music
Any other miscellaneous items, formatting, or meta-comments.
Ensure the entire output is just this uninterrupted plain text, optimized for clear audio rendering.
The full text must be over ten thousand English words. Let me repeat: this is a requirement that absolutely must be met.
Ensure content is non-conversational in format.
**IMPORTANT:** Use the specified protagonist names throughout the story: the human male protagonist should be called {selected_params["male_human_protagonist_names"]} and the alien female protagonist should be called {selected_params["female_alien_protagonist_names"]}. Do not change or modify these names during the story generation.
Make 100% sure the story is long enough to be a full audiobook, which is at least 100 minutes long.
*   Ensure the total word count reaches at least 150,000 words.
*   Ensure the total word count reaches at least 150,000 words.
"""
    return prompt


def remove_markdown(text):
    """移除文本中的markdown格式符号"""
    # 移除**加粗**标记
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    # 移除其他可能的markdown符号，如有需要可以扩展
    return text


def save_prompt_to_file(prompt, output_dir=DEFAULT_OUTPUT_DIR, filename=None):
    """
    将生成的提示保存到文本文件
    如果filename为None，则使用下一个可用的序号命名
    """
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        if filename is None:
            # 查找目录中现有的.txt文件
            existing_files = glob.glob(os.path.join(output_dir, "*.txt"))
            existing_numbers = []

            # 提取文件名中的数字部分
            for file_path in existing_files:
                basename = os.path.basename(file_path)
                match = re.match(r"(\d+)\.txt", basename)
                if match:
                    existing_numbers.append(int(match.group(1)))

            # 找到下一个可用的序号
            next_number = 1
            if existing_numbers:
                next_number = max(existing_numbers) + 1

            filename = f"{next_number}.txt"

        full_path = os.path.join(output_dir, filename)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(prompt)
        print(f"提示已保存到: {full_path}")
        return full_path
    except Exception as e:
        print(f"保存文件时出错: {e}")
        return None


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="生成科幻小说提示")
    parser.add_argument(
        "-n", "--num", type=int, default=1, help="要生成的提示数量（默认为1）"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"输出目录（默认为{DEFAULT_OUTPUT_DIR}）",
    )
    return parser.parse_args()


if __name__ == "__main__":
    # 解析命令行参数
    args = parse_arguments()

    # 生成指定数量的提示
    saved_files = []
    for i in range(args.num):
        print(f"正在生成第 {i+1}/{args.num} 个提示...")

        # 生成提示
        generated_story_prompt = generate_prompt()

        # 移除markdown格式
        clean_prompt = remove_markdown(generated_story_prompt)

        # 保存到文件
        saved_path = save_prompt_to_file(clean_prompt, args.output)
        if saved_path:
            saved_files.append(saved_path)

    # 打印生成结果摘要
    if saved_files:
        print(f"\n成功生成了 {len(saved_files)} 个提示文件:")
        for file_path in saved_files:
            print(f"- {file_path}")
    else:
        print("未能成功生成任何提示文件。")
