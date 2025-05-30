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

    params["primary_fantasy_subgenre"] = select_random_element(
        config["story_settings"]["primary_fantasy_subgenres"]
    )
    params["secondary_elements"] = ", ".join(
        select_random_elements(
            config["story_settings"]["secondary_fantasy_subgenre_elements"], 2
        )
    )
    params["world_era"] = select_random_element(config["story_settings"]["world_eras"])

    # Magic System
    magic_foundation = select_random_element(
        config["story_settings"]["magic_system_foundations"]
    )
    params["magic_system_foundation_name"] = magic_foundation["name"]
    params["magic_system_foundation_description"] = magic_foundation["description"]
    params["magic_system_costs_and_limitations"] = "; ".join(
        select_random_elements(
            config["story_settings"]["magic_system_costs_and_limitations"], 3
        )
    )
    params["unique_world_phenomenon"] = select_random_element(
        config["story_settings"]["unique_world_phenomena"]
    )

    # === Themes and Tone ===
    params["themes"] = select_random_element(config["thematic_cores_catalogue"])

    # Generate tone and pacing
    tone_options = [
        "Epic and Heroic",
        "Dark and Gritty",
        "Mystical and Adventurous",
        "Hopeful and Inspiring",
        "Mysterious and Dangerous",
        "Romantic and Heroic",
    ]
    pacing_options = [
        "Slow build to explosive climax",
        "Fast-paced with continuous revelations",
        "Steady progression with sudden twists",
        "Tense suspense gradually escalating",
    ]
    params["overall_tone"] = select_random_element(tone_options)
    params["pacing_strategy"] = select_random_element(pacing_options)

    # Core concept hooks
    hook_options = [
        "A scholar discovers that the power mentioned in ancient prophecies is actually hidden in everyday objects",
        "The protagonist accidentally inherits a cursed ability and must learn to control it",
        "A seemingly ordinary craftsman discovers they are the last heir of an ancient bloodline",
        "The protagonist discovers that the world's history has been deliberately altered, and the truth could change everything",
        "An accidental magical event transports the protagonist to the forbidden lands of the world",
    ]
    params["core_concept_hook"] = select_random_element(hook_options)

    # === Character Names ===
    params["protagonist_name"] = select_random_name(config["protagonist_names"])
    params["antagonist_name"] = select_random_name(config["antagonist_names"])
    params["mentor_name"] = select_random_name(config["mentor_names"])
    params["ally_name"] = select_random_name(config["ally_names"])
    params["love_interest_name"] = select_random_name(config["love_interest_names"])

    # === Protagonist Elements ===
    params["protagonist_archetype"] = select_random_element(
        config["protagonist_elements"]["archetypes"]
    )
    params["protagonist_species"] = select_random_element(
        config["protagonist_elements"]["species_options"]
    )
    params["protagonist_positive_traits"] = "; ".join(
        select_random_elements(config["protagonist_elements"]["positive_traits"], 2)
    )
    params["protagonist_flaws"] = "; ".join(
        select_random_elements(
            config["protagonist_elements"]["flaws_and_weaknesses"], 2
        )
    )
    params["protagonist_initial_goal"] = select_random_element(
        config["protagonist_elements"]["initial_goals"]
    )
    params["protagonist_core_motivation"] = select_random_element(
        config["protagonist_elements"]["core_motivations_for_growth"]
    )

    # Protagonist skills and conflicts
    skill_options = [
        "Natural magical perception abilities, but unable to fully control them",
        "Mastery of ancient texts and runic studies",
        "Exceptional combat skills and tactical thinking",
        "Ability to communicate with animals or natural elements",
        "Possesses fragments of prophetic ability",
    ]
    params["protagonist_skill_magic"] = select_random_element(skill_options)

    conflict_options = [
        "Struggling between personal desires and collective responsibility",
        "Must overcome inner fears to unleash true potential",
        "Learning to trust others and break free from isolation habits",
        "Choosing between revenge and forgiveness",
        "Accepting their destiny while maintaining free will",
    ]
    params["protagonist_internal_conflict_arc"] = select_random_element(
        conflict_options
    )
    params["protagonist_visual_keywords"] = (
        "Weathered but determined eyes, simple yet practical attire, bearing mysterious symbols or scars"
    )

    # === Antagonist Elements ===
    params["antagonist_archetype"] = select_random_element(
        config["antagonist_elements"]["archetypes"]
    )
    params["antagonist_species"] = select_random_element(
        config["protagonist_elements"]["species_options"]
    )  # Reuse species list
    params["antagonist_motivation"] = select_random_element(
        config["antagonist_elements"]["motivations"]
    )
    params["antagonist_methods"] = select_random_element(
        config["antagonist_elements"]["methods_of_conflict"]
    )

    connection_options = [
        "Was once the protagonist's mentor or ally",
        "Shares the same bloodline or origin as the protagonist",
        "Represents a dark version of what the protagonist could become",
        "Embodies the external manifestation of the protagonist's inner fears",
        "Possesses power that the protagonist desires but dares not pursue",
    ]
    params["antagonist_protagonist_connection"] = select_random_element(
        connection_options
    )
    params["antagonist_visual_keywords"] = (
        "Majestic yet dangerous demeanor, ornate but evil decorations, radiating ominous energy"
    )

    # === Supporting Characters ===
    # Mentor character
    mentor_template = next(
        item
        for item in config["supporting_character_templates"]
        if item["role"] == "Mentor"
    )
    params["supporting_char1_role"] = "Mentor"
    params["supporting_char1_archetype"] = select_random_element(
        mentor_template["archetypes"]
    )
    params["supporting_char1_species"] = select_random_element(
        config["protagonist_elements"]["species_options"]
    )
    params["supporting_char1_skill"] = (
        "Masters lost ancient magical knowledge and combat techniques"
    )
    params["supporting_char1_relationship_to_protagonist"] = (
        "Reluctant but ultimately loyal guide who sees the protagonist's potential"
    )
    params["supporting_char1_secret"] = select_random_element(
        mentor_template["potential_secrets"]
    )
    params["supporting_char1_arc_snippet"] = (
        "Learns to trust again, finding their own redemption through helping the protagonist succeed"
    )

    # Ally/Companion character
    ally_template = next(
        item
        for item in config["supporting_character_templates"]
        if item["role"] == "Ally/Companion"
    )
    params["supporting_char2_role"] = "Ally/Companion"
    params["supporting_char2_archetype"] = select_random_element(
        ally_template["archetypes"]
    )
    params["supporting_char2_species"] = select_random_element(
        config["protagonist_elements"]["species_options"]
    )
    params["supporting_char2_skill"] = select_random_element(
        ally_template["unique_skills"]
    )
    params["supporting_char2_relationship_to_protagonist"] = (
        "Loyal friend who provides support and different perspectives at crucial moments"
    )
    params["supporting_char2_secret"] = (
        "Hiding noble identity, fled from political marriage"
    )
    params["supporting_char2_arc_snippet"] = (
        "Transforms from naive to mature, learning to maintain kindness in a cruel world"
    )

    # Love Interest character
    love_template = next(
        item
        for item in config["supporting_character_templates"]
        if item["role"] == "Love Interest"
    )
    params["supporting_char3_role"] = "Love Interest"
    params["supporting_char3_archetype"] = select_random_element(
        love_template["archetypes"]
    )
    params["supporting_char3_species"] = select_random_element(
        config["protagonist_elements"]["species_options"]
    )
    params["supporting_char3_skill"] = "Expert in healing magic and herbalism"
    params["supporting_char3_relationship_to_protagonist"] = (
        "Initially strangers, gradually developing deep emotional connections"
    )
    params["supporting_char3_secret"] = (
        "Possesses forbidden magical bloodline, fears discovery"
    )
    params["supporting_char3_arc_snippet"] = (
        "Overcomes fear of intimate relationships, learns to trust and depend on others"
    )
    params["romance_conflict_driver"] = select_random_element(
        love_template["conflict_drivers_for_romance"]
    )

    # === Story Structure ===
    chosen_arc_name = select_random_element(list(config["story_arc_patterns"].keys()))
    params["story_arc_pattern_name"] = chosen_arc_name.replace("_", " ").title()
    params["story_arc_beats_description"] = "; ".join(
        config["story_arc_patterns"][chosen_arc_name]
    )

    # === Factions ===
    faction_names = [
        "Iron Raven Legion",
        "Silver Moon Council",
        "Shadow Cult",
        "Emerald Guardians",
        "Starfire Alliance",
        "Abyss Children",
    ]
    faction_descriptions = [
        "Imperial army that reveres order and military discipline, viewing magic as a tool that needs control",
        "Ancient mage organization protecting forbidden knowledge, extremely cautious toward outsiders",
        "Mysterious religious group believing that true power can be gained through suffering",
        "Guardians of natural magic, maintaining delicate balance with the civilized world",
        "Alliance of young rebels attempting to overthrow corrupt old systems",
        "Evil cult corrupted by dark forces, seeking to drag the world into eternal chaos",
    ]
    faction_relationships = [
        "Initial oppressors, but some members may become reluctant allies",
        "Potential source of aid, but requires proving one's worth",
        "Complex adversaries, both threat and mentor to some degree",
        "Natural allies, but cultural differences create communication barriers",
    ]

    params["faction1_name"] = select_random_element(faction_names)
    faction_names.remove(params["faction1_name"])
    params["faction1_description"] = select_random_element(faction_descriptions)
    params["faction1_relationship"] = select_random_element(faction_relationships)

    params["faction2_name"] = select_random_element(faction_names)
    faction_names.remove(params["faction2_name"])
    faction_descriptions_copy = faction_descriptions.copy()
    faction_descriptions_copy.remove(params["faction1_description"])
    params["faction2_description"] = select_random_element(faction_descriptions_copy)
    faction_relationships_copy = faction_relationships.copy()
    faction_relationships_copy.remove(params["faction1_relationship"])
    params["faction2_relationship"] = select_random_element(faction_relationships_copy)

    # === Plot Elements ===
    params["plot_twist_1"] = select_random_element(config["plot_twist_catalogue"])
    remaining_twists = config["plot_twist_catalogue"].copy()
    remaining_twists.remove(params["plot_twist_1"])
    params["plot_twist_2"] = select_random_element(remaining_twists)

    params["climactic_confrontation_style"] = select_random_element(
        config["climactic_confrontation_styles"]
    )
    params["ending_tone_and_sketch"] = (
        f"{select_random_element(config['ending_tones'])} - The main threat is eliminated, but the world has undergone irreversible changes, with the protagonist bearing new burdens and responsibilities as they face an uncertain future."
    )

    # === World Building ===
    world_names = ["Aetheria", "Valdora", "Arcanum", "Mirasia", "Zephania"]
    params["world_name"] = select_random_element(world_names)

    landscape_options = [
        "Rolling magical forests and ancient stone towers",
        "Desolate deserts hiding lost temples",
        "Snow-covered mountains and mysterious crystal caves",
        "Floating islands and ancient cities in the sky",
        "Underground cities and glowing mushroom forests",
    ]
    params["world_landscapes"] = select_random_element(landscape_options)

    lore_options = [
        "Ancient wars of the gods tore apart the primal source of magic, leaving dangerous echoes and fragmented power",
        "Lost civilizations once mastered time-controlling technology, but their arrogance led to catastrophic consequences",
        "The world was once the body of a giant creature, whose death created the current continents and oceans",
        "Ancient mages tried to create a perfect magical system, but failed experiments caused reality to fracture",
        "Legendary heroes sacrificed themselves to seal evil, their power still protecting the world",
    ]
    params["historical_lore_snippet"] = select_random_element(lore_options)

    incident_options = [
        "While performing routine work, the protagonist accidentally activates a dormant artifact, revealing their hidden magical potential and attracting unwanted attention",
        "A mysterious stranger brings news about the protagonist's true identity, forcing them on a dangerous journey",
        "The protagonist's hometown is attacked by mysterious forces, forcing them to flee and seek answers",
        "The protagonist accidentally discovers an ancient secret that draws them into an ancient conflict",
        "The fulfillment of a prophecy thrusts the protagonist toward a destiny they never imagined",
    ]
    params["inciting_incident_sketch"] = select_random_element(incident_options)

    midpoint_options = [
        "The antagonist's devastating attack destroys the protagonist's support system, forcing them into desperate alliance with former enemies",
        "The protagonist discovers a game-changing truth that questions all their beliefs",
        "An important ally betrays the protagonist, forcing them to reevaluate their judgment and trust",
        "The protagonist gains powerful new abilities, but the cost is higher than expected",
        "The enemy's true motives are revealed, showing the conflict is more complex than it appears",
    ]
    params["midpoint_idea"] = select_random_element(midpoint_options)

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
    return """System Prompt:
You are a master storyteller specialized in creating immersive multi-chapter fantasy audiobooks. \
    You are a master of short and medium-length fantasy storytelling, a ten-time Nobel laureate. Truly remarkable! \
    Your goal is to generate a complete script for an audiobook at least 100 minutes long. The story should be divided into approximately {suggested_chapter_count} chapters. Each chapter should have clear beginning, rising action, climax, and resolution/hook for the next chapter. Maintain consistent narrative style (third person limited perspective, primarily focused on {protagonist_name}, unless specifically designated for dramatic effect).

User Prompt:
Generate a fantasy audiobook script based on the following parameters:

I. Core Story Blueprint:
*   Primary Subtype: {primary_fantasy_subgenre}
*   Secondary Elements/Flavor: {secondary_elements}
*   Core Concept Hook: {core_concept_hook} (this should be woven in subtly, not immediately explained explicitly to characters)
*   Overall Theme to Explore: {themes}
*   Expected Overall Tone: {overall_tone}
*   Pacing Strategy: {pacing_strategy}
*   Selected Story Arc Pattern: {story_arc_pattern_name} - Follow this arc's beats: {story_arc_beats_description}

II. World and Setting:
*   World Name: {world_name}
*   Era/Technology Level: {world_era}
*   Primary Landscapes & Atmosphere Keywords: {world_landscapes}
*   Magic System Foundation: {magic_system_foundation_name} - {magic_system_foundation_description}
*   Key Magic Rules/Costs/Limitations: {magic_system_costs_and_limitations}
*   Unique World Phenomenon to Highlight: {unique_world_phenomenon}
*   Key Factions (minimum 2, maximum 4):
    1.  Faction Name: {faction1_name}
        *   Description/Ideology: {faction1_description}
        *   Relationship to Protagonist/Antagonist: {faction1_relationship}
    2.  Faction Name: {faction2_name}
        *   Description/Ideology: {faction2_description}
        *   Relationship to Protagonist/Antagonist: {faction2_relationship}
*   Brief Historical Lore Snippet (relevant to plot): {historical_lore_snippet}

III. Characters:

*   Protagonist - {protagonist_name}:
    *   Archetype: {protagonist_archetype}
    *   Species: {protagonist_species}
    *   Defining Positive Traits: {protagonist_positive_traits}
    *   Defining Flaws/Weaknesses: {protagonist_flaws}
    *   Unique Skills/Magic (if any): {protagonist_skill_magic}
    *   Initial Goal: {protagonist_initial_goal}
    *   Ultimate Core Motivation/Goal: {protagonist_core_motivation}
    *   Internal Conflict & Character Arc Summary: {protagonist_internal_conflict_arc}
    *   Visual Description Keywords: {protagonist_visual_keywords}

*   Antagonist - {antagonist_name}:
    *   Archetype: {antagonist_archetype}
    *   Species/Essence: {antagonist_species}
    *   Core Motivation: {antagonist_motivation}
    *   Primary Methods/Strategy: {antagonist_methods}
    *   Connection/Relationship to Protagonist (direct or thematic): {antagonist_protagonist_connection}
    *   Visual Description Keywords: {antagonist_visual_keywords}

*   Key Supporting Character 1 - {mentor_name}:
    *   Role: {supporting_char1_role}
    *   Archetype: {supporting_char1_archetype}
    *   Species: {supporting_char1_species}
    *   Key Skills/Knowledge: {supporting_char1_skill}
    *   Relationship to Protagonist: {supporting_char1_relationship_to_protagonist}
    *   Potential Secret/Subplot: {supporting_char1_secret}
    *   Brief Character Arc Snippet: {supporting_char1_arc_snippet}

*   Key Supporting Character 2 - {ally_name}:
    *   Role: {supporting_char2_role}
    *   Archetype: {supporting_char2_archetype}
    *   Species: {supporting_char2_species}
    *   Key Skills/Knowledge: {supporting_char2_skill}
    *   Relationship to Protagonist: {supporting_char2_relationship_to_protagonist}
    *   Potential Secret/Subplot: {supporting_char2_secret}
    *   Brief Character Arc Snippet: {supporting_char2_arc_snippet}

*   Key Supporting Character 3 - {love_interest_name}:
    *   Role: {supporting_char3_role}
    *   Archetype: {supporting_char3_archetype}
    *   Species: {supporting_char3_species}
    *   Key Skills/Knowledge: {supporting_char3_skill}
    *   Relationship to Protagonist: {supporting_char3_relationship_to_protagonist}
    *   Potential Secret/Subplot: {supporting_char3_secret}
    *   Brief Character Arc Snippet: {supporting_char3_arc_snippet}
    *   Romance Conflict Driver: {romance_conflict_driver}

IV. Plot and Narrative Elements:
*   Inciting Incident Summary: {inciting_incident_sketch} (how the story begins and pulls the protagonist in)
*   Midpoint Turning Point Idea: {midpoint_idea} (major transformation, revelation, or escalation)
*   Key Plot Twists to Incorporate (select 1-2 from catalog or create new):
    1.  {plot_twist_1}
    2.  {plot_twist_2}
*   Climactic Confrontation Style: {climactic_confrontation_style}
*   Expected Ending Tone & Resolution Summary: {ending_tone_and_sketch}

V. Audiobook Specific Requirements:
Introduction & Hook (Approx. 0-1 min): Create a compelling hook sentence based on the Opening Hook Style, incorporating some of the listed Opening Hook Elements, limited to 1-2 sentences. Immediately transition into vividly describing the setting and atmosphere of the Initial Scenario. Establish the initial conflict, misunderstanding, or tension.
Return only a single, continuous block of plain text.
This text must be directly readable by an audio engine without requiring any further modification.
The output should not include any of the following:
Breakpoints or elements that would interrupt smooth reading
Descriptions or explanations of background music
Any other miscellaneous items, formatting, or meta-comments.
Ensure the entire output is just this uninterrupted plain text, optimized for clear audio rendering.
Ensure the complete story meets the target audio length and deeply explores the provided parameters, creating a rich and engaging narrative."""


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
        f for f in os.listdir(directory) if f.endswith(".txt") and f[:-4].isdigit()
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
        print(f"故事参数已保存到: {filepath}")


def main():
    """Main function"""
    # Add command line argument parsing
    parser = argparse.ArgumentParser(description="生成奇幻故事脚本参数")
    parser.add_argument(
        "-n", "--number", type=int, default=1, help="要生成的故事数量 (默认: 1)"
    )
    args = parser.parse_args()

    try:
        # Load configuration
        config = load_config()
        print("配置文件加载成功")

        # Get starting story index
        story_directory = "/Volumes/dhl/audio/fantasy/story_param"
        starting_index = get_next_story_index(story_directory)

        print(f"开始生成 {args.number} 个故事参数...")

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
            print(f"  主要子类型: {params['primary_fantasy_subgenre']}")
            print(f"  世界名称: {params['world_name']}")
            print(
                f"  主角: {params['protagonist_name']} ({params['protagonist_archetype']})"
            )
            print(
                f"  反派: {params['antagonist_name']} ({params['antagonist_archetype']})"
            )
            print(f"  导师: {params['mentor_name']}")
            print(f"  盟友: {params['ally_name']}")
            print(f"  恋人: {params['love_interest_name']}")
            print(f"  魔法系统: {params['magic_system_foundation_name']}")
            print(f"  独特现象: {params['unique_world_phenomenon']}")
            print(f"  故事弧线: {params['story_arc_pattern_name']}")
            print(
                f"  目标长度: {params['target_audio_length_minutes_min']}-{params['target_audio_length_minutes_max']} 分钟"
            )
            print(f"  建议章节数: {params['suggested_chapter_count']}")

        print(f"\n=== 批量生成完成 ===")
        print(f"总共生成了 {args.number} 个故事参数")
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
