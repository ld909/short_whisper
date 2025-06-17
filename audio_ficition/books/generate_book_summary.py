#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍总结生成脚本 - 使用浏览器自动化抓取

功能说明：
1. 从 book_info_scraper.py 抓取的书籍信息中读取数据
2. 使用 AdsPower + Playwright 浏览器自动化
3. 支持PDF文件上传到 AI Studio（先点击Insert assets按钮，等待激活后上传）
4. 发送书籍信息到 AI Studio 生成讲稿总结（发送前按两次ESC确保按钮可见）
5. 每次启动动态检查已生成的总结（不依赖进度文件）
6. 保存总结到 /Volumes/dhl/audio/books/en/summary/[uuid].txt

使用方法：
python generate_book_summary.py --count 10          # 生成10个总结
python generate_book_summary.py --all               # 生成所有可用的总结
python generate_book_summary.py --ads-id your_id    # 指定浏览器ID
python generate_book_summary.py --check-status      # 检查当前状态

注意：脚本会自动检测 book_pdf_downloader.py 输出的PDF文件并上传到AI Studio
"""

import os
import sys
import json
import time
import random
import argparse
import platform
import glob
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
    open_url = f"http://127.0.0.1:50325/api/v1/browser/start?user_id={ads_id}"

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

    def __init__(self, ads_id="kq316tr", debug=False):
        self.ads_id = ads_id
        self.debug = debug
        self.base_media_path = get_base_media_path()
        self.books_base_path = os.path.join(self.base_media_path, "books", "en")
        # 自动设置 PDF 目录（与 book_pdf_downloader.py 保持一致）
        self.pdf_dir = os.path.join(self.books_base_path, "pdf")

        # 目录结构
        self.info_dir = os.path.join(self.books_base_path, "info")
        self.summary_dir = os.path.join(self.books_base_path, "summary")

        # 创建目录
        os.makedirs(self.summary_dir, exist_ok=True)

        # 浏览器相关
        self.playwright = None
        self.browser = None
        self.page = None

        # 生成讲稿的提示词模板
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
Make 100% sure the story is long enough to be a full audiobook, which is at least 30 minutes long.
Ensure the total word count reaches at least 4500 words.
Ensure the total word count reaches at least 4500 words.
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
            close_url = (
                f"http://127.0.0.1:50325/api/v1/browser/stop?user_id={self.ads_id}"
            )
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
                file_input.set_input_files(pdf_file_path)

                # 等待上传完成，并检查token计数
                print("⏳ 等待PDF上传和处理完成...")
                upload_success = self.wait_for_pdf_token_count(title)

                if upload_success:
                    print("✅ PDF文件上传并处理成功")
                    return True
                else:
                    print(f"❌ 第 {attempt} 次上传失败")
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

    def wait_for_pdf_token_count(self, title="PDF文件"):
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

        max_wait_time = 100  # 最多等待100秒，避免等待时间过长
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
                return True

            print(f"⏳ 等待token计数... 已等待 {elapsed_time}s")
            time.sleep(check_interval)
            elapsed_time += check_interval

        print(f"⚠️ 等待token计数超时 ({max_wait_time}s)，跳过此PDF文件")
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

注意：脚本会自动检测并使用 book_pdf_downloader.py 下载的PDF文件
        """,
    )

    parser.add_argument("--count", "-c", type=int, help="要生成的总结数量")
    parser.add_argument("--all", action="store_true", help="生成所有可用的总结")
    parser.add_argument(
        "--ads-id", default="kq316tr", help="AdsPower 浏览器ID (默认: kq316tr)"
    )
    parser.add_argument("--debug", "-d", action="store_true", help="启用调试模式")
    parser.add_argument(
        "--check-status", action="store_true", help="检查当前状态（不执行生成）"
    )

    args = parser.parse_args()

    # 创建生成器实例
    generator = BookSummaryGenerator(ads_id=args.ads_id, debug=args.debug)

    # 检查断点续传状态
    if args.check_status:
        generator.check_current_status()
        return

    # 确定生成数量
    max_count = None
    if args.count:
        max_count = args.count
    elif not args.all:
        # 默认生成5个
        max_count = 5

    print(f"🌐 使用 AdsPower ID: {args.ads_id}")

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
        print("🎯 生成所有可用的总结")

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
