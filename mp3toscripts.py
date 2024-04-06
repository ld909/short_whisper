import whisper
import os
from datetime import timedelta
from datetime import datetime
from datetime import time
from tqdm import tqdm
from srt_format import break_srt_txt_into_sentences, format_srt


def float_to_srt_timestamp(seconds):
    """Convert a float to a srt timestamp string"""
    # 将秒转换为毫秒
    milliseconds = int(seconds * 1000)

    # 将毫秒转换为小时、分钟、秒和毫秒
    hours = milliseconds // 3600000
    milliseconds = milliseconds % 3600000
    minutes = milliseconds // 60000
    milliseconds = milliseconds % 60000
    seconds = milliseconds // 1000
    milliseconds = milliseconds % 1000

    # 格式化字符串,确保小时、分钟、秒和毫秒都是两位数
    timestamp = "{:02d}:{:02d}:{:02d},{:03d}".format(
        hours, minutes, seconds, milliseconds
    )

    return timestamp


def mp3totxt(mp3_path):
    """this function using whisper larger v3 to generate pure transcriptions"""
    model = whisper.load_model("large-v3")
    print("strat transcribing...")
    result = model.transcribe(
        mp3_path,
        word_timestamps=True,
        initial_prompt="Hi everyone, welcome to my Youtube video.",
    )
    print("transcribing done")
    ts_list = []
    txt_list = []
    for segment in result["segments"]:
        start_time = float_to_srt_timestamp(float(segment["start"]))
        end_time = float_to_srt_timestamp(float(segment["end"]))
        text = segment["text"]
        # strip the text of any newline characters using strip()
        text = text.strip()
        if len(text) == 0:
            continue
        segmentId = segment["id"] + 1
        segment = f"{segmentId}\n{start_time} --> {end_time}\n{text}\n\n"
        ts_list.append((start_time, end_time))
        txt_list.append(text)
    return ts_list, txt_list


def check_ends_condition(txt_list):
    # check if every line except the last one ends with a qutation that ends a sentence
    for txt in txt_list:
        if txt[-1] not in [".", "?", "!"]:
            return False
        else:
            return True


def save_srt(ts_list, txt_list, srt_dst):
    """save the ts_list and txt_list as srt file in srt_dst"""
    srt_string = ""
    # save txt list with its corresponding ts list as srt file
    for idx, (ts, txt) in enumerate(zip(ts_list, txt_list)):
        # append to srt
        start_time, end_time = ts
        segmentId = idx + 1
        segment = f"{segmentId}\n{start_time} --> {end_time}\n{txt}\n\n"
        srt_string += segment
    # write to srt file
    with open(srt_dst, "w") as f:
        f.write(srt_string)


def read_test_mp3():

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
                # get base name without extension
                # save_srt(ts_list, txt_list, dst_srt)


# if __name__ == "__main__":
#     read_test_mp3()
