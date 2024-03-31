from collections import OrderedDict
from srt_format import read_srt_file, parse_srt_with_re
import os
import anthropic
from tqdm import tqdm
import ast
import jieba
import json



def wrap_srt_text_chinese(subtitle_text, max_length=25):
    """Wrap the subtitle text into lines with max_length characters per line, keeping words intact."""
    if len(subtitle_text) <= max_length:
        return subtitle_text

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

    if current_line:
        lines.append(current_line)

    return "\n".join(lines)


def controller():
    """Translate the formatted English srt files to Chinese srt files using Claude-3 Haiku."""
    api_key = "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"
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
            assert len(zh_srt) == len(subtitles)

            # save the translated subtitles and timestamps to a new file
            # 检查目标folder是否存在，不存在就创建
            if not os.path.exists(os.path.join(dst_zh_srt_abs_path, folder)):
                os.makedirs(os.path.join(dst_zh_srt_abs_path, folder))
            with open(os.path.join(dst_zh_srt_abs_path, folder, srt), "w") as f:
                for i in range(len(zh_srt)):
                    f.write(str(i + 1) + "\n")
                    f.write(timestamps[i][0] + " --> " + timestamps[i][1] + "\n")
                    srt_txt = zh_srt[i].replace("。", "")
                    # wrap the Chinese subtitle text
                    srt_txt = wrap_srt_text_chinese(srt_txt)
                    # if not the last sentence, add a \n\n
                    if i != len(zh_srt) - 1:
                        f.write(srt_txt + "\n\n")
                    # if the last sentence, add nothing
                    else:
                        f.write(srt_txt)


def translate_return_json(api_key, eng_srt_str):
    """translate srt from English to Chinese using Claude-3 Haiku"""
    client = anthropic.Anthropic(api_key=api_key)
    text = f"""我会给你一个字幕的list，list每个item是一条英文字幕，帮我翻译为中文。英文字幕list是:{eng_srt_str}。返回一个json，对应句子index（index从1开始）和翻译后的中文字幕，每除了翻译后的结果json外，不返回任何多余文字和额外说明，结果如{{"1":"字幕1"，"2":"字幕2"}}"""
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        temperature=0,
        system="你是一个优秀的翻译家，能够精确优雅准确精炼地把英文字幕翻译为中文字幕。返回一个json格式，格式严格遵循prompt中的标准。",
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
    translate_od = json.loads(translate_srt_str, object_pairs_hook=OrderedDict)
    translate_srt_list = []
    # extract the translated sentences from the ordered dictionary
    for key in translate_od:
        translate_srt_list.append(translate_od[key])
    success = message.stop_reason == "end_turn"
    return translate_srt_list, success


def translate_srt(api_key, eng_srt_str):
    """translate srt from English to Chinese using Claude-3 Haiku"""
    client = anthropic.Anthropic(api_key=api_key)
    text = f"我会给你一个字幕的list，list每个item是一条英文字幕，帮我翻译为中文。返回一个list，长度和输入的list长度一致，每个item是对应翻译后的中文字幕。除了翻译后的结果list外，不用返回任何多余的文字和额外说明。英文字幕list是: {eng_srt_str}"
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        temperature=0,
        system="你是一个优秀的翻译家，能够精确优雅准确精炼地把英文视频字幕翻译为中文字幕，视频题材为科技编程等相关领域。",
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
    assert len(translate_srt_list) == len(eng_srt_str)
    return translate_srt_list, success


if __name__ == "__main__":
    controller()
