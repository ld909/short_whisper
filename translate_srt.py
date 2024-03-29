from srt_format import read_srt_file, parse_srt_with_re
import os
import anthropic
from tqdm import tqdm
import ast


def controller():

    formatted_srts = os.listdir("./test_format_final")
    for srt in formatted_srts:
        srt_read = read_srt_file("./test_format_final/" + srt)
        print("Translating: ", srt)
        timestamps, subtitles = parse_srt_with_re(srt_read)

        assert len(timestamps) == len(subtitles)

        zh_srt = []
        # everytime get 3 subtitles and corresponding timestamps
        for i in tqdm(range(0, len(subtitles), 3)):
            # get 3 subtitles
            sentences = subtitles[i : i + 3]
            # format the 3 subtitles into a list, each item is a sentence, surrounded by double quotes
            sentences = [f"{sentence}" for sentence in sentences]

            # translate the 3 subtitles
            success = False
            while not success:
                translated_sentences, success = translate_srt(sentences)

            # assert the number of translated subtitles is the same as the original subtitles
            assert len(translated_sentences) == len(sentences)

            # for testing print the original and translated subtitles
            # for idx, sentence in enumerate(translated_sentences):
            #     print(f"Original: {sentences[idx]}")
            #     print(f"Translated: {sentence}")
            #     print("\n")

            # append the translated subtitles to the list
            for zh_sentence in translated_sentences:
                zh_srt.append(zh_sentence)

        # assert the number of translated subtitles is the same as the original subtitles
        print(len(zh_srt), len(subtitles))
        assert len(zh_srt) == len(subtitles)

        # save the translated subtitles and timestamps to a new file
        with open("./chinese_srt/" + srt, "w") as f:
            for i in range(len(zh_srt)):
                f.write(str(i + 1) + "\n")
                f.write(timestamps[i][0] + " --> " + timestamps[i][1] + "\n")
                srt_txt = zh_srt[i].replace("。", "")
                # if not the last sentence, add a \n\n
                if i != len(zh_srt) - 1:
                    f.write(srt_txt + "\n\n")
                else:
                    f.write(srt_txt)


def translate_srt(eng_srt_str):
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    text = f"我会给你一个字幕的list，list每个item是一条英文字幕，帮我翻译为中文。返回一个list，长度和输入的list长度一致，每个item是对应翻译后的中文字幕。除了翻译后的结果list外，不用返回任何多余的文字和额外说明。英文字幕list是: {eng_srt_str}"
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        temperature=0,
        system="你是一个优秀的翻译家，能够精确优雅准确精炼地把英文视频字幕翻译为中文字幕，视频题材为科技编程等相关领域。",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": text,
                    }
                ],
            }
        ],
    )
    translate_srt_str = message.content[0].text
    translate_srt_list = ast.literal_eval(translate_srt_str)
    success = message.stop_reason == "end_turn"
    return translate_srt_list, success


if __name__ == "__main__":
    controller()
