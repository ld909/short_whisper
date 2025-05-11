#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多语言字幕渲染测试脚本

用于测试不同语言字幕渲染参数效果的测试用例
支持英文、日语、韩语、越南语四种语言
"""

import os
import subprocess
import argparse
import logging
import shutil

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 定义路径
TEST_DIR = "/Users/donghaoliu/doc/short_whisper/test"
FONTS_DIR = "/Users/donghaoliu/doc/short_whisper/fonts"

# 定义语言设置
LANGUAGE_SETTINGS = {
    "en": {
        "name": "英文",
        "font_dir": "Noto_Sans_EN",
        "font_file": "NotoSans-VariableFont_wdth,wght.ttf",
        "font_name": "notosans",
    },
    "ja": {
        "name": "日语",
        "font_dir": "Noto_Sans_JP",
        "font_file": "NotoSansJP-VariableFont_wght.ttf",
        "font_name": "notosansjp",
    },
    "ko": {
        "name": "韩语",
        "font_dir": "Noto_Sans_KR",
        "font_file": "NotoSansKR-VariableFont_wght.ttf",
        "font_name": "notosanskr",
    },
    "vi": {
        "name": "越南语",
        "font_dir": "Noto_Sans_VI",
        "font_file": "NotoSans-VariableFont_wdth,wght.ttf",
        "font_name": "notosans",
    },
}


def translate_subtitle(source_srt, target_lang):
    """
    将英文字幕翻译成目标语言
    直接在代码中硬编码翻译，而不是调用API
    """
    target_srt = source_srt.replace("_en.srt", f"_{target_lang}.srt")

    if os.path.exists(target_srt):
        logger.info(f"目标语言字幕已存在: {target_srt}")
        return target_srt

    logger.info(
        f"正在将英文字幕翻译为{LANGUAGE_SETTINGS[target_lang]['name']}: {target_srt}"
    )

    # 读取英文字幕
    with open(source_srt, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 翻译字幕内容
    translated_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 字幕序号和时间码保持不变
        if line.isdigit() or "-->" in line:
            translated_lines.append(line + "\n")
        # 空行保持不变
        elif not line:
            translated_lines.append("\n")
        # 翻译文本内容
        else:
            # 根据目标语言进行硬编码翻译
            if target_lang == "ja":
                # 日语翻译
                if "In the vast ocean of Dharma" in line:
                    translated_lines.append(
                        "広大な法の海において、唯識学派は輝く宝石のように光り、衆生が心の神秘を理解するための道を照らしています。\n"
                    )
                elif "When we confront the intricate" in line:
                    translated_lines.append(
                        "私たちが世界の複雑な現実に直面するとき、しばしば外見に惑わされ、真実と虚偽を見分けることができなくなります。\n"
                    )
                else:
                    # 未匹配的句子保持原样
                    translated_lines.append(line + "\n")

            elif target_lang == "ko":
                # 韩语翻译
                if "In the vast ocean of Dharma" in line:
                    translated_lines.append(
                        "광대한 법의 바다에서 유식학파는 빛나는 보석처럼 빛나며, 중생이 마음의 신비를 이해하기 위한 길을 밝혀줍니다.\n"
                    )
                elif "When we confront the intricate" in line:
                    translated_lines.append(
                        "우리가 세계의 복잡하고 난해한 현실에 직면할 때, 종종 겉모습에 미혹되어 진실과 거짓을 구별할 수 없게 됩니다.\n"
                    )
                else:
                    # 未匹配的句子保持原样
                    translated_lines.append(line + "\n")

            elif target_lang == "vi":
                # 越南语翻译
                if "In the vast ocean of Dharma" in line:
                    translated_lines.append(
                        "Trong đại dương rộng lớn của Phật pháp, trường phái Duy thức tỏa sáng như một viên ngọc quý, soi sáng con đường để chúng sinh hiểu được những bí ẩn của tâm.\n"
                    )
                elif "When we confront the intricate" in line:
                    translated_lines.append(
                        "Khi đối mặt với thực tại phức tạp và rắc rối của thế giới, chúng ta thường bị lạc trong vẻ bề ngoài, không thể phân biệt được đâu là sự thật, đâu là giả dối.\n"
                    )
                else:
                    # 未匹配的句子保持原样
                    translated_lines.append(line + "\n")
            else:
                # 其他语言或未知语言保持原样
                translated_lines.append(line + "\n")
        i += 1

    # 写入翻译后的字幕
    with open(target_srt, "w", encoding="utf-8") as f:
        f.writelines(translated_lines)

    logger.info(f"已创建{LANGUAGE_SETTINGS[target_lang]['name']}字幕文件: {target_srt}")

    return target_srt


def add_subtitle_to_video(
    video_path,
    srt_path,
    output_path,
    lang_code,
    font_size=16,
    margin_v=20,
    font_weight=700,
    outline_color="0,0,0",  # 修改为RGB格式，默认为黑色
    outline_width=1,
):
    """为视频添加特定语言的字幕"""
    try:
        # 获取语言设置
        lang_settings = LANGUAGE_SETTINGS[lang_code]

        # 获取字体路径
        font_path = os.path.join(
            FONTS_DIR, lang_settings["font_dir"], lang_settings["font_file"]
        )
        fonts_dir = os.path.dirname(font_path)
        font_name = lang_settings["font_name"]

        # 将RGB格式转换为ASS格式（&HBBGGRR）
        r, g, b = map(int, outline_color.split(","))
        ass_outline_color = f"&H{b:02X}{g:02X}{r:02X}"

        # 创建输出目录
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 构建ffmpeg命令
        cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-vf",
            f"subtitles={srt_path}:fontsdir={fonts_dir}:force_style='Fontname={font_name},FontSize={font_size},PrimaryColour=&HFFFFFF,OutlineColour={ass_outline_color},BorderStyle=1,Outline={outline_width},Bold={font_weight},MarginV={margin_v}'",
            "-c:a",
            "copy",
            "-y",  # 覆盖已存在的文件
            output_path,
        ]

        # 执行ffmpeg命令
        logger.info(
            f"正在处理{lang_settings['name']}字幕视频: {os.path.basename(video_path)}"
        )
        logger.info(f"使用字幕: {os.path.basename(srt_path)}")
        logger.info(f"使用字体: {font_name} ({font_path})")
        logger.info(f"字体大小: {font_size}, 底部边距: {margin_v}")
        logger.info(
            f"字体粗细: {font_weight}, 描边颜色: RGB({outline_color}) -> ASS({ass_outline_color}), 描边粗细: {outline_width}"
        )

        process = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        if process.returncode == 0:
            logger.info(f"成功生成带{lang_settings['name']}字幕的视频: {output_path}")
            return True
        else:
            logger.error(f"添加{lang_settings['name']}字幕失败: {process.stderr}")
            return False

    except Exception as e:
        logger.error(f"添加{lang_code}字幕时出错: {str(e)}")
        return False


def process_all_languages(
    video_path,
    en_srt_path,
    font_size=16,
    margin_v=20,
    font_weight=700,
    outline_color="0,0,0",  # 修改为RGB格式，默认为黑色
    outline_width=1,
):
    """处理所有语言的字幕视频"""
    results = {}

    # 处理所有语言
    for lang_code in LANGUAGE_SETTINGS.keys():
        # 英文直接使用原始字幕
        if lang_code == "en":
            srt_path = en_srt_path
        else:
            # 其他语言需要翻译
            srt_path = translate_subtitle(en_srt_path, lang_code)

        # 构建输出路径
        output_filename = os.path.basename(video_path).replace(
            ".mp4", f"_{lang_code}.mp4"
        )
        output_path = os.path.join(TEST_DIR, output_filename)

        # 添加字幕
        success = add_subtitle_to_video(
            video_path,
            srt_path,
            output_path,
            lang_code,
            font_size=font_size,
            margin_v=margin_v,
            font_weight=font_weight,
            outline_color=outline_color,
            outline_width=outline_width,
        )

        results[lang_code] = {
            "success": success,
            "output_path": output_path,
            "language": LANGUAGE_SETTINGS[lang_code]["name"],
        }

    return results


def main():
    parser = argparse.ArgumentParser(description="多语言字幕参数测试工具")

    # 添加命令行参数
    parser.add_argument("--video", type=str, default="1.mp4", help="测试视频文件名")
    parser.add_argument("--srt", type=str, default="1_en.srt", help="英文字幕文件名")
    parser.add_argument("--font-size", type=int, default=16, help="字体大小")
    parser.add_argument("--margin-v", type=int, default=20, help="底部边距")
    parser.add_argument(
        "--font-weight", type=int, default=700, help="字体粗细(100-900)"
    )
    parser.add_argument(
        "--outline-color",
        type=str,
        default="0,0,0",
        help="描边颜色(RGB格式,如0,0,0表示黑色)",
    )
    parser.add_argument("--outline-width", type=float, default=1, help="描边粗细")
    parser.add_argument(
        "--language",
        type=str,
        choices=list(LANGUAGE_SETTINGS.keys()) + ["all"],
        default="all",
        help="要处理的语言代码(en=英文, ja=日语, ko=韩语, vi=越南语, all=全部)",
    )

    args = parser.parse_args()

    # 构建完整路径
    video_path = os.path.join(TEST_DIR, args.video)
    en_srt_path = os.path.join(TEST_DIR, args.srt)

    # 检查文件是否存在
    if not os.path.exists(video_path):
        logger.error(f"测试视频不存在: {video_path}")
        return

    if not os.path.exists(en_srt_path):
        logger.error(f"英文字幕不存在: {en_srt_path}")
        return

    # 处理指定语言或所有语言
    if args.language == "all":
        results = process_all_languages(
            video_path,
            en_srt_path,
            font_size=args.font_size,
            margin_v=args.margin_v,
            font_weight=args.font_weight,
            outline_color=args.outline_color,
            outline_width=args.outline_width,
        )

        # 输出处理结果摘要
        logger.info("\n处理结果摘要:")
        for lang, result in results.items():
            status = "成功" if result["success"] else "失败"
            logger.info(
                f"{result['language']}: {status} - {os.path.basename(result['output_path'])}"
            )
    else:
        # 处理单一语言
        lang_code = args.language

        # 获取字幕路径
        if lang_code == "en":
            srt_path = en_srt_path
        else:
            srt_path = translate_subtitle(en_srt_path, lang_code)

        # 构建输出路径
        output_filename = os.path.basename(video_path).replace(
            ".mp4", f"_{lang_code}.mp4"
        )
        output_path = os.path.join(TEST_DIR, output_filename)

        # 添加字幕
        add_subtitle_to_video(
            video_path,
            srt_path,
            output_path,
            lang_code,
            font_size=args.font_size,
            margin_v=args.margin_v,
            font_weight=args.font_weight,
            outline_color=args.outline_color,
            outline_width=args.outline_width,
        )


if __name__ == "__main__":
    main()
