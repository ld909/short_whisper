#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍总结生成脚本 - 支持多语言主题的浏览器自动化抓取

核心特性：
🌐 多语言主题支持：完全独立处理英文(en)和中文(zh)书籍
📚 智能书籍处理：自动识别并处理对应语言的书籍数据
🤖 AI生成总结：使用AI Studio生成高质量30分钟音频讲稿

功能说明：
1. 从 book_info_scraper.py 抓取的书籍信息中读取数据（按语言分类）
2. 使用 AdsPower + Playwright 浏览器自动化
3. 支持PDF文件上传到 AI Studio（先点击Insert assets按钮，等待激活后上传）
4. 发送书籍信息到 AI Studio 生成讲稿总结（发送前按两次ESC确保按钮可见）
5. 每次启动动态检查已生成的总结（不依赖进度文件）
6. 智能跳过机制：如果某个UUID连续5次无法统计到token，将自动跳过该书籍
7. JSON跟踪记录：在summary_json目录保存每个UUID的处理记录和失败次数
8. 多语言目录结构：
   - 英文主题：/Volumes/dhl/audio/books/en/
   - 中文主题：/Volumes/dhl/audio/books/zh/
9. 智能保存到对应语言目录：{基础路径}/books/{语言}/summary/[uuid].txt

使用方法：
# 基础操作
python generate_book_summary.py                     # 生成所有可用的总结（默认行为）
python generate_book_summary.py --count 10          # 生成10个总结（默认英文主题）
python generate_book_summary.py --all               # 生成所有可用的总结（与默认行为相同）
python generate_book_summary.py --ads-id your_id    # 指定浏览器ID
python generate_book_summary.py --check-status      # 检查当前状态

# 多语言主题支持
python generate_book_summary.py --count 10 --lang en  # 生成英文主题总结
python generate_book_summary.py --count 10 --lang zh  # 生成中文主题总结
python generate_book_summary.py --all --lang zh       # 生成所有中文主题总结
python generate_book_summary.py --check-status --lang zh  # 检查中文主题状态

注意：
- 脚本会自动检测 book_pdf_downloader.py 输出的PDF文件并上传到AI Studio
- 不同语言主题完全独立，拥有独立的目录结构和数据源
- 默认使用英文主题(en)，中文主题需要明确指定 --lang zh
"""

import os
import sys
import json
import time
import random
import argparse
import platform
import glob
import datetime
from pathlib import Path
from tqdm import tqdm

# 导入浏览器自动化相关模块
try:
    from playwright.sync_api import sync_playwright
    import urllib3
except ImportError:
    print("❌ 缺少依赖模块，请安装: pip install playwright urllib3")
    sys.exit(1)


def get_base_media_path():
    """根据系统类型返回基础媒体路径"""
    if platform.system() == "Darwin":  # macOS
        machine = platform.machine().lower()
        processor = platform.processor().lower()
        # Apple Silicon (M芯片)
        is_apple_silicon = (
            machine == "arm64"
            or "arm" in machine
            or "apple" in processor
            or "m1" in processor
            or "m2" in processor
            or "m3" in processor
        )
        if is_apple_silicon:
            return "/Users/donghaoliu/Documents/audio"
        else:
            # Intel Mac
            return "/Volumes/dhl/audio"
    return "/Users/donghaoliu/Documents/audio"  # 默认


def get_adspower_info(ads_id):
    """连接AdsPower浏览器"""
    open_url = f"http://local.adspower.net:50325/api/v1/browser/start?user_id={ads_id}"

    http = urllib3.PoolManager()

    print("正在连接AdsPower...")
    r = http.request("GET", open_url)

    if r.status != 200:
        print(f"错误: API返回状态码 {r.status}")
        print("请确保AdsPower已启动并且本地API已启用")
        return None, None, http

    resp = json.loads(r.data.decode("utf-8"))

    if resp["code"] != 0:
        print(f"错误: {resp['msg']}")
        print("请检查ads_id是否正确")
        return None, None, http

    ws_endpoint = resp["data"]["ws"]["puppeteer"]
    debug_port = resp["data"]["debug_port"]
    remote_debugging_url = f"http://localhost:{debug_port}"

    print(f"成功连接AdsPower，WebSocket地址: {ws_endpoint}")
    print(f"远程调试URL: {remote_debugging_url}")

    return ws_endpoint, remote_debugging_url, http


class BookSummaryGenerator:
    """书籍总结生成器 - 使用浏览器自动化"""

    def __init__(self, ads_id="k10i5y1s", debug=False, lang="en"):
        self.ads_id = ads_id
        self.debug = debug
        self.lang = lang
        self.base_media_path = get_base_media_path()
        self.books_base_path = os.path.join(self.base_media_path, "books", lang)
        # 自动设置 PDF 目录（与 book_pdf_downloader.py 保持一致）
        self.pdf_dir = os.path.join(self.books_base_path, "pdf")

        # 目录结构
        self.info_dir = os.path.join(self.books_base_path, "info")
        self.summary_dir = os.path.join(self.books_base_path, "summary")

        # JSON跟踪文件路径
        self.summary_json_dir = os.path.join(self.books_base_path, "summary_json")
        self.tracking_json_file = os.path.join(
            self.summary_json_dir, f"token_tracking_{lang}.json"
        )

        # 创建目录
        os.makedirs(self.summary_dir, exist_ok=True)
        os.makedirs(self.summary_json_dir, exist_ok=True)

        # 输出语言主题信息
        print(f"🌐 语言主题: {self.lang}")
        print(f"📁 基础路径: {self.books_base_path}")

        # 浏览器相关
        self.playwright = None
        self.browser = None
        self.page = None

        # 初始化跟踪数据
        self.tracking_data = self.load_tracking_data()

        # 根据语言主题选择对应的提示词模板
        if self.lang == "zh":
            # 中文提示词模板
            self.prompt_template = """
你是一位世界级的故事叙述者和畅销书营销专家，专门为一个广受欢迎的YouTube频道创作深度、富有洞察力的书籍总结。你的观众聪明、好奇，正在寻找下一本能够改变人生的好书。你的使命是将提供的书籍内容转化为引人入胜的30分钟音频讲稿。最终的讲稿应该生动、深刻、令人信服，让听众产生强烈的购买欲望，想要亲自体验这本书。总字数应约为4500字，以满足30分钟的目标时长。
你的分析和讲稿必须按照以下五个部分的框架来构建。
第一部分：无法抗拒的开场白（目标时长：0到45秒，约125字）
你的频道以其不可预测和引人入胜的开场白而闻名。为了保持这一声誉，你必须有意识地在不同的书籍总结中变换开场白的风格。避免陷入总是问问题的可预测模式。你的首要任务是用专为这本书独特灵魂量身定制的开场白抓住观众的注意力。选择以下方法之一：
惊人的陈述或统计数据：直接将听众带入一个令人惊讶的现实。一个大胆的、反直觉的说法，打破常见的信念。例如："现在听这句话的人中，超过一半将无法实现他们最大的人生目标。今天，我们要谈论真正掌控一切的隐藏力量。"这会立即引起好奇心。
简短而富有感召力的小故事：用几句话描绘一个小故事。介绍一个角色、一个场景、一个紧张或顿悟的时刻。例如："想象一位孤独的船长，在狂风暴雨中迷失方向，只有一个坏掉的指南针作为向导。那个船长就是你，暴风雨就是你的日常生活。但如果我告诉你有一张地图..."这会立即建立情感连接。
深刻的悖论：提出一个既奇特又真实的心理谜题。两个看似矛盾的想法，这本书将揭开谜底。例如："我们建造用来连接彼此的工具，往往是让我们感到最孤独的东西。这怎么可能，我们能做些什么？"这会吸引听众的理智。
深度个人化的问题：如果必须使用问题，那就提一个能迫使立即内省的问题，而不是一般性的询问。例如："你上一次真正、根本性地改变对某个重要事物的看法是什么时候？不仅仅是你的观点，而是你的核心信念？"
目标是令人难忘，让听众感觉这个总结是有意图和创造性地制作的，而不是从模板中来的。
第二部分：核心问题和宏伟承诺（目标时长：45秒到3分钟，约500字）
在开场白之后，立即介绍这本书要解决的核心问题、疑问或冲突。为什么这本书需要存在？它针对什么根本的人类斗争、社会问题或深度好奇心？以让听众个人感受到利害关系的方式来表述。然后，将这本书及其作者介绍为向导或深刻启示的来源。呈现这本书的宏伟承诺：它为读者提供什么样的转变、理解或体验？这一部分设定了舞台，告诉听众为什么这30分钟的投资将是一个游戏规则改变者。
第三部分：问题的核心 - 深度探讨（目标时长：3分钟到25分钟，约3300字）
这是你总结的核心，你作为故事叙述者的天赋在这里闪闪发光。你的方法必须适应书籍的类型。
对于非小说类（哲学、科学、自助、历史等）：
识别书中3到5个最强大、最基础的想法或原则。不要只是列出它们。对于每个想法，你必须：
首先，以简单、引人入胜的方式清楚地解释概念。
其次，用作者在文本中提供的最令人信服的故事、轶事或证据使其栩栩如生。这对于使抽象变得有形至关重要。
第三，将这个想法直接与听众的生活联系起来。使用修辞问题和相关场景，帮助他们看到这个概念如何适用于他们自己的经历、挑战和抱负。
对于小说类（小说、短篇故事）和叙述性非小说：
不要简单地列出情节要点。你的目标是传达情感旅程和书籍的氛围。追踪中心叙事弧线，专注于主人公的发展、他们面临的道德或哲学困境，以及总体主题。唤起书籍独特的感觉——是令人毛骨悚然、激动人心、鼓舞人心，还是令人心碎？捕捉作者散文的语调和风格。你可以暗示主要情节发展和高潮来建立紧张感和好奇心，但你不能透露会毁掉阅读体验的关键剧透。专注于事件背后的"为什么"，而不仅仅是"什么"。
第四部分：独特本质和营销亮点（目标时长：25分钟到28分钟，约450字）
现在，完全进入你作为营销大师的角色。要有主见和直接。在这一部分中，你必须明确说明为什么这本书是必读的。在你的讲稿中直接回答这些问题：是什么让这本书与其类别中的任何其他书籍根本不同？它提供了什么在其他地方找不到的独特视角或感受？这本书适合谁？要具体。是雄心勃勃的企业家、从失落中康复的人、内心的冒险家，还是真理的寻求者？同样重要的是，这本书不适合谁？这种诚实建立了信任和权威。通过阐述读者在读完最后一页很久之后仍会保留的最有价值的收获来结束这一部分。
第五部分：强有力的行动号召（目标时长：28分钟到30分钟，约125字）
以强有力、鼓舞人心和紧迫的结论结束。不要只说"链接在描述中"。再次总结书籍的变革性承诺，回到最初的开场白。将购买和阅读这本书的行为定义为听众成长、理解或娱乐旅程中的重要下一步。使用引人注目的语言，如："这个总结只是地图；阅读这本书才是旅程本身"，或"要真正理解这一点，你必须让作者的话语冲刷你。"让听众感觉他们不仅仅是在买一本书，而是在投资一种深刻的体验。然后，也只有到那时，才发出最终的后勤行动号召，要求点赞、订阅和购买这本书。
只返回单一的、连续的纯文本块。
不要包含任何舞台指示、音效或语调或音乐的括号描述。
这个文本必须能够直接被音频引擎读取，无需任何进一步修改。
确保故事足够长，成为一个完整的有声书，至少15分钟长。
确保总字数至少达到5000字。
"""
        else:
            # 英文提示词模板（保持原有内容不变）
            self.prompt_template = """
You are a world-class storyteller and a master book marketer for a highly popular YouTube channel specializing in deep, insightful book summaries. Your audience is intelligent, curious, and looking for their next life-changing read. Your mission is to take the provided book content and transform it into a captivating 30-minute audio script. The final script should be so vivid, profound, and compelling that it creates a powerful urge in the listener to purchase and experience the book firsthand. The total word count should be approximately 4500 words to meet the 30-minute target.
Your analysis and script must be structured according to the following five-part framework.
Part 1: The Irresistible Hook (Target length: 0 to 45 seconds, approx. 125 words)
Your channel is famous for its unpredictable and gripping openings. To maintain this reputation, you must deliberately vary your opening hooks across different book summaries. Avoid falling into a predictable pattern of always asking a question. Your first priority is to seize the audience's attention with an opening that is custom-crafted for the book's unique soul. Choose one of the following approaches:
A Startling Statement or Statistic: Drop the listener directly into a surprising reality. A bold, counter-intuitive claim that shatters a common belief. For example: "More than half the people listening to this sentence will not achieve their biggest life goal. Today, we're going to talk about the hidden force that's really in control." This creates immediate intrigue.
A Short, Evocative Anecdote: Paint a miniature story in just a few sentences. Introduce a character, a setting, a moment of tension or realization. For example: "Imagine a lone ship captain, lost in a raging storm, with only a broken compass for guidance. That captain is you, and the storm is your daily life. But what if I told you there's a map..." This creates an instant emotional connection.
A Profound Paradox: Present a mental puzzle that feels both strange and true. Two seemingly contradictory ideas that the book will unravel. For example: "The very tools we build to connect us are often what make us feel most alone. How is this possible, and what can we do about it?" This appeals to the listener's intellect.
A Deeply Personal Question: If you must use a question, make it one that forces immediate introspection, not a generic query. For example: "When was the last time you truly, fundamentally changed your mind about something important? Not just your opinion, but your core belief?"
The goal is to be unforgettable and to make the listener feel that this summary was made with intent and creativity, not from a template.
Part 2: The Core Problem and the Grand Promise (Target length: 45 seconds to 3 minutes, approx. 500 words)
After the hook, immediately introduce the central problem, question, or conflict that the book addresses. Why does this book need to exist? What fundamental human struggle, societal issue, or deep curiosity does it speak to? Frame this in a way that the listener feels the stakes personally. Then, introduce the book and its author as the guide or the source of a profound revelation. Present the book's grand promise: What transformation, understanding, or experience does it offer the reader? This section sets the stage and tells the listener why this 30-minute investment will be a game-changer.
Part 3: The Heart of the Matter - The Deep Dive (Target length: 3 minutes to 25 minutes, approx. 3300 words)
This is the core of your summary, where your gift as a storyteller shines brightest. Your approach here must adapt to the genre of the book.
For Non-Fiction (Philosophy, Science, Self-Help, History, etc.):
Identify the 3 to 5 most powerful, foundational ideas or principles from the book. Do not just list them. For each idea, you must:
First, clearly explain the concept in a simple, engaging way.
Second, bring it to life with the most compelling story, anecdote, or piece of evidence the author provides in the text. This is crucial for making the abstract tangible.
Third, connect this idea directly to the listener's life. Use rhetorical questions and relatable scenarios to help them see how this concept applies to their own experiences, challenges, and aspirations.
For Fiction (Novels, Short Stories) and Narrative Non-Fiction:
Do not simply list plot points. Your goal is to convey the emotional journey and the atmosphere of the book. Trace the central narrative arc, focusing on the protagonist's development, the moral or philosophical dilemmas they face, and the overarching themes. Evoke the book's unique feeling—is it haunting, thrilling, inspiring, heartbreaking? Capture the tone and style of the author's prose. You can hint at major plot developments and the climax to build tension and intrigue, but you must not reveal critical spoilers that would ruin the reading experience. Focus on the "why" behind the events, not just the "what."
Part 4: The Unique Essence and Marketing Spark (Target length: 25 minutes to 28 minutes, approx. 450 words)
Now, step fully into your role as a master marketer. Be opinionated and direct. In this section, you must explicitly address why this book is a must-read. Answer these questions directly in your script: What makes this book radically different from any other book in its category? What unique perspective or feeling does it offer that cannot be found elsewhere? Who is this book for? Be specific. Is it for the ambitious entrepreneur, the person healing from loss, the adventurer at heart, the seeker of truth? Equally important, who is this book NOT for? This honesty builds trust and authority. Conclude this part by articulating the single most valuable takeaway a reader will be left with long after they've finished the last page.
Part 5: The Powerful Call to Action (Target length: 28 minutes to 30 minutes, approx. 125 words)
End with a powerful, inspiring, and urgent conclusion. Do not just say "the link is in the description." Summarize the book's transformative promise one last time, connecting back to the initial hook. Frame the act of buying and reading the book as an essential next step in the listener's journey of growth, understanding, or entertainment. Use compelling language like, "This summary is just the map; reading the book is the journey itself," or "To truly understand this, you have to let the author's words wash over you." Make the listener feel that they are not just buying a book, but investing in a profound experience. Then, and only then, deliver the final logistical call to action to like, subscribe, and purchase the book.
Return only a single, continuous block of plain text.
Do not include any stage directions, sound effects, or parenthetical descriptions of tone or music.
This text must be directly readable by an audio engine without requiring any further modification.
Make 100% sure the story is long enough to be a full audiobook, which is at least 15 minutes long.
Ensure the total word count reaches at least 5000 words.
"""

    def load_book_info_list(self):
        """加载所有书籍信息"""
        book_list = []

        if not os.path.exists(self.info_dir):
            print(f"❌ 书籍信息目录不存在: {self.info_dir}")
            return book_list

        info_files = glob.glob(f"{self.info_dir}/*.json")
        print(f"📚 找到 {len(info_files)} 个书籍信息文件")

        for info_file in info_files:
            # 排除Mac系统文件
            if os.path.basename(info_file).startswith("."):
                continue

            try:
                with open(info_file, "r", encoding="utf-8") as f:
                    book_info = json.load(f)

                # 验证必要字段
                if book_info.get("uuid") and book_info.get("title"):
                    book_list.append(book_info)
                else:
                    print(f"⚠️ 跳过不完整的书籍信息: {info_file}")

            except Exception as e:
                print(f"⚠️ 读取书籍信息失败 {info_file}: {e}")

        print(f"✅ 成功加载 {len(book_list)} 个有效书籍信息")
        return book_list

    def get_existing_summaries(self):
        """获取已存在的总结 - 动态检查实际文件"""
        existing_uuids = set()

        if os.path.exists(self.summary_dir):
            summary_files = glob.glob(f"{self.summary_dir}/*.txt")
            for summary_file in summary_files:
                filename = os.path.basename(summary_file)
                # 排除Mac系统文件
                if filename.startswith("."):
                    continue

                # 提取UUID
                if filename.endswith(".txt"):
                    uuid_val = filename[:-4]
                    # 验证文件是否有效（大小大于1KB）
                    try:
                        if os.path.getsize(summary_file) > 1000:
                            existing_uuids.add(uuid_val)
                            if self.debug:
                                print(f"✅ 发现有效总结: {uuid_val}")
                        else:
                            if self.debug:
                                print(f"⚠️ 跳过过小的文件: {uuid_val}")
                    except:
                        if self.debug:
                            print(f"⚠️ 检查文件失败: {uuid_val}")

        print(f"📊 找到 {len(existing_uuids)} 个已存在的有效总结")
        return existing_uuids

    def filter_books_to_process(self, book_list, max_count=None):
        """筛选需要处理的书籍（只依赖实际文件检查）"""
        existing_summaries = self.get_existing_summaries()

        # 过滤已完成的书籍和没有PDF的书籍
        books_to_process = []
        books_without_pdf = 0
        books_already_done = 0

        for book in book_list:
            uuid_val = book.get("uuid")
            if not uuid_val:
                continue

            # 检查是否已存在总结
            if uuid_val in existing_summaries:
                books_already_done += 1
                if self.debug:
                    print(f"⏭️  跳过已完成: {book.get('title', uuid_val)}")
                continue

            # 检查是否应该跳过（连续5次token失败）
            if self.should_skip_uuid(uuid_val):
                continue

            # 检查是否有对应的PDF文件
            if self.check_pdf_file_exists(book):
                books_to_process.append(book)
                if self.debug:
                    print(f"🎯 待处理: {book.get('title', uuid_val)}")
            else:
                books_without_pdf += 1
                if self.debug:
                    print(f"📄 无PDF: {book.get('title', uuid_val)}")

        # 限制数量
        if max_count and len(books_to_process) > max_count:
            books_to_process = books_to_process[:max_count]

        print(f"🎯 筛选出 {len(books_to_process)} 本书需要生成总结")
        print(f"✅ 已完成 {books_already_done} 本书的总结")
        if books_without_pdf > 0:
            print(f"⏭️  跳过 {books_without_pdf} 本没有PDF文件的书籍")
        return books_to_process

    def setup_browser(self):
        """设置浏览器"""
        ws_endpoint, remote_debugging_url, http = get_adspower_info(self.ads_id)

        if not ws_endpoint:
            raise Exception("无法连接到AdsPower浏览器")

        print("🔌 正在使用Playwright连接浏览器...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.connect_over_cdp(remote_debugging_url)

        # 获取或创建上下文
        if not self.browser.contexts:
            context = self.browser.new_context()
        else:
            context = self.browser.contexts[0]

        # 获取当前所有页面
        existing_pages = context.pages
        print(f"📋 发现 {len(existing_pages)} 个现有标签页")

        # 创建新标签页
        print("🆕 创建新标签页...")
        self.page = context.new_page()

        # 关闭所有旧的标签页
        if existing_pages:
            print(f"❌ 关闭 {len(existing_pages)} 个旧标签页...")
            for old_page in existing_pages:
                try:
                    old_page.close()
                except Exception as e:
                    print(f"⚠️ 关闭旧标签页时出错: {e}")

        # 确保新标签页处于活动状态
        self.page.bring_to_front()
        print("✅ 浏览器已准备就绪，新标签页已激活")

        return http

    def cleanup_browser(self, http):
        """清理浏览器资源"""
        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()

            # 关闭AdsPower浏览器
            close_url = f"http://local.adspower.net:50325/api/v1/browser/stop?user_id={self.ads_id}"
            http.request("GET", close_url)

            print("🧹 浏览器资源已清理")
        except Exception as e:
            print(f"⚠️ 清理浏览器资源时出错: {e}")

    def wait_for_ai_completion(self):
        """等待AI运行完成 - 支持internal error自动重试"""
        print("🔄 正在等待AI运行完成...")

        # 停止按钮选择器
        stop_selectors = [
            'rect[class*="stoppable-stop"]',
            'button[aria-label*="stop"]',
            'button[aria-label*="Stop"]',
            '[class*="stop-button"]',
            '[class*="stoppable"]',
        ]

        # 错误提示选择器
        error_selectors = [
            'div.model-error:has-text("An internal error has occurred")',
            'div:has-text("An internal error has occurred")',
            '[class*="model-error"]:has-text("internal error")',
            'div:has-text("internal error")',
        ]

        # Rerun按钮选择器
        rerun_selectors = [
            'button[name="rerun-button"]',
            'button[aria-label*="Rerun"]',
            'button[mattooltip="Rerun"]',
            "button.rerun-button",
        ]

        # 等待AI开始运行
        self.page.wait_for_timeout(3000)

        # 监控运行状态
        check_count = 0
        consecutive_no_stop_button = 0
        rerun_attempted = False  # 标记是否已经尝试过rerun

        while True:
            check_count += 1

            # 检查错误提示
            error_detected = False
            for error_selector in error_selectors:
                try:
                    if self.page.locator(error_selector).count() > 0:
                        print("❌ 检测到AI生成错误 (internal error)")

                        if not rerun_attempted:
                            # 第一次遇到错误，尝试rerun
                            rerun_attempted = True
                            if self.try_rerun_on_error():
                                print("🔄 Rerun成功，继续等待AI完成...")
                                check_count = 0  # 重置计数器
                                consecutive_no_stop_button = 0
                                self.page.wait_for_timeout(5000)  # 等待rerun开始
                                break  # 跳出错误检查循环，继续监控
                            else:
                                print("❌ Rerun失败，跳过该书籍")
                                raise Exception(
                                    "AI生成过程中出现internal error且rerun失败"
                                )
                        else:
                            # 已经尝试过rerun但还是失败，直接跳过
                            print("❌ Rerun后仍然出现错误，跳过该书籍")
                            raise Exception(
                                "AI生成过程中出现internal error，rerun后依然失败"
                            )

                except Exception as e:
                    if "AI生成过程中出现internal error" in str(e):
                        raise e
                    continue

            # 检查停止按钮状态
            stop_buttons_exist = False
            for selector in stop_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        stop_buttons_exist = True
                        break
                except:
                    continue

            if stop_buttons_exist:
                print(f"🏃‍♂️ AI正在运行... (检查 {check_count})")
                consecutive_no_stop_button = 0
            else:
                consecutive_no_stop_button += 1
                print(f"⏸️ AI运行状态检查 (连续无活动 {consecutive_no_stop_button} 次)")

                # 连续3次检查都没有停止按钮，认为完成
                if consecutive_no_stop_button >= 3:
                    print("✅ AI运行完成")
                    break

            # 安全超时 - 如果已经rerun过，给更多时间（10分钟）
            max_checks = 240 if rerun_attempted else 120  # 20分钟 vs 10分钟
            if check_count >= max_checks:
                timeout_msg = "⏰ AI生成超时"
                if rerun_attempted:
                    timeout_msg += " (已包含rerun重试时间)"
                print(timeout_msg)
                raise Exception("AI生成超时")

            time.sleep(5)

        # 额外等待确保完成
        time.sleep(3)

    def try_rerun_on_error(self):
        """当遇到internal error时尝试点击rerun按钮"""
        print("🔄 尝试点击Rerun按钮重新生成...")

        # Rerun按钮选择器
        rerun_selectors = [
            'button[name="rerun-button"]',
            'button[aria-label*="Rerun"]',
            'button[mattooltip="Rerun"]',
            "button.rerun-button",
            'button:has-text("Rerun")',
        ]

        try:
            # 寻找最后一个rerun按钮（最新的错误）
            rerun_button = None
            for selector in rerun_selectors:
                try:
                    elements = self.page.locator(selector)
                    if elements.count() > 0:
                        # 选择最后一个rerun按钮
                        rerun_button = elements.last
                        print(
                            f"✅ 找到Rerun按钮，使用选择器: {selector} (共{elements.count()}个，选择最后一个)"
                        )
                        break
                except:
                    continue

            if not rerun_button:
                print("❌ 未找到Rerun按钮")
                return False

            # 点击rerun按钮
            print("🔘 点击Rerun按钮...")
            rerun_button.click()
            print("✅ 已点击Rerun按钮")

            # 等待一下让重新生成开始
            self.page.wait_for_timeout(3000)

            # 检查是否成功开始重新生成（检查停止按钮是否出现）
            stop_selectors = [
                'rect[class*="stoppable-stop"]',
                'button[aria-label*="stop"]',
                'button[aria-label*="Stop"]',
                '[class*="stop-button"]',
                '[class*="stoppable"]',
            ]

            rerun_started = False
            for selector in stop_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        rerun_started = True
                        print("✅ Rerun成功启动，AI开始重新生成")
                        break
                except:
                    continue

            if rerun_started:
                return True
            else:
                print("⚠️ Rerun可能未成功启动")
                return False

        except Exception as e:
            print(f"❌ 点击Rerun按钮失败: {e}")
            return False

    def extract_generated_summary(self):
        """提取生成的总结内容"""
        content_selectors = [
            "ms-prompt-chunk.text-chunk",
            "ms-prompt-chunk",
            "ms-text-chunk",
            "ms-cmark-node",
            "ms-prompt-chunk span",
            ".text-chunk",
            'div[class*="response"]',
            'div[class*="message-content"]',
        ]

        content = ""
        for selector in content_selectors:
            try:
                elements = self.page.locator(selector)
                if elements.count() > 0:
                    print(f"找到 {elements.count()} 个元素使用选择器: {selector}")

                    # 优先选择最后一个元素（最新生成的内容）
                    for i in range(elements.count() - 1, -1, -1):
                        element_text = elements.nth(i).inner_text().strip()
                        if element_text and len(element_text) > 100:
                            content = element_text
                            print(
                                f"从元素 #{i+1} 提取到内容，长度: {len(content)} 字符"
                            )
                            break

                    if content:
                        break
            except Exception as e:
                print(f"选择器 {selector} 提取失败: {e}")
                continue

        return content.strip() if content else ""

    def check_pdf_file_exists(self, book_info):
        """检查对应的PDF文件是否存在"""
        uuid_val = book_info.get("uuid", "")
        title = book_info.get("title", "未知标题")

        if not os.path.exists(self.pdf_dir):
            if self.debug:
                print(f"📁 PDF目录不存在: {self.pdf_dir}")
            return False

        # 按照 book_pdf_downloader.py 的规则，文件名为 {uuid}.pdf
        pdf_file_path = os.path.join(self.pdf_dir, f"{uuid_val}.pdf")

        if os.path.exists(pdf_file_path):
            file_size = os.path.getsize(pdf_file_path)
            if file_size > 1000:  # 至少1KB，确保不是空文件
                print(f"📎 找到PDF文件: {uuid_val}.pdf ({file_size} bytes)")
                return True
            else:
                print(f"⚠️ PDF文件太小，可能损坏: {uuid_val}.pdf ({file_size} bytes)")
                return False

        if self.debug:
            print(f"📄 未找到PDF文件: {title} (UUID: {uuid_val})")
        return False

    def upload_pdf_file(self, book_info):
        """上传PDF文件到AI Studio - 支持重试和token验证"""
        uuid_val = book_info.get("uuid", "")
        title = book_info.get("title", "未知标题")

        # 根据 book_pdf_downloader.py 的规则，PDF文件名为 {uuid}.pdf
        pdf_file_path = os.path.join(self.pdf_dir, f"{uuid_val}.pdf")

        if not os.path.exists(pdf_file_path):
            print(f"⚠️ PDF文件不存在: {pdf_file_path}")
            return False

        print(f"📎 使用PDF文件: {pdf_file_path}")

        # 最多尝试3次
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            print(f"🔄 尝试上传PDF文件 (第 {attempt}/{max_attempts} 次)...")

            try:
                # 第一步：点击"Insert assets"按钮来激活文件输入元素
                print("🔘 点击'Insert assets'按钮...")
                insert_button_selectors = [
                    'button[aria-label*="Insert assets"]',
                    "button.add-chunk-menu-button",
                    'button:has(.material-symbols-outlined:has-text("add_circle"))',
                    'button[mat-icon-button][aria-label*="Insert"]',
                    'button[aria-label*="Insert assets such as images, videos, files"]',
                ]

                insert_button = None
                for selector in insert_button_selectors:
                    try:
                        if self.page.locator(selector).count() > 0:
                            insert_button = self.page.locator(selector).first
                            print(f"✅ 找到Insert assets按钮，使用选择器: {selector}")
                            break
                    except:
                        continue

                if not insert_button:
                    print("❌ 未找到Insert assets按钮")
                    if attempt < max_attempts:
                        print(f"💫 等待3秒后重试...")
                        time.sleep(3)
                        continue
                    return False

                # 点击Insert assets按钮
                insert_button.click()
                print("✅ 已点击Insert assets按钮")

                # 等待1-2秒让input元素激活
                print("⏳ 等待input元素激活...")
                time.sleep(2)

                # 第二步：找到文件输入框
                file_input_selectors = [
                    'input[type="file"][multiple]',
                    'input[type="file"]',
                    'input[type="file"][style*="display: none"]',
                ]

                file_input = None
                for selector in file_input_selectors:
                    try:
                        if self.page.locator(selector).count() > 0:
                            file_input = self.page.locator(selector).first
                            print(f"✅ 找到文件输入框，使用选择器: {selector}")
                            break
                    except:
                        continue

                if not file_input:
                    print("❌ 未找到文件输入框")
                    if attempt < max_attempts:
                        print(f"💫 等待3秒后重试...")
                        time.sleep(3)
                        continue
                    return False

                # 第三步：上传文件
                print("📤 正在上传PDF文件...")

                # 优先使用CDP方法上传大文件，绕过50MB限制
                upload_success_cdp = False
                try:
                    # 检查文件大小
                    file_size = os.path.getsize(pdf_file_path)
                    file_size_mb = file_size / (1024 * 1024)
                    print(f"📊 PDF文件大小: {file_size_mb:.2f} MB")

                    if file_size_mb > 50:
                        print(f"🔧 文件大于50MB，使用CDP方法上传...")
                    else:
                        print(f"📁 文件小于50MB，但优先尝试CDP方法...")

                    # 获取文件输入选择器
                    file_input_selectors = [
                        'input[type="file"][multiple]',
                        'input[type="file"]',
                        'input[type="file"][style*="display: none"]',
                    ]

                    # 找到有效的文件输入选择器
                    active_file_selector = None
                    for selector in file_input_selectors:
                        try:
                            if self.page.locator(selector).count() > 0:
                                active_file_selector = selector
                                print(f"✅ 找到文件输入选择器: {selector}")
                                break
                        except:
                            continue

                    if not active_file_selector:
                        print("❌ 未找到文件输入选择器")
                        raise Exception("无法找到文件输入选择器")

                    # 创建CDP会话
                    print("🔗 创建CDP会话...")
                    cdp_session = self.page.context.new_cdp_session(self.page)

                    # 启用DOM
                    cdp_session.send("DOM.enable")

                    # 获取DOM文档
                    print("📄 获取DOM文档...")
                    dom_snapshot = cdp_session.send("DOM.getDocument", {"depth": -1})

                    # 查找文件输入节点
                    print("🔍 查找文件输入节点...")
                    node_result = cdp_session.send(
                        "DOM.querySelector",
                        {
                            "nodeId": dom_snapshot["root"]["nodeId"],
                            "selector": active_file_selector,
                        },
                    )

                    if not node_result.get("nodeId"):
                        print("❌ 无法找到文件输入节点!")
                        cdp_session.detach()
                        raise Exception("无法找到文件输入节点")

                    # 使用CDP设置文件
                    print("📁 使用CDP方法设置文件...")
                    cdp_session.send(
                        "DOM.setFileInputFiles",
                        {
                            "nodeId": node_result["nodeId"],
                            "files": [pdf_file_path],
                        },
                    )

                    # 关闭CDP会话
                    cdp_session.detach()
                    print("✅ PDF文件上传完成（使用CDP方法）")
                    upload_success_cdp = True

                except Exception as cdp_error:
                    print(f"❌ CDP上传方法失败: {cdp_error}")
                    print("🔄 尝试使用标准Playwright方法...")

                    # 如果CDP方法失败，回退到标准方法
                    try:
                        file_input.set_input_files(pdf_file_path)
                        print("✅ PDF文件上传完成（使用标准方法）")
                        upload_success_cdp = True
                    except Exception as standard_error:
                        print(f"❌ 标准上传方法也失败: {standard_error}")
                        upload_success_cdp = False

                if not upload_success_cdp:
                    print(f"❌ 第 {attempt} 次上传失败（所有方法都失败）")
                    if attempt < max_attempts:
                        print(f"💫 等待5秒后重试...")
                        time.sleep(5)
                        continue
                    return False

                # 等待上传完成，并检查token计数
                print("⏳ 等待PDF上传和处理完成...")
                upload_success = self.wait_for_pdf_token_count(title, uuid_val, title)

                if upload_success:
                    print("✅ PDF文件上传并处理成功")
                    return True
                else:
                    print(f"❌ 第 {attempt} 次上传失败（上传成功但token验证失败）")
                    if attempt < max_attempts:
                        print(f"💫 等待5秒后重试...")
                        time.sleep(5)
                        continue

            except Exception as e:
                print(f"❌ 第 {attempt} 次上传出错: {e}")
                if attempt < max_attempts:
                    print(f"💫 等待5秒后重试...")
                    time.sleep(5)
                    continue

        print(f"❌ PDF上传失败，已尝试 {max_attempts} 次")
        return False

    def wait_for_pdf_token_count(self, title="PDF文件", uuid_val="", book_title=""):
        """等待PDF token计数显示，用于验证上传成功"""
        print("🔍 等待token计数显示...")

        # token计数选择器
        token_selectors = [
            "span.token-count.ng-star-inserted",
            "span.token-count",
            'span:has-text("tokens")',
            '.token-count:has-text("tokens")',
        ]

        # 文件名选择器（用于验证是正确的文件）
        filename_selectors = [
            "span.name.gmat-body-medium",
            "span.name",
            ".file-chunk-container span.name",
        ]

        max_wait_time = 240  # 最多等待240秒（4分钟），确保有足够时间处理大文件
        check_interval = 3  # 每3秒检查一次
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            # 检查token计数
            token_found = False
            token_text = ""

            for selector in token_selectors:
                try:
                    token_elements = self.page.locator(selector)
                    if token_elements.count() > 0:
                        for i in range(token_elements.count()):
                            element_text = token_elements.nth(i).inner_text().strip()
                            if "tokens" in element_text.lower():
                                token_found = True
                                token_text = element_text
                                print(f"🎯 发现token计数: {token_text}")
                                break

                    if token_found:
                        break
                except Exception as e:
                    if self.debug:
                        print(f"检查token选择器失败 {selector}: {e}")
                    continue

            if token_found:
                # 验证是否有对应的文件名（可选验证）
                filename_found = False
                for selector in filename_selectors:
                    try:
                        filename_elements = self.page.locator(selector)
                        if filename_elements.count() > 0:
                            for i in range(filename_elements.count()):
                                filename_text = (
                                    filename_elements.nth(i).inner_text().strip()
                                )
                                if filename_text.endswith(".pdf"):
                                    filename_found = True
                                    print(f"📄 验证文件名: {filename_text}")
                                    break
                        if filename_found:
                            break
                    except:
                        continue

                print(f"✅ PDF上传验证成功 - {token_text}")

                # 更新成功记录
                if uuid_val:
                    self.update_token_success(uuid_val, book_title)

                return True

            print(f"⏳ 等待token计数... 已等待 {elapsed_time}s")
            time.sleep(check_interval)
            elapsed_time += check_interval

        print(f"⚠️ 等待token计数超时 ({max_wait_time}s)，跳过此PDF文件")

        # 更新失败记录
        if uuid_val:
            self.update_token_failure(uuid_val, book_title)

        return False

    def send_generation_request(self):
        """发送生成请求并等待AI开始运行"""
        print("🚀 发送生成请求...")

        # 发送前先按两次ESC键，确保run按钮可见
        print("⌨️ 按两次ESC键确保run按钮可见...")
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(500)
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(1000)
        print("✅ 已按两次ESC键")

        # 停止按钮选择器 - 用于验证AI是否开始运行
        stop_selectors = [
            'rect[class*="stoppable-stop"]',
            'button[aria-label*="stop"]',
            'button[aria-label*="Stop"]',
            '[class*="stop-button"]',
            '[class*="stoppable"]',
        ]

        # Run按钮选择器
        run_button_selectors = [
            'button[aria-label="Run"]',
            "button.run-button",
            'button[type="submit"][class*="run-button"]',
            'button:has-text("Run")',
            'button[aria-label*="Run"]',
        ]

        # 最多尝试3次发送
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            print(f"🔄 第 {attempt} 次尝试发送请求...")

            try:
                # 点击Run按钮
                print("🔘 点击Run按钮发送请求...")
                run_button = None

                for selector in run_button_selectors:
                    try:
                        if self.page.locator(selector).count() > 0:
                            run_button = self.page.locator(selector).first
                            print(f"✅ 找到Run按钮，使用选择器: {selector}")
                            break
                    except:
                        continue

                if not run_button:
                    print("❌ 未找到Run按钮")
                    if attempt < max_attempts:
                        print(f"💫 等待3秒后重试...")
                        self.page.wait_for_timeout(3000)
                        continue
                    raise Exception("无法找到Run按钮")

                # 点击Run按钮
                run_button.click()
                print("✅ 已点击Run按钮")

                # 等待一下让请求处理
                self.page.wait_for_timeout(3000)

                # 检查AI是否开始运行（通过停止按钮出现来判断）
                print("🔍 检查AI是否开始运行...")
                ai_started = False

                for selector in stop_selectors:
                    try:
                        if self.page.locator(selector).count() > 0:
                            ai_started = True
                            print(f"✅ AI已开始运行，发现停止按钮: {selector}")
                            break
                    except:
                        continue

                if ai_started:
                    print("🎉 生成请求发送成功，AI已开始运行")
                    return True
                else:
                    print(f"⚠️ 第 {attempt} 次发送后AI未开始运行，可能需要重试")
                    if attempt < max_attempts:
                        print("💫 等待3秒后重试...")
                        self.page.wait_for_timeout(3000)
                        continue

            except Exception as e:
                print(f"❌ 第 {attempt} 次发送请求失败: {e}")
                if attempt < max_attempts:
                    self.page.wait_for_timeout(2000)
                    continue

        raise Exception("无法发送生成请求或AI未开始运行")

    def generate_summary_for_book(self, book_info):
        """为单本书生成总结"""
        uuid_val = book_info.get("uuid", "")
        title = book_info.get("title", "未知标题")
        author = book_info.get("author", "未知作者")
        description = book_info.get("description", "暂无简介")
        year = book_info.get("publication_year", "未知年份")

        print(f"\n📖 正在检查书籍: {title}")
        print(f"   作者: {author}")
        print(f"   UUID: {uuid_val}")

        # 🔥 首先检查PDF文件是否存在，如果没有PDF就跳过
        pdf_exists = self.check_pdf_file_exists(book_info)
        if not pdf_exists:
            print("⏭️  未找到对应的PDF文件，跳过该书籍")
            return False

        print("✅ 发现PDF文件，开始生成总结...")

        try:
            # 导航到AI Studio
            print("🌐 正在打开AI Studio...")
            self.page.goto("https://aistudio.google.com/u/1/prompts/new_chat")
            self.page.wait_for_load_state("networkidle")
            self.page.wait_for_timeout(8000)

            # 构建提示词
            prompt = self.prompt_template.format(
                title=title, author=author, description=description, year=year
            )

            # 第一步：查找并输入文本框
            textarea_selectors = [
                ".text-wrapper textarea",
                "ms-autosize-textarea textarea",
                'textarea[aria-label*="Type something"]',
                'textarea[class*="textarea"]',
                "textarea",
            ]

            textarea = None
            for selector in textarea_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        textarea = self.page.locator(selector)
                        print(f"✅ 找到文本框，使用选择器: {selector}")
                        break
                except:
                    continue

            if not textarea or textarea.count() == 0:
                raise Exception("无法找到文本框")

            # 输入提示词
            print("📝 正在输入提示词...")
            textarea.click()
            self.page.wait_for_timeout(500)
            textarea.focus()
            self.page.wait_for_timeout(500)
            textarea.fill(prompt)
            self.page.wait_for_timeout(1000)

            print(f"📊 提示词长度: {len(prompt)} 字符")

            # 第二步：上传PDF文件
            print("📎 正在上传PDF文件...")
            pdf_uploaded = self.upload_pdf_file(book_info)
            if not pdf_uploaded:
                print("❌ PDF上传失败，跳过该书籍")
                return False

            # 第三步：发送请求
            self.send_generation_request()

            # 等待AI完成
            self.wait_for_ai_completion()

            # 提取生成的内容
            content = self.extract_generated_summary()

            if content:
                # 保存到文件
                summary_file = os.path.join(self.summary_dir, f"{uuid_val}.txt")
                with open(summary_file, "w", encoding="utf-8") as f:
                    f.write(content)

                print(f"✅ 总结已保存: {summary_file}")
                print(f"   内容长度: {len(content)} 字符")

                return True
            else:
                print("❌ 未能提取到生成的内容")
                return False

        except Exception as e:
            print(f"❌ 生成总结失败: {e}")
            return False

    def load_tracking_data(self):
        """加载UUID处理跟踪数据"""
        if os.path.exists(self.tracking_json_file):
            try:
                with open(self.tracking_json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    print(f"📊 加载跟踪数据: {len(data)} 个UUID记录")
                    return data
            except Exception as e:
                print(f"⚠️ 加载跟踪数据失败: {e}")

        print("📊 创建新的跟踪数据文件")
        return {}

    def save_tracking_data(self):
        """保存UUID处理跟踪数据"""
        try:
            with open(self.tracking_json_file, "w", encoding="utf-8") as f:
                json.dump(self.tracking_data, f, ensure_ascii=False, indent=2)
            if self.debug:
                print(f"💾 跟踪数据已保存: {self.tracking_json_file}")
        except Exception as e:
            print(f"❌ 保存跟踪数据失败: {e}")

    def update_token_failure(self, uuid_val, title=""):
        """更新token统计失败次数"""
        if uuid_val not in self.tracking_data:
            self.tracking_data[uuid_val] = {
                "title": title,
                "total_attempts": 0,
                "token_failures": 0,
                "last_failure_time": None,
            }

        self.tracking_data[uuid_val]["total_attempts"] += 1
        self.tracking_data[uuid_val]["token_failures"] += 1
        self.tracking_data[uuid_val][
            "last_failure_time"
        ] = datetime.datetime.now().isoformat()

        if title:
            self.tracking_data[uuid_val]["title"] = title

        print(
            f"📊 UUID {uuid_val} token失败次数: {self.tracking_data[uuid_val]['token_failures']}"
        )

        # 立即保存数据
        self.save_tracking_data()

    def update_token_success(self, uuid_val, title=""):
        """更新token统计成功（重置失败计数）"""
        if uuid_val not in self.tracking_data:
            self.tracking_data[uuid_val] = {
                "title": title,
                "total_attempts": 0,
                "token_failures": 0,
                "last_failure_time": None,
            }

        self.tracking_data[uuid_val]["total_attempts"] += 1
        # token成功时，重置失败计数
        self.tracking_data[uuid_val]["token_failures"] = 0

        if title:
            self.tracking_data[uuid_val]["title"] = title

        print(f"✅ UUID {uuid_val} token统计成功，失败计数已重置")

        # 立即保存数据
        self.save_tracking_data()

    def should_skip_uuid(self, uuid_val):
        """检查是否应该跳过某个UUID（连续5次token失败）"""
        if uuid_val in self.tracking_data:
            failures = self.tracking_data[uuid_val].get("token_failures", 0)
            if failures >= 5:
                title = self.tracking_data[uuid_val].get("title", "Unknown")
                print(
                    f"⏭️  跳过UUID {uuid_val} ({title}) - 连续{failures}次token统计失败"
                )
                return True
        return False

    def generate_summaries(self, max_count=None):
        """批量生成书籍总结"""
        print("📚 书籍总结生成器")
        print(f"📁 基础路径: {self.books_base_path}")
        print(f"💾 总结保存目录: {self.summary_dir}")

        # 加载书籍信息
        book_list = self.load_book_info_list()
        if not book_list:
            print("❌ 没有找到任何书籍信息")
            return

        # 筛选需要处理的书籍
        books_to_process = self.filter_books_to_process(book_list, max_count)
        if not books_to_process:
            print("🎉 所有书籍的总结都已生成完成！")
            return

        # 设置浏览器
        http = self.setup_browser()

        try:
            success_count = 0
            failed_count = 0

            print(f"🚀 开始生成 {len(books_to_process)} 本书的总结...")

            for i, book_info in enumerate(tqdm(books_to_process, desc="📖 生成进度")):
                try:
                    if self.generate_summary_for_book(book_info):
                        success_count += 1
                    else:
                        failed_count += 1

                    # 随机延迟，避免被限制
                    if i < len(books_to_process) - 1:
                        wait_time = random.randint(20, 30)
                        print(f"⏳ 等待 {wait_time} 秒后继续...")
                        time.sleep(wait_time)

                except KeyboardInterrupt:
                    print("⏹️ 用户中断，程序停止")
                    break
                except Exception as e:
                    print(f"❌ 处理书籍时出错: {e}")
                    failed_count += 1

            # 最终统计
            print(f"\n🎯 总结生成完成!")
            print(f"✅ 成功: {success_count} 本")
            print(f"❌ 失败: {failed_count} 本")

        finally:
            self.cleanup_browser(http)

    def check_current_status(self):
        """检查当前状态 - 不再依赖进度文件"""
        print("📊 当前状态检查")
        print(f"📁 基础路径: {self.books_base_path}")

        book_list = self.load_book_info_list()
        existing_summaries = self.get_existing_summaries()

        # 统计PDF文件情况
        books_with_pdf = 0
        books_without_pdf = 0
        for book in book_list:
            if self.check_pdf_file_exists(book):
                books_with_pdf += 1
            else:
                books_without_pdf += 1

        print(f"📚 总书籍数量: {len(book_list)}")
        print(f"📎 有PDF文件: {books_with_pdf}")
        print(f"📄 无PDF文件: {books_without_pdf}")
        print(f"✅ 已生成总结: {len(existing_summaries)}")

        # 计算实际可处理的书籍数量（有PDF且未生成总结的）
        processable_books = []
        for book in book_list:
            uuid_val = book.get("uuid")
            if (
                uuid_val
                and uuid_val not in existing_summaries
                and self.check_pdf_file_exists(book)
            ):
                processable_books.append(book)

        print(f"⏳ 待处理数量: {len(processable_books)} (有PDF且未生成总结)")

        # 显示跟踪统计信息
        if self.tracking_data:
            failed_uuids = {
                uuid: data
                for uuid, data in self.tracking_data.items()
                if data.get("token_failures", 0) >= 5
            }
            print(f"🚫 跳过数量: {len(failed_uuids)} (连续5次token失败)")

            if failed_uuids:
                print("\n📋 被跳过的书籍 (连续5次token失败):")
                for uuid, data in list(failed_uuids.items())[:5]:
                    title = data.get("title", "Unknown")
                    failures = data.get("token_failures", 0)
                    print(f"   - {title} (UUID: {uuid}, 失败{failures}次)")
                if len(failed_uuids) > 5:
                    print(f"   ... 还有 {len(failed_uuids) - 5} 本被跳过的书籍")

        if len(processable_books) > 0:
            print("\n📋 待处理书籍示例 (前5本):")
            for i, book in enumerate(processable_books[:5]):
                print(
                    f"   {i+1}. {book.get('title', 'Unknown')} - {book.get('author', 'Unknown')}"
                )
            if len(processable_books) > 5:
                print(f"   ... 还有 {len(processable_books) - 5} 本")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="📚 书籍总结生成脚本 - 使用浏览器自动化",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  python generate_book_summary.py --count 10          # 生成10个总结
  python generate_book_summary.py --all               # 生成所有可用的总结  
  python generate_book_summary.py --ads-id your_id    # 指定浏览器ID
  python generate_book_summary.py --check-status      # 检查当前状态
  python generate_book_summary.py --count 10 --lang zh  # 生成中文主题总结
  python generate_book_summary.py --count 10 --lang en  # 生成英文主题总结

注意：脚本会自动检测并使用 book_pdf_downloader.py 下载的PDF文件
        """,
    )

    parser.add_argument("--count", "-c", type=int, help="要生成的总结数量")
    parser.add_argument("--all", action="store_true", help="生成所有可用的总结")
    parser.add_argument(
        "--ads-id", default="k10i5y1s", help="AdsPower 浏览器ID (默认: k10i5y1s)"
    )
    parser.add_argument("--debug", "-d", action="store_true", help="启用调试模式")
    parser.add_argument(
        "--check-status", action="store_true", help="检查当前状态（不执行生成）"
    )
    parser.add_argument(
        "--lang", "-l", default="en", help="语言主题 (en: 英文, zh: 中文) (默认: en)"
    )

    args = parser.parse_args()

    # 创建生成器实例
    generator = BookSummaryGenerator(
        ads_id=args.ads_id, debug=args.debug, lang=args.lang
    )

    # 检查断点续传状态
    if args.check_status:
        generator.check_current_status()
        return

    # 确定生成数量
    max_count = None
    if args.count:
        max_count = args.count
    elif not args.all:
        # 默认处理所有PDF文件
        max_count = None

    print(f"🌐 使用 AdsPower ID: {args.ads_id}")
    print(f"🗣️ 语言主题: {args.lang}")

    # 检查PDF目录状态
    pdf_dir = os.path.join(generator.books_base_path, "pdf")
    if os.path.exists(pdf_dir):
        pdf_files = [
            f
            for f in os.listdir(pdf_dir)
            if f.endswith(".pdf") and not f.startswith(".")
        ]
        print(f"📎 PDF文件检查已启用，发现 {len(pdf_files)} 个PDF文件")
        print(f"📁 PDF目录: {pdf_dir}")
        print("⚠️  注意：只有存在对应PDF文件的书籍才会被处理")
    else:
        print("❌ PDF目录不存在，无法处理任何书籍")
        print("💡 请先运行 book_pdf_downloader.py 下载PDF文件")

    if max_count:
        print(f"🎯 生成数量: {max_count}")
    else:
        print("🎯 生成所有可用的总结（默认行为）")

    try:
        generator.generate_summaries(max_count=max_count)
    except KeyboardInterrupt:
        print("👋 程序已停止")
    except Exception as e:
        print(f"❌ 程序出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
