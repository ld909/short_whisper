# from srt_format import time_str_to_obj, timedelta_to_srt

# string = "00:00:06,260"

# timedelta_obj = time_str_to_obj(string)
# string_back = timedelta_to_srt(timedelta_obj)
# print(string, timedelta_obj, string_back)
from translate_srt import wrap_srt_text_chinese
import jieba

a = "所以尽管 ChatGPT 和 Gemini 在生成代码方面非常出色,但对我来说,主要问题仍然是输入,用户输入以及它如何影响 AI 模型。"
a, b = wrap_srt_text_chinese(a)
print(a)
