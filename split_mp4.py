import os


def split_mp4():
    mp4_folder = "/Volumes/dhl/ytb-videos/mp4_zh"
    topic = "code"
    channels = os.listdir(os.path.join(mp4_folder, topic))
    # remove DS_Store using list comprehension
    channels = [channel for channel in channels if channel != ".DS_Store"]

    for channel in channels:
        all_mp4 = os.listdir(os.path.join(mp4_folder, topic, channel))
        # remove .DS_Store
        all_mp4
