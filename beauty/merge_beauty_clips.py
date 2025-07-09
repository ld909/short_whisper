#!/usr/bin/env python3
"""
美容视频剪辑合并工具

用于将指定目录下的mp4剪辑按照特定规则合并成一个视频文件。
合并规则：
1. 优先按数字顺序合并（1.mp4, 2.mp4, 3.mp4...）
2. 然后随机合并其他非数字命名的文件
3. 确保每个文件只使用一次
4. 自动排除Mac系统生成的点开头文件

使用方法:
    python merge_beauty_clips.py --index 1
    python merge_beauty_clips.py --index 2 --dry-run

输入路径:
- Intel Mac: /Volumes/dhl/beauty/clips/[index]/*.mp4
- Apple Silicon Mac: /Users/donghaoliu/Documents/beauty/clips/[index]/*.mp4
- Ubuntu: /mnt/dhl/beauty/clips/[index]/*.mp4

输出路径:
- Intel Mac: /Volumes/dhl/beauty/mp4_low_res/[index].mp4
- Apple Silicon Mac: /Users/donghaoliu/Documents/beauty/mp4_low_res/[index].mp4
- Ubuntu: /mnt/dhl/beauty/mp4_low_res/[index].mp4
"""

import os
import sys
import glob
import argparse
import random
import re
import subprocess
import tempfile
import platform
from pathlib import Path
from typing import List, Tuple


def check_supported_system():
    """检查是否为支持的系统（macOS 或 Ubuntu）"""
    system = platform.system()

    if system == "Darwin":
        # macOS
        machine = platform.machine()
        if machine == "x86_64":
            print(f"✅ 系统检查通过：macOS (Intel)")
        elif machine == "arm64":
            print(f"✅ 系统检查通过：macOS (Apple Silicon)")
        else:
            print(f"✅ 系统检查通过：macOS ({machine})")
        return True

    elif system == "Linux":
        # 检查是否为Ubuntu
        try:
            with open("/etc/os-release", "r") as f:
                content = f.read()
                if "Ubuntu" in content:
                    print(f"✅ 系统检查通过：Ubuntu")
                    return True
                else:
                    print(f"✅ 系统检查通过：Linux")
                    return True
        except FileNotFoundError:
            # 尝试检查另一个文件
            try:
                with open("/etc/lsb-release", "r") as f:
                    content = f.read()
                    if "Ubuntu" in content:
                        print(f"✅ 系统检查通过：Ubuntu")
                        return True
            except FileNotFoundError:
                pass
            print(f"✅ 系统检查通过：Linux")
            return True
    else:
        print(f"❌ 错误：不支持的操作系统")
        print(f"   当前系统：{system}")
        print(f"   支持的系统：macOS, Ubuntu/Linux")
        return False


def get_base_media_path():
    """根据系统类型返回相应的媒体路径"""
    system = platform.system()

    if system == "Darwin":
        # macOS
        machine = platform.machine()
        if machine == "x86_64":
            # Intel Mac
            return "/Volumes/dhl/beauty"
        else:
            # Apple Silicon Mac
            return "/Users/donghaoliu/Documents/beauty"
    else:
        # Linux/Ubuntu
        return "/mnt/dhl/beauty"


def is_mac_system_file(filename: str) -> bool:
    """检查是否为Mac系统生成的文件"""
    return filename.startswith(".")


def get_mp4_files(clips_dir: str) -> List[str]:
    """获取目录下所有mp4文件，排除Mac系统文件"""
    if not os.path.exists(clips_dir):
        raise FileNotFoundError(f"剪辑目录不存在: {clips_dir}")

    # 获取所有mp4文件
    mp4_pattern = os.path.join(clips_dir, "*.mp4")
    all_mp4_files = glob.glob(mp4_pattern)

    # 过滤掉Mac系统文件
    filtered_files = []
    for file_path in all_mp4_files:
        filename = os.path.basename(file_path)
        if not is_mac_system_file(filename):
            filtered_files.append(file_path)

    return filtered_files


def parse_numbered_files(mp4_files: List[str]) -> Tuple[List[str], List[str]]:
    """
    解析数字命名的文件和其他文件

    返回:
        numbered_files: 按数字顺序排序的文件列表
        other_files: 其他非数字命名的文件列表
    """
    numbered_files = []
    other_files = []

    # 用于存储数字文件的字典 {数字: 文件路径}
    numbered_dict = {}

    for file_path in mp4_files:
        filename = os.path.basename(file_path)
        name_without_ext = os.path.splitext(filename)[0]

        # 检查是否为纯数字命名
        if re.match(r"^\d+$", name_without_ext):
            number = int(name_without_ext)
            numbered_dict[number] = file_path
        else:
            other_files.append(file_path)

    # 按数字顺序排序numbered_files
    if numbered_dict:
        sorted_numbers = sorted(numbered_dict.keys())
        numbered_files = [numbered_dict[num] for num in sorted_numbers]

    return numbered_files, other_files


def create_concat_file(file_list: List[str]) -> str:
    """创建ffmpeg concat文件"""
    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)

    for file_path in file_list:
        # 写入绝对路径，避免路径问题
        abs_path = os.path.abspath(file_path)
        temp_file.write(f"file '{abs_path}'\n")

    temp_file.close()
    return temp_file.name


def merge_videos(file_list: List[str], output_path: str) -> bool:
    """使用ffmpeg合并视频文件"""
    if not file_list:
        print("❌ 没有找到可合并的视频文件")
        return False

    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    # 创建concat文件
    concat_file = create_concat_file(file_list)

    try:
        # 构建ffmpeg命令
        cmd = [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_file,
            "-c",
            "copy",  # 直接复制流，不重新编码
            "-y",  # 覆盖输出文件
            output_path,
        ]

        print(f"🎬 开始合并 {len(file_list)} 个视频文件...")
        print(f"📁 输出文件: {output_path}")

        # 执行ffmpeg命令
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ 视频合并成功!")
            return True
        else:
            print(f"❌ 视频合并失败:")
            print(f"错误信息: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ 执行ffmpeg时发生错误: {e}")
        return False
    finally:
        # 清理临时文件
        if os.path.exists(concat_file):
            os.unlink(concat_file)


def main():
    parser = argparse.ArgumentParser(
        description="合并美容视频剪辑",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
    python merge_beauty_clips.py --index 1
    python merge_beauty_clips.py --index 2 --dry-run
    
合并规则:
    1. 优先按数字顺序合并 (1.mp4, 2.mp4, 3.mp4...)
    2. 然后随机合并其他文件
    3. 自动排除Mac系统文件 (.DS_Store等)
        """,
    )

    parser.add_argument("--index", type=str, required=True, help="指定剪辑目录的索引")

    parser.add_argument(
        "--dry-run", action="store_true", help="试运行模式，只显示合并计划，不实际执行"
    )

    args = parser.parse_args()

    print("🎬 美容视频剪辑合并工具启动")
    print("=" * 60)

    # 检查系统
    if not check_supported_system():
        sys.exit(1)

    # 获取基础路径
    base_path = get_base_media_path()
    clips_dir = os.path.join(base_path, "clips", args.index)
    output_path = os.path.join(base_path, "mp4_low_res", f"{args.index}.mp4")

    print(f"🎯 开始处理索引: {args.index}")
    print(f"📂 剪辑目录: {clips_dir}")
    print(f"📁 输出路径: {output_path}")

    try:
        # 获取所有mp4文件
        mp4_files = get_mp4_files(clips_dir)

        if not mp4_files:
            print("❌ 没有找到任何mp4文件")
            sys.exit(1)

        print(f"📊 找到 {len(mp4_files)} 个mp4文件")

        # 解析数字文件和其他文件
        numbered_files, other_files = parse_numbered_files(mp4_files)

        print(f"🔢 数字命名文件: {len(numbered_files)} 个")
        print(f"🎲 其他文件: {len(other_files)} 个")

        # 构建最终的合并列表
        final_merge_list = []

        # 先添加数字文件（按顺序）
        if numbered_files:
            final_merge_list.extend(numbered_files)
            print("📋 数字文件合并顺序:")
            for i, file_path in enumerate(numbered_files, 1):
                filename = os.path.basename(file_path)
                print(f"   {i}. {filename}")

        # 随机排序其他文件并添加
        if other_files:
            random.shuffle(other_files)
            final_merge_list.extend(other_files)
            print("📋 随机文件合并顺序:")
            start_idx = len(numbered_files) + 1
            for i, file_path in enumerate(other_files, start_idx):
                filename = os.path.basename(file_path)
                print(f"   {i}. {filename}")

        # 显示总的合并计划
        print(f"\n📋 最终合并计划 (共 {len(final_merge_list)} 个文件):")
        for i, file_path in enumerate(final_merge_list, 1):
            filename = os.path.basename(file_path)
            print(f"   {i}. {filename}")

        if args.dry_run:
            print("\n🔍 试运行模式 - 未执行实际合并")
            return

        # 执行合并
        success = merge_videos(final_merge_list, output_path)

        if success:
            # 检查输出文件大小
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                size_mb = file_size / (1024 * 1024)
                print(f"📊 输出文件大小: {size_mb:.2f} MB")

            print(f"🎉 合并完成! 输出文件: {output_path}")
        else:
            print("❌ 合并失败")
            sys.exit(1)

    except Exception as e:
        print(f"❌ 发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
