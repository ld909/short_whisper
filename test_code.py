# from srt_format import time_str_to_obj, timedelta_to_srt

# string = "00:00:06,260"

# timedelta_obj = time_str_to_obj(string)
# string_back = timedelta_to_srt(timedelta_obj)
# print(string, timedelta_obj, string_back)
# from translate_srt import wrap_srt_text_chinese
# import jieba


# def float_to_srt_timestamp(seconds):
#     # 将秒转换为毫秒
#     milliseconds = int(seconds * 1000)

#     # 将毫秒转换为小时、分钟、秒和毫秒
#     hours = milliseconds // 3600000
#     milliseconds = milliseconds % 3600000
#     minutes = milliseconds // 60000
#     milliseconds = milliseconds % 60000
#     seconds = milliseconds // 1000
#     milliseconds = milliseconds % 1000

#     # 格式化字符串,确保小时、分钟、秒和毫秒都是两位数
#     timestamp = "{:02d}:{:02d}:{:02d},{:03d}".format(
#         hours, minutes, seconds, milliseconds
#     )

#     return timestamp


# # 测试一下
# print(float_to_srt_timestamp(50.22))  # 应该输出 00:00:50,220


# import json

# # JSON 字符串
# json_string = """["编程语言","数据结构","C语言"]"""

# # 使用 json.loads() 函数解析 JSON 字符串
# python_list = json.loads(json_string)

# # 打印结果
# print(python_list)
# print(type(python_list))


from PIL import Image, ImageDraw, ImageFont
import textwrap
import jieba


def draw_ch_title_on_image(
    image_path, text, position, font_path, font_size, right_padding
):
    """在图像上绘制文本"""
    # 打开图像
    image = Image.open(image_path)
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
        draw.text((position[0], y), line, font=font, fill=(0, 255, 0))
        # 获取行高以更新y坐标
        (width, baseline), (offset_x, offset_y) = font.font.getsize(line)
        y += baseline + offset_y

    # 显示图像
    image.show()

    # 保存图像
    image.save("./test_thumbnail/final.png")


# 使用示例
# image_path = "./test_thumbnail/1_out_check_with_logo_text.png"  # 背景图像路径
# text = "研究python的列表和dict"  # 要写入的文本
# position = (160, 180)  # 文本的起始位置
# font_path = "./test_thumbnail/AlibabaHealthFont20CN-85B.TTF"  # 字体文件路径
# font_size = 120  # 字体大小
# right_padding = 100  # 文本到图像右边缘的距离

# draw_ch_title_on_image(image_path, text, position, font_path, font_size, right_padding)


# from PIL import Image, ImageDraw, ImageFont


# def write_text_on_image(
#     image_path, text, font_path, font_size, position, margin_right, line_spacing=10
# ):
#     # 打开背景图片
#     image = Image.open(image_path)

#     # 创建一个绘图对象
#     draw = ImageDraw.Draw(image)

#     # 加载字体
#     font = ImageFont.truetype(font_path, font_size)

#     # 计算每行文本的最大宽度
#     max_width = image.width - position[0] - margin_right

#     # 拆分文本为多行
#     lines = []
#     current_line = ""
#     for word in text.split():
#         if font.getbbox(current_line + " " + word)[2] <= max_width:
#             current_line += " " + word
#         else:
#             lines.append(current_line.strip())
#             current_line = word
#     lines.append(current_line.strip())

#     # 计算文本的宽度和高度
#     text_width, text_height = font.getsize_multiline("\n".join(lines))

#     # 计算文本的总高度
#     total_height = text_height + (len(lines) - 1) * line_spacing

#     # 计算文本的起始位置
#     x = position[0]
#     y = position[1] - total_height // 2

#     # 在图片上绘制文本
#     draw.multiline_text(
#         (x, y), "\n".join(lines), font=font, fill=(255, 255, 255), spacing=line_spacing
#     )

#     # 保存修改后的图片
#     image.save("output.png")


# # 示例用法
# image_path = "./test_thumbnail/1_out_check_with_logo_text.png"
# text = "这是一段很长的文本，需要自动换行。这是一段很长的文本，需要自动换行。"
# font_path = "./test_thumbnail/AlibabaHealthFont20CN-85B.TTF"
# font_size = 100
# position = (100, 540)  # 文本的中心位置
# margin_right = 100  # 距离右边背景的距离
# line_spacing = 10  # 行间距

# write_text_on_image(
#     image_path, text, font_path, font_size, position, margin_right, line_spacing
# )
import ast

a = """{'1':"既然我们在处理汽车,那么让我们把每个元素称为一辆车。","2":"在数组名称中添加"car",然后我们将每个元素称为一辆车。","3":"在数组名称中添加"car"和"cars"。"}"""
b = ast.literal_eval(a)
print(b)
