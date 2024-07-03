from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
from datetime import datetime, timedelta
import time
from tkinter import Image
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import anthropic
import os
import jieba
from moviepy.editor import ImageSequenceClip, concatenate_videoclips


def compute_year_progress_percentage(cur_date):
    """compute the year progress percentage"""
    year = cur_date.year
    start_date = datetime(year, 1, 1)
    end_date = datetime(year + 1, 1, 1)
    total_days = (end_date - start_date).days
    cur_days = (cur_date - start_date).days + 1  # Add 1 to include the current day

    # return rounded percentage, like 1.1%, 1.2%
    return round(cur_days / total_days * 100, 1)


def loop_until_year_last_day():
    """loop from the current day until the last day of the year"""
    # current date is now
    cur_date = datetime.now()
    year = cur_date.year
    thumbnail_vertical_dst_path = (
        "/media/dhl/TOSHIBA/video_material/thumbnail_vertical/time/time"
    )
    while cur_date.year == year:
        print(f"current date is {cur_date}")
        progress = compute_year_progress_percentage(cur_date)
        bar_upper_left, bar_lower_right, color = make_progress_bar(progress / 100)
        img_with_bar = draw_progress_bar(bar_upper_left, bar_lower_right, color)
        thumbnail_vertical = make_vertical_thumbnail(img_with_bar, progress)
        cur_month = cur_date.month
        cur_day = cur_date.day
        dst_path = (
            f"{thumbnail_vertical_dst_path}/{year}{cur_month:02d}{cur_day:02d}.png"
        )
        thumbnail_vertical.save(dst_path)
        print(f"{cur_date} - {compute_year_progress_percentage(cur_date)}%")

        make_vertical_video(cur_date, progress)

        cur_date += timedelta(days=1)


def make_progress_bar(percentage):
    """make a progress bar"""
    x1 = 106
    x2 = 1810
    x_diff = x2 - x1

    # bar_width
    bar_width = x_diff * percentage
    # round to the nearest integer
    bar_width = round(bar_width)

    bar_upper_left = (x1, 102)
    bar_lower_right = (x1 + bar_width, 473)

    # color is pure green
    color = (0, 255, 0)
    return bar_upper_left, bar_lower_right, color


def draw_progress_bar(bar_upper_left, bar_lower_right, color):
    """draw a progress bar"""

    img_path = "/home/dhl/Documents/short_whisper/year_progress/static_files/20240626-145623.jpg"
    img = cv2.imread(img_path)
    cv2.rectangle(img, bar_upper_left, bar_lower_right, color, -1)
    # cv2.imshow("progress bar", img)
    # cv2.waitKey(0)
    return img


def resize_image_keep_aspect_ratio(image, target_width):
    """resize image and keep the aspect ratio"""

    # 获取原图像的尺寸
    original_height, original_width = image.shape[:2]

    # 计算新的高度，以保持宽高比
    aspect_ratio = original_height / original_width
    new_height = int(target_width * aspect_ratio)

    # 调整图像大小
    resized_image = cv2.resize(image, (target_width, new_height))

    return resized_image


def combine_images_at_golden_ratio(bg_img, fg_img):
    """
    将前景图像放在背景图像的黄金分割点，并保存结果。

    参数：
    bg_image_path : str : 背景图像
    fg_image_path : str : 前景图像

    """

    # 获取背景图和前景图的宽高
    bg_height, bg_width = bg_img.shape[:2]
    fg_height, fg_width = fg_img.shape[:2]

    # 计算黄金分割点的位置
    golden_ratio = (1 + 5**0.5) / 2
    golden_height = int(bg_height / golden_ratio)

    # 计算前景图的放置位置（在背景图的下部分，居中对齐）
    x_offset = (bg_width - fg_width) // 2
    y_offset = golden_height

    # 创建一个具有相同通道数的背景区域
    bg_region = bg_img[y_offset : y_offset + fg_height, x_offset : x_offset + fg_width]

    # 如果前景图像有透明度，则需要考虑alpha混合
    if fg_img.shape[2] == 4:
        alpha_fg = fg_img[:, :, 3] / 255.0
        alpha_bg = 1.0 - alpha_fg

        for c in range(0, 3):
            bg_region[:, :, c] = (
                alpha_fg * fg_img[:, :, c] + alpha_bg * bg_region[:, :, c]
            )
    else:
        bg_img[y_offset : y_offset + fg_height, x_offset : x_offset + fg_width] = fg_img

    return bg_img


def add_text_to_image(image, text, position, font_path, font_size, text_color):
    """
    在图像上添加文字并保存结果。

    参数：
    image_path : str : 原始图像的文件路径
    text : str : 要添加的文字内容
    position : tuple : 文字在图像上的位置 (x, y)
    font_path : str : 字体文件的路径
    font_size : int : 文字的大小
    text_color : tuple : 文字的颜色 (R, G, B)
    output_path : str : 保存结果图像的路径
    """

    # 创建一个可以在图像上绘图的对象
    draw = ImageDraw.Draw(image)

    # 加载字体
    font = ImageFont.truetype(font_path, font_size)

    # 在图像上添加文字
    draw.text(position, text, font=font, fill=text_color)

    return image


def draw_text_on_image_thumbnail(conbined_img_pillow, percentage):

    # get current year
    cur_date = datetime.now()
    year = cur_date.year
    text1 = f"{year}已过去"
    text2 = f"{percentage}%"

    font_text2_path = (
        "/home/dhl/Documents/short_whisper/year_progress/static_files/douyuFont-2.otf"
    )
    font_text1_path = "/home/dhl/Documents/short_whisper/year_progress/static_files/SourceHanSerifCN-Medium.otf"

    font1_size = 160
    font2_size = 180

    font1_color = (0, 0, 0)
    font2_color = (0, 0, 0)

    font1_position = (100, 100)
    font2_position = (100, 450)

    # add text to the image
    conbined_img_pillow = add_text_to_image(
        conbined_img_pillow,
        text1,
        font1_position,
        font_text1_path,
        font1_size,
        font1_color,
    )
    conbined_img_pillow = add_text_to_image(
        conbined_img_pillow,
        text2,
        font2_position,
        font_text2_path,
        font2_size,
        font2_color,
    )

    # conbined_img_pillow.show()
    return conbined_img_pillow


def make_vertical_thumbnail(img_with_bar, percentage):
    """make a vertical thumbnail"""
    # resize the image to a thumbnail
    target_height = 1464
    target_width = 1080

    # make bg image with color white and size target_height x target_width
    bg_img = 255 * np.ones((target_height, target_width, 3), np.uint8)

    # resize image with bar to target width not the target height and keeping the aspect ratio
    resized_img_with_bar = resize_image_keep_aspect_ratio(img_with_bar, target_width)

    # combine the resized image with bar and the bg image
    combined_img = combine_images_at_golden_ratio(bg_img, resized_img_with_bar)

    # convert cv2 img to pillow img
    combined_img_pil = cv2.cvtColor(combined_img, cv2.COLOR_BGR2RGB)
    combined_img_pil = Image.fromarray(combined_img_pil)

    # draw text on the image
    thumbnail_vertical = draw_text_on_image_thumbnail(combined_img_pil, percentage)

    return thumbnail_vertical


def set_clash_proxy():

    # 设置环境变量
    os.environ["http_proxy"] = "http://127.0.0.1:7890"
    os.environ["https_proxy"] = "http://127.0.0.1:7890"
    os.environ["all_proxy"] = "socks5://127.0.0.1:7891"
    print("成功设定clash环境proxy...")


def unset_clash_proxy():
    # 删除环境变量
    os.environ.pop("http_proxy", None)
    os.environ.pop("https_proxy", None)
    os.environ.pop("all_proxy", None)
    print("成功取消clash环境proxy...")


def blend_images_center(background, foreground):
    """
    将前景图像融合到背景图像的正中间，并保存结果。

    参数：
    bg_image_path : str : 背景图像的文件路径
    fg_image_path : str : 前景图像的文件路径
    output_path : str : 保存结果图像的路径
    """

    # 获取背景图和前景图的宽高
    bg_height, bg_width = background.shape[:2]
    fg_height, fg_width = foreground.shape[:2]

    # 计算前景图像在背景图像中的位置，位于正中间
    x_offset = (bg_width - fg_width) // 2
    y_offset = (bg_height - fg_height) // 2

    # 检查前景图是否有透明度
    if foreground.shape[2] == 4:
        # 分离前景图的 BGR 和 alpha 通道
        fg_bgr = foreground[:, :, :3]
        alpha_channel = foreground[:, :, 3]

        # 创建 alpha 掩码和反向 alpha 掩码
        alpha_mask = alpha_channel / 255.0
        alpha_inv_mask = 1.0 - alpha_mask

        # 提取背景区域
        bg_region = background[
            y_offset : y_offset + fg_height, x_offset : x_offset + fg_width
        ]

        # 进行 alpha 融合
        for c in range(0, 3):
            bg_region[:, :, c] = (
                alpha_mask * fg_bgr[:, :, c] + alpha_inv_mask * bg_region[:, :, c]
            )

        # 将融合后的部分回放到背景图像中
        background[y_offset : y_offset + fg_height, x_offset : x_offset + fg_width] = (
            bg_region
        )
    else:
        # 如果没有透明度，直接覆盖
        background[y_offset : y_offset + fg_height, x_offset : x_offset + fg_width] = (
            foreground
        )

    # return the blended image
    return background


def draw_text_on_video(conbined_img_pillow, percentage):

    # get current year
    cur_date = datetime.now()
    year = cur_date.year
    text1 = f"{year}已过去"
    text2 = f"{percentage}%"

    font_text2_path = (
        "/home/dhl/Documents/short_whisper/year_progress/static_files/douyuFont-2.otf"
    )
    font_text1_path = "/home/dhl/Documents/short_whisper/year_progress/static_files/SourceHanSerifCN-Medium.otf"

    font1_size = 160
    font2_size = 180

    font1_color = (0, 0, 0)
    font2_color = (0, 0, 0)

    font1_position = (100, 100)
    font2_position = (100, 390)

    # add text to the image
    conbined_img_pillow = add_text_to_image(
        conbined_img_pillow,
        text1,
        font1_position,
        font_text1_path,
        font1_size,
        font1_color,
    )
    conbined_img_pillow = add_text_to_image(
        conbined_img_pillow,
        text2,
        font2_position,
        font_text2_path,
        font2_size,
        font2_color,
    )

    return conbined_img_pillow


def draw_sonnet_text_on_image(bg_img, text, font_path):
    """在图像上绘制sonnet提示语"""

    # Chinese title position on the thumbnail bg image
    position = (100, 1380)  # 文本的起始位置

    # chinese font
    font_size = 60  # 字体大小
    right_padding = 100  # 文本到图像右边缘的距离

    # 贴中文标题到背景图像上
    merged_thumbnail_img = draw_zh_with_warp_on_image(
        bg_img,
        text,
        position,
        font_path,
        font_size,
        right_padding,
    )

    return merged_thumbnail_img


def draw_zh_with_warp_on_image(
    image, text, position, font_path, font_size, right_padding
):
    """在图像上绘制文本"""
    color = "black"
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_path, font_size)

    # 计算文本宽度的最大值
    max_width = image.width - position[0] - right_padding

    # 使用 jieba 进行中文分词"
    words = list(jieba.cut(text, cut_all=False))

    # 自动换行
    lines = []
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


def text_comment():
    """generate a text comment for the video"""

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        temperature=1,
        system="你是一个很强的营销大师，你说的话能够引起用户的积极互动和讨论留言。在短视频每天进度下面出谋划策。每天进度这个号会可视化当天在本年的时间进度。你会针对每天的短视频，给出一句老少皆宜，通俗易懂的句子，引起大家讨论或反思，让大家进行对今天目标、工作、人生、感情等的思考和留言互动。目的是积极调动大家发言，积极调动大家的互动欲望。",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "给出今天互动提醒的一句话，直接返回提醒的句子，不需要返回任何多于的句子，句子字数不要多于20字，简短有力，发人深省，勾起互动欲望。",
                    }
                ],
            }
        ],
    )
    # print(message.content)

    # return the content of the message
    return message.content[0].text


def create_video(cur_date, audio_path, duration=2, bg_img_width=1080):
    """create a video clip with progress bar"""
    all_dates_frame = get_uniform_dates(cur_date)
    frames = []
    for date_frame in all_dates_frame:
        print(f"current date is {date_frame}")
        cur_progress = compute_year_progress_percentage(date_frame)
        bar_upper_left, bar_lower_right, _ = make_progress_bar(cur_progress / 100)
        img_with_bar = img_with_bar = draw_progress_bar(
            bar_upper_left, bar_lower_right, (0, 255, 0)
        )
        # show the progress bar
        img_with_bar = resize_image_keep_aspect_ratio(img_with_bar, bg_img_width)
        merged_img_pil = make_vertical_thumbnail(img_with_bar, cur_progress)
        # convert pillow img to cv2 img
        merged_img = cv2.cvtColor(np.array(merged_img_pil), cv2.COLOR_RGB2BGR)
        frames.append(merged_img)

    # turn image to rgb
    frames = [cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) for frame in frames]

    # 创建ImageSequenceClip对象，并设置fps为30
    clip = ImageSequenceClip(frames, fps=30)

    last_frame = frames[-1]

    # last clip duration 1.6s
    last_clip = ImageClip(last_frame).set_duration(duration - 2)

    # add last clip to the clip
    merged_clip = concatenate_videoclips([clip, last_clip])

    # 加载音频文件
    audio_clip = AudioFileClip(audio_path).subclip(0, duration)

    # 将音频添加到图像片段
    video_clip = merged_clip.set_audio(audio_clip)

    return video_clip


def get_uniform_dates(today, num_days=60):

    # 获取今年的元旦
    new_year = datetime(today.year, 1, 1)

    # 计算从元旦到今天的天数
    delta_days = (today - new_year).days + 1  # 加1包括今天

    if delta_days < num_days:
        # 如果天数不足60,进行差值
        dates = [new_year + timedelta(days=i % delta_days) for i in range(num_days)]
    else:
        # 均匀选择60天，确保今天被包含
        indices = np.linspace(0, delta_days - 1, num_days, dtype=int)
        dates = [new_year + timedelta(days=int(idx)) for idx in indices]
        # 确保今天在列表中
        if today not in dates:
            dates[-1] = today

    return sorted(dates)


def make_vertical_video(cur_date, progress):
    """make a vertical video"""
    # bg_img_width = 1080
    # bg_img_height = 1464
    # bg_img = 255 * np.ones((bg_img_height, bg_img_width, 3), np.uint8)

    # bar_upper_left, bar_lower_right, color = make_progress_bar(progress / 100)
    # img_with_bar = draw_progress_bar(bar_upper_left, bar_lower_right, color)
    # img_with_bar = resize_image_keep_aspect_ratio(img_with_bar, bg_img_width)

    # # combine the resized image with bar and the bg image at the center
    # merged_img = blend_images_center(bg_img, img_with_bar)

    # # convert cv2 img to pillow img
    # merged_img_pil = cv2.cvtColor(merged_img, cv2.COLOR_BGR2RGB)
    # merged_img_pil = Image.fromarray(merged_img_pil)

    # # draw text on the image
    # img_with_txt = draw_text_on_video(merged_img_pil, progress)

    # draw text_comment on the image
    # img_with_txt = draw_sonnet_text_on_image(
    #     img_with_txt,
    #     text_comment_str,
    #     font_path="/home/dhl/Documents/short_whisper/year_progress/static_files/SourceHanSerifCN-Medium.otf",
    # )

    bg_mp3_path = "/home/dhl/Documents/short_whisper/year_progress/static_files/second-hand-149907.mp3"
    final_clip = create_video(cur_date, bg_mp3_path, duration=3.8)

    mp4_dst = "/media/dhl/TOSHIBA/ytb-videos/tts_mp4/time/time"
    cur_month = cur_date.month
    cur_day = cur_date.day
    dst_path = f"{mp4_dst}/{cur_date.year}{cur_month:02d}{cur_day:02d}.mp4"

    final_clip.write_videofile(
        dst_path,
        fps=30,
        threads=4,
        codec="libx264",
        audio_codec="aac",
        audio_bitrate="192k",
        audio_fps=44100,
    )

    # # wait for 1000 second
    # print("wait for 1000 seconds")
    # final_clip.write_videofile("./t3.mp4", fps=30, threads=4)
    # time.sleep(1000)


if __name__ == "__main__":
    loop_until_year_last_day()
