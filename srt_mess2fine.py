# this file is the controller of the whole pipeline from mp3 to srt to video
# srt files are generated from mp3 files and are formatted to make it more readable
# srt are still in English

import os
from tqdm import tqdm
from mp3toscripts import mp3totxt, save_srt
from srt_format import format_srt, break_srt_txt_into_sentences


def controller_mp3_to_format_srt():
    mp3_abs_path = ""  # fill in the absolute path of the mp3 folder
    dst_srt_abs_path = ""  # fill in the absolute path of the srt folder

    # check if the dst_srt_abs_path exists, if not create it
    if not os.path.exists(dst_srt_abs_path):
        os.makedirs(dst_srt_abs_path)

    all_mp3_files = os.listdir(mp3_abs_path)

    # read all mp3 files in the folder
    for mp3_channel_folder in all_mp3_files:
        # read all mp3 files in the folder
        for mp3_file in tqdm(
            os.listdir(os.path.join(mp3_abs_path, mp3_channel_folder))
        ):
            if mp3_file.endswith(".mp3"):
                # check if base_name +'.srt' exists in the dst_srt
                base_name = os.path.splitext(mp3_file)[0]

                dst_srt = os.path.join(
                    dst_srt_abs_path, mp3_channel_folder, base_name + ".srt"
                )
                # check if os.path.join(dst_srt_abs_path, mp3_channel_folder) exists
                if not os.path.exists(
                    os.path.join(dst_srt_abs_path, mp3_channel_folder)
                ):
                    os.makedirs(os.path.join(dst_srt_abs_path, mp3_channel_folder))

                # check if the srt file exists, if it does, skip
                if os.path.exists(dst_srt):
                    continue

                print("processing:", base_name + ".mp3")
                mp3_path = os.path.join(mp3_abs_path, mp3_channel_folder, mp3_file)
                ts_list, txt_list = mp3totxt(mp3_path)

                # format srt
                ts_list, txt_list = format_srt(ts_list, txt_list)

                # break into sub sentences
                ts_list, txt_list = break_srt_txt_into_sentences(ts_list, txt_list)

                # check if the number of timestamps and subtitles are the same
                assert len(ts_list) == len(txt_list)

                # get base name without extension
                save_srt(ts_list, txt_list, dst_srt)
