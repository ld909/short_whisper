import os
from merge_srt_video import get_duration


def split_mp4():
    mp4_folder = "/Volumes/dhl/ytb-videos/mp4_zh"
    topic = "code"
    channels = os.listdir(os.path.join(mp4_folder, topic))
    # remove DS_Store using list comprehension
    channels = [channel for channel in channels if channel != ".DS_Store"]

    for channel in channels:
        all_mp4 = os.listdir(os.path.join(mp4_folder, topic, channel))
        # remove .DS_Store
        all_mp4 = [mp4 for mp4 in all_mp4 if mp4 != ".DS_Store"]
        for mp4_single in all_mp4:
            # get the duration of the mp4 file
            mp4_path = os.path.join(mp4_folder, topic, channel, mp4_single)
            duration = get_duration(mp4_path)

            # if duration is less than 30mins, skip
            if duration < 1800:
                continue

            # compute the number of clips
            num_clips = (duration // 1500) + 1

            # split the mp4 file, each clip is 25mins
