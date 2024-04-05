# this file is the controller of the whole pipeline from mp3 to srt to video
# srt files are generated from mp3 files and are formatted to make it more readable
# srt are still in English
# ！！！！此脚本需要Nividai GPU上运行，否则whisper模型会很慢！！！！

import os
from tqdm import tqdm
from mp3toscripts import mp3totxt, save_srt
from srt_format import format_srt, break_srt_txt_into_sentences


def controller_mp3_to_format_srt():
    mp3_abs_path = "/home/dhl/Documents/video_materials/mp3/code"  # fill in the absolute path of the mp3 folder
    dst_srt_abs_path = "/home/dhl/Documents/video_materials/format_srt/code"  # fill in the absolute path of the srt folder

    # check if the dst_srt_abs_path exists, if not create it
    if not os.path.exists(dst_srt_abs_path):
        os.makedirs(dst_srt_abs_path)

    all_mp3_folders = os.listdir(mp3_abs_path)

    # read all mp3 files in the folder
    for mp3_channel_folder in tqdm(all_mp3_folders):
        print("processing: ", mp3_channel_folder)
        # read all mp3 files in the folder
        for mp3_file in tqdm(
            os.listdir(os.path.join(mp3_abs_path, mp3_channel_folder))
        ):
            if mp3_file.endswith(".mp3"):
                # check if base_name +'.srt' exists in the dst_srt
                base_name = os.path.splitext(mp3_file)[0]
                print("processing: ", base_name + ".mp3")
                dst_srt = os.path.join(
                    dst_srt_abs_path, mp3_channel_folder, base_name + ".srt"
                )
                # check if os.path.join(dst_srt_abs_path, mp3_channel_folder) exists
                if not os.path.exists(
                    os.path.join(dst_srt_abs_path, mp3_channel_folder)
                ):
                    os.makedirs(os.path.join(dst_srt_abs_path, mp3_channel_folder))

                # 检查之前是否完成过此任务，完成就跳过
                if os.path.exists(dst_srt):
                    print("srt file exists, skip")
                    continue

                mp3_path = os.path.join(mp3_abs_path, mp3_channel_folder, mp3_file)
                print("transcribing mp3 to txt using OpenAI whisper model...")
                ts_list, txt_list = mp3totxt(mp3_path)

                # format srt
                ts_list, txt_list = format_srt(ts_list, txt_list)

                # break into sub sentences
                ts_list, txt_list = break_srt_txt_into_sentences(ts_list, txt_list)

                # check if the number of timestamps and subtitles are the same
                assert len(ts_list) == len(txt_list)

                # get base name without extension
                save_srt(ts_list, txt_list, dst_srt)
                print(f"srt formatted save on {dst_srt}")


if __name__ == "__main__":
    controller_mp3_to_format_srt()
