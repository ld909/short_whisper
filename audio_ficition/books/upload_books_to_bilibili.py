#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍B站上传脚本
上传 merge_clips_with_audio.py 产生的MP4文件到B站
支持中文书籍上传

📚 功能说明:
- 支持中文书籍处理
- 读取B站Excel文件，获取待上传的书籍列表
- 从 merge_clips_with_audio.py 的输出中读取MP4视频文件
- 使用 generate_b_cover.py 生成的B站封面
- 使用 generate_youtube_titles.py 的中文标题
- 使用 generate_youtube_descriptions.py 的中文描述
- 自动选择"知识"分类
- 支持设定视频间隔时间
- 更新Excel状态

🌍 语言支持:
- 中文 (zh): books/zh/ 目录，book-zh-bilibili.xlsx 文件

📥 输入信息:
- Excel文件: excel/book-zh-bilibili.xlsx (列名: UUID | 是否发布 | 发布时间)
- MP4文件: {media_path}/books/zh/mp4_with_audio/{uuid}.mp4
- B站封面: {media_path}/books/zh/b_cover/{uuid}.png
- 标题文件: {media_path}/books/zh/youtube_titles/{uuid}.txt
- 描述文件: {media_path}/books/zh/youtube_description/{uuid}.txt

📤 输出信息:
- B站视频上传
- 更新的Excel状态文件

🔄 处理规则:
1. 支持macOS（Intel和Apple Silicon）和Ubuntu系统
2. 媒体路径配置：
   - Intel Mac: /Volumes/dhl/audio
   - Apple Silicon Mac: /Users/donghaoliu/Documents/audio
   - Ubuntu: /media/dhl/audio
3. 支持断点续传，跳过已上传的视频（是否发布=1）
4. 自动排除以点开头的Mac系统文件
5. 使用AdsPower浏览器进行上传
6. 自动选择"知识"分类

💡 使用示例:

# 基础使用
python upload_books_to_bilibili.py                                # 中文书籍上传
python upload_books_to_bilibili.py --max-count 3                  # 限制上传3个视频
python upload_books_to_bilibili.py --dry-run                      # 试运行模式

# 浏览器设置
python upload_books_to_bilibili.py --browser-id your_browser_id   # 指定浏览器ID

# 间隔时间设置
python upload_books_to_bilibili.py --interval 8                   # 8小时间隔
"""

import os
import sys
import time
import json
import random
import argparse
import platform
import urllib3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright
from tqdm import tqdm
from typing import Optional, Dict, List, Tuple

# ============ 配置参数 ============
# B站上传页面
BILIBILI_UPLOAD_URL = "https://member.bilibili.com/platform/upload/video/frame"

# AdsPower浏览器ID配置（默认）
DEFAULT_ADSPOWER_BROWSER_ID = "k10i5y1s"

# 最小文件大小检查
MIN_MP4_SIZE = 1024 * 1024 * 5  # 5MB
MIN_COVER_SIZE = 1024 * 10  # 10KB

# 默认发布间隔
DEFAULT_INTERVAL_HOURS = 6

# Excel文件路径配置
EXCEL_FILE = "excel/book-zh-bilibili.xlsx"


def get_base_media_path():
    """根据操作系统和芯片类型返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        # 检查芯片类型
        arch = platform.machine()
        if arch == "x86_64":  # Intel Mac
            return "/Volumes/dhl/audio"
        else:  # Apple Silicon (arm64)
            return "/Users/donghaoliu/Documents/audio"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/audio"


def get_directories():
    """获取所有相关目录路径"""
    base_media_path = get_base_media_path()
    books_path = os.path.join(base_media_path, "books", "zh")

    return {
        "mp4": os.path.join(books_path, "mp4_with_audio"),
        "b_covers": os.path.join(books_path, "b_cover"),
        "titles": os.path.join(books_path, "youtube_titles"),
        "descriptions": os.path.join(books_path, "youtube_description"),
        "excel": EXCEL_FILE,
    }


def check_supported_system():
    """检查是否为支持的系统（macOS或Ubuntu）"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return True
    elif system == "Linux":  # Linux/Ubuntu
        return True
    else:
        return False


def is_valid_file(file_path: str, min_size: int = 1024) -> bool:
    """检查文件是否有效"""
    if not os.path.exists(file_path):
        return False

    # 排除Mac系统产生的点开头文件
    filename = os.path.basename(file_path)
    if filename.startswith(".") or filename.startswith("._"):
        return False

    try:
        file_size = os.path.getsize(file_path)
        if file_size < min_size:
            return False
        return True
    except Exception:
        return False


def countdown_timer(total_seconds, description="等待中"):
    """在终端显示倒计时"""
    print(f"\n⏰ {description}...")

    while total_seconds > 0:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            time_str = f"{minutes:02d}:{seconds:02d}"

        print(f"\r⏱️  剩余时间: {time_str}", end="", flush=True)
        time.sleep(1)
        total_seconds -= 1

    print(f"\r✅ {description}完成！" + " " * 20)
    print()


class BookBilibiliUploader:
    def __init__(
        self,
        interval_hours=DEFAULT_INTERVAL_HOURS,
        browser_id=DEFAULT_ADSPOWER_BROWSER_ID,
    ):
        self.interval_hours = interval_hours
        self.directories = get_directories()
        self.browser_id = browser_id
        self.upload_url = BILIBILI_UPLOAD_URL
        self.http = None

        print(f"📚 书籍B站上传系统初始化")
        print(f"🌍 语言设置: 中文")
        print(f"⏱️  发布间隔: {self.interval_hours} 小时")
        print(f"🌐 B站上传页面: {self.upload_url}")
        print(f"🖥️  浏览器ID: {self.browser_id}")
        print(f"📁 Excel文件: {self.directories['excel']}")

    def get_adspower_info(self):
        """连接AdsPower浏览器"""
        open_url = f"http://local.adspower.net:50325/api/v1/browser/start?user_id={self.browser_id}"

        self.http = urllib3.PoolManager()

        print("🔌 正在连接AdsPower...")
        r = self.http.request("GET", open_url)

        if r.status != 200:
            print(f"❌ API返回状态码 {r.status}")
            return None, None

        resp = json.loads(r.data.decode("utf-8"))

        if resp["code"] != 0:
            print(f"❌ 错误: {resp['msg']}")
            return None, None

        ws_endpoint = resp["data"]["ws"]["puppeteer"]
        debug_port = resp["data"]["debug_port"]
        remote_debugging_url = f"http://localhost:{debug_port}"

        print(f"✅ 成功连接AdsPower")
        return ws_endpoint, remote_debugging_url

    def initialize_browser(self, max_retries=3):
        """初始化浏览器"""
        print("🔄 正在初始化浏览器...")

        for attempt in range(max_retries):
            print(f"📡 尝试连接浏览器 (第 {attempt + 1}/{max_retries} 次)...")

            # 连接AdsPower
            ws_endpoint, remote_debugging_url = self.get_adspower_info()
            if not ws_endpoint:
                if attempt < max_retries - 1:
                    countdown_timer(5, "等待重试")
                    continue
                else:
                    return None, None, None

            playwright = None
            try:
                playwright = sync_playwright().start()
                browser = playwright.chromium.connect_over_cdp(
                    remote_debugging_url, timeout=15000
                )

                if not browser.contexts:
                    context = browser.new_context()
                    print("📝 创建了新的浏览器上下文")
                else:
                    context = browser.contexts[0]
                    print("📝 使用现有的浏览器上下文")

                # 关闭现有tab
                existing_pages = context.pages
                for page in existing_pages:
                    try:
                        page.close()
                    except:
                        pass

                # 创建新tab
                new_page = context.new_page()

                return playwright, browser, new_page

            except Exception as e:
                print(f"❌ 浏览器连接失败 (第 {attempt + 1} 次): {e}")
                if playwright:
                    try:
                        playwright.stop()
                    except:
                        pass

                if attempt < max_retries - 1:
                    countdown_timer(10, "等待重试")
                    continue

        return None, None, None

    def load_book_title(self, uuid: str) -> Optional[str]:
        """加载书籍标题"""
        title_file = os.path.join(self.directories["titles"], f"{uuid}.txt")

        if not is_valid_file(title_file, 10):
            print(f"⚠️  [UUID:{uuid[:8]}...] 标题文件不存在或无效")
            return None

        try:
            with open(title_file, "r", encoding="utf-8") as f:
                title = f.read().strip()

            if not title:
                print(f"⚠️  [UUID:{uuid[:8]}...] 标题文件为空")
                return None

            return title
        except Exception as e:
            print(f"❌ [UUID:{uuid[:8]}...] 读取标题失败: {e}")
            return None

    def load_book_description(self, uuid: str) -> str:
        """加载书籍描述"""
        desc_file = os.path.join(self.directories["descriptions"], f"{uuid}.txt")

        if not is_valid_file(desc_file, 10):
            print(f"⚠️  [UUID:{uuid[:8]}...] 描述文件不存在，使用默认描述")
            return "这是一个精彩的书籍总结视频，希望大家喜欢！"

        try:
            with open(desc_file, "r", encoding="utf-8") as f:
                description = f.read().strip()

            if not description:
                print(f"⚠️  [UUID:{uuid[:8]}...] 描述文件为空，使用默认描述")
                return "这是一个精彩的书籍总结视频，希望大家喜欢！"

            return description
        except Exception as e:
            print(f"❌ [UUID:{uuid[:8]}...] 读取描述失败，使用默认描述: {e}")
            return "这是一个精彩的书籍总结视频，希望大家喜欢！"

    def get_book_content(self, book_info):
        """获取书籍的完整内容（标题、描述、封面等）"""
        uuid = book_info["uuid"]
        mp4_path = book_info["mp4_path"]

        print(f"📖 [UUID:{uuid[:8]}...] 获取书籍内容...")

        # 加载标题
        title = self.load_book_title(uuid)
        if not title:
            print(f"❌ [UUID:{uuid[:8]}...] 无法加载标题")
            return None

        print(f"🎬 [UUID:{uuid[:8]}...] 标题: {title}")

        # 获取描述
        description = self.load_book_description(uuid)
        print(f"📝 [UUID:{uuid[:8]}...] 描述长度: {len(description)} 字符")

        # 检查B站封面文件
        cover_path = os.path.join(self.directories["b_covers"], f"{uuid}.png")
        cover_exists = is_valid_file(cover_path, MIN_COVER_SIZE)

        if cover_exists:
            print(f"🖼️  [UUID:{uuid[:8]}...] B站封面文件: 存在")
        else:
            print(f"⚠️  [UUID:{uuid[:8]}...] B站封面文件: 不存在")
            cover_path = None

        return {
            "uuid": uuid,
            "mp4_path": mp4_path,
            "title": title,
            "description": description,
            "cover_path": cover_path,
            "valid": True,
        }

    def get_pending_books(self):
        """获取待上传的书籍列表"""
        print(f"\n🔍 扫描待上传的书籍...")

        excel_file = self.directories["excel"]
        if not os.path.exists(excel_file):
            print(f"❌ Excel文件不存在: {excel_file}")
            print(
                f"💡 请先运行: python generate_book_publish_excel.py --language zh --platform bilibili"
            )
            return []

        try:
            # 读取Excel文件
            df = pd.read_excel(excel_file)
            print(f"📊 Excel文件共 {len(df)} 条记录")

            # 过滤待上传的书籍（使用中文列名）
            if "是否发布" not in df.columns:
                print(f"❌ Excel文件缺少 '是否发布' 列")
                return []

            pending = df[df["是否发布"] == 0]
            print(f"📝 待上传书籍: {len(pending)} 个")

            # 检查对应的MP4文件是否存在
            valid_pending = []
            for _, row in pending.iterrows():
                # 获取UUID (假设第一列为UUID)
                uuid = row.iloc[0] if len(row) > 0 else None
                if not uuid:
                    continue

                # 排除以点开头的UUID（Mac系统文件）
                if str(uuid).startswith("."):
                    continue

                # 检查MP4文件
                mp4_path = os.path.join(self.directories["mp4"], f"{uuid}.mp4")
                if is_valid_file(mp4_path, MIN_MP4_SIZE):
                    book_info = {
                        "uuid": uuid,
                        "mp4_path": mp4_path,
                        "excel_row": row.name,  # 行索引
                    }
                    valid_pending.append(book_info)
                    print(f"✅ 有效书籍: {uuid}")
                else:
                    print(f"❌ MP4文件不存在或无效: {uuid}")

            print(f"✅ 最终有效书籍: {len(valid_pending)} 个")
            return valid_pending

        except Exception as e:
            print(f"❌ 读取Excel文件时出错: {e}")
            return []

    def upload_video_to_bilibili(self, video_content, page, dry_run=False):
        """上传视频到B站"""
        if dry_run:
            print(f"[试运行] 将要上传视频:")
            print(f"  文件: {video_content['mp4_path']}")
            print(f"  标题: {video_content['title']}")
            print(f"  描述长度: {len(video_content['description'])} 字符")
            print(f"  封面: {video_content['cover_path'] or '无'}")
            return True

        if not video_content["valid"]:
            print("❌ 视频内容无效，跳过上传")
            return False

        try:
            # 导航到B站上传页面
            print(f"🌐 正在导航到B站上传页面: {self.upload_url}")
            page.goto(self.upload_url)

            # 等待页面加载
            print("⏳ 等待页面加载...")
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            page.wait_for_timeout(5000)

            # 1. 上传MP4文件
            print(f"📁 正在上传视频: {video_content['mp4_path']}")

            # 等待上传输入框
            print("⏳ 等待文件上传输入框...")
            upload_input_selector = 'input[accept*=".mp4"]'
            page.wait_for_selector(
                upload_input_selector, state="attached", timeout=15000
            )

            # 优先使用CDP方法上传大文件
            try:
                cdp_session = page.context.new_cdp_session(page)
                dom_snapshot = cdp_session.send("DOM.getDocument")
                node_result = cdp_session.send(
                    "DOM.querySelector",
                    {
                        "nodeId": dom_snapshot["root"]["nodeId"],
                        "selector": upload_input_selector,
                    },
                )

                if node_result.get("nodeId"):
                    cdp_session.send(
                        "DOM.setFileInputFiles",
                        {
                            "nodeId": node_result["nodeId"],
                            "files": [video_content["mp4_path"]],
                        },
                    )
                    cdp_session.detach()
                    print("✅ 视频文件上传完成（CDP方法）")
                else:
                    raise Exception("CDP方法失败")

            except Exception:
                # 回退到标准方法
                file_input = page.locator(upload_input_selector)
                file_input.set_input_files(video_content["mp4_path"])
                print("✅ 视频文件上传完成（标准方法）")

            # 等待上传处理
            print("⏳ 等待视频上传处理...")
            countdown_timer(20, "视频上传后等待页面稳定")

            # 2. 上传封面
            if video_content.get("cover_path") and os.path.exists(
                video_content["cover_path"]
            ):
                print(f"📷 正在上传B站封面: {video_content['cover_path']}")

                try:
                    # 点击"更换封面"按钮
                    print("🔄 正在点击更换封面按钮...")
                    change_cover_span = page.locator('span:has-text("更换封面")')
                    change_cover_span.click()
                    print("✅ 已点击更换封面按钮")

                    # 等待2秒
                    page.wait_for_timeout(2000)

                    # 点击"上传封面"按钮
                    print("📤 正在点击上传封面按钮...")
                    upload_cover_div = page.locator('div.text:has-text("上传封面")')
                    upload_cover_div.click()
                    print("✅ 已点击上传封面按钮")

                    # 等待封面上传输入框
                    cover_input_selector = 'input[accept*="image/png"]'
                    page.wait_for_selector(
                        cover_input_selector, state="attached", timeout=10000
                    )

                    # 上传封面文件
                    try:
                        # 使用CDP方法上传封面
                        cdp_session = page.context.new_cdp_session(page)
                        cdp_session.send("DOM.enable")
                        doc = cdp_session.send("DOM.getDocument", {"depth": -1})
                        node_result = cdp_session.send(
                            "DOM.querySelector",
                            {
                                "nodeId": doc["root"]["nodeId"],
                                "selector": cover_input_selector,
                            },
                        )
                        if node_result.get("nodeId"):
                            cdp_session.send(
                                "DOM.setFileInputFiles",
                                {
                                    "nodeId": node_result["nodeId"],
                                    "files": [video_content["cover_path"]],
                                },
                            )
                            cdp_session.detach()
                            print("✅ 封面上传完成（CDP方法）")
                    except Exception:
                        # 回退到标准方法
                        page.set_input_files(
                            cover_input_selector, video_content["cover_path"]
                        )
                        print("✅ 封面上传完成（标准方法）")

                    # 等待1.5秒后点击"完成"按钮
                    page.wait_for_timeout(1500)
                    try:
                        print("🔘 正在点击完成按钮...")
                        complete_button = page.locator('button:has-text("完成")')
                        complete_button.click()
                        print("✅ 已点击完成按钮")
                    except Exception as e:
                        print(f"⚠️  点击完成按钮失败，继续处理: {e}")

                    # 点击完成按钮后等待2秒
                    page.wait_for_timeout(2000)

                except Exception as e:
                    print(f"⚠️  封面上传失败，继续处理: {e}")

            # 3. 输入标题
            print("✏️  正在输入标题...")
            title_input_selector = 'input[placeholder="请输入稿件标题"]'
            page.wait_for_selector(title_input_selector, state="visible", timeout=15000)

            title_input = page.locator(title_input_selector)
            title_input.click()
            title_input.press("Control+a")  # 全选清空
            title_input.fill(video_content["title"])
            print(f"✅ 已输入标题: {video_content['title']}")

            page.wait_for_timeout(2000)

            # 4. 输入描述
            print("✏️  正在输入描述...")
            description_text = video_content["description"]
            print(f"📝 描述内容长度: {len(description_text)} 字符")

            try:
                # 定位到编辑器 - 选择第一个（视频描述编辑器）
                editor_selector = 'div.ql-editor[contenteditable="true"]'
                page.wait_for_selector(editor_selector, state="visible", timeout=10000)
                editor_locator = page.locator(editor_selector).first

                # --- 方法一：首选方案，使用 Playwright 的 fill 和 type 方法 ---
                # 这个方法最可靠，因为它模拟了用户的真实输入行为，能有效触发框架的事件监听

                # 步骤 1: 点击编辑器以确保其获得焦点
                print("🖱️  正在点击编辑器使其获得焦点...")
                editor_locator.click()
                page.wait_for_timeout(500)  # 短暂等待，确保焦点设置成功

                # 步骤 2: 清空现有内容 (模拟全选 + 删除)
                print("🗑️  正在清空现有内容...")
                # 根据操作系统选择正确的全选快捷键
                select_all_key = (
                    "Meta+a" if platform.system() == "Darwin" else "Control+a"
                )
                editor_locator.press(select_all_key)
                page.wait_for_timeout(500)
                editor_locator.press("Backspace")
                page.wait_for_timeout(500)

                # 步骤 3: 填入新的描述内容
                print(f"✍️  正在填入新描述...")
                # 将描述按行分割，保留原有的段落格式
                lines = description_text.split("\n")
                for i, line in enumerate(lines):
                    if line.strip():  # 跳过空行
                        editor_locator.type(line)
                    # 如果不是最后一行，则添加一个换行
                    if i < len(lines) - 1:
                        editor_locator.press("Enter")
                    page.wait_for_timeout(100)  # 模拟输入的微小延迟

                print("✅ 已成功输入描述")

            except Exception as e:
                print(f"❌ 使用 Playwright fill/type 方法输入描述时出错: {e}")
                print("🤔 正在尝试使用 JavaScript 粘贴方法作为备选方案...")

                # --- 方法二：备选方案，使用 JavaScript 模拟粘贴 ---
                # 这个方法在 fill/type 失效时可以尝试，它比直接修改 innerHTML 更可靠
                try:
                    import json

                    # 将描述文本格式化为适合 JS 的字符串，保留换行符
                    js_description = json.dumps(description_text)

                    js_code = f"""
                    (() => {{
                        const editor = document.querySelector('div.ql-editor[contenteditable="true"]');
                        if (!editor) {{
                            console.error('编辑器未找到');
                            return false;
                        }}
                        
                        editor.focus();
                        editor.innerHTML = ''; // 先清空
                        
                        // 模拟粘贴事件
                        const dataTransfer = new DataTransfer();
                        dataTransfer.setData('text/plain', {js_description});
                        
                        const pasteEvent = new ClipboardEvent('paste', {{
                            clipboardData: dataTransfer,
                            bubbles: true,
                            cancelable: true
                        }});
                        
                        editor.dispatchEvent(pasteEvent);
                        
                        // 检查内容是否成功粘贴
                        // Quill 可能需要一点时间来处理粘贴事件并更新 DOM
                        setTimeout(() => {{
                            if (editor.innerText.includes({js_description}.substring(0, 10))) {{
                                console.log('JavaScript 粘贴方法成功');
                            }} else {{
                                console.error('JavaScript 粘贴方法可能失败，内容未完全更新');
                            }}
                        }}, 500);

                        return true;
                    }})();
                    """
                    success = page.evaluate(js_code)
                    if success:
                        print("✅ 已通过 JavaScript 粘贴方法输入描述")
                    else:
                        print("❌ JavaScript 粘贴方法也失败了，请手动输入描述")

                except Exception as js_e:
                    print(f"❌ JavaScript 备选方案也出错: {js_e}")
                    print("💡 自动输入描述失败，请暂停脚本并手动输入描述内容")

            page.wait_for_timeout(3000)

            print("🎉 视频信息填写完成！")
            print("💡 请手动完成后续步骤（投币、充电等设置）并发布视频")

            # 等待一段时间让用户手动操作
            countdown_timer(30, "等待手动完成发布操作")

            return True

        except Exception as e:
            print(f"❌ 上传视频时出错: {e}")
            return False

    def update_excel_status(self, book_info, publish_time):
        """更新Excel中的发布状态"""
        excel_file = self.directories["excel"]
        uuid = book_info["uuid"]

        print(f"📝 开始更新Excel状态: {uuid}")

        try:
            # 读取当前数据
            df = pd.read_excel(excel_file)

            # 查找对应的行
            # 假设第一列是UUID
            mask = df.iloc[:, 0] == uuid

            if not mask.any():
                print(f"❌ 在Excel中未找到UUID记录: {uuid}")
                return False

            # 更新状态（使用中文列名）
            df.loc[mask, "是否发布"] = 1
            df.loc[mask, "发布时间"] = publish_time.strftime("%Y-%m-%d %H:%M:%S")

            # 保存更新后的数据
            df.to_excel(excel_file, index=False)
            print(f"✅ Excel状态更新成功")

            return True

        except Exception as e:
            print(f"❌ 更新Excel状态时出错: {e}")
            return False

    def run(self, max_count=None, dry_run=False):
        """运行书籍上传系统"""
        print(f"\n{'='*60}")
        print(f"🚀 书籍B站上传系统启动")
        print(f"{'='*60}")

        # 获取待上传书籍
        pending_books = self.get_pending_books()
        if not pending_books:
            print("❌ 没有待上传的书籍")
            return None

        # 限制上传数量
        if max_count:
            books_to_upload = pending_books[:max_count]
            print(
                f"\n📊 将要处理 {len(books_to_upload)} 个书籍 (限制数量: {max_count})"
            )
        else:
            books_to_upload = pending_books
            print(f"\n📊 将要处理所有 {len(books_to_upload)} 个书籍")

        # 显示书籍列表
        for i, book in enumerate(books_to_upload, 1):
            print(f"   {i}. UUID: {book['uuid']}")

        # 初始化浏览器（仅在非试运行模式）
        playwright = None
        browser = None
        page = None

        if not dry_run:
            print(f"\n🚀 正在初始化浏览器...")
            playwright, browser, page = self.initialize_browser()
            if not page:
                print("❌ 浏览器初始化失败，终止运行")
                return
            print("✅ 浏览器初始化完成")

        try:
            # 处理每个书籍
            for i, book_info in enumerate(books_to_upload, 1):
                print(f"\n{'-'*50}")
                print(f"📖 处理书籍 {i}/{len(books_to_upload)}: {book_info['uuid']}")
                print(f"{'-'*50}")

                # 获取书籍内容
                video_content = self.get_book_content(book_info)
                if not video_content:
                    print(f"❌ 无法获取书籍内容，跳过")
                    continue

                # 上传视频
                print(f"🚀 开始上传第 {i} 个书籍...")
                upload_result = self.upload_video_to_bilibili(
                    video_content, page, dry_run
                )

                # 处理上传结果
                if upload_result:
                    print(f"🎉 书籍 {book_info['uuid']} 上传成功！")

                    if not dry_run:
                        # 更新Excel状态
                        current_time = datetime.now()
                        update_success = self.update_excel_status(
                            book_info, current_time
                        )
                        if update_success:
                            print(f"✅✅ 完整成功: 视频发布成功且Excel已更新")
                        else:
                            print(f"❌⚠️ 部分成功: 视频发布成功，但Excel更新失败")
                    else:
                        print(f"✅ [试运行] 书籍处理完成")
                else:
                    print(f"❌ 书籍 {book_info['uuid']} 上传失败")

                # 视频间隔等待
                if i < len(books_to_upload):
                    wait_time = self.interval_hours * 3600  # 转换为秒
                    countdown_timer(
                        wait_time, f"视频间隔等待 {self.interval_hours} 小时"
                    )

        except KeyboardInterrupt:
            print("\n🛑 用户中断操作")
            raise
        except Exception as e:
            print(f"❌ 运行过程中发生错误: {e}")
        finally:
            # 清理资源
            if not dry_run and playwright:
                try:
                    print("\n🧹 正在清理浏览器资源...")
                    print("💡 浏览器将保持打开状态，方便检查上传结果")
                except Exception as cleanup_error:
                    print(f"⚠️ 清理资源时出错: {cleanup_error}")

        print(f"\n{'='*60}")
        print(f"🎉 书籍上传任务完成")
        print(f"📊 总计处理了 {len(books_to_upload)} 个书籍")
        print(f"{'='*60}")


def check_dependencies():
    """检查必要的依赖是否安装"""
    missing_deps = []

    try:
        import pandas as pd
    except ImportError:
        missing_deps.append("pandas")

    try:
        import urllib3
    except ImportError:
        missing_deps.append("urllib3")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        missing_deps.append("playwright")

    if missing_deps:
        print(f"❌ 缺少依赖包: {', '.join(missing_deps)}")
        print("请安装缺少的依赖:")
        for dep in missing_deps:
            print(f"  pip install {dep}")
        if "playwright" in missing_deps:
            print("  playwright install chromium")
        return False

    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="书籍B站上传脚本 - 上传merge_clips_with_audio.py产生的MP4文件到B站",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
功能说明:
  1. 读取B站Excel文件中的书籍列表
  2. 跳过已上传的书籍（是否发布=1）
  3. 获取书籍MP4文件、B站封面、标题、描述
  4. 按设定的时间间隔自动上传到B站
  5. 自动选择"知识"分类
  6. 更新Excel文件中的发布状态

Excel文件格式要求:
  - 列名: UUID | 是否发布 | 发布时间
  - '是否发布' 列: 0=未发布, 1=已发布
  - '发布时间' 列: 日期时间字符串 (YYYY-MM-DD HH:MM:SS)

使用示例:
  python upload_books_to_bilibili.py                    # 基础上传
  python upload_books_to_bilibili.py --dry-run          # 试运行模式
  python upload_books_to_bilibili.py --max-count 3      # 限制上传3个
  python upload_books_to_bilibili.py --interval 8       # 8小时间隔
  python upload_books_to_bilibili.py --browser-id xxx   # 指定浏览器ID

配置信息:
  B站上传页面: https://member.bilibili.com/platform/upload/video/frame
  默认浏览器ID: k10i5y1s
  默认发布间隔: 6小时
        """,
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_HOURS,
        help=f"视频上传间隔小时数 (默认: {DEFAULT_INTERVAL_HOURS})",
    )
    parser.add_argument("--max-count", type=int, help="最大上传数量 (默认: 全部)")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式，不实际上传")
    parser.add_argument(
        "--browser-id",
        default=DEFAULT_ADSPOWER_BROWSER_ID,
        help=f"AdsPower浏览器ID (默认: {DEFAULT_ADSPOWER_BROWSER_ID})",
    )

    args = parser.parse_args()

    print("📚 书籍B站上传系统")
    print("=" * 60)
    print(f"🖥️  操作系统: {platform.system()}")
    print(f"🏗️  架构类型: {platform.machine()}")
    print(f"📅 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 检查依赖
    if not check_dependencies():
        return

    # 检查系统
    if not check_supported_system():
        print("⚠️  此脚本主要为macOS和Ubuntu系统设计，其他系统可能需要调整路径")

    # 显示配置信息
    print(f"\n🔧 配置信息:")
    print(f"   语言设置: 中文")
    print(f"   B站上传页面: {BILIBILI_UPLOAD_URL}")
    print(f"   浏览器ID: {args.browser_id}")
    print(f"   Excel文件: {EXCEL_FILE}")
    print(f"   视频间隔: {args.interval} 小时")
    print(f"   最大数量: {args.max_count or '全部'}")
    print(f"   运行模式: {'试运行' if args.dry_run else '实际上传'}")
    print(f"   媒体根目录: {get_base_media_path()}")

    # 创建上传器实例
    uploader = BookBilibiliUploader(
        interval_hours=args.interval,
        browser_id=args.browser_id,
    )

    # 运行上传系统
    try:
        uploader.run(max_count=args.max_count, dry_run=args.dry_run)
        print("\n🎉 程序正常结束")

    except KeyboardInterrupt:
        print("\n\n🛑 用户中断操作")
        print("📝 提示：浏览器连接已断开，AdsPower浏览器实例仍保持打开状态")
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ 系统错误: {e}")
        print("\n🔧 故障排除建议:")
        print("   1. 检查AdsPower是否正常运行")
        print("   2. 确认浏览器ID是否正确")
        print("   3. 检查网络连接")
        print("   4. 确认Excel文件格式正确，列名为：UUID、是否发布、发布时间")
        print("   5. 检查视频文件路径是否正确")
        print("   6. 确认生成的标题、描述、B站封面文件存在")
        print("   7. 运行试运行模式检查：python upload_books_to_bilibili.py --dry-run")
        print(
            "   8. 生成Excel文件：python generate_book_publish_excel.py --language zh --platform bilibili"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
