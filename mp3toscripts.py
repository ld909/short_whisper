import whisper
import os
from datetime import timedelta
from datetime import datetime
from datetime import time
from tqdm import tqdm


def mp3totxt(mp3_path):
    model = whisper.load_model("large-v3")
    print("strat transcribing...")
    result = model.transcribe(mp3_path, word_timestamps=True)
    print("transcribing done")
    ts_list = []
    txt_list = []
    for segment in result["segments"]:
        start_time = str(0) + str(timedelta(seconds=int(segment["start"]))) + ",000"
        end_time = str(0) + str(timedelta(seconds=int(segment["end"]))) + ",000"
        text = segment["text"]
        # strip the text of any newline characters using strip()
        text = text.strip()
        if len(text) == 0:
            continue
        segmentId = segment["id"] + 1
        segment = f"{segmentId}\n{start_time} --> {end_time}\n{text}\n\n"
        # print(segment)
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


def format_srt(ts_list, txt_list):
    print("start formatting...")
    # merge lines with single qutation
    single_qutation_idx = []
    for txt_id, txt in enumerate(txt_list):
        # if txt is a single qutation, merge it with the previous line
        if len(txt) == 1 and txt in [",", ".", "?", "!"]:
            txt_list[txt_id - 1] += txt
            single_qutation_idx.append(txt_id)

    # remove lines with single qutation from ts_list and txt_list
    if len(single_qutation_idx) > 0:
        for idx in single_qutation_idx:
            ts_list.pop(idx)
            txt_list.pop(idx)

    # check if the last line ends with a qutation that ends a sentence, if not, add a qutation
    if txt_list[-1][-1] not in [".", "?", "!"]:
        txt_list[-1] += "."

    ########### merge lines that within a sentence
    end_condition = False

    while end_condition:
        new_ts_list = []
        new_txt_list = []

        cur_idx = 0
        while cur_idx < len(txt_list):
            cur_txt = txt_list[cur_idx]
            cur_ts = ts_list[cur_idx]

            # if the current line ends with a qutation that ends a sentence
            if cur_txt[-1] in [".", "?", "!"]:
                # append the current line to the new list
                new_ts_list.append(cur_ts)
                new_txt_list.append(cur_txt)
                # increase the index
                cur_idx += 1

            else:
                # merge the current line with the next line
                next_txt = txt_list[cur_idx + 1]
                next_ts = ts_list[cur_idx + 1]

                # merge the current and next line
                new_txt = cur_txt + " " + next_txt
                new_ts = (cur_ts[0], next_ts[1])

                # append the new line to the new list
                new_ts_list.append(new_ts)
                new_txt_list.append(new_txt)

                # skip the next line
                cur_idx += 2

        # assign the new list to the old list
        ts_list = new_ts_list
        txt_list = new_txt_list

        # check end condition
        end_condition = check_ends_condition(new_txt_list)

    # print each line
    for i in range(len(txt_list)):
        print(i + 1)
        print(ts_list[i][0], "-->", ts_list[i][1])
        print(txt_list[i])
        print("\n")


def save_srt(ts_list, txt_list, srt_dst):
    srt_string = ""
    # save txt list with its corresponding ts list as srt file
    print(len(ts_list), len(txt_list))
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
    mp3_folder = "./test_mp3"

    # read all mp3 files in the folder
    for mp3_file in tqdm(os.listdir(mp3_folder)):
        if mp3_file.endswith(".mp3"):
            # check is base_name +'.srt' exists in the dst_srt
            base_name = os.path.splitext(mp3_file)[0]
            dst_srt = os.path.join("./test_srt", base_name + ".srt")
            if os.path.exists(dst_srt):
                continue
            print("processing:", base_name + ".mp3")
            mp3_path = os.path.join(mp3_folder, mp3_file)
            ts_list, txt_list = mp3totxt(mp3_path)

            # get base name without extension
            save_srt(ts_list, txt_list, dst_srt)
            # format_srt(ts_list, txt_list)


if __name__ == "__main__":
    read_test_mp3()
