import subprocess
import os


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


# 使用示例
input_video = "/Volumes/dhl/ytb-videos/code/patloeber/PyScript is officially here!🚀 Build web apps with Python & HTML.mp4"
subtitles = "/Users/donghaoliu/doc/short_whisper/chinese_srt/PyScript is officially here!🚀 Build web apps with Python & HTML [owopzp436jM].srt 11-16-30-269.srt"
font_file = "/Users/donghaoliu/Downloads/HYYiSongW.ttf"
output_video = "./test.mp4"

# check if input_video, subtitles, font_file seperately exist, find the missing one

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
