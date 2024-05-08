# 这个是运行在在linux上whisper识别srt之后，主要的逻辑都在这里
import os
from translate_srt import controller_srt



def controller_after_whisper(topic):

    # 识别后的srt文件路径, 调用的起始依赖
    format_srt = f"/Users/donghaoliu/doc/video_material/zh_srt_nowarp/{topic}"

    # 所有频道，依赖fomat_srt文件夹
    all_channels = os.listdir(format_srt)
    #  .DS_Store using list comprehension
    all_channels = [channel for channel in all_channels if channel != ".DS_Store"]

    # 遍历所有频道
    for channel in all_channels:
        ###### step1： 翻译srt文件 ######
        print(f"当前处理的频道是{channel}...")
        all_eng_srt = os.listdir(os.path.join(format_srt, channel))
        # 删掉.DS_Store
        all_eng_srt = [srt for srt in all_eng_srt if srt != ".DS_Store"]
        
        for eng_srt in all_eng_srt:
            # eng_srt_path
