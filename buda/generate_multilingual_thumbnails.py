"""
多语言视频封面生成工具

功能说明:
此脚本用于为视频批量生成多语言封面。从指定路径随机选择背景图片，
并将多语言关键词/短语添加到封面上。支持根据不同语言自动选择合适的字体。

输入:
- 背景图片: [媒体路径]/thumbnail_base/
- 多语言关键词: [媒体路径]/key_words/[频道名称]/[语言代码]/[视频名称].json

输出:
- 生成的封面: [媒体路径]/thumbnail/[频道名称]/[语言代码]/[视频名称].png

使用方法:
1. 基本使用: python generate_multilingual_thumbnails.py
2. 指定频道: python generate_multilingual_thumbnails.py -c 频道名称
3. 指定视频: python generate_multilingual_thumbnails.py -v 视频名称
4. 指定语言: python generate_multilingual_thumbnails.py -l English Japanese
5. 调整文字大小: python generate_multilingual_thumbnails.py --font_size 50
6. 设置字体颜色: python generate_multilingual_thumbnails.py --font_color white
7. 设置文字描边: python generate_multilingual_thumbnails.py --stroke_width 2 --stroke_color black
8. 设置字体粗细: python generate_multilingual_thumbnails.py --font_weight 700
9. 关闭文字描边: python generate_multilingual_thumbnails.py --no_stroke
10. 随机选择关键词高亮: python generate_multilingual_thumbnails.py --random_highlight
"""

import os
import json
import random
import argparse
import platform
import glob
import re
from PIL import Image, ImageDraw, ImageFont, ImageColor

# 支持的语言及其代码
LANGUAGES = {
    "English": "en",
    "Japanese": "ja",
    "Vietnamese": "vi",
    "Korean": "ko",
    "Chinese": "zh",
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
        "Japanese": "Noto_Sans_JP",
        "Vietnamese": "Noto_Sans_VI",
        "Korean": "Noto_Sans_KR",
        "Chinese": "Noto_Sans_SC",  # 或者使用 Noto_Sans_TC 取决于简体/繁体需求
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


def get_random_background_image(media_path):
    """从指定路径随机选择一张背景图片"""
    background_dir = os.path.join(media_path, "thumbnail_base")
    if not os.path.exists(background_dir):
        raise FileNotFoundError(f"背景图片目录不存在: {background_dir}")

    image_files = []
    for ext in ["*.jpg", "*.jpeg", "*.png"]:
        image_files.extend(glob.glob(os.path.join(background_dir, ext)))

    if not image_files:
        raise FileNotFoundError(f"在 {background_dir} 中找不到任何图片")

    return random.choice(image_files)


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
    """高亮关键词，将关键词设置为绿色

    参数:
    - text: 要处理的文本
    - font_color: 普通文字颜色
    - highlight_color: 高亮文字颜色
    - random_highlight: 是否随机选择关键词高亮
    """
    highlighted_text = []

    if random_highlight:
        # 根据不同语言特点拆分文本
        if any(ord(c) > 127 for c in text):  # 检测是否包含非ASCII字符
            # 对于中日韩等语言，按字符拆分
            words = list(text)
        else:
            # 对于英语等拉丁语系，按空格拆分
            words = text.split()

        # 随机选择1-3个词高亮
        num_to_highlight = min(len(words), random.randint(1, 3))
        indices_to_highlight = sorted(
            random.sample(range(len(words)), num_to_highlight)
        )

        # 构建高亮文本
        for i, word in enumerate(words):
            if i in indices_to_highlight:
                highlighted_text.append((word, highlight_color))
            else:
                highlighted_text.append((word, font_color))

        # 如果是按空格拆分的，需要在单词之间添加空格
        if not any(ord(c) > 127 for c in text):
            spaced_text = []
            for i, (word, color) in enumerate(highlighted_text):
                if i < len(highlighted_text) - 1:
                    spaced_text.append((word + " ", color))
                else:
                    spaced_text.append((word, color))
            highlighted_text = spaced_text

        return highlighted_text

    # 传统方式: 查找可能的关键词（大写单词、引号内的内容等）
    # 对于所有语言，默认处理引号内的内容
    quote_pattern = r'["\']([^"\']+)["\']'

    # 尝试匹配引号内内容或全大写单词
    uppercase_pattern = r"\b([A-Z][A-Z]+)\b"

    # 将文本拆分为普通部分和高亮部分
    last_end = 0

    # 首先尝试匹配引号内的内容
    for match in re.finditer(quote_pattern, text):
        start, end = match.span()
        if start > last_end:
            highlighted_text.append((text[last_end:start], font_color))
        highlighted_text.append((match.group(1), highlight_color))
        last_end = end

    # 如果没有发现引号匹配，尝试匹配全大写单词（适用于英文）
    if not highlighted_text:
        for match in re.finditer(uppercase_pattern, text):
            start, end = match.span()
            if start > last_end:
                highlighted_text.append((text[last_end:start], font_color))
            highlighted_text.append((match.group(0), highlight_color))
            last_end = end

    # 添加最后一段文本
    if last_end < len(text):
        highlighted_text.append((text[last_end:], font_color))

    # 如果没有找到任何匹配，则返回原始文本
    if not highlighted_text:
        highlighted_text = [(text, font_color)]

    return highlighted_text


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
    languages=None,
    font_size=65,
    font_color=APPLE_WHITE,
    stroke_width=2,
    stroke_color=APPLE_BLACK,
    font_weight=400,
    no_stroke=False,
    random_highlight=False,
    left_margin=30,
):
    """生成多语言视频封面"""
    media_path = get_base_media_path()

    # 如果没有指定语言，使用所有支持的语言
    if not languages:
        languages = list(LANGUAGES.keys())

    # 频道目录列表
    if channel:
        channels = [channel]
    else:
        key_words_dir = os.path.join(media_path, "key_words")
        if not os.path.exists(key_words_dir):
            print(f"错误: 关键词目录不存在: {key_words_dir}")
            return
        channels = [
            d
            for d in os.listdir(key_words_dir)
            if os.path.isdir(os.path.join(key_words_dir, d)) and not d.startswith(".")
        ]

    print(f"处理 {len(channels)} 个频道")

    for current_channel in channels:
        print(f"\n处理频道: {current_channel}")

        channel_dir = os.path.join(media_path, "key_words", current_channel)
        if not os.path.exists(channel_dir):
            print(f"跳过: 频道目录不存在 {channel_dir}")
            continue

        # 获取支持的所有语言代码目录
        lang_dirs = []
        for lang in languages:
            lang_code = LANGUAGES.get(lang, lang.lower())
            lang_dir = os.path.join(channel_dir, lang_code)
            if os.path.exists(lang_dir):
                lang_dirs.append((lang, lang_code, lang_dir))

        if not lang_dirs:
            print(f"跳过: 频道 {current_channel} 下没有找到任何语言目录")
            continue

        # 从第一个语言目录获取所有视频名称
        first_lang_dir = lang_dirs[0][2]

        # 视频文件列表
        if video_name:
            video_files = [f"{video_name}.json"]
        else:
            video_files = [
                f
                for f in os.listdir(first_lang_dir)
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

                key_phrase = key_phrases[language]

                # 随机选择背景图片
                try:
                    bg_image = get_random_background_image(media_path)
                except FileNotFoundError as e:
                    print(f"错误: {e}")
                    continue

                # 设置输出路径
                output_dir = os.path.join(
                    media_path, "thumbnail", current_channel, lang_code
                )
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"{video_name_no_ext}.png")

                print(f"为 {language} 创建封面:")
                print(f"  - 关键词: {key_phrase}")
                print(f"  - 背景图: {os.path.basename(bg_image)}")
                print(f"  - 输出路径: {output_path}")

                # 创建缩略图
                create_thumbnail(
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
    parser = argparse.ArgumentParser(description="生成多语言视频封面")
    parser.add_argument("-c", "--channel", help="指定要处理的频道")
    parser.add_argument("-v", "--video", help="指定要处理的视频名称（不含扩展名）")
    parser.add_argument("-l", "--languages", nargs="+", help="指定要生成的语言列表")
    parser.add_argument("--font_size", type=int, default=60, help="字体大小")
    parser.add_argument("--font_color", default=APPLE_WHITE, help="字体颜色")
    parser.add_argument(
        "--stroke_width", type=int, default=2, help="文字描边宽度（像素）"
    )
    parser.add_argument("--stroke_color", default=APPLE_BLACK, help="文字描边颜色")
    parser.add_argument(
        "--font_weight", type=int, default=400, help="字体粗细 (100-900)"
    )
    parser.add_argument("--no_stroke", action="store_true", help="关闭文字描边")
    parser.add_argument(
        "--random_highlight", action="store_true", help="随机选择关键词高亮"
    )
    parser.add_argument(
        "--left_margin", type=int, default=30, help="文字距离左边界的像素距离"
    )
    parser.add_argument("--debug", action="store_true", help="打印调试信息")

    args = parser.parse_args()

    # 验证语言
    if args.languages:
        for lang in args.languages:
            if lang not in LANGUAGES:
                print(
                    f"警告: 不支持的语言 {lang}，支持的语言有: {', '.join(LANGUAGES.keys())}"
                )

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
            "Japanese": "Noto_Sans_JP",
            "Vietnamese": "Noto_Sans_VI",
            "Korean": "Noto_Sans_KR",
            "Chinese": "Noto_Sans_SC",
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
        languages=args.languages,
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
