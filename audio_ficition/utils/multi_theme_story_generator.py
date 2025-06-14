#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多主题故事参数生成器
Multi-Theme Story Parameter Generator

功能描述:
    一次性为多个主题生成故事参数，支持 thriller（惊悚）、scifi（科幻）、
    romance（爱情）、horror（恐怖）、fantasy（奇幻）五个主题。
    可以批量生成指定数量的故事参数，每个主题独立生成。
    支持断点续传，自动排除Mac系统产生的点文件。

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
    - 本地目录: /Users/donghaoliu/Documents/audio/story_param/[theme_name]/

系统要求:
    - 必须在 macOS 系统上运行
    - 支持 Apple Silicon (M1/M2/M3) 或 Intel 芯片

作者: 多主题故事生成系统
版本: 2.0
"""

import os
import sys
import subprocess
import argparse
import platform
from pathlib import Path


def check_system_requirements():
    """检查系统要求：必须是Mac（支持Intel和Apple Silicon）"""
    if platform.system() != "Darwin":
        print("❌ 错误：此程序只能在 macOS 系统上运行")
        print(f"当前系统：{platform.system()}")
        sys.exit(1)

    machine = platform.machine().lower()
    processor = platform.processor().lower()

    is_apple_silicon = (
        machine == "arm64"
        or "arm" in machine
        or "apple" in processor
        or "m1" in processor
        or "m2" in processor
        or "m3" in processor
    )
    is_intel_mac = (
        machine == "x86_64"
        or "intel" in processor
        or "i7" in processor
        or "i5" in processor
        or "i9" in processor
    )

    if not (is_apple_silicon or is_intel_mac):
        print("❌ 错误：此程序只能在 Apple Silicon 或 Intel 芯片的 Mac 上运行")
        print(f"当前芯片架构：{machine}")
        print(f"当前处理器：{processor}")
        sys.exit(1)

    if is_apple_silicon:
        print("✅ 系统检查通过：macOS + Apple Silicon")
    else:
        print("✅ 系统检查通过：macOS + Intel")
    print(f"芯片架构：{machine}")


def get_base_audio_dir():
    """返回音频基础目录，根据芯片类型区分路径"""
    # 检查操作系统
    if platform.system() == "Darwin":
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
            return "/Users/donghaoliu/Documents/audio"
        else:
            # Intel Mac
            return "/Volumes/dhl/audio"
    # 其他系统暂时不支持
    return "/Users/donghaoliu/Documents/audio"


def count_existing_files(directory):
    """统计目录中已存在的有效文件数量，排除Mac产生的点文件"""
    if not os.path.exists(directory):
        return 0

    try:
        files = os.listdir(directory)
        # 排除点文件（Mac系统文件）
        valid_files = [
            f
            for f in files
            if not f.startswith(".") and os.path.isfile(os.path.join(directory, f))
        ]
        return len(valid_files)
    except Exception as e:
        print(f"警告：无法读取目录 {directory}: {e}")
        return 0


# 主题配置：每个主题对应的脚本路径和名称
def get_themes_config():
    """获取主题配置，使用正确的输出路径"""
    base_dir = get_base_audio_dir()

    return {
        "thriller": {
            "script_path": "audio_ficition/thriller/thriller_script_generator.py",
            "display_name": "惊悚故事",
            "output_info": f"{base_dir}/thriller/story_param",
        },
        "scifi": {
            "script_path": "audio_ficition/scifi/gen_prompt.py",
            "display_name": "科幻故事",
            "output_info": f"{base_dir}/scifi/story_param",
        },
        "romance": {
            "script_path": "audio_ficition/romance/romance_script_generator.py",
            "display_name": "爱情故事",
            "output_info": f"{base_dir}/romance/story_param",
        },
        "horror": {
            "script_path": "audio_ficition/horror/horror_script_generator.py",
            "display_name": "恐怖故事",
            "output_info": f"{base_dir}/horror/story_param",
        },
        "fantasy": {
            "script_path": "audio_ficition/fantasy/fantasy_script_generator.py",
            "display_name": "奇幻故事",
            "output_info": f"{base_dir}/fantasy/story_param",
        },
    }


def get_workspace_root():
    """获取工作区根目录"""
    return Path(__file__).parent.parent.parent


def run_theme_generator(theme, count, workspace_root):
    """运行特定主题的生成器，支持断点续传"""
    themes_config = get_themes_config()
    config = themes_config[theme]
    script_path = workspace_root / config["script_path"]

    if not script_path.exists():
        print(f"错误: 未找到 {config['display_name']} 生成器脚本: {script_path}")
        return False

    # 检查断点续传
    output_dir = config["output_info"]
    existing_count = count_existing_files(output_dir)

    if existing_count >= count:
        print(f"\n{'='*50}")
        print(f"📁 {config['display_name']} 已有 {existing_count} 个文件，无需生成")
        print(f"目标数量: {count}，已存在: {existing_count}")
        print(f"输出目录: {output_dir}")
        print(f"{'='*50}")
        print(f"✅ {config['display_name']} 跳过生成（已完成）!")
        return True

    need_generate = count - existing_count
    print(f"\n{'='*50}")
    print(f"正在为 {config['display_name']} 生成 {need_generate} 个故事参数...")
    print(f"目标数量: {count}，已存在: {existing_count}，需要生成: {need_generate}")
    print(f"脚本路径: {script_path}")
    print(f"输出目录: {output_dir}")
    print(f"{'='*50}")

    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 构建命令
        cmd = [sys.executable, str(script_path)]

        # 为科幻主题使用不同的参数名
        if theme == "scifi":
            cmd.extend(["--num", str(need_generate)])
        else:
            cmd.extend(["-n", str(need_generate)])

        # 设置正确的工作目录（脚本所在目录）
        script_dir = script_path.parent

        # 设置环境变量，传递正确的基础路径给子脚本
        env = os.environ.copy()
        env["AUDIO_BASE_DIR"] = get_base_audio_dir()

        print(f"🔧 设置环境变量 AUDIO_BASE_DIR={env['AUDIO_BASE_DIR']}")

        # 执行命令
        result = subprocess.run(
            cmd,
            cwd=script_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )

        # 输出结果
        if result.stdout:
            print("📤 脚本标准输出:")
            print(result.stdout)
        if result.stderr:
            print(f"⚠️  脚本错误输出: {result.stderr}")

        # 检查是否包含明显的错误信息
        has_error = False
        if result.stdout and (
            "错误:" in result.stdout
            or "Error:" in result.stdout
            or "未找到" in result.stdout
            or "Too many levels of symbolic links" in result.stdout
            or "符号链接" in result.stdout
        ):
            has_error = True
            print("🚨 在标准输出中检测到错误信息")
        if result.stderr and (
            "error" in result.stderr.lower()
            or "Too many levels of symbolic links" in result.stderr
            or "符号链接" in result.stderr
        ):
            has_error = True
            print("🚨 在错误输出中检测到错误信息")

        if result.returncode == 0 and not has_error:
            # 再次检查文件数量确认生成成功
            final_count = count_existing_files(output_dir)
            print(f"✅ {config['display_name']} 生成完成! 最终文件数量: {final_count}")
            return True
        else:
            print(f"❌ {config['display_name']} 生成失败! 返回码: {result.returncode}")
            return False

    except Exception as e:
        print(f"❌ 运行 {config['display_name']} 生成器时出错: {str(e)}")
        return False


def main():
    """主函数"""
    # 首先检查系统要求
    check_system_requirements()

    parser = argparse.ArgumentParser(
        description="一次性生成多个主题的故事参数（支持断点续传）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
支持的主题:
  thriller  - 惊悚故事
  scifi     - 科幻故事  
  romance   - 爱情故事
  horror    - 恐怖故事
  fantasy   - 奇幻故事

系统要求:
  - macOS 系统
  - Apple Silicon 或 Intel 芯片

断点续传:
  - 自动检测已存在的文件数量
  - 只生成缺少的文件
  - 自动排除 Mac 系统产生的点文件

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

    print("🚀 多主题故事参数生成器启动 (支持断点续传)")
    print(f"工作区根目录: {workspace_root}")
    print(f"选择的主题: {[themes_config[t]['display_name'] for t in args.themes]}")
    print(f"每个主题目标数量: {args.number}")
    print(f"输出基础目录: {get_base_audio_dir()}")

    # 显示断点续传信息
    print(f"\n📊 断点续传检查:")
    for theme in args.themes:
        config = themes_config[theme]
        existing = count_existing_files(config["output_info"])
        status = (
            "✅ 已完成"
            if existing >= args.number
            else f"📝 需要生成 {args.number - existing} 个"
        )
        print(f"  {config['display_name']}: {existing}/{args.number} - {status}")

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
        print(f"\n✅ 成功处理 {successful_themes} 个主题")
        print("📁 输出目录:")
        for theme in args.themes:
            if themes_config[theme]["display_name"] not in failed_themes:
                final_count = count_existing_files(themes_config[theme]["output_info"])
                print(
                    f"  {themes_config[theme]['display_name']}: {themes_config[theme]['output_info']} ({final_count} 个文件)"
                )

    if failed_themes:
        print(f"\n❌ {len(failed_themes)} 个主题生成失败，请检查错误信息")
        return 1
    else:
        print(f"\n🎉 所有主题都成功处理！")
        return 0


if __name__ == "__main__":
    sys.exit(main())
