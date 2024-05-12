import anthropic

client = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    api_key="my_api_key",
)

message = client.messages.create(
    model="claude-3-haiku-20240307",
    max_tokens=1000,
    temperature=0,
    system="你是一个超高的营销大师，你可以为每个短视频重新起一个好名字，名字也是让你点击观看的重要因素。现在，我需要你的创意和灵感来为这个视频起一个新的名字。这个视频内容充满了惊喜和创意，需要一个能够引人入胜、让观众眼前一亮的名字。",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "原视频关于计算机科学，中文名是：C语言100秒。请起一个新名字，不能删去任何重点信息，只返回新名字，不返回任何多余内容，不要加标点和emoji。字数12汉字以内。",
                }
            ],
        }
    ],
)
print(message.content)
