# from moviepy.editor import VideoFileClip
# import numpy as np


# def detect_silence(video_path, silence_threshold_factor=0.9, min_silence_duration=1.0):
#     # 加载视频
#     video = VideoFileClip(video_path)
#     audio = video.audio

#     # 确保音频存在
#     if audio is None:
#         raise ValueError("No audio found in the video.")

#     # 获取音频的帧率
#     audio_framerate = audio.fps
#     if audio_framerate is None:
#         raise ValueError("Audio framerate is not available.")

#     # 手动获取音频帧数据
#     frames = []
#     for frame in audio.iter_frames(fps=audio_framerate, dtype="int16"):
#         frames.append(frame)
#     audio_samples = np.vstack(frames).mean(axis=1)

#     # 计算短时能量
#     hop_length = int(audio_framerate * 0.01)  # 10ms
#     frame_length = int(audio_framerate * 0.025)  # 25ms
#     energy = np.array(
#         [
#             np.sum(np.abs(audio_samples[i : i + frame_length] ** 2))
#             for i in range(0, len(audio_samples), hop_length)
#         ]
#     )

#     # 将能量转换为分贝
#     dB = 10 * np.log10(energy + np.finfo(float).eps)

#     # 计算平均分贝值并设置动态阈值
#     average_dB = np.mean(dB)
#     silence_threshold = average_dB * silence_threshold_factor

#     # 检测静音
#     silence = dB < silence_threshold
#     padded_silence = np.pad(silence, 1, mode="constant")
#     changes = np.diff(padded_silence.astype(int))
#     starts = np.where(changes == 1)[0] * hop_length / audio_framerate
#     ends = np.where(changes == -1)[0] * hop_length / audio_framerate

#     # 合并过短的静音间隔
#     min_silence_duration = float(min_silence_duration)
#     segments = []
#     start = 0
#     for end in ends:
#         if end - start >= min_silence_duration:
#             segments.append((start, end))
#             start = end

#     # 分割视频
#     video_segments = []
#     start_idx = 0
#     for start, end in segments:
#         if start > start_idx:
#             clip = video.subclip(start_idx, start)
#             video_segments.append(clip)
#         start_idx = end
#     if start_idx < video.duration:
#         clip = video.subclip(start_idx)
#         video_segments.append(clip)

#     # 保存分割后的视频
#     for i, segment in enumerate(video_segments):
#         segment.write_videofile(f"video_chunk{i}.mp4", codec="libx264")

#     print(f"Generated {len(video_segments)} clips.")


# # 主流程
# video_filename = "/Volumes/dhl/ytb-videos/mp4_zh/code/brocodez/C Programming Full Course for free 🕹️.mp4"
# detect_silence(video_filename)
