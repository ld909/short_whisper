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
- 默认情况下处理所有语言，也可指定特定语言
- 默认启用句级分块模式，将chunk按句号进一步分割为单独的句子文件

📥 输入信息:
- Intel Mac输入目录: /Volumes/dhl/audio/books/{language}/summary/
- Apple Silicon Mac输入目录: /Users/donghaoliu/Documents/audio/books/{language}/summary/
- 支持文件格式: .txt 文件
- 文件编码: UTF-8
- 文件命名规则: {uuid}.txt

📤 输出信息:
- 输出根目录: /home/dhl/Documents/book/{language}/
- 完整输出路径格式: /home/dhl/Documents/book/{language}/{uuid}/{chunk_index}.txt
- 完整路径示例(中文): /home/dhl/Documents/book/zh/12345678-abcd-efgh-ijkl-123456789012/1.txt
- 完整路径示例(英文): /home/dhl/Documents/book/en/12345678-abcd-efgh-ijkl-123456789012/1.txt
- 按语言分目录存储，每个书籍有自己的子目录，按UUID命名
- 块级模式: 每个子目录内的文件按块索引命名（1.txt, 2.txt, 3.txt...）
- 句级模式: 每个子目录内的文件按句索引累加命名（1.txt, 2.txt, 3.txt...）

🔄 处理规则:
1. 将书籍总结分割成指定最大字符数的块
2. 每个块去除换行符，变成一大段话
3. 自动排除以点开头的Mac系统文件
4. 支持断点续传，跳过已处理的书籍
5. 中文模式下自动将阿拉伯数字转换为中文数字（如12→十二，199→一百九十九）
6. 中文模式下自动将英文逗号","替换为中文逗号"，"
7. 默认句级模式下，将每个chunk按句号进一步分割为单独的句子文件

💡 使用示例:
# 处理所有语言书籍总结（默认句级分块）
python chunk_book_summaries.py

# 处理英文书籍总结（默认句级分块）
python chunk_book_summaries.py --lang en

# 处理中文书籍总结（默认句级分块）
python chunk_book_summaries.py --lang zh

# 禁用句级分块，使用块级分块模式
python chunk_book_summaries.py --no-sentence-level

# 块级分块模式处理中文书籍
python chunk_book_summaries.py --lang zh --no-sentence-level

# 设置最大字符数
python chunk_book_summaries.py --max-chars 2500 --lang zh

# 预览模式（不实际处理，只显示会处理哪些文件）
python chunk_book_summaries.py --preview --lang en

# 禁用断点续传
python chunk_book_summaries.py --no-resume --lang zh

# 强制重新处理所有文件（推荐用于确保清理功能正常工作）
python chunk_book_summaries.py --force --lang zh

🔢 数字转换功能 (仅中文模式):
- 将文本中的阿拉伯数字自动转换为中文数字
- 支持数字范围: 0-9999999999999（万亿以内）
- 转换示例: 1→一, 12→十二, 199→一百九十九, 2024→二千零二十四
- 正确处理零: 305→三百零五, 1001→一千零一
- 适用于年份、页码、章节号等所有数字

# 指定输入目录
python chunk_book_summaries.py --input-dir /custom/path/to/summaries --lang en

# 指定输出目录
python chunk_book_summaries.py --output-dir /custom/output/path --lang zh
"""

import os
import glob
import argparse
import platform
import re
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


def get_default_output_dir(language="en"):
    """获取默认输出目录（按语言分类）"""
    return f"/home/dhl/Documents/book/{language}"


def arabic_to_chinese_number(text, debug=False):
    """
    将文本中的阿拉伯数字转换为中文数字

    支持的数字范围：0-9999999999999（万亿以内）

    Args:
        text (str): 包含阿拉伯数字的文本
        debug (bool): 是否显示调试信息

    Returns:
        str: 转换后的文本
    """

    def number_to_chinese(num):
        """
        将单个数字转换为中文数字

        Args:
            num (int): 阿拉伯数字

        Returns:
            str: 中文数字
        """
        if num == 0:
            return "零"

        # 中文数字字符
        chinese_digits = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"]
        chinese_units = ["", "十", "百", "千"]
        chinese_big_units = ["", "万", "亿", "万亿"]

        def convert_section(n):
            """转换0-9999内的数字"""
            if n == 0:
                return ""

            result = ""
            str_n = str(n)
            length = len(str_n)

            for i, digit in enumerate(str_n):
                digit_val = int(digit)
                pos = length - i - 1  # 位置（0为个位，1为十位...）

                if digit_val != 0:
                    # 处理"一十"的特殊情况
                    if digit_val == 1 and pos == 1 and length == 2:
                        result += "十"
                    else:
                        result += chinese_digits[digit_val]
                        if pos > 0:
                            result += chinese_units[pos]
                else:
                    # 处理零的情况
                    if result and i < length - 1:
                        # 检查后面是否还有非零数字
                        has_non_zero_after = any(int(d) != 0 for d in str_n[i + 1 :])
                        # 避免连续的"零"
                        if has_non_zero_after and not result.endswith("零"):
                            result += "零"

            return result

        # 处理负数
        if num < 0:
            return "负" + number_to_chinese(-num)

        # 分组处理：万亿、亿、万、个
        groups = []
        temp_num = num

        # 分解成各个组
        for i in range(4):  # 个、万、亿、万亿
            groups.append(temp_num % 10000)
            temp_num //= 10000
            if temp_num == 0:
                break

        result = ""
        for i, group in enumerate(reversed(groups)):
            if group != 0:
                group_text = convert_section(group)
                if group_text:
                    result += group_text
                    unit_index = len(groups) - 1 - i
                    if unit_index > 0:
                        result += chinese_big_units[unit_index]
            else:
                # 处理中间的零
                if result and i < len(groups) - 1:
                    # 检查是否需要添加零
                    remaining_groups = groups[: len(groups) - 1 - i]
                    if any(g != 0 for g in remaining_groups):
                        result += "零"

        return result if result else "零"

    # 查找所有数字并替换
    converted_count = 0

    def replace_number(match):
        nonlocal converted_count
        number_str = match.group(0)
        try:
            number = int(number_str)
            chinese_num = number_to_chinese(number)
            converted_count += 1
            if debug:
                print(f"         🔢 数字转换: {number_str} → {chinese_num}")
            return chinese_num
        except ValueError:
            return number_str

    # 使用正则表达式匹配数字（包括年份等）
    # 匹配所有连续的数字
    result = re.sub(r"\d+", replace_number, text)

    if debug and converted_count > 0:
        print(f"         📊 总共转换了 {converted_count} 个数字")

    return result


def clean_text_content(text, language="en", debug=False):
    """
    根据语言清理文本内容，去除不需要的符号

    Args:
        text (str): 原始文本
        language (str): 语言类型 (en/zh)
        debug (bool): 是否启用调试模式

    Returns:
        str: 清理后的文本
    """
    original_text = text

    # 统一处理所有引号（中文和英文主题都去除引号）
    # 定义所有可能的引号字符 - 使用Unicode码点确保字符正确
    quote_chars = [
        chr(0x0022),  # 标准英文双引号 " (U+0022)
        chr(0x0027),  # 标准英文单引号 ' (U+0027)
        chr(0x2018),  # 左单引号 ' (U+2018)
        chr(0x2019),  # 右单引号 ' (U+2019)
        chr(0x201C),  # 左双引号 " (U+201C) ★ 文件中实际使用的字符
        chr(0x201D),  # 右双引号 " (U+201D) ★ 文件中实际使用的字符
        chr(0x0060),  # 反引号 ` (U+0060)
        chr(0x00B4),  # 重音符 ´ (U+00B4)
        chr(0x201E),  # 德文双引号下标 „ (U+201E)
        chr(0x201A),  # 德文单引号下标 ‚ (U+201A)
        chr(0x00AB),  # 法文左引号 « (U+00AB)
        chr(0x00BB),  # 法文右引号 » (U+00BB)
        chr(0x2039),  # 单角引号左 ‹ (U+2039)
        chr(0x203A),  # 单角引号右 › (U+203A)
        chr(0x3008),  # 中文角括号左 〈 (U+3008)
        chr(0x3009),  # 中文角括号右 〉 (U+3009)
        chr(0x300A),  # 中文书名号左 《 (U+300A)
        chr(0x300B),  # 中文书名号右 》 (U+300B)
        chr(0x300C),  # 日文角引号左 「 (U+300C)
        chr(0x300D),  # 日文角引号右 」 (U+300D)
        chr(0x300E),  # 日文双角引号左 『 (U+300E)
        chr(0x300F),  # 日文双角引号右 』 (U+300F)
        chr(0x301D),  # 中文引号上标左 〝 (U+301D)
        chr(0x301E),  # 中文引号上标右 〞 (U+301E)
        chr(0x301F),  # 中文引号下标 〟 (U+301F)
        chr(0xFF02),  # 全角双引号 ＂ (U+FF02)
        chr(0xFF07),  # 全角单引号 ＇ (U+FF07)
    ]

    # 破折号处理 - 使用Unicode码点确保字符正确
    dash_chars = [
        chr(0x2014),  # 长破折号 — (em dash, U+2014)
        chr(0x2013),  # 短破折号 – (en dash, U+2013)
        chr(0x002D),  # 连字符 - (hyphen, U+002D)
        chr(0x2212),  # 减号 − (U+2212)
        chr(0x2010),  # 短连字符 ‐ (U+2010)
        chr(0x2011),  # 不断行连字符 ‑ (U+2011)
        chr(0x2043),  # 三角连字符 ⁃ (U+2043)
        chr(0xFE63),  # 全角连字符 ﹣ (U+FE63)
        chr(0xFF0D),  # 全角减号 － (U+FF0D)
        # 添加省略号（可能影响语音合成）
        chr(0x2026) + chr(0x2026),  # 中文省略号 …… (两个U+2026)
        chr(0x2026),  # 省略号 … (U+2026)
    ]

    removed_quotes = 0
    removed_dashes = 0
    removed_colons = 0
    replaced_commas = 0

    # 统一处理：中文和英文都去除所有引号
    for quote in quote_chars:
        if quote in text:
            count = text.count(quote)
            text = text.replace(quote, "")
            removed_quotes += count
            if debug and count > 0:
                print(f"         🔍 移除了 {count} 个 '{quote}' 字符")

    if language == "zh":
        # 中文处理：完全去除破折号和连字符
        for dash in dash_chars:
            if dash in text:
                count = text.count(dash)
                text = text.replace(dash, "")
                removed_dashes += count
                if debug and count > 0:
                    print(f"         🔍 移除了 {count} 个 '{dash}' 字符")

        # 中文模式下，去除冒号
        colon_chars = [":", "："]  # 英文冒号和中文冒号
        for colon in colon_chars:
            if colon in text:
                count = text.count(colon)
                text = text.replace(colon, "")
                removed_colons += count
                if debug and count > 0:
                    print(f"         🔍 移除了 {count} 个 '{colon}' 字符")

        # 中文模式下，将英文逗号替换为中文逗号
        if "," in text:
            count = text.count(",")
            text = text.replace(",", "，")
            replaced_commas += count
            if debug and count > 0:
                print(f"         🔍 替换了 {count} 个 ',' 为 '，'")

        # 中文模式下：将阿拉伯数字转换为中文数字
        text = arabic_to_chinese_number(text, debug)
    else:
        # 英文处理：破折号和连字符替换为空格
        for dash in dash_chars:
            if dash in text:
                count = text.count(dash)
                text = text.replace(dash, " ")
                removed_dashes += count
                if debug and count > 0:
                    print(f"         🔍 替换了 {count} 个 '{dash}' 为空格")

    # 清理多余空格
    text = " ".join(text.split())

    if debug:
        total_removed = len(original_text) - len(text)
        if language == "zh":
            print(
                f"         📊 清理统计: 引号{removed_quotes}个, 破折号{removed_dashes}个, 冒号{removed_colons}个, 逗号替换{replaced_commas}个, 总计处理了 {total_removed} 个字符"
            )
        else:
            print(
                f"         📊 清理统计: 引号{removed_quotes}个, 破折号{removed_dashes}个, 冒号{removed_colons}个, 总计清理了 {total_removed} 个字符"
            )

    return text.strip()


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


def split_chunk_into_sentences(chunk_content, language="en"):
    """
    将chunk内容按句号分割为单独的句子

    Args:
        chunk_content (str): 块内容
        language (str): 语言类型，用于选择合适的句号分隔符

    Returns:
        list: 句子列表
    """
    if not chunk_content.strip():
        return []

    # 根据语言选择句号分隔符
    if language == "zh":
        # 中文句号
        sentence_delimiters = ["。", "！", "？"]
    else:
        # 英文句号
        sentence_delimiters = [".", "!", "?"]

    # 使用正则表达式分割句子
    import re
    
    # 构建分割模式
    pattern = "|".join(re.escape(delimiter) for delimiter in sentence_delimiters)
    
    # 分割文本，保留分隔符
    sentences = re.split(f"({pattern})", chunk_content)
    
    # 重新组合句子和分隔符
    result_sentences = []
    for i in range(0, len(sentences), 2):
        if i < len(sentences):
            sentence = sentences[i].strip()
            if sentence:  # 只保留非空句子
                # 如果有分隔符，加上分隔符
                if i + 1 < len(sentences):
                    delimiter = sentences[i + 1]
                    sentence += delimiter
                result_sentences.append(sentence)
    
    # 过滤掉空句子和只有标点的句子
    filtered_sentences = []
    for sentence in result_sentences:
        sentence = sentence.strip()
        if sentence and len(sentence) > 1:  # 确保句子不只是标点符号
            filtered_sentences.append(sentence)
    
    return filtered_sentences


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


def process_single_summary(input_file, output_base_dir, max_chars=3000, language="en", sentence_level=False):
    """
    处理单个书籍总结文件，分割成块并保存

    Args:
        input_file (str): 输入总结文件路径
        output_base_dir (str): 输出基础目录
        max_chars (int): 每个块的最大字符数
        language (str): 语言类型，用于不同的文本处理规则
        sentence_level (bool): 是否启用句级分块模式

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
        total_chars_cleaned = 0
        total_files_saved = 0
        global_sentence_index = 0  # 全局句子计数器，从0开始

        for chunk_index, chunk_content in enumerate(chunks, 1):
            # 去掉换行符，变成一大段话
            chunk_content_no_newlines = chunk_content.replace("\n", " ").strip()

            # 清理文本内容，去除各种引号和符号
            chunk_content_cleaned = clean_text_content(
                chunk_content_no_newlines, language, debug=True
            )

            # 显示清理前后的详细对比
            original_length = len(chunk_content_no_newlines)
            cleaned_length = len(chunk_content_cleaned)
            chars_removed = original_length - cleaned_length

            if sentence_level:
                # 句级分块模式
                sentences = split_chunk_into_sentences(chunk_content_cleaned, language)
                
                print(
                    f"      📝 块 {chunk_index}: {original_length} → {cleaned_length} 字符 (清理了 {chars_removed} 个) → {len(sentences)} 句"
                )
                
                # 保存每个句子为单独的文件
                for sentence_index, sentence in enumerate(sentences, 1):
                    global_sentence_index += 1  # 累加全局句子计数器
                    sentence_filename = f"{global_sentence_index}.txt"
                    sentence_filepath = os.path.join(book_output_dir, sentence_filename)
                    
                    try:
                        with open(sentence_filepath, "w", encoding="utf-8") as f:
                            f.write(sentence.strip())
                        
                        sentence_size = len(sentence.strip())
                        print(f"         📄 句子 {global_sentence_index}: {sentence_size} 字符")
                        print(f"         💾 已保存到: {sentence_filepath}")
                        
                        # 显示句子预览
                        sentence_preview = sentence.strip()[:80] + ("..." if len(sentence.strip()) > 80 else "")
                        print(f"         📖 内容: {sentence_preview}")
                        
                        total_files_saved += 1
                        
                    except Exception as write_error:
                        print(f"         ❌ 写入句子文件失败: {write_error}")
                        return False, 0
                        
            else:
                # 块级分块模式（原有逻辑）
                chunk_filename = f"{chunk_index}.txt"
                chunk_filepath = os.path.join(book_output_dir, chunk_filename)

                # 总是显示每个chunk的处理信息
                print(
                    f"      📝 块 {chunk_index}: {original_length} → {cleaned_length} 字符 (清理了 {chars_removed} 个)"
                )

                # 如果有字符被清理，显示更详细的信息
                if chars_removed > 0:
                    print(f"         ✂️  成功清理了 {chars_removed} 个标点符号和特殊字符")
                    # 显示清理前后的片段对比（前50个字符）
                    before_preview = chunk_content_no_newlines[:100] + (
                        "..." if len(chunk_content_no_newlines) > 100 else ""
                    )
                    after_preview = chunk_content_cleaned[:100] + (
                        "..." if len(chunk_content_cleaned) > 100 else ""
                    )
                    print(f"         📄 清理前片段: {before_preview}")
                    print(f"         ✨ 清理后片段: {after_preview}")

                # 确保写入文件
                try:
                    with open(chunk_filepath, "w", encoding="utf-8") as f:
                        f.write(chunk_content_cleaned)
                    print(f"         💾 已保存到: {chunk_filepath}")

                    # 验证文件确实被写入
                    if os.path.exists(chunk_filepath):
                        actual_size = os.path.getsize(chunk_filepath)
                        print(f"         ✅ 文件大小: {actual_size} bytes")
                    else:
                        print(f"         ❌ 文件未找到: {chunk_filepath}")

                    total_files_saved += 1

                except Exception as write_error:
                    print(f"         ❌ 写入文件失败: {write_error}")
                    return False, 0

            chunk_sizes.append(len(chunk_content_cleaned))
            total_chars_cleaned += chars_removed

        total_chars = len(content)
        avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes)
        chunk_sizes_str = ", ".join([str(size) for size in chunk_sizes])

        if sentence_level:
            print(f"✅ {filename}: {len(chunks)} 个块 → {total_files_saved} 个句子文件 (总计 {total_chars} 字符)")
            print(f"   📁 UUID: {uuid_val}")
            print(f"   📊 块大小: [{chunk_sizes_str}] 字符, 平均: {avg_chunk_size:.0f} 字符")
            print(f"   📄 句子模式: 总计 {total_files_saved} 个句子文件")
            print(f"   🧹 总共清理了: {total_chars_cleaned} 个字符")
            print(f"   📂 输出目录: {book_output_dir}")
        else:
            print(f"✅ {filename}: {len(chunks)} 个块 (总计 {total_chars} 字符)")
            print(f"   📁 UUID: {uuid_val}")
            print(
                f"   📊 块大小: [{chunk_sizes_str}] 字符, 平均: {avg_chunk_size:.0f} 字符"
            )
            print(f"   🧹 总共清理了: {total_chars_cleaned} 个字符")
            print(f"   📂 输出目录: {book_output_dir}")

        return True, total_files_saved if sentence_level else len(chunks)

    except Exception as e:
        filename = os.path.basename(input_file)
        print(f"❌ 处理文件 {filename} 时出错: {e}")
        import traceback

        traceback.print_exc()
        return False, 0


def process_book_summaries(
    input_dir,
    output_dir,
    max_chars=3000,
    preview_mode=False,
    resume_mode=True,
    language="en",
    sentence_level=False,
):
    """
    处理所有书籍总结文件

    Args:
        input_dir (str): 输入目录
        output_dir (str): 输出目录
        max_chars (int): 每个块的最大字符数
        preview_mode (bool): 是否为预览模式
        resume_mode (bool): 是否启用断点续传
        language (str): 语言类型，用于不同的文本处理规则
        sentence_level (bool): 是否启用句级分块模式

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

        success, chunk_count = process_single_summary(
            input_file, output_dir, max_chars, language, sentence_level
        )

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
  python chunk_book_summaries.py                          # 处理所有语言书籍总结（默认句级分块）
  python chunk_book_summaries.py --lang en                # 处理英文书籍总结（默认句级分块）
  python chunk_book_summaries.py --lang zh                # 处理中文书籍总结（默认句级分块）
  python chunk_book_summaries.py --no-sentence-level      # 禁用句级分块，使用块级分块模式
  python chunk_book_summaries.py --lang zh --no-sentence-level # 块级分块模式处理中文书籍
  python chunk_book_summaries.py --max-chars 2500 --lang en # 设置最大字符数
  python chunk_book_summaries.py --preview --lang zh      # 预览模式
  python chunk_book_summaries.py --no-resume --lang en    # 禁用断点续传
  python chunk_book_summaries.py --force --lang zh        # 强制重新处理（推荐）
        """,
    )

    # 语言参数
    parser.add_argument(
        "--lang",
        "-l",
        choices=["en", "zh"],
        default=None,
        help="语言主题: en(英文) 或 zh(中文) [默认: 处理所有语言]",
    )

    # 获取默认输入和输出目录（现在需要语言参数，所以先解析参数）
    args_preview = parser.parse_known_args()[0]
    
    # 当没有指定语言时，使用英文作为默认来显示帮助信息
    preview_lang = args_preview.lang if args_preview.lang else "en"
    default_input_dir = get_default_input_dir(preview_lang)
    default_output_dir = get_default_output_dir(preview_lang)

    parser.add_argument(
        "--input-dir",
        default=None,
        help=f"输入目录路径 (默认: 根据语言自动选择)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=f"输出目录路径 (默认: 根据语言自动选择)",
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
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新处理所有文件，即使已存在（等同于--no-resume）",
    )
    parser.add_argument(
        "--sentence-level",
        action="store_true",
        default=True,
        help="启用句级分块模式，将每个chunk按句号进一步分割为单独的句子文件 [默认: 启用]",
    )
    parser.add_argument(
        "--no-sentence-level",
        action="store_true",
        help="禁用句级分块模式，使用块级分块模式",
    )

    args = parser.parse_args()

    max_chars = args.max_chars
    resume_mode = not (args.no_resume or args.force)
    # 句级分块模式：默认启用，但可以通过 --no-sentence-level 禁用
    sentence_level = args.sentence_level and not args.no_sentence_level
    
    # 确定要处理的语言列表
    if args.lang:
        languages_to_process = [args.lang]
    else:
        languages_to_process = ["en", "zh"]

    print(f"\n🎯 书籍总结分块器")
    print(f"🌍 语言主题: {', '.join(languages_to_process) if len(languages_to_process) > 1 else ('中文' if languages_to_process[0] == 'zh' else 'English')}")
    print(f"🖥️  系统类型: {platform.system()}")
    print(f"📊 最大字符数: {max_chars} 字符/块")
    print(f"🔄 断点续传: {'启用' if resume_mode else '禁用'}")
    print(f"📄 分块模式: {'句级分块 (默认)' if sentence_level else '块级分块'}")
    if args.force:
        print(f"💪 强制模式: 重新处理所有文件，确保清理功能正常执行")
    print(f"🚫 自动排除Mac系统文件 (.DS_Store等)")
    print(f"🧹 文本清理: 自动去除引号、破折号等标点符号")

    if args.preview:
        print(f"👁️  预览模式：只显示将要处理的文件")

    # 处理每种语言
    all_results = []
    
    for language in languages_to_process:
        lang_name = "中文" if language == "zh" else "English"
        print(f"\n" + "="*50)
        print(f"🌐 开始处理 {lang_name} 书籍总结")
        print(f"="*50)
        
        # 确定输入输出目录
        if args.input_dir:
            input_dir = args.input_dir
        else:
            input_dir = get_default_input_dir(language)
            
        if args.output_dir:
            output_dir = args.output_dir
        else:
            output_dir = get_default_output_dir(language)

        print(f"📁 输入目录: {input_dir}")
        print(f"📁 输出目录: {output_dir}")

        # 检查输入目录是否存在
        if not os.path.exists(input_dir):
            print(f"⚠️  输入目录不存在: {input_dir}")
            print("💡 请确保 generate_book_summary.py 已经运行并生成了总结文件")
            continue

        try:
            result = process_book_summaries(
                input_dir,
                output_dir,
                max_chars,
                args.preview,
                resume_mode,
                language,
                sentence_level,
            )
            result['language'] = language
            all_results.append(result)

        except Exception as e:
            print(f"❌ 处理 {lang_name} 时出错: {e}")
            import traceback
            traceback.print_exc()

    # 最终统计
    print(f"\n" + "="*50)
    print(f"🎉 所有语言处理完成总结")
    print(f"="*50)
    
    if all_results:
        total_books = sum(r['total'] for r in all_results)
        total_successful = sum(r['successful'] for r in all_results)
        total_failed = sum(r['failed'] for r in all_results)
        total_skipped = sum(r['skipped'] for r in all_results)
        total_chunks = sum(r['total_chunks'] for r in all_results)
        
        if args.preview:
            print(f"📊 预览统计:")
            for result in all_results:
                lang_name = "中文" if result['language'] == "zh" else "English"
                print(f"  {lang_name}:")
                print(f"    - 发现总结总数: {result['total']} 个")
                print(f"    - 需要处理: {result.get('preview', 0)} 个")
                print(f"    - 已处理跳过: {result['skipped']} 个")
        else:
            print(f"📊 汇总统计:")
            print(f"  - 总结总数: {total_books} 个")
            print(f"  - 成功处理: {total_successful} 个")
            print(f"  - 处理失败: {total_failed} 个")
            print(f"  - 跳过书籍: {total_skipped} 个")
            
            if sentence_level:
                print(f"  - 生成文件数: {total_chunks} 个句子文件")
            else:
                print(f"  - 生成块数: {total_chunks} 个")

            if total_books > 0:
                success_rate = (
                    (total_successful / (total_successful + total_failed))
                    * 100
                    if (total_successful + total_failed) > 0
                    else 0
                )
                print(f"  - 成功率: {success_rate:.1f}%")

                if total_successful > 0:
                    avg_chunks_per_book = total_chunks / total_successful
                    avg_label = "平均句子数/书籍" if sentence_level else "平均块数/书籍"
                    print(f"  - {avg_label}: {avg_chunks_per_book:.1f} 个")

            # 显示每种语言的详细统计
            print(f"\n📋 分语言统计:")
            for result in all_results:
                lang_name = "中文" if result['language'] == "zh" else "English"
                print(f"  {lang_name}: {result['successful']}/{result['total']} 成功")
                if result['successful'] > 0:
                    output_dir = get_default_output_dir(result['language'])
                    print(f"    📝 文件已保存到: {output_dir}")
                    if sentence_level:
                        print(f"    📁 目录结构: book/{result['language']}/<uuid>/<累加索引>.txt")
                    else:
                        print(f"    📁 目录结构: book/{result['language']}/<uuid>/<chunk_index>.txt")
    else:
        print(f"❌ 没有成功处理任何语言的书籍总结")


if __name__ == "__main__":
    main()
