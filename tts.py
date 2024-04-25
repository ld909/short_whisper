import requests
from srt_format import read_srt_file, parse_srt_with_re
import os
from tqdm import tqdm


def tts(content_str, mp3_dst_path):
    group_id = "1725312458689614655"
    api_key = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiLliJjkuJzmmIoiLCJVc2VyTmFtZSI6IuWImOS4nOaYiiIsIkFjY291bnQiOiIiLCJTdWJqZWN0SUQiOiIxNzI1MzEyNDU4Njk4MDAzMjYzIiwiUGhvbmUiOiIxODU4MzM4MTAzNiIsIkdyb3VwSUQiOiIxNzI1MzEyNDU4Njg5NjE0NjU1IiwiUGFnZU5hbWUiOiIiLCJNYWlsIjoiIiwiQ3JlYXRlVGltZSI6IjIwMjQtMDQtMjMgMjA6NTU6MTQiLCJpc3MiOiJtaW5pbWF4In0.yv7qeUESVBLpi67g-BvEhFE0Fl9j13VUF0NddFJFAlauxZeTt1n8uaRSba__HGoLrDz_JgbWYFZPt1FEIbeYZQaDuTYJw68qbSTnSuUZCCRX7VjGeQ6x3tiWA7LlpF6hbzsUsiKRo2gT95Q3TQVKQJvpZszUrPlr6TODsrPycgoTaSbZ_gUwgY97ZHcJmSzbZyZEcsDyHe5hw_JYcGeO-fh8bsxZXrXHwFB1doR5YT3pVm8B24O_QMx2co3Z1jSh6ahJO1ctCvC0ff6Fpo9oZ4bKUbUUtcRm9iMeCwCx4LMaq80z3TnOKM22i5CTZxOfuOLjiCxD4Sp4Aq4-gDcSkA"

    url = f"https://api.minimax.chat/v1/text_to_speech?GroupId={group_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "voice_id": "male-qn-jingying-jingpin",
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


def controller_tts():
    topic = "code"
    zh_nowarp_srt_path = f"/Users/donghaoliu/doc/video_material/zh_srt_nowarp/{topic}"
    tts_mp3_path = f"/Users/donghaoliu/doc/video_material/tts_mp3/{topic}"

    all_channels = os.listdir(zh_nowarp_srt_path)
    # remove .DS_Store using list comprehension
    all_channels = [channel for channel in all_channels if channel != ".DS_Store"]
    for channel in all_channels:
        print(f"当前处理的频道是{channel}")
        all_srt = os.listdir(os.path.join(zh_nowarp_srt_path, channel))

        # remove .DS_Store using list comprehension
        all_srt = [srt for srt in all_srt if srt != ".DS_Store"]

        # create tts_mp3_path
        if not os.path.exists(os.path.join(tts_mp3_path, channel)):
            os.makedirs(os.path.join(tts_mp3_path, channel))

        for srt_name in all_srt:
            srt_path = os.path.join(zh_nowarp_srt_path, channel, srt_name)
            srt_content = read_srt_file(srt_path)
            timestamps, subtitles = parse_srt_with_re(srt_content)
            srt_basename = os.path.splitext(srt_name)[0]

            if not os.path.exists(os.path.join(tts_mp3_path, channel, srt_basename)):
                os.makedirs(os.path.join(tts_mp3_path, channel, srt_basename))

            # 生成字幕，并保存为mp3
            for sub_idx, subtitle in tqdm(enumerate(subtitles)):
                tts_success = False
                mp3_dst_path = os.path.join(
                    tts_mp3_path, channel, srt_basename, f"{sub_idx}.mp3"
                )
                # if mp3 already exists, skip
                if os.path.exists(mp3_dst_path):
                    print(f"{srt_basename} {sub_idx} already exists!")
                    continue

                while not tts_success:
                    tts_success = tts(
                        subtitle,
                        os.path.join(
                            tts_mp3_path, channel, srt_basename, f"{sub_idx}.mp3"
                        ),
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

            all_mp3s = get_sorted_mp3_list(
                os.path.join(tts_mp3_path, channel, mp3_folder)
            )

            srt_content = read_srt_file(
                os.path.join(zh_srt_path, channel, f"{mp3_folder}.srt")
            )
            ts_list, txt_list = parse_srt_with_re(srt_content)
            


def controller_merge_single_mp3():
    topic = "code"
    zh_nowarp_srt_path = f"/Users/donghaoliu/doc/video_material/zh_srt_nowarp/{topic}"
    merge_mp3_dst_path = "/Users/donghaoliu/doc/video_material/merge_mp3/{topic}"
    if not os.path.exists(merge_mp3_dst_path):
        os.makedirs(merge_mp3_dst_path)
    tts_mp3_path = f"/Users/donghaoliu/doc/video_material/tts_mp3/{topic}"

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
            print(f"当前处理的文件夹是{mp3_folder}")
            all_mp3_path = os.listdir(os.path.join(tts_mp3_path, channel, mp3_folder))
            all_mp3 = get_sorted_mp3_list(all_mp3_path)

            # read srt file
            single_srt_path = os.path.join(
                zh_nowarp_srt_path, channel, f"{mp3_folder}.srt"
            )

            srt_content = read_srt_file(single_srt_path)
            ts_list, txt_list = parse_srt_with_re(srt_content)

            # 计算每个srt的duration，如果mp3的duration和srt的duration不一致，就需要调整，如果mp3 duraion <= srt duration，就不需要调整,
            # 如果mp3 duration > srt duration，就需要对mp3进行加速，让mp3 duration = srt duration
            current_mp3_duration = None


if __name__ == "__main__":
    controller_tts()
