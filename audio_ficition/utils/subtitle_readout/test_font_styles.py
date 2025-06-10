#!/usr/bin/env python3
"""
字体样式测试脚本
用于测试不同字体粗细、字号和描边效果

使用方法:
# 使用默认字幕文件（故事1的word level字幕）
python test_font_styles.py --font-weight bold --font-size 24 --outline-width 3

# 指定故事索引（自动使用word level字幕）
python test_font_styles.py --story 1 --font-weight bold
python test_font_styles.py --story 5 --font-size 28

# 手动指定字幕文件
python test_font_styles.py --input-srt /path/to/custom.srt --font-weight medium

# 手动指定字幕目录
python test_font_styles.py --srt-dir /custom/path/to/srt_merge --story 3

参数:
--story: 故事索引，自动使用对应的word level字幕 (格式: {story}_word.srt)
--srt-dir: 字幕目录路径，默认自动检测Mac或Ubuntu路径
--input-srt: 手动指定SRT文件路径，会覆盖 --story 参数
--font-weight: 字体粗细 (extra-light, light, regular, medium, semi-bold, bold, extra-bold) 或数字 (100-900)
--font-size: 字体大小 (默认: 24)
--outline-width: 描边粗细 (默认: 2)
"""

import argparse
import os
import sys
from datetime import timedelta
import srt

# 添加当前目录到Python路径，以便导入本地模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from add_fade import select_font_by_weight


def create_test_ass_file(
    input_srt_path,
    output_ass_path,
    font_weight="regular",
    font_size=24,
    outline_width=2,
    font_dir="../font/en/",
    video_width=1920,
    video_height=1080,
):
    """
    创建测试用的ASS字幕文件

    Args:
        input_srt_path: 输入SRT文件路径
        output_ass_path: 输出ASS文件路径
        font_weight: 字体粗细
        font_size: 字体大小
        outline_width: 描边粗细
        font_dir: 字体目录
        video_width: 视频宽度
        video_height: 视频高度
    """

    # 处理数字权重字符串转换
    if font_weight.isdigit():
        font_weight = int(font_weight)

    # 自动选择字体
    font_path, font_name = select_font_by_weight(font_weight, font_dir)
    print(f"选择的字体: {font_name} ({os.path.basename(font_path)})")
    print(f"字体大小: {font_size}")
    print(f"描边粗细: {outline_width}")

    # 读取SRT文件
    try:
        with open(input_srt_path, "r", encoding="utf-8") as f:
            srt_content = f.read()
        subtitles = list(srt.parse(srt_content))
    except Exception as e:
        print(f"读取SRT文件时出错: {e}")
        return

    # ASS头部
    ass_header = f"""[Script Info]
Title: Font Test Subtitles
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,{outline_width},0,2,10,10,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # 转换时间格式
    def srt_time_to_ass_time(td):
        """将timedelta转换为ASS时间格式 H:MM:SS.cc"""
        total_seconds = td.total_seconds()
        hours = int(total_seconds / 3600)
        minutes = int((total_seconds % 3600) / 60)
        seconds = int(total_seconds % 60)
        centiseconds = int((total_seconds - int(total_seconds)) * 100)
        return f"{hours}:{minutes:02}:{seconds:02}.{centiseconds:02}"

    # 生成对话行
    dialogues = []
    for subtitle in subtitles:
        # 处理文本，替换换行符
        text = subtitle.content.replace("\n", "\\N")

        # 添加字体覆盖标签确保使用正确的字体
        font_override = f"{{\\fn{font_name}}}{{\\fs{font_size}}}"
        text_with_font = f"{font_override}{text}"

        # 创建对话行
        dialogue = f"Dialogue: 0,{srt_time_to_ass_time(subtitle.start)},{srt_time_to_ass_time(subtitle.end)},Default,,0,0,0,,{text_with_font}"
        dialogues.append(dialogue)

    # 写入ASS文件
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        for dialogue in dialogues:
            f.write(dialogue + "\n")

    print(f"✅ ASS文件已生成: {output_ass_path}")
    return output_ass_path


def create_test_video(ass_file_path, input_video="1.mp4", output_video=None):
    """
    创建测试视频（可选功能）

    Args:
        ass_file_path: ASS字幕文件路径
        input_video: 输入视频文件
        output_video: 输出视频文件
    """
    import subprocess

    if output_video is None:
        # 根据字幕文件名生成输出视频名
        base_name = os.path.splitext(os.path.basename(ass_file_path))[0]
        output_video = f"test_{base_name}.mp4"

    # 检查输入视频是否存在
    if not os.path.exists(input_video):
        print(f"⚠️  输入视频文件不存在: {input_video}")
        print("   请确保当前目录有 1.mp4 文件，或者手动使用以下命令:")
        print(
            f'   ffmpeg -i your_video.mp4 -vf "ass={ass_file_path}" -c:a copy {output_video}'
        )
        return

    # FFmpeg命令
    cmd = [
        "ffmpeg",
        "-y",  # -y 覆盖输出文件
        "-i",
        input_video,
        "-vf",
        f"ass={ass_file_path}",
        "-c:a",
        "copy",
        output_video,
    ]

    try:
        print(f"🎬 正在生成测试视频: {output_video}")
        print(f"   命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ 测试视频已生成: {output_video}")
        else:
            print(f"❌ 视频生成失败:")
            print(f"   错误信息: {result.stderr}")
    except FileNotFoundError:
        print("❌ 未找到 ffmpeg，请先安装 ffmpeg")
        print("   macOS: brew install ffmpeg")
    except Exception as e:
        print(f"❌ 生成视频时出错: {e}")


def main():
    parser = argparse.ArgumentParser(description="字体样式测试脚本")

    # 字体相关参数
    parser.add_argument(
        "--font-weight",
        default="regular",
        help="字体粗细: extra-light, light, regular, medium, semi-bold, bold, extra-bold 或数字 100-900 (默认: regular)",
    )

    parser.add_argument("--font-size", type=int, default=24, help="字体大小 (默认: 24)")

    parser.add_argument(
        "--outline-width", type=int, default=2, help="描边粗细 (默认: 2)"
    )

    # 文件路径参数
    parser.add_argument(
        "--input-srt",
        help="输入SRT文件路径，如果不指定且不提供--story参数，将使用默认字幕",
    )

    parser.add_argument(
        "--story",
        type=str,
        help="指定故事索引，将自动使用对应的word level合并字幕文件 (格式: {story}_word.srt)",
    )

    parser.add_argument(
        "--srt-dir",
        help="字幕目录路径，默认自动检测 Mac(/Volumes/dhl/audio/scifi/srt_merge) 或 Ubuntu(/mnt/dhl/audio/scifi/srt_merge)",
    )

    parser.add_argument("--output-ass", help="输出ASS文件路径 (默认: 根据参数自动生成)")

    parser.add_argument(
        "--font-dir", default="../font/en/", help="字体目录路径 (默认: ../font/en/)"
    )

    # 视频相关参数
    parser.add_argument(
        "--video-width", type=int, default=1920, help="视频宽度 (默认: 1920)"
    )

    parser.add_argument(
        "--video-height", type=int, default=1080, help="视频高度 (默认: 1080)"
    )

    # 可选功能
    parser.add_argument(
        "--create-video", action="store_true", help="是否同时生成测试视频"
    )

    parser.add_argument(
        "--input-video", default="1.mp4", help="输入视频文件 (默认: 1.mp4)"
    )

    # 列出可用字体
    parser.add_argument("--list-fonts", action="store_true", help="列出可用的字体")

    args = parser.parse_args()

    # 自动检测字幕目录路径
    if args.srt_dir:
        merge_srt_dir = args.srt_dir
    else:
        # 自动检测系统路径
        mac_path = "/Volumes/dhl/audio/scifi/srt_merge"
        ubuntu_path = "/mnt/dhl/audio/scifi/srt_merge"

        if os.path.exists(mac_path):
            merge_srt_dir = mac_path
            print(f"🍎 检测到Mac系统，使用字幕目录: {merge_srt_dir}")
        elif os.path.exists(ubuntu_path):
            merge_srt_dir = ubuntu_path
            print(f"🐧 检测到Ubuntu系统，使用字幕目录: {merge_srt_dir}")
        else:
            print(f"❌ 未找到字幕目录，请检查路径:")
            print(f"   Mac: {mac_path}")
            print(f"   Ubuntu: {ubuntu_path}")
            print(f"   或使用 --srt-dir 手动指定")
            return

    # 处理故事索引和字幕路径
    if args.story:
        # 总是使用word level字幕（格式: {story}_word.srt）
        args.input_srt = os.path.join(merge_srt_dir, f"{args.story}_word.srt")
        print(f"🎯 指定故事 {args.story}，使用word level字幕: {args.input_srt}")
    elif not args.input_srt:
        # 如果没有指定故事和输入文件，使用默认的故事1的word字幕
        args.input_srt = os.path.join(merge_srt_dir, "1_word.srt")
        print(f"📝 使用默认字幕文件: {args.input_srt}")

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

    # 检查输入文件是否存在
    if not os.path.exists(args.input_srt):
        print(f"❌ 输入SRT文件不存在: {args.input_srt}")
        return

    # 生成输出文件名
    if args.output_ass is None:
        # 根据参数生成文件名
        weight_str = str(args.font_weight).replace("-", "_")
        args.output_ass = (
            f"test_{weight_str}_size{args.font_size}_outline{args.outline_width}.ass"
        )

    print(f"📋 测试配置:")
    print(f"   输入SRT: {args.input_srt}")
    print(f"   输出ASS: {args.output_ass}")
    print(f"   字体粗细: {args.font_weight}")
    print(f"   字体大小: {args.font_size}")
    print(f"   描边粗细: {args.outline_width}")
    print()

    # 生成ASS文件
    ass_file = create_test_ass_file(
        input_srt_path=args.input_srt,
        output_ass_path=args.output_ass,
        font_weight=args.font_weight,
        font_size=args.font_size,
        outline_width=args.outline_width,
        font_dir=args.font_dir,
        video_width=args.video_width,
        video_height=args.video_height,
    )

    # 可选：生成测试视频
    if args.create_video:
        create_test_video(ass_file, args.input_video)

    print(f"\n💡 使用说明:")
    print(f"   1. 字幕文件已生成: {args.output_ass}")
    print(f"   2. 字幕来源: {args.input_srt}")
    print(f"      📁 ASR合并字幕目录: {merge_srt_dir}")
    print(f"      🔹 使用格式: {{story_index}}_word.srt (word level 字幕)")
    print(f"      📌 示例: 1_word.srt, 2_word.srt, 3_word.srt ...")
    print(f"   3. 要生成视频，运行:")
    print(
        f'      ffmpeg -i {args.input_video} -vf "ass={args.output_ass}" -c:a copy output.mp4'
    )
    print(f"   4. 或者使用 --create-video 参数自动生成测试视频")


if __name__ == "__main__":
    main()
