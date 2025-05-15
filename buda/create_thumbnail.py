import os
import numpy as np
from tqdm import tqdm
import random
import jieba
from PIL import Image, ImageDraw, ImageFont
import cv2

# from upload_controller import read_channels_from_ref_json, load_ref_json

Image.MAX_IMAGE_PIXELS = None


def convert_thumbnail_black(input_path, output_path):
    # 打开PNG图像
    image = Image.open(input_path)

    # 将图像转换为RGBA模式
    image = image.convert("RGBA")

    # 将图像转换为NumPy数组
    data = np.array(image)

    # 创建一个布尔掩码，标识非背景部分的像素
    mask = data[:, :, 3] != 0

    # 将非背景部分的像素变成白色
    data[mask] = [255, 255, 255, 255]

    # 将修改后的NumPy数组转换回图像
    output_image = Image.fromarray(data)

    # 保存修改后的图像为PNG格式
    output_image.save(output_path, "PNG")


def controller_convert_black_to_white():
    srt_black_path = "/Users/donghaoliu/doc/video_material/thumbnail/black"

    dst_white_path = "/Users/donghaoliu/doc/video_material/thumbnail/white"

    all_files = os.listdir(srt_black_path)
    # remove .DS_Store using list comprehension
    all_files = [file for file in all_files if file != ".DS_Store"]

    for png in tqdm(all_files):
        print("Converting: ", png)
        convert_thumbnail_black(
            os.path.join(srt_black_path, png), os.path.join(dst_white_path, png)
        )


def create_thumbnail(
    srt_png_path,
    dst_thumbnail_path,
    cover_width,
    cover_height,
    margin,
    left_right_margin,
    bottom_margin,
):

    # 设置参数
    # cover_width = 1080
    # cover_height = 1464
    # margin = 50  # 图片a距离灰色背景的边距
    # left_right_margin = 26  # 图像b距离背景a左右边的距离
    # bottom_margin = 26  # 图像b距离背景a下边的距离

    # 创建纯黑色背景a
    background_a = np.zeros((cover_height, cover_width, 3), dtype=np.uint8)

    # 读取图片a
    image_a = Image.open(srt_png_path)

    # 创建指定颜色的灰色背景
    gray_background_height = image_a.size[1] + 2 * margin
    gray_background_width = image_a.size[0] + 2 * margin
    gray_background = Image.new(
        "RGB",
        (gray_background_width, gray_background_height),
        (25, 25, 25),  # 设置灰色背景的RGB值
    )

    # 将图片a放置在灰色背景正中
    x_offset = (gray_background_width - image_a.size[0]) // 2
    y_offset = (gray_background_height - image_a.size[1]) // 2
    gray_background.paste(image_a, (x_offset, y_offset), mask=image_a)

    # 将图像b放置在背景a正下方
    image_b_width = cover_width - 2 * left_right_margin
    # image_b_height = int(image_b_width * gray_background_height / gray_background_width)
    image_b_height = int(cover_height * 0.46)
    image_b = gray_background.resize(
        (image_b_width, image_b_height), Image.Resampling.LANCZOS
    )

    x_offset = left_right_margin
    y_offset = cover_height - image_b_height - bottom_margin
    background_a[
        y_offset : y_offset + image_b_height, x_offset : x_offset + image_b_width
    ] = np.array(image_b)

    # 保存最终图像
    cv2.imwrite(dst_thumbnail_path, background_a)


def paste_logo(jpg_path, png_path, position, size):
    # 打开JPG背景图像
    background = Image.open(jpg_path)

    # 打开PNG logo图像
    logo = Image.open(png_path)

    # 将PNG logo图像转换为RGBA模式
    logo = logo.convert("RGBA")

    # 调整logo图像的大小
    logo = logo.resize(size, Image.Resampling.LANCZOS)

    # 创建一个与背景图像大小相同的空白图像
    result = Image.new("RGB", background.size)

    # 将背景图像复制到结果图像上
    result.paste(background, (0, 0))

    # 将PNG logo图像贴入到结果图像的指定位置,只显示logo的前景部分
    result.paste(logo, position, mask=logo)

    return result


def write_text_on_image(image, text, position, font_path, font_size, font_color):
    """在图像上写入文字"""

    # 创建一个绘图对象
    draw = ImageDraw.Draw(image)

    # 加载字体
    font = ImageFont.truetype(font_path, font_size)

    # 在图像上绘制文字
    draw.text(position, text, font=font, fill=font_color)

    return image


def white_temp1_controller():
    """Convert all white png files to black png files"""

    # read all white png files
    white_png_path = "/Users/donghaoliu/doc/video_material/thumbnail_material/white"
    dst_white_path = (
        "/Users/donghaoliu/doc/video_material/thumbnail_material/white1_horizontal"
    )

    # create the destination folder if it does not exist
    if not os.path.exists(dst_white_path):
        os.makedirs(dst_white_path)

    # get all png files
    pngs = os.listdir(white_png_path)
    # remove .DS_Store using list comprehension
    pngs = [png for png in pngs if png != ".DS_Store"]

    # horizontal thumbnail for 微信视频号
    for png in tqdm(pngs):
        print("Converting: ", png)
        create_thumbnail(
            os.path.join(white_png_path, png),
            os.path.join(dst_white_path, png),
            1920,
            1080,
            50,
            610,
            50,
        )


def white_temp2_controller():
    """Paste logo and write 芒果文档 chinese text on the white thumbnail images"""

    # read all white png files from white1 folder
    src_white_path = (
        "/Users/donghaoliu/doc/video_material/thumbnail_material/white1_horizontal"
    )
    dst_white_path = (
        "/Users/donghaoliu/doc/video_material/thumbnail_material/white2_horizontal"
    )

    # create the destination folder if it does not exist
    if not os.path.exists(dst_white_path):
        os.makedirs(dst_white_path)

    all_pngs = os.listdir(src_white_path)
    # remove .DS_Store using list comprehension
    all_pngs = [png for png in all_pngs if png != ".DS_Store"]
    for png in tqdm(all_pngs):

        # 贴入logo 竖屏for 抖音和快手
        # img = paste_logo(
        #     os.path.join(src_white_path, png),
        #     "./test_thumbnail/mango.png",
        #     (700, 25),
        #     (60, 60),
        # )

        # 贴入logo 横屏 for 微信视频号
        img = paste_logo(
            os.path.join(src_white_path, png),
            "./test_thumbnail/mango.png",
            (940, 25),
            (60, 60),
        )

        text = "</> 芒果文档"
        # 竖屏for 抖音和快手
        # position_vertical = (780, 36)  # 指定文字的位置(x, y)

        # 横屏 for 微信视频号
        position_horizontal = (1000, 36)  # 指定文字的位置(x, y)
        font_path = "/Users/donghaoliu/doc/video_material/font/douyuFont-2.otf"  # 字体文件的路径
        font_size = 38  # 字体大小
        font_color = (255, 255, 255)  # 字体颜色(白色)

        # 竖屏for 抖音和快手
        # result_image = write_text_on_image(
        #     img, text, position_vertical, font_path, font_size, font_color
        # )

        # 横屏 for 微信视频号
        result_image = write_text_on_image(
            img, text, position_horizontal, font_path, font_size, font_color
        )

        # save the image
        result_image.save(os.path.join(dst_white_path, png))


def draw_ch_title_on_image_rect(
    image_path,
    text,
    position,
    font_path,
    font_size,
    right_padding,
    box_color=(0, 255, 128),
    box_thickness=15,
    padding=20,  # 新增的padding参数
    line_spacing=30,  # 新增的line_spacing参数
):
    """在图像上绘制文本并在文本周围绘制矩形框"""
    # 打开图像
    if isinstance(image_path, Image.Image):
        image = image_path
        text_color = (255, 255, 255)
    else:
        image = Image.open(image_path)
        text_color = (0, 255, 0)

    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_path, font_size)

    # 计算文本宽度的最大值
    max_width = image.width - position[0] - right_padding

    # 使用 jieba 进行中文分词
    words = list(jieba.cut(text, cut_all=False))

    # 自动换行
    lines = []
    while words:
        line = ""
        while words:
            word = words[0]
            test_line = line + word if line else word
            (width, baseline), (offset_x, offset_y) = font.font.getsize(test_line)
            if width <= max_width:
                line = test_line
                words.pop(0)
            else:
                break
        lines.append(line)

    # 计算文本块的总高度
    total_height = 0
    max_line_width = 0
    for line in lines:
        (width, baseline), (offset_x, offset_y) = font.font.getsize(line)
        total_height += baseline + offset_y + line_spacing
        max_line_width = max(max_line_width, width)

    # 绘制矩形框
    box_top_left = (
        position[0] - padding - box_thickness,
        position[1] - padding - box_thickness,
    )
    box_bottom_right = (
        position[0] + max_line_width + padding + box_thickness,
        position[1] + total_height + padding + box_thickness - line_spacing,
    )
    draw.rectangle(
        [box_top_left, box_bottom_right], outline=box_color, width=box_thickness
    )

    # 绘制文本
    y = position[1]
    for line in lines:
        draw.text((position[0], y), line, font=font, fill=text_color)
        (width, baseline), (offset_x, offset_y) = font.font.getsize(line)
        y += baseline + offset_y + line_spacing

    return image


def draw_ch_title_on_image(
    image_path, text, position, font_path, font_size, right_padding
):
    """在图像上绘制文本"""
    # 打开图像
    # 如果image_path是一个PIL图像对象，则直接使用它
    if isinstance(image_path, Image.Image):
        image = image_path
        color = (255, 255, 255)
    else:
        image = Image.open(image_path)
        color = (0, 255, 0)

    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_path, font_size)

    # 计算文本宽度的最大值
    max_width = image.width - position[0] - right_padding

    # 使用 jieba 进行中文分词
    if len(text) > 20:
        # return the first 20 characters
        text = text[:20] + "..."
    words = list(jieba.cut(text, cut_all=False))

    # 自动换行
    lines = []
    # print(words)
    # replace space with '' empty string
    words = [word.replace(" ", "") for word in words]
    # remove empty string
    words = [word for word in words if word]
    print(f"current words {words}")
    while words:
        line = ""
        # 根据您提供的方式获取文本尺寸
        while words:
            word = words[0]
            # 尝试添加下一个词
            test_line = line + word if line else word
            (width, baseline), (offset_x, offset_y) = font.font.getsize(test_line)
            if width <= max_width:
                line = test_line
                words.pop(0)
            else:
                # 如果添加下一个词使行宽超出最大宽度，则停止添加
                break
        lines.append(line)

    # 绘制文本
    y = position[1]
    for line in lines:
        draw.text((position[0], y), line, font=font, fill=color)
        # 获取行高以更新y坐标
        (width, baseline), (offset_x, offset_y) = font.font.getsize(line)
        y += baseline + offset_y

    return image


def random_bg(bg_path):
    """randomly select a background image"""
    # bg_path = "/media/dhl/TOSHIBA/video_material/thumbnail_material/white2"
    all_bg_images = os.listdir(bg_path)
    all_bg_images = [bg for bg in all_bg_images if bg != ".DS_Store"]

    return os.path.join(bg_path, random.choice(all_bg_images))


def random_bg_horizontal(bg_path):
    """randomly select a background image"""
    # bg_path = "/media/dhl/TOSHIBA/video_material/thumbnail_material/white2_horizontal"
    all_bg_images = os.listdir(bg_path)
    all_bg_images = [bg for bg in all_bg_images if bg != ".DS_Store"]

    return os.path.join(bg_path, random.choice(all_bg_images))


def read_zh_title(zh_title_path):
    """read chinese title corresponding file"""
    with open(zh_title_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def create_zh_title_thumbnail_vertical():
    """Create thumbnail for Chinese title"""
    # 参考中文srt文件的路径
    zh_title_src_path = "/Users/donghaoliu/doc/video_material/zh_title"
    dst_thumbnail_path = "/Users/donghaoliu/doc/video_material/thumbnail_vertical"

    topic = "code"
    # remove .DS_Store using list comprehension

    ref_dict = load_ref_json("code")

    # read all channels from ref_dict
    all_channels = read_channels_from_ref_json(topic)

    for channel in all_channels:
        all_titles = list(ref_dict[channel].keys())

        # 如果topic和channel文件夹不存在，创建他们
        if not os.path.exists(os.path.join(dst_thumbnail_path, topic, channel)):
            os.makedirs(os.path.join(dst_thumbnail_path, topic, channel))

        for title in all_titles:
            base_name = os.path.splitext(title)[0]
            dst_file_name = base_name + ".png"
            if os.path.exists(
                os.path.join(dst_thumbnail_path, topic, channel, dst_file_name)
            ):
                print(f"{dst_file_name} 文件存在, 跳过继续...")
                continue
            print("Creating thumbnail for: ", title)

            map_title = ref_dict[channel][title]
            map_base_name = os.path.splitext(map_title)[0]

            bg_image_path = random_bg()
            map_title = ref_dict[channel][title]
            map_base_name = os.path.splitext(map_title)[0]

            if "_clip_" in base_name:
                clip_id = base_name.split("_clip_")[-1]
                zh_title = (
                    read_zh_title(
                        os.path.join(
                            zh_title_src_path,
                            topic,
                            channel,
                            map_base_name + "_title.txt",
                        )
                    )
                    + f" - {clip_id}"
                )
            else:
                zh_title = read_zh_title(
                    os.path.join(
                        zh_title_src_path,
                        topic,
                        channel,
                        map_base_name + "_title.txt",
                    )
                )
            # Chinese title position on the thumbnail bg image
            position = (160, 180)  # 文本的起始位置

            # chinese font path
            font_path = "/Users/donghaoliu/doc/video_material/font/DottedSongtiCircleRegular.otf"  # 字体文件路径
            font_size = 100  # 字体大小
            right_padding = 100  # 文本到图像右边缘的距离

            # 贴中文标题到背景图像上
            merged_thumbnail_img = draw_ch_title_on_image(
                bg_image_path,
                zh_title,
                position,
                font_path,
                font_size,
                right_padding,
            )

            # save the image to the destination folder
            merged_thumbnail_img.save(
                os.path.join(dst_thumbnail_path, topic, channel, dst_file_name)
            )


def create_zh_title_thumbnail_vertical_single(
    dst_thumbnail_path, zh_title_path, vertical_font_path, bg_path
):
    """针对一个srt文件创建竖直封面"""
    if os.path.exists(dst_thumbnail_path):
        print(f"{dst_thumbnail_path} 封面存在, 跳过继续...")
        return
    print(f"创建封面 {dst_thumbnail_path}....")

    bg_image_path = random_bg(bg_path)

    # 读取中文标题
    zh_title = read_zh_title(zh_title_path)

    # Chinese title position on the thumbnail bg image
    position = (160, 180)  # 文本的起始位置

    # chinese font
    font_size = 100  # 字体大小
    right_padding = 100  # 文本到图像右边缘的距离

    # 贴中文标题到背景图像上
    merged_thumbnail_img = draw_ch_title_on_image(
        bg_image_path,
        zh_title,
        position,
        vertical_font_path,
        font_size,
        right_padding,
    )

    # save the image to the destination folder
    merged_thumbnail_img.save(dst_thumbnail_path)
    print(f"封面{dst_thumbnail_path}创建完成！")


def create_zh_title_thumbnail_horizontal():
    """Create thumbnail for Chinese title"""

    # 依赖路径，来自中文标题
    zh_title_src_path = "/Users/donghaoliu/doc/video_material/zh_title"

    dst_thumbnail_path = "/Users/donghaoliu/doc/video_material/thumbnail_horizontal"

    topic = "code"

    # remove .DS_Store using list comprehension

    ref_dict = load_ref_json(topic)

    all_channels = read_channels_from_ref_json(topic)

    for channel in all_channels:

        all_titles = ref_dict[channel].keys()

        # 如果topic和channel文件夹不存在，创建他们
        if not os.path.exists(os.path.join(dst_thumbnail_path, topic, channel)):
            os.makedirs(os.path.join(dst_thumbnail_path, topic, channel))

        for title in all_titles:
            base_name = os.path.splitext(title)[0]
            dst_file_name = base_name + ".png"
            if os.path.exists(
                os.path.join(dst_thumbnail_path, topic, channel, dst_file_name)
            ):
                print(f"{dst_file_name} 文件存在, 跳过继续...")
                continue
            print("Creating thumbnail for: ", title)

            bg_image_path = random_bg_horizontal()

            map_title = ref_dict[channel][title]
            map_base_name = os.path.splitext(map_title)[0]

            if "_clip_" in base_name:
                clip_id = base_name.split("_clip_")[-1]
                zh_title = (
                    read_zh_title(
                        os.path.join(
                            zh_title_src_path,
                            topic,
                            channel,
                            map_base_name + "_title.txt",
                        )
                    )
                    + f" - {clip_id}"
                )
            else:
                zh_title = read_zh_title(
                    os.path.join(
                        zh_title_src_path,
                        topic,
                        channel,
                        map_base_name + "_title.txt",
                    )
                )
            # Chinese title position on the thumbnail bg image
            position = (700, 100)  # 文本的起始位置

            # chinese font path
            font_path = "/Users/donghaoliu/doc/video_material/font/DottedSongtiCircleRegular.otf"  # 字体文件路径
            font_size = 100  # 字体大小
            right_padding = 600  # 主标题到图像右边缘的距离

            # 贴中文标题到背景图像上
            merged_thumbnail_img = draw_ch_title_on_image(
                bg_image_path,
                zh_title,
                position,
                font_path,
                font_size,
                right_padding,
            )

            # save the image to the destination folder
            merged_thumbnail_img.save(
                os.path.join(dst_thumbnail_path, topic, channel, dst_file_name)
            )


def create_zh_title_thumbnail_horizontal_single(
    dst_thumbnail_path, zh_title_path, font_path, bg_path
):
    """针对一个srt文件创建竖直封面"""
    if os.path.exists(dst_thumbnail_path):
        print(f"{dst_thumbnail_path} 封面存在, 跳过继续...")
        return
    print(f"创建封面 {dst_thumbnail_path}....")

    bg_image_path = random_bg_horizontal(bg_path)

    # 读取中文标题
    zh_title = read_zh_title(zh_title_path)

    # Chinese title position on the thumbnail bg image
    position = (700, 100)  # 文本的起始位置

    # chinese font path
    font_size = 100  # 字体大小
    right_padding = 600  # 主标题到图像右边缘的距离

    # 贴中文标题到背景图像上
    merged_thumbnail_img = draw_ch_title_on_image(
        bg_image_path,
        zh_title,
        position,
        font_path,
        font_size,
        right_padding,
    )

    # save the image to the destination folder
    merged_thumbnail_img.save(dst_thumbnail_path)
    print(f"封面{dst_thumbnail_path}创建完成！")


def read_bg(bg_path):
    # read bg image using pillow
    bg_img = Image.open(bg_path)
    return bg_img


def paste_youtube_to_bg(bg, thumbnail_path):
    """把youtube封面图粘贴到背景图上"""

    # 打开封面图片 (WebP格式)
    thumbnail = Image.open(thumbnail_path)

    # 获取背景图片的尺寸
    bg_width, bg_height = bg.size

    # 计算调整后的封面图片高度,保持宽高比
    thumbnail_width = 1080
    thumbnail_height = int(thumbnail.size[1] * (thumbnail_width / thumbnail.size[0]))

    # 调整封面图片大小
    thumbnail = thumbnail.resize(
        (thumbnail_width, thumbnail_height), Image.Resampling.LANCZOS
    )

    # 创建一个新的图像,大小为1080x1464,用于放置背景图和封面图
    new_img = Image.new("RGB", (1080, 1464), color="white")

    # 计算背景图片在新图像中的位置,使其居中
    bg_x = 0
    bg_y = 0

    # 将背景图片粘贴到新图像中
    new_img.paste(bg, (bg_x, bg_y))

    # 计算封面图片在新图像中的位置,使其底部对齐
    thumbnail_x = 0
    thumbnail_y = bg_height - thumbnail_height

    # 将封面图片粘贴到新图像中
    new_img.paste(thumbnail, (thumbnail_x, thumbnail_y))

    # # 保存最终的图片
    # new_img.save(dst_thumbnail_path)
    return new_img


def create_thumbnail_from_original_vertical_single(
    dst_thumbnail_path, zh_title_path, vertical_font_path, bg_path, ytb_thumbnail_path
):
    """创建从原始封面图和中文标题创建竖直封面图"""
    bg_img = read_bg(bg_path)
    merged_bg = paste_youtube_to_bg(bg_img, ytb_thumbnail_path)

    # 读取中文标题
    zh_title = read_zh_title(zh_title_path)

    # Chinese title position on the thumbnail bg image
    position = (160, 180)  # 文本的起始位置

    # chinese font
    font_size = 100  # 字体大小
    right_padding = 100  # 文本到图像右边缘的距离

    # 贴中文标题到背景图像上
    merged_thumbnail_img = draw_ch_title_on_image_rect(
        merged_bg,
        zh_title,
        position,
        vertical_font_path,
        font_size,
        right_padding,
    )

    # save the image to the destination folder
    merged_thumbnail_img.save(dst_thumbnail_path)
    print(f"封面{dst_thumbnail_path}创建完成！")


if __name__ == "__main__":
    # white_temp2_controller()
    print("创造vertical海报")
    create_zh_title_thumbnail_vertical()
    print("*" * 50)
    # print("创造horizontal海报")
    create_zh_title_thumbnail_horizontal()
