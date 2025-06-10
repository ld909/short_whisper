import re
import subprocess
import os
import shutil


def select_font_by_weight(font_weight, font_dir="../font/en/"):
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
            print(f"警告：未知的字体粗细 '{font_weight}'，使用默认 Regular")
    elif isinstance(font_weight, int):
        # 找到最接近的权重
        closest_weight = min(weight_to_file.keys(), key=lambda x: abs(x - font_weight))
        font_file, font_name = weight_to_file[closest_weight]
        if font_weight != closest_weight:
            print(f"字体权重 {font_weight} 映射到最接近的 {closest_weight}")
    else:
        # 默认使用regular
        font_file, font_name = font_mapping["regular"]
        print(f"警告：无效的字体粗细类型，使用默认 Regular")

    font_path = os.path.join(font_dir, font_file)

    # 检查文件是否存在
    if not os.path.exists(font_path):
        print(f"警告：字体文件不存在 {font_path}，使用默认可变字体")
        font_path = os.path.join(font_dir, "Oxanium-VariableFont_wght.ttf")
        font_name = "Oxanium"

    return font_path, font_name


def add_fade_and_font_to_ass_file(
    input_ass_path, output_ass_path, fade_in_ms, fade_out_ms, custom_font=None
):
    with open(
        input_ass_path, "r", encoding="utf-8-sig"
    ) as f_in:  # utf-8-sig handles BOM
        lines = f_in.readlines()

    with open(output_ass_path, "w", encoding="utf-8") as f_out:
        for line in lines:
            if line.startswith("Style:") and custom_font:
                # Style: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
                parts = line.strip().split(",")
                if len(parts) >= 3:
                    parts[1] = custom_font  # 替换字体名称
                    f_out.write(",".join(parts) + "\n")
                else:
                    f_out.write(line)
            elif line.startswith("Dialogue:"):
                # Dialogue: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
                parts = line.split(",", 9)
                if len(parts) == 10:
                    # 添加淡入淡出效果
                    fade_tag = f"{{\\fad({fade_in_ms},{fade_out_ms})}}"

                    # 如果需要在对话行中指定字体（备用方法）
                    font_tag = f"{{\\fn{custom_font}}}" if custom_font else ""

                    parts[9] = f"{fade_tag}{font_tag}{parts[9]}"
                    f_out.write(",".join(parts))
                else:
                    f_out.write(line)  # Should not happen with valid ASS
            else:
                f_out.write(line)
    print(f"Processed ASS file saved to: {output_ass_path}")


def install_font_to_system(font_path):
    """
    尝试将字体安装到系统中（macOS）
    """
    try:
        if os.path.exists(font_path):
            # macOS 字体安装路径
            font_dir = os.path.expanduser("~/Library/Fonts/")
            if not os.path.exists(font_dir):
                os.makedirs(font_dir)

            font_filename = os.path.basename(font_path)
            dest_path = os.path.join(font_dir, font_filename)

            if not os.path.exists(dest_path):
                shutil.copy2(font_path, dest_path)
                print(f"字体已安装到系统: {dest_path}")
                return True
            else:
                print(f"字体已存在于系统中: {dest_path}")
                return True
    except Exception as e:
        print(f"字体安装失败: {e}")
        return False


def create_custom_style_ass_with_attachment(
    input_ass_path,
    output_ass_path,
    fade_in_ms,
    fade_out_ms,
    font_weight,  # 修改：现在这里接受font_weight而不是font_name和font_path
    font_dir="../font/en/",  # 新增：字体目录
    font_size=30,
    font_color="&H00FFFFFF",
):
    """
    创建带有字体附件的ASS文件，自动根据font_weight选择对应字体
    font_weight: "light", "normal", "medium", "bold", "extra-bold" 或数字 (100-900)
    """
    # 自动选择字体
    font_path, font_name = select_font_by_weight(font_weight, font_dir)
    print(f"选择字体: {font_name} ({os.path.basename(font_path)})")

    with open(input_ass_path, "r", encoding="utf-8-sig") as f_in:
        lines = f_in.readlines()

    with open(output_ass_path, "w", encoding="utf-8") as f_out:
        # 由于我们直接使用对应粗细的字体文件，所以不需要额外的粗细设置
        bold_value = 0  # 字体文件本身已经是对应粗细
        weight_override = ""  # 不需要重写权重
        outline_override = ""  # 不需要额外轮廓

        # 添加字体附件信息到文件头
        script_info_written = False

        for line in lines:
            if line.startswith("[Script Info]"):
                f_out.write(line)
                f_out.write(f"!: This file uses custom font: {font_name}\n")
                f_out.write(f"!: Font file location: {font_path}\n")
                f_out.write(f"!: Font weight: {font_weight}\n")
                script_info_written = True
                continue

            elif line.startswith("[V4+ Styles]") or (
                script_info_written and line.strip() == ""
            ):
                # 在样式部分之前添加字体附件部分
                if not script_info_written:
                    f_out.write("[Script Info]\n")
                    f_out.write(f"!: This file uses custom font: {font_name}\n")
                    f_out.write(f"!: Font file location: {font_path}\n")
                    f_out.write(f"!: Font weight: {font_weight}\n")
                    f_out.write("\n")

                # 添加字体附件部分（某些播放器支持）
                f_out.write("[Fonts]\n")
                font_filename = os.path.basename(font_path)
                f_out.write(f"fontname: {font_filename}\n")
                f_out.write("\n")

                if line.startswith("[V4+ Styles]"):
                    styles_section_found = True
                    f_out.write(line)
                    f_out.write(
                        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                    )
                    # 创建字体样式 - 使用选择的字体，不需要额外的bold设置
                    custom_style = f"Style: CustomFont,{font_name},{font_size},{font_color},&H000000FF,&H00000000,&H80000000,{bold_value},0,0,0,100,100,0,0,1,2,0,2,10,10,10,1\n"
                    f_out.write(custom_style)
                    # 添加一个备用样式使用系统字体
                    fallback_style = f"Style: FallbackFont,Arial,{font_size},{font_color},&H000000FF,&H00000000,&H80000000,{bold_value},0,0,0,100,100,0,0,1,2,0,2,10,10,10,1\n"
                    f_out.write(fallback_style)
                    continue
                else:
                    f_out.write(line)
                    continue

            elif line.startswith("Style:"):
                # 跳过原有的默认样式
                continue
            elif line.startswith("Dialogue:"):
                # 处理对话行
                parts = line.split(",", 9)
                if len(parts) == 10:
                    # 使用自定义样式名称
                    parts[3] = "CustomFont"  # Style字段
                    # 添加字体指定和淡入淡出效果（不需要weight_override）
                    font_override = f"{{\\fn{font_name}}}{{\\fs{font_size}}}"
                    fade_effect = f"{{\\fad({fade_in_ms},{fade_out_ms})}}"
                    parts[9] = f"{font_override}{fade_effect}{parts[9]}"
                    f_out.write(",".join(parts))
                else:
                    f_out.write(line)
            else:
                f_out.write(line)

    print(f"创建了增强的ASS文件: {output_ass_path}")
    return font_path  # 返回选择的字体路径，用于后续处理


def create_custom_style_ass(
    input_ass_path,
    output_ass_path,
    fade_in_ms,
    fade_out_ms,
    font_weight,  # 修改：现在接受font_weight
    font_dir="../font/en/",  # 新增：字体目录
    font_size=20,
    font_color="&H00FFFFFF",
):
    """
    创建带有自定义样式的ASS文件，自动根据font_weight选择对应字体
    font_weight: "light", "normal", "medium", "bold", "extra-bold" 或数字 (100-900)
    """
    # 自动选择字体
    font_path, font_name = select_font_by_weight(font_weight, font_dir)
    print(f"选择字体: {font_name} ({os.path.basename(font_path)})")

    with open(input_ass_path, "r", encoding="utf-8-sig") as f_in:
        lines = f_in.readlines()

    with open(output_ass_path, "w", encoding="utf-8") as f_out:
        # 由于我们直接使用对应粗细的字体文件，所以不需要额外的粗细设置
        bold_value = 0  # 字体文件本身已经是对应粗细
        weight_override = ""  # 不需要重写权重
        outline_override = ""  # 不需要额外轮廓

        styles_section_found = False
        dialogue_started = False

        for line in lines:
            if line.startswith("[V4+ Styles]"):
                styles_section_found = True
                f_out.write(line)
                f_out.write(
                    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                )
                # 创建自定义样式
                custom_style = f"Style: CustomFont,{font_name},{font_size},{font_color},&H000000FF,&H00000000,&H80000000,{bold_value},0,0,0,100,100,0,0,1,2,0,2,10,10,10,1\n"
                f_out.write(custom_style)
                continue
            elif line.startswith("Style:") and styles_section_found:
                # 跳过原有的默认样式，使用我们的自定义样式
                continue
            elif line.startswith("Dialogue:"):
                if not dialogue_started:
                    dialogue_started = True
                # 处理对话行
                parts = line.split(",", 9)
                if len(parts) == 10:
                    # 使用自定义样式名称
                    parts[3] = "CustomFont"  # Style字段
                    # 添加淡入淡出效果（不需要weight_override）
                    fade_effect = f"{{\\fad({fade_in_ms},{fade_out_ms})}}"
                    parts[9] = f"{fade_effect}{parts[9]}"
                    f_out.write(",".join(parts))
                else:
                    f_out.write(line)
            else:
                f_out.write(line)

    print(f"Created custom styled ASS file: {output_ass_path}")
    return font_path  # 返回选择的字体路径


def main():
    """主程序入口"""
    # --- 使用方法 ---
    # 1. 先用 ffmpeg -i input.srt temp.ass 将srt转为ass
    # 2. 然后运行这个脚本
    input_srt = "./word_level.srt"
    temp_ass = "temp.ass"
    final_ass_with_fade = "./final_faded.ass"
    fade_in_duration = 200  # 毫秒
    fade_out_duration = 200  # 毫秒

    # 自定义字体设置 - 现在只需要指定weight，系统会自动选择对应字体
    font_weight = "semi-bold"  # 可选: "extra-light", "light", "normal", "medium", "semi-bold", "bold", "extra-bold" 或数字 100-900
    font_size = 36
    font_dir = "../font/en/"  # 字体目录

    # 步骤1: SRT to ASS (如果还没有做)
    try:
        subprocess.run(["ffmpeg", "-i", input_srt, temp_ass], check=True)
        print(f"Successfully converted {input_srt} to {temp_ass}")
    except subprocess.CalledProcessError as e:
        print(f"Error converting SRT to ASS: {e}")
        exit()
    except FileNotFoundError:
        print(
            "ffmpeg command not found. Please ensure FFmpeg is installed and in your PATH."
        )
        exit()

    # 步骤1.5: 选择字体并安装到系统
    selected_font_path, selected_font_name = select_font_by_weight(
        font_weight, font_dir
    )
    print(f"\n选择的字体: {selected_font_name}")
    print(f"字体文件: {selected_font_path}")
    print(f"\n正在尝试安装字体到系统...")
    font_installed = install_font_to_system(selected_font_path)

    # 步骤2: 添加淡入淡出和自定义字体到 ASS 文件
    try:
        final_font_path = create_custom_style_ass_with_attachment(
            temp_ass,
            final_ass_with_fade,
            fade_in_duration,
            fade_out_duration,
            font_weight,  # 直接传入weight，函数内部会选择对应字体
            font_dir,
            font_size,
        )

        print(f"\n使用自定义字体 '{selected_font_name}' 处理完成！")
        print(f"输出文件: {final_ass_with_fade}")
        print(f"\n字体处理状态:")
        print(f"- 选择的字体: {selected_font_name}")
        print(f"- 字体文件: {os.path.basename(final_font_path)}")
        print(f"- 字体粗细: {font_weight}")
        print(f"- 字体是否已安装到系统: {'是' if font_installed else '否'}")
        print(f"\n播放建议:")
        print(f"1. 如果字体已安装到系统，大部分播放器应该能正确显示")
        print(f"2. 如果仍有问题，请将字体文件复制到与字幕文件相同的目录")
        print(f"3. 推荐使用支持ASS格式的播放器，如VLC、PotPlayer等")
        print(f"4. 某些播放器可能需要重启才能识别新安装的字体")

    finally:
        # 清理临时文件
        if os.path.exists(temp_ass):
            try:
                os.remove(temp_ass)
                print(f"\n已删除临时文件: {temp_ass}")
            except OSError as e:
                print(f"\n警告：无法删除临时文件 {temp_ass}: {e}")


if __name__ == "__main__":
    main()

# 字体粗细设置示例:
# font_weight = "extra-light"  # 极细体 -> Oxanium-ExtraLight.ttf
# font_weight = "light"        # 细体 -> Oxanium-Light.ttf
# font_weight = "normal"       # 普通体 -> Oxanium-Regular.ttf
# font_weight = "medium"       # 中等体 -> Oxanium-Medium.ttf
# font_weight = "semi-bold"    # 半粗体 -> Oxanium-SemiBold.ttf
# font_weight = "bold"         # 粗体 -> Oxanium-Bold.ttf
# font_weight = "extra-bold"   # 极粗体 -> Oxanium-ExtraBold.ttf

# 或者使用数字:
# font_weight = 100  # -> Oxanium-ExtraLight.ttf
# font_weight = 300  # -> Oxanium-Light.ttf
# font_weight = 400  # -> Oxanium-Regular.ttf
# font_weight = 500  # -> Oxanium-Medium.ttf
# font_weight = 600  # -> Oxanium-SemiBold.ttf
# font_weight = 700  # -> Oxanium-Bold.ttf
# font_weight = 800  # -> Oxanium-ExtraBold.ttf
# font_weight = 900  # -> Oxanium-ExtraBold.ttf
