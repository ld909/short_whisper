# from srt_format import time_str_to_obj, timedelta_to_srt

# string = "00:00:06,260"

# timedelta_obj = time_str_to_obj(string)
# string_back = timedelta_to_srt(timedelta_obj)
# print(string, timedelta_obj, string_back)
# from translate_srt import wrap_srt_text_chinese
# import jieba


def float_to_srt_timestamp(seconds):
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


# 测试一下
print(float_to_srt_timestamp(50.22))  # 应该输出 00:00:50,220
