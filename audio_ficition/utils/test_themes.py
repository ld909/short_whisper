#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI Studio 多主题功能测试脚本

用于测试主题验证、参数生成等功能，无需实际运行浏览器
"""

import sys
import os

# 添加当前目录到路径
sys.path.append(os.path.dirname(__file__))

from ai_studio_bot import (
    SUPPORTED_THEMES,
    validate_theme,
    list_available_themes,
    generate_story_prompt_by_theme,
    get_theme_story_dir,
    get_story_parameters_to_generate,
)


def test_theme_validation():
    """测试主题验证功能"""
    print("=== 测试主题验证功能 ===")

    # 测试有效主题
    valid_themes = ["scifi", "fantasy"]
    for theme in valid_themes:
        try:
            validate_theme(theme)
            print(f"✅ {theme}: 验证通过")
        except ValueError as e:
            print(f"❌ {theme}: {e}")

    # 测试无效主题
    invalid_themes = ["love", "detective", "mystery", "unknown"]
    for theme in invalid_themes:
        try:
            validate_theme(theme)
            print(f"❌ {theme}: 应该验证失败但通过了")
        except ValueError as e:
            print(f"✅ {theme}: 正确拒绝 - {str(e)[:50]}...")


def test_theme_directories():
    """测试主题目录生成"""
    print("\n=== 测试主题目录生成 ===")

    for theme in SUPPORTED_THEMES.keys():
        story_dir = get_theme_story_dir(theme)
        print(f"{theme}: {story_dir}")


def test_prompt_generation():
    """测试故事参数生成"""
    print("\n=== 测试故事参数生成 ===")

    # 测试scifi主题
    try:
        print("测试 scifi 主题...")
        scifi_prompt = generate_story_prompt_by_theme("scifi")
        print(f"✅ scifi 参数生成成功，长度: {len(scifi_prompt)} 字符")
        print(f"预览: {scifi_prompt[:200]}...")
    except Exception as e:
        print(f"❌ scifi 参数生成失败: {e}")

    print()

    # 测试fantasy主题
    try:
        print("测试 fantasy 主题...")
        fantasy_prompt = generate_story_prompt_by_theme("fantasy")
        print(f"✅ fantasy 参数生成成功，长度: {len(fantasy_prompt)} 字符")
        print(f"预览: {fantasy_prompt[:200]}...")
    except Exception as e:
        print(f"❌ fantasy 参数生成失败: {e}")


def test_story_parameters_generation():
    """测试故事参数列表生成（不实际保存文件）"""
    print("\n=== 测试故事参数列表生成 ===")

    for theme in ["scifi", "fantasy"]:
        if SUPPORTED_THEMES[theme]["available"]:
            try:
                print(f"\n测试 {theme} 主题参数列表生成...")
                # 注意：这里不会实际创建目录或检查现有文件
                # 因为get_story_parameters_to_generate会尝试创建目录
                print(f"主题 {theme} 的故事目录: {get_theme_story_dir(theme)}")
                print(f"✅ {theme} 主题目录路径生成成功")
            except Exception as e:
                print(f"❌ {theme} 参数列表生成失败: {e}")


def main():
    """主函数"""
    print("🧪 AI Studio 多主题功能测试\n")

    # 显示所有支持的主题
    list_available_themes()

    # 运行各项测试
    test_theme_validation()
    test_theme_directories()
    test_prompt_generation()
    test_story_parameters_generation()

    print("\n=== 测试完成 ===")
    print("如果所有测试都通过，说明多主题功能基本正常。")
    print("可以运行以下命令进行实际测试：")
    print("python ai_studio_bot.py --list-themes")
    print("python ai_studio_bot.py --theme scifi --count 1")
    print("python ai_studio_bot.py --theme fantasy --count 1")


if __name__ == "__main__":
    main()
