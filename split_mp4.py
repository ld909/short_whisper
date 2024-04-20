import os
from merge_srt_video import get_duration
from srt_format import parse_srt_with_re, time_str_to_obj, read_srt_file
from datetime import timedelta
import subprocess
import json


def calculate_video_cuts(end_times, max_length=timedelta(minutes=25)):
    """
    根据字幕结束时间计算视频的切割点。

    参数:
    end_times (list of timedelta): 每个字幕的结束时间列表。
    max_length (timedelta): 每段视频的最大长度，默认为25分钟。

    返回:
    list of timedelta: 视频切割点的列表。
    """
    if not end_times:
        return []

    # 初始化切割点列表和当前段的起始时间
    cut_points = []
    segment_start = timedelta(0)

    # 遍历所有字幕结束时间
    for i, end_time in enumerate(end_times):
        # 检查当前字幕结束时间是否超过了25分钟限制
        if end_time - segment_start > max_length:
            # 在上一个字幕的结束时间处进行切割
            cut_points.append(end_times[i - 1])
            segment_start = end_times[i - 1]

    return cut_points


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


def time_large_than_25(duration_seconds):
    return duration_seconds > 25 * 60


def split_mp4():
    mp4_folder = "/Volumes/dhl/ytb-videos/mp4_zh"
    topic = "code"
    channels = os.listdir(os.path.join(mp4_folder, topic))
    eng_format_srt_path = "/Users/donghaoliu/doc/video_material/format_srt"

    # remove DS_Store using list comprehension
    channels = [channel for channel in channels if channel != ".DS_Store"]

    for channel in channels:
        all_mp4 = os.listdir(os.path.join(mp4_folder, topic, channel))
        # remove .DS_Store
        all_mp4 = [mp4 for mp4 in all_mp4 if mp4 != ".DS_Store"]
        for mp4_single in all_mp4:
            # get the duration of the mp4 file
            mp4_path = os.path.join(mp4_folder, topic, channel, mp4_single)
            mp4_duration = get_duration(mp4_path)
            if not time_large_than_25(mp4_duration):
                continue
            # get the base name of the mp4 single file
            base_name = os.path.basename(mp4_single)
            base_name_prefix = os.path.splitext(base_name)[0]

            # srt path
            eng_srt_path = os.path.join(
                eng_format_srt_path, topic, channel, base_name_prefix + ".srt"
            )
            srt_content = read_srt_file(eng_srt_path)
            ts, _ = parse_srt_with_re(srt_content)

            # get the end time of each timestamp using list comprehension
            end_time_list = [time_str_to_obj(t[1]) for t in ts]

            # calculate the cut points
            cut_points = calculate_video_cuts(end_time_list)

            # cut the video
            ffmpeg_cut_video(mp4_path, cut_points)


if __name__ == "__main__":
    split_mp4()
