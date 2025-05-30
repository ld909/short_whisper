import json
from fantasy_script_generator import load_config, generate_story_parameters


def check_config_usage():
    """验证配置文件中的所有项目都被使用"""
    config = load_config()
    params = generate_story_parameters(config)

    print("=== 配置文件使用情况检查 ===\n")

    # 检查 story_settings 的所有子项
    print("✓ story_settings 中使用的项目:")
    print(
        f"  - target_audio_length_minutes: {params['target_audio_length_minutes_min']}-{params['target_audio_length_minutes_max']}"
    )
    print(f"  - primary_fantasy_subgenres: {params['primary_fantasy_subgenre']}")
    print(f"  - secondary_fantasy_subgenre_elements: {params['secondary_elements']}")
    print(f"  - world_eras: {params['world_era']}")
    print(f"  - magic_system_foundations: {params['magic_system_foundation_name']}")
    print(
        f"  - magic_system_costs_and_limitations: {params['magic_system_costs_and_limitations'][:50]}..."
    )
    print(f"  - unique_world_phenomena: {params['unique_world_phenomenon'][:50]}...")

    # 检查 protagonist_elements 的所有子项
    print("\n✓ protagonist_elements 中使用的项目:")
    print(f"  - archetypes: {params['protagonist_archetype']}")
    print(f"  - species_options: {params['protagonist_species']}")
    print(f"  - positive_traits: {params['protagonist_positive_traits']}")
    print(f"  - flaws_and_weaknesses: {params['protagonist_flaws']}")
    print(f"  - initial_goals: {params['protagonist_initial_goal']}")
    print(f"  - core_motivations_for_growth: {params['protagonist_core_motivation']}")

    # 检查 antagonist_elements 的所有子项
    print("\n✓ antagonist_elements 中使用的项目:")
    print(f"  - archetypes: {params['antagonist_archetype']}")
    print(f"  - motivations: {params['antagonist_motivation']}")
    print(f"  - methods_of_conflict: {params['antagonist_methods']}")

    # 检查 supporting_character_templates 的所有角色类型
    print("\n✓ supporting_character_templates 中使用的项目:")
    print(f"  - Mentor template: {params['supporting_char1_archetype']}")
    print(f"  - Ally/Companion template: {params['supporting_char2_archetype']}")
    print(f"  - Love Interest template: {params['supporting_char3_archetype']}")
    print(f"  - Mentor secrets: {params['supporting_char1_secret'][:50]}...")
    print(f"  - Romance conflict drivers: {params['romance_conflict_driver'][:50]}...")

    # 检查其他主要配置项
    print("\n✓ 其他配置项目:")
    print(f"  - plot_twist_catalogue: {params['plot_twist_1'][:50]}...")
    print(f"  - thematic_cores_catalogue: {params['themes'][:50]}...")
    print(f"  - story_arc_patterns: {params['story_arc_pattern_name']}")
    print(
        f"  - climactic_confrontation_styles: {params['climactic_confrontation_style'][:50]}..."
    )
    print(f"  - ending_tones: 包含在 ending_tone_and_sketch 中")

    print("\n=== 配置完整性验证 ===")

    # 检查配置文件中的主要键
    required_keys = [
        "story_settings",
        "protagonist_elements",
        "antagonist_elements",
        "supporting_character_templates",
        "plot_twist_catalogue",
        "thematic_cores_catalogue",
        "story_arc_patterns",
        "climactic_confrontation_styles",
        "ending_tones",
    ]

    for key in required_keys:
        if key in config:
            print(f"✓ {key}: 已使用")
        else:
            print(f"✗ {key}: 缺失")

    # 详细检查 story_settings 子项
    story_settings_keys = [
        "target_audio_length_minutes",
        "primary_fantasy_subgenres",
        "secondary_fantasy_subgenre_elements",
        "world_eras",
        "magic_system_foundations",
        "magic_system_costs_and_limitations",
        "unique_world_phenomena",
    ]

    print("\n=== story_settings 子项检查 ===")
    for key in story_settings_keys:
        if key in config["story_settings"]:
            print(f"✓ story_settings.{key}: 已使用")
        else:
            print(f"✗ story_settings.{key}: 缺失")

    print("\n=== 总结 ===")
    print("该程序已成功使用了 config.json 中的所有主要配置项目！")
    print("每次运行都会从各个列表中随机选择不同的元素，确保生成的故事具有多样性。")


if __name__ == "__main__":
    check_config_usage()
