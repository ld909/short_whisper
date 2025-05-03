#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from moviepy import VideoFileClip, TextClip, CompositeVideoClip


def add_subtitles_to_video(video_path, srt_path, output_path, font_path):
    """
    使用 MoviePy 2.x 为视频添加 SRT 格式的字幕

    参数:
        video_path (str): 输入视频文件路径
        srt_path (str): 输入 SRT 字幕文件路径
        output_path (str): 输出视频文件路径
        font_path (str): 字体文件路径
    """
    print(
        f"添加字幕：\n视频: {video_path}\n字幕: {srt_path}\n输出: {output_path}\n字体: {font_path}"
    )

    # 检查文件是否存在
    if not os.path.exists(video_path):
        print(f"错误: 视频文件不存在 - {video_path}")
        return False

    if not os.path.exists(srt_path):
        print(f"错误: 字幕文件不存在 - {srt_path}")
        return False

    if not os.path.exists(font_path):
        print(f"错误: 字体文件不存在 - {font_path}")
        return False

    try:
        # 加载视频文件
        print("加载视频文件...")
        video = VideoFileClip(video_path)

        # 解析SRT文件，手动构建字幕
        print("解析字幕文件...")
        subtitles = []

        # 解析SRT文件格式
        with open(srt_path, "r", encoding="utf-8") as srt_file:
            content = srt_file.read()

        # 分割每个字幕条目
        subtitle_blocks = content.strip().split("\n\n")
        for block in subtitle_blocks:
            lines = block.strip().split("\n")
            if len(lines) >= 3:  # 至少需要3行：序号、时间、文本
                # 解析时间行 (格式: 00:00:00,000 --> 00:00:00,000)
                time_line = lines[1]
                times = time_line.split(" --> ")
                if len(times) == 2:
                    start_time = convert_time(times[0])
                    end_time = convert_time(times[1])

                    # 获取字幕文本 (可能有多行)
                    text = "\n".join(lines[2:])

                    # 添加到字幕列表
                    subtitles.append(((start_time, end_time), text))

        print(f"解析到 {len(subtitles)} 条字幕")

        # 创建字幕剪辑
        print("创建字幕剪辑...")
        subtitle_clips = []

        for (start_time, end_time), text in subtitles:
            duration = end_time - start_time
            if duration > 0:
                # 创建文本剪辑
                text_clip = TextClip(
                    text=text,
                    font=font_path,
                    font_size=30,
                    color="white",
                    stroke_color="black",
                    stroke_width=2,
                )

                # 设置位置、持续时间和开始时间
                text_clip = text_clip.with_position(("center", "bottom"))
                text_clip = text_clip.with_duration(duration)
                text_clip = text_clip.with_start(start_time)

                subtitle_clips.append(text_clip)

        # 合成视频和所有字幕剪辑
        print("合成视频和字幕...")
        final_video = CompositeVideoClip([video] + subtitle_clips)

        # 写入输出文件
        print("正在生成带字幕的视频文件...")
        final_video.write_videofile(
            output_path, codec="libx264", audio_codec="aac", fps=video.fps
        )

        # 关闭视频文件以释放资源
        video.close()

        print(f"字幕添加完成！输出文件: {output_path}")
        return True

    except Exception as e:
        print(f"处理过程中出错: {str(e)}")
        # 打印更详细的异常信息
        import traceback

        traceback.print_exc()
        return False


def convert_time(time_str):
    """
    将SRT时间格式 (00:00:00,000) 转换为秒
    """
    # 替换逗号为点
    time_str = time_str.replace(",", ".")

    # 分割时、分、秒
    h, m, s = time_str.split(":")

    # 转换为秒
    total_seconds = int(h) * 3600 + int(m) * 60 + float(s)
    return total_seconds


if __name__ == "__main__":
    # 设置输入和输出文件路径
    input_video = "./clip_1.mp4"
    input_srt = "./test_srt_out/o_en.srt"
    output_video = "./clip_1_with_subtitles.mp4"
    font_file = "/Users/donghaoliu/doc/short_whisper/fonts/Noto_Sans_EN/NotoSans-VariableFont_wdth,wght.ttf"

    # 执行字幕添加
    add_subtitles_to_video(input_video, input_srt, output_video, font_file)
