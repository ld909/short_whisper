import os
import threading
import nls

URL = "wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1"
TOKEN = "d14ca8b458664d089714dbce3ddf1347"  # 参考https://help.aliyun.com/document_detail/450255.html 获取token
APPKEY = "jtud4cprXE2nGCuk"  # 获取Appkey请前往控制台：https://nls-portal.console.aliyun.com/applist


# 以下代码会根据上述TEXT文本反复进行语音合成
class TestTts:
    def __init__(self, tid, test_file, test_speed):
        self.__id = tid
        self.__test_file = test_file
        self.__test_speed = test_speed

    def start(self, text):
        self.__text = text
        self.__f = open(self.__test_file, "wb")
        self.__test_run()

    def test_on_metainfo(self, message, *args):
        print("on_metainfo message=>{}".format(message))

    def test_on_error(self, message, *args):
        print("on_error args=>{}".format(args))

    def test_on_close(self, *args):
        print("on_close: args=>{}".format(args))
        try:
            self.__f.close()
        except Exception as e:
            print("close file failed since:", e)

    def test_on_data(self, data, *args):
        try:
            self.__f.write(data)
        except Exception as e:
            print("write data failed:", e)

    def test_on_completed(self, message, *args):
        print("on_completed:args=>{} message=>{}".format(args, message))

    def __test_run(self):
        print("task:{} start..".format(self.__id))
        tts = nls.NlsSpeechSynthesizer(
            url=URL,
            token=TOKEN,
            appkey=APPKEY,
            on_metainfo=self.test_on_metainfo,
            on_data=self.test_on_data,
            on_completed=self.test_on_completed,
            on_error=self.test_on_error,
            on_close=self.test_on_close,
            callback_args=[self.__id],
        )
        print("{}: session start".format(self.__id))
        r = tts.start(
            self.__text,
            voice="aishuo",
            aformat="mp3",
            speech_rate=self.__test_speed,
            volume=100,
        )
        print("{}: tts done with result:{}".format(self.__id, r))


def get_file_size(filepath):
    return os.path.getsize(filepath)


def aliyun_tts_single(
    text,
    mp3_dst,
    mp3_speed,
    num=1,
):
    for i in range(0, num):
        name = "task" + str(i)
        t = TestTts(name, mp3_dst, mp3_speed)
        t.start(text)
