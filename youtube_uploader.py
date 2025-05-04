#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
YouTube 视频上传工具
-------------------
这个脚本用于将处理好的视频自动上传到 YouTube。

功能：
1. 从 merge_mp4_mp3.py 输出的目录获取对应语种的视频
2. 从 title_translator_multi_lang.py 生成的 JSON 文件中获取对应语种的标题
3. 自动处理关键词和视频描述的多语言翻译
4. 支持批量上传和断点续传
5. 使用不同语言频道对应的 OAuth 认证信息

使用方法：
  # 上传指定频道和语言的视频
  python youtube_uploader.py -c <channel> -l <language>

  # 上传特定文件
  python youtube_uploader.py -c <channel> -l <language> -f <filename>

  # 列出可用频道
  python youtube_uploader.py --list-channels

  # 列出指定频道的可用语言
  python youtube_uploader.py --list-languages <channel>

  # 使用自定义基础路径
  python youtube_uploader.py -c <channel> -l <language> --base-path <path>
"""

import os
import sys
import json
import time
import argparse
import platform
import httplib2
import glob
from tqdm import tqdm
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow
import http.client as httplib  # Python 3 compatible

# 语言映射
LANG_CODES = {"english": "en", "japanese": "ja", "korean": "ko", "vietnamese": "vi"}

LANG_TO_SECRET = {
    "english": "en.json",
    "japanese": "jp.json",
    "korean": "ko.json",
    "vietnamese": "vi.json",
}

# 语言关键词映射（将在后面通过函数翻译）
DEFAULT_KEYWORDS = (
    "#佛教 #佛家 #佛法 #佛學知識 #佛學智慧 #修心修行 #佛教文化 #禪悟人生 #傳統文化"
)

# 语言描述（将在后面通过函数翻译）
DEFAULT_DESCRIPTION = """重新认识"因果法则""空性""自性"的深刻含义。
学会放下焦虑，用佛家智慧化解情绪与烦恼。
在快节奏的生活中，找到属于自己的"禅意时刻"。"""


# 获取基础路径函数
def get_base_path():
    """根据操作系统类型返回对应的基础路径"""
    if platform.system() == "Darwin":  # Mac OS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# YouTube API 设置
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
RETRIABLE_EXCEPTIONS = (
    httplib2.HttpLib2Error,
    IOError,
    httplib.NotConnected,
    httplib.IncompleteRead,
    httplib.ImproperConnectionState,
    httplib.CannotSendRequest,
    httplib.CannotSendHeader,
    httplib.ResponseNotReady,
    httplib.BadStatusLine,
)
MAX_RETRIES = 10
MISSING_CLIENT_SECRETS_MESSAGE = """
警告: 请配置 OAuth 2.0 认证

要运行此脚本，您需要在以下位置创建 client_secrets.json 文件:
   %s

有关 client_secrets.json 文件格式的更多信息，请访问:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
"""

# 基础路径
BASE_PATH = get_base_path()

# 目录配置
VIDEO_BASE_DIR = f"{BASE_PATH}/mp4_with_audio"
TITLE_BASE_DIR = f"{BASE_PATH}/multi_lang_titles"
SECRET_DIR = "./secret_json"


# 获取认证服务
def get_authenticated_service(language, args):
    """根据语言获取已认证的YouTube服务"""
    # 根据语言选择对应的密钥文件
    client_secrets_file = os.path.join(
        SECRET_DIR, LANG_TO_SECRET.get(language.lower(), "jp.json")
    )

    if not os.path.exists(client_secrets_file):
        print(f"错误: {language} 语言的密钥文件不存在: {client_secrets_file}")
        return None

    # 创建认证流程
    flow = flow_from_clientsecrets(
        client_secrets_file,
        scope=YOUTUBE_UPLOAD_SCOPE,
        message=MISSING_CLIENT_SECRETS_MESSAGE % client_secrets_file,
    )

    # 存储认证信息
    storage_file = f"{language.lower()}-oauth2.json"
    storage = Storage(storage_file)
    credentials = storage.get()

    # 如果没有有效的认证信息，则运行认证流程
    if credentials is None or credentials.invalid:
        print(f"需要为 {language} 频道进行 YouTube 认证...")
        credentials = run_flow(flow, storage, args)

    # 构建 YouTube API 服务
    return build(
        YOUTUBE_API_SERVICE_NAME,
        YOUTUBE_API_VERSION,
        http=credentials.authorize(httplib2.Http()),
    )


# 翻译关键词
def translate_keywords(keywords, language):
    """将中文关键词翻译成目标语言"""
    # 不同语言的关键词映射
    translated_keywords = {
        "english": "#Buddhism #Dharma #BuddhistWisdom #Meditation #MindCultivation #BuddhistCulture #Zen #TraditionalCulture #SpiritualPractice",
        "japanese": "#仏教 #仏法 #仏教の知恵 #精神修行 #マインドフルネス #仏教文化 #禅 #伝統文化 #内なる平和",
        "korean": "#불교 #불법 #불교지혜 #명상 #마음수행 #불교문화 #선 #전통문화 #영적수행",
        "vietnamese": "#PhậtGiáo #PhápPhật #TríTuệPhậtGiáo #ThiềnĐịnh #TuTâm #VănHóaPhậtGiáo #Thiền #VănHóaTruyềnThống #ThựcHànhTâmLinh",
    }

    return translated_keywords.get(language.lower(), keywords)


# 翻译描述
def translate_description(description, language):
    """将中文描述翻译成目标语言"""
    # 不同语言的描述映射
    translated_description = {
        "english": """Rediscover the profound meanings of "Law of Cause and Effect", "Emptiness", and "Self-nature".
Learn to let go of anxiety and resolve emotions and troubles with Buddhist wisdom.
Find your own "Zen moment" in the fast-paced life.""",
        "japanese": """「因果の法則」「空性」「自性」の深い意味を再認識しましょう。
不安を手放し、仏教の知恵で感情や悩みを解消する方法を学びましょう。
忙しい日常の中で、自分だけの「禅の瞬間」を見つけましょう。""",
        "korean": """"인과법칙", "공성", "자성"의 심오한 의미를 재발견하세요.
불교 지혜로 불안을 내려놓고 감정과 번뇌를 해소하는 법을 배우세요.
바쁜 일상 속에서 나만의 "선(禪)의 순간"을 찾으세요.""",
        "vietnamese": """Tái khám phá ý nghĩa sâu sắc của "Luật nhân quả", "Tính không" và "Tự tính".
Học cách buông bỏ lo lắng và hóa giải cảm xúc, phiền não bằng trí tuệ Phật giáo.
Tìm thấy "khoảnh khắc Thiền" của riêng bạn trong cuộc sống nhịp điệu nhanh.""",
    }

    return translated_description.get(language.lower(), description)


# 上传视频
def upload_video(youtube, options):
    """上传视频到YouTube"""
    tags = None
    if options.keywords:
        tags = [tag.strip() for tag in options.keywords.split("#") if tag.strip()]

    body = dict(
        snippet=dict(
            title=options.title,
            description=options.description,
            tags=tags,
            categoryId=options.category,
        ),
        status=dict(privacyStatus=options.privacyStatus),
    )

    # 显示上传信息
    print(f"准备上传视频: {os.path.basename(options.file)}")
    print(f"标题: {options.title}")
    print(
        f"描述: {options.description[:50]}..."
        if len(options.description) > 50
        else f"描述: {options.description}"
    )
    print(f"标签: {options.keywords}")
    print(f"类别ID: {options.category}")
    print(f"隐私状态: {options.privacyStatus}")

    # 创建媒体上传对象
    media_file = MediaFileUpload(options.file, chunksize=-1, resumable=True)

    # 调用API的videos.insert方法创建并上传视频
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()), body=body, media_body=media_file
    )

    video_id = resumable_upload(insert_request, options)
    return video_id


# 可恢复的上传
def resumable_upload(insert_request, options=None):
    """可恢复的视频上传过程"""
    response = None
    error = None
    retry = 0

    print("开始上传...")

    while response is None:
        try:
            # 下一个上传块
            status, response = insert_request.next_chunk()

            # 显示上传进度
            if status:
                # 当status不为None时，表示上传正在进行中
                print(f"已上传 {int(status.progress() * 100)}%...")

            if response is not None:
                if "id" in response:
                    print(f"视频上传成功! 视频ID: {response['id']}")
                    print(f"YouTube链接: https://youtu.be/{response['id']}")
                    # 记录上传信息到日志
                    log_upload(response["id"], options)
                    return response["id"]
                else:
                    print(f"上传失败: {response}")
                    return None
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = f"可重试的HTTP错误 {e.resp.status}: {e.content}"
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = f"可重试的错误: {e}"

        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                print(f"超过最大重试次数 {MAX_RETRIES}")
                return None

            max_sleep = 2**retry
            sleep_seconds = max_sleep
            print(f"等待 {sleep_seconds} 秒后重试...")
            time.sleep(sleep_seconds)


# 记录上传信息
def log_upload(video_id, options=None):
    """记录已上传的视频信息"""
    log_dir = "./upload_log"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 按频道和语言记录
    if options:
        log_file = os.path.join(
            log_dir, f"upload_log_{options.channel}_{options.language}.txt"
        )
    else:
        log_file = os.path.join(log_dir, "upload_log.txt")

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    # 记录详细信息
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} - 上传成功: {video_id}\n")
        if options:
            f.write(f"  标题: {options.title}\n")
            f.write(f"  文件: {os.path.basename(options.file)}\n")
            f.write(f"  频道: {options.channel}\n")
            f.write(f"  语言: {options.language}\n")
            f.write(f"  链接: https://youtu.be/{video_id}\n")
        f.write("-" * 60 + "\n")


# 获取视频标题
def get_video_title(channel, video_name, language):
    """从title_translator_multi_lang.py生成的JSON获取对应语言的标题"""
    title_json_path = os.path.join(TITLE_BASE_DIR, channel, f"{video_name}.json")

    if not os.path.exists(title_json_path):
        print(f"警告: 找不到标题JSON文件: {title_json_path}")
        # 如果无法找到翻译，直接使用视频文件名作为标题
        return clean_filename_for_title(video_name)

    try:
        with open(title_json_path, "r", encoding="utf-8") as f:
            title_data = json.load(f)

        # 获取对应语言代码的标题
        lang_code = LANG_CODES.get(language.lower())
        if lang_code and lang_code in title_data and title_data[lang_code].strip():
            return title_data[lang_code]
        elif "original" in title_data and title_data["original"].strip():
            print(f"警告: 找不到 {language} 的标题翻译，使用原始标题")
            return title_data["original"]
        else:
            print(f"警告: 标题JSON文件中没有有效标题")
            return clean_filename_for_title(video_name)
    except Exception as e:
        print(f"读取标题文件时出错: {e}")
        return clean_filename_for_title(video_name)


# 清理文件名，使其适合作为标题
def clean_filename_for_title(filename):
    """清理文件名使其适合作为视频标题"""
    # 移除扩展名
    if "." in filename:
        filename = filename.rsplit(".", 1)[0]

    # 将下划线和连字符替换为空格
    filename = filename.replace("_", " ").replace("-", " ")

    # 首字母大写每个单词
    title = " ".join(word.capitalize() for word in filename.split())

    return title


# 处理单个视频上传
def process_video(youtube, channel, language, video_name, force=False):
    """处理单个视频的上传流程"""
    # 构建视频文件路径
    video_path = os.path.join(VIDEO_BASE_DIR, channel, language, f"{video_name}.mp4")

    # 检查视频文件是否存在
    if not os.path.exists(video_path):
        print(f"错误: 视频文件不存在: {video_path}")
        return False

    # 获取视频标题
    title = get_video_title(channel, video_name, language)

    # 获取翻译后的关键词和描述
    keywords = translate_keywords(DEFAULT_KEYWORDS, language)
    description = translate_description(DEFAULT_DESCRIPTION, language)

    # 创建选项对象
    class VideoOptions:
        pass

    options = VideoOptions()
    options.file = video_path
    options.title = title
    options.description = description
    options.category = "22"  # People & Blogs
    options.keywords = keywords
    options.privacyStatus = "public"  # 设置为公开

    # 添加频道和语言信息（用于日志记录）
    options.channel = channel
    options.language = language
    options.video_name = video_name

    # 上传视频
    video_id = upload_video(youtube, options)
    return video_id is not None


# 处理频道和语言下的所有视频
def process_channel_language(
    youtube, channel, language, specific_file=None, force=False
):
    """处理指定频道和语言的所有视频"""
    # 构建视频目录路径
    video_dir = os.path.join(VIDEO_BASE_DIR, channel, language)

    if not os.path.exists(video_dir):
        print(f"错误: 视频目录不存在: {video_dir}")
        return

    # 获取要处理的视频文件
    if specific_file:
        # 处理单个指定文件
        file_base = (
            specific_file.rsplit(".", 1)[0] if "." in specific_file else specific_file
        )
        video_files = [os.path.join(video_dir, f"{file_base}.mp4")]
        if not os.path.exists(video_files[0]):
            print(f"错误: 指定的视频文件不存在: {video_files[0]}")
            return
    else:
        # 处理目录中的所有MP4文件
        video_files = glob.glob(os.path.join(video_dir, "*.mp4"))

    if not video_files:
        print(f"在 {video_dir} 中未找到任何MP4文件")
        return

    print(f"在 {video_dir} 中找到 {len(video_files)} 个视频文件")

    # 使用进度条处理视频上传
    with tqdm(total=len(video_files), desc=f"上传 {channel}/{language} 视频") as pbar:
        success_count = 0
        for video_file in video_files:
            video_name = os.path.basename(video_file).rsplit(".", 1)[0]
            print(f"\n处理视频: {video_name}")

            if process_video(youtube, channel, language, video_name, force):
                success_count += 1

            pbar.update(1)

    print(f"上传完成: {success_count}/{len(video_files)} 个视频成功上传")


# 列出可用频道
def list_channels():
    """列出所有可用频道"""
    if not os.path.exists(VIDEO_BASE_DIR):
        print(f"错误: 视频基础目录不存在: {VIDEO_BASE_DIR}")
        return []

    channels = [
        d
        for d in os.listdir(VIDEO_BASE_DIR)
        if os.path.isdir(os.path.join(VIDEO_BASE_DIR, d))
    ]

    if not channels:
        print("未找到任何频道目录")
        return []

    print("可用频道列表:")
    for channel in sorted(channels):
        print(f"- {channel}")

    return sorted(channels)


# 列出频道下的语言
def list_languages(channel):
    """列出指定频道的所有可用语言"""
    channel_dir = os.path.join(VIDEO_BASE_DIR, channel)

    if not os.path.exists(channel_dir):
        print(f"错误: 频道目录不存在: {channel_dir}")
        return []

    languages = [
        d
        for d in os.listdir(channel_dir)
        if os.path.isdir(os.path.join(channel_dir, d))
    ]

    if not languages:
        print(f"在频道 {channel} 中未找到任何语言目录")
        return []

    print(f"频道 {channel} 的可用语言列表:")
    for language in sorted(languages):
        print(f"- {language}")

    return sorted(languages)


# 解析命令行参数
def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="上传视频到YouTube")
    parser.add_argument("-c", "--channel", help="指定要处理的频道名")
    parser.add_argument("-l", "--language", help="指定要处理的语言")
    parser.add_argument("-f", "--file", help="指定要处理的文件名")
    parser.add_argument("--list-channels", action="store_true", help="列出所有可用频道")
    parser.add_argument(
        "--list-languages", metavar="CHANNEL", help="列出指定频道的所有可用语言"
    )
    parser.add_argument("--force", action="store_true", help="强制重新上传已上传的文件")
    parser.add_argument("--base-path", help="指定自定义的基础路径，覆盖默认路径")
    parser.add_argument(
        "--show-multilingual", action="store_true", help="显示多语言内容"
    )

    # 添加OAuth2客户端所需的参数
    parser.add_argument(
        "--noauth_local_webserver",
        action="store_true",
        help="不使用本地Web服务器进行认证",
    )

    # 添加logging_level参数，用于OAuth2客户端
    parser.add_argument(
        "--logging_level",
        default="ERROR",
        help="设置日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )

    # 添加auth_host_port参数，用于OAuth2客户端
    parser.add_argument(
        "--auth_host_port",
        nargs="*",
        default=[8080, 8090],
        type=int,
        help="认证服务器的端口",
    )

    # 添加auth_host_name参数，用于OAuth2客户端
    parser.add_argument(
        "--auth_host_name",
        default="localhost",
        help="认证服务器的主机名",
    )

    return parser.parse_args()


# 显示多语言内容
def show_multilingual_content():
    """显示所有语言的关键词和描述，方便用户查看"""
    print("\n多语言内容预览：")
    print("-" * 80)

    for lang in ["english", "japanese", "korean", "vietnamese"]:
        print(f"\n--- {lang.capitalize()} ---")

        # 显示关键词
        keywords = translate_keywords(DEFAULT_KEYWORDS, lang)
        print(f"关键词: {keywords}")

        # 显示描述
        description = translate_description(DEFAULT_DESCRIPTION, lang)
        print(f"描述:\n{description}")

    print("-" * 80)


# 主函数
def main():
    """主函数"""
    args = parse_args()

    # 如果用户请求显示多语言内容
    if args.show_multilingual:
        show_multilingual_content()
        return

    # 如果指定了自定义基础路径，则覆盖默认路径
    global VIDEO_BASE_DIR, TITLE_BASE_DIR
    if args.base_path:
        custom_base_path = args.base_path
        VIDEO_BASE_DIR = f"{custom_base_path}/mp4_with_audio"
        TITLE_BASE_DIR = f"{custom_base_path}/multi_lang_titles"
        print(f"使用自定义基础路径: {custom_base_path}")
    else:
        print(f"使用默认基础路径: {BASE_PATH}")

    # 处理列表命令
    if args.list_channels:
        list_channels()
        return

    if args.list_languages:
        list_languages(args.list_languages)
        return

    # 检查必要参数
    if not args.channel:
        print("错误: 必须指定频道名 (-c/--channel)")
        return

    if not args.language:
        print("错误: 必须指定语言 (-l/--language)")
        return

    # 获取认证的YouTube服务
    youtube = get_authenticated_service(args.language, args)
    if not youtube:
        print(f"错误: 无法为语言 {args.language} 获取认证服务")
        return

    # 处理上传
    process_channel_language(
        youtube, args.channel, args.language, args.file, args.force
    )

    print("上传流程完成！")


if __name__ == "__main__":
    main()
