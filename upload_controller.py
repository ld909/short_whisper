import os
import json
from datetime import datetime, timedelta
from short.publish_douyin import upload_douyin_video
from short.publish_kuaishou import publish_kuaishou_video
from short.publish_weixin import upload_weixin_video


def read_upload_log():
    """读取上传日志文件，返回一个字典。"""
    log_path = "./upload_log/upload_log.json"
    if not os.path.exists(log_path):
        return {}
    return json.load(open(log_path))


def get_the_latest_upload_time(upload_log):
    """返回最近上传的时间，datetime格式"""
    latest_time = datetime(1900, 1, 1, 0, 0)
    # get all keys from upload_log
    all_keys = upload_log.keys()
    for key in all_keys:
        upload_time_list = upload_log[key]["upload_time"]
        upload_time_str = upload_time_list[0]
        # convert upload time str from 'year-month-day-hour-min' to datetime
        upload_time = datetime.strptime(upload_time_str, "%Y-%m-%d-%H-%M")

        # 得到最临近上传时间
        if upload_time > latest_time:
            latest_time = upload_time

    return latest_time


def update_log(log_key, platform, date_time_str):
    """更新日志文件，记录上传时间和平台。"""

    # 读取日志文件
    upload_log = read_upload_log()

    if log_key not in upload_log:
        upload_log[log_key] = {"platforms": [platform], "upload_time": [date_time_str]}
    else:
        # add the platform to the platforms list
        upload_log[log_key]["platforms"].append(platform)

    # print("更新日志：", upload_log)

    # 使用 ensure_ascii=False 和 indent=4 参数
    json_data = json.dumps(upload_log, ensure_ascii=False, indent=4)

    # 将 JSON 数据写入文件
    with open(
        "/Users/donghaoliu/doc/short_whisper/upload_log/upload_log.json",
        "w",
        encoding="utf-8",
    ) as file:
        file.write(json_data)


def next_time_point(current_time, chunk_split):
    """根据当前时间，返回下一个视频上传时间。"""

    # 开始时间是早上6点
    start_hour = 6
    # 结束时间是晚上22点
    end_hour = 22

    # 一共时间间隔
    time_gap = (end_hour - start_hour) / chunk_split

    # 四舍五入到最近的整数
    time_gap = round(time_gap)
    time_gap = int(time_gap)

    # 计算从6点开始的所有时间点,包括6点和22点
    all_time_points = [start_hour + i * time_gap for i in range(chunk_split + 1)]

    # 如果当前时间小于当前时间
    if current_time < datetime.now():
        # 返回当前时间的明早6点
        next_time = datetime.now().replace(
            hour=6, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)

    # 如果当前时间在所有时间点之前,除开最后一个时间点
    elif current_time > datetime.now() and current_time.hour in all_time_points[:-1]:
        next_time = current_time + timedelta(hours=time_gap)

    # 如果当前时间是最后一个时间点，设定下一个时间是明天早上6点
    elif current_time > datetime.now() and current_time.hour == all_time_points[-1]:
        next_time = current_time.replace(
            hour=6, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)

    return next_time


def read_channels_from_ref_json(topic):
    """读取ref.json文件，返回所有的channel名称。"""
    ref_json_path = f"/Users/donghaoliu/doc/video_material/publish_ref/{topic}/ref.json"
    ref_dict = json.load(open(ref_json_path))
    return ref_dict.keys()


def load_ref_json(topic):
    ref_json_path = f"/Users/donghaoliu/doc/video_material/publish_ref/{topic}/ref.json"
    return json.load(open(ref_json_path))


def get_upload_time(uploaded_platforms, upload_log, log_key, topic):
    """根据上传情况，返回下一次上传的时间。"""
    if 0 < len(uploaded_platforms) < 3:
        #  "部分上传"
        print("部分上传")
        upload_time_list = upload_log[log_key]["upload_time"]
        # get all keys from upload_time_dict
        upload_time_str = upload_time_list[0]
        # convert upload time str from 'year-month-day-hour-min' to datetime
        upload_time_obj = datetime.strptime(upload_time_str, "%Y-%m-%d-%H-%M")

    else:
        # "全部上传" 或从未上传
        partial_upload_time_obj = get_the_latest_upload_time(upload_log)
        print(
            "最新已上传的视频上传时间：",
            partial_upload_time_obj.strftime("%Y-%m-%d %H:%M"),
        )

        if topic == "code":
            split_chunk = 12
        elif topic == "mama":
            split_chunk == 6

        # 得到下一个视频上传时间
        upload_time_obj = next_time_point(partial_upload_time_obj, split_chunk)

    return upload_time_obj


def get_uploaded_mp4s():
    log_dict = read_upload_log()

    # 得到所有keys，作为一个list
    all_keys = log_dict.keys()

    upload_dict = {}
    for single_key in all_keys:
        topic, channel, mp4_name = single_key.split("~~~~")
        print(f"主题: {topic}, 频道: {channel}, mp4文件名: {mp4_name}")

        # 如果topic不在upload_dict的key中，添加topic
        if topic not in upload_dict:
            upload_dict[topic] = {}
        # 如果topic在upload_dict的key中，添加channel
        else:
            # 添加channel
            if channel not in upload_dict[topic]:
                upload_dict[topic][channel] = {}
            # 如果channel在upload_dict的key中，添加mp4_name对应的平台
            else:
                uploaded_platforms = log_dict[single_key]["platforms"]
                # 如果channel在upload_dict的key中，添加mp4_name对应的平台
                upload_dict[topic][channel][mp4_name] = uploaded_platforms


def upload_all_platforms(topic):
    # zh_mp4_path作为上传视频的路径读取依赖
    zh_mp4_path = "/Volumes/dhl/ytb-videos/tts_mp4"
    zh_title_path = "/Users/donghaoliu/doc/video_material/zh_title"
    zh_tags = "/Users/donghaoliu/doc/video_material/zh_tag"
    thumbnail_vertical_path = "/Users/donghaoliu/doc/video_material/thumbnail_vertical"
    thumbnail_horizontal_path = (
        "/Users/donghaoliu/doc/video_material/thumbnail_horizontal"
    )
    # ref_dict = load_ref_json(topic)
    # # get all channels from the ref.json file
    # channels = read_channels_from_ref_json(topic)

    channels = os.listdir(os.path.join(zh_mp4_path, topic))
    # remove .DS_Store using list comprehension
    channels = [channel for channel in channels if channel != ".DS_Store"]

    for channel in channels:
        # get all mp4 files from the ref_dict
        all_mp4 = os.listdir(os.path.join(zh_mp4_path, topic, channel))
        # remove .DS_Store using list comprehension
        all_mp4 = [mp4 for mp4 in all_mp4 if mp4 != ".DS_Store"]

        for mp4_single in all_mp4:

            upload_log = read_upload_log()

            log_key = f"{topic}~~~~{channel}~~~~{mp4_single}"
            if log_key in upload_log:
                uploaded_platforms = upload_log[log_key]["platforms"]
            else:
                uploaded_platforms = []

            # if len(uploaded_platforms) == 3:
            #     continue
            if "douyin" in uploaded_platforms and "kuaishou" in uploaded_platforms:
                print(f"mp4 {mp4_single} 已经上传到抖音和快手，跳过...")
                continue

            # preapre the video and upload
            # ref_mp4 = ref_dict[channel][mp4_single]
            # basename = mp4_single
            base_name_prefix = os.path.splitext(mp4_single)[0]

            # video path
            video_path = os.path.join(zh_mp4_path, topic, channel, mp4_single)

            print("上传视频路径：", video_path)

            # read zh title from the txt file
            video_zh_title_txt_path = os.path.join(
                zh_title_path, topic, channel, base_name_prefix + ".txt"
            )

            if "_clip_" in mp4_single:
                # extract the clip id
                mp4_single_prefix = os.path.splitext(mp4_single)[0]
                clip_id = mp4_single_prefix.split("_clip_")[1]
                video_title_zh = (
                    open(video_zh_title_txt_path).read().strip() + f"{clip_id}"
                )
            else:
                video_title_zh = open(video_zh_title_txt_path).read().strip()
            print("视频标题：", video_title_zh)

            # read zh tags from the txt file
            video_zh_tags_txt_path = os.path.join(
                zh_tags, topic, channel, base_name_prefix + ".txt"
            )
            video_tags_zh_lines = open(video_zh_tags_txt_path).readlines()

            # convert list to str and add # in front of each tag
            video_tags_zh_str = (
                " ".join(["#" + tag.strip() for tag in video_tags_zh_lines]) + " "
            )
            print(f"视频标签：{video_tags_zh_str}")

            # thumbnail path
            thunbnail_basename = os.path.splitext(mp4_single)[0]
            thumbnail_png_vertical = os.path.join(
                thumbnail_vertical_path,
                topic,
                channel,
                thunbnail_basename + ".png",
            )

            # 微信使用横版缩略图
            # thumbnail_png_horizontal = os.path.join(
            #     thumbnail_horizontal_path,
            #     topic,
            #     channel,
            #     thunbnail_basename + ".png",
            # )

            # get the upload time
            upload_time_obj = get_upload_time(
                uploaded_platforms, upload_log, log_key, topic
            )
            print(
                "获取下一个视频上传时间：", upload_time_obj.strftime("%Y-%m-%d %H:%M")
            )

            # 如果upload_time_obj超过当下北京时间七天，结束整个程序
            if upload_time_obj > datetime.now() + timedelta(days=7):
                print("上传时间超过7天，结束上传程序...")
                break

            if "douyin" not in uploaded_platforms:
                print("uploading to douyin...")

                # convert upload time to str to format 'year-month-day hour:min'
                upload_time_str = upload_time_obj.strftime("%Y-%m-%d %H:%M")

                # upload to douyin
                upload_douyin_video(
                    video_path,
                    video_title_zh,
                    video_tags_zh_str,
                    thumbnail_png_vertical,
                    upload_time_str,
                )

                # update the log
                update_log(
                    log_key, "douyin", upload_time_obj.strftime("%Y-%m-%d-%H-%M")
                )
                print("douyin上传完成,已更新日志...")
                print("*" * 50)

            if "kuaishou" not in uploaded_platforms:
                print("uploading to kuaishou...")
                title_add_description = (
                    video_title_zh.replace("#", "sharp") + " " + video_tags_zh_str
                )

                # convert upload time to str to format '2024-04-21 04:03:00', 'year-month-day hour:min:sec'
                kuaishou_time_str = upload_time_obj.strftime("%Y-%m-%d %H:%M:00")

                # upload to kuaishou
                publish_kuaishou_video(
                    video_path,
                    thumbnail_png_vertical,
                    title_add_description,
                    kuaishou_time_str,
                )
                # 更新日志
                update_log(
                    log_key, "kuaishou", upload_time_obj.strftime("%Y-%m-%d-%H-%M")
                )
                print("kuaishou上传完成,已更新日志...")
                print("*" * 50)

            # if "weixin" not in uploaded_platforms:
            #     print("uploading to weixin...")
            # # upload to weixin
            # title_add_description = video_title_zh + " " + video_tags_zh_str

            # weixin_time_str = upload_time_obj.strftime("%Y-%m-%d %H:%M")

            # # upload to weixin
            # upload_weixin_video(
            #     video_path,
            #     thumbnail_png_horizontal,
            #     video_title_zh.replace("#", "sharp"),
            #     title_add_description,
            #     weixin_time_str,
            # )

            # # 更新日志
            # update_log(
            #     log_key, "weixin", upload_time_obj.strftime("%Y-%m-%d-%H-%M")
            # )
            # print("weixin上传完成,已更新日志...")
            # print("*" * 50)


if __name__ == "__main__":
    topic = "code"
    upload_all_platforms(topic=topic)
