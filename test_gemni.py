from google import genai
from google.genai import types
import base64


def generate():
    client = genai.Client(
        vertexai=True,
        project="ytb-upload-383815",
        location="us-central1",
    )

    msg1_text1 = types.Part.from_text(
        text="""你是一个优秀的翻译家，译经家，翻译佛经很在行，能够精确优雅准确精炼地把中文的佛学视频字幕翻译为日文字幕，原视频是关于佛学/佛教/佛经相关话题的，请注意你的专业用语。直接返回翻译后的结果，不返回其他任何多余结果, 结果不要带任何引号。原中文字幕是字幕是：佛陀涅槃，无声无息，不生不灭"""
    )
    msg3_text1 = types.Part.from_text(
        text="""你是一个优秀的翻译家，译经家，翻译佛经很在行，能够精确优雅准确精炼地把中文的佛学视频字幕翻译为日文字幕，原视频是关于佛学/佛教/佛经相关话题的，请注意你的专业用语。直接返回翻译后的结果，不返回其他任何多余结果, 结果不要带任何引号。原中文字幕是字幕是：第一品法会因由分. 如是我闻，一时，佛在舍卫国祗树给孤独园，与大比丘众千二百五十人俱。尔时，世尊食时，著衣持钵，. 入舍卫大城乞食。"""
    )
    msg4_text1 = types.Part.from_text(
        text="""{
  \"response\": \"第一章 法の会の理由分 如是我聞、一時、仏は舎衛国の祇樹給孤独園におられた。大比丘衆千二百五十人と共に。 その時、世尊は食時、衣をつけ鉢を持ち、舎衛の大城に入って乞食された。\"
}"""
    )
    msg5_text1 = types.Part.from_text(
        text="""你是一个优秀的翻译家，译经家，翻译佛经很在行，能够精确优雅准确精炼地把中文的佛学视频字幕翻译为韩文字幕，原视频是关于佛学/佛教/佛经相关话题的，请注意你的专业用语。直接返回翻译后的结果，不返回其他任何多余结果, 结果不要带任何引号。原中文字幕是字幕是：第一品法会因由分. 如是我闻，一时，佛在舍卫国祗树给孤独园，与大比丘众千二百五十人俱。尔时，世尊食时，著衣持钵，. 入舍卫大城乞食。"""
    )
    msg6_text1 = types.Part.from_text(
        text="""{
  \"response\": \"제1품 법회의 인연분. 이와 같이 내가 들었다. 한 때 부처님께서 사위국 기수급고독원에 계셨다. 큰 비구 무리 천이백오십 명과 함께. 그때 세존께서 식사 때가 되어 옷을 입고 발우를 들고, 사위 대성으로 들어가 걸식을 하셨다.\"
}"""
    )
    msg7_text1 = types.Part.from_text(
        text="""你是一个优秀的翻译家，译经家，翻译佛经很在行，能够精确优雅准确精炼地把中文的佛学视频字幕翻译为英文字幕，原视频是关于佛学/佛教/佛经相关话题的，请注意你的专业用语。直接返回翻译后的结果，不返回其他任何多余结果, 结果不要带任何引号。原中文字幕是字幕是：第一品法会因由分. 如是我闻，一时，佛在舍卫国祗树给孤独园，与大比丘众千二百五十人俱。尔时，世尊食时，著衣持钵，. 入舍卫大城乞食。"""
    )

    model = "gemini-2.5-flash-preview-04-17"
    contents = [
        types.Content(role="user", parts=[msg1_text1]),
        types.Content(
            role="model",
            parts=[
                types.Part.from_text(
                    text="""{
  \"response\": \"仏陀の涅槃は、音もなく、生もなく、滅もない\"
}"""
                )
            ],
        ),
        types.Content(role="user", parts=[msg3_text1]),
        types.Content(role="model", parts=[msg4_text1]),
        types.Content(role="user", parts=[msg5_text1]),
        types.Content(role="model", parts=[msg6_text1]),
        types.Content(role="user", parts=[msg7_text1]),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=1,
        seed=0,
        max_output_tokens=65535,
        response_modalities=["TEXT"],
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
            ),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ],
        response_mime_type="application/json",
        response_schema={
            "type": "OBJECT",
            "properties": {"response": {"type": "STRING"}},
        },
        thinking_config=types.ThinkingConfig(
            thinking_budget=0,
        ),
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        print(chunk.text, end="")


generate()
