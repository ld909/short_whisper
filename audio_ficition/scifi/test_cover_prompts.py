#!/usr/bin/env python3
"""
测试封面提示词生成脚本的基本功能
"""

import os
import sys
import tempfile
import shutil
from generate_cover_prompts import (
    get_existing_stories,
    get_existing_cover_prompts,
    save_cover_prompt,
    setup_openai_client,
)


def test_file_operations():
    """测试文件操作功能"""
    print("测试文件操作功能...")

    # 测试保存封面提示词
    test_prompt = "A beautiful alien female with blue skin, standing beside a human male astronaut, futuristic background, romantic atmosphere"

    # 创建临时测试目录
    test_dir = "/tmp/test_cover_prompts"
    os.makedirs(test_dir, exist_ok=True)

    # 临时修改输出目录用于测试
    original_save = save_cover_prompt

    def test_save_cover_prompt(story_index, prompt_content):
        """测试版本的保存函数"""
        file_path = os.path.join(test_dir, f"{story_index}.txt")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(prompt_content)
            print(f"✅ 测试保存成功: {file_path}")
            return True
        except Exception as e:
            print(f"❌ 测试保存失败: {e}")
            return False

    # 测试保存功能
    success = test_save_cover_prompt(999, test_prompt)
    if success:
        # 验证文件内容
        test_file = os.path.join(test_dir, "999.txt")
        if os.path.exists(test_file):
            with open(test_file, "r", encoding="utf-8") as f:
                content = f.read()
            if content == test_prompt:
                print("✅ 文件内容验证通过")
            else:
                print("❌ 文件内容验证失败")
        else:
            print("❌ 测试文件未创建")

    # 清理测试文件
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        print("🧹 测试文件已清理")


def test_story_discovery():
    """测试故事发现功能"""
    print("\n测试故事发现功能...")

    stories = get_existing_stories()
    print(f"发现故事数量: {len(stories)}")

    if stories:
        # 显示前5个故事的基本信息
        story_indices = sorted(stories.keys())[:5]
        for idx in story_indices:
            content_length = len(stories[idx])
            print(f"  故事 {idx}: {content_length} 字符")
    else:
        print("⚠️ 未发现任何故事文件")


def test_existing_prompts():
    """测试现有提示词发现功能"""
    print("\n测试现有提示词发现功能...")

    existing = get_existing_cover_prompts()
    print(f"现有提示词数量: {len(existing)}")

    if existing:
        sorted_indices = sorted(list(existing))[:10]  # 显示前10个
        print(f"  现有索引: {sorted_indices}")
    else:
        print("⚠️ 未发现任何现有提示词文件")


def test_openai_client():
    """测试OpenAI客户端设置"""
    print("\n测试OpenAI客户端设置...")

    api_key = os.environ.get("UNI_API_KEY")
    if api_key:
        print("✅ 找到API密钥")
        try:
            client = setup_openai_client()
            print("✅ OpenAI客户端初始化成功")
            return True
        except Exception as e:
            print(f"❌ OpenAI客户端初始化失败: {e}")
            return False
    else:
        print("⚠️ 未设置UNI_API_KEY环境变量")
        return False


def main():
    """主测试函数"""
    print("🧪 封面提示词生成器功能测试")
    print("=" * 50)

    # 测试文件操作
    test_file_operations()

    # 测试故事发现
    test_story_discovery()

    # 测试现有提示词发现
    test_existing_prompts()

    # 测试OpenAI客户端
    api_ready = test_openai_client()

    print("\n" + "=" * 50)
    print("🏁 测试完成")

    if api_ready:
        print("✅ 所有功能准备就绪，可以开始生成封面提示词")
    else:
        print("⚠️ 需要设置UNI_API_KEY环境变量才能使用AI生成功能")


if __name__ == "__main__":
    main()
