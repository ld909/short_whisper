from pyannote.audio import Pipeline
import os


# def set_clash_proxy():

#     # 设置环境变量
#     os.environ["http_proxy"] = "http://127.0.0.1:7899"
#     os.environ["https_proxy"] = "http://127.0.0.1:7899"
#     # os.environ["all_proxy"] = "socks5://127.0.0.1:7891"
#     print("成功设定clash环境proxy...")


# def unset_clash_proxy():
#     # 删除环境变量
#     os.environ.pop("http_proxy", None)
#     os.environ.pop("https_proxy", None)
#     os.environ.pop("all_proxy", None)
#     print("成功取消clash环境proxy...")


def test_code():
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token="YOUR_TOKEN_PLACEHOLDER",
    )

    # send pipeline to GPU (when available)
    import torch

    pipeline.to(torch.device("cuda"))

    # apply pretrained pipeline
    diarization = pipeline("./tt.mp3", num_speakers=2)

    # print the result
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        print(f"start={turn.start:.1f}s stop={turn.end:.1f}s speaker_{speaker}")
    # start=0.2s stop=1.5s speaker_0
    # start=1.8s stop=3.9s speaker_1
    # start=4.2s stop=5.7s speaker_0
    # ...


if __name__ == "__main__":
    # set_clash_proxy()
    # try to ping google.com for 10 seconds
    # os.system("ping -c 10 google.com")
    test_code()
    # unset_clash_proxy()
