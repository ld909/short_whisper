import os
from merge_srt_video import get_duration
from srt_format import parse_srt_with_re, time_str_to_obj, read_srt_file
from datetime import timedelta
import subprocess
import json
from upload_controller import read_channels_from_ref_json, load_ref_json


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


def ffmpeg_cut_video(video_path, cut_points, reference_dict, channel):
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
        output_filename = video_path.replace(".mp4", f"_clip_{i}.mp4")
        clip_base_name = os.path.basename(output_filename)

        # if output filename exist skip
        if os.path.exists(output_filename):
            continue

        # get the base name of the video
        base_name = os.path.basename(video_path)
        # add the base name to the reference dict
        reference_dict[channel][clip_base_name] = base_name

        # 构建ffmpeg命令
        command = ["ffmpeg", "-i", video_path, "-ss", str(start_time)]
        if end_time is not None:
            command += ["-to", str(end_time)]
        command += ["-c", "copy", output_filename]  # 使用无损剪辑

        # 执行ffmpeg命令
        subprocess.run(command)

        print(f"Created clip: {output_filename}")

    return reference_dict


def time_large_than_30(duration_seconds):
    """判断视频时长是否大于25分钟。"""
    return duration_seconds > 30 * 60


def read_ref_json(ref_json_path):
    """读取ref.json文件并返回字典。"""
    with open(ref_json_path, "r", encoding="utf-8") as file:
        ref_dict = json.load(file)
    return ref_dict


def split_mp4(topic):
    """split the mp4 files into clips with duration less than 25 minutes and generate the reference json file."""

    mp4_folder = "/Volumes/dhl/ytb-videos/mp4_zh"
    eng_format_srt_path = "/Users/donghaoliu/doc/video_material/format_srt"

    publish_ref = f"/Users/donghaoliu/doc/video_material/publish_ref/{topic}"
    # create the publish_ref folder if not exist
    if not os.path.exists(publish_ref):
        os.makedirs(publish_ref)

    # 创造ref.json文件的路径
    ref_json_path = os.path.join(publish_ref, "ref.json")

    # get all channels from the ref.json file
    channels = read_channels_from_ref_json(topic)
    # if ref.json exists, read the ref.json file
    if os.path.exists(ref_json_path):
        # json load the ref.json file
        print(f"读取 {ref_json_path} 文件...")
        ref_dict = load_ref_json(topic)
    else:
        # reference dict
        ref_dict = {}

    for channel in channels:
        print(f"处理频道：{channel}...")
        all_mp4 = os.listdir(os.path.join(mp4_folder, topic, channel))
        # remove .DS_Store
        all_mp4 = [mp4 for mp4 in all_mp4 if mp4 != ".DS_Store"]

        if channel not in ref_dict:
            ref_dict[channel] = {}
        for mp4_single in all_mp4:
            # print(mp4_single, list(ref_dict[channel].keys()))
            # check if the mp4 file is already in the ref.json file
            if mp4_single in list(ref_dict[channel].keys()):

                # print(
                #     f"频道：{channel}，视频：{mp4_single} 已经在 ref.json 文件中，跳过..."
                # )
                continue
            else:
                print(f"新视频，处理视频：{mp4_single}")

            # get the duration of the mp4 file
            mp4_path = os.path.join(mp4_folder, topic, channel, mp4_single)
            mp4_duration = get_duration(mp4_path)
            if not time_large_than_30(mp4_duration):
                ref_dict[channel][mp4_single] = mp4_single
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
            ref_dict = ffmpeg_cut_video(mp4_path, cut_points, ref_dict, channel)

    # 使用 ensure_ascii=False 和 indent=4 参数
    json_data = json.dumps(ref_dict, ensure_ascii=False, indent=4)

    # 将 JSON 数据写入文件
    with open(ref_json_path, "w", encoding="utf-8") as file:
        file.write(json_data)


if __name__ == "__main__":
    topic = "code"
    split_mp4(topic)
