"""
  For more samples please visit https://github.com/Azure-Samples/cognitive-services-speech-sdk 
"""

import azure.cognitiveservices.speech as speechsdk
import xml.etree.ElementTree as ET
from xml.dom import minidom


def create_ssml_string(text, rate="1.05", yinse_name="zh-CN-YunjieNeural"):
    # 创建根元素
    speak = ET.Element(
        "speak",
        version="1.0",
        xmlns="http://www.w3.org/2001/10/synthesis",
        attrib={"xml:lang": "zh-CN"},
    )

    # 创建 voice 元素
    voice = ET.SubElement(speak, "voice", name=yinse_name)

    # 创建 prosody 元素
    prosody = ET.SubElement(voice, "prosody", rate=rate)

    # 设置 prosody 元素的文本内容
    prosody.text = text

    # 创建 minidom 对象,用于格式化 XML
    xml_str = ET.tostring(speak, "utf-8")
    dom = minidom.parseString(xml_str)

    # 获取格式化后的 SSML 字符串
    ssml_string = dom.toprettyxml(indent="    ", encoding="utf-8").decode("utf-8")

    return ssml_string


def tts_ms(txt_string, topic):
    # Creates an instance of a speech config with specified subscription key and service region.
    speech_key = "cba10589e21e48dfb986f493e276b833"
    service_region = "eastasia"

    speech_config = speechsdk.SpeechConfig(
        subscription=speech_key, region=service_region
    )

    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3
    )

    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=None
    )
    # 示例用法
    content = "如何学习python编程？今天我们来学习一下Python编程的基础知识。"
    ssml_string = create_ssml_string(content)

    # 将 SSML 字符串传递给语音合成函数
    result = speech_synthesizer.speak_ssml_async(ssml_string).get()
    # ssml_string = open("./test_ssml/ssml.xml", "r").read()
    # result = speech_synthesizer.speak_ssml_async(ssml_string).get()

    stream = speechsdk.AudioDataStream(result)
    stream.save_to_wav_file("./file-Audio48Khz192KBitRateMonoMp3.mp3")
