# 这个是运行在在linux上whisper识别srt之后，主要的逻辑都在这里
import os
from translate_srt import controller_translate_srt_single, get_duration
from tts_zh_mp3 import controller_tts_single
from merge_tts_mp3 import merge_mp4_controller_single
from get_zh_title import zh_title_tags_controller_single


def controller_after_whisper(topic):

    # 识别后的srt文件路径, 调用的起始依赖
    format_srt = f"/Users/donghaoliu/doc/video_material/zh_srt_nowarp/{topic}"
    tts_mp3_path = f"/Users/donghaoliu/doc/video_material/tts_mp3/{topic}"
    mp4_abs_path = f"/Volumes/dhl/ytb-videos/{topic}"
    jump30 = True

    # 目标文件路径
    dst_zh_srt_abs_path = f"/Users/donghaoliu/doc/video_material/zh_srt_nowarp/{topic}"
    dst_merged_mp4_path = f"/Volumes/dhl/ytb-videos/tts_mp4/{topic}"
    zh_title_dst_path = "/Users/donghaoliu/doc/video_material/zh_title"
    zh_tag_dst_path = "/Users/donghaoliu/doc/video_material/zh_tag"

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

        ### 要除开掉warp=True已经翻译的字幕，也就是已经发布的纯英文mp4对应的中文srt
        # 得到已经完成翻译的字幕列表
        formatted_srts_warp = os.listdir(
            os.path.join(
                f"/Users/donghaoliu/doc/video_material/zh_srt/{topic}",
                channel,
            )
        )
        # remove .DS_Store using list comprehension
        formatted_srts_warp = [srt for srt in formatted_srts_warp if srt != ".DS_Store"]
        # 除去已经翻译的字幕
        formatted_srts = list(set(formatted_srts) - set(formatted_srts_warp))
        print(
            f"移除前：{len(formatted_srts) + len(formatted_srts_warp)}个，移除后：{len(formatted_srts)}个"
        )
        ### 以上代码是为了除去已经翻译的字幕

        ### 创建相关channel文件夹，如果不存在的话
        # 检查目标翻译srt folder是否存在，不存在就创建
        if not os.path.exists(os.path.join(dst_zh_srt_abs_path, channel)):
            os.makedirs(os.path.join(dst_zh_srt_abs_path, channel))

        # 创建目标tts mp3文件夹
        if not os.path.exists(os.path.join(tts_mp3_path, channel)):
            os.makedirs(os.path.join(tts_mp3_path, channel))

        # 创建mp4合并mp3的mp4存放目录，如果不存在
        if not os.path.exists(dst_merged_mp4_path):
            os.makedirs(dst_merged_mp4_path)

        # 创建中文tag和title的文件夹
        if not os.path.exists(os.path.join(zh_title_dst_path, topic, channel)):
            os.makedirs(os.path.join(zh_title_dst_path, topic, channel))
        if not os.path.exists(os.path.join(zh_tag_dst_path, topic, channel)):
            os.makedirs(os.path.join(zh_tag_dst_path, topic, channel))
        ### 完成创建

        # 遍历所有的srt文件
        for srt in formatted_srts:

            # 检查之前是否完成过此任务，完成就跳过
            if os.path.exists(os.path.join(dst_zh_srt_abs_path, channel, srt)):
                print(f"{srt} 文件存在, 跳过继续...")
                continue

            # 超过30min的视频，跳过
            if jump30:
                # 读取mp4视视频，得到duration
                mp4_file = os.path.join(
                    mp4_abs_path, channel, srt.replace(".srt", ".mp4")
                )
                mp4_duration = get_duration(mp4_file)
                if mp4_duration > 1800:
                    print(f"频道{channel}的{srt} 超过30min，跳过...")
                    continue

            ###### step1： 翻译srt文件 ######
            print(f"正在翻译频道{channel}的{srt}...")
            controller_translate_srt_single(
                os.path.join(format_srt, channel, srt),
                os.path.join(dst_zh_srt_abs_path, channel, srt),
            )

            ###### step2： tts合成语音 ######
            print(f"正在tts合成，频道{channel}的{srt}...")
            controller_tts_single(
                os.path.join(dst_zh_srt_abs_path, channel, srt), tts_mp3_path, channel
            )

            ###### step3： 合并mp3和mp4 ######
            tts_folder_name = srt.replace(".srt", "")
            tts_mp3_path = os.path.join(tts_mp3_path, channel, tts_folder_name)
            mp4_abs_path = os.path.join(mp4_abs_path, channel, f"{tts_folder_name}.mp4")
            dst_mp4_path = os.path.join(
                dst_merged_mp4_path, channel, f"{tts_folder_name}.mp4"
            )
            cur_zh_srt_path = os.path.join(dst_zh_srt_abs_path, channel, srt)

            merge_mp4_controller_single(
                tts_mp3_path=tts_mp3_path,
                mp4_path=mp4_abs_path,
                channel=channel,
                tts_folder_name=tts_folder_name,
                dst_mp4_path=dst_mp4_path,
                cur_zh_srt_path=cur_zh_srt_path,
            )

            ###### step4: get chinese tag and titles ######
            title_dst_path = os.path.join(
                zh_title_dst_path, topic, channel, tts_folder_name + ".txt"
            )
            tag_dst_path = os.path.join(
                zh_tag_dst_path, topic, channel, tts_folder_name + ".txt"
            )
            zh_title_tags_controller_single(
                srt_file_name=srt,
                zh_title_dst_path=title_dst_path,
                zh_tag_dst_path=tag_dst_path,
            )

            ###### step5: 创建封面 ######
