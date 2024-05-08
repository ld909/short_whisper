import requests
from srt_format import read_srt_file, parse_srt_with_re
import os
from tqdm import tqdm
from srt_format import time_str_to_obj

import azure.cognitiveservices.speech as speechsdk
import xml.etree.ElementTree as ET
from xml.dom import minidom


def create_ssml_string(text, rate="1.05", yinse_name="zh-CN-YunjieNeural"):
    """创建SSML字符串"""
    # 创建根元素
    speak = ET.Element(
        "speak",
        version="1.0",
        xmlns="http://www.w3.org/2001/10/synthesis",
        attrib={"xml:lang": "zh-CN"},
    )

    # 创建 voice 元素
    voice = ET.SubElement(speak, "voice", name=yinse_name)

    # 创建 prosody 元素
    prosody = ET.SubElement(voice, "prosody", rate=rate)

    # 设置 prosody 元素的文本内容
    prosody.text = text

    # 创建 minidom 对象,用于格式化 XML
    xml_str = ET.tostring(speak, "utf-8")
    dom = minidom.parseString(xml_str)

    # 获取格式化后的 SSML 字符串
    ssml_string = dom.toprettyxml(indent="    ", encoding="utf-8").decode("utf-8")

    return ssml_string


def tts_ms(txt_string, topic, clip_dst_path):
    """调用微软的tts接口，生成mp3文件"""

    # 配置参数
    speech_key = "cba10589e21e48dfb986f493e276b833"
    service_region = "eastasia"

    speech_config = speechsdk.SpeechConfig(
        subscription=speech_key, region=service_region
    )

    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3
    )

    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=None
    )
    if topic == "mama":
        yinse_name = ""
    elif topic == "code":
        yinse_name = "zh-CN-YunjieNeural"
    # 构造SSML字符串
    ssml_string = create_ssml_string(txt_string, yinse_name=yinse_name)

    # 将 SSML 字符串传递给语音合成函数
    result = speech_synthesizer.speak_ssml_async(ssml_string).get()

    # 保存到本地
    stream = speechsdk.AudioDataStream(result)
    stream.save_to_wav_file(clip_dst_path)

    # 判断是否合成成功
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return True
    else:
        return False


def tts_minimax(content_str, mp3_dst_path, topic):
    """调用minimax的tts接口，生成mp3文件"""

    if topic == "mama":
        voice_id = "presenter_female"
    elif topic == "code":
        voice_id = "male-qn-jingying-jingpin"
    else:
        print("对应的topic不存在，请检查topic是否正确")
        return

    """生成字幕"""
    group_id = "1725312458689614655"
    api_key = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiLliJjkuJzmmIoiLCJVc2VyTmFtZSI6IuWImOS4nOaYiiIsIkFjY291bnQiOiIiLCJTdWJqZWN0SUQiOiIxNzI1MzEyNDU4Njk4MDAzMjYzIiwiUGhvbmUiOiIxODU4MzM4MTAzNiIsIkdyb3VwSUQiOiIxNzI1MzEyNDU4Njg5NjE0NjU1IiwiUGFnZU5hbWUiOiIiLCJNYWlsIjoiIiwiQ3JlYXRlVGltZSI6IjIwMjQtMDQtMjMgMjA6NTU6MTQiLCJpc3MiOiJtaW5pbWF4In0.yv7qeUESVBLpi67g-BvEhFE0Fl9j13VUF0NddFJFAlauxZeTt1n8uaRSba__HGoLrDz_JgbWYFZPt1FEIbeYZQaDuTYJw68qbSTnSuUZCCRX7VjGeQ6x3tiWA7LlpF6hbzsUsiKRo2gT95Q3TQVKQJvpZszUrPlr6TODsrPycgoTaSbZ_gUwgY97ZHcJmSzbZyZEcsDyHe5hw_JYcGeO-fh8bsxZXrXHwFB1doR5YT3pVm8B24O_QMx2co3Z1jSh6ahJO1ctCvC0ff6Fpo9oZ4bKUbUUtcRm9iMeCwCx4LMaq80z3TnOKM22i5CTZxOfuOLjiCxD4Sp4Aq4-gDcSkA"

    url = f"https://api.minimax.chat/v1/text_to_speech?GroupId={group_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "voice_id": voice_id,
        # 如同时传入voice_id和timber_weights时，则会自动忽略voice_id，以timber_weights传递的参数为准
        "text": f"{content_str}",
        "model": "speech-02",
        "speed": 1.0,
        "vol": 1.0,
        "pitch": 0,
    }

    response = requests.post(url, headers=headers, json=data)
    print("trace_id", response.headers.get("Trace-Id"))
    if response.status_code != 200 or "json" in response.headers["Content-Type"]:
        print("调用失败", response.status_code, response.text)
        return False
    with open(mp3_dst_path, "wb") as f:
        f.write(response.content)
        return True


def controller_tts(topic):
    zh_nowarp_srt_path = f"/Users/donghaoliu/doc/video_material/zh_srt_nowarp/{topic}"
    tts_mp3_path = f"/Users/donghaoliu/doc/video_material/tts_mp3/{topic}"

    all_channels = os.listdir(zh_nowarp_srt_path)
    # remove .DS_Store using list comprehension
    all_channels = [channel for channel in all_channels if channel != ".DS_Store"]
    for channel in all_channels:
        print(f"当前处理的频道是{channel}...")
        all_srt = os.listdir(os.path.join(zh_nowarp_srt_path, channel))

        # remove .DS_Store using list comprehension
        all_srt = [srt for srt in all_srt if srt != ".DS_Store"]

        # 创建目标tts mp3文件夹
        if not os.path.exists(os.path.join(tts_mp3_path, channel)):
            os.makedirs(os.path.join(tts_mp3_path, channel))

        # 对每个中文字幕文件遍历，生成对应的mp3文件
        for srt_name in all_srt:
            srt_path = os.path.join(zh_nowarp_srt_path, channel, srt_name)
            srt_content = read_srt_file(srt_path)
            _, subtitles = parse_srt_with_re(srt_content)
            srt_basename = os.path.splitext(srt_name)[0]

            # 创建一个文件夹，用于存放每个字幕的mp3 clips
            if not os.path.exists(os.path.join(tts_mp3_path, channel, srt_basename)):
                os.makedirs(os.path.join(tts_mp3_path, channel, srt_basename))

            # 生成字幕，并保存为mp3
            for sub_idx, subtitle in tqdm(enumerate(subtitles)):
                tts_success = False

                # 目标mp3 clip的路径
                mp3_dst_path = os.path.join(
                    tts_mp3_path, channel, srt_basename, f"{sub_idx}.mp3"
                )

                # 如果文件已经存在，则跳过
                if os.path.exists(mp3_dst_path):
                    print(f"{srt_basename} {sub_idx} already exists!")
                    continue

                while not tts_success:
                    tts_success = tts_ms(
                        subtitle,
                        clip_dst_path=os.path.join(
                            tts_mp3_path, channel, srt_basename, f"{sub_idx}.mp3"
                        ),
                        topic=topic,
                    )
                print(f"{srt_basename} {sub_idx} tts done!")


def controller_tts_single(
    zh_srt_path,
    tts_mp3_path,
    channel,
):
    srt_path = zh_srt_path
    srt_content = read_srt_file(srt_path)
    _, subtitles = parse_srt_with_re(srt_content)
    srt_file_name = os.path.basename(srt_path)
    srt_basename = os.path.splitext(srt_file_name)[0]

    # 创建一个文件夹，用于存放每个字幕的mp3 clips
    if not os.path.exists(os.path.join(tts_mp3_path, channel, srt_basename)):
        os.makedirs(os.path.join(tts_mp3_path, channel, srt_basename))

    # 生成字幕，并保存为mp3
    for sub_idx, subtitle in tqdm(enumerate(subtitles)):
        tts_success = False

        # 目标mp3 clip的路径
        mp3_dst_path = os.path.join(
            tts_mp3_path, channel, srt_basename, f"{sub_idx}.mp3"
        )

        # 如果文件已经存在，则跳过
        if os.path.exists(mp3_dst_path):
            print(f"{srt_basename} {sub_idx} already exists!")
            continue

        while not tts_success:
            tts_success = tts_ms(
                subtitle,
                clip_dst_path=os.path.join(
                    tts_mp3_path, channel, srt_basename, f"{sub_idx}.mp3"
                ),
                topic=topic,
            )
        print(f"{srt_basename} {sub_idx} tts done!")


def get_sorted_mp3_list(folder_path):
    # 获取文件夹内所有 MP3 文件
    mp3_files = [file for file in os.listdir(folder_path) if file.endswith(".mp3")]

    # 按照文件名的前缀从1到n进行排序
    sorted_mp3_files = sorted(mp3_files, key=lambda x: int(x.split(".")[0]))

    return sorted_mp3_files


def merge_tts_mp3():
    topic = "code"
    tts_mp3_path = f"/Users/donghaoliu/doc/video_material/tts_mp3/{topic}"
    merge_mp3_dst_path = "/Users/donghaoliu/doc/video_material/merge_tts_mp3/{topic}"
    zh_srt_path = f"/Users/donghaoliu/doc/video_material/zh_srt_nowarp/{topic}"

    if not os.path.exists(merge_mp3_dst_path):
        os.makedirs(merge_mp3_dst_path)

    all_channels = os.listdir(tts_mp3_path)
    # remove .DS_Store using list comprehension
    all_channels = [channel for channel in all_channels if channel != ".DS_Store"]

    for channel in all_channels:
        print(f"当前处理的频道是{channel}")
        all_mp3_folders = os.listdir(os.path.join(tts_mp3_path, channel))
        # remove .DS_Store using list comprehension
        all_mp3_folders = [
            mp3_folder for mp3_folder in all_mp3_folders if mp3_folder != ".DS_Store"
        ]
        for mp3_folder in all_mp3_folders:

            all_mp3 = get_sorted_mp3_list(
                os.path.join(tts_mp3_path, channel, mp3_folder)
            )

            srt_content = read_srt_file(
                os.path.join(zh_srt_path, channel, f"{mp3_folder}.srt")
            )
            ts_list, txt_list = parse_srt_with_re(srt_content)


def ts_to_duration(ts_list):
    duration_list = []
    for ts_str in ts_list:
        start_time_str, end_time_str = ts_str
        # convert from string to timedelta
        start_time_obj = time_str_to_obj(start_time_str)
        end_time_obj = time_str_to_obj(end_time_str)
        duration = end_time_obj - start_time_obj
        # convert from timedelta to seconds
        duration_seconds = duration.total_seconds()

        # append to the list
        duration_list.append(duration_seconds)
    return duration_list


if __name__ == "__main__":
    topic = "code"
    controller_tts(topic=topic)
    # controller_merge_single_mp3(topic)
