#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化版字幕烧录工具

直接读取SRT字幕文件，将其烧录到MP4视频中，不生成ASS文件。
支持自定义字体、字号、颜色等参数，支持根据字体粗细自动选择字体文件。

使用方法:
python burn_subtitles_to_mp4.py -v video.mp4 -s subtitle.srt -o output.mp4

参数说明:
- -v, --video: 输入视频文件路径
- -s, --subtitle: 输入字幕文件路径（SRT格式）
- -o, --output: 输出视频文件路径
- --font-size: 字体大小，默认16
- --font-color: 字体颜色，默认白色(FFFFFF)
- --outline-color: 字幕描边颜色，默认黑色(000000)
- --outline-width: 描边宽度，默认2
- --margin-v: 底部边距，默认20
- --font-path: 自定义字体文件路径
- --font-weight: 字体粗细 (extra-light, light, regular, medium, semi-bold, bold, extra-bold) 或数字 (100-900)
- --font-dir: 字体目录路径，默认 font/en/
- --gpu: 启用GPU硬件加速
- --list-fonts: 列出可用的字体

字体粗细示例:
python burn_subtitles_to_mp4.py -v video.mp4 -s subtitle.srt -o output.mp4 --font-weight bold
python burn_subtitles_to_mp4.py -v video.mp4 -s subtitle.srt -o output.mp4 --font-weight 700
"""

import os
import argparse
import subprocess
import sys
import logging
import platform
import multiprocessing

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def select_font_by_weight(font_weight, font_dir="font/en/"):
    """
    根据字体粗细选择对应的字体文件

    Args:
        font_weight: 字体粗细，可以是字符串("light", "normal", "medium", "bold", "extra-bold", "black")
                    或数字(100-900)
        font_dir: 字体文件目录

    Returns:
        tuple: (font_file_path, font_display_name)
    """
    # 定义字体映射
    font_mapping = {
        # 字符串映射
        "extra-light": ("Oxanium-ExtraLight.ttf", "Oxanium ExtraLight"),
        "light": ("Oxanium-Light.ttf", "Oxanium Light"),
        "normal": ("Oxanium-Regular.ttf", "Oxanium Regular"),
        "regular": ("Oxanium-Regular.ttf", "Oxanium Regular"),
        "medium": ("Oxanium-Medium.ttf", "Oxanium Medium"),
        "semi-bold": ("Oxanium-SemiBold.ttf", "Oxanium SemiBold"),
        "bold": ("Oxanium-Bold.ttf", "Oxanium Bold"),
        "extra-bold": ("Oxanium-ExtraBold.ttf", "Oxanium ExtraBold"),
        "black": ("Oxanium-ExtraBold.ttf", "Oxanium ExtraBold"),
    }

    # 数字权重映射
    weight_to_file = {
        100: ("Oxanium-ExtraLight.ttf", "Oxanium ExtraLight"),
        200: ("Oxanium-ExtraLight.ttf", "Oxanium ExtraLight"),
        300: ("Oxanium-Light.ttf", "Oxanium Light"),
        400: ("Oxanium-Regular.ttf", "Oxanium Regular"),
        500: ("Oxanium-Medium.ttf", "Oxanium Medium"),
        600: ("Oxanium-SemiBold.ttf", "Oxanium SemiBold"),
        700: ("Oxanium-Bold.ttf", "Oxanium Bold"),
        800: ("Oxanium-ExtraBold.ttf", "Oxanium ExtraBold"),
        900: ("Oxanium-ExtraBold.ttf", "Oxanium ExtraBold"),
    }

    # 根据类型选择字体
    if isinstance(font_weight, str):
        font_key = font_weight.lower().replace("_", "-")
        if font_key in font_mapping:
            font_file, font_name = font_mapping[font_key]
        else:
            # 默认使用regular
            font_file, font_name = font_mapping["regular"]
            logger.warning(f"未知的字体粗细 '{font_weight}'，使用默认 Regular")
    elif isinstance(font_weight, int):
        # 找到最接近的权重
        closest_weight = min(weight_to_file.keys(), key=lambda x: abs(x - font_weight))
        font_file, font_name = weight_to_file[closest_weight]
        if font_weight != closest_weight:
            logger.info(f"字体权重 {font_weight} 映射到最接近的 {closest_weight}")
    else:
        # 默认使用regular
        font_file, font_name = font_mapping["regular"]
        logger.warning(f"无效的字体粗细类型，使用默认 Regular")

    font_path = os.path.join(font_dir, font_file)

    # 检查文件是否存在
    if not os.path.exists(font_path):
        logger.warning(f"字体文件不存在 {font_path}，使用默认可变字体")
        font_path = os.path.join(font_dir, "Oxanium-VariableFont_wght.ttf")
        font_name = "Oxanium"

    return font_path, font_name


# 默认字体映射（备用）
DEFAULT_FONTS = {
    "zh": "fonts/Noto_Sans_SC/NotoSansSC-VariableFont_wght.ttf",
    "en": "fonts/Noto_Sans_EN/NotoSans-VariableFont_wdth,wght.ttf",
    "ja": "fonts/Noto_Sans_JP/NotoSansJP-VariableFont_wght.ttf",
    "ko": "fonts/Noto_Sans_KR/NotoSansKR-VariableFont_wght.ttf",
    "vi": "fonts/Noto_Sans_VI/NotoSans-VariableFont_wdth,wght.ttf",
}

DEFAULT_FONT_NAMES = {
    "zh": "notosanssc",
    "en": "notosans",
    "ja": "notosansjp",
    "ko": "notosanskr",
    "vi": "notosans",
}


def check_ffmpeg():
    """检查ffmpeg是否可用"""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        logger.error("未找到ffmpeg，请先安装ffmpeg")
        return False


def check_gpu_support():
    """检查GPU支持情况"""
    system = platform.system()

    if system == "Darwin":  # macOS
        return True, "videotoolbox"
    elif system == "Linux":
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                return True, "cuda"
        except FileNotFoundError:
            pass

    return False, None


def detect_subtitle_language(srt_path):
    """简单检测字幕语言"""
    try:
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 简单的语言检测
        if any("\u4e00" <= char <= "\u9fff" for char in content):
            return "zh"  # 中文
        elif any(
            "\u3040" <= char <= "\u309f" or "\u30a0" <= char <= "\u30ff"
            for char in content
        ):
            return "ja"  # 日文
        elif any("\uac00" <= char <= "\ud7af" for char in content):
            return "ko"  # 韩文
        else:
            return "en"  # 默认英文
    except Exception:
        return "en"


def burn_subtitles(video_path, subtitle_path, output_path, **kwargs):
    """将字幕烧录到视频中"""

    # 参数设置
    font_size = kwargs.get("font_size", 16)
    font_color = kwargs.get("font_color", "FFFFFF")
    outline_color = kwargs.get("outline_color", "000000")
    outline_width = kwargs.get("outline_width", 2)
    margin_v = kwargs.get("margin_v", 20)
    font_path = kwargs.get("font_path")
    font_weight = kwargs.get("font_weight", "regular")
    font_dir = kwargs.get("font_dir", "font/en/")
    use_gpu = kwargs.get("use_gpu", False)

    # 自动检测字幕语言
    detected_lang = detect_subtitle_language(subtitle_path)
    logger.info(f"检测到字幕语言: {detected_lang}")

    # 选择字体
    if not font_path:
        # 使用字体粗细选择逻辑
        if detected_lang == "en":
            # 对于英文使用 Oxanium 字体系列
            font_path, font_name = select_font_by_weight(font_weight, font_dir)
            logger.info(f"选择的字体: {font_name} ({os.path.basename(font_path)})")
        else:
            # 对于其他语言使用默认字体
            default_font = DEFAULT_FONTS.get(detected_lang, DEFAULT_FONTS["en"])
            if os.path.exists(default_font):
                font_path = default_font
                font_name = DEFAULT_FONT_NAMES.get(
                    detected_lang, DEFAULT_FONT_NAMES["en"]
                )
            else:
                logger.warning(f"默认字体不存在: {default_font}，将使用系统默认字体")
                font_name = "arial"
    else:
        # 从字体路径提取字体名
        font_name = os.path.splitext(os.path.basename(font_path))[0].lower()

    # 构建ffmpeg命令
    cmd = ["ffmpeg"]

    # GPU加速设置
    hw_accel_used = False
    if use_gpu:
        has_gpu, gpu_type = check_gpu_support()
        if has_gpu:
            if gpu_type == "cuda":
                cmd.extend(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])
                hw_accel_used = True
                logger.info("启用NVIDIA GPU硬件加速")
            elif gpu_type == "videotoolbox":
                cmd.extend(["-hwaccel", "videotoolbox"])
                hw_accel_used = True
                logger.info("启用macOS VideoToolbox硬件加速")
        else:
            logger.warning("未检测到可用GPU，使用CPU处理")

    # 输入文件
    cmd.extend(["-i", video_path])

    # 字幕滤镜
    fonts_dir = os.path.dirname(font_path) if font_path else ""

    # 构建字幕样式
    force_style = (
        f"Fontname={font_name},"
        f"FontSize={font_size},"
        f"PrimaryColour=&H{font_color[:6]},"
        f"OutlineColour=&H{outline_color[:6]},"
        f"BorderStyle=1,"
        f"Outline={outline_width},"
        f"MarginV={margin_v}"
    )

    if hw_accel_used and gpu_type == "cuda":
        # GPU加速的字幕处理
        subtitle_filter = f"hwdownload,format=nv12,subtitles={subtitle_path}"
        if fonts_dir:
            subtitle_filter += f":fontsdir={fonts_dir}"
        subtitle_filter += f":force_style='{force_style}',hwupload_cuda"
    else:
        # CPU处理的字幕
        subtitle_filter = f"subtitles={subtitle_path}"
        if fonts_dir:
            subtitle_filter += f":fontsdir={fonts_dir}"
        subtitle_filter += f":force_style='{force_style}'"

    cmd.extend(["-vf", subtitle_filter])

    # 音频复制
    cmd.extend(["-c:a", "copy"])

    # 视频编码设置
    if hw_accel_used:
        if gpu_type == "cuda":
            cmd.extend(
                [
                    "-c:v",
                    "h264_nvenc",
                    "-preset",
                    "fast",
                    "-b:v",
                    "2M",
                    "-maxrate",
                    "3M",
                    "-bufsize",
                    "3M",
                ]
            )
        elif gpu_type == "videotoolbox":
            cmd.extend(["-c:v", "h264_videotoolbox", "-b:v", "2M", "-maxrate", "3M"])
    else:
        # CPU编码
        cpu_count = multiprocessing.cpu_count()
        cmd.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-threads",
                str(cpu_count),
                "-b:v",
                "2M",
            ]
        )

    # 覆盖输出文件
    cmd.extend(["-y", output_path])

    # 创建输出目录
    output_dir = os.path.dirname(output_path)
    if output_dir:  # 只有当输出目录不为空时才创建
        os.makedirs(output_dir, exist_ok=True)

    # 执行命令
    logger.info(f"开始处理: {os.path.basename(video_path)}")
    logger.info(f"使用字幕: {os.path.basename(subtitle_path)}")
    logger.info(f"输出文件: {output_path}")
    logger.info(f"FFmpeg命令: {' '.join(cmd)}")

    try:
        process = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"成功生成带字幕的视频: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"处理失败: {e.stderr}")
        if use_gpu and hw_accel_used:
            logger.warning("GPU加速失败，尝试使用CPU模式...")
            kwargs["use_gpu"] = False
            return burn_subtitles(video_path, subtitle_path, output_path, **kwargs)
        return False
    except Exception as e:
        logger.error(f"处理时出错: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description="将SRT字幕直接烧录到MP4视频中")
    parser.add_argument("-v", "--video", required=True, help="输入视频文件路径")
    parser.add_argument("-s", "--subtitle", required=True, help="输入字幕文件路径")
    parser.add_argument("-o", "--output", required=True, help="输出视频文件路径")
    parser.add_argument("--font-size", type=int, default=16, help="字体大小（默认16）")
    parser.add_argument(
        "--font-color", default="FFFFFF", help="字体颜色（十六进制，默认FFFFFF）"
    )
    parser.add_argument(
        "--outline-color", default="000000", help="描边颜色（十六进制，默认000000）"
    )
    parser.add_argument(
        "--outline-width", type=float, default=2, help="描边宽度（默认2）"
    )
    parser.add_argument("--margin-v", type=int, default=20, help="底部边距（默认20）")
    parser.add_argument("--font-path", help="自定义字体文件路径")
    parser.add_argument(
        "--font-weight",
        default="regular",
        help="字体粗细: extra-light, light, regular, medium, semi-bold, bold, extra-bold 或数字 100-900 (默认: regular)",
    )
    parser.add_argument(
        "--font-dir", default="font/en/", help="字体目录路径 (默认: font/en/)"
    )
    parser.add_argument("--gpu", action="store_true", help="启用GPU硬件加速")
    parser.add_argument("--list-fonts", action="store_true", help="列出可用的字体")

    args = parser.parse_args()

    # 列出字体选项
    if args.list_fonts:
        print("可用的字体粗细选项:")
        print(
            "  字符串选项: extra-light, light, regular, medium, semi-bold, bold, extra-bold"
        )
        print("  数字选项: 100 (最细) - 900 (最粗)")
        print("\n字体文件映射:")
        font_options = [
            ("extra-light", "Oxanium-ExtraLight.ttf"),
            ("light", "Oxanium-Light.ttf"),
            ("regular", "Oxanium-Regular.ttf"),
            ("medium", "Oxanium-Medium.ttf"),
            ("semi-bold", "Oxanium-SemiBold.ttf"),
            ("bold", "Oxanium-Bold.ttf"),
            ("extra-bold", "Oxanium-ExtraBold.ttf"),
        ]
        for weight, filename in font_options:
            print(f"  {weight:12} -> {filename}")
        return

    # 检查ffmpeg
    if not check_ffmpeg():
        sys.exit(1)

    # 检查输入文件
    if not os.path.exists(args.video):
        logger.error(f"视频文件不存在: {args.video}")
        sys.exit(1)

    if not os.path.exists(args.subtitle):
        logger.error(f"字幕文件不存在: {args.subtitle}")
        sys.exit(1)

    # 处理字体权重参数（支持数字字符串）
    font_weight = args.font_weight
    if args.font_weight.isdigit():
        font_weight = int(args.font_weight)

    # 处理字幕烧录
    success = burn_subtitles(
        args.video,
        args.subtitle,
        args.output,
        font_size=args.font_size,
        font_color=args.font_color,
        outline_color=args.outline_color,
        outline_width=args.outline_width,
        margin_v=args.margin_v,
        font_path=args.font_path,
        font_weight=font_weight,
        font_dir=args.font_dir,
        use_gpu=args.gpu,
    )

    if success:
        logger.info("字幕烧录完成！")
    else:
        logger.error("字幕烧录失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
