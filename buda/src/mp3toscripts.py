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
                'https://httpbin.org/ip', 
                proxies={'http': proxy_url, 'https': proxy_url},
                timeout=5
            )
            if test_response.status_code == 200:
                print(f"✓ {config['name']}连接成功！")
                
                # 设置环境变量
                os.environ['HTTP_PROXY'] = proxy_url
                os.environ['HTTPS_PROXY'] = proxy_url
                os.environ['http_proxy'] = proxy_url
                os.environ['https_proxy'] = proxy_url
                
                # 设置不使用代理的地址（本地地址）
                os.environ['NO_PROXY'] = 'localhost,127.0.0.1,::1'
                os.environ['no_proxy'] = 'localhost,127.0.0.1,::1'
                
                print(f"已设置代理: {proxy_url}")
                return True
                
        except Exception as e:
            print(f"✗ {config['name']}连接失败: {e}")
            continue
    
    print("⚠️  所有代理端口都无法连接，将使用直连方式")
    print("如果下载速度较慢，请检查代理软件是否正常运行")
    return False

# 在导入whisper之前设置代理
setup_proxy()

import whisper
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
    """this function using whisper larger v3 turbo model to generate pure transcriptions"""
    model = whisper.load_model("large-v2")

    print(f"开始转录 {mp3_path}...")
    result = model.transcribe(
        mp3_path,
        word_timestamps=True,
        initial_prompt="你好，欢迎来到我的佛法课程。佛法无边。",
        verbose=True,  # 添加verbose=True参数来显示转换进度
    )
    print("转录完成")
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


def transcribemp3(topic):
    """读入mp3文件，使用openai Whisper模型，转换为srt文件"""
    mp3_abs_path = f"/home/dhl/Downloads/27c99b155e2448f9a91dbf31d79f8d6f/video/mp3/mp3/{topic}"  # fill in the absolute path of the mp3 folder
    dst_srt_abs_path = f"/home/dhl/Documents/video_materials/format_srt/{topic}"  # fill in the absolute path of the srt folder

    # check if the dst_srt_abs_path exists, if not create it
    if not os.path.exists(dst_srt_abs_path):
        os.makedirs(dst_srt_abs_path)

    all_channels = os.listdir(mp3_abs_path)
    # remove the .DS_Store file using list comprehension
    all_channels = [channel for channel in all_channels if channel != ".DS_Store"]

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
                ts_list, txt_list = mp3totxt(mp3_path)
                # get base name without extension
                print(f"保存srt文件到{dst_srt}...")
                # save_srt(ts_list, txt_list, dst_srt)


# if __name__ == "__main__":
#     topic = "code"
#     transcribemp3(topic=topic)
