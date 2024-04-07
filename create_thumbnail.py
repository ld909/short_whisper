import os
from PIL import Image
import numpy as np
from tqdm import tqdm
import cv2


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


from PIL import Image
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2

Image.MAX_IMAGE_PIXELS = None


def create_thumbnail(srt_png_path, dst_thumbnail_path):

    # 设置参数
    cover_width = 1080
    cover_height = 1920
    margin = 50  # 图片a距离灰色背景的边距
    left_right_margin = 26  # 图像b距离背景a左右边的距离
    bottom_margin = 80  # 图像b距离背景a下边的距离

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
    image_b_height = int(image_b_width * gray_background_height / gray_background_width)
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


from PIL import Image, ImageDraw, ImageFont


def write_text_on_image(image, text, position, font_path, font_size, font_color):
    # 打开图像
    # image = Image.open(image_path)

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
    white_png_path = "/Users/donghaoliu/doc/video_material/thumbnail/white"
    dst_white_path = "/Users/donghaoliu/doc/video_material/thumbnail/white1"
    pngs = os.listdir(white_png_path)
    # remove .DS_Store using list comprehension
    pngs = [png for png in pngs if png != ".DS_Store"]
    for png in tqdm(pngs):
        print("Converting: ", png)
        create_thumbnail(
            os.path.join(white_png_path, png), os.path.join(dst_white_path, png)
        )


def white_temp2_controller():

    # read all white png files from white1 folder
    src_white_path = "/Users/donghaoliu/doc/video_material/thumbnail/white1"
    dst_white_path = "/Users/donghaoliu/doc/video_material/thumbnail/white2"
    all_pngs = os.listdir(src_white_path)
    # remove .DS_Store using list comprehension
    all_pngs = [png for png in all_pngs if png != ".DS_Store"]
    for png in tqdm(all_pngs):

        # 贴入logo
        img = paste_logo(
            os.path.join(src_white_path, png),
            "./test_thumbnail/mango.png",
            (700, 25),
            (70, 70),
        )
        # save the image
        # img.save("./test_thumbnail/1_out_check_with_logo.png")

        # 写入芒果文档的文字
        # image_path = "./test_thumbnail/1_out_check_with_logo.png"
        text = "</> 芒果文档"
        position = (780, 36)  # 指定文字的位置(x, y)
        font_path = "./test_thumbnail/AlibabaHealthFont20CN-85B.TTF"  # 字体文件的路径
        font_size = 40  # 字体大小
        font_color = (255, 255, 255)  # 字体颜色(白色)

        result_image = write_text_on_image(
            img, text, position, font_path, font_size, font_color
        )
        # save the image
        result_image.save(os.path.join(dst_white_path, png))


if __name__ == "__main__":
    white_temp2_controller()
