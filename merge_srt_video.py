import subprocess


def run_ffmpeg_command(input_video, subtitles, font_file, output_video):
    ffmpeg_command = [
        "ffmpeg",
        "-i",
        input_video,
        "-vf",
        f"subtitles={subtitles}:force_style='FontName=MyCustomFont,FontFile={font_file},FontSize=24,PrimaryColour=&H00FFFFFF&'",
        "-c:a",
        "copy",
        output_video,
    ]

    subprocess.run(ffmpeg_command, check=True)


# 使用示例
input_video = "input_video.mp4"
subtitles = "subtitles.srt"
font_file = "/path/to/font/file.ttf"
output_video = "output_video.mp4"

run_ffmpeg_command(input_video, subtitles, font_file, output_video)
