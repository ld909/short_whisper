#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
运镜脚本实现平移和缩放效果
要求：
1. 平移移动，不要折返，直线运动
2. 放大或缩小，单程按动，要么放大，要么缩小
3. 运动生成mp4 clip，可以选择生成的duration，默认7秒
4. 运镜效果非常平滑，无卡顿
5. mp4分辨率为1080p
6. mp4开始时，视频没有黑边，图像填满
7. 使用MoviePy 2.x版本
"""

# 修改导入部分，兼容MoviePy 2.x
from moviepy import VideoClip, ImageClip, ColorClip
import numpy as np
import cv2
from PIL import Image
import math
from typing import Tuple, Callable, Literal, Optional, Union

# 定义分辨率
TARGET_RESOLUTION = (1920, 1080)


def smooth_pan(
    image_path: str,
    output_path: str,
    duration: float = 7.0,
    direction: Literal[
        "left_to_right", "right_to_left", "top_to_bottom", "bottom_to_top"
    ] = "left_to_right",
    fps: int = 30,
    pan_speed: float = 1.0,
    start_padding: float = 0.15,  # 新增参数：起始视野边距比例
) -> None:
    """
    创建平滑的平移运镜效果

    参数:
        image_path: 输入图像路径
        output_path: 输出视频路径
        duration: 视频时长（秒）
        direction: 平移方向
        fps: 视频帧率
        pan_speed: 平移速度，值越大移动越快
        start_padding: 起始视野边距比例，数值越大，起始视野范围越大
    """
    # 加载图像
    orig_img = Image.open(image_path)

    # 确保图像足够大以支持平移
    # 需要放大图像使其至少是目标分辨率的两倍宽/高（取决于平移方向）
    width, height = orig_img.size
    target_width, target_height = TARGET_RESOLUTION

    # 计算需要的放大比例
    if direction in ["left_to_right", "right_to_left"]:
        scale = max(1, (target_width * 2) / width)
    else:  # 上下平移
        scale = max(1, (target_height * 2) / height)

    # 放大图像
    new_width = int(width * scale)
    new_height = int(height * scale)
    img_resized = orig_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    img_array = np.array(img_resized)

    # 定义平移函数，基于方向计算每一帧的位置
    def get_panned_frame(t: float):
        # 归一化时间，从0到1
        # 应用速度因子，使用缓动函数使运动更平滑
        # 使用 min(1.0, ...) 确保进度不会超过1
        progress = min(1.0, (t / duration) * pan_speed)

        # 计算可用的边距空间
        available_width_margin = new_width - target_width
        available_height_margin = new_height - target_height

        # 使用start_padding参数调整起始视野
        if direction == "left_to_right":
            # 从左向右移动，保留部分左边界
            start_offset = int(available_width_margin * start_padding)
            max_offset = available_width_margin - start_offset
            offset_x = int(start_offset + progress * max_offset)
            offset_y = (new_height - target_height) // 2
            frame = img_array[
                offset_y : offset_y + target_height, offset_x : offset_x + target_width
            ]

        elif direction == "right_to_left":
            # 从右向左移动，保留部分右边界
            start_offset = int(available_width_margin * start_padding)
            max_offset = available_width_margin - start_offset
            offset_x = int(
                available_width_margin - start_offset - progress * max_offset
            )
            offset_y = (new_height - target_height) // 2
            frame = img_array[
                offset_y : offset_y + target_height, offset_x : offset_x + target_width
            ]

        elif direction == "top_to_bottom":
            # 从上到下移动，保留部分上边界
            start_offset = int(available_height_margin * start_padding)
            max_offset = available_height_margin - start_offset
            offset_x = (new_width - target_width) // 2
            offset_y = int(start_offset + progress * max_offset)
            frame = img_array[
                offset_y : offset_y + target_height, offset_x : offset_x + target_width
            ]

        elif direction == "bottom_to_top":
            # 从下到上移动，保留部分下边界
            start_offset = int(available_height_margin * start_padding)
            max_offset = available_height_margin - start_offset
            offset_x = (new_width - target_width) // 2
            offset_y = int(
                available_height_margin - start_offset - progress * max_offset
            )
            frame = img_array[
                offset_y : offset_y + target_height, offset_x : offset_x + target_width
            ]

        return frame

    # 创建自定义视频剪辑
    clip = VideoClip(lambda t: get_panned_frame(t), duration=duration)
    clip = clip.with_fps(fps)

    # 保存视频
    clip.write_videofile(output_path, codec="libx264", fps=fps)

    print(f"平移视频已保存到: {output_path}")


def smooth_zoom(
    image_path: str,
    output_path: str,
    duration: float = 7.0,
    zoom_type: Literal["in", "out"] = "in",
    fps: int = 30,
    zoom_speed: float = 1.0,
    position: Literal[
        "center",
        "left",
        "right",
        "top",
        "bottom",
        "topleft",
        "topright",
        "bottomleft",
        "bottomright",
    ] = "center",
) -> None:
    """
    创建平滑的缩放运镜效果

    参数:
        image_path: 输入图像路径
        output_path: 输出视频路径
        duration: 视频时长（秒）
        zoom_type: 缩放类型，"in"表示放大，"out"表示缩小
        fps: 视频帧率
        zoom_speed: 缩放速度
        position: 缩放中心位置
    """
    # 读取图像并调整大小以匹配目标分辨率
    img = Image.open(image_path)

    # 计算调整后的大小，保持纵横比
    width, height = img.size
    target_width, target_height = TARGET_RESOLUTION

    # 计算缩放比例
    ratio = max(target_width / width, target_height / height)

    # 调整图像大小，使其至少填满目标分辨率
    new_width = int(width * ratio)
    new_height = int(height * ratio)
    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # 创建一个与目标分辨率相同大小的图像
    canvas = Image.new("RGB", TARGET_RESOLUTION, (0, 0, 0))

    # 将调整大小后的图像粘贴到中心
    x_offset = (target_width - new_width) // 2
    y_offset = (target_height - new_height) // 2
    canvas.paste(img_resized, (x_offset, y_offset))

    # 将PIL图像转换为numpy数组
    img_array = np.array(canvas)

    # 创建视频剪辑
    clip = ImageClip(img_array).with_duration(duration).with_fps(fps)

    # 使用OpenCV实现的平滑缩放效果
    def zoom_effect(clip, mode="in", position="center", speed=1.0):
        fps = clip.fps
        duration = clip.duration
        total_frames = int(duration * fps)

        def main(get_frame, t):
            frame = get_frame(t)
            h, w = frame.shape[:2]
            i = t * fps

            if mode == "out":
                i = total_frames - i

            # 计算当前帧的缩放比例，使用一个平滑的缩放函数
            zoom = 1 + (i * ((0.1 * speed) / total_frames))

            # 根据位置计算偏移量
            positions = {
                "center": [(w - (w * zoom)) / 2, (h - (h * zoom)) / 2],
                "left": [0, (h - (h * zoom)) / 2],
                "right": [(w - (w * zoom)), (h - (h * zoom)) / 2],
                "top": [(w - (w * zoom)) / 2, 0],
                "topleft": [0, 0],
                "topright": [(w - (w * zoom)), 0],
                "bottom": [(w - (w * zoom)) / 2, (h - (h * zoom))],
                "bottomleft": [0, (h - (h * zoom))],
                "bottomright": [(w - (w * zoom)), (h - (h * zoom))],
            }

            tx, ty = positions[position]

            # 创建仿射变换矩阵
            M = np.array([[zoom, 0, tx], [0, zoom, ty]])

            # 应用仿射变换
            frame = cv2.warpAffine(frame, M, (w, h))

            return frame

        return clip.transform(main)

    # 应用缩放效果
    zoomed_clip = zoom_effect(clip, mode=zoom_type, position=position, speed=zoom_speed)

    # 保存视频
    zoomed_clip.write_videofile(output_path, codec="libx264", fps=fps)

    print(f"缩放视频已保存到: {output_path}")


def main():
    """
    演示运镜脚本的使用方法
    """
    import argparse

    parser = argparse.ArgumentParser(description="运镜脚本：平移和缩放")
    parser.add_argument("image_path", help="输入图像路径")
    parser.add_argument("--output", "-o", default="output.mp4", help="输出视频路径")
    parser.add_argument(
        "--type",
        "-t",
        choices=["pan", "zoom"],
        default="pan",
        help="运镜类型：平移或缩放",
    )
    parser.add_argument(
        "--direction",
        "-d",
        choices=["left_to_right", "right_to_left", "top_to_bottom", "bottom_to_top"],
        default="left_to_right",
        help="平移方向",
    )
    parser.add_argument(
        "--zoom", "-z", choices=["in", "out"], default="in", help="缩放类型"
    )
    parser.add_argument("--duration", default=7.0, type=float, help="视频时长，默认7秒")
    parser.add_argument("--fps", default=30, type=int, help="帧率，默认30")
    parser.add_argument(
        "--zoom-speed", default=1.0, type=float, help="缩放速度，默认1.0"
    )
    parser.add_argument(
        "--pan-speed", default=1.0, type=float, help="平移速度，默认1.0"
    )
    parser.add_argument(
        "--position",
        choices=[
            "center",
            "left",
            "right",
            "top",
            "bottom",
            "topleft",
            "topright",
            "bottomleft",
            "bottomright",
        ],
        default="center",
        help="缩放中心位置",
    )
    parser.add_argument(
        "--start-padding",
        type=float,
        default=0.15,
        help="平移起始视野边距比例，值越大视野越大，默认0.15",
    )

    args = parser.parse_args()

    if args.type == "pan":
        smooth_pan(
            args.image_path,
            args.output,
            duration=args.duration,
            direction=args.direction,
            fps=args.fps,
            pan_speed=args.pan_speed,
            start_padding=args.start_padding,
        )
    else:  # zoom
        smooth_zoom(
            args.image_path,
            args.output,
            duration=args.duration,
            zoom_type=args.zoom,
            fps=args.fps,
            zoom_speed=args.zoom_speed,
            position=args.position,
        )


if __name__ == "__main__":
    main()
