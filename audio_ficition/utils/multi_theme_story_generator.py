#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多主题故事参数生成器
Multi-Theme Story Parameter Generator

功能描述:
    一次性为多个主题生成故事参数，支持 thriller（惊悚）、scifi（科幻）、
    romance（爱情）、horror（恐怖）、fantasy（奇幻）五个主题。
    可以批量生成指定数量的故事参数，每个主题独立生成。

支持的主题:
    - thriller: 惊悚故事
    - scifi: 科幻故事
    - romance: 爱情故事
    - horror: 恐怖故事
    - fantasy: 奇幻故事

使用方法:
    1. 为所有主题各生成1个故事参数:
       python multi_theme_story_generator.py

    2. 为所有主题各生成指定数量的故事参数:
       python multi_theme_story_generator.py -n 5

    3. 只为特定主题生成故事参数:
       python multi_theme_story_generator.py -t thriller romance -n 3

    4. 查看帮助:
       python multi_theme_story_generator.py -h

输出目录:
    - Thriller: /Volumes/dhl/audio/thriller/story_params/
    - Scifi: /Volumes/dhl/audio/scifi/story_params/
    - Romance: /Volumes/dhl/audio/romance/story_params/
    - Horror: /Volumes/dhl/audio/horror/story_params/
    - Fantasy: /Volumes/dhl/audio/fantasy/story_params/

作者: 多主题故事生成系统
版本: 1.0
"""

import os
import sys
import subprocess
import argparse
import platform
from pathlib import Path


def get_base_audio_dir():
    """根据操作系统返回合适的音频基础目录"""
    if platform.system() == "Darwin":  # macOS
        return "/Volumes/dhl/audio"
    else:  # Linux 和其他系统
        return "/media/dhl/audio"


# 主题配置：每个主题对应的脚本路径和名称
def get_themes_config():
    """获取主题配置，根据操作系统动态设置路径"""
    base_dir = get_base_audio_dir()
    
    return {
        "thriller": {
            "script_path": "audio_ficition/thriller/thriller_script_generator.py",
            "display_name": "惊悚故事",
            "output_info": f"{base_dir}/thriller/story_params/",
        },
        "scifi": {
            "script_path": "audio_ficition/scifi/gen_prompt.py",
            "display_name": "科幻故事",
            "output_info": f"{base_dir}/scifi/story_param/en/",
        },
        "romance": {
            "script_path": "audio_ficition/romance/romance_script_generator.py",
            "display_name": "爱情故事",
            "output_info": f"{base_dir}/romance/story_params/",
        },
        "horror": {
            "script_path": "audio_ficition/horror/horror_script_generator.py",
            "display_name": "恐怖故事",
            "output_info": f"{base_dir}/horror/story_params/",
        },
        "fantasy": {
            "script_path": "audio_ficition/fantasy/fantasy_script_generator.py",
            "display_name": "奇幻故事",
            "output_info": f"{base_dir}/fantasy/story_param/",
        },
    }


def get_workspace_root():
    """获取工作区根目录"""
    return Path(__file__).parent.parent.parent


def run_theme_generator(theme, count, workspace_root):
    """运行特定主题的生成器"""
    themes_config = get_themes_config()
    config = themes_config[theme]
    script_path = workspace_root / config["script_path"]

    if not script_path.exists():
        print(f"错误: 未找到 {config['display_name']} 生成器脚本: {script_path}")
        return False

    print(f"\n{'='*50}")
    print(f"正在为 {config['display_name']} 生成 {count} 个故事参数...")
    print(f"脚本路径: {script_path}")
    print(f"输出目录: {config['output_info']}")
    print(f"{'='*50}")

    try:
        # 构建命令
        cmd = [sys.executable, str(script_path)]

        # 为科幻主题使用不同的参数名
        if theme == "scifi":
            cmd.extend(["--num", str(count)])
        else:
            cmd.extend(["-n", str(count)])

        # 设置正确的工作目录（脚本所在目录）
        script_dir = script_path.parent

        # 执行命令
        result = subprocess.run(
            cmd, cwd=script_dir, capture_output=True, text=True, encoding="utf-8"
        )

        # 输出结果
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"错误输出: {result.stderr}")

        # 检查是否包含明显的错误信息
        has_error = False
        if result.stdout and (
            "错误:" in result.stdout
            or "Error:" in result.stdout
            or "未找到" in result.stdout
        ):
            has_error = True
        if result.stderr:
            has_error = True

        if result.returncode == 0 and not has_error:
            print(f"✅ {config['display_name']} 生成完成!")
            return True
        else:
            print(f"❌ {config['display_name']} 生成失败! 返回码: {result.returncode}")
            return False

    except Exception as e:
        print(f"❌ 运行 {config['display_name']} 生成器时出错: {str(e)}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="一次性生成多个主题的故事参数",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
支持的主题:
  thriller  - 惊悚故事
  scifi     - 科幻故事  
  romance   - 爱情故事
  horror    - 恐怖故事
  fantasy   - 奇幻故事

示例:
  %(prog)s                          # 为所有主题各生成1个故事
  %(prog)s -n 5                     # 为所有主题各生成5个故事
  %(prog)s -t thriller romance -n 3 # 只为惊悚和爱情主题各生成3个故事
        """,
    )

    parser.add_argument(
        "-n", "--number", type=int, default=1, help="每个主题要生成的故事数量 (默认: 1)"
    )

    parser.add_argument(
        "-t",
        "--themes",
        nargs="+",
        choices=list(get_themes_config().keys()),
        default=list(get_themes_config().keys()),
        help="要生成故事的主题列表 (默认: 所有主题)",
    )

    args = parser.parse_args()

    # 获取工作区根目录
    workspace_root = get_workspace_root()
    themes_config = get_themes_config()

    print("🚀 多主题故事参数生成器启动")
    print(f"工作区根目录: {workspace_root}")
    print(f"选择的主题: {[themes_config[t]['display_name'] for t in args.themes]}")
    print(f"每个主题生成数量: {args.number}")

    # 统计信息
    total_themes = len(args.themes)
    successful_themes = 0
    failed_themes = []

    # 为每个主题生成故事参数
    for theme in args.themes:
        success = run_theme_generator(theme, args.number, workspace_root)
        if success:
            successful_themes += 1
        else:
            failed_themes.append(themes_config[theme]["display_name"])

    # 输出最终统计
    print(f"\n{'='*60}")
    print("📊 生成统计报告")
    print(f"{'='*60}")
    print(f"总主题数: {total_themes}")
    print(f"成功生成: {successful_themes}")
    print(f"失败主题: {len(failed_themes)}")

    if failed_themes:
        print(f"失败的主题: {', '.join(failed_themes)}")

    if successful_themes > 0:
        print(
            f"\n✅ 成功为 {successful_themes} 个主题各生成了 {args.number} 个故事参数"
        )
        print("📁 输出目录:")
        for theme in args.themes:
            if themes_config[theme]["display_name"] not in failed_themes:
                print(
                    f"  {themes_config[theme]['display_name']}: {themes_config[theme]['output_info']}"
                )

    if failed_themes:
        print(f"\n❌ {len(failed_themes)} 个主题生成失败，请检查错误信息")
        return 1
    else:
        print(f"\n🎉 所有主题都成功生成！")
        return 0


if __name__ == "__main__":
    sys.exit(main())
