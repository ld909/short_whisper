from datetime import timedelta


# def calculate_video_cuts(end_times, max_length=timedelta(minutes=25)):
#     """
#     根据字幕结束时间计算视频的切割点。

#     参数:
#     end_times (list of timedelta): 每个字幕的结束时间列表。
#     max_length (timedelta): 每段视频的最大长度，默认为25分钟。

#     返回:
#     list of timedelta: 视频切割点的列表。
#     """
#     if not end_times:
#         return []

#     # 初始化切割点列表和当前段的起始时间
#     cut_points = []
#     segment_start = timedelta(0)

#     # 遍历所有字幕结束时间
#     for i, end_time in enumerate(end_times):
#         # 检查当前字幕结束时间是否超过了25分钟限制
#         if end_time - segment_start > max_length:
#             # 在上一个字幕的结束时间处进行切割
#             cut_points.append(end_times[i - 1])
#             segment_start = end_times[i - 1]

#     # 添加最后一个切割点
#     if end_times and (end_times[-1] - segment_start > timedelta(0)):
#         cut_points.append(end_times[-1])

#     return cut_points


# # 示例数据
# end_times = [
#     timedelta(minutes=5, seconds=30),
#     timedelta(minutes=23, seconds=45),
#     timedelta(minutes=48, seconds=10),
#     timedelta(minutes=70, seconds=30),
#     timedelta(minutes=95, seconds=20),
# ]

# # 计算切割点
# cut_points = calculate_video_cuts(end_times)
# print("切割点：", cut_points)

import subprocess


def ffmpeg_cut_video(video_path, cut_points):
    """
    使用 FFmpeg 根据提供的切割点将视频切割成多个片段。

    参数:
    video_path (str): 原始视频文件的路径。
    cut_points (list of timedelta): 视频切割点的列表。
    """
    # 添加视频开始作为第一个切割点
    cut_points = (
        [timedelta(0)] + cut_points + [None]
    )  # 添加None作为最后一个切割点的结束标志

    for i in range(1, len(cut_points)):
        start_time = cut_points[i - 1].total_seconds()
        end_time = cut_points[i].total_seconds() if cut_points[i] is not None else None

        # 构建输出文件名
        output_filename = f"{video_path.split('.')[0]}_clip_{i}.mp4"

        # 构建ffmpeg命令
        command = ["ffmpeg", "-i", video_path, "-ss", str(start_time)]
        if end_time is not None:
            command += ["-to", str(end_time)]
        command += ["-c", "copy", output_filename]  # 使用无损剪辑

        # 执行ffmpeg命令
        subprocess.run(command)

        print(f"Created clip: {output_filename}")


import json


def get_video_duration_ffprobe(video_path):
    """使用 ffprobe 获取视频的持续时间（秒）。"""
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        "-of",
        "json",
        video_path,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    duration = json.loads(result.stdout)["format"]["duration"]
    return float(duration)


# 示例使用
video_path = (
    "/Volumes/dhl/ytb-videos/mp4_zh/code/brocodez/C# Full Course for free 🎮.mp4"
)
cut_points = [timedelta(minutes=25), timedelta(minutes=50), timedelta(minutes=75)]
print("视频路径：", video_path)
duration = get_video_duration_ffprobe(video_path)
print("视频持续时间：", duration, "秒")
# ffmpeg_cut_video(video_path, cut_points)
