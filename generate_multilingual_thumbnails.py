"""
多语言视频封面生成工具

功能说明:
此脚本用于为视频批量生成多语言封面。从指定路径随机选择背景图片，
并将多语言关键词/短语添加到封面上。支持根据不同语言自动选择合适的字体。

输入:
- 背景图片: [媒体路径]/buda_images_crop/
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
7. 设置背景颜色: python generate_multilingual_thumbnails.py --bg_color "88,235,52,180"
8. 设置底部边距: python generate_multilingual_thumbnails.py --bottom_margin 100
9. 设置背景圆角: python generate_multilingual_thumbnails.py --corner_radius 20
"""

import os
import json
import random
import argparse
import platform
import glob
from PIL import Image, ImageDraw, ImageFont, ImageColor

# 支持的语言及其代码
LANGUAGES = {
    "English": "en",
    "Japanese": "ja",
    "Vietnamese": "vi",
    "Korean": "ko",
    "Chinese": "zh",
}


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


def get_font_path(language):
    """根据语言获取合适的字体路径"""
    base_font_dir = "/Users/donghaoliu/doc/short_whisper/fonts"

    # 为不同语言指定默认字体
    language_font_dirs = {
        "English": "Noto_Sans_EN",
        "Japanese": "Noto_Sans_JP",
        "Vietnamese": "Noto_Sans_VI",
        "Korean": "Noto_Sans_KR",
        "Chinese": "Noto_Sans_SC",  # 或者使用 Noto_Sans_TC 取决于简体/繁体需求
    }

    if language in language_font_dirs:
        font_dir = os.path.join(base_font_dir, language_font_dirs[language])
        if os.path.exists(font_dir):
            font_files = glob.glob(os.path.join(font_dir, "*.ttf"))
            if font_files:
                return random.choice(font_files)

    # 如果没有找到特定语言的字体，使用默认字体
    default_font = os.path.join(
        base_font_dir, "Noto_Sans_EN/NotoSans-VariableFont_wdth,wght.ttf"
    )
    if os.path.exists(default_font):
        return default_font
    else:
        # 尝试找到任何可用的字体
        all_fonts = glob.glob(os.path.join(base_font_dir, "**/*.ttf"), recursive=True)
        if all_fonts:
            return all_fonts[0]
        else:
            raise FileNotFoundError(f"找不到任何可用的字体文件在 {base_font_dir}")


def get_random_background_image(media_path):
    """从指定路径随机选择一张背景图片"""
    background_dir = os.path.join(media_path, "buda_images_crop")
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

    # 处理中文（如果有）
    chinese_file = os.path.join(
        media_path, "key_words", channel, "zh", f"{video_name}.json"
    )
    if os.path.exists(chinese_file):
        try:
            with open(chinese_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "key_phrases" in data:
                    result["Chinese"] = data["key_phrases"]
                elif "title" in data:
                    result["Chinese"] = data["title"]
        except Exception as e:
            print(f"加载中文关键词文件时出错: {e}")

    return result


def create_thumbnail(
    bg_image_path,
    title,
    output_path,
    language,
    font_size=45,
    font_color="white",
    bg_color="88,235,52,180",
    bottom_margin=50,
    corner_radius=0,
):
    """创建单个缩略图"""
    try:
        # 加载背景图片
        img = Image.open(bg_image_path)

        # 调整大小为1080p (1920x1080)，但保持宽高比
        # 计算原始宽高比
        width, height = img.size
        original_ratio = width / height
        target_ratio = 1920 / 1080

        # 根据宽高比决定裁剪或填充方式
        if original_ratio > target_ratio:
            # 图片比目标更宽，基于高度等比例调整，然后裁剪宽度
            new_height = 1080
            new_width = int(new_height * original_ratio)
            try:
                # 新版PIL使用Image.Resampling.LANCZOS
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            except AttributeError:
                # 旧版PIL使用Image.LANCZOS
                img = img.resize((new_width, new_height), Image.LANCZOS)

            # 从中心裁剪到目标宽度
            left = (new_width - 1920) // 2
            right = left + 1920
            img = img.crop((left, 0, right, new_height))
        else:
            # 图片比目标更高，基于宽度等比例调整，然后裁剪高度
            new_width = 1920
            new_height = int(new_width / original_ratio)
            try:
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            except AttributeError:
                img = img.resize((new_width, new_height), Image.LANCZOS)

            # 从中心裁剪到目标高度
            top = (new_height - 1080) // 2
            bottom = top + 1080
            img = img.crop((0, top, new_width, bottom))

        # 创建绘图对象
        draw = ImageDraw.Draw(img, "RGBA")

        # 获取合适的字体
        font_path = get_font_path(language)
        print(f"  - 使用字体: {font_path}")
        font = ImageFont.truetype(font_path, font_size)

        # 处理背景颜色 (r,g,b,a)
        bg_color_rgba = tuple(map(int, bg_color.split(",")))

        # 计算文本大小和位置
        max_width = img.width * 0.9
        text_lines = []

        # 根据语言使用不同的文本分割策略
        asian_languages = ["Japanese", "Chinese", "Korean"]

        if language in asian_languages:
            # 对于亚洲语言，逐字符检查并在需要时换行
            current_line = ""
            for char in title:
                test_line = current_line + char
                bbox = draw.textbbox((0, 0), test_line, font=font)
                line_width = bbox[2] - bbox[0]

                if line_width <= max_width:
                    current_line = test_line
                else:
                    text_lines.append(current_line)
                    current_line = char

            if current_line:
                text_lines.append(current_line)
        else:
            # 对于西方语言，按单词分割
            current_line = ""
            words = title.split()
            for word in words:
                # 检查单个单词是否超过最大宽度
                word_bbox = draw.textbbox((0, 0), word, font=font)
                word_width = word_bbox[2] - word_bbox[0]

                # 如果单个单词超过最大宽度，需要逐字符处理
                if word_width > max_width:
                    # 如果当前行不为空，先添加到行列表中
                    if current_line:
                        text_lines.append(current_line)
                        current_line = ""

                    # 逐字符处理长单词
                    char_line = ""
                    for char in word:
                        test_char_line = char_line + char
                        char_bbox = draw.textbbox((0, 0), test_char_line, font=font)
                        char_line_width = char_bbox[2] - char_bbox[0]

                        if char_line_width <= max_width:
                            char_line = test_char_line
                        else:
                            text_lines.append(char_line)
                            char_line = char

                    if char_line:
                        current_line = char_line
                else:
                    # 正常处理单词
                    test_line = current_line + " " + word if current_line else word
                    bbox = draw.textbbox((0, 0), test_line, font=font)
                    line_width = bbox[2] - bbox[0]

                    if line_width <= max_width:
                        current_line = test_line
                    else:
                        text_lines.append(current_line)
                        current_line = word

            if current_line:
                text_lines.append(current_line)

        # 计算文本总高度
        line_height = font_size * 1.5
        text_height = len(text_lines) * line_height

        # 绘制文本背景和文本
        if bottom_margin:
            # 如果设置了底部边距，则根据底部边距计算 y 坐标
            y_position = int(img.height - text_height - bottom_margin)
        else:
            # 否则居中显示
            y_position = (img.height - int(text_height)) // 2

        for line in text_lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            x_position = (img.width - line_width) // 2

            # 绘制背景矩形
            rect_padding = 20
            # 获取文本的实际高度和ascent/descent信息
            text_bbox = draw.textbbox((0, 0), line, font=font)
            text_height = text_bbox[3] - text_bbox[1]

            # 获取文本基线信息，以便更准确地定位文本
            # 使用textbbox得到的值计算文本的基线位置与y_position的偏移
            baseline_offset = -text_bbox[1]  # 文本顶部到基线的距离

            # 计算背景矩形坐标，确保上下边距相等
            rect_top = int(y_position - rect_padding - baseline_offset)
            rect_bottom = int(
                y_position + (text_height - baseline_offset) + rect_padding
            )

            rect_coords = [
                int(x_position - rect_padding),
                rect_top,
                int(x_position + line_width + rect_padding),
                rect_bottom,
            ]

            # 使用圆角矩形而不是普通矩形
            if corner_radius > 0:
                # 绘制圆角矩形
                x1, y1, x2, y2 = rect_coords
                # 确保圆角半径不超过矩形的一半宽度和高度
                cr = min(corner_radius, (x2 - x1) // 2, (y2 - y1) // 2)

                # 创建一个透明的遮罩图层
                mask = Image.new("L", (x2 - x1, y2 - y1), 0)
                mask_draw = ImageDraw.Draw(mask)

                # 绘制圆角矩形到遮罩
                mask_draw.rounded_rectangle([(0, 0), (x2 - x1, y2 - y1)], cr, fill=255)

                # 创建背景色图层
                color_layer = Image.new("RGBA", (x2 - x1, y2 - y1), bg_color_rgba)

                # 将背景色图层与遮罩组合，然后粘贴到主图像
                img.paste(color_layer, (x1, y1), mask)
            else:
                # 普通矩形（无圆角）
                draw.rectangle(rect_coords, fill=bg_color_rgba)

            # 绘制文本，保持在原来的y_position
            draw.text((x_position, y_position), line, font=font, fill=font_color)
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
    font_color="white",
    bg_color="88,235,52,180",
    bottom_margin=200,
    corner_radius=0,
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
            if os.path.isdir(os.path.join(key_words_dir, d))
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
            video_files = [f for f in os.listdir(first_lang_dir) if f.endswith(".json")]

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
                    bg_color=bg_color,
                    bottom_margin=bottom_margin,
                    corner_radius=corner_radius,
                )


def main():
    parser = argparse.ArgumentParser(description="生成多语言视频封面")
    parser.add_argument("-c", "--channel", help="指定要处理的频道")
    parser.add_argument("-v", "--video", help="指定要处理的视频名称（不含扩展名）")
    parser.add_argument("-l", "--languages", nargs="+", help="指定要生成的语言列表")
    parser.add_argument("--font_size", type=int, default=95, help="字体大小")
    parser.add_argument("--font_color", default="gray", help="字体颜色")
    parser.add_argument(
        "--bg_color", default="240,240,53,180", help="背景颜色 (r,g,b,a)"
    )
    parser.add_argument(
        "--bottom_margin", type=int, default=200, help="文字距离底部的距离（像素）"
    )
    parser.add_argument(
        "--corner_radius", type=int, default=100, help="背景矩形的圆角半径（像素）"
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
        base_font_dir = "/Users/donghaoliu/doc/short_whisper/fonts"
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
            else:
                print(f"  {lang}: 目录不存在 {full_dir}")

    generate_thumbnails(
        channel=args.channel,
        video_name=args.video,
        languages=args.languages,
        font_size=args.font_size,
        font_color=args.font_color,
        bg_color=args.bg_color,
        bottom_margin=args.bottom_margin,
        corner_radius=args.corner_radius,
    )


if __name__ == "__main__":
    main()
