#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Romance Story Script Parameter Generator

Description:
    Automatically generates romance novel story parameters for creating audiobook scripts.
    Based on configuration files, randomly combines various elements (characters, settings, conflict types, etc.)
    to generate complete story creation prompt templates.

Dependencies:
    - config.json: Configuration file containing all optional story elements
      Must be placed in the same directory as the script

Input:
    - config.json: Story elements configuration file
    - Command line arguments: Optional generation quantity

Output:
    - Fixed directory: /Users/donghaoliu/Documents/audio/story_param/romance/
    - File format: {index}.txt (e.g., 1.txt, 2.txt, 3.txt...)
    - Content: Complete story creation prompts, ready for AI story generation

Usage:
    1. Basic usage (generate 1 story parameter):
       python romance_script_generator.py

    2. Batch generation (generate N story parameters):
       python romance_script_generator.py -n 5
       python romance_script_generator.py --number 10

    3. View help:
       python romance_script_generator.py -h

Notes:
    - Ensure config.json file exists and is properly formatted
    - Output directory will be created automatically (if it doesn't exist)
    - Script automatically avoids overwriting existing files (starts from max index + 1)
    - Each generated story parameter contains complete settings, character configurations, plot structures, etc.

Author: Romance Story Generation System
Version: 1.0
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

    params["primary_romance_subgenre"] = select_random_element(
        config["story_settings"]["primary_romance_subgenres"]
    )
    params["secondary_elements"] = ", ".join(
        select_random_elements(
            config["story_settings"]["secondary_romance_elements"], 2
        )
    )
    params["setting_era"] = select_random_element(
        config["story_settings"]["setting_eras"]
    )

    # Romance specific settings
    params["heat_level"] = select_random_element(
        config["story_settings"]["heat_levels"]
    )
    params["romance_trope"] = select_random_element(
        config["story_settings"]["romance_tropes"]
    )
    params["conflict_source"] = select_random_element(
        config["story_settings"]["conflict_sources"]
    )

    # === Themes and Tone ===
    params["themes"] = select_random_element(config["thematic_cores_catalogue"])
    params["overall_tone"] = select_random_element(
        config["additional_story_elements"]["tone_options"]
    )
    params["pacing_strategy"] = select_random_element(
        config["additional_story_elements"]["pacing_options"]
    )
    params["core_concept_hook"] = select_random_element(
        config["additional_story_elements"]["core_concept_hooks"]
    )

    # === Character Names ===
    params["protagonist_name"] = select_random_name(config["protagonist_names"])
    params["love_interest_name"] = select_random_name(config["love_interest_names"])
    params["supporting_friend_name"] = select_random_name(
        config["supporting_friend_names"]
    )
    params["rival_name"] = select_random_name(config["rival_names"])

    # === Protagonist Elements ===
    params["protagonist_archetype"] = select_random_element(
        config["protagonist_elements"]["archetypes"]
    )
    params["protagonist_occupation"] = select_random_element(
        config["protagonist_elements"]["occupations"]
    )
    params["protagonist_positive_traits"] = "; ".join(
        select_random_elements(config["protagonist_elements"]["positive_traits"], 2)
    )
    params["protagonist_flaws"] = "; ".join(
        select_random_elements(
            config["protagonist_elements"]["flaws_and_weaknesses"], 2
        )
    )
    params["protagonist_background"] = select_random_element(
        config["protagonist_elements"]["backgrounds"]
    )
    params["protagonist_relationship_history"] = select_random_element(
        config["protagonist_elements"]["relationship_histories"]
    )

    # === Love Interest Elements ===
    params["love_interest_archetype"] = select_random_element(
        config["love_interest_elements"]["archetypes"]
    )
    params["love_interest_occupation"] = select_random_element(
        config["love_interest_elements"]["occupations"]
    )
    params["love_interest_positive_traits"] = "; ".join(
        select_random_elements(config["love_interest_elements"]["positive_traits"], 2)
    )
    params["love_interest_flaws"] = "; ".join(
        select_random_elements(
            config["love_interest_elements"]["flaws_and_weaknesses"], 2
        )
    )
    params["love_interest_background"] = select_random_element(
        config["love_interest_elements"]["backgrounds"]
    )

    # === Supporting Characters ===
    params["supporting_friend_role"] = select_random_element(
        config["supporting_characters"]["friend_roles"]
    )
    params["supporting_friend_personality"] = select_random_element(
        config["supporting_characters"]["personalities"]
    )

    params["rival_type"] = select_random_element(
        config["supporting_characters"]["rival_types"]
    )
    params["rival_motivation"] = select_random_element(
        config["supporting_characters"]["rival_motivations"]
    )

    # === Story Structure ===
    chosen_arc_name = select_random_element(list(config["story_arc_patterns"].keys()))
    params["story_arc_pattern_name"] = chosen_arc_name.replace("_", " ").title()
    params["story_arc_beats_description"] = "; ".join(
        config["story_arc_patterns"][chosen_arc_name]
    )

    # === Plot Elements ===
    params["meet_cute_scenario"] = select_random_element(config["meet_cute_scenarios"])
    params["first_conflict"] = select_random_element(config["first_conflicts"])
    params["midpoint_crisis"] = select_random_element(config["midpoint_crises"])
    params["dark_moment"] = select_random_element(config["dark_moments"])
    params["resolution_style"] = select_random_element(config["resolution_styles"])

    # === Setting Elements ===
    params["primary_setting"] = select_random_element(
        config["additional_story_elements"]["primary_settings"]
    )
    params["atmosphere_keywords"] = select_random_element(
        config["additional_story_elements"]["atmosphere_keywords"]
    )
    params["cultural_context"] = select_random_element(
        config["additional_story_elements"]["cultural_contexts"]
    )

    # === Romance Development ===
    params["attraction_catalyst"] = select_random_element(
        config["romance_development"]["attraction_catalysts"]
    )
    params["relationship_obstacle"] = select_random_element(
        config["romance_development"]["relationship_obstacles"]
    )
    params["emotional_turning_point"] = select_random_element(
        config["romance_development"]["emotional_turning_points"]
    )
    params["intimacy_progression"] = select_random_element(
        config["romance_development"]["intimacy_progressions"]
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
You are a master storyteller specialized in creating immersive multi-chapter romance audiobooks. \
    You are a master of romance storytelling, a ten-time Nobel laureate in literature. Truly remarkable! \
    Your goal is to generate a complete script for an audiobook at least 100 minutes long. \
    The story should be divided into approximately {suggested_chapter_count} chapters. Each chapter should have clear beginning, rising action, climax, and resolution/hook for the next chapter. Maintain consistent narrative style (third person limited perspective, alternating between {protagonist_name} and {love_interest_name} viewpoints for dramatic effect).

Generate a romance audiobook script based on the following parameters:

I. Core Story Blueprint:
*   Primary Romance Subtype: {primary_romance_subgenre}
*   Secondary Elements/Flavor: {secondary_elements}
*   Core Concept Hook: {core_concept_hook} (this should be woven in subtly, not immediately explained explicitly to characters)
*   Overall Theme to Explore: {themes}
*   Expected Overall Tone: {overall_tone}
*   Pacing Strategy: {pacing_strategy}
*   Heat Level: {heat_level}
*   Primary Romance Trope: {romance_trope}
*   Main Conflict Source: {conflict_source}
*   Selected Story Arc Pattern: {story_arc_pattern_name} - Follow this arc's beats: {story_arc_beats_description}

II. Setting and Context:
*   Time Period/Era: {setting_era}
*   Primary Setting: {primary_setting}
*   Atmosphere Keywords: {atmosphere_keywords}
*   Cultural Context: {cultural_context}

III. Characters:

*   Protagonist - {protagonist_name}:
    *   Archetype: {protagonist_archetype}
    *   Occupation: {protagonist_occupation}
    *   Background: {protagonist_background}
    *   Defining Positive Traits: {protagonist_positive_traits}
    *   Defining Flaws/Weaknesses: {protagonist_flaws}
    *   Relationship History: {protagonist_relationship_history}

*   Love Interest - {love_interest_name}:
    *   Archetype: {love_interest_archetype}
    *   Occupation: {love_interest_occupation}
    *   Background: {love_interest_background}
    *   Defining Positive Traits: {love_interest_positive_traits}
    *   Defining Flaws/Weaknesses: {love_interest_flaws}

*   Supporting Friend - {supporting_friend_name}:
    *   Role: {supporting_friend_role}
    *   Personality: {supporting_friend_personality}

*   Rival/Obstacle Character - {rival_name}:
    *   Type: {rival_type}
    *   Motivation: {rival_motivation}

IV. Romance Development Arc:
*   Meet Cute/First Encounter: {meet_cute_scenario}
*   Attraction Catalyst: {attraction_catalyst}
*   First Major Conflict: {first_conflict}
*   Relationship Obstacle: {relationship_obstacle}
*   Midpoint Crisis: {midpoint_crisis}
*   Emotional Turning Point: {emotional_turning_point}
*   Dark Moment/Near Breakup: {dark_moment}
*   Intimacy Progression Style: {intimacy_progression}
*   Resolution & Happy Ending Style: {resolution_style}

V. Audiobook Specific Requirements:
Introduction & Hook (Approx. 0-1 min): Create a compelling hook sentence that immediately establishes the romantic tension and emotional stakes. Immediately transition into vividly describing the setting and atmosphere of the opening scene. Establish the initial conflict, misunderstanding, or romantic tension.

Return only a single, continuous block of plain text.
This text must be directly readable by an audio engine without requiring any further modification.
The output should not include any of the following:
Breakpoints or elements that would interrupt smooth reading
Descriptions or explanations of background music
Any other miscellaneous items, formatting, or meta-comments.
Ensure the entire output is just this uninterrupted plain text, optimized for clear audio rendering.
Ensure the complete story meets the target audio length and deeply explores the provided parameters, creating a rich and engaging narrative.
Make 100% sure the story is long enough to be a full audiobook, which is at least 100 minutes long.

*   Focus on emotional depth, character development, and romantic tension
*   Include satisfying romantic progression with appropriate intimacy for the heat level
*   Ensure both characters have complete character arcs and personal growth
*   Create compelling secondary characters and subplots
*   Build to a satisfying happily-ever-after or happy-for-now ending
*   Ensure the total word count reaches at least 150,000 words.
*   Ensure the total word count reaches at least 150,000 words.
*   Ensure the total word count reaches at least 150,000 words.

**IMPORTANT:** Use the specified character names throughout the story: Do not change or modify these names during the story generation.
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

    # Exclude Mac-generated files starting with dots
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
        print(f"Story parameters saved to: {filepath}")


def main():
    """Main function"""
    # Add command line argument parsing
    parser = argparse.ArgumentParser(
        description="Generate romance story script parameters"
    )
    parser.add_argument(
        "-n",
        "--number",
        type=int,
        default=1,
        help="Number of stories to generate (default: 1)",
    )
    args = parser.parse_args()

    try:
        # Load configuration
        config = load_config()
        print("Configuration file loaded successfully")

        # Get starting story index
        story_directory = "/Users/donghaoliu/Documents/audio/story_param/romance"
        starting_index = get_next_story_index(story_directory)

        print(f"Starting to generate {args.number} story parameters...")

        # Generate multiple stories
        for i in range(args.number):
            current_index = starting_index + i
            print(f"\nGenerating story {i+1}/{args.number} (Index: {current_index})...")

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
            print(f"Story {current_index} parameter preview:")
            print(f"  Primary Subgenre: {params['primary_romance_subgenre']}")
            print(f"  Setting Era: {params['setting_era']}")
            print(
                f"  Protagonist: {params['protagonist_name']} ({params['protagonist_archetype']})"
            )
            print(
                f"  Love Interest: {params['love_interest_name']} ({params['love_interest_archetype']})"
            )
            print(f"  Supporting Friend: {params['supporting_friend_name']}")
            print(f"  Rival: {params['rival_name']}")
            print(f"  Heat Level: {params['heat_level']}")
            print(f"  Romance Trope: {params['romance_trope']}")
            print(f"  Conflict Source: {params['conflict_source']}")
            print(f"  Story Arc: {params['story_arc_pattern_name']}")
            print(
                f"  Target Length: {params['target_audio_length_minutes_min']}-{params['target_audio_length_minutes_max']} minutes"
            )
            print(f"  Suggested Chapters: {params['suggested_chapter_count']}")

        print(f"\n=== Batch Generation Complete ===")
        print(f"Generated a total of {args.number} story parameters")
        print(
            f"File range: {starting_index}.txt to {starting_index + args.number - 1}.txt"
        )
        print(f"Save directory: {story_directory}")

    except FileNotFoundError:
        print("Error: Configuration file 'config.json' not found")
        print("Please ensure config.json file is in the current directory")
    except Exception as e:
        print(f"Error occurred: {str(e)}")


if __name__ == "__main__":
    main()
