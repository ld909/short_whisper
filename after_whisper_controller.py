##### 这个是运行在在linux上whisper识别srt之后
##### 主要的逻辑都在这里
import os
from sys import argv
from translate_srt import controller_translate_srt_single, get_duration
from tts_zh_mp3 import controller_tts_single
from merge_tts_mp3 import merge_mp4_controller_single
from get_zh_title import zh_title_tags_controller_single
from create_thumbnail import create_zh_title_thumbnail_vertical_single
from tqdm import tqdm


def load_bad_json(data):
    """载入bad.json文件，返回字典"""
    import json

    # 载入bad.json文件
    with open("./upload_log/bad.json", "r") as file:
        data = json.load(file)
    return data


def set_clash_proxy():

    # 设置环境变量
    os.environ["http_proxy"] = "http://127.0.0.1:7890"
    os.environ["https_proxy"] = "http://127.0.0.1:7890"
    os.environ["all_proxy"] = "socks5://127.0.0.1:7891"
    print("成功设定clash环境proxy...")


def retain_pipe_status(
    channel,
    all_format_srts,
    dst_zh_srt_abs_path,
    mp3_merge_path,
    dst_merged_mp4_path,
    zh_title_dst_path,
    zh_tag_dst_path,
    dst_vertical_thumbnail_path,
    eng_mp4_abs_path,
    jump30,
):
    """恢复pipe的状态，如果已经完成，就设定为True，否则继续执行"""
    lookup_dict = {}
    done_srts = os.listdir(os.path.join(dst_zh_srt_abs_path, channel))
    done_srts = [srt for srt in done_srts if srt != ".DS_Store"]
    done_srts = [srt.replace(".srt", "") for srt in done_srts]

    done_merge_mp3 = os.listdir(os.path.join(mp3_merge_path, channel))
    done_merge_mp3 = [mp3 for mp3 in done_merge_mp3 if mp3 != ".DS_Store"]
    done_merge_mp3 = [mp3.replace(".mp3", "") for mp3 in done_merge_mp3]

    done_mp4_path = os.listdir(os.path.join(dst_merged_mp4_path, channel))
    done_mp4_path = [mp4 for mp4 in done_mp4_path if mp4 != ".DS_Store"]
    done_mp4_path = [mp4.replace(".mp4", "") for mp4 in done_mp4_path]

    done_zh_title = os.listdir(os.path.join(zh_title_dst_path, channel))
    done_zh_title = [title for title in done_zh_title if title != ".DS_Store"]
    done_zh_title = [title.replace(".txt", "") for title in done_zh_title]

    done_zh_tag = os.listdir(os.path.join(zh_tag_dst_path, channel))
    done_zh_tag = [tag for tag in done_zh_tag if tag != ".DS_Store"]
    done_zh_tag = [tag.replace(".txt", "") for tag in done_zh_tag]

    done_thumbnail = os.listdir(os.path.join(dst_vertical_thumbnail_path, channel))
    done_thumbnail = [
        thumbnail for thumbnail in done_thumbnail if thumbnail != ".DS_Store"
    ]
    done_thumbnail = [thumbnail.replace(".png", "") for thumbnail in done_thumbnail]

    print(f"正在生成lookup_dict...")
    for srt in tqdm(all_format_srts):
        srt_basename = srt.replace(".srt", "")
        lookup_dict[srt_basename] = {}
        if srt_basename in done_srts:
            lookup_dict[srt_basename]["srt"] = True
        else:
            lookup_dict[srt_basename]["srt"] = False
        if srt_basename in done_merge_mp3:
            lookup_dict[srt_basename]["merge_mp3"] = True
        else:
            lookup_dict[srt_basename]["merge_mp3"] = False
        if srt_basename in done_mp4_path:
            lookup_dict[srt_basename]["mp4"] = True
        else:
            lookup_dict[srt_basename]["mp4"] = False
        # if srt_basename in done_zh_title:
        #     lookup_dict[srt_basename]["zh_title"] = True
        # else:
        #     lookup_dict[srt_basename]["zh_title"] = False
        # if srt_basename in done_zh_tag:
        #     lookup_dict[srt_basename]["zh_tag"] = True
        # else:
        #     lookup_dict[srt_basename]["zh_tag"] = False
        if srt_basename in done_zh_title and srt_basename in done_zh_tag:
            lookup_dict[srt_basename]["zh_title_tag"] = True
        else:
            lookup_dict[srt_basename]["zh_title_tag"] = False

        if srt_basename in done_thumbnail:
            lookup_dict[srt_basename]["thumbnail"] = True
        else:
            lookup_dict[srt_basename]["thumbnail"] = False

        if jump30:
            mp4_file = os.path.join(eng_mp4_abs_path, channel, srt_basename + ".mp4")
            mp4_duration = get_duration(mp4_file)
            # 超过30min的视频，跳过
            if mp4_duration > 1800:
                lookup_dict[srt_basename]["jump30"] = True
            else:
                lookup_dict[srt_basename]["jump30"] = False
    print(f"生成lookup_dict完成！")
    return lookup_dict


def controller_after_whisper(topic):

    # 设定clash环境
    set_clash_proxy()

    hard_dive_path = "/media/dhl/TOSHIBA"
    # whisper识别后的srt文件路径, 调用的起始依赖
    format_srt_path = f"{hard_dive_path}/video_material/format_srt/{topic}"
    tts_mp3_path = f"{hard_dive_path}/video_material/tts_mp3/{topic}"
    eng_mp4_abs_path = f"{hard_dive_path}/ytb-videos/{topic}"
    mp3_merge_path = f"{hard_dive_path}/ytb-videos/merge_mp3/{topic}"
    jump30 = True

    # 目标文件路径
    dst_zh_srt_abs_path = f"{hard_dive_path}/video_material/zh_srt_nowarp/{topic}"
    dst_merged_mp4_path = f"{hard_dive_path}/ytb-videos/tts_mp4/{topic}"
    zh_title_dst_path = f"{hard_dive_path}/video_material/zh_title/{topic}"
    zh_tag_dst_path = f"{hard_dive_path}/video_material/zh_tag/{topic}"
    dst_vertical_thumbnail_path = (
        f"{hard_dive_path}/video_material/thumbnail_vertical/{topic}"
    )
    vertical_thumbnail_font_path = (
        f"{hard_dive_path}/video_material/font/DottedSongtiCircleRegular.otf"
    )

    # 所有频道，依赖fomat_srt文件夹
    all_channels = os.listdir(format_srt_path)
    #  .DS_Store using list comprehension
    all_channels = [channel for channel in all_channels if channel != ".DS_Store"]

    data = load_bad_json("./upload_log/bad.json")

    # 遍历所有频道
    for channel in all_channels:
        ###### step1： 翻译srt文件 ######
        print(f"当前处理的频道是{channel}...")
        all_eng_srt = os.listdir(os.path.join(format_srt_path, channel))
        # 删掉.DS_Store
        all_eng_srt = [srt for srt in all_eng_srt if srt != ".DS_Store"]

        ### warp=True已经翻译的字幕，也就是已经发布的纯英文mp4对应的中文srt
        zh_srts_warp = os.listdir(
            os.path.join(
                f"{hard_dive_path}/video_material/zh_srt/{topic}",
                channel,
            )
        )
        zh_srts_warp_done = [srt for srt in zh_srts_warp if srt != ".DS_Store"]

        # 得到whisper识别后的英文srt文件列表
        formatted_srts_all = os.listdir(os.path.join(format_srt_path, channel))
        formatted_srts_all = [srt for srt in formatted_srts_all if srt != ".DS_Store"]

        # 除去已经翻译的字幕
        formatted_srts = list(set(formatted_srts_all) - set(zh_srts_warp_done))
        print(f"移除前：{len(formatted_srts_all)}个，移除后：{len(formatted_srts)}个")

        # sort formatted_srts
        formatted_srts.sort()
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

        # 合成mp3保存的文件夹
        if not os.path.exists(os.path.join(mp3_merge_path, channel)):
            os.makedirs(os.path.join(mp3_merge_path, channel))

        # 创建中文tag和title的文件夹
        if not os.path.exists(os.path.join(zh_title_dst_path, channel)):
            os.makedirs(os.path.join(zh_title_dst_path, channel))
        if not os.path.exists(os.path.join(zh_tag_dst_path, channel)):
            os.makedirs(os.path.join(zh_tag_dst_path, channel))

        # 创建封面的文件夹
        if not os.path.exists(os.path.join(dst_vertical_thumbnail_path, channel)):
            os.makedirs(os.path.join(dst_vertical_thumbnail_path, channel))
        ### 完成创建

        lookup_dict = retain_pipe_status(
            channel,
            formatted_srts,
            dst_zh_srt_abs_path,
            mp3_merge_path,
            dst_merged_mp4_path,
            zh_title_dst_path,
            zh_tag_dst_path,
            dst_vertical_thumbnail_path,
            eng_mp4_abs_path,
            jump30,
        )

        # 遍历所有的srt文件
        for srt in tqdm(formatted_srts):
            srt_basename = srt.replace(".srt", "")
            # 超过30min的视频，跳过
            if jump30:
                if lookup_dict[srt_basename]["jump30"]:
                    print(f"频道{channel}的{srt} 超过30min，跳过...")
                    continue
            ###### step0: 读取bad.json文件，如果存在，跳过 ######
            if topic in data:
                if channel in data[topic]:
                    # 得到无后缀的srt文件名
                    if srt_basename in data[topic][channel]:
                        print(f"话题{topic},频道{channel}的{srt}在bad.json中，跳过...")
                        continue

            ###### step1： 翻译srt文件 ######
            if not lookup_dict[srt_basename]["srt"]:
                print(f"正在翻译频道{channel}的{srt}...")
                controller_translate_srt_single(
                    os.path.join(format_srt_path, channel, srt),
                    os.path.join(dst_zh_srt_abs_path, channel, srt),
                    topic=topic,
                )
                print(f"翻译{channel}的{srt}完成！")
                print("#" * 20)

            ###### step2： tts合成语音 ######
            tts_folder_name = srt.replace(".srt", "")
            tts_mp3_path_single = os.path.join(tts_mp3_path, channel, tts_folder_name)
            mp4_abs_single_path = os.path.join(
                eng_mp4_abs_path, channel, f"{tts_folder_name}.mp4"
            )
            dst_mp4_path = os.path.join(
                dst_merged_mp4_path, channel, f"{tts_folder_name}.mp4"
            )

            merge_mp3_single_path = os.path.join(
                mp3_merge_path, channel, f"{tts_folder_name}.mp3"
            )
            if not lookup_dict[srt_basename]["merge_mp3"]:
                print(f"正在合并mp3和mp4，频道{channel}的{srt}...")
                controller_tts_single(
                    os.path.join(dst_zh_srt_abs_path, channel, srt),
                    tts_mp3_path,
                    channel,
                    topic,
                    merge_single_mp3_path=merge_mp3_single_path,
                )
                print(f"tts合成{channel}的{srt}完成！")
                print("#" * 20)

            ###### step3： 合并mp3和mp4 ######
            cur_zh_srt_path = os.path.join(dst_zh_srt_abs_path, channel, srt)
            if not lookup_dict[srt_basename]["mp4"]:
                merge_mp4_controller_single(
                    tts_mp3_path=tts_mp3_path_single,
                    mp4_path=mp4_abs_single_path,
                    channel=channel,
                    tts_folder_name=tts_folder_name,
                    dst_mp4_path=dst_mp4_path,
                    cur_zh_srt_path=cur_zh_srt_path,
                    merge_mp3_single_path=merge_mp3_single_path,
                )
                print(f"合并mp3和mp4{channel}的{srt}完成！")
                print("#" * 20)

            ###### step4: 得到中文标题和tags ######

            title_dst_path = os.path.join(
                zh_title_dst_path, channel, tts_folder_name + ".txt"
            )
            tag_dst_path = os.path.join(
                zh_tag_dst_path, channel, tts_folder_name + ".txt"
            )

            # 如果没有中文标题和tags，就生成
            if not lookup_dict[srt_basename]["zh_title_tag"]:
                print(f"正在得到中文标题和tags，频道{channel}的{srt}...")
                zh_title_tags_controller_single(
                    srt_file_name=srt,
                    zh_title_dst_path=title_dst_path,
                    zh_tag_dst_path=tag_dst_path,
                    topic=topic,
                )
                print(f"中文标题和tags{channel}的{srt}完成！")
                print("#" * 20)

            ###### step5: 创建封面 ######
            vertical_thumbnail_dst_path = os.path.join(
                dst_vertical_thumbnail_path, channel, tts_folder_name + ".png"
            )
            zh_title_single_path = os.path.join(
                zh_title_dst_path, channel, tts_folder_name + ".txt"
            )
            if not lookup_dict[srt_basename]["thumbnail"]:
                print(f"正在创建封面，频道{channel}的{srt}...")
                create_zh_title_thumbnail_vertical_single(
                    dst_thumbnail_path=vertical_thumbnail_dst_path,
                    zh_title_path=zh_title_single_path,
                    vertical_font_path=vertical_thumbnail_font_path,
                )
                print(f"封面{channel}的{srt}完成！")
                print("#" * 20)


if __name__ == "__main__":
    # 从命令行第一个参数得到topic
    topic = argv[1]
    controller_after_whisper(topic)
