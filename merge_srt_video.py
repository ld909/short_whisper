import subprocess
import os
from mutagen import File


def run_ffmpeg_command(input_video, subtitles, font_file, output_video):
    """merge subtitle srt file into original mp4"""
    ffmpeg_command = [
        "ffmpeg",
        "-i",
        input_video,
        "-vf",
        f"subtitles='{subtitles}':force_style='FontName=MyCustomFont,FontFile={font_file},FontSize=24,PrimaryColour=&H00FFFFFF&'",
        "-c:a",
        "copy",
        output_video,
    ]

    subprocess.run(ffmpeg_command, check=True)


def get_duration(file_path):
    """get the duration of the media file in seconds"""
    media = File(file_path)
    duration = media.info.length
    return duration


def prev_mp4_done(mp4_in_path, mp4_out_path):
    """compare the duration of mp3 and mp4 files"""
    # 获取MP3文件的持续时间
    mp4_in_duration = get_duration(mp4_in_path)

    # 获取MP4文件的音频持续时间
    mp4_out_duration = get_duration(mp4_out_path)

    # find the larger duration
    larger_duration = max(mp4_in_duration, mp4_out_duration)
    less_duration = min(mp4_in_duration, mp4_out_duration)

    # divide the less duration by the larger duration
    ratio = less_duration / larger_duration

    if ratio < 0.997:
        print(f"MP4 in和MP4 out的音频持续时间不同")
        print(f"MP4 in持续时间: {mp4_in_duration}秒")
        print(f"MP4 out持续时间: {mp4_out_duration}秒")
        return False
    else:
        print(f"MP4 in和MP4 out的音频持续时间相同")
        return True


def merger_single(input_video, subtitles, output_video):
    # 使用示例
    font_file = "/Users/donghaoliu/Downloads/HYYiSongW.ttf"

    print("*" * 20)
    print("*" * 20)
    if not os.path.exists(input_video):
        print(f"{input_video} not found")
    if not os.path.exists(subtitles):
        print(f"{subtitles} not found")
    if not os.path.exists(font_file):
        print(f"{font_file} not found")
    print("*" * 20)
    print("*" * 20)

    run_ffmpeg_command(input_video, subtitles, font_file, output_video)


def controller():
    zh_srt_abs_path = "/Users/donghaoliu/doc/video_material/zh_srt/code"
    input_video_abs_path = "/Volumes/dhl/ytb-videos/code"
    dst_video_abs_path = "/Volumes/dhl/ytb-videos/mp4_zh/code"

    all_channels = os.listdir(zh_srt_abs_path)
    # remove .DS_Store using list comprehension
    all_channels = [folder for folder in all_channels if folder != ".DS_Store"]

    for channel in all_channels:
        # get all zh_srt files in the folder
        zh_srts = os.listdir(os.path.join(zh_srt_abs_path, channel))
        # remove .DS_Store using list comprehension
        zh_srts = [srt for srt in zh_srts if srt != ".DS_Store"]

        for zh_srt in zh_srts:
            # check if the output video file exists
            dst_mp4_path = os.path.join(
                dst_video_abs_path, channel, zh_srt.replace(".srt", ".mp4")
            )
            # 如果目标folder不存在，创建一个
            if not os.path.exists(os.path.join(dst_video_abs_path, channel)):
                os.makedirs(os.path.join(dst_video_abs_path, channel))

            # 输入视频文件路径
            mp4_path_in = os.path.join(
                input_video_abs_path, channel, zh_srt.replace(".srt", ".mp4")
            )

            # 比较mp4_path_in duration 和dst_mp4_path duration, 如果一致，跳过,使用python mutagen库
            # 如果不一致，重新merge
            if os.path.exists(dst_mp4_path):
                pre_done = prev_mp4_done(mp4_path_in, dst_mp4_path)
                if pre_done:
                    print(f"{dst_mp4_path} 视频合并完成 跳过继续...")
                    continue

            # merge the video with the zh_srt
            merger_single(
                mp4_path_in,
                os.path.join(zh_srt_abs_path, channel, zh_srt),
                dst_mp4_path,
            )


if __name__ == "__main__":
    controller()
