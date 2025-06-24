#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍总结分块脚本
将 generate_book_summary.py 生成的书籍总结文件分割成3000字符以内的块
每个块保存为单独的文件

📚 功能说明:
- 读取 generate_book_summary.py 输出的书籍总结文件
- 将每个总结分割成指定字符数的块
- 自动排除Mac系统产生的点开头文件
- 支持断点续传，跳过已处理的文件
- 支持中文(zh)和英文(en)两种语言主题

📥 输入信息:
- Intel Mac输入目录: /Volumes/dhl/audio/books/{language}/summary/
- Apple Silicon Mac输入目录: /Users/donghaoliu/Documents/audio/books/{language}/summary/
- 支持文件格式: .txt 文件
- 文件编码: UTF-8
- 文件命名规则: {uuid}.txt

📤 输出信息:
- 输出根目录: /home/dhl/Documents/book/
- 完整输出路径格式: /home/dhl/Documents/book/{uuid}/{chunk_index}.txt
- 完整路径示例: /home/dhl/Documents/book/12345678-abcd-efgh-ijkl-123456789012/1.txt
- 每个书籍有自己的子目录，按UUID命名
- 每个子目录内的文件按块索引命名（1.txt, 2.txt, 3.txt...）

🔄 处理规则:
1. 将书籍总结分割成指定最大字符数的块
2. 每个块去除换行符，变成一大段话
3. 自动排除以点开头的Mac系统文件
4. 支持断点续传，跳过已处理的书籍

💡 使用示例:
# 处理英文书籍总结
python chunk_book_summaries.py --lang en

# 处理中文书籍总结
python chunk_book_summaries.py --lang zh

# 设置最大字符数
python chunk_book_summaries.py --max-chars 2500 --lang zh

# 预览模式（不实际处理，只显示会处理哪些文件）
python chunk_book_summaries.py --preview --lang en

# 禁用断点续传
python chunk_book_summaries.py --no-resume --lang zh

# 指定输入目录
python chunk_book_summaries.py --input-dir /custom/path/to/summaries --lang en

# 指定输出目录
python chunk_book_summaries.py --output-dir /custom/output/path --lang zh
"""

import os
import glob
import argparse
import platform
from pathlib import Path


def get_base_media_path():
    """根据系统类型返回基础媒体路径（与generate_book_summary.py保持一致）"""
    if platform.system() == "Darwin":  # macOS
        machine = platform.machine().lower()
        processor = platform.processor().lower()
        # Apple Silicon (M芯片)
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
    elif platform.system() == "Linux":  # Linux/Ubuntu
        # 在Linux系统上使用 /mnt/dhl/audio 路径
        return "/mnt/dhl/audio"
    return "/Users/donghaoliu/Documents/audio"  # 默认


def get_default_input_dir(language="en"):
    """获取默认输入目录"""
    base_path = get_base_media_path()
    return os.path.join(base_path, "books", language, "summary")


def split_content_into_chunks(content, max_chars=3000):
    """
    将内容分割成指定最大字符数的块，严格遵守字符数限制

    Args:
        content (str): 内容
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
                for punct in ["。", "！", "？", ".", "!", "?"]:
                    pos = line.rfind(punct, 0, max_chars)
                    if pos > max_chars * 0.7:  # 至少要有70%的长度
                        split_pos = pos + 1
                        break

                # 如果没找到合适的标点，就在空格处分割
                if split_pos == max_chars:
                    space_pos = line.rfind(" ", 0, max_chars)
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


def get_summary_files(input_dir):
    """
    获取输入目录中的所有书籍总结文件
    排除以点开头的Mac系统meta文件

    Args:
        input_dir (str): 输入目录路径

    Returns:
        list: 总结文件路径列表
    """
    if not os.path.exists(input_dir):
        return []

    # 查找所有 .txt 文件
    pattern = os.path.join(input_dir, "*.txt")
    all_txt_files = glob.glob(pattern)

    # 过滤掉以点开头的文件（Mac系统meta文件）
    summary_files = []
    skipped_files = []
    for filepath in all_txt_files:
        basename = os.path.basename(filepath)
        if not basename.startswith("."):
            summary_files.append(filepath)
        else:
            skipped_files.append(basename)

    if skipped_files:
        print(f"🚫 跳过 {len(skipped_files)} 个Mac系统文件: {', '.join(skipped_files)}")

    # 按文件名排序
    summary_files.sort()
    return summary_files


def get_processed_books(output_dir):
    """
    获取已处理的书籍列表（用于断点续传）

    Args:
        output_dir (str): 输出目录路径

    Returns:
        set: 已处理的书籍UUID集合
    """
    if not os.path.exists(output_dir):
        return set()

    processed_books = set()

    # 遍历输出目录中的所有子目录
    for item in os.listdir(output_dir):
        item_path = os.path.join(output_dir, item)
        if os.path.isdir(item_path) and not item.startswith("."):
            # 检查目录中是否有chunk文件
            chunk_files = glob.glob(os.path.join(item_path, "*.txt"))
            if chunk_files:
                processed_books.add(item)

    return processed_books


def extract_uuid_from_filename(filename):
    """
    从文件名中提取UUID

    Args:
        filename (str): 文件名

    Returns:
        str: UUID值，如果提取失败返回None
    """
    # 去掉.txt后缀
    if filename.endswith(".txt"):
        uuid_val = filename[:-4]
        # 简单验证UUID格式（36字符，包含4个连字符）
        if len(uuid_val) == 36 and uuid_val.count("-") == 4:
            return uuid_val
    return None


def process_single_summary(input_file, output_base_dir, max_chars=3000):
    """
    处理单个书籍总结文件，分割成块并保存

    Args:
        input_file (str): 输入总结文件路径
        output_base_dir (str): 输出基础目录
        max_chars (int): 每个块的最大字符数

    Returns:
        tuple: (成功标志, 块数量)
    """
    try:
        # 读取总结文件
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            filename = os.path.basename(input_file)
            print(f"⚠️  文件为空: {filename}")
            return False, 0

        # 从文件名提取UUID
        filename = os.path.basename(input_file)
        uuid_val = extract_uuid_from_filename(filename)

        if not uuid_val:
            print(f"⚠️  无法从文件名提取UUID: {filename}")
            return False, 0

        # 创建书籍专用目录
        book_output_dir = os.path.join(output_base_dir, uuid_val)
        os.makedirs(book_output_dir, exist_ok=True)

        # 分割总结
        chunks = split_content_into_chunks(content, max_chars)

        if not chunks:
            print(f"⚠️  无法分割文件: {filename}")
            return False, 0

        # 保存每个块并显示每个块的信息
        chunk_sizes = []
        for chunk_index, chunk_content in enumerate(chunks, 1):
            chunk_filename = f"{chunk_index}.txt"
            chunk_filepath = os.path.join(book_output_dir, chunk_filename)

            # 去掉换行符，变成一大段话，并替换所有"-"为空格
            chunk_content_no_newlines = (
                chunk_content.replace("\n", " ").replace("-", " ").strip()
            )

            with open(chunk_filepath, "w", encoding="utf-8") as f:
                f.write(chunk_content_no_newlines)

            chunk_sizes.append(len(chunk_content_no_newlines))

        total_chars = len(content)
        avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes)
        chunk_sizes_str = ", ".join([str(size) for size in chunk_sizes])

        print(f"✅ {filename}: {len(chunks)} 个块 (总计 {total_chars} 字符)")
        print(f"   UUID: {uuid_val}")
        print(f"   块大小: [{chunk_sizes_str}] 字符, 平均: {avg_chunk_size:.0f} 字符")

        return True, len(chunks)

    except Exception as e:
        filename = os.path.basename(input_file)
        print(f"❌ 处理文件 {filename} 时出错: {e}")
        return False, 0


def process_book_summaries(
    input_dir,
    output_dir,
    max_chars=3000,
    preview_mode=False,
    resume_mode=True,
):
    """
    处理所有书籍总结文件

    Args:
        input_dir (str): 输入目录
        output_dir (str): 输出目录
        max_chars (int): 每个块的最大字符数
        preview_mode (bool): 是否为预览模式
        resume_mode (bool): 是否启用断点续传

    Returns:
        dict: 处理结果统计
    """
    print(f"\n=== 📚 处理书籍总结分块 ===")
    print(f"📁 输入目录: {input_dir}")
    print(f"📁 输出目录: {output_dir}")

    # 获取所有总结文件
    summary_files = get_summary_files(input_dir)

    if not summary_files:
        print(f"❌ 在目录 {input_dir} 中未找到任何 .txt 文件")
        return {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_chunks": 0,
        }

    print(f"📊 找到 {len(summary_files)} 个书籍总结文件")

    # 获取已处理的书籍（断点续传）
    processed_books = set()
    skipped_count = 0

    if resume_mode:
        processed_books = get_processed_books(output_dir)
        if processed_books:
            print(f"🔄 断点续传模式：发现 {len(processed_books)} 个已处理的书籍")

    # 筛选需要处理的文件
    files_to_process = []
    for input_file in summary_files:
        filename = os.path.basename(input_file)
        uuid_val = extract_uuid_from_filename(filename)

        if not uuid_val:
            print(f"⚠️  跳过无效文件名: {filename}")
            continue

        if resume_mode and uuid_val in processed_books:
            skipped_count += 1
            if not preview_mode:
                print(f"⏭️  跳过已处理书籍: {filename}")
        else:
            files_to_process.append(input_file)

    if skipped_count > 0:
        print(
            f"📋 跳过 {skipped_count} 个已处理书籍，还需处理 {len(files_to_process)} 个"
        )

    if not files_to_process:
        print(f"✅ 所有书籍总结都已处理完成")
        return {
            "total": len(summary_files),
            "successful": len(summary_files) - skipped_count,
            "failed": 0,
            "skipped": skipped_count,
            "total_chunks": 0,
        }

    if preview_mode:
        print(f"\n📋 预览模式 - 将要处理的书籍总结:")
        for i, input_file in enumerate(files_to_process, 1):
            filename = os.path.basename(input_file)
            uuid_val = extract_uuid_from_filename(filename)
            book_output_dir = os.path.join(output_dir, uuid_val)
            print(f"  {i:2d}. {filename}")
            print(f"      UUID: {uuid_val}")
            print(f"      输入: {input_file}")
            print(f"      输出目录: {book_output_dir}")
        return {
            "total": len(summary_files),
            "successful": 0,
            "failed": 0,
            "skipped": skipped_count,
            "preview": len(files_to_process),
            "total_chunks": 0,
        }

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n🔄 开始处理 {len(files_to_process)} 个书籍总结...")

    successful_count = 0
    failed_count = 0
    total_chunks = 0

    for i, input_file in enumerate(files_to_process, 1):
        filename = os.path.basename(input_file)

        print(f"\n处理第 {i}/{len(files_to_process)} 个总结: {filename}")

        success, chunk_count = process_single_summary(input_file, output_dir, max_chars)

        if success:
            successful_count += 1
            total_chunks += chunk_count
        else:
            failed_count += 1

    # 返回处理结果
    return {
        "total": len(summary_files),
        "successful": successful_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "total_chunks": total_chunks,
    }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="书籍总结分块器 - 将书籍总结分割成指定字符数的块",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  python chunk_book_summaries.py --lang en                # 处理英文书籍总结
  python chunk_book_summaries.py --lang zh                # 处理中文书籍总结
  python chunk_book_summaries.py --max-chars 2500 --lang en # 设置最大字符数
  python chunk_book_summaries.py --preview --lang zh      # 预览模式
  python chunk_book_summaries.py --no-resume --lang en    # 禁用断点续传
        """,
    )

    # 语言参数
    parser.add_argument(
        "--lang",
        "-l",
        choices=["en", "zh"],
        default="en",
        help="语言主题: en(英文) 或 zh(中文) [默认: en]",
    )

    # 获取默认输入和输出目录（现在需要语言参数，所以先解析参数）
    args_preview = parser.parse_known_args()[0]
    default_input_dir = get_default_input_dir(args_preview.lang)
    default_output_dir = "/home/dhl/Documents/book"

    parser.add_argument(
        "--input-dir",
        default=default_input_dir,
        help=f"输入目录路径 (默认: {default_input_dir})",
    )
    parser.add_argument(
        "--output-dir",
        default=default_output_dir,
        help=f"输出目录路径 (默认: {default_output_dir})",
    )
    parser.add_argument(
        "--max-chars", type=int, default=3000, help="每个块的最大字符数 (默认: 3000)"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="预览模式，只显示会处理哪些文件，不实际处理",
    )
    parser.add_argument(
        "--no-resume", action="store_true", help="禁用断点续传，重新处理所有书籍"
    )

    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir
    max_chars = args.max_chars
    resume_mode = not args.no_resume
    language = args.lang

    # 如果用户没有手动指定input_dir，重新计算正确的路径
    if args.input_dir == default_input_dir:
        input_dir = get_default_input_dir(language)

    lang_name = "中文" if language == "zh" else "English"

    print(f"\n🎯 书籍总结分块器")
    print(f"🌍 语言主题: {lang_name}")
    print(f"🖥️  系统类型: {platform.system()}")
    print(f"📁 输入目录: {input_dir}")
    print(f"📁 输出目录: {output_dir}")
    print(f"📊 最大字符数: {max_chars} 字符/块")
    print(f"🔄 断点续传: {'启用' if resume_mode else '禁用'}")
    print(f"🚫 自动排除Mac系统文件 (.DS_Store等)")

    if args.preview:
        print(f"👁️  预览模式：只显示将要处理的文件")

    # 检查输入目录是否存在
    if not os.path.exists(input_dir):
        print(f"❌ 输入目录不存在: {input_dir}")
        print("💡 请确保 generate_book_summary.py 已经运行并生成了总结文件")
        return

    try:
        result = process_book_summaries(
            input_dir,
            output_dir,
            max_chars,
            args.preview,
            resume_mode,
        )

        # 最终统计
        print(f"\n=== 🎉 处理完成总结 ===")

        if args.preview:
            print(f"📊 预览统计:")
            print(f"  - 发现总结总数: {result['total']} 个")
            print(f"  - 需要处理: {result.get('preview', 0)} 个")
            print(f"  - 已处理跳过: {result['skipped']} 个")
        else:
            print(f"📊 处理统计:")
            print(f"  - 总结总数: {result['total']} 个")
            print(f"  - 成功处理: {result['successful']} 个")
            print(f"  - 处理失败: {result['failed']} 个")
            print(f"  - 跳过书籍: {result['skipped']} 个")
            print(f"  - 生成块数: {result['total_chunks']} 个")

            if result["total"] > 0:
                success_rate = (
                    (result["successful"] / (result["successful"] + result["failed"]))
                    * 100
                    if (result["successful"] + result["failed"]) > 0
                    else 0
                )
                print(f"  - 成功率: {success_rate:.1f}%")

                if result["successful"] > 0:
                    avg_chunks_per_book = result["total_chunks"] / result["successful"]
                    print(f"  - 平均块数/书籍: {avg_chunks_per_book:.1f} 个")

            if result["successful"] > 0:
                print(f"\n📝 分块后的文件已保存到: {output_dir}")
                print("📁 目录结构: book/<uuid>/<chunk_index>.txt")

    except Exception as e:
        print(f"❌ 处理过程中出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
