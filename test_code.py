from pydub import AudioSegment


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

    # 输出新的 MP3 文件
    output_file = "./output.mp3"
    audio.export(output_file, format="mp3")
    return output_file


# 使用示例
input_file = "input.mp3"
target_time = 120  # 目标时长为 120 秒
output_file = truncate_or_repeat_audio(input_file, target_time)
print(f"Output file: {output_file}")
