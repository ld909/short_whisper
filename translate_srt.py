from collections import OrderedDict
from srt_format import (
    read_srt_file,
    parse_srt_with_re,
    time_str_to_obj,
    timedelta_to_srt,
)
import os
import anthropic
from tqdm import tqdm
import ast
import jieba
import json
from datetime import time, timedelta


def get_line_timestamps(lines, start_time, end_time):
    """计算每行字幕的时间戳"""
    # 计算字幕的持续时间(以秒为单位)
    duration = (end_time - start_time).total_seconds()

    # 计算总字数
    total_words = sum(len(line) for line in lines)

    # 计算每个单词的平均持续时间
    word_duration = duration / total_words

    line_timestamps = []
    current_time = start_time

    for line in lines:
        # 计算当前行的字数
        line_words = len(line)

        # 计算当前行的结束时间戳
        line_end_time = current_time + timedelta(seconds=line_words * word_duration)

        # 将当前行的开始和结束时间戳添加到结果列表中
        line_timestamps.append(
            (timedelta_to_srt(current_time), timedelta_to_srt(line_end_time))
        )

        # 更新当前时间戳为下一行的开始时间戳
        current_time = line_end_time

    return line_timestamps


def merge_lines_and_timestamps(lines, line_timestamps):
    """将字幕行和时间戳合并为一行字幕和时间戳"""
    merged_lines = []
    merged_timestamps = []

    # 使用zip函数将lines和line_timestamps两两配对
    # 分别得到偶数索引和奇数索引的元素
    for (line1, timestamp1), (line2, timestamp2) in zip(
        zip(lines[::2], line_timestamps[::2]), zip(lines[1::2], line_timestamps[1::2])
    ):
        # 将两个字幕行合并为一行
        merged_line = "\n".join([line1, line2])

        # 取第一个时间戳的开始时间和第二个时间戳的结束时间作为合并后的时间戳
        merged_timestamp = (timestamp1[0], timestamp2[1])

        # 将合并后的字幕行和时间戳添加到结果列表中
        merged_lines.append(merged_line)
        merged_timestamps.append(merged_timestamp)

    # 如果lines的长度为奇数,将最后一个字幕行和时间戳单独处理
    if len(lines) % 2 != 0:
        merged_lines.append(lines[-1])
        merged_timestamps.append(line_timestamps[-1])

    return merged_lines, merged_timestamps


def wrap_srt_text_chinese(subtitle_text, max_length=25, timestamps=None):
    """Wrap the subtitle text into lines with max_length characters per line, keeping words intact."""
    if len(subtitle_text) <= max_length:
        return [subtitle_text], [timestamps]

    # 使用jieba对字幕文本进行分词
    words = jieba.lcut(subtitle_text)

    lines = []
    current_line = ""

    for word in words:
        if len(current_line + word) <= max_length:
            current_line += word
        else:
            lines.append(current_line)
            current_line = word

    # append the last line
    if current_line:
        lines.append(current_line)

    if len(lines) <= 2:
        return ["\n".join(lines)], [timestamps]
    else:
        start_time_obj = time_str_to_obj(timestamps[0])
        end_time_obj = time_str_to_obj(timestamps[1])
        line_timestamps = get_line_timestamps(lines, start_time_obj, end_time_obj)

        assert len(lines) == len(line_timestamps)

        new_lines, new_timestamps = merge_lines_and_timestamps(lines, line_timestamps)
        return new_lines, new_timestamps


def controller():
    """Translate the formatted English srt files to Chinese srt files using Claude-3 Haiku."""
    api_key = ""
    eng_srt_abs_path = "/Users/donghaoliu/doc/video_material/format_srt/code"
    dst_zh_srt_abs_path = "/Users/donghaoliu/doc/video_material/zh_srt/code"
    all_folders = os.listdir(eng_srt_abs_path)
    # remove .DS_Store using list comprehension
    all_folders = [folder for folder in all_folders if folder != ".DS_Store"]
    for folder in all_folders:
        formatted_srts = os.listdir(os.path.join(eng_srt_abs_path, folder))
        # remove .DS_Store using list comprehension
        formatted_srts = [srt for srt in formatted_srts if srt != ".DS_Store"]
        for srt in formatted_srts:

            # 检查之前是否完成过此任务，完成就跳过
            if os.path.exists(os.path.join(dst_zh_srt_abs_path, folder, srt)):
                print(f"{srt} 文件存在, 跳过继续...")
                continue

            # parse the srt file
            srt_read = read_srt_file(os.path.join(eng_srt_abs_path, folder, srt))
            print("Translating: ", srt)
            # get the timestamps and subtitles from the srt file
            timestamps, subtitles = parse_srt_with_re(srt_read)

            # 检查时间戳和字幕数量是否一致
            assert len(timestamps) == len(subtitles)

            zh_srt = []
            # everytime get 3 subtitles and corresponding timestamps
            for i in tqdm(range(0, len(subtitles), 3)):
                # get 3 subtitles
                sentences = subtitles[i : i + 3]
                # format the 3 subtitles into a list, each item is a sentence, surrounded by double quotes
                sentences = [f"{sentence}" for sentence in sentences]

                # translate the 3 subtitles
                success = False
                while not success:
                    translated_sentences, success = translate_srt(api_key, sentences)

                # assert the number of translated subtitles is the same as the original subtitles
                assert len(translated_sentences) == len(sentences)

                # append the translated subtitles to the list
                for zh_sentence in translated_sentences:
                    zh_srt.append(zh_sentence)

            # assert the number of translated subtitles is the same as the original subtitles
            assert len(zh_srt) == len(subtitles) == len(timestamps)

            # save the translated subtitles and timestamps to a new file
            # 检查目标folder是否存在，不存在就创建
            if not os.path.exists(os.path.join(dst_zh_srt_abs_path, folder)):
                os.makedirs(os.path.join(dst_zh_srt_abs_path, folder))

            ts_list = []
            srt_zh_list = []

            for i in range(len(zh_srt)):
                srt_txt = zh_srt[i].replace("。", "")
                temp_srt_list, temp_ts_list = wrap_srt_text_chinese(
                    srt_txt, timestamps=timestamps[i]
                )
                ts_list += temp_ts_list
                srt_zh_list += temp_srt_list

            # 检查时间戳和字幕数量是否一致
            assert len(ts_list) == len(srt_zh_list)

            # 写入目标srt文件
            with open(os.path.join(dst_zh_srt_abs_path, folder, srt), "w") as f:
                for i in range(len(srt_zh_list)):
                    f.write(str(i + 1) + "\n")
                    f.write(ts_list[i][0] + " --> " + ts_list[i][1] + "\n")
                    # if not the last sentence, add a \n\n
                    if i != len(srt_zh_list) - 1:
                        f.write(srt_zh_list[i] + "\n\n")
                    # if the last sentence, add nothing
                    else:
                        f.write(srt_zh_list[i])


def translate_single_srt(api_key, eng_srt_single_str):
    """translate a single srt from English to Chinese using Claude-3 Haiku"""
    client = anthropic.Anthropic(
        # defaults to os.environ.get("ANTHROPIC_API_KEY")
        api_key=api_key,
    )
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        temperature=0,
        system="你是一个优秀的翻译家，能够精确优雅准确精炼地把英文字幕翻译为中文字幕。不要返回多余信息，精准严格存寻prompt。原视频是关于计算机科学/编程/数学相关话题的，请注意你的专业用语。",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""我有一个英文字幕，请帮我翻译为英文，直接返回翻译后的结果，不返回其他任何多余结果, 结果不要带任何引号。英文字幕是：{eng_srt_single_str}""",
                    }
                ],
            }
        ],
    )
    translate_srt_str = message.content[0].text
    success = message.stop_reason == "end_turn"
    return translate_srt_str, success


def translate_return_json(api_key, eng_srt_str):
    """translate srt from English to Chinese using Claude-3 Haiku"""
    client = anthropic.Anthropic(api_key=api_key)
    text = f"""我会给你一个字幕的list，list每个item是一条英文字幕，帮我翻译为中文。英文字幕list是:{eng_srt_str}。返回一个json，对应句子index（index从1开始）和翻译后的中文字幕，每除了翻译后的结果json外，不返回任何多余文字和额外说明，翻译后字幕不要包含双引号"，返回结果如{{"1":"字幕1"，"2":"字幕2"}}。"""
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        temperature=0,
        system="你是一个优秀的翻译家，能够精确优雅准确精炼地把英文字幕翻译为中文字幕。返回一个json格式，格式严格遵循prompt中的标准。原视频是关于计算机科学/编程/数学相关话题的，请注意你的专业用语。",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": text,
                    }
                ],
            }
        ],
    )
    translate_srt_str = message.content[0].text
    try:
        # 先尝试转化为json
        print("尝试转化为json格式")
        translate_srt_list = []

        translate_od = json.loads(translate_srt_str, object_pairs_hook=OrderedDict)
        # extract the translated sentences from the ordered dictionary
        for key in translate_od:
            # replace double quotes with single quotes
            translate_srt_list.append(translate_od[key].replace('"', "'"))
        success = message.stop_reason == "end_turn"
    except:
        # 逐句翻译
        print("尝试逐句翻译")
        translate_srt_list = []
        for srt_eng_single_str in eng_srt_str:
            success = False
            while not success:
                zh_single_srt, success = translate_single_srt(
                    api_key, srt_eng_single_str
                )

            translate_srt_list.append(zh_single_srt)
    return translate_srt_list, success


def translate_srt(api_key, eng_srt_str):
    """translate srt from English to Chinese using Claude-3 Haiku"""
    print("正在翻译：", eng_srt_str)
    client = anthropic.Anthropic(api_key=api_key)
    text = f"我会给你一个字幕的list，list每个item是一条英文字幕，帮我翻译为中文。返回一个list，长度和输入的list长度一致，每个item是对应翻译后的中文字幕。除了翻译后的结果list外，不用返回任何多余的文字和额外说明。英文字幕list是: {eng_srt_str}"
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        temperature=0,
        system="你是一个优秀的翻译家，能够精确优雅准确精炼地把英文视频字幕翻译为中文字幕，原视频是关于计算机科学/编程/数学相关话题的，请注意你的专业用语。",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": text,
                    }
                ],
            }
        ],
    )
    translate_srt_str = message.content[0].text
    try:
        translate_srt_list = ast.literal_eval(translate_srt_str)
        success = message.stop_reason == "end_turn"
    except:
        translate_srt_list, success = translate_return_json(api_key, eng_srt_str)
        print("使用json格式返回，结果：", translate_srt_list)

    return translate_srt_list, success


if __name__ == "__main__":
    controller()
