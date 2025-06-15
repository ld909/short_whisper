#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多主题故事分块脚本
将 process_stories.py 处理后的故事文件分割成3000字符以内的块
每个块保存为单独的文件

📚 支持的主题:
- scifi: 科幻故事
- thriller: 惊悚故事
- horror: 恐怖故事
- romance: 爱情故事
- fantasy: 奇幻故事

📥 输入信息:
- 默认输入根目录: /media/dhl/audio/
- 各主题输入目录: /media/dhl/audio/{theme}/full_story_refine/
- 支持文件格式: .txt 文件
- 文件编码: UTF-8
- 文件命名规则: 数字.txt (例如: 1.txt, 2.txt, 3.txt...)

📤 输出信息:
- Ubuntu 系统输出根目录: /home/dhl/Documents/audio/chunks/
- Mac 系统输出根目录: /Volumes/dhl/audio/
- Ubuntu 输出目录结构: chunks/{theme}/{story_index}/{chunk_index}.txt
- Mac 输出目录结构: {theme}/story_chunks/{story_index}/{chunk_index}.txt
- 例如 Ubuntu: chunks/scifi/1/1.txt, chunks/scifi/1/2.txt...
- 例如 Mac: scifi/story_chunks/1/1.txt, scifi/story_chunks/1/2.txt...
- 每个故事有自己的子目录，按故事索引命名
- 每个子目录内的文件按块索引命名

🔄 处理规则:
1. 将故事分割成指定最大字符数的块
2. 每个块去除换行符，变成一大段话
3. 自动排除以点开头的Mac系统文件
4. 支持断点续传，跳过已处理的故事

💡 使用示例:
# 处理所有默认主题（scifi、thriller、horror、romance、fantasy）
python chunk_stories.py

# 处理指定主题
python chunk_stories.py --theme scifi
python chunk_stories.py --theme scifi,horror

# 指定自定义输入根目录
python chunk_stories.py --input-base-dir /custom/path

# 指定自定义输出根目录
python chunk_stories.py --output-base-dir /custom/output/path

# 处理单个文件
python chunk_stories.py --file /path/to/story.txt

# 设置最大字符数
python chunk_stories.py --max-chars 2500

# 预览模式（不实际处理，只显示会处理哪些文件）
python chunk_stories.py --preview

# 禁用断点续传
python chunk_stories.py --no-resume

# 查看所有支持的主题
python chunk_stories.py --list-themes
"""

import os
import glob
import argparse
import re
import platform
from pathlib import Path


# 支持的主题配置
SUPPORTED_THEMES = {
    "scifi": {
        "name": "科幻",
        "description": "科幻故事，包含未来科技、太空探索、时间旅行等元素",
    },
    "thriller": {"name": "惊悚", "description": "惊悚故事，包含紧张刺激、悬念等元素"},
    "horror": {"name": "恐怖", "description": "恐怖故事，包含惊悚、悬疑、超自然等元素"},
    "romance": {
        "name": "爱情",
        "description": "爱情故事，包含浪漫情节、感情发展等元素",
    },
    "fantasy": {
        "name": "奇幻",
        "description": "奇幻故事，包含魔法、龙、精灵等奇幻元素",
    },
}

# 默认处理的主题列表
DEFAULT_THEMES = ["scifi", "thriller", "horror", "romance", "fantasy"]

# 默认路径配置
DEFAULT_INPUT_BASE_DIR = "/media/dhl/audio"
DEFAULT_OUTPUT_BASE_DIR = "/home/dhl/Documents/audio/chunks"


def check_supported_system():
    """
    检查是否为支持的系统 (Ubuntu 或 macOS)

    Returns:
        tuple: (是否支持, 系统类型)
    """
    try:
        system = platform.system()

        if system == "Linux":
            # 检查是否为Ubuntu
            try:
                with open("/etc/os-release", "r") as f:
                    content = f.read()
                    if "Ubuntu" in content or "ubuntu" in content:
                        return True, "ubuntu"
            except:
                pass
            return False, "linux"
        elif system == "Darwin":
            return True, "mac"
        else:
            return False, system.lower()
    except:
        return False, "unknown"


def get_default_paths(system_type):
    """
    根据系统类型获取默认路径配置

    Args:
        system_type (str): 系统类型 ("ubuntu" 或 "mac")

    Returns:
        tuple: (默认输入基础目录, 默认输出基础目录)
    """
    if system_type == "ubuntu":
        input_base_dir = "/media/dhl/audio"
        output_base_dir = "/home/dhl/Documents/audio/chunks"
    elif system_type == "mac":
        input_base_dir = "/Volumes/dhl/audio"
        output_base_dir = "/Volumes/dhl/audio"  # Mac 输出到同一根目录下
    else:
        # 使用 Ubuntu 默认值作为兜底
        input_base_dir = "/media/dhl/audio"
        output_base_dir = "/home/dhl/Documents/audio/chunks"

    return input_base_dir, output_base_dir


def split_story_into_chunks(content, max_chars=3000):
    """
    将故事内容分割成指定最大字符数的块，严格遵守字符数限制

    Args:
        content (str): 故事内容
        max_chars (int): 每个块的最大字符数

    Returns:
        list: 分割后的文本块列表
    """
    content = content.strip()
    if not content:
        return []

    chunks = []
    lines = content.split("\n")
    current_chunk = []
    current_char_count = 0

    for line in lines:
        line = line.strip()
        if not line:  # 跳过空行
            continue
            
        # 如果单行就超过限制，需要分割这一行
        if len(line) > max_chars:
            # 先保存当前块（如果有内容）
            if current_chunk:
                chunk_text = "\n".join(current_chunk).strip()
                if chunk_text:
                    chunks.append(chunk_text)
                current_chunk = []
                current_char_count = 0
            
            # 分割长行
            while len(line) > max_chars:
                # 尝试在句号、感叹号、问号处分割
                split_pos = max_chars
                for punct in ['。', '！', '？', '.', '!', '?']:
                    pos = line.rfind(punct, 0, max_chars)
                    if pos > max_chars * 0.7:  # 至少要有70%的长度
                        split_pos = pos + 1
                        break
                
                # 如果没找到合适的标点，就在空格处分割
                if split_pos == max_chars:
                    space_pos = line.rfind(' ', 0, max_chars)
                    if space_pos > max_chars * 0.7:
                        split_pos = space_pos
                
                chunk_part = line[:split_pos].strip()
                if chunk_part:
                    chunks.append(chunk_part)
                line = line[split_pos:].strip()
            
            # 处理剩余部分
            if line:
                current_chunk = [line]
                current_char_count = len(line)
            continue

        # 检查加入这一行是否会超过限制
        line_length = len(line)
        if current_char_count > 0:
            # 需要考虑换行符的长度
            needed_length = current_char_count + 1 + line_length  # +1 for newline
        else:
            needed_length = line_length

        if needed_length > max_chars and current_chunk:
            # 超过限制，保存当前块并开始新块
            chunk_text = "\n".join(current_chunk).strip()
            if chunk_text:
                chunks.append(chunk_text)
            current_chunk = [line]
            current_char_count = line_length
        else:
            # 可以加入当前块
            current_chunk.append(line)
            current_char_count = needed_length

    # 处理最后一个块
    if current_chunk:
        chunk_text = "\n".join(current_chunk).strip()
        if chunk_text:
            chunks.append(chunk_text)

    return chunks


def get_theme_directories(input_base_dir, output_base_dir, theme, system_type="ubuntu"):
    """
    获取指定主题的输入和输出目录

    Args:
        input_base_dir (str): 输入基础目录
        output_base_dir (str): 输出基础目录
        theme (str): 主题名称
        system_type (str): 系统类型

    Returns:
        tuple: (输入目录, 输出目录)
    """
    input_dir = os.path.join(input_base_dir, theme, "full_story_refine")

    if system_type == "mac":
        # Mac 系统使用 /Volumes/dhl/audio/theme/story_chunks/ 结构
        output_dir = os.path.join(output_base_dir, theme, "story_chunks")
    else:
        # Ubuntu 系统使用原有的 chunks 结构
        output_dir = os.path.join(output_base_dir, theme)

    return input_dir, output_dir


def get_story_files(input_dir):
    """
    获取输入目录中的所有故事文件
    排除以点开头的Mac系统meta文件

    Args:
        input_dir (str): 输入目录路径

    Returns:
        list: 故事文件路径列表
    """
    if not os.path.exists(input_dir):
        return []

    # 查找所有 .txt 文件
    pattern = os.path.join(input_dir, "*.txt")
    all_txt_files = glob.glob(pattern)

    # 过滤掉以点开头的文件（Mac系统meta文件）
    story_files = []
    skipped_files = []
    for filepath in all_txt_files:
        basename = os.path.basename(filepath)
        if not basename.startswith("."):
            story_files.append(filepath)
        else:
            skipped_files.append(basename)

    if skipped_files:
        print(f"🚫 跳过 {len(skipped_files)} 个Mac系统文件: {', '.join(skipped_files)}")

    # 按文件名中的数字排序
    def extract_number(filepath):
        basename = os.path.basename(filepath)
        try:
            # 提取文件名中的数字部分
            number_str = basename.split(".")[0]
            return int(number_str)
        except:
            return 0

    story_files.sort(key=extract_number)
    return story_files


def get_processed_stories(output_dir):
    """
    获取已处理的故事列表（用于断点续传）

    Args:
        output_dir (str): 输出目录路径

    Returns:
        set: 已处理的故事索引集合
    """
    if not os.path.exists(output_dir):
        return set()

    processed_stories = set()

    # 遍历输出目录中的所有子目录
    for item in os.listdir(output_dir):
        item_path = os.path.join(output_dir, item)
        if os.path.isdir(item_path) and not item.startswith("."):
            # 检查是否为有效的故事目录（只包含数字）
            try:
                story_index = int(item)
                # 检查目录中是否有chunk文件
                chunk_files = glob.glob(os.path.join(item_path, "*.txt"))
                if chunk_files:
                    processed_stories.add(story_index)
            except ValueError:
                continue

    return processed_stories


def process_single_story(input_file, output_base_dir, max_chars=3000, theme_name=""):
    """
    处理单个故事文件，分割成块并保存

    Args:
        input_file (str): 输入故事文件路径
        output_base_dir (str): 输出基础目录
        max_chars (int): 每个块的最大字符数
        theme_name (str): 主题名称（用于显示）

    Returns:
        tuple: (成功标志, 块数量)
    """
    try:
        # 读取故事文件
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            filename = os.path.basename(input_file)
            prefix = f"[{theme_name}] " if theme_name else ""
            print(f"⚠️  {prefix}文件为空: {filename}")
            return False, 0

        # 从文件名提取故事索引
        filename = os.path.basename(input_file)
        story_index = filename.split(".")[0]  # 假设文件名格式为 "数字.txt"

        # 创建故事专用目录
        story_output_dir = os.path.join(output_base_dir, story_index)
        os.makedirs(story_output_dir, exist_ok=True)

        # 分割故事
        chunks = split_story_into_chunks(content, max_chars)

        if not chunks:
            prefix = f"[{theme_name}] " if theme_name else ""
            print(f"⚠️  {prefix}无法分割文件: {filename}")
            return False, 0

        # 保存每个块并显示每个块的信息
        chunk_sizes = []
        for chunk_index, chunk_content in enumerate(chunks, 1):
            chunk_filename = f"{chunk_index}.txt"
            chunk_filepath = os.path.join(story_output_dir, chunk_filename)

            # 去掉换行符，变成一大段话
            chunk_content_no_newlines = chunk_content.replace("\n", " ").strip()

            with open(chunk_filepath, "w", encoding="utf-8") as f:
                f.write(chunk_content_no_newlines)

            chunk_sizes.append(len(chunk_content_no_newlines))

        total_chars = len(content)
        avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes)
        chunk_sizes_str = ", ".join([str(size) for size in chunk_sizes])

        prefix = f"[{theme_name}] " if theme_name else ""
        print(f"✅ {prefix}{filename}: {len(chunks)} 个块 (总计 {total_chars} 字符)")
        print(f"   块大小: [{chunk_sizes_str}] 字符, 平均: {avg_chunk_size:.0f} 字符")

        return True, len(chunks)

    except Exception as e:
        filename = os.path.basename(input_file)
        prefix = f"[{theme_name}] " if theme_name else ""
        print(f"❌ {prefix}处理文件 {filename} 时出错: {e}")
        return False, 0


def process_theme(
    theme,
    input_base_dir,
    output_base_dir,
    max_chars=3000,
    preview_mode=False,
    resume_mode=True,
    system_type="ubuntu",
):
    """
    处理指定主题的所有故事文件

    Args:
        theme (str): 主题名称
        input_base_dir (str): 输入基础目录
        output_base_dir (str): 输出基础目录
        max_chars (int): 每个块的最大字符数
        preview_mode (bool): 是否为预览模式
        resume_mode (bool): 是否启用断点续传
        system_type (str): 系统类型

    Returns:
        dict: 处理结果统计
    """
    theme_name = SUPPORTED_THEMES[theme]["name"]
    input_dir, output_dir = get_theme_directories(
        input_base_dir, output_base_dir, theme, system_type
    )

    print(f"\n=== 🎭 处理{theme_name}主题 ({theme}) ===")
    print(f"📁 输入目录: {input_dir}")
    print(f"📁 输出目录: {output_dir}")

    # 获取所有故事文件
    story_files = get_story_files(input_dir)

    if not story_files:
        print(f"❌ 在目录 {input_dir} 中未找到任何 .txt 文件")
        return {
            "theme": theme,
            "theme_name": theme_name,
            "total": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_chunks": 0,
        }

    print(f"📊 找到 {len(story_files)} 个{theme_name}故事文件")

    # 获取已处理的故事（断点续传）
    processed_stories = set()
    skipped_count = 0

    if resume_mode:
        processed_stories = get_processed_stories(output_dir)
        if processed_stories:
            print(f"🔄 断点续传模式：发现 {len(processed_stories)} 个已处理的故事")

    # 筛选需要处理的文件
    files_to_process = []
    for input_file in story_files:
        filename = os.path.basename(input_file)
        try:
            story_index = int(filename.split(".")[0])
            if resume_mode and story_index in processed_stories:
                skipped_count += 1
                if not preview_mode:
                    print(f"⏭️  跳过已处理故事: {filename}")
            else:
                files_to_process.append(input_file)
        except ValueError:
            # 如果文件名不是数字格式，仍然处理
            files_to_process.append(input_file)

    if skipped_count > 0:
        print(
            f"📋 跳过 {skipped_count} 个已处理故事，还需处理 {len(files_to_process)} 个故事"
        )

    if not files_to_process:
        print(f"✅ {theme_name}主题的所有故事都已处理完成")
        return {
            "theme": theme,
            "theme_name": theme_name,
            "total": len(story_files),
            "successful": len(story_files) - skipped_count,
            "failed": 0,
            "skipped": skipped_count,
            "total_chunks": 0,
        }

    if preview_mode:
        print(f"\n📋 预览模式 - {theme_name}主题将要处理的故事:")
        for i, input_file in enumerate(files_to_process, 1):
            filename = os.path.basename(input_file)
            story_index = filename.split(".")[0]
            story_output_dir = os.path.join(output_dir, story_index)
            print(f"  {i:2d}. {filename}")
            print(f"      输入: {input_file}")
            print(f"      输出目录: {story_output_dir}")
        return {
            "theme": theme,
            "theme_name": theme_name,
            "total": len(story_files),
            "successful": 0,
            "failed": 0,
            "skipped": skipped_count,
            "preview": len(files_to_process),
            "total_chunks": 0,
        }

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n🔄 开始处理{theme_name}主题的 {len(files_to_process)} 个故事...")

    successful_count = 0
    failed_count = 0
    total_chunks = 0

    for i, input_file in enumerate(files_to_process, 1):
        filename = os.path.basename(input_file)

        print(f"\n[{theme_name}] 处理第 {i}/{len(files_to_process)} 个故事: {filename}")

        success, chunk_count = process_single_story(
            input_file, output_dir, max_chars, theme_name
        )

        if success:
            successful_count += 1
            total_chunks += chunk_count
        else:
            failed_count += 1

    # 返回处理结果
    return {
        "theme": theme,
        "theme_name": theme_name,
        "total": len(story_files),
        "successful": successful_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "total_chunks": total_chunks,
    }


def list_themes():
    """列出所有支持的主题"""
    print("\n=== 📚 支持的主题列表 ===")
    for theme_id, theme_info in SUPPORTED_THEMES.items():
        print(f"  {theme_id}: {theme_info['name']}")
        print(f"    描述: {theme_info['description']}")
    print()


def validate_themes(theme_list):
    """验证主题列表是否有效"""
    invalid_themes = []
    for theme in theme_list:
        if theme not in SUPPORTED_THEMES:
            invalid_themes.append(theme)

    if invalid_themes:
        print(f"❌ 不支持的主题: {', '.join(invalid_themes)}")
        list_themes()
        return False

    return True


def main():
    """主函数"""
    # 首先检查是否为支持的系统
    supported, system_type = check_supported_system()
    if not supported:
        print(f"❌ 此脚本只能在 {system_type} 系统上运行！")
        print("🖥️  当前系统: " + platform.system())
        exit(1)

    print(f"✅ {system_type}系统检测通过")

    parser = argparse.ArgumentParser(
        description="多主题故事分块器 - 将故事分割成指定字符数的块",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
支持的主题:
  scifi    - 科幻故事
  thriller - 惊悚故事  
  horror   - 恐怖故事
  romance  - 爱情故事
  fantasy  - 奇幻故事

使用示例:
  python chunk_stories.py                           # 处理所有默认主题
  python chunk_stories.py --theme scifi            # 处理科幻主题
  python chunk_stories.py --theme scifi,horror     # 处理多个主题
  python chunk_stories.py --max-chars 2500         # 设置最大字符数
  python chunk_stories.py --preview                # 预览模式
  python chunk_stories.py --no-resume              # 禁用断点续传
        """,
    )

    parser.add_argument(
        "--theme",
        "-t",
        help="要处理的主题，用逗号分隔多个主题 (默认: scifi,thriller,horror,romance,fantasy)",
    )
    # 获取当前系统的默认路径
    default_input_dir, default_output_dir = get_default_paths(system_type)

    parser.add_argument(
        "--input-base-dir",
        default=default_input_dir,
        help=f"输入基础目录路径 (默认: {default_input_dir})",
    )
    parser.add_argument(
        "--output-base-dir",
        default=default_output_dir,
        help=f"输出基础目录路径 (默认: {default_output_dir})",
    )
    parser.add_argument(
        "--max-chars", type=int, default=3000, help="每个块的最大字符数 (默认: 3000)"
    )
    parser.add_argument("--file", help="处理单个文件（指定此参数时忽略其他参数）")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="预览模式，只显示会处理哪些文件，不实际处理",
    )
    parser.add_argument(
        "--no-resume", action="store_true", help="禁用断点续传，重新处理所有故事"
    )
    parser.add_argument("--list-themes", action="store_true", help="列出所有支持的主题")

    args = parser.parse_args()

    # 显示支持的主题
    if args.list_themes:
        list_themes()
        return

    # 处理单个文件
    if args.file:
        input_file = args.file
        if not os.path.exists(input_file):
            print(f"❌ 指定的文件不存在: {input_file}")
            return

        output_base_dir = args.output_base_dir

        if args.preview:
            print(f"\n📋 预览模式 - 将要处理的文件:")
            filename = os.path.basename(input_file)
            story_index = filename.split(".")[0]
            story_output_dir = os.path.join(output_base_dir, "single_file", story_index)
            print(f"  输入: {input_file}")
            print(f"  输出目录: {story_output_dir}")
            return

        print(f"\n🔄 开始处理单个文件...")
        single_file_output_dir = os.path.join(output_base_dir, "single_file")
        success, chunk_count = process_single_story(
            input_file, single_file_output_dir, args.max_chars
        )

        if success:
            print(f"✅ 文件处理完成! 生成了 {chunk_count} 个块")
        else:
            print(f"❌ 文件处理失败!")

        return

    # 确定要处理的主题
    if args.theme:
        # 解析用户指定的主题
        theme_list = [theme.strip() for theme in args.theme.split(",")]
        if not validate_themes(theme_list):
            return
    else:
        # 默认处理所有主题
        theme_list = DEFAULT_THEMES.copy()

    # 使用用户指定的路径或默认路径
    input_base_dir = args.input_base_dir
    output_base_dir = args.output_base_dir
    max_chars = args.max_chars
    resume_mode = not args.no_resume

    print(f"\n🎯 多主题故事分块器")
    print(f"📁 输入基础目录: {input_base_dir}")
    print(f"📁 输出基础目录: {output_base_dir}")
    print(f"📊 最大字符数: {max_chars} 字符/块")
    print(
        f"🎭 处理主题: {', '.join([SUPPORTED_THEMES[t]['name'] for t in theme_list])}"
    )
    print(f"🔄 断点续传: {'启用' if resume_mode else '禁用'}")
    print(f"🚫 自动排除Mac系统文件 (.DS_Store等)")

    if args.preview:
        print(f"👁️  预览模式：只显示将要处理的文件")

    # 处理所有主题
    all_results = []

    for theme in theme_list:
        try:
            result = process_theme(
                theme,
                input_base_dir,
                output_base_dir,
                max_chars,
                args.preview,
                resume_mode,
                system_type,
            )
            all_results.append(result)
        except Exception as e:
            theme_name = SUPPORTED_THEMES[theme]["name"]
            print(f"❌ 处理{theme_name}主题时出错: {e}")
            import traceback

            traceback.print_exc()

    # 统计总结果
    if all_results:
        print(f"\n=== 🎉 处理完成总结 ===")

        total_files = sum(r["total"] for r in all_results)
        total_successful = sum(r["successful"] for r in all_results)
        total_failed = sum(r["failed"] for r in all_results)
        total_skipped = sum(r["skipped"] for r in all_results)
        total_chunks = sum(r["total_chunks"] for r in all_results)

        if args.preview:
            total_preview = sum(r.get("preview", 0) for r in all_results)
            print(f"📊 预览统计:")
            print(f"  - 发现故事总数: {total_files} 个")
            print(f"  - 需要处理: {total_preview} 个")
            print(f"  - 已处理跳过: {total_skipped} 个")

            print(f"\n📋 各主题详情:")
            for result in all_results:
                preview_count = result.get("preview", 0)
                print(
                    f"  - {result['theme_name']}: 发现 {result['total']} 个，需处理 {preview_count} 个，跳过 {result['skipped']} 个"
                )
        else:
            print(f"📊 处理统计:")
            print(f"  - 故事总数: {total_files} 个")
            print(f"  - 成功处理: {total_successful} 个")
            print(f"  - 处理失败: {total_failed} 个")
            print(f"  - 跳过故事: {total_skipped} 个")
            print(f"  - 生成块数: {total_chunks} 个")

            if total_files > 0:
                success_rate = (
                    (total_successful / (total_successful + total_failed)) * 100
                    if (total_successful + total_failed) > 0
                    else 0
                )
                print(f"  - 成功率: {success_rate:.1f}%")

                if total_successful > 0:
                    avg_chunks_per_story = total_chunks / total_successful
                    print(f"  - 平均块数/故事: {avg_chunks_per_story:.1f} 个")

            print(f"\n📋 各主题详情:")
            for result in all_results:
                print(
                    f"  - {result['theme_name']}: 成功 {result['successful']} 个，失败 {result['failed']} 个，跳过 {result['skipped']} 个，生成 {result['total_chunks']} 块"
                )

            if total_successful > 0:
                print(f"\n📝 分块后的文件已保存到: {output_base_dir}")
                if system_type == "mac":
                    print(
                        "📁 目录结构: <theme>/story_chunks/<story_index>/<chunk_index>.txt"
                    )
                else:
                    print("📁 目录结构: chunks/<theme>/<story_index>/<chunk_index>.txt")


if __name__ == "__main__":
    main()
