# from PIL import Image

# # 指定颜色 (例如，RGB(0, 201, 187))
# color = (0, 201, 187)  # RGB格式

# # 指定图像的尺寸
# width = 1080
# height = 1464

# # 创建一个纯色背景图
# background = Image.new("RGB", (width, height), color)

# # 保存纯色背景图
# background.save("/media/dhl/TOSHIBA/video_material/thumbnail_material/bg/code/bg1.png")


from PIL import Image

# # 打开背景图片
# bg = Image.open("/media/dhl/TOSHIBA/video_material/thumbnail_material/bg/code/bg1.png")

# # 打开封面图片 (WebP格式)
# thumbnail = Image.open(
#     "/media/dhl/TOSHIBA/ytb-videos_toshiba/code/fireship/5 Cool New Features in AngularFire.webp"
# )

# # 获取背景图片的尺寸
# bg_width, bg_height = bg.size

# # 计算调整后的封面图片高度,保持宽高比
# thumbnail_width = 1080
# thumbnail_height = int(thumbnail.size[1] * (thumbnail_width / thumbnail.size[0]))

# # 调整封面图片大小
# thumbnail = thumbnail.resize(
#     (thumbnail_width, thumbnail_height), Image.Resampling.LANCZOS
# )

# # 创建一个新的图像,大小为1080x1464,用于放置背景图和封面图
# new_img = Image.new("RGB", (1080, 1464), color="white")

# # 计算背景图片在新图像中的位置,使其居中
# bg_x = 0
# bg_y = 0

# # 将背景图片粘贴到新图像中
# new_img.paste(bg, (bg_x, bg_y))

# # 计算封面图片在新图像中的位置,使其底部对齐
# thumbnail_x = 0
# thumbnail_y = 1464 - thumbnail_height

# # 将封面图片粘贴到新图像中
# new_img.paste(thumbnail, (thumbnail_x, thumbnail_y))

# # 保存最终的图片
# new_img.save("./test_thumbnail/t.png")
# from create_thumbnail import draw_ch_title_on_image


from PIL import Image, ImageDraw, ImageFont
import jieba


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


# # 示例调用
# image = draw_ch_title_on_image(
#     "bg.png",
#     "这是一个测试标题",
#     (50, 50),
#     "path/to/font.ttf",
#     40,
#     20,
#     box_color=(255, 0, 0),
#     box_thickness=5,
# )
# image.show()


def read_bg(bg_path):
    # read bg image using pillow
    bg_img = Image.open(bg_path)
    return bg_img


"""创建从原始封面图和中文标题创建竖直封面图"""
bg_img = read_bg("./test_thumbnail/t.png")
hard_dive_path = "/media/dhl/TOSHIBA"
vertical_thumbnail_font_path = (
    f"{hard_dive_path}/video_material/font/GenJyuuGothic-Bold-2.ttf"
)
# 读取中文标题
zh_title = "Javascript看你运气如何运用生死在掌握之中"

# Chinese title position on the thumbnail bg image
position = (160, 180)  # 文本的起始位置

# chinese font
font_size = 100  # 字体大小
right_padding = 100  # 文本到图像右边缘的距离

# 贴中文标题到背景图像上
merged_thumbnail_img = draw_ch_title_on_image_rect(
    bg_img,
    zh_title,
    position,
    vertical_thumbnail_font_path,
    font_size,
    right_padding,
)

# save the image to the destination folder
merged_thumbnail_img.save("./test_thumbnail/zh_thumbnail.png")
# print(f"封面{dst_thumbnail_path}创建完成！")
