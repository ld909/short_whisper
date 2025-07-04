#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍 1080p MP4 Clip 生成工具

功能说明:
此脚本用于生成书籍的 1080p MP4 宣传片段，布局为：
- 左半边: 静态封面图片 (来自 upscale_book_thumbnails.py 输出)
- 右半边上部分: 书籍标题 (白色字体，黑色背景)
- 右半边下部分: 放大的 MP4 素材 (来自 assets 目录)
- 右侧视频上叠加: "Book summary" 文字 (绿色，Merriweather字体，居中对齐)

智能标题处理:
1. 自动检测中文/英文，采用不同换行策略
2. 固定字体大小模式：保持指定字体大小，长标题自动换行
3. 智能溢出防护：如果标题过长导致溢出，自动使用省略号
4. 中文按字符换行，英文按单词换行
5. 支持按标点符号边界智能截断
6. 可调节标题距离上边沿的距离，解决多行标题布局过紧的问题

省略号处理策略:
- 优先保留标题前半部分的完整性
- 中文：在标点符号(，。！？；：)后截断
- 英文：在单词边界截断
- 智能估算最佳长度，避免过度截断
- 保证最终显示不溢出屏幕边界

主要功能:
1. 自动扫描超分后的书籍封面图片 (thumbnails_large 目录)
2. 读取对应的书籍信息获取标题
3. 合成左右布局的 1080p 视频
4. 在右侧视频上叠加绿色"Book summary"文字（使用Merriweather字体）
5. 支持断点续传，跳过已处理的文件
6. 自动跳过Mac系统生成的点开头文件
7. 支持中文和英文两种语言
8. 智能防溢出，长标题自动省略

输入:
- 封面图片: /mnt/dhl/audio/books/{lang}/thumbnails_large/*.png
- 书籍信息: /mnt/dhl/audio/books/{lang}/info/*.json
- 背景视频: audio_ficition/books/assets/plate_upscaled.mp4
- 字体文件: audio_ficition/books/font/{lang}/*.ttf

输出:
- 输出目录: /mnt/dhl/audio/books/{lang}/1080_clips/
- 命名规则: [uuid].mp4

使用方法:
1. 默认处理英文书籍: python generate_book_clips.py
2. 处理中文书籍: python generate_book_clips.py --language zh
3. 固定字体大小: python generate_book_clips.py --language zh --fixed-font-size --font-size 56
4. 强制重新处理: python generate_book_clips.py --force --language en
5. 调试模式: python generate_book_clips.py --debug --language zh

推荐中文用法:
python generate_book_clips.py --language zh --fixed-font-size --font-size 48 --debug

处理流程:
1. 扫描 thumbnails_large 目录中的所有超分封面图片
2. 读取对应的书籍信息 JSON 文件获取标题
3. 智能处理标题长度和溢出问题
4. 使用 FFmpeg 合成左右布局的 1080p 视频
5. 保存到 1080_clips 目录

注意:
- 需要安装 FFmpeg 和相关 Python 库
- 1080p 分辨率 (1920x1080)
- 左右各占 960px 宽度
- 右边上下分配需要根据标题长度动态调整
- 自动跳过点开头的系统文件
- 支持中英文两种语言的书籍处理
- 支持 macOS (Intel/Apple Silicon) 和 Linux/Ubuntu 系统
- 长标题会智能使用省略号，确保不溢出屏幕
"""

import os
import sys
import json
import time
import argparse
import glob
import re
import platform
import logging
import subprocess
import shutil
from pathlib import Path
from tqdm import tqdm
from typing import Optional, List, Tuple, Dict

from PIL import Image, ImageDraw, ImageFont
import cv2

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def check_supported_system():
    """
    检查是否为支持的系统

    Returns:
        tuple: (是否支持, 系统类型描述)
    """
    system = platform.system()

    if system == "Darwin":  # macOS
        machine = platform.machine()
        if machine == "x86_64":
            return True, "macOS (Intel)"
        else:
            return True, "macOS (Apple Silicon)"
    elif system == "Linux":
        try:
            # 检查是否为Ubuntu
            with open("/etc/os-release", "r") as f:
                content = f.read()
                if "Ubuntu" in content or "ubuntu" in content:
                    return True, "Ubuntu"
                else:
                    return True, "Linux"
        except:
            return True, "Linux"
    else:
        # 其他系统也支持，但可能需要手动配置路径
        return True, system


# 保持向后兼容性
def check_ubuntu_system():
    """
    检查是否为Ubuntu系统（保持向后兼容性）

    Returns:
        bool: 是否为支持的系统
    """
    supported, _ = check_supported_system()
    return supported


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()

    if system == "Darwin":  # macOS
        # 检测芯片架构
        machine = platform.machine()
        if machine == "x86_64":
            # Intel Mac
            return "/Volumes/dhl/audio"
        else:
            # Apple Silicon (arm64)
            return "/Users/donghaoliu/Documents/audio"
    elif system == "Linux":
        # Ubuntu/Linux
        return "/media/dhl/audio"
    else:
        # 其他系统给出提示，让用户手动配置
        logger.warning(f"⚠️ 未明确支持的操作系统: {system}")
        logger.warning("💡 请手动设置AUDIO_BASE_DIR环境变量或修改代码中的路径配置")
        # 检查是否设置了环境变量
        env_path = os.environ.get("AUDIO_BASE_DIR")
        if env_path:
            logger.info(f"✅ 使用环境变量路径: {env_path}")
            return env_path
        return None  # 返回None让调用者处理


def get_script_dir():
    """获取脚本所在目录"""
    return os.path.dirname(os.path.abspath(__file__))


def get_input_directories(language="en"):
    """
    获取输入目录路径

    Args:
        language: 语言代码 (en/zh)

    Returns:
        dict: 包含各种输入目录路径的字典
    """
    base_media_path = get_base_media_path()
    if not base_media_path:
        return {}

    # 根据语言设置基础路径
    base_path = os.path.join(base_media_path, "books", language)

    return {
        "thumbnails_large": os.path.join(base_path, "thumbnails_large"),
        "info": os.path.join(base_path, "info"),
        "assets": os.path.join(get_script_dir(), "assets"),
        "font": os.path.join(get_script_dir(), "font", language),
    }


def get_output_directory(language="en"):
    """
    获取输出目录路径

    Args:
        language: 语言代码 (en/zh)

    Returns:
        str: 输出目录路径
    """
    base_media_path = get_base_media_path()
    if not base_media_path:
        return ""

    return os.path.join(base_media_path, "books", language, "1080_clips")


def check_dependencies():
    """检查必要的依赖是否安装"""
    dependencies = ["ffmpeg", "ffprobe"]
    missing = []

    for dep in dependencies:
        if not shutil.which(dep):
            missing.append(dep)

    if missing:
        print(f"❌ 缺少依赖: {', '.join(missing)}")
        print("请安装 FFmpeg:")
        system = platform.system()
        if system == "Darwin":
            print("macOS: brew install ffmpeg")
        elif system == "Linux":
            print("Ubuntu/Linux: sudo apt install ffmpeg")
        else:
            print("请根据您的操作系统安装 FFmpeg")
        return False

    return True


def get_video_info(video_path: str) -> Dict:
    """获取视频文件信息"""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as e:
        logger.error(f"❌ 获取视频信息失败: {e}")
        return {}


def get_available_books(language="en") -> List[Tuple[str, str]]:
    """
    获取可用的书籍列表 (包含超分封面的书籍)

    Args:
        language: 语言代码 (en/zh)

    Returns:
        书籍信息元组列表: [(封面图片路径, UUID)]
    """
    directories = get_input_directories(language)
    thumbnails_dir = directories.get("thumbnails_large", "")

    if not thumbnails_dir or not os.path.exists(thumbnails_dir):
        print(f"❌ 超分封面目录不存在: {thumbnails_dir}")
        return []

    # 获取所有PNG文件
    png_files = glob.glob(os.path.join(thumbnails_dir, "*.png"))

    # 过滤掉点开头的系统文件
    valid_books = []
    for png_file in png_files:
        basename = os.path.basename(png_file)

        # 跳过点开头的文件
        if basename.startswith("."):
            continue

        # 提取UUID
        uuid_match = re.match(r"([a-f0-9\-]+)\.png", basename)
        if uuid_match:
            uuid = uuid_match.group(1)
            valid_books.append((png_file, uuid))

    # 按UUID排序
    valid_books.sort(key=lambda x: x[1])

    print(f"📁 找到 {len(valid_books)} 个包含超分封面的书籍")
    return valid_books


def get_book_info(uuid: str, language="en") -> Optional[Dict]:
    """
    根据UUID获取书籍信息

    Args:
        uuid: 书籍UUID
        language: 语言代码 (en/zh)

    Returns:
        书籍信息字典，失败时返回None
    """
    directories = get_input_directories(language)
    info_file = os.path.join(directories.get("info", ""), f"{uuid}.json")

    if not os.path.exists(info_file):
        logger.warning(f"⚠️ 书籍信息文件不存在: {info_file}")
        return None

    try:
        with open(info_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"❌ 读取书籍信息失败: {e}")
        return None


def get_available_fonts(language="en") -> List[str]:
    """
    获取可用的字体文件列表

    Args:
        language: 语言代码 (en/zh)

    Returns:
        list: 字体文件路径列表
    """
    directories = get_input_directories(language)
    font_dir = directories.get("font", "")

    if not font_dir or not os.path.exists(font_dir):
        logger.warning(f"⚠️ 字体目录不存在: {font_dir}")
        return []

    # 获取所有TTF字体文件
    font_files = glob.glob(os.path.join(font_dir, "*.ttf"))
    font_files.extend(glob.glob(os.path.join(font_dir, "*.TTF")))

    return font_files


def select_font_by_path_or_weight(
    font_path: Optional[str] = None,
    font_weight: Optional[str] = None,
    language: str = "en",
) -> str:
    """
    根据字体路径或权重选择字体

    Args:
        font_path: 指定的字体文件路径，优先使用
        font_weight: 字体权重 (extra-light, light, regular, medium, semi-bold, bold, extra-bold)
        language: 语言代码 (en/zh)

    Returns:
        选中的字体文件路径
    """
    # 如果指定了字体路径，直接使用
    if font_path:
        if os.path.exists(font_path):
            print(f"🔤 使用指定字体: {os.path.basename(font_path)}")
            return font_path
        else:
            logger.warning(f"⚠️ 指定的字体文件不存在: {font_path}，将使用默认字体")

    # 获取可用字体列表
    font_files = get_available_fonts(language)
    if not font_files:
        logger.error("❌ 未找到任何字体文件")
        return ""

    # 如果指定了字体权重，尝试匹配
    if font_weight:
        # 字体权重映射 (基于Oxanium字体系列和中文字体)
        if language == "en":
            weight_mapping = {
                "extra-light": ["ExtraLight", "extralight", "100", "200"],
                "light": ["Light", "light", "300"],
                "regular": ["Regular", "regular", "normal", "400"],
                "medium": ["Medium", "medium", "500"],
                "semi-bold": ["SemiBold", "semibold", "semi-bold", "600"],
                "bold": ["Bold", "bold", "700"],
                "extra-bold": ["ExtraBold", "extrabold", "extra-bold", "800", "900"],
            }
        else:  # 中文字体权重映射
            weight_mapping = {
                "light": ["Light", "light", "细", "W1", "W2"],
                "regular": ["Regular", "regular", "normal", "标准", "W3", "W4"],
                "medium": ["Medium", "medium", "中等", "W5"],
                "semi-bold": ["SemiBold", "semibold", "半粗", "W6"],
                "bold": ["Bold", "bold", "粗", "黑", "W7"],
                "extra-bold": ["ExtraBold", "extrabold", "特粗", "W8", "W9"],
            }

        # 规范化权重名称
        normalized_weight = font_weight.lower().replace("_", "-")

        # 查找匹配的字体文件
        for font_file in font_files:
            font_basename = os.path.basename(font_file).lower()

            # 检查是否匹配指定权重
            if normalized_weight in weight_mapping:
                for pattern in weight_mapping[normalized_weight]:
                    if pattern.lower() in font_basename:
                        print(
                            f"🔤 根据权重 '{font_weight}' 选择字体: {os.path.basename(font_file)}"
                        )
                        return font_file

        logger.warning(f"⚠️ 未找到匹配权重 '{font_weight}' 的字体，使用默认字体")

    # 默认使用第一个字体，优先选择Regular或Medium
    if language == "en":
        preferred_weights = ["regular", "medium", "semi-bold", "bold"]
    else:  # 中文字体优先选择
        preferred_weights = ["regular", "标准", "medium", "中等", "semi-bold", "半粗"]

    for weight in preferred_weights:
        for font_file in font_files:
            if weight in os.path.basename(font_file).lower():
                print(f"🔤 使用默认字体: {os.path.basename(font_file)}")
                return font_file

    # 如果没有找到首选字体，使用第一个
    selected_font = font_files[0]
    print(f"🔤 使用第一个可用字体: {os.path.basename(selected_font)}")
    return selected_font


def get_background_video(language="en") -> Optional[str]:
    """获取背景视频路径"""
    directories = get_input_directories(language)
    assets_dir = directories.get("assets", "")

    if not assets_dir:
        return None

    # 优先使用超分后的视频
    upscaled_video = os.path.join(assets_dir, "plate_upscaled.mp4")
    if os.path.exists(upscaled_video):
        return upscaled_video

    # 备用原始视频
    original_video = os.path.join(assets_dir, "plate.mp4")
    if os.path.exists(original_video):
        return original_video

    logger.error(f"❌ 未找到背景视频文件在: {assets_dir}")
    return None


def get_merriweather_font_path(language="en") -> Optional[str]:
    """
    获取适合的字体路径（英文使用Merriweather，中文使用合适的中文字体）

    Args:
        language: 语言代码 (en/zh)

    Returns:
        str: 字体文件路径，如果没找到返回None
    """
    directories = get_input_directories(language)
    font_dir = directories.get("font", "")

    if not font_dir or not os.path.exists(font_dir):
        logger.warning(f"⚠️ 字体目录不存在: {font_dir}")
        return None

    # 查找字体文件
    font_files = glob.glob(os.path.join(font_dir, "*.ttf"))
    font_files.extend(glob.glob(os.path.join(font_dir, "*.TTF")))

    if language == "en":
        # 英文：查找M开头的字体文件，优先选择Merriweather
        m_fonts = [f for f in font_files if os.path.basename(f).lower().startswith("m")]
        merriweather_fonts = [f for f in m_fonts if "merriweather" in f.lower()]

        if merriweather_fonts:
            selected_font = merriweather_fonts[0]
            logger.info(f"🔤 找到Merriweather字体: {os.path.basename(selected_font)}")
            return selected_font
        elif m_fonts:
            selected_font = m_fonts[0]
            logger.info(f"🔤 找到M开头字体: {os.path.basename(selected_font)}")
            return selected_font
    else:  # language == "zh"
        # 中文：使用任何可用的中文字体
        if font_files:
            selected_font = font_files[0]
            logger.info(f"🔤 找到中文字体: {os.path.basename(selected_font)}")
            return selected_font

    logger.warning(f"⚠️ 未找到合适的字体文件在: {font_dir}")
    return None


def process_title_for_overflow(
    title: str,
    draw: ImageDraw.Draw,
    font_path: str,
    font_size: int,
    max_width: int,
    max_height: int,
    debug: bool = False,
    fixed_font_size: bool = False,  # 新增：是否固定字体大小
) -> Tuple[str, int, bool]:
    """
    智能处理标题溢出问题

    Args:
        title: 原始标题
        draw: ImageDraw对象
        font_path: 字体文件路径
        font_size: 初始字体大小
        max_width: 标题区域最大宽度
        max_height: 标题区域最大高度
        debug: 是否启用调试模式
        fixed_font_size: 是否固定字体大小（不动态调整，允许换行）

    Returns:
        tuple: (处理后的标题, 最终字体大小, 是否进行了处理)
    """
    processed = False
    processed_title = title
    current_font_size = font_size

    # 辅助函数：计算文本是否溢出
    def will_text_overflow(text: str, font_sz: int) -> Tuple[bool, int, int, int]:
        """
        检查文本是否会溢出
        Returns: (是否溢出, 文本宽度, 文本高度, 行数)
        """
        font = ImageFont.truetype(font_path, font_sz)

        # 分词换行计算
        import re

        has_chinese = bool(re.search(r"[\u4e00-\u9fff]", text))

        lines = []
        max_line_width = 0

        if has_chinese:
            # 中文换行：逐字符处理
            current_line = ""
            for char in text:
                test_line = current_line + char
                bbox = draw.textbbox((0, 0), test_line, font=font)
                test_width = bbox[2] - bbox[0]

                if test_width <= max_width - 40:  # 留40px边距
                    current_line = test_line
                    max_line_width = max(max_line_width, test_width)
                else:
                    if current_line:
                        lines.append(current_line)
                        current_line = char
                    else:
                        lines.append(char)  # 单个字符也强制加入

                    # 计算当前字符的宽度
                    bbox = draw.textbbox((0, 0), char, font=font)
                    char_width = bbox[2] - bbox[0]
                    max_line_width = max(max_line_width, char_width)

            if current_line:
                lines.append(current_line)
                bbox = draw.textbbox((0, 0), current_line, font=font)
                line_width = bbox[2] - bbox[0]
                max_line_width = max(max_line_width, line_width)
        else:
            # 英文换行：按单词处理
            words = text.split()
            current_line = ""

            for word in words:
                test_line = current_line + " " + word if current_line else word
                bbox = draw.textbbox((0, 0), test_line, font=font)
                test_width = bbox[2] - bbox[0]

                if test_width <= max_width - 40:  # 留40px边距
                    current_line = test_line
                    max_line_width = max(max_line_width, test_width)
                else:
                    if current_line:
                        lines.append(current_line)
                        current_line = word
                    else:
                        lines.append(word)  # 单词太长也强制加入

                    # 计算当前词的宽度
                    bbox = draw.textbbox((0, 0), word, font=font)
                    word_width = bbox[2] - bbox[0]
                    max_line_width = max(max_line_width, word_width)

            if current_line:
                lines.append(current_line)
                bbox = draw.textbbox((0, 0), current_line, font=font)
                line_width = bbox[2] - bbox[0]
                max_line_width = max(max_line_width, line_width)

        # 计算总高度
        bbox = draw.textbbox((0, 0), "A", font=font)
        line_height = bbox[3] - bbox[1] + 5  # 加5px行间距
        total_height = len(lines) * line_height

        # 判断是否溢出（宽度或高度）
        width_overflow = max_line_width > max_width - 40
        height_overflow = total_height > max_height

        return (
            width_overflow or height_overflow,
            max_line_width,
            total_height,
            len(lines),
        )

    if debug:
        print(f"🔍 开始处理标题溢出检测: '{title}'")
        print(f"   区域限制: 宽度={max_width}px, 高度={max_height}px")
        print(f"   初始字体大小: {font_size}px")
        print(f"   固定字体大小模式: {'是' if fixed_font_size else '否'}")

    # 步骤1: 检查原始标题是否溢出
    overflow, text_width, text_height, line_count = will_text_overflow(
        processed_title, current_font_size
    )

    if debug:
        print(
            f"   原始标题检测: 溢出={'是' if overflow else '否'}, 宽度={text_width}px, 高度={text_height}px, 行数={line_count}"
        )

    if not overflow:
        # 原始标题没有溢出，直接返回
        if debug:
            print(f"✅ 标题无需处理，直接使用")
        return processed_title, current_font_size, False

    # 如果启用固定字体大小模式，保持字体大小但检查溢出，必要时使用省略号
    if fixed_font_size:
        if debug:
            print(f"🔒 固定字体大小模式：保持{font_size}px字体，检查溢出并智能处理")

        # 检查原始标题是否溢出
        if not overflow:
            if debug:
                print(f"✅ 原始标题无溢出，直接使用")
            return title, font_size, False

        # 溢出了，需要使用省略号处理
        if debug:
            print(f"⚠️ 原始标题溢出，开始省略号处理")

        # 检查是否包含中文字符
        import re

        has_chinese = bool(re.search(r"[\u4e00-\u9fff]", title))
        ellipsis = "..." if not has_chinese else "..."  # 中英文都用...

        # 智能缩短标题直到不溢出
        processed_title = title
        min_length = 3  # 最少保留字符数

        # 先估算需要的大概长度（粗略估算）
        original_length = len(title)
        target_lines = max_height // (font_size + 5)  # 估算最大行数
        chars_per_line = (max_width - 40) // (font_size * 0.6)  # 粗略估算每行字符数
        estimated_max_chars = int(target_lines * chars_per_line * 0.8)  # 保守估计

        if debug:
            print(
                f"   估算参数: 原长度={original_length}, 目标行数≤{target_lines}, 每行约{chars_per_line:.1f}字符"
            )
            print(f"   估算最大字符数: {estimated_max_chars}")

        # 如果估算长度远小于原长度，直接跳到估算长度附近开始测试
        if estimated_max_chars > 0 and estimated_max_chars < original_length * 0.7:
            processed_title = title[: max(estimated_max_chars, min_length)]
            if debug:
                print(f"   快速定位到估算长度: '{processed_title}'")

        # 逐步精确调整
        while len(processed_title) > min_length:
            # 尝试添加省略号
            test_title = processed_title + ellipsis

            # 检查是否还溢出
            test_overflow, test_width, test_height, test_lines = will_text_overflow(
                test_title, font_size
            )

            if debug:
                print(
                    f"   测试标题长度{len(test_title)}: 溢出={'是' if test_overflow else '否'}, 高度={test_height}px/{max_height}px, 行数={test_lines}"
                )

            if not test_overflow:
                # 找到合适的长度
                if debug:
                    print(f"✅ 省略号处理成功: '{test_title}'")
                return test_title, font_size, True

            # 继续缩短，智能选择缩短长度
            if has_chinese:
                # 中文：尝试按标点符号边界或字符截断
                shorter_length = len(processed_title) - 1
                # 寻找合适的截断点（标点符号后）
                punctuation_chars = "，。！？；：、）】』」"
                for i in range(
                    len(processed_title) - 1, max(len(processed_title) - 5, 0), -1
                ):
                    if processed_title[i] in punctuation_chars:
                        shorter_length = i + 1
                        break
                processed_title = processed_title[:shorter_length]
            else:
                # 英文：尝试按单词边界截断
                words = processed_title.split()
                if len(words) > 1:
                    processed_title = " ".join(words[:-1])  # 删除最后一个单词
                else:
                    processed_title = processed_title[:-1]  # 按字符删除

        # 如果缩短到很短还是溢出，使用最短安全版本
        safe_title = title[:min_length] + ellipsis
        if debug:
            print(f"⚠️ 使用最短安全版本: '{safe_title}'")
        return safe_title, font_size, True

    # 步骤2: 如果溢出，尝试按冒号分割
    if ":" in processed_title:
        # 取冒号前的部分
        title_before_colon = processed_title.split(":")[0].strip()

        if debug:
            print(f"📝 尝试冒号分割: '{title_before_colon}'")

        # 检查分割后的标题是否还溢出
        overflow_after_split, text_width, text_height, line_count = will_text_overflow(
            title_before_colon, current_font_size
        )

        if debug:
            print(
                f"   分割后检测: 溢出={'是' if overflow_after_split else '否'}, 宽度={text_width}px, 高度={text_height}px, 行数={line_count}"
            )

        if not overflow_after_split:
            # 分割后不溢出，使用分割后的标题
            processed_title = title_before_colon
            processed = True
            if debug:
                print(f"✅ 冒号分割成功，使用: '{processed_title}'")
            return processed_title, current_font_size, processed
        else:
            # 分割后仍然溢出，使用分割后的标题继续后续处理
            processed_title = title_before_colon
            processed = True
            if debug:
                print(f"⚠️ 冒号分割后仍溢出，继续字体调整: '{processed_title}'")

    # 步骤3: 如果仍然溢出，按step=2减少字体大小
    min_font_size = 12  # 最小字体大小
    step = 2

    while current_font_size > min_font_size:
        current_font_size -= step
        if current_font_size < min_font_size:
            current_font_size = min_font_size

        overflow_after_resize, text_width, text_height, line_count = will_text_overflow(
            processed_title, current_font_size
        )

        if debug:
            print(
                f"   字体调整至{current_font_size}px: 溢出={'是' if overflow_after_resize else '否'}, 宽度={text_width}px, 高度={text_height}px, 行数={line_count}"
            )

        if not overflow_after_resize:
            # 找到合适的字体大小
            processed = True
            if debug:
                print(f"✅ 字体调整成功，最终字体大小: {current_font_size}px")
            break

        if current_font_size <= min_font_size:
            # 已到最小字体大小，检查是否还溢出，如果是则使用省略号
            processed = True
            if debug:
                print(f"⚠️ 已达最小字体大小({min_font_size}px)")

            # 检查最小字体大小是否还溢出
            final_overflow, _, _, _ = will_text_overflow(processed_title, min_font_size)
            if final_overflow:
                if debug:
                    print(f"⚠️ 最小字体仍溢出，启用省略号处理")

                # 使用省略号处理逻辑
                import re

                has_chinese = bool(re.search(r"[\u4e00-\u9fff]", processed_title))
                ellipsis = "..."

                # 逐步缩短直到不溢出
                test_title = processed_title
                min_length = 3

                while len(test_title) > min_length:
                    test_with_ellipsis = test_title + ellipsis
                    test_overflow, _, _, _ = will_text_overflow(
                        test_with_ellipsis, min_font_size
                    )

                    if not test_overflow:
                        processed_title = test_with_ellipsis
                        processed = True
                        if debug:
                            print(f"✅ 省略号处理成功: '{processed_title}'")
                        break

                    # 智能缩短
                    if has_chinese:
                        # 中文按标点或字符截断
                        shorter_length = len(test_title) - 1
                        punctuation_chars = "，。！？；：、）】』」"
                        for i in range(
                            len(test_title) - 1, max(len(test_title) - 5, 0), -1
                        ):
                            if test_title[i] in punctuation_chars:
                                shorter_length = i + 1
                                break
                        test_title = test_title[:shorter_length]
                    else:
                        # 英文按单词边界截断
                        words = test_title.split()
                        if len(words) > 1:
                            test_title = " ".join(words[:-1])
                        else:
                            test_title = test_title[:-1]

                # 如果循环结束还没找到合适长度，使用最短版本
                if len(test_title) <= min_length:
                    processed_title = processed_title[:min_length] + ellipsis
                    if debug:
                        print(f"⚠️ 使用最短安全版本: '{processed_title}'")

            break

    if debug:
        final_overflow, final_width, final_height, final_lines = will_text_overflow(
            processed_title, current_font_size
        )
        print(
            f"🎯 最终结果: 标题='{processed_title}', 字体={current_font_size}px, 溢出={'是' if final_overflow else '否'}"
        )
        print(
            f"   最终尺寸: 宽度={final_width}px, 高度={final_height}px, 行数={final_lines}"
        )

    return processed_title, current_font_size, processed


def create_left_composite_image(
    cover_path: str,
    title: str,
    font_path: str,
    font_size: int = 48,
    debug: bool = False,
    cover_preserve_aspect: bool = True,  # 新增：是否保持封面比例（不crop）
    video_width_ratio: float = 0.5,  # 新增：右侧视频宽度比例（相对于右半边）
    video_align_right: bool = True,  # 新增：视频是否右对齐
    force_single_line: bool = False,  # 新增：强制单行显示
    fixed_font_size: bool = False,  # 新增：固定字体大小
    title_top_margin: int = 0,  # 新增：标题距离上边沿的距离（像素）
) -> Optional[str]:
    """
    预先合成左半边的完整图片（封面 + 标题区域）

    Args:
        cover_path: 封面图片路径
        title: 书籍标题
        font_path: 字体文件路径
        font_size: 字体大小
        debug: 是否启用调试模式
        cover_preserve_aspect: 是否保持封面比例（不crop，可留黑边）
        video_width_ratio: 右侧视频宽度比例（相对于右半边宽度）
        video_align_right: 视频是否右对齐
        force_single_line: 强制单行显示
        fixed_font_size: 固定字体大小（不动态调整，允许换行）
        title_top_margin: 标题距离上边沿的距离（像素），用于调整标题垂直位置

    Returns:
        合成图片的临时文件路径，失败时返回None
    """
    try:
        # 1080p 尺寸参数
        total_width = 1920
        total_height = 1080
        left_width = 960
        right_width = 960
        title_height = int(total_height * 0.3)

        # 创建完整的1080p黑色背景
        composite_img = Image.new("RGB", (total_width, total_height), color="black")

        # 处理封面图片 - 修复版本：确保完整显示在左半边
        cover_img = Image.open(cover_path)

        if cover_preserve_aspect:
            # 保持比例，确保完全适配左半边区域，必要时留黑边
            cover_ratio = cover_img.width / cover_img.height
            left_area_ratio = left_width / total_height

            if cover_ratio > left_area_ratio:
                # 封面更宽，以左半边宽度为准缩放，确保不超出左边界
                new_width = left_width
                new_height = int(left_width / cover_ratio)
                # 确保高度不超过总高度
                if new_height > total_height:
                    new_height = total_height
                    new_width = int(total_height * cover_ratio)
            else:
                # 封面更高，以总高度为准缩放，确保不超出上下边界
                new_height = total_height
                new_width = int(total_height * cover_ratio)
                # 确保宽度不超过左半边宽度
                if new_width > left_width:
                    new_width = left_width
                    new_height = int(left_width / cover_ratio)

            # 调整封面尺寸
            cover_resized = cover_img.resize(
                (new_width, new_height), Image.Resampling.LANCZOS
            )

            # 在左半边居中粘贴封面，确保完全在左半边内
            cover_x = max(0, (left_width - new_width) // 2)
            cover_y = max(0, (total_height - new_height) // 2)

            # 双重检查确保不超出左半边边界
            if cover_x + new_width > left_width:
                cover_x = left_width - new_width
            if cover_y + new_height > total_height:
                cover_y = total_height - new_height

            if debug:
                print(
                    f"🖼️ 封面保持比例缩放: {cover_img.size} -> {new_width}x{new_height}"
                )
                print(f"📍 封面位置: ({cover_x}, {cover_y})")
                print(f"🔍 左半边区域: 0,0 到 {left_width},{total_height}")
                print(
                    f"✅ 封面完全在左半边内: {cover_x + new_width <= left_width and cover_y + new_height <= total_height}"
                )
        else:
            # 原有逻辑：可能会crop，但也确保在左半边内
            cover_ratio = cover_img.width / cover_img.height
            left_ratio = left_width / total_height

            if cover_ratio > left_ratio:
                # 图片更宽，按高度缩放
                new_height = total_height
                new_width = int(total_height * cover_ratio)
                # 如果仍然太宽，按宽度重新缩放
                if new_width > left_width:
                    new_width = left_width
                    new_height = int(left_width / cover_ratio)
            else:
                # 图片更高，按宽度缩放
                new_width = left_width
                new_height = int(left_width / cover_ratio)
                # 如果仍然太高，按高度重新缩放
                if new_height > total_height:
                    new_height = total_height
                    new_width = int(total_height * cover_ratio)

            # 调整封面尺寸
            cover_resized = cover_img.resize(
                (new_width, new_height), Image.Resampling.LANCZOS
            )

            # 居中粘贴封面到左半边，确保在边界内
            cover_x = max(0, min(left_width - new_width, (left_width - new_width) // 2))
            cover_y = max(
                0, min(total_height - new_height, (total_height - new_height) // 2)
            )

        composite_img.paste(cover_resized, (cover_x, cover_y))

        # 创建标题部分
        draw = ImageDraw.Draw(composite_img)

        # 标题区域是右上角
        title_x_start = left_width
        title_y_start = 0
        title_area_width = right_width
        title_area_height = title_height

        # 🆕 智能处理标题溢出
        processed_title, actual_font_size, was_processed = process_title_for_overflow(
            title=title,
            draw=draw,
            font_path=font_path,
            font_size=font_size,
            max_width=title_area_width,
            max_height=title_area_height,
            debug=debug,
            fixed_font_size=fixed_font_size,
        )

        # 使用处理后的标题和字体大小
        font = ImageFont.truetype(font_path, actual_font_size)

        if debug and was_processed:
            print(f"📝 标题处理完成:")
            print(f"   原标题: '{title}'")
            print(f"   处理后: '{processed_title}'")
            print(f"   字体大小: {font_size}px → {actual_font_size}px")

        # 获取处理后的文本尺寸
        bbox = draw.textbbox((0, 0), processed_title, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # 处理文本换行和绘制
        if force_single_line:
            # 强制单行显示，已经通过智能处理确保不溢出
            x = title_x_start + (title_area_width - text_width) // 2
            # 应用上边距：如果设置了上边距，从上边距开始，否则垂直居中
            if title_top_margin > 0:
                y = title_y_start + title_top_margin
            else:
                y = title_y_start + (title_area_height - text_height) // 2

            if debug:
                print(f"🔤 强制单行显示: 字体大小={actual_font_size}px")
                print(f"   文本宽度={text_width}px, 区域宽度={title_area_width}px")
                print(f"   标题位置: x={x}, y={y} (上边距={title_top_margin}px)")

            draw.text((x, y), processed_title, font=font, fill="white")
        elif text_width <= title_area_width - 40:
            # 文本适合单行显示
            x = title_x_start + (title_area_width - text_width) // 2
            # 应用上边距：如果设置了上边距，从上边距开始，否则垂直居中
            if title_top_margin > 0:
                y = title_y_start + title_top_margin
            else:
                y = title_y_start + (title_area_height - text_height) // 2

            if debug:
                print(
                    f"🔤 单行显示: 标题位置 x={x}, y={y} (上边距={title_top_margin}px)"
                )

            draw.text((x, y), processed_title, font=font, fill="white")
        else:
            # 需要换行，已经通过智能处理优化过的标题
            # 用处理后的标题和字体大小进行换行

            # 检查是否包含中文字符
            import re

            has_chinese = bool(re.search(r"[\u4e00-\u9fff]", processed_title))

            lines = []
            max_line_width = 0

            if has_chinese:
                # 中文换行：逐字符处理
                current_line = ""
                for char in processed_title:
                    test_line = current_line + char
                    bbox = draw.textbbox((0, 0), test_line, font=font)
                    test_width = bbox[2] - bbox[0]

                    if test_width <= title_area_width - 40:
                        current_line = test_line
                        max_line_width = max(max_line_width, test_width)
                    else:
                        if current_line:
                            lines.append(current_line)
                            current_line = char
                            # 计算单个字符的宽度
                            bbox = draw.textbbox((0, 0), char, font=font)
                            char_width = bbox[2] - bbox[0]
                            max_line_width = max(max_line_width, char_width)
                        else:
                            # 单个字符也太宽，强制添加
                            lines.append(char)
                            bbox = draw.textbbox((0, 0), char, font=font)
                            char_width = bbox[2] - bbox[0]
                            max_line_width = max(max_line_width, char_width)

                if current_line:
                    lines.append(current_line)
                    bbox = draw.textbbox((0, 0), current_line, font=font)
                    line_width = bbox[2] - bbox[0]
                    max_line_width = max(max_line_width, line_width)
            else:
                # 英文换行：按单词处理
                words = processed_title.split()
                current_line = ""

                for word in words:
                    test_line = current_line + " " + word if current_line else word
                    bbox = draw.textbbox((0, 0), test_line, font=font)
                    test_width = bbox[2] - bbox[0]

                    if test_width <= title_area_width - 40:
                        current_line = test_line
                        max_line_width = max(max_line_width, test_width)
                    else:
                        if current_line:
                            lines.append(current_line)
                            current_line = word
                            # 检查单个词的宽度
                            bbox = draw.textbbox((0, 0), word, font=font)
                            word_width = bbox[2] - bbox[0]
                            max_line_width = max(max_line_width, word_width)
                        else:
                            # 单个词太长，强制添加
                            lines.append(word)
                            bbox = draw.textbbox((0, 0), word, font=font)
                            word_width = bbox[2] - bbox[0]
                            max_line_width = max(max_line_width, word_width)

                if current_line:
                    lines.append(current_line)
                    bbox = draw.textbbox((0, 0), current_line, font=font)
                    line_width = bbox[2] - bbox[0]
                    max_line_width = max(max_line_width, line_width)

            # 绘制多行文本
            line_height = text_height + 5  # 行间距
            total_text_height = len(lines) * line_height

            # 应用上边距：如果设置了上边距，从上边距开始，否则垂直居中
            if title_top_margin > 0:
                start_y = title_y_start + title_top_margin
            else:
                start_y = title_y_start + (title_area_height - total_text_height) // 2

            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                x = title_x_start + (title_area_width - line_width) // 2
                y = start_y + i * line_height
                draw.text((x, y), line, font=font, fill="white")

            if debug:
                print(f"🔤 多行显示: {len(lines)}行, 字体大小={actual_font_size}px")
                print(
                    f"   最宽行宽度={max_line_width}px, 区域宽度={title_area_width}px"
                )
                print(
                    f"   多行起始位置: start_y={start_y} (上边距={title_top_margin}px)"
                )
                print(f"   总文本高度: {total_text_height}px")

        # 保存合成图片
        temp_composite_path = f"/tmp/composite_{int(time.time())}_{os.getpid()}.png"
        composite_img.save(temp_composite_path, optimize=True)

        if debug:
            print(f"✅ 左半边合成图片已创建: {temp_composite_path}")
            print(
                f"🎬 右侧视频配置: 宽度比例={video_width_ratio}, 右对齐={video_align_right}"
            )

        return temp_composite_path

    except Exception as e:
        logger.error(f"❌ 创建左半边合成图片失败: {e}")
        return None


def get_optimal_encoder_settings():
    """获取最优的编码器设置"""

    system = platform.system()

    # 检测可用的硬件编码器
    encoders_to_test = []

    if system == "Darwin":  # macOS
        encoders_to_test = [
            ("h264_videotoolbox", "veryfast"),  # Apple硬件编码
            ("libx264", "ultrafast"),  # 软件编码
        ]
    else:  # Linux/Ubuntu
        encoders_to_test = [
            ("h264_nvenc", "fast"),  # NVIDIA GPU
            ("h264_qsv", "fast"),  # Intel GPU
            ("h264_amf", "fast"),  # AMD GPU
            ("libx264", "ultrafast"),  # 软件编码
        ]

    # 测试编码器可用性
    for encoder, preset in encoders_to_test:
        try:
            # 简单测试编码器是否可用
            test_cmd = [
                "ffmpeg",
                "-f",
                "lavfi",
                "-i",
                "testsrc=duration=0.1:size=32x32:rate=1",
                "-c:v",
                encoder,
                "-preset",
                preset,
                "-f",
                "null",
                "-",
            ]
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return encoder, preset
        except:
            continue

    # 默认回退
    return "libx264", "ultrafast"


def create_book_clip(
    cover_path: str,
    title: str,
    background_video: str,
    output_path: str,
    font_path: str,
    font_size: int = 48,
    debug: bool = False,
    cover_preserve_aspect: bool = True,  # 新增：是否保持封面比例
    video_width_ratio: float = 0.5,  # 新增：右侧视频宽度比例
    video_align_right: bool = True,  # 新增：视频是否右对齐
    force_single_line: bool = False,  # 新增：强制单行显示
    fixed_font_size: bool = False,  # 新增：固定字体大小
    show_book_summary: bool = True,  # 新增：是否显示"Book summary"文字
    summary_font_size: int = 24,  # 新增：Book summary字体大小
    summary_top_margin: int = 20,  # 新增：Book summary文字距离视频底部向上的像素距离
    summary_right_margin: int = 10,  # 新增：Book summary文字距离右边缘的像素距离
    summary_icon_size: int = 0,  # 新增：📚图标大小，0表示自动调整
    icon_vertical_offset: int = 0,  # 新增：图标垂直偏移量，负数向上移动
    language: str = "en",  # 新增：语言代码
    title_top_margin: int = 0,  # 新增：标题距离上边沿的距离（像素）
) -> bool:
    """
    创建书籍MP4 clip - 优化版本

    Args:
        cover_path: 封面图片路径
        title: 书籍标题
        background_video: 背景视频路径
        output_path: 输出视频路径
        font_path: 字体文件路径
        font_size: 字体大小
        debug: 是否启用调试模式
        cover_preserve_aspect: 是否保持封面比例（不crop，可留黑边）
        video_width_ratio: 右侧视频宽度比例（相对于右半边宽度）
        video_align_right: 视频是否右对齐
        force_single_line: 强制单行显示，保持固定字体大小
        fixed_font_size: 固定字体大小（不动态调整，允许换行）
        show_book_summary: 是否在右侧视频上显示书籍摘要文字
        summary_font_size: 书籍摘要文字的字体大小
        summary_top_margin: 书籍摘要文字距离视频底部向上的像素距离
        summary_right_margin: 书籍摘要文字距离右边缘的像素距离
        title_top_margin: 标题距离上边沿的距离（像素），用于调整多行标题的垂直位置

    Returns:
        处理成功返回True，失败返回False
    """

    # 1080p 尺寸参数
    total_width = 1920
    total_height = 1080
    left_width = 960
    right_width = 960
    title_height = int(total_height * 0.3)
    video_height = total_height - title_height

    # 计算右侧视频的实际尺寸和位置
    video_actual_width = int(right_width * video_width_ratio)
    video_actual_height = int(video_height * video_width_ratio)  # 保持比例

    # 计算视频位置
    if video_align_right:
        video_x_offset = left_width + (right_width - video_actual_width)  # 右对齐
    else:
        video_x_offset = left_width + (right_width - video_actual_width) // 2  # 居中

    # 视频贴底部对齐
    video_y_offset = total_height - video_actual_height

    temp_files = []

    try:
        # 步骤1: 预先合成左半边静态部分（封面+标题区域）
        print(f"🖼️ 预合成静态部分...")
        composite_image = create_left_composite_image(
            cover_path,
            title,
            font_path,
            font_size,
            debug,
            cover_preserve_aspect,
            video_width_ratio,
            video_align_right,
            force_single_line,
            fixed_font_size,
            title_top_margin,
        )
        if not composite_image:
            return False
        temp_files.append(composite_image)

        # 步骤2: 获取最优编码器设置
        encoder, preset = get_optimal_encoder_settings()
        if debug:
            print(f"🚀 使用编码器: {encoder}, 预设: {preset}")
            print(f"📐 视频布局参数:")
            print(
                f"   - 右侧视频宽度: {video_actual_width}px ({video_width_ratio*100:.1f}%)"
            )
            print(f"   - 右侧视频高度: {video_actual_height}px")
            print(f"   - 视频位置: ({video_x_offset}, {video_y_offset})")
            print(f"   - 右对齐: {'是' if video_align_right else '否'}")

        # 步骤3: 构建优化的FFmpeg命令，使用新的布局参数
        print(f"🎬 快速合成最终视频...")

        # 构建FFmpeg滤镜链
        filter_complex = f"[0:v]scale={video_actual_width}:{video_actual_height}[bg_scaled];"  # 按新尺寸缩放背景视频

        # 先把背景视频叠加到1080p画面上，不添加文字
        filter_complex += f"[1:v][bg_scaled]overlay={video_x_offset}:{video_y_offset}[video_composed];"  # 叠加到指定位置

        # 然后在整个1080p画面上添加全局文字叠加
        if show_book_summary:
            # 获取合适的字体路径（根据语言选择）
            summary_font_path = get_merriweather_font_path(language)
            if summary_font_path:
                # 转义字体路径中的特殊字符
                escaped_font_path = summary_font_path.replace(":", "\\:").replace(
                    ",", "\\,"
                )

                # 计算在1080p全局坐标系中的位置
                # summary_right_margin 是从整个画面右边缘往左的偏移量
                global_text_x = f"({total_width}-{summary_right_margin})"
                global_text_y = f"({total_height}-text_h-{summary_top_margin})"

                # 根据语言选择合适的文字
                summary_text = "书籍摘要" if language == "zh" else "Book summary"

                # 先添加纯文字（不含emoji）
                filter_complex += (
                    f"[video_composed]drawtext=text='{summary_text}':"
                    f"fontfile='{escaped_font_path}':"
                    f"fontsize={summary_font_size}:"
                    f"fontcolor=0x00FF00:"
                    f"x={global_text_x}:"
                    f"y={global_text_y}[text_added];"
                )

                # 检查是否有书籍图标PNG文件
                book_icon_path = os.path.join(get_script_dir(), "assets", "books.png")
                if os.path.exists(book_icon_path):
                    # 计算图标位置（在文字左边，留一些间距）
                    icon_size = (
                        summary_icon_size
                        if summary_icon_size > 0
                        else int(summary_font_size * 1.2)
                    )  # 使用设定大小或默认大小
                    icon_x = f"({total_width}-{summary_right_margin}-{icon_size}-10)"  # 在文字左边10px
                    # 添加垂直偏移量来调整图标对齐
                    if icon_vertical_offset != 0:
                        icon_y = f"({total_height}-{summary_top_margin}-{icon_size}{icon_vertical_offset:+d})"
                    else:
                        icon_y = f"({total_height}-{summary_top_margin}-{icon_size})"

                    # 转义图标路径
                    escaped_icon_path = book_icon_path.replace(":", "\\:").replace(
                        ",", "\\,"
                    )

                    # 叠加书籍图标
                    filter_complex += (
                        f"[2:v]scale={icon_size}:{icon_size}[icon_scaled];"
                        f"[text_added][icon_scaled]overlay={icon_x}:{icon_y}[final]"
                    )

                    if debug:
                        print(f"📚 添加书籍图标:")
                        print(f"   图标文件: {book_icon_path}")
                        print(
                            f"   图标大小: {icon_size}x{icon_size}px {'(用户设定)' if summary_icon_size > 0 else '(自动计算)'}"
                        )
                        print(f"   图标位置: x={icon_x}, y={icon_y}")
                        if icon_vertical_offset != 0:
                            print(f"   垂直偏移: {icon_vertical_offset:+d}px")
                else:
                    # 没有图标文件，直接用文字
                    filter_complex = filter_complex.replace("[text_added];", "[final];")
                    if debug:
                        print(f"⚠️ 未找到书籍图标文件: {book_icon_path}")

                if debug:
                    print(f"📝 添加全局书籍摘要文字:")
                    print(f"   显示文字: {summary_text}")
                    print(f"   字体: {os.path.basename(summary_font_path)}")
                    print(f"   字体大小: {summary_font_size}px")
                    print(f"   颜色: 纯绿色 (0x00FF00)")
                    print(
                        f"   全局位置: 从1080p右边缘往左偏移{summary_right_margin}px, 距离底部向上{summary_top_margin}px"
                    )
                    print(
                        f"   1080p坐标: x=({total_width}-{summary_right_margin}), y=({total_height}-{summary_top_margin})"
                    )
            else:
                logger.warning("⚠️ 未找到合适的字体，跳过书籍摘要文字叠加")
                filter_complex += "[video_composed]copy[final]"
        else:
            filter_complex += "[video_composed]copy[final]"

        # 构建基础命令
        cmd = [
            "ffmpeg",
            "-y",  # 覆盖输出文件
            "-i",
            background_video,  # 输入背景视频
            "-i",
            composite_image,  # 输入预合成的静态图片
        ]

        # 如果有书籍图标，添加为第三个输入
        book_icon_path = os.path.join(get_script_dir(), "assets", "books.png")
        if show_book_summary and os.path.exists(book_icon_path):
            cmd.extend(["-i", book_icon_path])  # 添加图标作为第三个输入

        # 添加其余参数
        cmd.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                "[final]",
                "-an",  # 禁用音频输出，生成无声视频
                "-c:v",
                encoder,  # 使用最优编码器
                "-preset",
                preset,  # 使用快速预设
                "-crf",
                "25",  # 稍微降低质量以换取速度
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",  # 优化网络播放
                "-threads",
                "0",  # 使用所有可用线程
                output_path,
            ]
        )

        if debug:
            print(f"🔧 优化后的FFmpeg命令: {' '.join(cmd)}")
            print(f"🎭 滤镜链: {filter_complex}")

        # 执行FFmpeg命令
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        process_time = time.time() - start_time

        if result.returncode == 0:
            print(f"✅ 视频合成成功: {output_path}")
            print(f"⚡ 处理时间: {process_time:.2f} 秒")

            # 验证输出文件
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
                print(f"📏 输出文件大小: {file_size:.2f} MB")
                return True
            else:
                print(f"❌ 输出文件未生成: {output_path}")
                return False
        else:
            print(f"❌ FFmpeg执行失败:")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"❌ 创建书籍clip失败: {e}")
        return False

    finally:
        # 清理临时文件
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    if debug:
                        print(f"🗑️  清理临时文件: {temp_file}")
            except Exception as e:
                logger.warning(f"⚠️ 清理临时文件失败: {temp_file}, {e}")


def get_existing_clips(language="en") -> set:
    """
    获取已存在的clip文件UUID集合

    Returns:
        已存在文件的UUID集合
    """
    output_dir = get_output_directory(language)

    if not os.path.exists(output_dir):
        return set()

    # 获取所有MP4文件
    clip_files = glob.glob(os.path.join(output_dir, "*.mp4"))
    existing_uuids = set()

    for clip_file in clip_files:
        basename = os.path.basename(clip_file)

        # 跳过点开头的文件
        if basename.startswith("."):
            continue

        # 提取UUID
        uuid_match = re.match(r"([a-f0-9\-]+)\.mp4", basename)
        if uuid_match:
            uuid = uuid_match.group(1)
            existing_uuids.add(uuid)

    return existing_uuids


def process_all_books(
    font_size: int = 48,
    force: bool = False,
    debug: bool = False,
    language: str = "en",
    cover_preserve_aspect: bool = True,  # 新增：是否保持封面比例
    video_width_ratio: float = 0.5,  # 新增：右侧视频宽度比例
    video_align_right: bool = True,  # 新增：视频是否右对齐
    font_path: Optional[str] = None,  # 新增：指定字体路径
    font_weight: Optional[str] = None,  # 新增：指定字体权重
    force_single_line: bool = False,  # 新增：强制单行显示
    fixed_font_size: bool = False,  # 新增：固定字体大小
    show_book_summary: bool = True,  # 新增：是否显示Book summary文字
    summary_font_size: int = 24,  # 新增：Book summary字体大小
    summary_top_margin: int = 20,  # 新增：Book summary文字距离视频底部向上的像素距离
    summary_right_margin: int = 10,  # 新增：Book summary文字距离右边缘的像素距离
    summary_icon_size: int = 0,  # 新增：图标大小，0表示自动计算
    icon_vertical_offset: int = 0,  # 新增：图标垂直偏移量
    title_top_margin: int = 0,  # 新增：标题距离上边沿的距离（像素）
) -> bool:
    """
    批量处理所有书籍生成MP4 clips

    Args:
        font_size: 字体大小
        force: 是否强制重新处理
        debug: 是否启用调试模式
        language: 语言
        cover_preserve_aspect: 是否保持封面比例（不crop，可留黑边）
        video_width_ratio: 右侧视频宽度比例（相对于右半边宽度）
        video_align_right: 视频是否右对齐
        font_path: 指定字体文件路径（优先级最高）
        font_weight: 指定字体权重（当font_path为None时使用）
        force_single_line: 强制单行显示，保持固定字体大小
        fixed_font_size: 固定字体大小（不动态调整，允许换行）
        show_book_summary: 是否在右侧视频上显示书籍摘要文字
        summary_font_size: 书籍摘要文字的字体大小
        summary_top_margin: 书籍摘要文字距离视频底部向上的像素距离
        summary_right_margin: 书籍摘要文字距离右边缘的像素距离
        title_top_margin: 标题距离上边沿的距离（像素），用于调整多行标题的垂直位置

    Returns:
        处理成功返回True，失败返回False
    """

    # 检查依赖
    if not check_dependencies():
        return False

    # 获取可用书籍列表
    available_books = get_available_books(language)
    if not available_books:
        print("❌ 未找到包含超分封面的书籍")
        return False

    # 获取已存在的clips
    existing_clips = get_existing_clips(language)

    # 过滤需要处理的书籍
    books_to_process = []
    for cover_path, uuid in available_books:
        if force or uuid not in existing_clips:
            books_to_process.append((cover_path, uuid))
        else:
            if debug:
                print(f"⏭️ 跳过已存在的clip: {uuid}")

    if not books_to_process:
        print("✅ 所有书籍clip都已完成处理")
        return True

    # 获取背景视频
    background_video = get_background_video(language)
    if not background_video:
        return False

    # 选择字体文件
    selected_font_path = select_font_by_path_or_weight(font_path, font_weight, language)
    if not selected_font_path or not os.path.exists(selected_font_path):
        print("❌ 未找到可用的字体文件")
        return False

    # 确保输出目录存在
    output_dir = get_output_directory(language)
    os.makedirs(output_dir, exist_ok=True)

    # 显示处理统计
    directories = get_input_directories(language)
    lang_name = "中文" if language == "zh" else "English"

    print(f"\n=== 📊 书籍MP4 Clip生成统计 ===")
    print(f"📁 封面目录: {directories.get('thumbnails_large', 'N/A')}")
    print(f"📁 输出目录: {output_dir}")
    print(f"🌍 语言: {lang_name}")
    print(f"📹 总书籍数量: {len(available_books)}")
    print(f"✅ 已处理数量: {len(existing_clips)}")
    print(f"🎯 需要处理: {len(books_to_process)}")
    print(f"🎬 背景视频: {os.path.basename(background_video)}")
    print(f"🔤 字体大小: {font_size}px")
    print(f"🔄 强制重新处理: {'是' if force else '否'}")
    print(f"🐛 调试模式: {'是' if debug else '否'}")
    print(f"🖼️ 封面保持比例: {'是' if cover_preserve_aspect else '否'}")
    print(f"📐 右侧视频宽度比例: {video_width_ratio*100:.1f}%")
    print(f"↗️ 视频右对齐: {'是' if video_align_right else '否'}")

    # 统计变量
    success_count = 0
    failure_count = 0

    # 批量处理
    with tqdm(total=len(books_to_process), desc="🎬 生成进度") as pbar:
        for cover_path, uuid in books_to_process:
            print(f"\n=== 🎬 处理书籍: {uuid} ===")

            # 获取书籍信息
            book_info = get_book_info(uuid, language)
            if not book_info:
                print(f"❌ 无法获取书籍信息: {uuid}")
                failure_count += 1
                pbar.update(1)
                continue

            title = book_info.get("title", f"Book {uuid[:8]}")
            print(f"📖 书籍标题: {title}")
            print(f"📂 封面图片: {cover_path}")

            # 检查封面文件
            if not os.path.exists(cover_path):
                print(f"❌ 封面文件不存在: {cover_path}")
                failure_count += 1
                pbar.update(1)
                continue

            # 生成输出路径
            output_path = os.path.join(output_dir, f"{uuid}.mp4")

            # 创建书籍clip
            success = create_book_clip(
                cover_path=cover_path,
                title=title,
                background_video=background_video,
                output_path=output_path,
                font_path=selected_font_path,
                font_size=font_size,
                debug=debug,
                cover_preserve_aspect=cover_preserve_aspect,
                video_width_ratio=video_width_ratio,
                video_align_right=video_align_right,
                force_single_line=force_single_line,
                fixed_font_size=fixed_font_size,
                show_book_summary=show_book_summary,
                summary_font_size=summary_font_size,
                summary_top_margin=summary_top_margin,
                summary_right_margin=summary_right_margin,
                summary_icon_size=summary_icon_size,
                icon_vertical_offset=icon_vertical_offset,
                language=language,
                title_top_margin=title_top_margin,
            )

            if success:
                success_count += 1
                print(f"✅ {uuid} 处理成功")
            else:
                failure_count += 1
                print(f"❌ {uuid} 处理失败")

            pbar.update(1)

            # 在处理间隔添加短暂延迟
            if success_count + failure_count < len(books_to_process):
                time.sleep(1)

    # 输出最终统计
    print(f"\n=== 📈 书籍MP4 Clip生成完成统计 ===")
    print(f"✅ 成功处理: {success_count}/{len(books_to_process)} 个书籍")
    print(f"❌ 处理失败: {failure_count}/{len(books_to_process)} 个书籍")
    print(f"📊 成功率: {success_count/len(books_to_process)*100:.1f}%")

    # 显示处理后的文件列表
    if success_count > 0:
        print(f"\n📁 处理完成的文件位于: {output_dir}")
        clip_files = glob.glob(os.path.join(output_dir, "*.mp4"))
        if clip_files:
            print("🎬 生成的MP4 clip文件:")
            for clip_file in sorted(clip_files)[:10]:  # 只显示前10个
                filename = os.path.basename(clip_file)
                if not filename.startswith("."):
                    file_size = os.path.getsize(clip_file) / (1024 * 1024)
                    print(f"   📄 {filename} ({file_size:.2f} MB)")
            if len(clip_files) > 10:
                print(f"   ... 还有 {len(clip_files) - 10} 个文件")

    return success_count > 0


def main():
    """主函数"""
    # 检查系统支持情况
    supported, system_desc = check_supported_system()
    if supported:
        print(f"✅ 系统检测: {system_desc}")
    else:
        print(f"⚠️ 系统检测: {system_desc} (可能需要手动配置路径)")

    print(f"🖥️  操作系统: {platform.system()}")

    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description="📚 书籍 1080p MP4 Clip 生成器",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  python generate_book_clips.py                        # 默认处理英文书籍
  python generate_book_clips.py --language zh          # 处理中文书籍
  python generate_book_clips.py --font-size 56         # 使用56px字体
  python generate_book_clips.py --force                # 强制重新处理
  python generate_book_clips.py --debug                # 启用调试模式
  
布局优化参数:
  python generate_book_clips.py --no-preserve-aspect   # 允许crop封面（旧行为）
  python generate_book_clips.py --video-width 0.3      # 右侧视频占30%宽度
  python generate_book_clips.py --video-center         # 右侧视频居中对齐
  
字体设置:
  python generate_book_clips.py --font-weight bold     # 使用粗体字体
  python generate_book_clips.py --font-weight semi-bold # 使用半粗体字体
  python generate_book_clips.py --font-path /path/to/font.ttf # 指定字体文件
  python generate_book_clips.py --force-single-line    # 强制单行显示，保持固定字体大小
  python generate_book_clips.py --fixed-font-size      # 固定字体大小，长标题自动换行
  python generate_book_clips.py --title-top-margin 30  # 标题距离上边沿30px（调整多行标题位置）

Book summary文字设置:
  python generate_book_clips.py --no-book-summary      # 不显示Book summary文字
  python generate_book_clips.py --summary-font-size 30 # 设置Book summary字体大小为30px
  python generate_book_clips.py --summary-top-margin 30 # 设置距离顶部30px
  python generate_book_clips.py --summary-right-margin 15 # 设置从右边缘往左偏移15px
  python generate_book_clips.py --icon-size 32         # 设置书籍图标大小为32x32像素
  python generate_book_clips.py --icon-vertical-offset -5 # 图标向上移动5像素对齐文字
  
  组合使用:
  python generate_book_clips.py --video-width 0.4 --video-center --font-weight bold --force-single-line --summary-font-size 28 --summary-right-margin 15 --icon-size 30 --icon-vertical-offset -3 --title-top-margin 25 --debug
  
  中文书籍特殊用法:  
  python generate_book_clips.py --language zh --fixed-font-size --font-size 56 --title-top-margin 20 --debug  # 中文书籍固定56px字体，长标题自动换行，上边距20px

注意:
- 支持 macOS (Intel/Apple Silicon) 和 Linux/Ubuntu 系统
- 需要安装 FFmpeg
- 需要超分后的封面图片 (来自 upscale_book_thumbnails.py)
- 需要背景视频文件 (assets/plate_upscaled.mp4)
- 生成 1080p (1920x1080) 分辨率视频
- 自动跳过已处理的文件（除非使用 --force）
- 自动跳过Mac系统生成的点开头文件
- 支持中文和英文两种语言的书籍处理
- 中文字体在 font/zh/ 目录，英文字体在 font/en/ 目录
- 新版本默认保持封面比例，不crop，可留黑边
- 右侧视频默认占右半边50%宽度，右对齐
- 支持固定字体大小模式，长标题自动换行（推荐中文书籍使用）
- 中文标题按字符换行，英文标题按单词换行
- 支持调节标题距离上边沿的距离，改善多行标题布局
        """,
    )

    # 添加原有的命令行参数
    parser.add_argument(
        "--font-size",
        type=int,
        default=48,
        help="字体大小 (默认: 48)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新处理所有书籍",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式",
    )
    parser.add_argument(
        "--language",
        "-l",
        choices=["en", "zh"],
        default="en",
        help="选择语种: en(英文) 或 zh(中文) [默认: en]",
    )

    # 添加新的布局参数
    parser.add_argument(
        "--no-preserve-aspect",
        action="store_true",
        help="不保持封面比例，允许crop（恢复旧行为）[默认: False，即保持比例]",
    )
    parser.add_argument(
        "--video-width",
        type=float,
        default=0.5,
        help="右侧视频宽度比例，相对于右半边 (0.1-1.0) [默认: 0.5]",
    )
    parser.add_argument(
        "--video-center",
        action="store_true",
        help="右侧视频居中对齐（而非右对齐）[默认: 右对齐]",
    )

    # 添加字体相关参数
    parser.add_argument(
        "--font-path",
        type=str,
        help="指定字体文件路径（优先级最高）",
    )
    parser.add_argument(
        "--font-weight",
        type=str,
        choices=[
            "extra-light",
            "light",
            "regular",
            "medium",
            "semi-bold",
            "bold",
            "extra-bold",
        ],
        help="指定字体权重：extra-light, light, regular, medium, semi-bold, bold, extra-bold",
    )
    parser.add_argument(
        "--force-single-line",
        action="store_true",
        help="强制单行显示标题，不自动换行[默认: 自动换行]",
    )
    parser.add_argument(
        "--fixed-font-size",
        action="store_true",
        help="固定字体大小，长标题自动换行而不缩小字体[默认: 自动调整字体大小]",
    )

    # 添加Book summary文字相关参数
    parser.add_argument(
        "--no-book-summary",
        action="store_true",
        help="不显示Book summary文字[默认: 显示]",
    )
    parser.add_argument(
        "--summary-font-size",
        type=int,
        default=24,
        help="Book summary文字的字体大小 [默认: 24]",
    )
    parser.add_argument(
        "--summary-top-margin",
        type=int,
        default=20,
        help="Book summary文字距离视频底部向上的像素距离 [默认: 20]",
    )
    parser.add_argument(
        "--summary-right-margin",
        type=int,
        default=10,
        help="Book summary文字从右边缘往左偏移的像素距离 [默认: 10]",
    )
    parser.add_argument(
        "--icon-size",
        type=int,
        default=0,
        help="书籍图标大小(像素)，方形PNG，0表示自动调整为字体大小的1.2倍 [默认: 0]",
    )
    parser.add_argument(
        "--icon-vertical-offset",
        type=int,
        default=0,
        help="书籍图标垂直偏移量(像素)，负数向上移动，正数向下移动 [默认: 0]",
    )
    parser.add_argument(
        "--title-top-margin",
        type=int,
        default=0,
        help="标题距离上边沿的距离(像素)，用于调整多行标题的垂直位置，0表示垂直居中 [默认: 0]",
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 验证参数
    if not (0.1 <= args.video_width <= 1.0):
        print("❌ 视频宽度比例必须在 0.1-1.0 之间")
        sys.exit(1)

    print("🎬 书籍 1080p MP4 Clip 生成器")
    print("=" * 50)

    # 显示系统信息和路径
    directories = get_input_directories(args.language)
    output_dir = get_output_directory(args.language)
    lang_name = "中文" if args.language == "zh" else "English"

    print(f"🌍 语种: {lang_name}")
    print(f"📁 封面目录: {directories.get('thumbnails_large', 'N/A')}")
    print(f"📁 输出目录: {output_dir}")
    print(f"🖥️ 操作系统: {platform.system()}")

    # 检查基础路径是否正确配置
    if not directories:
        print("❌ 无法获取目录配置，可能的原因:")
        base_path = get_base_media_path()
        if not base_path:
            print("   - 无法确定基础媒体路径")
            system = platform.system()
            if system == "Darwin":
                print("   💡 macOS用户请确保以下路径之一存在:")
                print("      Intel Mac: /Volumes/dhl/audio")
                print("      Apple Silicon: /Users/donghaoliu/Documents/audio")
            elif system == "Linux":
                print("   💡 Linux用户请确保路径存在: /media/dhl/audio")
            else:
                print(f"   💡 {system}用户解决方案:")
                print("      1. 设置环境变量: export AUDIO_BASE_DIR=/your/audio/path")
                print("      2. 或修改代码中的get_base_media_path()函数")
        sys.exit(1)

    # 检查目录是否存在
    thumbnails_dir = directories.get("thumbnails_large", "")
    if not thumbnails_dir or not os.path.exists(thumbnails_dir):
        print(f"❌ 超分封面目录不存在: {thumbnails_dir}")
        print("💡 请先运行 upscale_book_thumbnails.py 生成超分封面图片")
        sys.exit(1)

    assets_dir = directories.get("assets", "")
    if not assets_dir or not os.path.exists(assets_dir):
        print(f"❌ 素材目录不存在: {assets_dir}")
        print("💡 请确保 assets 目录包含背景视频文件")
        sys.exit(1)

    print(f"🔤 字体大小: {args.font_size}px")
    print(f"🔄 强制重新处理: {'是' if args.force else '否'}")
    print(f"🐛 调试模式: {'是' if args.debug else '否'}")

    # 显示布局参数
    cover_preserve_aspect = not args.no_preserve_aspect
    video_align_right = not args.video_center

    print(f"🖼️ 封面保持比例: {'是' if cover_preserve_aspect else '否'}")
    print(f"📐 右侧视频宽度比例: {args.video_width*100:.1f}%")
    print(f"↗️ 视频对齐方式: {'右对齐' if video_align_right else '居中'}")
    print()

    print(f"🔤 强制单行显示: {'是' if args.force_single_line else '否'}")
    print(f"🔒 固定字体大小: {'是' if args.fixed_font_size else '否'}")
    print(
        f"📏 标题上边距: {args.title_top_margin}px {'(垂直居中)' if args.title_top_margin == 0 else '(距离顶部)'}"
    )
    print(f"📝 显示Book summary: {'否' if args.no_book_summary else '是'}")
    if not args.no_book_summary:
        print(f"📝 Book summary字体大小: {args.summary_font_size}px")
        print(f"📝 Book summary顶部边距: {args.summary_top_margin}px")
        print(f"📝 Book summary右边距: {args.summary_right_margin}px")
        print(
            f"📚 书籍图标大小: {args.icon_size}px {'(自动计算)' if args.icon_size == 0 else '(用户设定)'}"
        )
        if args.icon_vertical_offset != 0:
            print(f"📚 图标垂直偏移: {args.icon_vertical_offset:+d}px")

    # 批量处理书籍MP4 clips
    success = process_all_books(
        font_size=args.font_size,
        force=args.force,
        debug=args.debug,
        language=args.language,
        cover_preserve_aspect=cover_preserve_aspect,
        video_width_ratio=args.video_width,
        video_align_right=video_align_right,
        font_path=args.font_path,
        font_weight=args.font_weight,
        force_single_line=args.force_single_line,
        fixed_font_size=args.fixed_font_size,
        show_book_summary=not args.no_book_summary,
        summary_font_size=args.summary_font_size,
        summary_top_margin=args.summary_top_margin,
        summary_right_margin=args.summary_right_margin,
        summary_icon_size=args.icon_size,
        icon_vertical_offset=args.icon_vertical_offset,
        title_top_margin=args.title_top_margin,
    )

    if success:
        print(f"\n🎉 书籍MP4 Clip生成任务完成!")
        print(f"💡 布局优化说明:")
        print(f"   - 封面现在在左半边居中显示，保持原始比例")
        print(
            f"   - 右侧视频缩小到 {args.video_width*100:.1f}% 并{'右对齐' if video_align_right else '居中对齐'}"
        )
        print(f"   - 可使用不同参数调整布局效果")
        sys.exit(0)
    else:
        print(f"\n❌ 书籍MP4 Clip生成任务失败!")
        sys.exit(1)


if __name__ == "__main__":
    main()
