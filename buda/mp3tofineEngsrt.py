"""
MP3到英文SRT字幕转换控制器

此脚本控制整个从MP3音频到SRT字幕的转换流程：
1. 使用OpenAI的Whisper模型将MP3音频文件转录为文本
2. 生成英文SRT字幕文件
3. 对SRT格式进行优化，使其更易读
4. 处理字幕断句，提高可读性

输入路径：/media/dhl/buda_videos_youtube/{主题名称}/{频道名称}/*.mp3
输出路径：/media/dhl/buda_videos_youtube/format_srt_zh/{主题名称}/{频道名称}/*.srt

注意：此脚本需要在Nvidia GPU上运行，否则Whisper模型处理速度会很慢！

使用方法：
    python mp3tofineEngsrt.py <主题名称>

示例：
    python mp3tofineEngsrt.py code
"""

import os
import sys
from tqdm import tqdm
from mp3toscripts import mp3totxt, save_srt
from srt_format import format_srt, break_srt_txt_into_sentences
from mutagen import File


def get_duration(file_path):
    """get the duration of the media file in seconds"""
    media = File(file_path)
    duration = media.info.length
    return duration


def remove_trash_files(mp3_abs_path):
    """
    清理目录中的垃圾文件

    此函数删除指定目录及其子目录中的.DS_Store文件和所有以'._'开头的文件，
    这些通常是macOS系统生成的元数据文件。

    参数:
        mp3_abs_path (str): MP3文件所在的绝对路径
    """
    # 先删除主目录下的.DS_Store文件
    ds_store_path = os.path.join(mp3_abs_path, ".DS_Store")
    if os.path.exists(ds_store_path):
        try:
            os.remove(ds_store_path)
            print(f"已删除主目录中的 .DS_Store 文件")
        except OSError as e:
            print(f"无法删除 {ds_store_path}: {e}")
            print("继续执行，跳过此文件")

    # 获取目录列表，过滤掉所有非目录项
    channels = []
    for item in os.listdir(mp3_abs_path):
        item_path = os.path.join(mp3_abs_path, item)
        if os.path.isdir(item_path):
            channels.append(item)

    # 处理子目录中的垃圾文件
    for channel in channels:
        channel_path = os.path.join(mp3_abs_path, channel)
        for file in os.listdir(channel_path):
            if file.startswith("._") or file == ".DS_Store":
                try:
                    os.remove(os.path.join(channel_path, file))
                    print(f"{channel}, {file} 已删除")
                except OSError as e:
                    print(f"无法删除 {channel}/{file}: {e}")
                    print("继续执行，跳过此文件")


def controller_mp3_to_format_srt(topic):
    """
    MP3到格式化SRT的控制器主函数

    此函数控制整个处理流程：
    1. 清理垃圾文件
    2. 遍历指定主题下的所有频道和MP3文件
    3. 使用Whisper模型转录音频为文本
    4. 格式化文本为SRT格式
    5. 优化SRT字幕的断句
    6. 保存格式化后的SRT文件

    函数会自动跳过：
    - 已处理过的文件
    - 时长超过30分钟的音频文件

    参数:
        topic (str): 主题名称，用于确定处理的文件夹
    """
    hard_dive_path = "/media/dhl"
    mp3_abs_path = f"{hard_dive_path}/buda_videos_youtube/{topic}"  # fill in the absolute path of the mp3 folder

    remove_trash_files(mp3_abs_path)
    dst_srt_abs_path = f"{hard_dive_path}/buda_videos_youtube/format_srt_zh/{topic}"  # fill in the absolute path of the srt folder

    # check if the dst_srt_abs_path exists, if not create it
    if not os.path.exists(dst_srt_abs_path):
        os.makedirs(dst_srt_abs_path)

    all_channels = os.listdir(mp3_abs_path)
    # remove .DS_store
    all_channels = [folder for folder in all_channels if folder != ".DS_Store"]

    # 删除._开头的文件
    all_channels = [folder for folder in all_channels if not folder.startswith("._")]

    print("所有频道包括:", all_channels)

    # read all mp3 files in the folder
    for channel in tqdm(all_channels):

        print("处理频道: ", channel)
        # read all mp3 files in the folder
        mp3_files = os.listdir(os.path.join(mp3_abs_path, channel))
        # 过滤掉点开头的文件
        mp3_files = [f for f in mp3_files if not f.startswith(".")]

        for mp3_file in tqdm(mp3_files):
            if mp3_file.endswith(".mp3"):
                # check if base_name +'.srt' exists in the dst_srt
                base_name = os.path.splitext(mp3_file)[0]
                dst_srt = os.path.join(dst_srt_abs_path, channel, base_name + ".srt")

                # check if os.path.join(dst_srt_abs_path, channel) exists
                if not os.path.exists(os.path.join(dst_srt_abs_path, channel)):
                    os.makedirs(os.path.join(dst_srt_abs_path, channel))

                # 检查之前是否完成过此任务，完成就跳过
                if os.path.exists(dst_srt):
                    print(f"SRT文件已存在，跳过 {channel} 中的 {base_name}")
                    continue
                mp3_path = os.path.join(mp3_abs_path, channel, mp3_file)
                print("正在处理: ", mp3_path, " 频道: ", channel)
                # if mp3 duration is larger than 30 minutes, skip
                mp3_duration_seconds = get_duration(mp3_path)
                if mp3_duration_seconds > 1800:
                    print(f"MP3 {mp3_file} 时长超过30分钟，跳过")
                    continue

                mp3_path = os.path.join(mp3_abs_path, channel, mp3_file)

                print("开始使用OpenAI whisper模型将MP3转录为文本...")
                ts_list, txt_list = mp3totxt(mp3_path)

                # format srt
                ts_list, txt_list = format_srt(ts_list, txt_list)

                # break into sub sentences
                ts_list, txt_list = break_srt_txt_into_sentences(ts_list, txt_list)

                # check if the number of timestamps and subtitles are the same
                assert len(ts_list) == len(txt_list)

                # get base name without extension
                save_srt(ts_list, txt_list, dst_srt)
                print(f"格式化后的字幕已保存到 {dst_srt}")


if __name__ == "__main__":
    # topic = "code"
    topic = sys.argv[1]
    # topic = "mama"
    controller_mp3_to_format_srt(topic=topic)
