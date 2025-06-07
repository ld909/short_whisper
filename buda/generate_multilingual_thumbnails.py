"""
多语言视频封面生成工具（专用于en和ko语言）

功能说明:
此脚本用于为视频批量生成英语和韩语封面。从thumbnail_base目录中随机选择
背景图片，并将多语言关键词/短语添加到封面上。

主要特点:
- 以key_words目录作为唯一的依赖源头，不再依赖mp4_with_audio目录
- 只要有关键词文件，就会生成对应的封面，即使没有视频文件

输入:
- 背景图片: [媒体路径]/thumbnail_base/[图片文件]
- 多语言关键词: [媒体路径]/key_words/[频道名称]/[语言代码]/[视频名称].json

输出:
- 生成的封面: [媒体路径]/thumbnail/[频道名称]/[语言代码]/[视频名称].png

使用方法:
1. 基本使用: python generate_multilingual_thumbnails.py
2. 指定频道: python generate_multilingual_thumbnails.py -c 频道名称
3. 指定视频: python generate_multilingual_thumbnails.py -v 视频名称
4. 调整文字大小: python generate_multilingual_thumbnails.py --font_size 50
5. 设置字体颜色: python generate_multilingual_thumbnails.py --font_color white
6. 设置文字描边: python generate_multilingual_thumbnails.py --stroke_width 2 --stroke_color black
7. 设置字体粗细: python generate_multilingual_thumbnails.py --font_weight 700
8. 关闭文字描边: python generate_multilingual_thumbnails.py --no_stroke
9. 随机选择关键词高亮: python generate_multilingual_thumbnails.py --random_highlight
"""

import os
import json
import random
import argparse
import platform
import glob
import re
from PIL import Image, ImageDraw, ImageFont, ImageColor

# 支持的语言及其代码（仅限英语和韩语）
LANGUAGES = {
    "English": "en",
    "Korean": "ko",
}

# 苹果风格的颜色
APPLE_WHITE = "white"
APPLE_BLACK = "black"
APPLE_GREEN = "#33cc33"  # 苹果风格的绿色


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


def get_font_path(language, font_weight=400):
    """根据语言获取合适的字体路径，支持字体粗细选择"""
    # 根据操作系统设置不同的字体路径
    system = platform.system()
    if system == "Darwin":  # macOS
        base_font_dir = "/Users/donghaoliu/doc/short_whisper/fonts"
    else:  # 默认为Linux/Ubuntu
        base_font_dir = "/home/dhl/Documents/short_whisper/fonts"

    # 为不同语言指定默认字体
    language_font_dirs = {
        "English": "Noto_Sans_EN",
        "Korean": "Noto_Sans_KR",
    }

    # 根据字体粗细选择合适的字体文件
    weight_patterns = {
        100: ["Thin", "100"],
        200: ["ExtraLight", "200"],
        300: ["Light", "300"],
        400: ["Regular", "400", ""],  # 普通/常规字体
        500: ["Medium", "500"],
        600: ["SemiBold", "600"],
        700: ["Bold", "700"],
        800: ["ExtraBold", "800"],
        900: ["Black", "900"],
    }

    # 获取最接近指定粗细的值
    closest_weight = min(weight_patterns.keys(), key=lambda x: abs(x - font_weight))
    weight_keywords = weight_patterns[closest_weight]

    if language in language_font_dirs:
        font_dir = os.path.join(base_font_dir, language_font_dirs[language])
        if os.path.exists(font_dir):
            # 尝试找到匹配指定粗细的字体
            font_files = glob.glob(os.path.join(font_dir, "*.ttf"))

            # 首先尝试精确匹配指定粗细的字体
            for keyword in weight_keywords:
                for font_file in font_files:
                    if keyword in os.path.basename(font_file):
                        return font_file, closest_weight

            # 如果没有找到匹配的粗细，使用可变字体或任意可用字体
            variable_fonts = [
                f for f in font_files if "Variable" in os.path.basename(f)
            ]
            if variable_fonts:
                return variable_fonts[0], closest_weight
            elif font_files:
                return font_files[0], closest_weight

    # 如果没有找到特定语言的字体，使用默认字体
    default_font = os.path.join(
        base_font_dir, "Noto_Sans_EN/NotoSans-VariableFont_wdth,wght.ttf"
    )
    if os.path.exists(default_font):
        return default_font, closest_weight
    else:
        # 尝试找到任何可用的字体
        all_fonts = glob.glob(os.path.join(base_font_dir, "**/*.ttf"), recursive=True)
        if all_fonts:
            return all_fonts[0], closest_weight
        else:
            raise FileNotFoundError(f"找不到任何可用的字体文件在 {base_font_dir}")


def get_video_background_image(media_path, channel, language_code, video_name):
    """从thumbnail_base目录中随机选择背景图片"""
    # 构建thumbnail_base目录路径
    thumbnail_base_dir = os.path.join(media_path, "thumbnail_base")

    if not os.path.exists(thumbnail_base_dir):
        print(f"错误: thumbnail_base目录不存在 {thumbnail_base_dir}")
        return None

    # 获取所有图片文件，排除以点开头的文件（mac生成的隐藏文件）
    image_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"]
    image_files = []

    for file in os.listdir(thumbnail_base_dir):
        # 排除以点开头的文件
        if file.startswith("."):
            continue

        # 检查文件扩展名
        file_lower = file.lower()
        if any(file_lower.endswith(ext) for ext in image_extensions):
            full_path = os.path.join(thumbnail_base_dir, file)
            if os.path.isfile(full_path):
                image_files.append(full_path)

    if not image_files:
        print(f"错误: thumbnail_base目录中没有找到可用的图片文件 {thumbnail_base_dir}")
        return None

    # 随机选择一张图片
    selected_image = random.choice(image_files)
    print(f"选择背景图片: {os.path.basename(selected_image)}")

    return selected_image


def load_multilingual_titles(media_path, channel, video_name):
    """加载多语言关键词/短语"""
    result = {}

    # 映射语言代码到语言名称
    code_to_lang = {code: lang for lang, code in LANGUAGES.items()}

    # 遍历支持的语言
    for lang_code, lang_name in code_to_lang.items():
        # 构建关键词文件路径
        key_phrases_file = os.path.join(
            media_path, "key_words", channel, lang_code, f"{video_name}.json"
        )

        if not os.path.exists(key_phrases_file):
            print(f"警告: 找不到关键词文件 {key_phrases_file}")
            continue

        try:
            with open(key_phrases_file, "r", encoding="utf-8") as f:
                data = json.load(f)

                # 从JSON中获取关键词和标题
                if "key_phrases" in data:
                    result[lang_name] = data["key_phrases"]
                elif "title" in data:
                    # 如果没有关键词，使用标题
                    result[lang_name] = data["title"]
                    print(f"警告: {lang_name}语言缺少关键词，使用标题替代")

        except json.JSONDecodeError:
            print(f"错误: 无法解析JSON文件 {key_phrases_file}")
        except Exception as e:
            print(f"加载关键词文件时出错: {e}")

    return result


def highlight_keywords(
    text, font_color=APPLE_WHITE, highlight_color=APPLE_GREEN, random_highlight=False
):
    """处理文本，统一使用指定的字体颜色，不再使用高亮

    参数:
    - text: 要处理的文本
    - font_color: 文字颜色（统一使用这个颜色）
    - highlight_color: 高亮文字颜色（已废弃，不再使用）
    - random_highlight: 是否随机选择关键词高亮（已废弃，不再使用）
    """
    # 统一使用font_color，不再进行任何高亮处理
    return [(text, font_color)]


def create_thumbnail(
    bg_image_path,
    title,
    output_path,
    language,
    font_size=45,
    font_color=APPLE_WHITE,
    stroke_width=2,
    stroke_color=APPLE_BLACK,
    font_weight=400,
    no_stroke=False,
    random_highlight=False,
    left_margin=30,
):
    """创建单个缩略图"""
    try:
        # 加载背景图片
        img = Image.open(bg_image_path)

        # 直接调整大小为1280x720，不保持原始比例
        img = img.resize(
            (1280, 720),
            Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS,
        )

        # 创建绘图对象
        draw = ImageDraw.Draw(img)

        # 获取合适的字体
        font_path, actual_weight = get_font_path(language, font_weight)
        print(f"  - 使用字体: {font_path}, 粗细: {font_weight}")

        # 加载字体
        font = ImageFont.truetype(font_path, font_size)

        # 检查是否是可变字体并设置粗细
        if "Variable" in os.path.basename(font_path):
            try:
                # 尝试获取字体变体信息
                variation_axes = font.get_variation_axes()

                # 查找权重轴
                weight_axis = None
                for axis in variation_axes:
                    axis_name = axis.get("name", b"").decode("utf-8", "ignore").lower()
                    if "weight" in axis_name:
                        weight_axis = axis
                        break

                if weight_axis:
                    # 确保权重值在允许的范围内
                    min_weight = weight_axis.get("minimum", 100)
                    max_weight = weight_axis.get("maximum", 900)
                    adjusted_weight = max(min_weight, min(max_weight, font_weight))

                    # 检查字体是否有宽度轴
                    has_width_axis = any(
                        "width"
                        in axis.get("name", b"").decode("utf-8", "ignore").lower()
                        for axis in variation_axes
                    )

                    if has_width_axis:
                        # 如果字体同时有宽度和粗细轴，需要同时设置两个值
                        # 设置宽度为默认值100，粗细为指定值
                        font.set_variation_by_axes([adjusted_weight, 100])
                        print(f"  - 设置可变字体粗细: {adjusted_weight}, 宽度: 100")
                    else:
                        # 只有粗细轴，只设置一个值
                        font.set_variation_by_axes([adjusted_weight])
                        print(f"  - 设置可变字体粗细: {adjusted_weight}")
            except Exception as e:
                print(f"  - 无法设置字体粗细: {e}")

        # 高亮关键词
        highlighted_text = highlight_keywords(
            title, font_color, APPLE_GREEN, random_highlight
        )

        # 计算文本需要的行数
        max_width = img.width * 0.6  # 文本最大宽度为图像宽度的60%
        x_position = left_margin  # 文本位置从左边界偏移指定像素

        # 处理文本换行
        text_lines = []
        current_line = []
        current_line_width = 0

        for text_segment, color in highlighted_text:
            words = (
                text_segment.split()
                if language not in ["Japanese", "Chinese", "Korean"]
                and " " in text_segment
                else list(text_segment)
            )

            for word in words:
                word_with_space = (
                    word + " "
                    if language not in ["Japanese", "Chinese", "Korean"]
                    and not word.endswith(" ")
                    else word
                )
                bbox = draw.textbbox((0, 0), word_with_space, font=font)
                word_width = bbox[2] - bbox[0]

                if current_line_width + word_width <= max_width:
                    current_line.append((word_with_space, color))
                    current_line_width += word_width
                else:
                    text_lines.append(current_line)
                    current_line = [(word_with_space, color)]
                    current_line_width = word_width

        if current_line:
            text_lines.append(current_line)

        # 计算文本总高度
        line_height = font_size * 1.5
        text_height = len(text_lines) * line_height

        # 计算文本的垂直位置（居中）
        y_position = (img.height - text_height) // 2

        # 绘制文本
        for line in text_lines:
            x = x_position

            for text_segment, color in line:
                # 绘制描边
                if stroke_width > 0 and not no_stroke:
                    for offset_x in range(-stroke_width, stroke_width + 1):
                        for offset_y in range(-stroke_width, stroke_width + 1):
                            if offset_x == 0 and offset_y == 0:
                                continue
                            draw.text(
                                (x + offset_x, y_position + offset_y),
                                text_segment,
                                font=font,
                                fill=stroke_color,
                            )

                # 绘制文本
                draw.text((x, y_position), text_segment, font=font, fill=color)

                # 更新x位置
                bbox = draw.textbbox((0, 0), text_segment, font=font)
                x += bbox[2] - bbox[0]

            y_position += int(line_height)

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 保存图片
        img.save(output_path)
        print(f"成功创建封面: {output_path}")
        return True

    except Exception as e:
        print(f"创建封面时出错: {e}")
        return False


def generate_thumbnails(
    channel=None,
    video_name=None,
    font_size=80,
    font_color=APPLE_WHITE,
    stroke_width=2,
    stroke_color=APPLE_BLACK,
    font_weight=400,
    no_stroke=True,
    random_highlight=False,
    left_margin=80,
):
    """生成英语和韩语视频封面"""
    media_path = get_base_media_path()

    # 固定使用英语和韩语
    languages = ["English", "Korean"]

    # 频道目录列表
    if channel:
        channels = [channel]
    else:
        # 从mp4_with_audio目录获取频道列表
        mp4_with_audio_dir = os.path.join(media_path, "mp4_with_audio")
        if not os.path.exists(mp4_with_audio_dir):
            print(f"错误: mp4_with_audio目录不存在: {mp4_with_audio_dir}")
            return
        channels = [
            d
            for d in os.listdir(mp4_with_audio_dir)
            if os.path.isdir(os.path.join(mp4_with_audio_dir, d))
            and not d.startswith(".")
        ]

    print(f"处理 {len(channels)} 个频道")

    for current_channel in channels:
        print(f"\n处理频道: {current_channel}")

        # 检查mp4_with_audio目录下的频道目录（可选）
        channel_mp4_dir = os.path.join(media_path, "mp4_with_audio", current_channel)
        if not os.path.exists(channel_mp4_dir):
            print(f"注意: mp4_with_audio频道目录不存在 {channel_mp4_dir}，但继续处理")

        # 检查关键词目录
        channel_keywords_dir = os.path.join(media_path, "key_words", current_channel)
        if not os.path.exists(channel_keywords_dir):
            print(f"跳过: 关键词频道目录不存在 {channel_keywords_dir}")
            continue

        # 获取支持的所有语言代码目录（仅检查key_words目录）
        lang_dirs = []
        for lang in languages:
            lang_code = LANGUAGES.get(lang, lang.lower())

            # 仅检查key_words目录存在（mp4_with_audio目录可选）
            mp4_lang_dir = os.path.join(channel_mp4_dir, lang_code)
            keywords_lang_dir = os.path.join(channel_keywords_dir, lang_code)

            if os.path.exists(keywords_lang_dir):
                lang_dirs.append((lang, lang_code, mp4_lang_dir, keywords_lang_dir))
                if not os.path.exists(mp4_lang_dir):
                    print(f"注意: {lang} 语言的mp4目录不存在 {mp4_lang_dir}，但继续处理")

        if not lang_dirs:
            print(f"跳过: 频道 {current_channel} 下没有找到任何支持的语言目录")
            continue

        # 从第一个语言的key_words目录获取所有视频名称（基于JSON文件）
        first_lang_keywords_dir = lang_dirs[0][3]

        # 视频文件列表（基于key_words目录中的JSON文件）
        if video_name:
            video_files = [f"{video_name}.json"]
        else:
            video_files = [
                f
                for f in os.listdir(first_lang_keywords_dir)
                if f.endswith(".json") and not f.startswith(".")
            ]

        print(f"找到 {len(video_files)} 个关键词文件")

        for video_file in video_files:
            video_name_no_ext = os.path.splitext(video_file)[0]
            print(f"\n处理视频: {video_name_no_ext}")

            # 加载多语言关键词
            key_phrases = load_multilingual_titles(
                media_path, current_channel, video_name_no_ext
            )
            if not key_phrases:
                print(f"跳过: 未找到有效的关键词数据")
                continue

            # 为每种语言创建封面
            for language in languages:
                lang_code = LANGUAGES.get(language, language.lower())

                # 如果没有该语言的关键词，跳过
                if language not in key_phrases:
                    print(f"跳过: 找不到 {language} 关键词")
                    continue

                # 检查mp4文件是否存在（仅作提示，不影响封面生成）
                mp4_file = os.path.join(
                    media_path,
                    "mp4_with_audio",
                    current_channel,
                    lang_code,
                    f"{video_name_no_ext}.mp4",
                )
                if not os.path.exists(mp4_file):
                    print(f"注意: 找不到对应的 {language} 视频文件 {mp4_file}，但依然生成封面")

                key_phrase = key_phrases[language]

                # 从thumbnail_base目录中选择背景图片
                try:
                    bg_image = get_video_background_image(
                        media_path, current_channel, lang_code, video_name_no_ext
                    )
                    if bg_image is None:
                        print(f"跳过: 无法获取 {language} 背景图片")
                        continue
                except Exception as e:
                    print(f"错误: {e}")
                    continue

                # 设置输出路径
                output_dir = os.path.join(
                    media_path, "thumbnail", current_channel, lang_code
                )
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"{video_name_no_ext}.png")

                # 检查封面是否已存在
                if os.path.exists(output_path):
                    print(f"跳过 {language}: 封面已存在 {output_path}")
                    continue

                print(f"为 {language} 创建封面:")
                print(f"  - 关键词: {key_phrase}")
                print(f"  - 背景图: {os.path.basename(bg_image)}")
                print(f"  - 输出路径: {output_path}")

                # 创建缩略图
                success = create_thumbnail(
                    bg_image,
                    key_phrase,
                    output_path,
                    language,
                    font_size=font_size,
                    font_color=font_color,
                    stroke_width=stroke_width,
                    stroke_color=stroke_color,
                    font_weight=font_weight,
                    no_stroke=no_stroke,
                    random_highlight=random_highlight,
                    left_margin=left_margin,
                )


def main():
    parser = argparse.ArgumentParser(description="生成英语和韩语视频封面")
    parser.add_argument("-c", "--channel", help="指定要处理的频道")
    parser.add_argument("-v", "--video", help="指定要处理的视频名称（不含扩展名）")
    parser.add_argument("--font_size", type=int, default=80, help="字体大小")
    parser.add_argument("--font_color", default=APPLE_WHITE, help="字体颜色")
    parser.add_argument(
        "--stroke_width", type=int, default=2, help="文字描边宽度（像素）"
    )
    parser.add_argument("--stroke_color", default=APPLE_BLACK, help="文字描边颜色")
    parser.add_argument(
        "--font_weight", type=int, default=400, help="字体粗细 (100-900)"
    )
    parser.add_argument("--no_stroke", action="store_true", default=True, help="关闭文字描边")
    parser.add_argument(
        "--random_highlight", action="store_true", help="随机选择关键词高亮"
    )
    parser.add_argument(
        "--left_margin", type=int, default=80, help="文字距离左边界的像素距离"
    )
    parser.add_argument("--debug", action="store_true", help="打印调试信息")

    args = parser.parse_args()

    if args.debug:
        # 打印字体目录信息
        system = platform.system()
        if system == "Darwin":  # macOS
            base_font_dir = "/Users/donghaoliu/doc/short_whisper/fonts"
        else:  # 默认为Linux/Ubuntu
            base_font_dir = "/home/dhl/Documents/short_whisper/fonts"

        print("\n字体目录信息:")
        for lang, font_dir in {
            "English": "Noto_Sans_EN",
            "Korean": "Noto_Sans_KR",
        }.items():
            full_dir = os.path.join(base_font_dir, font_dir)
            if os.path.exists(full_dir):
                fonts = glob.glob(os.path.join(full_dir, "*.ttf"))
                print(f"  {lang}: {len(fonts)} 个字体文件")
                for font in fonts:
                    print(f"    - {os.path.basename(font)}")
                    # 测试是否支持变体设置
                    try:
                        tt_font = ImageFont.truetype(font, 24)
                        axes = tt_font.get_variation_axes()
                        if axes:
                            print(f"      支持变体设置: {axes}")
                    except Exception as e:
                        pass
            else:
                print(f"  {lang}: 目录不存在 {full_dir}")

    generate_thumbnails(
        channel=args.channel,
        video_name=args.video,
        font_size=args.font_size,
        font_color=args.font_color,
        stroke_width=args.stroke_width,
        stroke_color=args.stroke_color,
        font_weight=args.font_weight,
        no_stroke=args.no_stroke,
        random_highlight=args.random_highlight,
        left_margin=args.left_margin,
    )


if __name__ == "__main__":
    main()
