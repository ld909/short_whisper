import yt_dlp
import os


def get_original_title(video_id):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}", download=False
            )
            return info["title"]
        except Exception as e:
            print(f"获取标题时出错: {str(e)}")
            return None


def set_clash_proxy():

    # 设置环境变量
    os.environ["http_proxy"] = "http://127.0.0.1:7897"
    os.environ["https_proxy"] = "http://127.0.0.1:7897"
    # os.environ["all_proxy"] = "socks5://127.0.0.1:7891"
    print("成功设定clash环境proxy...")


def unset_clash_proxy():
    # 删除环境变量
    os.environ.pop("http_proxy", None)
    os.environ.pop("https_proxy", None)
    # os.environ.pop("all_proxy", None)
    print("成功取消clash环境proxy...")


# 使用示例
video_id = "dQw4w9WgXcQ"
set_clash_proxy()
original_title = get_original_title(video_id)
print(f"原始标题: {original_title}")
unset_clash_proxy()
