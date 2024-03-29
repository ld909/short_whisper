import datetime
import re
import os
from datetime import time, timedelta


def time_str_to_obj(time_str):
    """将时间戳字符串转换为 timedelta 对象。"""
    # 将时间戳拆分成小时、分钟、秒和毫秒
    hours, minutes, seconds = time_str.split(":")
    seconds, milliseconds = seconds.split(",")

    # 计算总秒数
    total_seconds = (
        int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000
    )

    # 创建 timedelta 对象
    time_obj = timedelta(seconds=total_seconds)

    return time_obj


def check_ends_condition(txt_list):
    """check if the last line ends with a qutation that ends a sentence"""
    # check if every line except the last one ends with a qutation that ends a sentence
    for txt in txt_list:
        txt = txt.strip()
        if txt[-1] not in [".", "?", "!"]:
            return False
    return True


def format_srt(ts_list, txt_list):
    """format the srt file to make it more readable and easier to understand"""
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

    # merge lines that within a sentence
    end_condition = False

    while not end_condition:
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

    print("formatting finished!")
    return ts_list, txt_list


def parse_srt_with_re(srt_content):
    """
    使用正则表达式解析SRT字幕内容。

    Args:
        srt_content (str): SRT文件的内容字符串。

    Returns:
        tuple: (timestamps, subtitles) 时间戳列表和字幕列表。
    """
    timestamps = []
    subtitles = []

    # 定义一个正则表达式来匹配字幕块：序号、时间戳和字幕文本
    pattern = re.compile(
        r"\d+\s+(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\s+(.*?)(?=\n\n|\Z)",
        re.DOTALL,
    )

    matches = pattern.findall(srt_content)

    for match in matches:
        start_time, end_time, subtitle = match
        timestamps.append((start_time, end_time))
        subtitle = subtitle.replace(
            "\n", " "
        ).strip()  # 将字幕文本中的换行符替换为空格，并去除首尾空白
        subtitles.append(subtitle)

    return timestamps, subtitles


def read_srt_file(file_path):
    """read the srt file and return the content"""
    with open(file_path, "r") as f:
        srt_content = f.read()
    return srt_content


def check_breack_condition(txt):
    """check if the txt is a single sentence, if it is, return True, otherwise return False"""
    if ". " not in txt and "? " not in txt and "! " not in txt:
        return True
    else:
        return False


def timedelta_to_srt(timedelta_obj):
    """convert timedelta object to srt format time string"""
    total_seconds = timedelta_obj.total_seconds()

    # compute hours, minutes, seconds and milliseconds
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int(total_seconds * 1000 % 1000)

    # format the time string
    time_string = "{}:{}:{},{}".format(
        str(hours).zfill(2),
        str(minutes).zfill(2),
        str(seconds).zfill(2),
        str(milliseconds).zfill(3),
    )

    return time_string


def break_srt_txt_into_sentences(old_ts_list, old_txt_list):
    """break the srt text into sentences"""

    for qutation in [". ", "? ", "! "]:
        ts_list = []
        txt_list = []

        # split the text into sentences,
        # if the result length is greater than 1, generate corresponding timestamps
        for txt_id, txt in enumerate(old_txt_list):
            if len(txt.split(qutation)) > 1:
                # 分割成子句
                sentences = txt.split(qutation)
                # compute timestamps for each sentence
                timestamp = old_ts_list[txt_id]
                start_time_str = timestamp[0]
                end_time_str = timestamp[1]
                # convert from string to obj
                start_time_obj = time_str_to_obj(start_time_str)
                end_time_obj = time_str_to_obj(end_time_str)
                # compute the duration of the sentence
                duration = end_time_obj - start_time_obj
                # convert the duration to seconds
                duration = duration.total_seconds()

                # compute the duration of each word
                # unit is seconds/word
                words = txt.split(" ")
                word_speed = duration / len(words)
                print(duration, len(words), start_time_str, end_time_str, word_speed)

                # loop through each new sentence split by qutation
                temp_ts = None
                for sentence_idx in range(len(sentences)):
                    # if the sentence is not the last sentence, append the qutation to the sentence
                    if sentence_idx != len(sentences) - 1:
                        sentence = sentences[sentence_idx] + qutation.strip()
                    else:
                        sentence = sentences[sentence_idx]
                    # compute the start and end time of the sentence
                    if sentence_idx == 0:
                        new_start_time_obj = start_time_obj
                        new_end_time_obj = new_start_time_obj + datetime.timedelta(
                            seconds=word_speed * len(sentence.split(" "))
                        )
                        ts_list.append(
                            (start_time_str, timedelta_to_srt(new_end_time_obj))
                        )
                        txt_list.append(sentence)
                        temp_ts = new_end_time_obj

                    elif sentence_idx != len(sentences) - 1:
                        new_start_time_obj = temp_ts
                        new_end_time_obj = new_start_time_obj + datetime.timedelta(
                            seconds=word_speed * len(sentence.split(" "))
                        )
                        ts_list.append(
                            (
                                timedelta_to_srt(new_start_time_obj),
                                timedelta_to_srt(new_end_time_obj),
                            )
                        )
                        txt_list.append(sentence)
                        temp_ts = new_end_time_obj
                    # 最后一个子句
                    elif sentence_idx == len(sentences) - 1:
                        new_start_time_obj = temp_ts
                        new_end_time_obj = end_time_obj
                        ts_list.append(
                            (
                                timedelta_to_srt(new_start_time_obj),
                                timedelta_to_srt(new_end_time_obj),
                            )
                        )
                        txt_list.append(sentence)
                        temp_ts = None
            else:
                ts_list.append(old_ts_list[txt_id])
                txt_list.append(old_txt_list[txt_id])

        # assign the new list to the old list
        old_ts_list = ts_list
        old_txt_list = txt_list

    return ts_list, txt_list


def read_and_format():
    srt_dst = "./test_srt"
    all_srt = os.listdir(srt_dst)
    for srt_name in all_srt:
        srt_path = os.path.join(srt_dst, srt_name)
        srt_content = read_srt_file(srt_path)
        timestamps, subtitles = parse_srt_with_re(srt_content)
        ts_list, txt_list = format_srt(timestamps, subtitles)
        # save to ./test_format
        # with open("./test_format/" + srt_name, "w") as f:
        #     for i in range(len(txt_list)):
        #         f.write(str(i + 1) + "\n")
        #         f.write(ts_list[i][0] + " --> " + ts_list[i][1] + "\n")
        #         f.write(txt_list[i] + "\n\n")
        ts_list, txt_list = break_srt_txt_into_sentences(ts_list, txt_list)

        # check if the number of timestamps and subtitles are the same
        assert len(ts_list) == len(txt_list)

        # save to ./test_format_final
        with open("./test_format_final/" + srt_name, "w") as f:
            for i in range(len(txt_list)):
                f.write(str(i + 1) + "\n")
                f.write(ts_list[i][0] + " --> " + ts_list[i][1] + "\n")
                f.write(txt_list[i] + "\n\n")


if __name__ == "__main__":
    read_and_format()
