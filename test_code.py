import json


def update_log(log_key, platform, date_time_str):
    """更新日志文件，记录上传时间和平台。"""

    # 读取日志文件
    upload_log = {}

    if log_key not in upload_log:
        upload_log[log_key] = {"platforms": [platform], "upload_time": [date_time_str]}
    else:
        # add the platform to the platforms list
        upload_log[log_key]["platforms"].append(platform)

    print("更新日志：", upload_log)

    # 使用 ensure_ascii=False 和 indent=4 参数
    json_data = json.dumps(upload_log, ensure_ascii=False, indent=4)

    # 将 JSON 数据写入文件
    with open(
        "/Users/donghaoliu/doc/short_whisper/upload_log/upload_log.json",
        "w",
        encoding="utf-8",
    ) as file:
        file.write(json_data)


logkey = "a~~~b~~~Build a Stopwatch using React in 20 minutes! ⏱.mp4"
platform = "douyin"
date_time_str = "2021-08-01-12-00"
update_log(logkey, platform, date_time_str)
