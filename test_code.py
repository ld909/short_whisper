from pydub import AudioSegment


def cross_fade(pydub_audio):
    """在音频的开头和结尾添加 cross fade 效果"""
    # 设置 cross fade 时长 (以毫秒为单位)
    fade_duration = 2000  # 1 秒

    # 在开始和结束添加 cross fade 效果
    audio_with_fade = pydub_audio.fade_in(fade_duration).fade_out(fade_duration)
    return audio_with_fade


def truncate_or_repeat_audio(input_file, target_time):
    """截断或重复 MP3 文件,以使其达到目标时长"""
    # 读取 MP3 文件
    audio = AudioSegment.from_file(input_file, format="mp3")

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

    # 输出新的 MP3 文件
    output_file = "./test_tts_mp3/bg.mp3"
    audio.export(output_file, format="mp3")
    return output_file


def combine_speech_bg(speech, background):

    # 设置背景音乐的音量 (以 dB 为单位)
    background_volume = -15  # 将背景音乐降低 10 dB

    # 合并 speech 和 background
    combined = speech.overlay(background.apply_gain(background_volume))

    # 保存合并后的音频
    combined.export("./test_tts_mp3/combined.mp3", format="mp3")


# 使用示例
# input_file = "/Users/donghaoliu/doc/video_material/tts_mp3/background/bg.mp3"
# target_time = 14  # 目标时长为 120 秒
# output_file = truncate_or_repeat_audio(input_file, target_time)
# print(f"Output file: {output_file}")

# 加载 speech 和 background 音乐
speech = AudioSegment.from_file("./test_tts_mp3/output.mp3", format="mp3")
background = AudioSegment.from_file("./test_tts_mp3/bg.mp3", format="mp3")
combine_speech_bg(speech, background)
