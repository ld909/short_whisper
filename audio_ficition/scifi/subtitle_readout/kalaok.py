import srt
from datetime import timedelta


def srt_time_to_ass_time(td):
    """Converts timedelta to ASS time format H:MM:SS.cc"""
    total_seconds = td.total_seconds()
    hours = int(total_seconds / 3600)
    minutes = int((total_seconds % 3600) / 60)
    seconds = int(total_seconds % 60)
    centiseconds = int((total_seconds - int(total_seconds)) * 100)
    return f"{hours}:{minutes:02}:{seconds:02}.{centiseconds:02}"


def create_ass_file(
    segment_srt_path, word_srt_path, ass_output_path, video_res_x=1920, video_res_y=1080
):
    """
    Generates an ASS file with word-level karaoke highlighting.

    Args:
        segment_srt_path (str): Path to the segment-level SRT file.
        word_srt_path (str): Path to the word-level SRT file.
        ass_output_path (str): Path to save the generated ASS file.
        video_res_x (int): Video width for PlayResX in ASS header.
        video_res_y (int): Video height for PlayResY in ASS header.
    """
    try:
        with open(segment_srt_path, "r", encoding="utf-8") as f:
            segment_subs_gen = srt.parse(f.read())
        segment_subs = list(segment_subs_gen)

        with open(word_srt_path, "r", encoding="utf-8") as f:
            word_subs_gen = srt.parse(f.read())
        word_subs = list(word_subs_gen)
    except Exception as e:
        print(f"Error reading SRT files: {e}")
        return

    ass_header = f"""[Script Info]
Title: Karaoke Subtitles
ScriptType: v4.00+
PlayResX: {video_res_x}
PlayResY: {video_res_y}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,50,&H00505050,&H000000FF,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,30,1
; PrimaryColour: &HBBGGRR (505050 = Dark Gray for unsung text - 未唱的文字)
; SecondaryColour: &HBBGGRR (0000FF = Red for currently singing - 正在唱的文字)
; OutlineColour: &H00FFFFFF (White for sung text - 已唱过的文字)
; BackColour: &H00000000 (Black background)
; \kf效果：未唱的显示为PrimaryColour(深灰)，正在唱的显示为SecondaryColour(红色)，已唱过的显示为OutlineColour(白色)

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    ass_dialogues = []

    word_idx = 0
    for seg_sub in segment_subs:
        seg_start_time = seg_sub.start
        seg_end_time = seg_sub.end

        current_segment_text_parts = []

        # Find words belonging to this segment
        words_in_segment = []
        temp_word_idx = word_idx
        while temp_word_idx < len(word_subs):
            word_sub = word_subs[temp_word_idx]
            # Check if the word starts within the segment duration, or slightly before but ends within.
            # A common heuristic is if the word's midpoint is within the segment.
            # Or, more simply, if word start is within segment.
            if word_sub.start >= seg_start_time and word_sub.start < seg_end_time:
                words_in_segment.append(word_sub)
                temp_word_idx += 1
            elif word_sub.start >= seg_end_time:  # Words are sorted, so we can break
                break
            else:  # Word starts before this segment, but might be part of it if word SRT isn't perfectly aligned
                # For simplicity, we advance if it clearly belongs to a past segment
                # A more robust method would be to check word_sub.end vs seg_start_time
                if word_sub.end < seg_start_time:
                    word_idx += 1  # Move global word_idx forward
                temp_word_idx += 1

        if not words_in_segment:
            # If no words found for this segment (e.g. silence segment in word SRT),
            # just display the segment text normally or skip.
            # For now, let's create a simple non-karaoke line if segment text exists
            if seg_sub.content.strip():
                ass_line_text = seg_sub.content.replace(
                    "\n", "\\N"
                )  # ASS uses \N for newlines
                dialogue = f"Dialogue: 0,{srt_time_to_ass_time(seg_start_time)},{srt_time_to_ass_time(seg_end_time)},Default,,0,0,0,,{ass_line_text}"
                ass_dialogues.append(dialogue)
            continue

        # Update the main word_idx to the start of the words processed for next segment
        if words_in_segment:
            # Find the index of the last processed word in the global word_subs list
            last_processed_word_original_index = word_subs.index(words_in_segment[-1])
            word_idx = last_processed_word_original_index + 1

        # Construct karaoke text for the segment
        karaoke_text_for_segment = ""

        # Build karaoke text with proper word-by-word highlighting
        for i, word_s in enumerate(words_in_segment):
            word_text = word_s.content.replace("\n", "")  # Remove newlines

            # Duration of this word's highlight
            word_duration_td = word_s.end - word_s.start
            # Handle cases where duration might be zero or negative if SRT is malformed
            if word_duration_td.total_seconds() <= 0:
                word_duration_cs = 1  # Minimum 1cs
            else:
                word_duration_cs = int(word_duration_td.total_seconds() * 100)

            # Add karaoke tag with word text - using \kf for fill effect
            # \kf效果配合OutlineColour设置：
            # - 未唱的文字：深灰色 (PrimaryColour)
            # - 正在唱的文字：红色 (SecondaryColour)
            # - 已唱过的文字：白色 (OutlineColour)
            karaoke_text_for_segment += f"{{\\kf{word_duration_cs}}}{word_text}"

            # For Chinese text, typically no spaces between words
            # For English or mixed content, you might want to add spaces
            # if i < len(words_in_segment) - 1:
            #     karaoke_text_for_segment += " "

        # The entire segment (with karaoke tags) will be displayed for the segment's duration
        dialogue = f"Dialogue: 0,{srt_time_to_ass_time(seg_start_time)},{srt_time_to_ass_time(seg_end_time)},Default,,0,0,0,,{karaoke_text_for_segment.strip()}"
        ass_dialogues.append(dialogue)

    with open(ass_output_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        for line in ass_dialogues:
            f.write(line + "\n")
    print(f"ASS file generated: {ass_output_path}")


def create_karaoke_from_real_files(
    segment_srt_path,
    word_srt_path,
    output_ass_path,
    video_width=1920,
    video_height=1080,
):
    """
    为真实的SRT文件创建卡拉OK字幕的便利函数

    Args:
        segment_srt_path (str): 段落级SRT文件路径
        word_srt_path (str): 词级SRT文件路径
        output_ass_path (str): 输出ASS文件路径
        video_width (int): 视频宽度，默认1920
        video_height (int): 视频高度，默认1080

    示例使用:
        create_karaoke_from_real_files(
            "my_segment.srt",
            "my_word.srt",
            "my_karaoke.ass"
        )

        然后用ffmpeg合成:
        ffmpeg -i input.mp4 -vf "ass=my_karaoke.ass" -c:a copy output_with_karaoke.mp4
    """
    create_ass_file(
        segment_srt_path, word_srt_path, output_ass_path, video_width, video_height
    )
    print(f"✅ 卡拉OK字幕文件已生成: {output_ass_path}")
    print(f"💡 使用以下命令合成视频:")
    print(
        f'   ffmpeg -i your_video.mp4 -vf "ass={output_ass_path}" -c:a copy output_with_karaoke.mp4'
    )


if __name__ == "__main__":
    # 如果你有真实的SRT文件，直接调用:
    # create_karaoke_from_real_files("your_segment.srt", "your_word.srt", "your_karaoke.ass")

    # 以下是测试代码，生成示例文件进行测试
    # --- CONFIGURATION ---
    segment_srt = "segment_level.srt"  # 输入你的片段级SRT文件路径
    word_srt = "word_level.srt"  # 输入你的词级SRT文件路径
    output_ass = "karaoke_subs.ass"  # 输出的ASS文件名

    # 可选: 视频分辨率，用于ASS头的PlayResX, PlayResY。FFmpeg的ass滤镜通常会自动缩放，但指定它可以更精确。
    # 你可以通过 ffprobe input.mp4 查看视频分辨率
    video_width = 1920
    video_height = 1080
    # --- END CONFIGURATION ---

    # Example: Create dummy SRT files for testing
    # Remove this section if you have your actual SRT files
    with open(segment_srt, "w", encoding="utf-8") as f:
        f.write(
            """1
00:00:01,000 --> 00:00:05,000
这是一句测试字幕，包含多个词语。

2
00:00:06,000 --> 00:00:09,000
第二句字幕在这里。
"""
        )
    with open(word_srt, "w", encoding="utf-8") as f:
        f.write(
            """1
00:00:01,000 --> 00:00:01,500
这是

2
00:00:01,500 --> 00:00:02,000
一句

3
00:00:02,000 --> 00:00:02,800
测试

4
00:00:02,800 --> 00:00:03,500
字幕，

5
00:00:03,500 --> 00:00:04,000
包含

6
00:00:04,000 --> 00:00:04,500
多个

7
00:00:04,500 --> 00:00:05,000
词语。

8
00:00:06,000 --> 00:00:06,800
第二句

9
00:00:06,800 --> 00:00:07,500
字幕

10
00:00:07,500 --> 00:00:08,000
在

11
00:00:08,000 --> 00:00:08,800
这里。
"""
        )  # Note: No trailing period to match segment for simplicity here

    create_ass_file(segment_srt, word_srt, output_ass, video_width, video_height)
