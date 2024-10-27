##### 这个是运行在在linux上whisper识别srt之后
##### 主要的逻辑都在这里
import os
from sys import argv
from translate_srt import controller_translate_srt_single, get_duration
from tts_zh_mp3 import controller_tts_single
from merge_tts_mp3 import merge_mp4_controller_single
from get_zh_title import zh_title_tags_controller_single
from create_thumbnail import (
    create_zh_title_thumbnail_vertical_single,
    create_zh_title_thumbnail_horizontal_single,
)
from tqdm import tqdm
import sys
import time
from moviepy.editor import VideoFileClip
import platform


def delete_zero_size_mp3s(directory, extension=".mp3"):
    """
    删除指定目录及其子目录下所有大小为0的指定扩展名文件。

    :param directory: 目标目录路径
    :param extension: 指定文件的扩展名，默认为 .mp3
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(extension):
                file_path = os.path.join(root, file)
                if os.path.getsize(file_path) == 0:
                    print(f"Deleting {file_path} ...")
                    os.remove(file_path)


def delete_all_trash_files():
    """删除hard drive下的所有._开头的文件"""
    print("正在删除hard drive下的所有._开头的文件...")
    cur_os = detect_os()
    if cur_os == "mac":
        hard_dive_path = "/Volumes/TOSHIBA"
    else:
        hard_dive_path = "/media/dhl/TOSHIBA"

    # 删除hard drive下的所有._开头的文件
    for root, dirs, files in os.walk(hard_dive_path):
        for file in files:
            if file.startswith("._"):
                os.remove(os.path.join(root, file))
                print(f"删除{file}成功！")

    if cur_os == "mac":
        # 删除hard drive下的所有.DS_Store文件
        for root, dirs, files in os.walk(hard_dive_path):
            for file in files:
                if file == ".DS_Store":
                    os.remove(os.path.join(root, file))
                    print(f"删除{file}成功！")
    print("删除hard drive下的所有._开头的文件完成！")


def load_bad_json():
    """载入bad.json文件，返回字典"""
    import json

    # 载入bad.json文件
    with open("./upload_log/bad.json", "r") as file:
        data = json.load(file)
    return data


def set_clash_proxy():

    # 设置环境变量
    os.environ["http_proxy"] = "http://127.0.0.1:7897"
    os.environ["https_proxy"] = "http://127.0.0.1:7897"
    # os.environ["all_proxy"] = "socks5://127.0.0.1:7891"
    print("成功设定clash环境proxy...")


def unset_clash_proxy():
    # 删除环境变量
    os.environ.pop("http_proxy", None)
    os.environ.pop("https_proxy", None)
    # os.environ.pop("all_proxy", None)
    print("成功取消clash环境proxy...")


def retain_pipe_status(
    channel,
    all_format_srts,
    dst_zh_srt_abs_path,
    mp3_merge_path,
    dst_merged_mp4_path,
    zh_title_dst_path,
    zh_tag_dst_path,
    dst_vertical_thumbnail_path,
    dst_horizontal_thumbnail_path,
    eng_mp4_abs_path,
    jump60,
):
    """恢复pipe的状态，如果已经完成，就设定为True，否则继续执行"""
    lookup_dict = {}
    done_srt_path = os.path.join(dst_zh_srt_abs_path, channel)
    if os.path.exists(done_srt_path):
        done_srts = os.listdir(done_srt_path)
        done_srts = [srt for srt in done_srts if srt != ".DS_Store"]
        done_srts = [srt for srt in done_srts if not srt.startswith("._")]
        done_srts = [srt.replace(".srt", "") for srt in done_srts]
    else:
        done_srts = []

    done_merge_mp3_path = os.path.join(mp3_merge_path, channel)
    if os.path.exists(done_merge_mp3_path):
        done_merge_mp3 = os.listdir(done_merge_mp3_path)
        done_merge_mp3 = [mp3 for mp3 in done_merge_mp3 if mp3 != ".DS_Store"]
        done_merge_mp3 = [mp3 for mp3 in done_merge_mp3 if not mp3.startswith("._")]
        done_merge_mp3 = [mp3.replace(".mp3", "") for mp3 in done_merge_mp3]
    else:
        done_merge_mp3 = []

    done_mp4_path = os.path.join(dst_merged_mp4_path, channel)
    if os.path.exists(done_mp4_path):
        done_mp4_path = os.listdir(done_mp4_path)
        done_mp4_path = [mp4 for mp4 in done_mp4_path if mp4 != ".DS_Store"]
        done_mp4_path = [mp4 for mp4 in done_mp4_path if not mp4.startswith("._")]
        done_mp4_path = [mp4.replace(".mp4", "") for mp4 in done_mp4_path]
    else:
        done_mp4_path = []

    done_zh_title_path = os.path.join(zh_title_dst_path, channel)
    if os.path.exists(done_zh_title_path):
        done_zh_title = os.listdir(done_zh_title_path)
        done_zh_title = [title for title in done_zh_title if title != ".DS_Store"]
        done_zh_title = [title for title in done_zh_title if not title.startswith("._")]
        done_zh_title = [title.replace(".txt", "") for title in done_zh_title]
    else:
        done_zh_title = []

    done_zh_tag_path = os.path.join(zh_tag_dst_path, channel)
    if os.path.exists(done_zh_tag_path):
        done_zh_tag = os.listdir(done_zh_tag_path)
        done_zh_tag = [tag for tag in done_zh_tag if tag != ".DS_Store"]
        done_zh_tag = [tag for tag in done_zh_tag if not tag.startswith("._")]
        done_zh_tag = [tag.replace(".txt", "") for tag in done_zh_tag]
    else:
        done_zh_tag = []

    done_thumbnail_vertical_path = os.path.join(dst_vertical_thumbnail_path, channel)
    if os.path.exists(done_thumbnail_vertical_path):
        done_thumbnail_vertical = os.listdir(done_thumbnail_vertical_path)
    else:
        done_thumbnail_vertical = []

    done_thumbnail_horizontal_path = os.path.join(
        dst_horizontal_thumbnail_path, channel
    )
    if os.path.exists(done_thumbnail_horizontal_path):
        done_thumbnail_horizontal = os.listdir(done_thumbnail_horizontal_path)
    else:
        done_thumbnail_horizontal = []

    done_thumbnail_vertical = [
        thumbnail for thumbnail in done_thumbnail_vertical if thumbnail != ".DS_Store"
    ]
    done_thumbnail_vertical = [
        thumbnail
        for thumbnail in done_thumbnail_vertical
        if not thumbnail.startswith("._")
    ]
    done_thumbnail_horizontal = [
        thumbnail
        for thumbnail in done_thumbnail_horizontal
        if not thumbnail.startswith("._")
    ]
    done_thumbnail_vertical = [
        thumbnail.replace(".png", "") for thumbnail in done_thumbnail_vertical
    ]
    done_thumbnail_horizontal = [
        thumbnail.replace(".png", "") for thumbnail in done_thumbnail_horizontal
    ]

    print(f"正在生成lookup_dict...")
    for srt in tqdm(all_format_srts):
        video_id = srt.replace(".srt", "")
        lookup_dict[video_id] = {}
        if video_id in done_srts:
            lookup_dict[video_id]["srt"] = True
        else:
            lookup_dict[video_id]["srt"] = False
        if video_id in done_merge_mp3:
            lookup_dict[video_id]["merge_mp3"] = True
        else:
            lookup_dict[video_id]["merge_mp3"] = False
        if video_id in done_mp4_path:
            lookup_dict[video_id]["mp4"] = True
        else:
            lookup_dict[video_id]["mp4"] = False
        if video_id in done_zh_title and video_id in done_zh_tag:
            lookup_dict[video_id]["zh_title_tag"] = True
        else:
            lookup_dict[video_id]["zh_title_tag"] = False

        if (
            video_id in done_thumbnail_vertical
            and video_id in done_thumbnail_horizontal
        ):
            lookup_dict[video_id]["thumbnail"] = True
        else:
            lookup_dict[video_id]["thumbnail"] = False

        if jump60:

            mp4_file = os.path.join(eng_mp4_abs_path, channel, video_id + ".mp4")
            mp4_duration = get_duration(mp4_file)

            # 超过60min的视频，跳过
            if mp4_duration > 3600:
                lookup_dict[video_id]["jump60"] = True
            else:
                lookup_dict[video_id]["jump60"] = False
    print(f"生成lookup_dict完成！")
    return lookup_dict


def is_valid_mp4(file_path):
    """Check if an MP4 file is valid."""
    try:
        video = VideoFileClip(file_path)
        # Try to read a frame from the video to check if it's read correctly
        video.reader.nframes
        video.close()
        return True
    except Exception:
        return False


def remove_invalid_mp4_files(directory):
    """Remove invalid MP4 files in the specified directory and its subdirectories."""
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".mp4"):
                file_path = os.path.join(root, filename)
                if not is_valid_mp4(file_path):
                    print(f"Deleting invalid MP4 file: {file_path}")
                    os.remove(file_path)


def controller_after_whisper(topic):
    cur_os = detect_os()
    if cur_os == "mac":
        hard_dive_path = "/Volumes/TOSHIBA"
    else:
        hard_dive_path = "/media/dhl/TOSHIBA"

    # whisper识别后的srt文件路径, 调用的起始依赖
    format_srt_path = f"{hard_dive_path}/video_material/format_srt/{topic}"
    eng_mp4_abs_path = f"{hard_dive_path}/video_v3/{topic}/download_shorts/mp4"
    mp3_merge_path = f"{hard_dive_path}/video_v3/merge_mp3/{topic}"
    jump60 = True

    # 目标文件路径
    dst_tts_mp3_path = f"{hard_dive_path}/video_material/tts_mp3/{topic}"
    dst_zh_srt_abs_path = f"{hard_dive_path}/video_material/zh_srt_nowarp/{topic}"
    dst_merged_mp4_path = f"{hard_dive_path}/video_v3/tts_mp4/{topic}"
    zh_title_dst_path = f"{hard_dive_path}/video_material/zh_title/{topic}"
    zh_tag_dst_path = f"{hard_dive_path}/video_material/zh_tag/{topic}"
    dst_vertical_thumbnail_path = (
        f"{hard_dive_path}/video_material/thumbnail_vertical/{topic}"
    )
    dst_horizontal_thumbnail_path = (
        f"{hard_dive_path}/video_material/thumbnail_horizontal/{topic}"
    )

    if topic in ["code"]:
        bg_mp3_path = f"{hard_dive_path}/video_material/tts_mp3/background/bg.mp3"
    else:
        bg_mp3_path = None

    # # 所有频道，依赖fomat_srt文件夹
    all_channels = os.listdir(format_srt_path)
    #  .DS_Store using list comprehension
    all_channels = [channel for channel in all_channels if channel != ".DS_Store"]
    # 删除._开头的文件
    all_channels = [channel for channel in all_channels if not channel.startswith("._")]

    data = load_bad_json()

    # delete all mp3s with 0 size
    print("开始删除size=0的mp3")
    target_directory = "/media/dhl/TOSHIBA/video_material/tts_mp3"
    delete_zero_size_mp3s(target_directory)
    print("删除mp3完成")

    # delete all bad mp4 files
    print("开始删除bad mp4")
    target_directory = f"/media/dhl/TOSHIBA/video_v3/tts_mp4/{topic}"
    remove_invalid_mp4_files(target_directory)
    print("删除bad mp4完成")

    # 遍历所有频道
    for channel in all_channels:
        ###### step1： 翻译srt文件 ######
        print(f"当前处理的频道是{channel}...")
        all_eng_srt = os.listdir(os.path.join(format_srt_path, channel))
        # 删掉.DS_Store
        all_eng_srt = [srt for srt in all_eng_srt if srt != ".DS_Store"]
        # 删除._开头的文件
        all_eng_srt = [srt for srt in all_eng_srt if not srt.startswith("._")]

        # 得到whisper识别后的英文srt文件列表
        formatted_srts_all = os.listdir(os.path.join(format_srt_path, channel))
        formatted_srts_all = [srt for srt in formatted_srts_all if srt != ".DS_Store"]
        formatted_srts_all = [
            srt for srt in formatted_srts_all if not srt.startswith("._")
        ]
        ### 创建相关channel文件夹，如果不存在的话
        # 检查目标翻译srt folder是否存在，不存在就创建
        if not os.path.exists(os.path.join(dst_zh_srt_abs_path, channel)):
            os.makedirs(os.path.join(dst_zh_srt_abs_path, channel))

        # 创建目标tts mp3文件夹
        if not os.path.exists(os.path.join(dst_tts_mp3_path, channel)):
            os.makedirs(os.path.join(dst_tts_mp3_path, channel))

        # 创建mp4合并mp3的mp4存放目录，如果不存在
        if not os.path.exists(os.path.join(dst_merged_mp4_path, channel)):
            os.makedirs(os.path.join(dst_merged_mp4_path, channel))

        # 创建合成mp3保存的文件夹
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
        if not os.path.exists(os.path.join(dst_horizontal_thumbnail_path, channel)):
            os.makedirs(os.path.join(dst_horizontal_thumbnail_path, channel))

        ### 完成创建
        lookup_dict = retain_pipe_status(
            channel,
            formatted_srts_all,
            dst_zh_srt_abs_path,
            mp3_merge_path,
            dst_merged_mp4_path,
            zh_title_dst_path,
            zh_tag_dst_path,
            dst_vertical_thumbnail_path,
            dst_horizontal_thumbnail_path,
            eng_mp4_abs_path,
            jump60,
        )

        # 遍历所有的srt文件
        for srt in tqdm(formatted_srts_all):
            video_id = srt.replace(".srt", "")
            # 超过30min的视频，跳过
            if jump60:
                if lookup_dict[video_id]["jump60"]:
                    print(f"频道{channel}的{srt} 超过60min，跳过...")
                    continue

            ###### step0: 读取bad.json文件，如果当前srt在bad.json中，跳过 ######
            if topic in data:
                if channel in data[topic]:
                    # 得到无后缀的srt文件名
                    if video_id in data[topic][channel]:
                        print(f"话题{topic},频道{channel}的{srt}在bad.json中，跳过...")
                        continue

            ###### step1： 翻译srt文件 ######
            if not lookup_dict[video_id]["srt"]:
                # 设定代理
                if cur_os == "linux":
                    set_clash_proxy()

                print(f"正在翻译频道{channel}的{srt}...")
                controller_translate_srt_single(
                    os.path.join(format_srt_path, channel, srt),
                    os.path.join(dst_zh_srt_abs_path, channel, srt),
                    topic=topic,
                )
                print(f"翻译{channel}的{srt}完成！")
                print("#" * 20)
                # 取消代理
                if cur_os == "linux":
                    unset_clash_proxy()

            ###### step2： tts合成语音clips ######
            # video_id = srt.replace(".srt", "")
            tts_mp3_path_single = os.path.join(dst_tts_mp3_path, channel, video_id)
            mp4_abs_single_path = os.path.join(
                eng_mp4_abs_path, channel, f"{video_id}.mp4"
            )
            dst_mp4_path = os.path.join(dst_merged_mp4_path, channel, f"{video_id}.mp4")

            merge_mp3_single_path = os.path.join(
                mp3_merge_path, channel, f"{video_id}.mp3"
            )
            if not lookup_dict[video_id]["merge_mp3"]:
                unset_clash_proxy()
                print(f"正在合成mp3，频道{channel}的{srt}...")
                controller_tts_single(
                    os.path.join(dst_zh_srt_abs_path, channel, srt),
                    dst_tts_mp3_path,
                    channel,
                    topic,
                    merge_single_mp3_path=merge_mp3_single_path,
                )
                print(f"tts合成{channel}的{srt}完成！")
                print("#" * 20)

            ###### step3： 合并mp3和mp4 ######
            # delete_all_trash_files()
            cur_zh_srt_path = os.path.join(dst_zh_srt_abs_path, channel, srt)
            if topic == "history":
                bg_music = False
            else:
                bg_music = True
            if not lookup_dict[video_id]["mp4"]:
                merge_mp4_controller_single(
                    tts_mp3_path=tts_mp3_path_single,
                    mp4_path=mp4_abs_single_path,
                    channel=channel,
                    tts_folder_name=video_id,
                    dst_mp4_path=dst_mp4_path,
                    cur_zh_srt_path=cur_zh_srt_path,
                    merge_mp3_single_path=merge_mp3_single_path,
                    bg_mp3_path=bg_mp3_path,
                    bg_music=bg_music,
                )

                print(f"合并mp3和mp4{channel}的{srt}完成！")
                print("#" * 20)

            ###### step4: 得到中文标题和tags ######
            title_dst_path = os.path.join(zh_title_dst_path, channel, video_id + ".txt")
            tag_dst_path = os.path.join(zh_tag_dst_path, channel, video_id + ".txt")

            # 如果没有中文标题和tags，就生成
            if not lookup_dict[video_id]["zh_title_tag"]:
                # set clash
                if cur_os == "linux":
                    set_clash_proxy()
                print(f"正在得到中文标题和tags，频道{channel}的{srt}...")
                zh_title_tags_controller_single(
                    srt_file_name=srt,
                    zh_title_dst_path=title_dst_path,
                    zh_tag_dst_path=tag_dst_path,
                    topic=topic,
                )
                print(f"中文标题和tags{channel}的{srt}完成！")
                print("#" * 20)
                # unset clash
                if cur_os == "linux":
                    unset_clash_proxy()

            ###### step5: 创建封面 ######
            if topic == "code" and not lookup_dict[video_id]["thumbnail"]:

                print(f"正在创建封面，频道{channel}的{srt}...")
                vertical_thumbnail_dst_path = os.path.join(
                    dst_vertical_thumbnail_path, channel, video_id + ".png"
                )
                zh_title_single_path = os.path.join(
                    zh_title_dst_path, channel, video_id + ".txt"
                )
                vertical_thumbnail_font_path = f"{hard_dive_path}/video_material/font/DottedSongtiCircleRegular.otf"
                bg_thumbnail_path_vertical = (
                    f"{hard_dive_path}/video_material/thumbnail_material/white2"
                )
                print(f"创建抖音封面")
                create_zh_title_thumbnail_vertical_single(
                    dst_thumbnail_path=vertical_thumbnail_dst_path,
                    zh_title_path=zh_title_single_path,
                    vertical_font_path=vertical_thumbnail_font_path,
                    bg_path=bg_thumbnail_path_vertical,
                )
                print("创建微信封面")
                horizontal_thumbnail_dst_path = os.path.join(
                    dst_horizontal_thumbnail_path, channel, video_id + ".png"
                )
                bg_thumbnail_path_horizontal = f"{hard_dive_path}/video_material/thumbnail_material/white2_horizontal"
                create_zh_title_thumbnail_horizontal_single(
                    dst_thumbnail_path=horizontal_thumbnail_dst_path,
                    zh_title_path=zh_title_single_path,
                    font_path=vertical_thumbnail_font_path,
                    bg_path=bg_thumbnail_path_horizontal,
                )
                print(f"封面{channel}的{srt}完成！")
                print("#" * 20)


def detect_os():
    os_name = platform.system()
    if os_name == "Darwin":
        print("You are using macOS.")
        return "mac"
    elif os_name == "Linux":
        print("You are using Linux.")
        return "linux"


if __name__ == "__main__":
    # 从命令行第一个参数得到topic
    topic = argv[1]

    delete_all_trash_files()
    controller_after_whisper(topic)
