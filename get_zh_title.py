import json
import os
import anthropic
from tqdm import tqdm


def translate_to_zh_title(eng_title, topic):
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    if topic == "code":
        prompt_txt = f"""我有一个英文视频的名称，视频是关于变成或者计算机科学的话题，请准确翻译相关专业词汇。请注意，英文名可能包含emoji等表情符号，返回的结果中请剔除这些emoji等符号，我要得到纯净的中文翻译结果。直接返回翻译后的中文标题，不需要其他多余信息。英文标题是：{eng_title}"""
    elif topic == "mama":
        prompt_txt = f"""我有一个英文视频的名称，视频是母婴类的标题，请准确翻译相关专业词汇。请注意，英文名可能包含emoji等表情符号，返回的结果中请剔除这些emoji等符号，我要得到纯净的中文翻译结果。直接返回翻译后的中文标题，不需要其他多余信息。英文标题是：{eng_title}"""
    message = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1000,
        temperature=0,
        system="你是一个优秀的翻译家，能够精确优雅准确精炼地把英文字幕翻译为中文字幕。不要返回多余信息，精准严格存寻prompt。",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt_txt,
                    }
                ],
            }
        ],
    )
    return message.content[0].text


def claude3_zh_tag(zh_title):

    client = anthropic.Anthropic(
        # defaults to os.environ.get("ANTHROPIC_API_KEY")
        # api_key=api_key,
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )
    message = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1000,
        temperature=0,
        system="你是一个优秀的翻译家，能够精确优雅准确精炼地把英文字幕翻译为中文字幕。不要返回多余信息，精准严格存寻prompt。",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""我有一个中文视频标题，基于此标题，给出三个tag，切记tag不要加井号#，返回格式是list,例如['tag1','tag2','tag3']。中文标题是：{zh_title}""",
                    }
                ],
            }
        ],
    )
    print("tags:", message.content[0].text)
    return message.content[0].text


def get_zh_title_tags(topic):

    # zh title从format srt这个文件夹中获取依赖
    format_srt_path = "/Users/donghaoliu/doc/video_material/format_srt"

    zh_title_dst_path = "/Users/donghaoliu/doc/video_material/zh_title"
    zh_tag_dst_path = "/Users/donghaoliu/doc/video_material/zh_tag"
    if topic == "code":
        all_topics = os.listdir(format_srt_path)
    elif topic == "mama":
        all_topics = ["mama"]
    # remove DS_store using list comprehension
    all_topics = [topic for topic in all_topics if topic != ".DS_Store"]

    for topic in tqdm(all_topics):

        # if topic folder does not exist in dst path, create one
        if not os.path.exists(os.path.join(zh_title_dst_path, topic)):

            # make directory
            os.makedirs(os.path.join(zh_title_dst_path, topic))

        if not os.path.exists(os.path.join(zh_tag_dst_path, topic)):
            os.makedirs(os.path.join(zh_tag_dst_path, topic))

        # get all channel folders under the topic folder
        all_channels = os.listdir(os.path.join(format_srt_path, topic))
        all_channels = [channel for channel in all_channels if channel != ".DS_Store"]

        # for each channel, get all srt files
        for channel in all_channels:

            # if channel folder does not exist in dst path, create one
            if not os.path.exists(os.path.join(zh_title_dst_path, topic, channel)):
                os.makedirs(os.path.join(zh_title_dst_path, topic, channel))

            if not os.path.exists(os.path.join(zh_tag_dst_path, topic, channel)):
                os.makedirs(os.path.join(zh_tag_dst_path, topic, channel))

            # get all srt files under the channel folder
            all_srt_files = os.listdir(os.path.join(format_srt_path, topic, channel))
            all_srt_files = [
                srt_file for srt_file in all_srt_files if srt_file != ".DS_Store"
            ]

            for srt_file in tqdm(all_srt_files):

                # get the base name of the srt file
                base_name = os.path.splitext(srt_file)[0]

                dst_file_name = base_name + "_title.txt"

                # if dst file already exists, skip
                if os.path.exists(
                    os.path.join(zh_title_dst_path, topic, channel, dst_file_name)
                ) and os.path.exists(
                    (os.path.join(zh_tag_dst_path, topic, channel, dst_file_name))
                ):
                    print(f"{dst_file_name} already exists, skip...")
                    continue

                # get the english title which is the base name of the srt file
                eng_title = base_name

                # using claude 3 to translate the eng title to zh title
                title_zh = translate_to_zh_title(eng_title, topic)
                print(f"英文标题：{eng_title}")
                print(f"中文标题：{title_zh}")

                tags_zh = claude3_zh_tag(title_zh)
                # convert from string to json by
                tags_zh = eval(tags_zh)
                print(f"中文tag：{tags_zh}")

                # write the zh title to the dst file
                with open(
                    os.path.join(zh_title_dst_path, topic, channel, dst_file_name), "w"
                ) as f:
                    f.write(title_zh)
                print(f"write {title_zh} to {dst_file_name}")
                print("*" * 50)

                # write the zh tags to the dst file
                with open(
                    os.path.join(zh_tag_dst_path, topic, channel, dst_file_name),
                    "w",
                    encoding="utf-8",
                ) as f:
                    for tag in tags_zh:
                        f.write(tag + "\n")


def zh_title_tags_controller_single(
    srt_file_name, zh_title_dst_path, zh_tag_dst_path, topic
):
    """得到中文标题和中文tag，写入到指定的文件中"""

    # 如果文件已经存在，则跳过
    if os.path.exists(zh_title_dst_path) and os.path.exists(zh_tag_dst_path):
        print(f"{srt_file_name} 中文title和tag 存在，跳过继续!")
        return

    # get the base name of the srt file
    base_name = os.path.splitext(srt_file_name)[0]
    dst_file_name = base_name + ".txt"

    # 得到英文标题，即srt文件的base name
    eng_title = base_name

    # using claude 3 to translate the eng title to zh title
    title_zh = translate_to_zh_title(eng_title, topic)
    print(f"英文标题：{eng_title}")
    print(f"中文标题：{title_zh}")

    tags_zh = claude3_zh_tag(title_zh)
    # convert from string to json
    tags_zh = eval(tags_zh)
    print(f"中文tag：{tags_zh}")

    # write the zh title to the dst file
    with open(zh_title_dst_path, "w") as f:
        f.write(title_zh)
    print(f"write {title_zh} to {dst_file_name}")
    print("*" * 50)

    # write the zh tags to the dst file
    with open(
        zh_tag_dst_path,
        "w",
        encoding="utf-8",
    ) as f:
        for tag in tags_zh:
            f.write(tag + "\n")


if __name__ == "__main__":
    topic = "code"
    get_zh_title_tags(topic)
