import os
import tempfile
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


from moviepy.editor import VideoFileClip
from datetime import timedelta


def get_mp4_clip_list(video_path, ts_list, mp3_list):
    """得到mp4和mp3的clips"""
    # 加载视频文件
    video = VideoFileClip(video_path)

    mp4_clip_list = []
    mp3_clip_list = []
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
            # 创建一个silence片段
            silence_duration = (start_time - current_time).total_seconds()
            silence = AudioSegment.silent(duration=int(silence_duration * 1000))
            mp3_clip_list.append([0, silence])

        # 处理字幕时间戳内的片段
        mp4_clip = video.subclip(start_seconds, end_seconds)
        mp4_clip_list.append([1, mp4_clip])
        mp3_clip_list.append([1, mp3_clip])
        current_time = end_time

    # 处理最后一个字幕时间戳之后的片段
    if current_time < timedelta(seconds=video.duration):
        mp4_clip = video.subclip(current_time.total_seconds())
        mp4_clip_list.append([0, mp4_clip])
        # 创建一个silence片段
        silence_duration = video.duration - current_time.total_seconds()
        silence = AudioSegment.silent(duration=int(silence_duration * 1000))
        mp3_clip_list.append([0, silence])

    return mp4_clip_list, mp3_clip_list


def merge_mp3tomp4(srt_file, video_file, chinese_audio_files):
    srt_content = read_srt_file(srt_file)
    ts_list, _ = parse_srt_with_re(srt_content)

    mp4_list, mp3_list = get_mp4_clip_list(video_file, ts_list, chinese_audio_files)
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

    # 保存音频为临时文件，使用后删除
    temp_audio = tempfile.NamedTemporaryFile()
    final_audio.export(temp_audio.name, format="mp3")
    # 从临时文件中加载音频，使用moviepy的AudioFileClip
    final_audio = AudioFileClip(temp_audio.name)
    print(final_audio.duration, final_video.duration)
    # 将音频添加到视频中
    final_video = final_video.set_audio(final_audio)

    return final_video


# 示例用法
tts_mp3_path = f"/Users/donghaoliu/doc/video_material/tts_mp3/code/developedbyed/This React Drag and Drop Component Is Magic"
srt_file = "/Users/donghaoliu/doc/video_material/zh_srt_nowarp/code/developedbyed/This React Drag and Drop Component Is Magic.srt"
video_file = "/Volumes/dhl/ytb-videos/code/developedbyed/This React Drag and Drop Component Is Magic.mp4"
mp3 = get_sorted_mp3_list(tts_mp3_path)

# get mp3 absolute path
chinese_audio_files = [os.path.join(tts_mp3_path, mp3_file) for mp3_file in mp3]
final_video = merge_mp3tomp4(srt_file, video_file, chinese_audio_files)
final_video.write_videofile("./output.mp4")
