"""
使用 faster-whisper 高效地将 MP3 文件批量转录为 SRT 字幕文件。

本脚本主要功能是遍历指定主题（Topic）下的所有MP3音频文件，
利用 `faster-whisper` 的 `large-v2` 模型进行语音识别，并生成对应的 SRT 格式字幕文件。
为了达到最佳性能，脚本默认使用 CUDA 加速，并采用批处理推理（Batched Inference）。

主要特性:
- 高性能转录: 基于 faster-whisper 和 CUDA (float16) 实现。
- VAD 语音活动检测: 自动过滤静音片段，提高字幕质量。
- 批处理: `BatchedInferencePipeline` 加速处理多个文件。
- 代理支持: 内置代理设置功能，可加速模型文件的下载。
- 断点续传: 自动跳过已生成 SRT 文件的 MP3，方便中断后继续。
- 错误处理: 记录并报告转录失败的文件列表。

输入文件夹结构:
/home/dhl/Downloads/27c99b155e2448f9a91dbf31d79f8d6f/video/mp3/mp3/{topic}/{channel_name}/{video_id}.mp3
- `{topic}`: 主题名称，例如 'code'。
- `{channel_name}`: 频道或分类的子目录。
- `{video_id}.mp3`: 音频文件。

输出文件夹结构:
/home/dhl/Documents/video_materials/format_srt/{topic}/{channel_name}/{video_id}.srt
- 字幕文件将与输入文件保持相同的目录结构和基本文件名。

使用说明:
1.  确保已安装所有依赖 (包括 faster-whisper, torch, Cuda等)。
2.  根据需要修改 `transcribemp3` 函数中的 `mp3_abs_path` 和 `dst_srt_abs_path` 变量，指向你的实际路径。
3.  在文件末尾的 `if __name__ == "__main__":` 代码块中：
    a. 设置 `topic` 为你需要处理的主题名称。
    b. 取消该代码块的注释。
4.  运行脚本:
    ```bash
    python buda/mp3toscripts_faster.py
    ```
"""

import os
import requests


# 设置代理环境变量，加速Whisper模型下载
def setup_proxy():
    """
    设置代理环境变量以加速模型下载
    根据截图中的代理设置，支持多种代理端口
    """
    # 根据截图中的代理端口配置
    proxy_configs = [
        {"name": "混合代理", "port": "7897"},
        {"name": "HTTP(S)代理", "port": "7899"},
        {"name": "SOCKS代理", "port": "7898"},
    ]

    proxy_host = "127.0.0.1"

    # 尝试不同的代理端口，找到可用的
    for config in proxy_configs:
        proxy_url = f"http://{proxy_host}:{config['port']}"
        print(f"尝试使用{config['name']}端口 {config['port']}...")

        try:
            # 测试代理连接
            test_response = requests.get(
                "https://httpbin.org/ip",
                proxies={"http": proxy_url, "https": proxy_url},
                timeout=5,
            )
            if test_response.status_code == 200:
                print(f"✓ {config['name']}连接成功！")

                # 设置环境变量
                os.environ["HTTP_PROXY"] = proxy_url
                os.environ["HTTPS_PROXY"] = proxy_url
                os.environ["http_proxy"] = proxy_url
                os.environ["https_proxy"] = proxy_url

                # 设置不使用代理的地址（本地地址）
                os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"
                os.environ["no_proxy"] = "localhost,127.0.0.1,::1"

                print(f"已设置代理: {proxy_url}")
                return True

        except Exception as e:
            print(f"✗ {config['name']}连接失败: {e}")
            continue

    print("⚠️  所有代理端口都无法连接，将使用直连方式")
    print("如果下载速度较慢，请检查代理软件是否正常运行")
    return False


# 在导入faster_whisper之前设置代理
# setup_proxy()  # 代理功能已关闭，需要时取消注释

from faster_whisper import WhisperModel, BatchedInferencePipeline
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
    """使用faster-whisper large-v2模型生成转录文本"""
    # 使用CUDA模式获得最佳性能
    print("🚀 使用CUDA模式运行faster-whisper批处理管道，获得最佳转录性能")
    model = WhisperModel("large-v2", device="cuda", compute_type="float16")
    batched_model = BatchedInferencePipeline(model=model)

    print(f"开始转录 {mp3_path}...")

    # 使用批处理管道进行转录
    segments, info = batched_model.transcribe(
        mp3_path,
        word_timestamps=True,
        initial_prompt="你好，欢迎来到我的佛法课程。佛法无边。",
        vad_filter=True,  # 开启VAD过滤以提高质量
        vad_parameters=dict(min_silence_duration_ms=500),
        beam_size=5,
        batch_size=8,
    )

    print(
        f"转录完成，检测到的语言: {info.language} (置信度: {info.language_probability:.2f})"
    )

    ts_list = []
    txt_list = []

    for segment in segments:
        start_time = float_to_srt_timestamp(segment.start)
        end_time = float_to_srt_timestamp(segment.end)
        text = segment.text.strip()

        if len(text) == 0:
            continue

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


def transcribemp3(topic):
    """读入mp3文件，使用faster-whisper模型，转换为srt文件"""
    mp3_abs_path = f"/home/dhl/Downloads/27c99b155e2448f9a91dbf31d79f8d6f/video/mp3/mp3/{topic}"  # fill in the absolute path of the mp3 folder
    dst_srt_abs_path = f"/home/dhl/Documents/video_materials/format_srt/{topic}"  # fill in the absolute path of the srt folder

    # check if the dst_srt_abs_path exists, if not create it
    if not os.path.exists(dst_srt_abs_path):
        os.makedirs(dst_srt_abs_path)

    all_channels = os.listdir(mp3_abs_path)
    # 排除mac产生的点开头的文件
    all_channels = [channel for channel in all_channels if not channel.startswith(".")]

    # 用于记录转录失败的文件
    failed_files = []

    # read all mp3 files in the folder
    for single_channel in all_channels:
        # read all mp3 files in the folder
        for mp3_file in tqdm(os.listdir(os.path.join(mp3_abs_path, single_channel))):
            if mp3_file.endswith(".mp3"):
                # check if base_name +'.srt' exists in the dst_srt
                base_name = os.path.splitext(mp3_file)[0]

                dst_srt = os.path.join(
                    dst_srt_abs_path, single_channel, base_name + ".srt"
                )
                # check if os.path.join(dst_srt_abs_path, single_channel) exists
                if not os.path.exists(os.path.join(dst_srt_abs_path, single_channel)):
                    os.makedirs(os.path.join(dst_srt_abs_path, single_channel))

                # check if the srt file exists, if it does, skip
                if os.path.exists(dst_srt):
                    print(f"文件{dst_srt}存在，跳过...")
                    continue

                print("processing:", base_name + ".mp3", f"位于频道{single_channel}")
                mp3_path = os.path.join(mp3_abs_path, single_channel, mp3_file)

                try:
                    ts_list, txt_list = mp3totxt(mp3_path)
                    # get base name without extension
                    print(f"保存srt文件到{dst_srt}...")
                    save_srt(ts_list, txt_list, dst_srt)
                    print(f"✓ 成功转录: {mp3_file}")
                except Exception as e:
                    print(f"✗ 转录失败: {mp3_file}, 错误: {str(e)}")
                    failed_files.append(f"{single_channel}/{mp3_file}")

    # 在最后打印所有失败的文件
    if failed_files:
        print("\n" + "=" * 50)
        print(f"转录失败的文件 ({len(failed_files)} 个):")
        print("=" * 50)
        for failed_file in failed_files:
            print(f"- {failed_file}")
        print("=" * 50)
    else:
        print("\n🎉 所有文件都转录成功了！")


# if __name__ == "__main__":
#     topic = "code"
#     transcribemp3(topic=topic)
