import os
import sys
from google import genai
from google.genai import types
from pathlib import Path


def setup_genai_client():
    """设置 Google GenAI 客户端并验证 API 密钥"""
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        print("错误: 未找到 API 密钥")
        print("请设置环境变量 GEMINI_API_KEY")
        print("例如: export GEMINI_API_KEY='your-api-key'")
        sys.exit(1)

    try:
        # 设置更长的超时时间来处理大文件
        http_options = types.HttpOptions(
            timeout=300.0,  # 5分钟超时
        )
        client = genai.Client(api_key=api_key, http_options=http_options)
        return client
    except Exception as e:
        print(f"初始化 GenAI 客户端时出错: {e}")
        sys.exit(1)


def main():
    """主函数，用于生成书籍讲稿"""
    client = setup_genai_client()

    # 脚本位于PDF文件所在的同一目录中
    pdf_file_path = Path(__file__).parent / "t.pdf"
    if not pdf_file_path.exists():
        print(f"错误: PDF 文件未找到: {pdf_file_path}")
        sys.exit(1)

    prompt = """
请你扮演一位经验丰富的说书人、知识渊博的阅读推广大使，或者一位能将复杂概念讲得引人入胜的导师。
我将提供一本书的全文内容。
你的任务是为这本书创作一份深度解读与精彩呈现的讲稿。这份讲稿的目标读者/听众是对该书可能不了解但有浓厚兴趣的人。你需要用生动、富有吸引力且易于理解的语言，让他们听完后，不仅能把握书籍的精华，更能产生强烈的阅读欲望或引发深刻的思考。
讲稿内容应精心编排，并至少包含以下几个层面，请根据书籍类型灵活调整侧重点：

引人入胜的开篇（Hook）：
用一个悬念、一个惊人的事实、一个直击人心的问题，或者一个与听众生活息息相关的情境，迅速抓住他们的注意力。
点出这本书为何独特、为何值得一读，它试图解答什么核心问题或描绘了怎样的世界。

核心观点/主线脉络（The Core）：
对于非虚构类（如历史、哲学、科普、经管、自我提升等）：清晰、准确地提炼出书中的核心论点、关键概念、理论框架或实用方法。用生动的例子或比喻来解释复杂的思想。
对于虚构类（如小说、故事集）：概述主要故事情节（避免过度剧透关键转折），突出主要人物的塑造、命运和成长，以及故事发生的独特背景。

核心矛盾/关键冲突/深度议题（The Conflict/Challenge）：
揭示书中探讨的主要矛盾冲突（人物内心、人与人、人与社会、观念与现实等）。
对于思辨性强的书籍，阐述其引发的关键性思考、挑战的传统观念或提出的争议性观点。

最精彩/震撼/启发性的部分（The Highlights）：
选取书中1-2个最能体现其精髓、最具冲击力、最令人拍案叫绝或最能引发共鸣的片段、情节、观点或案例进行重点描绘和解读。
这部分要讲得有声有色，富有画面感和情感张力，让听众仿佛身临其境或深受触动。

核心思考/现实意义/启发价值（The Takeaway & Reflection）：
引导听众思考这本书对于个人成长、理解世界、社会现象或人性的启示。
它如何回应我们时代的关切？它留下了哪些值得进一步探索的问题？
对于实用类书籍，可以总结出可操作的建议或行动指南。

语言风格与结构要求：
语言：务必使用口语化、生动、富有感染力的语言。多用比喻、排比、设问、感叹等修辞手法，避免干巴巴的学术论述。你需要通过文字本身来营造演讲的氛围和节奏感，让文字读起来就像一位经验丰富的演讲者正在激情讲述。
结构：逻辑清晰，层次分明，过渡自然。确保各个部分有机结合，形成一个引人入胜的整体叙事。
情感：根据书籍内容，通过文字的组织和修辞，自然地注入适当的情感，或激情澎湃，或引人深思，或温暖治愈。
长度：输出的讲稿全文，按照正常中文语速朗读，预计时长在30-40分钟左右，即大约 6000-7000汉字。请确保内容充实，避免不必要的冗余。

结尾（The Call to Action/Lasting Impression）：
用一个有力的总结再次强调书籍的价值，或者留下一个开放性的问题激发听众的持续思考。
鼓励听众亲自去阅读这本书，体验其中的奥妙。

特别强调：最终生成的讲稿中，请不要包含任何类似 （模仿当年明月的语气，略带调侃） 或 （稍作停顿，环顾四周，仿佛在与听众眼神交流） 这样的括号内或旁白式的提示、场景描述、语气指导、动作建议，或任何非讲稿正文的元注释。我希望得到的是纯粹的、可以直接朗读的讲稿文本，所有情感、节奏的表达都应融入在文字本身，而不是通过额外的提示来说明。

请你基于以上要求，为我提供的书籍生成一份精彩绝伦的讲稿。务必确保内容既忠于原著精髓，又能展现你独特的讲述魅力和深刻的洞察力，并且通篇皆为可直接朗读的讲稿内容。
"""

    print(f"正在处理文件: {pdf_file_path}...")
    print(f"文件大小: {pdf_file_path.stat().st_size / 1024 / 1024:.2f} MB")

    # 上传PDF文件到Google AI
    print("正在上传PDF文件...")
    try:
        uploaded_file = client.files.upload(file=pdf_file_path)
        print("文件上传成功！")
        print(f"上传文件ID: {uploaded_file}")
    except Exception as e:
        print(f"文件上传失败: {e}")
        print("将创建一个示例讲稿，演示脚本的工作方式...")

        # 如果文件上传失败，我们创建一个演示性的讲稿
        demo_prompt = (
            prompt + "\n\n由于无法上传PDF文件，请为《深度学习》这本书创建一份示例讲稿。"
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-pro-preview-06-05",
                contents=demo_prompt,
            )

            output_file_path = pdf_file_path.with_name("t_summary_demo.txt")
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write("# 演示讲稿 - 由于文件上传问题生成的示例\n\n")
                f.write(response.text)

            print(f"演示讲稿已生成并保存到: {output_file_path}")
            print("\n--- 讲稿预览 ---")
            print(response.text[:500] + "...")
            print("--- 预览结束 ---")
            return

        except Exception as e:
            print(f"演示讲稿生成失败: {e}")
            return

    print("正在生成讲稿，这可能需要一些时间...")

    # 尝试多次生成，处理网络问题
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"尝试第 {attempt + 1} 次生成讲稿...")

            # 使用与参考代码类似的配置
            response = client.models.generate_content(
                model="gemini-2.5-pro-preview-06-05",
                contents=[prompt, uploaded_file],
            )

            output_file_path = pdf_file_path.with_name("t_summary.txt")
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(response.text)

            print(f"讲稿已生成并保存到: {output_file_path}")
            print("\n--- 讲稿预览 ---")
            print(response.text[:500] + "...")
            print("--- 预览结束 ---")
            return  # 成功生成，退出函数

        except Exception as e:
            print(f"第 {attempt + 1} 次尝试失败: {e}")
            if attempt < max_retries - 1:
                print("等待5秒后重试...")
                import time

                time.sleep(5)
            else:
                print("所有重试都失败了。")
                import traceback

                traceback.print_exc()


if __name__ == "__main__":
    main()
