import os
import platform
import tempfile

import ffmpeg
from pydub import AudioSegment
from moviepy.editor import (
    VideoFileClip,
    concatenate_videoclips,
    AudioFileClip,
)
from srt_format import read_srt_file, parse_srt_with_re
from tts_zh_mp3 import get_sorted_mp3_list
from srt_format import time_str_to_obj
from tqdm import tqdm
from merge_srt_video import get_duration
import time
from moviepy.editor import VideoFileClip
from datetime import timedelta
from colorama import Fore, Back, Style, init


def detect_os():
    os_name = platform.system()
    if os_name == "Darwin":
        print("You are using macOS.")
        return "mac"
    elif os_name == "Linux":
        print("You are using Linux.")
        return "linux"


def get_mp4_clip_list(video_path, ts_list, mp3_list):
    """得到mp4和mp3的clips"""
    # 加载视频文件
    video = VideoFileClip(video_path)

    mp4_clip_list = []
    mp3_clip_list = []
    clip_idx = 0
    current_time = timedelta(seconds=0)
    for srt_idx, (ts, mp3_path) in enumerate(tqdm(zip(ts_list, mp3_list))):
        start_time_str, end_time_str = ts

        # read mp3 file
        mp3_clip = AudioSegment.from_mp3(mp3_path)

        start_time = time_str_to_obj(start_time_str)
        end_time = time_str_to_obj(end_time_str)

        # 将 timedelta 对象转换为秒
        start_seconds = start_time.total_seconds()
        end_seconds = end_time.total_seconds()

        # 处理字幕时间戳之前的片段
        if current_time < start_time:
            mp4_clip = video.subclip(current_time.total_seconds(), start_seconds)
            mp4_clip_list.append([0, mp4_clip])
            # 创建一个silence mp3片段
            silence_duration = (start_time - current_time).total_seconds()
            silence = AudioSegment.silent(duration=int(silence_duration * 1000))
            mp3_clip_list.append([0, silence])

            # for test, save mp3 and mp4 clips to ./test_mp3 and ./test_mp4 with clip_idx as name
            # mp3_clip.export(f"./test_mp3/{clip_idx}.mp3", format="mp3")
            # mp4_clip.write_videofile(f"./test_mp4/{clip_idx}.mp4", codec="libx264")
            # clip_idx += 1

        # 处理字幕时间戳内的片段
        mp4_clip = video.subclip(start_seconds, end_seconds)
        mp4_clip_list.append([1, mp4_clip])
        mp3_clip_list.append([1, mp3_clip])
        current_time = end_time

        # for test, save mp3 and mp4 clips to ./test_mp3 and ./test_mp4 with clip_idx as name
        # mp3_clip.export(f"./test_mp3/{clip_idx}.mp3", format="mp3")
        # mp4_clip.write_videofile(f"./test_mp4/{clip_idx}.mp4", codec="libx264")
        # clip_idx += 1

    # 处理最后一个字幕时间戳之后的片段,前提是视频时长和当前时间差大于0.5s
    time_diff = video.duration - current_time.total_seconds()
    if current_time < timedelta(seconds=video.duration) and time_diff > 0.5:

        mp4_clip = video.subclip(current_time.total_seconds())
        mp4_clip_list.append([0, mp4_clip])
        # 创建一个silence片段
        silence_duration = video.duration - current_time.total_seconds()
        silence = AudioSegment.silent(duration=int(silence_duration * 1000))
        mp3_clip_list.append([0, silence])

        # for test, save mp3 and mp4 clips to ./test_mp3 and ./test_mp4 with clip_idx as name
        # mp3_clip.export(f"./test_mp3/{clip_idx}.mp3", format="mp3")
        # mp4_clip.write_videofile(f"./test_mp4/{clip_idx}.mp4", codec="libx264")
        # clip_idx += 1

    return mp4_clip_list, mp3_clip_list


def combine_speech_bg(speech, background):

    # 设置背景音乐的音量 (以 dB 为单位)
    background_volume = -15  # 将背景音乐降低 X dB

    # 合并 speech 和 background
    combined = speech.overlay(background.apply_gain(background_volume))
    return combined


def merge_mp3tomp4(
    srt_file_path,
    video_file_path,
    chinese_audio_files,
    bg_music,
    merge_mp3_single_path=None,
    bg_mp3_path="",
):
    """把mp3和mp4合成为新视频"""
    srt_content = read_srt_file(srt_file_path)
    ts_list, _ = parse_srt_with_re(srt_content)

    mp4_list, mp3_list = get_mp4_clip_list(
        video_file_path, ts_list, chinese_audio_files
    )
    print(f"mp4_list长度：{len(mp4_list)}")

    new_mp4_list = []
    new_mp3_list = []

    for index, (mp3, mp4) in tqdm(enumerate(zip(mp3_list, mp4_list))):
        if mp3[0] == 1 and mp4[0] == 1:

            # 比较音频和视频的长度
            mp3_duration = mp3[1].duration_seconds
            mp4_duration = mp4[1].duration

            # 如果音频长度小于视频长度，则在音频后面添加silence
            if mp3_duration < mp4_duration:
                silence_duration = mp4_duration - mp3_duration
                silence = AudioSegment.silent(duration=int(silence_duration * 1000))
                new_mp3_clip = mp3[1] + silence
                new_mp3_list.append(new_mp3_clip)
                new_mp4_list.append(mp4[1])

            # 如果音频长度大于视频长度，延长视频长度
            else:
                new_mp3_list.append(mp3[1])
                new_mp4_list.append(mp4[1].set_duration(mp3_duration))

        # 此部分存在视频但没有对应音频,此时mp3是silence
        elif mp3[0] == 0 and mp4[0] == 0:
            mp3_duration = mp3[1].duration_seconds
            mp4_duration = mp4[1].duration

            # 两个片段长度比例不能小于0.98
            assert mp3_duration / mp4_duration > 0.98
            new_mp4_list.append(mp4[1])
            new_mp3_list.append(mp3[1])

    # 合并视频
    final_video = concatenate_videoclips(new_mp4_list)

    # 合并音频
    final_audio = AudioSegment.empty()
    for audio in new_mp3_list:
        final_audio += audio

    if bg_music:
        # 添加背景音乐
        bg_audio = AudioSegment.from_file(
            bg_mp3_path,
            format="mp3",
        )
        bg_audio = truncate_or_repeat_audio(bg_audio, final_video.duration)

        # 合并音频
        final_audio = combine_speech_bg(final_audio, bg_audio)

    # 保存音频为临时文件，使用后删除
    # temp_audio = tempfile.NamedTemporaryFile()
    final_audio.export(merge_mp3_single_path, format="mp3")
    time.sleep(3)

    # 从临时文件中加载音频，使用moviepy的AudioFileClip
    final_audio = AudioFileClip(merge_mp3_single_path)
    # 将音频添加到视频中
    final_video = final_video.set_audio(final_audio)

    return final_video


def merge_mp3tomp4_gpu(
    srt_file_path,
    video_file_path,
    chinese_audio_files,
    bg_music,
    merge_mp3_single_path=None,
    bg_mp3_path="",
    dst_mp4_path="",
):
    """把mp3和mp4合成为新视频"""
    print(f"使用gpu合成！")
    srt_content = read_srt_file(srt_file_path)
    ts_list, _ = parse_srt_with_re(srt_content)

    mp4_list, mp3_list = get_mp4_clip_list(
        video_file_path, ts_list, chinese_audio_files
    )
    assert len(mp4_list) == len(mp3_list)

    new_mp4_list = []
    new_mp3_list = []

    for mp3, mp4 in tqdm(zip(mp3_list, mp4_list)):
        if mp3[0] == 1 and mp4[0] == 1:

            # 比较音频和视频的长度
            mp3_duration = mp3[1].duration_seconds
            mp4_duration = mp4[1].duration

            # 如果音频长度小于视频长度，则在音频后面添加silence
            if mp3_duration < mp4_duration:
                silence_duration = mp4_duration - mp3_duration
                silence = AudioSegment.silent(duration=int(silence_duration * 1000))
                new_mp3_clip = mp3[1] + silence
                new_mp3_list.append(new_mp3_clip)
                new_mp4_list.append(mp4[1])

            # 如果音频长度大于视频长度，延长视频长度
            else:
                new_mp3_list.append(mp3[1])
                new_mp4_list.append(mp4[1].set_duration(mp3_duration))

        # 此部分存在视频但没有对应音频,此时mp3是silence
        elif mp3[0] == 0 and mp4[0] == 1:
            mp3_duration = mp3[1].duration_seconds
            mp4_duration = mp4[1].duration
            # 两个片段长度比例不能小于0.98
            assert mp3_duration / mp4_duration > 0.98
            new_mp4_list.append(mp4[1])
            new_mp3_list.append(mp3[1])

    # 合并视频
    final_video = concatenate_videoclips(new_mp4_list)
    # 合并音频
    final_audio = AudioSegment.empty()
    for audio in new_mp3_list:
        final_audio += audio

    if bg_music:
        # 添加背景音乐
        bg_audio = AudioSegment.from_file(
            bg_mp3_path,
            format="mp3",
        )
        bg_audio = truncate_or_repeat_audio(bg_audio, final_video.duration)

        # 合并音频
        final_audio = combine_speech_bg(final_audio, bg_audio)

    # 保存音频为临时文件，使用后删除
    final_audio.export(merge_mp3_single_path, format="mp3")
    print(f"合成mp3完成，路径为：{merge_mp3_single_path}")
    time.sleep(3)

    # 加载合成的mp3，使用moviepy的AudioFileClip
    final_audio = AudioFileClip(merge_mp3_single_path)
    # 将音频添加到视频中
    final_video = final_video.set_audio(final_audio)

    # 保存合并后的文件
    final_video_path = "output_video.mp4"
    final_video.write_videofile(final_video_path, codec="libx264")

    # 使用 ffmpeg 进行 GPU 加速的音视频合成
    input_video = ffmpeg.input(final_video_path)
    input_audio = ffmpeg.input(merge_mp3_single_path)
    # output_file = "output_video_with_gpu.mp4"

    ffmpeg.output(input_video, input_audio, dst_mp4_path, vcodec="h264_nvenc").run()

    # return output_file


def cross_fade(pydub_audio):
    """在音频的开头和结尾添加 cross fade 效果"""
    # 设置 cross fade 时长 (以毫秒为单位)
    fade_duration = 2000  # 1 秒

    # 在开始和结束添加 cross fade 效果
    audio_with_fade = pydub_audio.fade_in(fade_duration).fade_out(fade_duration)
    return audio_with_fade


def truncate_or_repeat_audio(audio, target_time):
    """截断或重复 MP3 文件,以使其达到目标时长"""
    # 读取 MP3 文件
    # audio = AudioSegment.from_file(input_file, format="mp3")

    # 获取 MP3 文件的原始时长
    original_duration = audio.duration_seconds

    # 如果目标时长小于或等于原始时长
    if target_time <= original_duration:
        # 截断 MP3 文件
        audio = audio[: int(target_time * 1000)]  # 单位是毫秒
    else:
        # 重复 MP3 文件
        num_repeats = int(target_time // original_duration)
        remainder = target_time % original_duration
        repeated_audio = audio * num_repeats
        if remainder > 0:
            repeated_audio += audio[: int(remainder * 1000)]
        audio = repeated_audio

    # 添加 cross fade 效果
    audio = cross_fade(audio)

    return audio


def merge_mp4_controller(topic):
    tts_path = f"/Users/donghaoliu/doc/video_material/tts_mp3/{topic}"
    srt_path = f"/Users/donghaoliu/doc/video_material/zh_srt_nowarp/{topic}"
    video_path = f"/Volumes/dhl/ytb-videos/{topic}"

    dst_merged_mp4_path = f"/Volumes/dhl/ytb-videos/tts_mp4/{topic}"
    # 创建目录，如果不存在
    if not os.path.exists(dst_merged_mp4_path):
        os.makedirs(dst_merged_mp4_path)

    # 得到所有的channel
    all_channels = os.listdir(tts_path)
    # remove .DS_Store using list comprehension
    all_channels = [channel for channel in all_channels if channel != ".DS_Store"]

    # 遍历所有的channel
    for channel in all_channels:
        tts_channel_path = os.path.join(tts_path, channel)
        all_tts_done = os.listdir(tts_channel_path)

        # remove .DS_Store using list comprehension
        all_tts_done = [
            tts_done for tts_done in all_tts_done if tts_done != ".DS_Store"
        ]

        # 创建目录，如果不存在
        if not os.path.exists(os.path.join(dst_merged_mp4_path, channel)):
            os.makedirs(os.path.join(dst_merged_mp4_path, channel))

        # 遍历所有的tts_done，每个tts_done对应一个mp4视频，每个tts_done是一个文件夹，内部是mp3的clips
        for tts_done in tqdm(all_tts_done):
            dst_mp4_path = os.path.join(dst_merged_mp4_path, channel, f"{tts_done}.mp4")
            # 如果文件已经存在，则跳过
            if os.path.exists(dst_mp4_path):
                print(f"{dst_mp4_path} 已经存在，跳过...")
                continue
            print(f"处理 {tts_done} ，位于频道 {channel}")
            cur_srt_path = os.path.join(srt_path, channel, f"{tts_done}.srt")
            mp4_path = os.path.join(video_path, channel, f"{tts_done}.mp4")
            tts_mp3_path = os.path.join(tts_channel_path, tts_done)
            mp3 = get_sorted_mp3_list(tts_mp3_path)
            chinese_audio_clips = [
                os.path.join(tts_mp3_path, mp3_file) for mp3_file in mp3
            ]
            final_video = merge_mp3tomp4(cur_srt_path, mp4_path, chinese_audio_clips)
            final_video.write_videofile(dst_mp4_path)


def merge_mp4_controller_single(
    tts_mp3_path,
    mp4_path,
    channel,
    tts_folder_name,
    dst_mp4_path,
    cur_zh_srt_path,
    bg_music=True,
    merge_mp3_single_path=None,
    bg_mp3_path="",
):
    # 初始化 colorama
    init(autoreset=True)
    # get merged mp3 duration
    if os.path.exists(dst_mp4_path) and os.path.exists(merge_mp3_single_path):
        print(f"!@!@!@{dst_mp4_path} 视频已经存在，检查是否需要重复合成...")
        print(Fore.GREEN + f"合成的mp4路径：{dst_mp4_path}")
        print(Fore.GREEN + f"合成的mp3路径：{merge_mp3_single_path}")
        mp3_merged_duraion = get_duration(merge_mp3_single_path)
        pre_done_mp4_duration = get_duration(dst_mp4_path)
        if pre_done_mp4_duration / mp3_merged_duraion > 0.98:
            print(f"!@!@!@{dst_mp4_path} 视频合并完成,不进行重复合成，跳过继续...")
            return

    print(f"处理 {tts_folder_name} ，位于频道 {channel}")

    mp3 = get_sorted_mp3_list(tts_mp3_path)
    chinese_audio_clips = [os.path.join(tts_mp3_path, mp3_file) for mp3_file in mp3]
    final_video = merge_mp3tomp4(
        cur_zh_srt_path,
        mp4_path,
        chinese_audio_clips,
        bg_music,
        merge_mp3_single_path,
        bg_mp3_path=bg_mp3_path,
    )
    os_str = detect_os()
    if os_str == "mac":
        thread_num = 4
    elif os_str == "linux":
        thread_num = 12
    final_video.write_videofile(
        dst_mp4_path, threads=thread_num, codec="libx264", audio_codec="aac"
    )


if __name__ == "__main__":
    topic = "code"
    merge_mp4_controller(topic)
